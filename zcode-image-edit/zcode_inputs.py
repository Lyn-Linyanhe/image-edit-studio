#!/usr/bin/env python3
"""从 ZCode 自己的存储里重建画廊「输入」页签的索引（不依赖 DSH）。

为什么需要单独一个脚本：DSH 版索引（`build_user_inputs_index.py`）读的是
`~/.dsh/sessions/**/session.jsonl.zstd`；ZCode 完全不存那个格式——ZCode 把用户上传的图
**以 base64 data URL 存成"artifact"文本文件**，元数据在 SQLite 里。所以数据源必须换掉。

ZCode 侧的存储事实（2026-09-25 实测核实）：
  · 会话与消息：`<storage>/cli/db/db.sqlite`
      - 表 `session(id, directory, time_updated, …)` —— `directory` 是工作区路径，用它过滤项目
      - 表 `session_input(session_id, kind, payload, …)`；`kind='sendText'` 的 payload 里有
        `attachments: [{ref, fileName, mime, bytes, previewRef?}]`
  · 上传的图：`<storage>/cli/artifacts/<把 sessionId 里非 [A-Za-z0-9._-] 换成 _ 并截断 120 字符>/`
      文件名形如 `prompt-attachment-upload-<ts36>-<rand>-tool-result-<uuid>.txt`，
      正文是一整条 `data:<mime>;base64,<...>` 文本
  · `ref` 是 `zcode-artifact://<sessionId>/<artifactId>`，artifactId 即文件名里的 `tool-result-<uuid>` 段
  · **ZCode 不持久化上传内容的 sha256**（只有传输期的 checksum 字段，不落库），
    所以要自己 base64 解码后算哈希，才能与工作区文件配对。

输出 schema 与 DSH 版**完全一致**（`paths` / `excluded` / `unreachable`），
因为画廊只消费这三个键；这样切数据源只需把 `GALLERY_USER_INPUTS` 指向本文件，
**不用改 gallery_category 的任何判定**（保护那 64 条回归断言）。
  · paths        上传的图能在工作区里按 sha256 找到 → 画廊可展示（工作区相对路径、小写、正斜杠）
  · excluded     会话比"最近一次"更早 → 按你的既有口径"只从最近这轮开始计入"，故不展示
  · unreachable  解出来了但工作区里没有同内容文件 → 无法定位，只能如实报数量（不造假卡片）
"""
from __future__ import annotations
import sys as _sys

# Windows 上 stdout 默认 cp936：打印 GBK 编不出的字符会直接崩，故脚本自带 UTF-8 前置。
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

import argparse
import base64
import hashlib
import io
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}


def storage_root() -> Path:
    """ZCode 存储根。文档口径：ZCODE_STORAGE_DIR 可覆盖，默认 ~/.zcode。"""
    env = os.environ.get("ZCODE_STORAGE_DIR")
    return Path(env) if env else (Path.home() / ".zcode")


def sanitize(session_id: str) -> str:
    """对应 ZCode 内部的 sF()：非 [A-Za-z0-9._-] 一律换成 _，并截断到 120 字符。"""
    return re.sub(r"[^A-Za-z0-9._-]", "_", session_id)[:120]


def find_artifact(artifacts_dir: Path, session_id: str, artifact_id: str) -> Path | None:
    """artifacts 目录里挑出文件名含 artifactId 的那个。"""
    d = artifacts_dir / sanitize(session_id)
    if not d.is_dir():
        return None
    aid = artifact_id.strip()
    for p in d.iterdir():
        if p.is_file() and aid and aid in p.name:
            return p
    return None


def decode_data_url(text: str) -> tuple[bytes, str] | None:
    """把 `data:<mime>;base64,<...>` 解回原始字节。"""
    m = re.match(r"\s*data:([^;,]+);base64,(.*)\Z", text, re.S)
    if not m:
        return None
    mime, b64 = m.group(1), re.sub(r"\s+", "", m.group(2))
    try:
        return base64.b64decode(b64), mime
    except Exception:
        return None


def workspace_images(root: Path) -> dict[str, str]:
    """工作区里所有图片：sha256 -> 相对路径（正斜杠、小写）。"""
    out = {}
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            p = Path(dp) / f
            if p.suffix.lower() not in IMG_EXT:
                continue
            try:
                if p.stat().st_size > 64 * 1024 * 1024:
                    continue
                h = hashlib.sha256(p.read_bytes()).hexdigest()
            except Exception:
                continue
            out.setdefault(h, str(p.relative_to(root)).replace("\\", "/").lower())
    return out


def collect(store: Path, root: Path) -> dict:
    db = store / "cli" / "db" / "db.sqlite"
    art = store / "cli" / "artifacts"
    info = {"db": str(db), "artifacts": str(art), "db_found": db.is_file(),
            "notes": []}
    if not db.is_file():
        info["notes"].append(f"找不到 ZCode 数据库：{db}")
        return info

    # 只读打开：uri=True + mode=ro，绝不写库
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        target = os.path.normcase(os.path.normpath(str(root)))
        sessions = []
        for sid, directory, tupd in cur.execute(
                "SELECT id, directory, time_updated FROM session"):
            if not directory:
                continue
            if os.path.normcase(os.path.normpath(str(directory))) == target:
                sessions.append((sid, tupd or 0))
        info["sessions_total"] = len(sessions)
        latest = max((t for _, t in sessions), default=None)

        uploads = []          # (session_id, ts, desc, ref)
        for sid, payload, tcreated in cur.execute(
                "SELECT session_id, payload, time_created FROM session_input "
                "WHERE kind = 'sendText' ORDER BY time_created"):
            if sid not in {s for s, _ in sessions}:
                continue
            try:
                d = json.loads(payload or "{}")
            except Exception:
                continue
            for a in (d.get("attachments") or []):
                mime = str(a.get("mime") or "")
                if not mime.startswith("image/"):
                    continue
                uploads.append((sid, tcreated or 0, a, str(a.get("ref") or "")))
        info["uploads_total"] = len(uploads)
    finally:
        con.close()

    return {"info": info, "sessions": sessions, "uploads": uploads,
            "latest": latest}


def main() -> int:
    ap = argparse.ArgumentParser(description="从 ZCode 存储重建画廊「输入」索引")
    ap.add_argument("--root", default="", help="工作区根（默认从本文件往上找 mantu）")
    ap.add_argument("-o", "--out", default="",
                    help="输出 JSON（默认 <root>/style-distill/round_lib/user_inputs_zcode.json）")
    ap.add_argument("--all-sessions", action="store_true",
                    help="把更早会话的上传也算进来（默认只算最近一次会话）")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    root = Path(a.root).resolve() if a.root else None
    if root is None:
        for cand in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]:
            if (cand / "compose" / "images" / "mask_edit_app.py").is_file():
                root = cand
                break
    if root is None or not root.is_dir():
        raise SystemExit("找不到工作区根，请用 --root 指定")

    store = storage_root()
    print(f"  工作区根   : {root}")
    print(f"  ZCode 存储 : {store}")

    got = collect(store, root)
    info = got["info"]
    print(f"  数据库     : {'✓' if info['db_found'] else '**缺失**'} {info['db']}")
    for n in info["notes"]:
        print("   ! " + n)
    print(f"  本项目会话 : {info.get('sessions_total', 0)} 个")
    print(f"  图片附件   : {info.get('uploads_total', 0)} 条")

    hash2rel = workspace_images(root)
    print(f"  工作区图片 : {len(hash2rel)} 个不同内容（用于 sha256 配对）")

    latest = got["latest"]
    paths, excluded, unreachable = [], [], []
    seen = set()
    for sid, ts, att, ref in got["uploads"]:
        name = str(att.get("fileName") or "")
        older = (not a.all_sessions) and latest is not None and ts < latest
        # ref: zcode-artifact://<sessionId>/<artifactId>
        art_id = ref.rsplit("/", 1)[-1] if "://" in ref else ""
        rel = None
        if art_id:
            p = find_artifact(Path(info["artifacts"]), sid, art_id)
            if p is not None:
                dec = decode_data_url(p.read_text(encoding="utf-8", errors="replace"))
                if dec:
                    data, _mime = dec
                    rel = hash2rel.get(hashlib.sha256(data).hexdigest())
                    if rel is None:
                        try:
                            from PIL import Image
                            im = Image.open(io.BytesIO(data)); im.load()
                            unreachable.append({"name": name, "width": im.width,
                                                "height": im.height, "bytes": len(data)})
                        except Exception:
                            unreachable.append({"name": name, "bytes": len(data)})
        if rel and not older:
            if rel not in seen:
                seen.add(rel)
                paths.append(rel)
        elif rel and older:
            excluded.append({"name": name, "path": rel})
        elif not rel:
            # 既没定位到工作区、也可能连 artifact 都没找到：只报数量，不造假卡片
            if a.verbose:
                print(f"    · 无法定位：{name or ref}")
    # 工作区里没有对应内容的那些，若连 artifact 都没读到，也要有个数量口径
    idx = {
        "source": "zcode",
        "generated_from": {
            "storage": str(store),
            "db": info["db"],
            "sessions": info.get("sessions_total", 0),
            "scope": "all-sessions" if a.all_sessions else "latest-session-only",
        },
        "paths": sorted(set(paths)),
        "excluded": excluded,
        "unreachable": unreachable,
    }
    out = Path(a.out) if a.out else (root / "style-distill" / "round_lib" / "user_inputs_zcode.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  写出 {out}")
    print(f"    paths        {len(idx['paths'])} 条（可在画廊展示）")
    print(f"    excluded     {len(excluded)} 条（更早会话的上传，按口径不计入）")
    print(f"    unreachable  {len(unreachable)} 条（工作区里没有同内容文件，只报数量）")
    if not idx["paths"] and not unreachable:
        print("\n  说明：这台机器上目前没有任何 ZCode 上传的图片，所以是 0 条——这是**如实结果**，不是故障。")
        print("        在 ZCode 对话里发一张图后重跑本脚本即可看到数据。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
