# -*- coding: utf-8 -*-
"""zimage reliability primitives.

This module is deliberately local-only: hashing, manifests, atomic writes, and
post-generation image/mask measurements. It never sends a network request and
never stores credentials.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

SCHEMA_VERSION = "zimage-reliability-v2"


def job_id() -> str:
    """Return a sortable, collision-resistant job id."""
    return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_prompt(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\r\n", "\n").strip())


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_replace(src: Path, dst: Path, *, force: bool = False) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and not force:
        raise FileExistsError(f"输出已存在（加 --force 才覆盖）：{dst}")
    os.replace(src, dst)


def atomic_copy(src: Path, dst: Path, *, force: bool = True) -> None:
    """Copy a completed artifact atomically; never expose a half-written cache file."""
    import shutil
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and not force:
        raise FileExistsError(f"目标已存在：{dst}")
    fd, tmp = tempfile.mkstemp(prefix=f".{dst.name}.", suffix=".tmp", dir=str(dst.parent))
    os.close(fd)
    try:
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def cache_entry(root: Path, fingerprint: str) -> tuple[Path, Path, Path]:
    """Return (entry_dir, result_path, manifest_path) for one request fingerprint."""
    entry = root / fingerprint[:2] / fingerprint
    return entry, entry / "result.png", entry / "manifest.json"


def load_valid_cache(root: Path, fingerprint: str) -> dict[str, Any] | None:
    """Return a validated cache record, or None for any incomplete/corrupt entry."""
    entry, result, manifest = cache_entry(root, fingerprint)
    if not result.is_file() or not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if data.get("request_fingerprint") != fingerprint:
            return None
        validation = data.get("validation") or {}
        if validation.get("status") not in ("PASS", "PASS_WITH_WARNING"):
            return None
        if data.get("result_sha256") != sha256_file(result):
            return None
        with Image.open(result) as im:
            im.load()
        data["result_path"] = str(result)
        return data
    except (OSError, ValueError, TypeError):
        return None


def store_cache(root: Path, fingerprint: str, result: Path, **metadata: Any) -> dict[str, Any]:
    """Store a validated result and its metadata; manifest is written last."""
    entry, cached_result, manifest = cache_entry(root, fingerprint)
    entry.mkdir(parents=True, exist_ok=True)
    atomic_copy(result, cached_result, force=True)
    with Image.open(cached_result) as im:
        im.load()
        result_size = list(im.size)
    record = {
        "request_fingerprint": fingerprint,
        "result_sha256": sha256_file(cached_result),
        "result_size": result_size,
        "cached_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        **metadata,
    }
    write_manifest(manifest, record)
    return record


def _scrub(value: Any, *, field: str = "") -> Any:
    """递归清理 manifest 里的常见凭据字段和值。"""
    sensitive = any(x in field.lower() for x in ("key", "authorization", "token", "secret", "password"))
    if sensitive:
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): _scrub(v, field=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v, field=field) for v in value]
    if isinstance(value, str):
        if "sk-" in value or "Bearer " in value:
            return "[REDACTED]"
    return value


def write_manifest(path: Path, data: dict[str, Any]) -> None:
    clean = _scrub(data)
    atomic_write_text(path, json.dumps(clean, ensure_ascii=False, indent=2) + "\n")


def update_manifest(path: Path, **updates: Any) -> dict[str, Any]:
    """Merge updates atomically, preserving a redacted state history for diagnosis."""
    current: dict[str, Any] = {}
    if path.is_file():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            current = {}
    previous = current.get("state")
    next_state = updates.get("state")
    if next_state and next_state != previous:
        history = list(current.get("state_history") or [])
        history.append({"state": next_state, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
        updates["state_history"] = history
    current.update(updates)
    write_manifest(path, current)
    return current


def request_fingerprint(*, source: Path, mask: Path | None, prompt: str,
                        model: str, size: str, quality: str,
                        pad: str, mask_invert: bool,
                        refs: list[Path] | None = None,
                        encode: str = "png", jpg_quality: int = 90,
                        budget_mib: float = 1.55,
                        endpoint: str = "",
                        mask_primary: bool = False) -> str:
    payload = {
        "source_sha256": sha256_file(source),
        "mask_sha256": sha256_file(mask) if mask else None,
        "ref_sha256": [sha256_file(Path(ref)) for ref in (refs or [])],
        "normalized_prompt_sha256": sha256_text(normalize_prompt(prompt)),
        "model": model,
        "size": size,
        "quality": quality,
        "pad": pad,
        "encode": encode,
        "jpg_quality": int(jpg_quality),
        "budget_mib": float(budget_mib),
        "endpoint": endpoint.rstrip("/"),
        "mask_invert": bool(mask_invert),
        "mask_primary": bool(mask_primary),
        "schema": SCHEMA_VERSION,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _crop_for_target(im: Image.Image, target_ar: float) -> Image.Image:
    src_ar = im.width / im.height
    if src_ar > target_ar:
        nw = int(im.height * target_ar)
        x = (im.width - nw) // 2
        return im.crop((x, 0, x + nw, im.height))
    nh = int(im.width / target_ar)
    y = (im.height - nh) // 2
    return im.crop((0, y, im.width, y + nh))


def _fit_mask(mask: Image.Image, tw: int, th: int, pad: str, out_size: tuple[int, int]) -> np.ndarray:
    """将源图坐标 alpha 映射到结果坐标，严格复刻 normalise_to_size 的 crop/pad 语义。"""
    target_ar = tw / th
    if pad == "crop":
        fitted = _crop_for_target(mask, target_ar)
        return np.asarray(fitted.resize(out_size, Image.NEAREST)) > 127
    scale = min(tw / mask.width, th / mask.height)
    nw, nh = max(1, round(mask.width * scale)), max(1, round(mask.height * scale))
    fitted = Image.new("L", (tw, th), 0)
    resized = mask.resize((nw, nh), Image.NEAREST)
    fitted.paste(resized, ((tw - nw) // 2, (th - nh) // 2))
    return np.asarray(fitted.resize(out_size, Image.NEAREST)) > 127


def _fit_source(source: Image.Image, tw: int, th: int, pad: str, out_size: tuple[int, int]) -> Image.Image:
    """和 mask 使用同一对齐规则，生成用于保护区比较的源图。"""
    target_ar = tw / th
    if pad == "crop":
        fitted = _crop_for_target(source.convert("RGB"), target_ar)
        return fitted.resize(out_size, Image.LANCZOS)
    scale = min(tw / source.width, th / source.height)
    nw, nh = max(1, round(source.width * scale)), max(1, round(source.height * scale))
    fitted = Image.new("RGB", (tw, th), (255, 255, 255))
    resized = source.convert("RGB").resize((nw, nh), Image.LANCZOS)
    fitted.paste(resized, ((tw - nw) // 2, (th - nh) // 2))
    return fitted.resize(out_size, Image.LANCZOS)


def protection_metrics(source: Path, result: Path, mask: Path, *, requested_size: str,
                       pad: str = "crop", invert: bool) -> dict[str, Any]:
    """Compare result against a normalized source and report editable/protected diffs."""
    sw, sh = (int(x) for x in requested_size.split("x"))
    src = Image.open(source).convert("RGB")
    out = Image.open(result).convert("RGB")
    out.load()
    src_fit = _fit_source(src, sw, sh, pad, out.size)

    m = Image.open(mask)
    m.load()
    alpha = np.asarray(m.convert("RGBA").getchannel("A")) > 127
    alpha_img = Image.fromarray((alpha.astype(np.uint8) * 255), "L")
    # 与 run_round 的 normalise_to_size 使用相同 pad/crop 语义，不能直接拉伸整张 mask。
    edit = _fit_mask(alpha_img, sw, sh, pad, out.size)
    protected = ~edit if not invert else edit

    a = np.asarray(src_fit).astype(np.float32)
    b = np.asarray(out).astype(np.float32)
    diff = np.abs(a - b).mean(axis=2)
    protected_mean = float(diff[protected].mean()) if protected.any() else 0.0
    editable_mean = float(diff[~protected].mean()) if (~protected).any() else 0.0
    protected_unchanged = float((diff[protected] < 12).mean()) if protected.any() else 1.0
    editable_changed = float((diff[~protected] > 12).mean()) if (~protected).any() else 0.0
    ratio = editable_mean / max(protected_mean, 1e-6)
    status = "PASS"
    warnings: list[str] = []
    if protected_unchanged < 0.98:
        status = "FAIL"
        warnings.append(f"保护区保持率 {protected_unchanged * 100:.1f}% < 98%")
    if editable_mean <= protected_mean and (~protected).any():
        status = "FAIL"
        warnings.append("可改区平均差异不高于保护区，疑似未按遮罩编辑")
    if out.size != (sw, sh):
        if status == "PASS":
            status = "PASS_WITH_WARNING"
        warnings.append(f"结果尺寸 {out.width}x{out.height} != 请求 {sw}x{sh}")
    return {
        "status": status,
        "source_size": list(src.size),
        "result_size": list(out.size),
        "requested_size": [sw, sh],
        "protected_mean_abs_diff": round(protected_mean, 3),
        "editable_mean_abs_diff": round(editable_mean, 3),
        "protected_unchanged_ratio": round(protected_unchanged, 5),
        "editable_changed_ratio": round(editable_changed, 5),
        "editable_to_protected_ratio": round(ratio, 3),
        "warnings": warnings,
    }
