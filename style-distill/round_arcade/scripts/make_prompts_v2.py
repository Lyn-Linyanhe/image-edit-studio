"""从 v1 派生 v2（加身份锚定）与 v3（v2 + 图2 招牌表情），保证 v1 的块逐字不变。

模块化依据（仓库既有做法，见 build_prompts.py）：只动"人物身份"这一个模块，
其余块逐字继承——这样结果变好/变坏都能归因到这一处（R6）。
每个锚点必须命中 1 次，否则立刻停。
"""
from __future__ import annotations

import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")

D = pathlib.Path("style-distill/round_arcade")
v1 = (D / "prompt_arcade_v1.txt").read_text(encoding="utf-8")

IDENTITY_BLOCK = """【人物身份锚点：逐条照第二张图与第三张图核对（本轮要提高的就是这里的辨识度）】
- **脸型**：鹅蛋脸偏圆，**下颌线条柔和**、下巴**短而略收**（不尖削）、脸颊有一点肉感。
  不要画成通用的萌系圆脸，也不要拉长成锥子脸。
- **睁着的那只眼的形状与颜色**：**杏形、横向偏长**；虹膜是**琥珀金色**，
  **虹膜外圈是一道更深的棕环**；瞳孔是**竖长的深色**；**虹膜上部有一块明亮的浅金高光**。
  上眼睑有一条**较粗的深棕眼线**，睫毛**粗、根根分明、向外翘**；下眼睑另有一条细线。
  **不要**把眼睛画成又大又圆、瞳孔占满的通用动漫眼。
- **闭着的那只眼**（图2、图3 里都是闭着的）：**一条上弯的弧线（^ 形）**，
  弧线**两端略粗、中间细**，弧线下方有一条淡色的下眼睑线。
- **眉**：细、淡棕、**平缓的弧**，眉尾略下垂。
- **鼻**：只用**一小段极简的鼻头暗示**，**不要画鼻梁线**，不要立体鼻影。
- **嘴**：**小**、**嘴角上翘**成微笑，**下唇略厚**、唇线偏深。
- **颊**：睁开的那只眼**下方有 3 到 4 颗极小的深棕色小点**（雀斑点），
  两颊各有一团**淡粉色腮红**；雀斑与小点的**位置与数量照图3**，不要抹掉也不要画多。
- **耳**：露出的那只耳朵轮廓清楚（画面右侧那只）。
- **头发轮廓（辨识度的大头）**：**蓬松、发量很大**；从**头顶偏右的分缝**起，
  额前刘海分成**三到四缕粗弧线**垂在脸前；两侧是**大波浪**，垂到胸下，
  **发梢向内卷**；发色是**暖栗橙棕（比纯橙更红）**，暗部用**深褐的短排线**，
  再加**几处更深的褐色块**做层次。**不要**画成直发、不要减少发量、不要变成金黄色或纯橙色。
- **身份标记必须全部在场且位置正确**：金皇冠（三个尖角、中间五角星镂空）＋**粉色云朵垫**＋
  **刘海上方一粉一蓝两枚长条发夹**＋**画面右侧发间一整朵向日葵**＋**青绿色缎带颈圈与星形坠**。
- 一句话：**"这就是图2、图3 里那个女孩"**——把她的眼睛颜色、睫毛、雀斑、发量与发色画对，
  比把脸画得更漂亮重要。

"""

EXTRA_NEG = """
generic moe face, oversized round eyes, pupils filling the iris, sharp pointed chin, elongated face,
thin straight hair, reduced hair volume, golden blonde hair, flat pure-orange hair,
missing freckles, missing blush, missing eyelashes, eyebrow moved, nose bridge line added,
crown missing, cloud cushion missing, hair clips missing, sunflower missing, choker missing,
expression changed to a wide grin, expression changed to a neutral stare.
"""

pairs = [
    ("【两张图各提供什么，不许越界】", "【三张图各提供什么，不许越界】"),
    ("""- **第二张图**（橙发女孩）提供：**人物身份**（脸型五官、发型发色、头饰、颈饰、服装）与
  **全部渲染手法**（线稿、上色方式、笔触、边缘处理）——**只取手法，不取配色**。""",
     """- **第二张图**（橙发女孩）提供：**人物身份**（脸型五官、发型发色、头饰、颈饰、服装）与
  **全部渲染手法**（线稿、上色方式、笔触、边缘处理）——**只取手法，不取配色**。
- **第三张图**是**同一个女孩的脸部特写（她本人）**：**只用来核对脸型、五官形状、睫毛、雀斑位置、
  发量发色与发型轮廓**。不要从第三张图取姿势、背景、构图或任何新内容。"""),
    ("【渲染手法：完全按第二张图", IDENTITY_BLOCK + "【渲染手法：完全按第二张图"),
]

t = v1
for old, new in pairs:
    n = t.count(old)
    print(f"  锚点命中 {n} 次：{old.strip().splitlines()[0][:52]}")
    assert n == 1, f"锚点命中 {n} 次 → 停止"
    t = t.replace(old, new)

v2 = t + EXTRA_NEG
(D / "prompt_arcade_v2.txt").write_text(v2, encoding="utf-8")
print(f"  写出 v2  {len(v2)} 字（v1 是 {len(v1)} 字）")

# v3 = v2 + 图2 的招牌表情（只改这一处，便于单独判读）
old_expr = "- 表情轻松、专注带一点得意；两条腿**在画面中被圆凳遮住大半**，只露一点点。"
new_expr = ("- **表情照图2、图3**：**画面左侧那只眼闭成上弯的弧线（眨眼）**，"
            "**另一只眼睁开、看向观者**，**嘴角上翘成有点得意的微笑**；"
            "两条腿**在画面中被圆凳遮住大半**，只露一点点。")
n = v2.count(old_expr)
print(f"  表情锚点命中 {n} 次")
assert n == 1, "表情锚点未命中 1 次 → 停止"
v3 = v2.replace(old_expr, new_expr)
(D / "prompt_arcade_v3.txt").write_text(v3, encoding="utf-8")
print(f"  写出 v3  {len(v3)} 字")
