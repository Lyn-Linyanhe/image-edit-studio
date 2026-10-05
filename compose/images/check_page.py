"""Cross-check the embedded page: every $('id') in the JS must exist in the HTML.

A single missing id makes $('x').addEventListener throw, which aborts the whole
<script> and leaves #drop with no click handler -> "clicking does nothing".
"""
import re
import sys

src = open("mask_edit_app.py", encoding="utf-8").read()
m = re.search(r'PAGE = r"""(.*?)"""', src, re.S)
if not m:
    print("PAGE literal not found")
    sys.exit(1)
page = m.group(1)

ids = set(re.findall(r'id="([A-Za-z0-9_\[\]\-]+)"', page))
print("HTML ids:")
for i in sorted(ids):
    print("   ", i)

sc = re.search(r"<script>(.*?)</script>", page, re.S)
js = sc.group(1) if sc else ""
if not js:
    print("\nNO <script> FOUND")
    sys.exit(1)

refs = sorted(set(re.findall(r"\$\('([A-Za-z0-9_]+)'\)", js)))
print("\nids referenced via $() in JS:")
missing = []
for r in refs:
    ok = r in ids
    if not ok:
        missing.append(r)
    print("   ", r, "" if ok else "   <<<< MISSING IN HTML")

print("\nRESULT:", "all references resolve" if not missing else f"MISSING {missing}")

# also print the order of handler bindings so we can spot early aborts
print("\n--- top-level statement order (rough) ---")
for mm in re.finditer(r"^\$?\('?([A-Za-z0-9_]+)'?\)?\.(onclick|addEventListener|onchange)\s*=", js, re.M):
    pass
for line_no, line in enumerate(js.splitlines(), 1):
    if re.search(r"\.(onclick|onchange)\s*=", line) or "addEventListener" in line:
        print(f"   js line {line_no:4d}: {line.strip()[:88]}")
