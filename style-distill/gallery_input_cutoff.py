"""画廊侧适配新索引（带切点）：
  · user_inputs() 读 paths（计入的上传）+ excluded/unreachable 计数（供页头如实标注）
  · 去掉"附件库合成行"的追加逻辑（那些上传已按切点排除）
  · _input_note() 改为说明"按你的要求只计入最近一次上传，更早的 N 张不计入"
"""
from __future__ import annotations

import pathlib
import py_compile
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("compose/images/mask_edit_app.py")
t = P.read_text(encoding="utf-8")

pairs = [
    # 1) user_inputs()：字段换成 paths + 计数
    ('    paths, atts = set(), []\n'
     '    try:\n'
     '        with open(USER_INPUT_INDEX, encoding="utf-8") as f:\n'
     '            d = json.load(f)\n'
     '        paths = {str(x).lower() for x in (d.get("paths") or [])}\n'
     '        atts = list(d.get("attachments") or [])\n'
     '    except (OSError, ValueError):\n'
     '        pass\n'
     '    _USER_INPUTS["paths"] = paths\n'
     '    _USER_INPUTS["atts"] = atts\n'
     '    return _USER_INPUTS',
     '    paths, excluded, unreachable = set(), 0, 0\n'
     '    try:\n'
     '        with open(USER_INPUT_INDEX, encoding="utf-8") as f:\n'
     '            d = json.load(f)\n'
     '        paths = {str(x).lower() for x in (d.get("paths") or [])}\n'
     '        excluded = len(d.get("excluded") or [])\n'
     '        unreachable = len(d.get("unreachable") or [])\n'
     '    except (OSError, ValueError):\n'
     '        pass\n'
     '    _USER_INPUTS["paths"] = paths\n'
     '    _USER_INPUTS["excluded"] = excluded\n'
     '    _USER_INPUTS["unreachable"] = unreachable\n'
     '    return _USER_INPUTS'),
    # 2) 去掉附件库合成行
    ('    for a in user_inputs()["atts"]:\n'
     '        oid = str(a.get("id") or "")\n'
     '        if not oid:\n'
     '            continue\n'
     '        p = os.path.join(ATTACHMENTS_DIR, "v1", "objects", oid[:2], oid[2:])\n'
     '        try:\n'
     '            st = os.stat(p)\n'
     '        except OSError:\n'
     '            continue\n'
     '        kept.append({"mtime": st.st_mtime, "size": st.st_size,\n'
     '                     "full": "att:" + oid, "cat": "input",\n'
     '                     "rel": "你的上传（未进仓库）/" + str(a.get("name") or oid[:12])})\n'
     '\n'
     '    counts = {key: 0 for key, _ in CATEGORIES}',
     '    # 注意：按切点排除掉的上传**不再**合成行——它们要么是"之前的"，要么无法在画廊定位。\n'
     '    counts = {key: 0 for key, _ in CATEGORIES}'),
    # 3) 页头说明改口径
    ('    try:\n'
     '        n = len(user_inputs()["atts"])\n'
     '    except Exception:                                            # noqa: BLE001\n'
     '        n = 0\n'
     '    return f" · 另有 {n} 张你上传的图未复制进仓库（只在附件库里，无法在此定位）" if n else ""',
     '    ui = user_inputs()\n'
     '    n_ex, n_un = int(ui.get("excluded") or 0), int(ui.get("unreachable") or 0)\n'
     '    if not n_ex:\n'
     '        return ""\n'
     '    return (f" · 「输入」只计入最近一次上传（{len(ui.get(\'paths\') or [])} 张）；"\n'
     '            f"更早的 {n_ex} 张按你的要求不计入（其中 {n_un} 张只在附件库、无法在此定位）")'),
]

for old, new in pairs:
    n = t.count(old)
    print(f"  锚点命中 {n} 次：{old.strip().splitlines()[0][:52]}")
    assert n == 1, f"锚点命中 {n} 次 → 停止"
    t = t.replace(old, new)

P.write_text(t, encoding="utf-8")
py_compile.compile(str(P), doraise=True)
print("  已写入并编译通过")
