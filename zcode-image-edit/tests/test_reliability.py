# -*- coding: utf-8 -*-
"""zimage reliability 第一批本地测试：不访问上游。"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\Users\typ\Desktop\mantu")
PY = r"C:\Python314\python.exe"
PKG = ROOT / "zcode-image-edit"
sys.path.insert(0, str(PKG))
import reliability as R  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="zimage-reliability-test-"))
failures = []

def check(ok, name, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}  {detail}")
    if not ok:
        failures.append(name)

try:
    print("== reliability.py primitives ==")
    ids = {R.job_id() for _ in range(20)}
    check(len(ids) == 20, "job id uniqueness")
    check(all(len(x.split("-")) == 3 for x in ids), "job id shape")
    check(R.normalize_prompt("  a\r\n b   c ") == "a b c", "prompt normalization")

    src = ROOT / "style-distill" / "round_arcade" / "out_v2_r4_wink.png"
    mask = TMP / "mask.png"
    r = subprocess.run([PY, str(PKG / "mask_gen.py"), "--image", str(src),
                        "--rect", "300,200,700,600", "-o", str(mask)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(r.returncode == 0 and mask.is_file(), "mask generation", r.stderr[:180])

    f1 = R.request_fingerprint(source=src, mask=mask, prompt="  change  background ",
                               model="gpt-image-2", size="1024x1536", quality="low",
                               pad="crop", mask_invert=False)
    f2 = R.request_fingerprint(source=src, mask=mask, prompt="change background",
                               model="gpt-image-2", size="1024x1536", quality="low",
                               pad="crop", mask_invert=False)
    f3 = R.request_fingerprint(source=src, mask=mask, prompt="change background",
                               model="gpt-image-2", size="1024x1536", quality="low",
                               pad="crop", mask_invert=True)
    check(f1 == f2, "fingerprint stable under whitespace normalization")
    check(f1 != f3, "fingerprint changes with mask semantics")

    mf = TMP / "manifest.json"
    R.write_manifest(mf, {"job_id": "test", "state": "created", "api_key": "secret"})
    d = json.loads(mf.read_text(encoding="utf-8"))
    check(d.get("api_key") == "[REDACTED]", "manifest secret scrub")
    nested = TMP / "nested-manifest.json"
    R.write_manifest(nested, {"meta": {"token": "secret", "text": "ok"}})
    nd = json.loads(nested.read_text(encoding="utf-8"))
    check(nd["meta"]["token"] == "[REDACTED]", "nested manifest secret scrub")
    target = TMP / "atomic.txt"
    R.atomic_write_text(target, "one\n")
    check(target.read_text(encoding="utf-8") == "one\n", "atomic write")
    check(not list(TMP.glob(".atomic.txt.*.tmp")), "atomic temp cleanup")
    state = TMP / "state.json"
    R.update_manifest(state, state="created")
    R.update_manifest(state, state="prepared")
    sd = json.loads(state.read_text(encoding="utf-8"))
    check([x["state"] for x in sd["state_history"]] == ["created", "prepared"],
          "manifest state history")
    atomic_target = TMP / "atomic-result.png"
    temp_result = TMP / "result.tmp.png"
    temp_result.write_bytes(b"new")
    R.atomic_replace(temp_result, atomic_target)
    check(atomic_target.read_bytes() == b"new" and not temp_result.exists(), "atomic result replace")
    atomic_copy_target = TMP / "atomic-copy.bin"
    R.atomic_copy(atomic_target, atomic_copy_target)
    check(atomic_copy_target.read_bytes() == b"new" and not list(TMP.glob(".atomic-copy.bin.*.tmp")),
          "atomic cache copy")

    cache_root = TMP / "cache"
    cache_source = TMP / "cache-source.png"
    Image.new("RGB", (24, 18), (12, 34, 56)).save(cache_source)
    cache_fp = R.request_fingerprint(source=src, mask=mask, prompt="cache",
                                     model="gpt-image-2", size="1024x1536", quality="low",
                                     pad="crop", mask_invert=False, encode="png", mask_primary=True)
    R.store_cache(cache_root, cache_fp, cache_source, validation={"status": "PASS"})
    hit = R.load_valid_cache(cache_root, cache_fp)
    check(hit is not None and Path(hit["result_path"]).is_file(), "valid cache hit")
    Path(hit["result_path"]).write_bytes(b"corrupt")
    check(R.load_valid_cache(cache_root, cache_fp) is None, "corrupt cache rejected")

    print("\n== protection metrics ==")
    source = TMP / "source.png"
    result = TMP / "result.png"
    Image.new("RGB", (200, 200), (100, 100, 100)).save(source)
    m = Image.new("RGBA", (200, 200), (255, 255, 255, 0))
    ImageDraw.Draw(m).rectangle((50, 50, 150, 150), fill=(255, 255, 255, 255))
    mpath = TMP / "m.png"; m.save(mpath)
    out = Image.open(source).copy()
    ImageDraw.Draw(out).rectangle((50, 50, 150, 150), fill=(200, 50, 20))
    out.save(result)
    met = R.protection_metrics(source, result, mpath, requested_size="200x200", pad="crop", invert=False)
    check(met["status"] == "PASS", "protection metrics pass", json.dumps(met, ensure_ascii=False))
    check(met["protected_unchanged_ratio"] == 1.0, "protected area unchanged")
    check(met["editable_mean_abs_diff"] > met["protected_mean_abs_diff"], "editable area changed more")
    technical = R.technical_image_metrics(result, requested_size="200x200")
    check(technical["status"] == "PASS" and technical["size"] == [200, 200], "technical image metrics")
    flat = TMP / "flat.png"
    Image.new("RGB", (20, 20), (50, 50, 50)).save(flat)
    flat_metrics = R.technical_image_metrics(flat, requested_size="20x20")
    check(flat_metrics["status"] == "PASS_WITH_WARNING", "flat result needs review")

    print("\n== zimage CLI local behavior ==")
    cli_root = TMP / "cli-root"
    cli_env = {**os.environ, "ZIMAGE_JOBS_DIR": str(cli_root / "jobs"),
               "ZIMAGE_CACHE_DIR": str(cli_root / "cache")}
    plan_path = TMP / "plan.json"
    plan = subprocess.run([
        PY, str(PKG / "bin" / "zimage.py"), "plan", "--image", str(src),
        "--rect", "300,200,700,600", "--prompt", "change background",
        "--plan-out", str(plan_path), "--job-id", "plan-local-test"],
        cwd=str(ROOT), env=cli_env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(plan.returncode == 0 and plan_path.is_file() and "fingerprint" in plan.stdout and "preflight_ok" in plan.stdout,
          "plan produces local evidence", plan.stderr[:180])
    if plan_path.is_file():
        pd = json.loads(plan_path.read_text(encoding="utf-8"))
        check(pd.get("artifact_type") == "zimage.plan" and pd.get("schema_version") == "zimage-plan-v1",
              "plan artifact schema")
        check(pd.get("source", {}).get("sha256") == R.sha256_file(src), "plan source hash")
        check(pd.get("mask", {}).get("sha256") == R.sha256_file(Path(pd["mask"]["path"])),
              "plan mask persisted")
        raw_plan = plan_path.read_text(encoding="utf-8")
        check("change background" not in raw_plan and "RELAY_API_KEY" not in raw_plan,
              "plan artifact omits prompt and credentials")
        overwrite = subprocess.run([
            PY, str(PKG / "bin" / "zimage.py"), "plan", "--image", str(src),
            "--rect", "300,200,700,600", "--prompt", "changed", "--plan-out", str(plan_path)],
            cwd=str(ROOT), env=cli_env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        check(overwrite.returncode != 0 and "计划已存在" in overwrite.stderr,
              "plan refuses silent overwrite")
    else:
        check(False, "plan artifact exists")
    plan_edit = subprocess.run([
        PY, str(PKG / "bin" / "zimage.py"), "edit", "--plan-file", str(plan_path),
        "--out", str(TMP / "plan-dry.png"), "--dry-run", "--job-id", "plan-edit-local-test"],
        cwd=str(ROOT), env=cli_env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(plan_edit.returncode == 0 and "dry-run" in plan_edit.stdout and not (TMP / "plan-dry.png").exists(),
          "edit reuses plan artifact without sending", plan_edit.stderr[:180])
    conflicting = subprocess.run([
        PY, str(PKG / "bin" / "zimage.py"), "edit", "--plan-file", str(plan_path),
        "--image", str(src), "--out", str(TMP / "conflict.png"), "--dry-run",
        "--job-id", "conflict-job"], cwd=str(ROOT), env=cli_env,
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(conflicting.returncode != 0 and "不能混用" in conflicting.stderr
          and not (cli_root / "jobs" / "conflict-job").exists(),
          "plan refuses mixed input flags")
    duplicate = subprocess.run([
        PY, str(PKG / "bin" / "zimage.py"), "edit", "--plan-file", str(plan_path),
        "--out", str(TMP / "duplicate.png"), "--dry-run",
        "--job-id", "plan-edit-local-test"], cwd=str(ROOT), env=cli_env,
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(duplicate.returncode != 0 and "Job ID 已存在" in duplicate.stderr,
          "duplicate job cannot overwrite prior manifest")
    forced = subprocess.run([
        PY, str(PKG / "bin" / "zimage.py"), "plan", "--image", str(src),
        "--rect", "300,200,700,600", "--prompt", "changed", "--plan-out", str(plan_path), "--force"],
        cwd=str(ROOT), env=cli_env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(forced.returncode == 0 and plan_path.is_file(), "plan force overwrite", forced.stderr[:180])
    forced_data = json.loads(plan_path.read_text(encoding="utf-8"))
    prompt_path = Path(forced_data["prompt_path"])
    original_prompt = prompt_path.read_bytes()
    prompt_path.write_bytes(original_prompt + b"changed")
    stale_prompt = subprocess.run([
        PY, str(PKG / "bin" / "zimage.py"), "edit", "--plan-file", str(plan_path),
        "--out", str(TMP / "stale-prompt.png"), "--dry-run", "--job-id", "stale-prompt-job"],
        cwd=str(ROOT), env=cli_env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(stale_prompt.returncode != 0 and "计划失效：提示词已变化" in stale_prompt.stderr
          and not (cli_root / "jobs" / "stale-prompt-job").exists(),
          "changed prompt rejects before job creation")
    prompt_path.write_bytes(original_prompt)
    plan_mask_path = Path(forced_data["mask"]["path"])
    original_mask = plan_mask_path.read_bytes()
    plan_mask_path.write_bytes(original_mask + b"changed")
    stale_mask = subprocess.run([
        PY, str(PKG / "bin" / "zimage.py"), "edit", "--plan-file", str(plan_path),
        "--out", str(TMP / "stale-mask.png"), "--dry-run", "--job-id", "stale-mask-job"],
        cwd=str(ROOT), env=cli_env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(stale_mask.returncode != 0 and "计划失效：遮罩已变化" in stale_mask.stderr
          and not (cli_root / "jobs" / "stale-mask-job").exists(),
          "changed mask rejects before job creation")
    plan_mask_path.write_bytes(original_mask)
    source_copy = TMP / "source-copy.png"
    shutil.copy2(src, source_copy)
    source_plan = TMP / "source-plan.json"
    copied = subprocess.run([
        PY, str(PKG / "bin" / "zimage.py"), "plan", "--image", str(source_copy),
        "--whole", "--prompt", "preserve subject", "--plan-out", str(source_plan)],
        cwd=str(ROOT), env=cli_env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(copied.returncode == 0 and source_plan.is_file(), "source-copy plan created", copied.stderr[:180])
    with Image.open(source_copy) as source_image:
        source_image.load()
        source_image.convert("RGB").crop((0, 0, source_image.width, source_image.height)).save(source_copy)
    stale_source = subprocess.run([
        PY, str(PKG / "bin" / "zimage.py"), "edit", "--plan-file", str(source_plan),
        "--out", str(TMP / "stale-source.png"), "--dry-run", "--job-id", "stale-source-job"],
        cwd=str(ROOT), env=cli_env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(stale_source.returncode != 0 and "计划失效：源图内容已变化" in stale_source.stderr
          and not (cli_root / "jobs" / "stale-source-job").exists(),
          "changed source rejects before job creation")
    bad_plan = TMP / "bad-plan.json"
    bad_mask = TMP / "bad-mask.png"
    Image.new("RGBA", (10, 10), (255, 255, 255, 255)).save(bad_mask)
    invalid = subprocess.run([
        PY, str(PKG / "bin" / "zimage.py"), "plan", "--image", str(src),
        "--mask-file", str(bad_mask), "--prompt", "invalid mask", "--plan-out", str(bad_plan)],
        cwd=str(ROOT), env=cli_env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(invalid.returncode != 0 and not bad_plan.exists() and not (TMP / "bad-plan.assets").exists()
          and not list(TMP.glob(".bad-plan.*")), "failed plan leaves no artifact")
    whole_plan = TMP / "whole-plan.json"
    whole = subprocess.run([
        PY, str(PKG / "bin" / "zimage.py"), "plan", "--image", str(src),
        "--whole", "--prompt", "whole", "--plan-out", str(whole_plan)],
        cwd=str(ROOT), env=cli_env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if whole_plan.is_file():
        wd = json.loads(whole_plan.read_text(encoding="utf-8"))
        check(whole.returncode == 0 and wd.get("mask") is None and wd.get("budget_estimate") == "deferred_to_run_round_dry_run",
              "whole plan has null mask and deferred budget")
    else:
        check(False, "whole plan artifact exists")
    dry = subprocess.run([
        PY, str(PKG / "bin" / "zimage.py"), "edit", "--image", str(src),
        "--rect", "300,200,700,600", "--prompt", "change background",
        "--out", str(TMP / "dry.png"), "--dry-run", "--job-id", "local-test-job"],
        cwd=str(ROOT), env=cli_env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(dry.returncode == 0 and "dry-run" in dry.stdout and not (TMP / "dry.png").exists(),
          "dry-run does not send or create final output", dry.stderr[:180])

    cache_mask = TMP / "cache-mask.png"
    cache_mask.write_bytes(mask.read_bytes())
    cache_fp = R.request_fingerprint(
        source=src, mask=cache_mask, prompt="cache hit",
        model="gpt-image-2", size="1024x1536", quality="low", pad="crop",
        mask_invert=False, refs=[], encode="png", jpg_quality=90,
        budget_mib=1.55, endpoint="https://image-direct.geiliapi.com/v1", mask_primary=True)
    cache_root_cli = TMP / "cli-cache"
    R.store_cache(cache_root_cli, cache_fp, src, validation={"status": "PASS"})
    cache_out = TMP / "cache-hit.png"
    cache_job = "cache-hit-local-test"
    cache_env = dict(__import__("os").environ)
    cache_env.pop("RELAY_API_KEY", None)
    cache_env.pop("RELAY_API_KEY_HD", None)
    cache_env.pop("RELAY_BASE_URL", None)
    cache_env.pop("RELAY_MODEL", None)
    hit_run = subprocess.run([
        PY, str(PKG / "bin" / "zimage.py"), "edit", "--image", str(src),
        "--mask-file", str(cache_mask), "--prompt", "cache hit", "--out", str(cache_out),
        "--job-id", cache_job], cwd=str(ROOT), env={**cache_env, "ZIMAGE_CACHE_DIR": str(cache_root_cli),
                                                     "ZIMAGE_JOBS_DIR": str(cli_root / "jobs")},
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(hit_run.returncode == 0 and "缓存命中" in hit_run.stdout and cache_out.is_file(),
          "CLI cache hit skips upstream", hit_run.stderr[:180])
    shutil.rmtree(cli_root / "jobs" / cache_job, ignore_errors=True)
    job_manifest = cli_root / "jobs" / "local-test-job" / "manifest.json"
    if job_manifest.is_file():
        md = json.loads(job_manifest.read_text(encoding="utf-8"))
        check(md.get("state") == "prepared" and md.get("status") == "plan_only",
              "dry-run manifest state", json.dumps(md, ensure_ascii=False)[:180])
        check(md.get("job_id") == "local-test-job", "dry-run job id")
    else:
        check(False, "dry-run manifest exists")
finally:
    import shutil
    shutil.rmtree(TMP, ignore_errors=True)

print(f"\nSUMMARY: {'PASS' if not failures else 'FAIL'} ({len(failures)} failures)")
if failures:
    print("Failures:", failures)
    raise SystemExit(1)
