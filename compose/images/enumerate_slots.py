"""Enumerate the client slot map declared across @deepseek-ai packages."""
import re
from pathlib import Path

ROOT = Path(_os.environ.get("DSH_NPM_CACHE_DIR", ""))

slots = {}
for f in ROOT.rglob("*.d.ts"):
    try:
        txt = f.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    m = re.search(r"interface SlotMap\s*\{(.*?)\n\s*\}", txt, re.S)
    if not m:
        continue
    body = m.group(1)
    for sm in re.finditer(r"'([\w.\-]+)'\s*:", body):
        slots.setdefault(sm.group(1), set()).add(f.parts[-4] if len(f.parts) > 4 else str(f))
    for sm in re.finditer(r'"([\w.\-]+)"\s*:', body):
        slots.setdefault(sm.group(1), set()).add(f.parts[-4] if len(f.parts) > 4 else str(f))

print(f"slot ids declared in SlotMap interfaces: {len(slots)}\n")
for name in sorted(slots):
    src = ", ".join(sorted(slots[name])[:2])
    print(f"  {name:44s}  [{src}]")

# also collect slot names actually used with slots.inject / register
used = {}
for f in ROOT.rglob("*.js"):
    try:
        txt = f.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    for m in re.finditer(r'slots\.inject\(\s*"([\w.\-]+)"', txt):
        used.setdefault(m.group(1), 0)
        used[m.group(1)] += 1
    for m in re.finditer(r"slots\.inject\(\s*'([\w.\-]+)'", txt):
        used.setdefault(m.group(1), 0)
        used[m.group(1)] += 1

print(f"\nslot ids actually injected at runtime: {len(used)}\n")
for name, n in sorted(used.items()):
    print(f"  {name:44s}  x{n}")
