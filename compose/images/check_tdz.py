"""Static TDZ check for the embedded page.

`const`/`let` live in a temporal dead zone: calling a function that reads one
BEFORE its declaration line throws
    ReferenceError: Cannot access 'X' before initialization
and that aborts the entire <script>, leaving every button unbound.

This walks the extracted JS and, for every top-level `const X = ...` / `let X`,
reports any line ABOVE the declaration that references X (directly or through a
call to a top-level function that references X at its own top level).
"""
import re
import sys
from collections import defaultdict

JS = "_page_extracted.js"
src = open(JS, encoding="utf-8").read()
lines = src.splitlines()


def strip_strings(s):
    """Remove string/template/regex-ish content so we don't match inside text."""
    s = re.sub(r"`[^`]*`", "``", s)
    s = re.sub(r"'[^'\n]*'", "''", s)
    s = re.sub(r'"[^"\n]*"', '""', s)
    return s


def strip_comments(s):
    """Blank out // and /* */ comments so prose mentioning a name is not a hit."""
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    out = []
    for ln in s.split("\n"):
        # keep code before a trailing //, ignore it if the line is a comment
        idx = ln.find("//")
        if idx == 0:
            out.append("")
        elif idx > 0:
            out.append(ln[:idx])
        else:
            out.append(ln)
    return "\n".join(out)


CODE = strip_comments(src)
clines = CODE.splitlines()


def is_property_only(line: str, name: str) -> bool:
    """True when no occurrence of `name` is a BARE identifier.

    Two shapes are not variable references and must be ignored:
      * object-literal keys     `key: 'sk-...'`
      * member access           `d.key` / `engine.key`
    Without this, engine-profile lines are wrongly reported as uses of the const
    named `key`."""
    occ = [m.start() for m in re.finditer(r"\b" + re.escape(name) + r"\b", line)]
    if not occ:
        return False
    for pos in occ:
        after = line[pos + len(name):].lstrip()
        before = line[:pos].rstrip()
        if before.endswith("."):            # member access, not a variable
            continue
        if after.startswith(":") and not before.endswith(("const", "let")):
            continue                        # object-literal key
        return False                        # a genuine bare reference
    return True


# ---- collect top-level const/let declarations (approx: no leading indent) ----
decls = {}          # name -> line index (0-based)
for i, ln in enumerate(clines):
    if ln.startswith((" ", "\t")):
        continue
    m = re.match(r"(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=", ln)
    if m:
        decls.setdefault(m.group(1), i)
    for m2 in re.finditer(r",\s*([A-Za-z_$][\w$]*)\s*=", ln):
        if re.match(r"(?:const|let)\s", ln):
            decls.setdefault(m2.group(1), i)

# ---- collect top-level function declarations and the consts they touch ----
funcs = {}          # name -> (start, end, set(consts referenced))
for i, ln in enumerate(clines):
    m = re.match(r"function\s+([A-Za-z_$][\w$]*)\s*\(", ln)
    if not m:
        continue
    name = m.group(1)
    depth = 0
    started = False
    body = []
    j = i
    while j < len(clines):
        body.append(clines[j])
        depth += clines[j].count("{") - clines[j].count("}")
        if "{" in clines[j]:
            started = True
        if started and depth <= 0:
            break
        j += 1
    text = strip_strings("\n".join(body))
    refs = set(re.findall(r"\b([A-Za-z_$][\w$]*)\b", text))
    funcs[name] = (i, j, refs)

func_headers = {f[0] for f in funcs.values()}

# ---- for each const, find references above its declaration line ----
problems = []
for name, dline in sorted(decls.items(), key=lambda kv: kv[1]):
    pat = re.compile(r"\b" + re.escape(name) + r"\b")
    for i in range(dline):
        if i in func_headers:
            continue
        code_line = strip_strings(clines[i])
        if not pat.search(code_line):
            continue
        if is_property_only(code_line, name):
            continue
        via = [fn for fn, (fs, fe, refs) in funcs.items()
               if name in refs and fe < dline
               and re.search(r"\b" + re.escape(fn) + r"\s*\(", code_line)]
        kind = "direct" if not via else "via call to " + ", ".join(sorted(set(via)))
        problems.append((name, dline + 1, i + 1, kind, clines[i].strip()[:78]))

print(f"top-level const/let declarations : {len(decls)}")
print(f"top-level functions              : {len(funcs)}")
print()
if not problems:
    print("NO TDZ RISK FOUND")
else:
    seen = set()
    print("POTENTIAL 'used before initialization' issues:")
    for name, dline, uline, kind, text in problems:
        key = (name, uline)
        if key in seen:
            continue
        seen.add(key)
        print(f"  const {name:16s} declared line {dline:4d}")
        print(f"        referenced line {uline:4d} ({kind})")
        print(f"        {text}")
print()
sys.exit(1 if problems else 0)
