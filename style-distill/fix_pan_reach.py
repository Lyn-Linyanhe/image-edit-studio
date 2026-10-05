"""修"放大后拖不到最上/最下"：舞台的 flex 居中在内容溢出时会吃掉滚动范围。

病因（经典 flexbox 陷阱）：`.lb-stage` 用 display:flex + align-items:center + justify-content:center。
当**子元素比容器大**时，居中会让它向上/向左溢出，而滚动容器只能从内容起点开始滚——
于是上方（与左侧）那一段永远滚不到，表现为"拖不到最上面"。

修法：去掉 flex 居中，改用**子元素 margin:auto**——
  · 子元素比容器小 → auto 外边距把它居中（视觉与此前一致）
  · 子元素比容器大 → auto 归零，内容从起点铺开，滚动范围完整，四边都能看到
两侧的翻页按钮是 position:absolute，不参与 flex 布局，不受影响。
"""
from __future__ import annotations

import pathlib
import py_compile
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("compose/images/mask_edit_app.py")
t = P.read_text(encoding="utf-8")

pairs = [
    ("'.lb-stage{flex:1;position:relative;overflow:auto;display:flex;align-items:center;justify-content:center}'",
     "'/* 居中改用子元素 margin:auto：flex 的 align/justify:center 在内容溢出时会吃掉滚动范围，'\n"
     "        '   导致放大后拖不到最上/最下（经典 flexbox 陷阱）。 */'\n"
     "        '.lb-stage{flex:1;position:relative;overflow:auto;display:flex}'"),
    ("'#lb-img{max-width:100%;max-height:100%;object-fit:contain;cursor:zoom-in}'",
     "'#lb-img{max-width:100%;max-height:100%;object-fit:contain;cursor:zoom-in;margin:auto}'"),
]

for old, new in pairs:
    n = t.count(old)
    print(f"  锚点命中 {n} 次：{old.strip().splitlines()[0][:48]}")
    assert n == 1, f"锚点命中 {n} 次 → 停止"
    t = t.replace(old, new)

P.write_text(t, encoding="utf-8")
py_compile.compile(str(P), doraise=True)
print("  已写入并编译通过")
