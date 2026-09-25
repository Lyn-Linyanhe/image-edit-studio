# -*- coding: utf-8 -*-
"""zimage reliability 第一批本地测试：不访问上游。"""
from __future__ import annotations
import json
import subprocess
import sys
import tempfile
from pathlib import Path

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

    print("\n== protection metrics ==")
    from PIL import Image, ImageDraw
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

    print("\n== zimage CLI local behavior ==")
    plan = subprocess.run([
        PY, str(PKG / "bin" / "zimage.py"), "plan", "--image", str(src),
        "--rect", "300,200,700,600", "--prompt", "change background"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(plan.returncode == 0 and "fingerprint" in plan.stdout and "preflight_ok" in plan.stdout,
          "plan produces local evidence", plan.stderr[:180])
    dry = subprocess.run([
        PY, str(PKG / "bin" / "zimage.py"), "edit", "--image", str(src),
        "--rect", "300,200,700,600", "--prompt", "change background",
        "--out", str(TMP / "dry.png"), "--dry-run", "--job-id", "local-test-job"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(dry.returncode == 0 and "dry-run" in dry.stdout and not (TMP / "dry.png").exists(),
          "dry-run does not send or create final output", dry.stderr[:180])
    job_manifest = ROOT / ".zimage" / "jobs" / "local-test-job" / "manifest.json"
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
