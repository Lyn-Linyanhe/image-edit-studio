"""文档收窄到只讲 GPT 通道：删掉 grok 小节与两处 grok 举例，并在开头声明范围。

依据（用户口径）："只需要 gpt 的接入即可，grok 不用"。
grok 在文档里原出现 4 处：第 4 节一个完整小节 + 第 5 节两处举例（t2i/i2i 不同名、edits_b64 不可达 url）。
保留的"体积实测"与"尺寸不严格"等结论与引擎无关，继续保留。
"""
from __future__ import annotations

import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("dsh-plugins/dsh-image-edit/README.md")
t = P.read_text(encoding="utf-8")

GROK_SECTION = """### grok（`grok-imagine` / `grok-imagine-edit`）
- 文生图**只有带 `response_format="b64_json"` 才可用**：默认回的是 `imgen.x.ai` 上的 url，
  而本网络解析到 `162.125.1.8` 后连接超时 → 图永远下不回来。
- **图生图不可用**：`/images/edits` 会忽略 `response_format`，于是永远回那个不可达的 url。
- `grok-imagine-edit` **不接受超过一张参考图**（HTTP 400）。
- 它按规范**不要发 OpenAI 的 `quality`**，改用 `resolution`（1k/2k）驱动输出尺寸。

"""

pairs = [
    (GROK_SECTION, ""),
    ("| `t2i_model` / `i2i_model` | 文生图 / 图生图各用哪个模型名 | 有的上游两者不同名（如 `grok-imagine` vs `grok-imagine-edit`） |",
     "| `t2i_model` / `i2i_model` | 文生图 / 图生图各用哪个模型名 | 两者可以不同名（本预设里是同一个 `gpt-image-2`） |"),
    ("| `edits_b64` | `/images/edits` 是否回内联 base64 | 为 false 时必须能下载它回的 url；**若那个 url 在你网络里不可达，图生图就等于不可用**（grok 正是这种） |",
     "| `edits_b64` | `/images/edits` 是否回内联 base64 | 本预设为 **true**（直接拿 base64，最省事）；若某上游为 false，则必须能下载它回的 url，否则图生图不可用 |"),
    # 开头声明范围
    ("> **用途：私下交流用**——给同行看这个「改图」挂件是怎么做的、实测到什么、踩过哪些坑。\n"
     "> 不是对外发布物（无 LICENSE、未发布 npm）。",
     "> **用途：私下交流用**——给同行看这个「改图」挂件是怎么做的、实测到什么、踩过哪些坑。\n"
     "> 不是对外发布物（无 LICENSE、未发布 npm）。\n"
     "> **范围：只讲 GPT 通道（`gpt-image-2`）**；代码里另有的一条备用通道已弃用，不在本文范围。"),
]

for old, new in pairs:
    n = t.count(old)
    print(f"  锚点命中 {n} 次：{old.strip().splitlines()[0][:44]}")
    assert n == 1, f"锚点命中 {n} 次 → 停止"
    t = t.replace(old, new)

P.write_text(t, encoding="utf-8")
left = t.lower().count("grok")
print(f"  已写入；文档中剩余 'grok' 提及 {left} 处（应为 1，即开头那句范围声明）")
