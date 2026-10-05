"""Dump the settings-side SlotMap and owner-prop interfaces so the registrant
component contract is exact."""
import re
from pathlib import Path

ROOT = Path(_os.environ.get("DSH_NPM_CACHE_DIR", ""))

for pkg in ["dsh-client-ui-settings", "dsh-client-ui-sidebar", "dsh-client-ui-slots"]:
    d = ROOT / pkg / "lib" / "types"
    if not d.exists():
        print(f"[{pkg}] no types dir at {d}")
        continue
    for f in sorted(d.rglob("*.d.ts")):
        txt = f.read_text(encoding="utf-8", errors="replace")
        if "SlotMap" not in txt:
            continue
        print(f"\n========== {pkg}/{f.relative_to(d)} ==========")
        m = re.search(r"(?:declare module[^\n]*\n)?\s*interface SlotMap\s*\{(.*?)\n\s{0,8}\}", txt, re.S)
        if m:
            print("--- SlotMap ---")
            print(m.group(1).strip()[:1800])
        for im in re.finditer(r"interface (Settings\w*OwnerProps|Sidebar\w*OwnerProps)\s*\{(.*?)\n\s*\}", txt, re.S):
            print(f"--- {im.group(1)} ---")
            print(im.group(2).strip()[:900])
