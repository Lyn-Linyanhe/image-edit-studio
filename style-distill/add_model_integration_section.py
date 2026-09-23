"""给文档补一节「接入你自己的模型 / 中转站」，并把后续章节序号顺延。

事实来源（都已在代码里核对）：
  · 认证：req.add_header("Authorization", f"Bearer {api_key}")           L440 / L2554
  · 端点：{base}/models（测试与列表）、/images/generations（文生图）、/images/edits（图生图，multipart）
  · 引擎预设字段：ENGINES 字典（label/base/key/t2i_model/i2i_model/uses_quality/
    uses_resolution/edits_b64/multi_image/mask/sizes），在请求构造处被逐项使用
  · key 存放：页面 localStorage，并带"记住/清除"开关
"""
from __future__ import annotations

import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("dsh-plugins/dsh-image-edit/README.md")
t = P.read_text(encoding="utf-8")

NEW_SECTION = """## 5. 接入你自己的模型 / 中转站

### 上游需要满足什么
- OpenAI 兼容的两个端点：文生图 `POST {base}/images/generations`、
  图生图 `POST {base}/images/edits`（multipart）。**图生图是遮罩玩法的基础**——
  上游若没有 `/images/edits`，改图功能就只剩文生图。
- 认证：`Authorization: Bearer <api_key>`（本工具就是这样发的）。
- 可选：`GET {base}/models`，用于"测试"与"获取模型列表"。

### 在页面上填三样就能用
1. **Base URL**：到 `/v1` 为止（例如 `https://…/v1`）。
2. **API Key**：`Bearer` 后面那串。它**只存在浏览器本地**（localStorage，带注入/清除开关），
   插件包与配置文件里**没有任何密钥**。
3. **模型名**：可直接填；旁边有「获取模型列表」与「测试」两个按钮（小眼睛可切明文显示）。

「测试」打的是 `{base}/models` 并回报可用模型数——这是最快的连通性验证。

### 要新增一个"引擎"预设：只改一处
引擎是本地服务里的预设字典（`mask_edit_app.py` 顶部的 `ENGINES`）。字段决定了**这个上游能干什么、
该发哪些参数**：

| 字段 | 含义 | 影响 |
|---|---|---|
| `label` | 下拉里显示的名字 | — |
| `base` / `key` | 默认 Base URL 与 key | 留空则要求页面上手填 |
| `t2i_model` / `i2i_model` | 文生图 / 图生图各用哪个模型名 | 有的上游两者不同名（如 `grok-imagine` vs `grok-imagine-edit`） |
| `uses_quality` | 是否发 OpenAI 的 `quality` | 与 `uses_resolution` **二选一**，发错会被上游拒 |
| `uses_resolution` | 是否发 `resolution`（1k/2k） | 有些上游用它而不是 quality 驱动输出尺寸 |
| `edits_b64` | `/images/edits` 是否回内联 base64 | 为 false 时必须能下载它回的 url；**若那个 url 在你网络里不可达，图生图就等于不可用**（grok 正是这种） |
| `multi_image` | 是否接受多张参考图 | 为 false 时多于一张会 HTTP 400 |
| `mask` | 是否支持"红标遮罩"玩法 | 为 false 时只能整图重画 |
| `sizes` | 各档位可选尺寸 | 填上游**真实接受**的尺寸组合 |

新增做法：复制一段，改 `label` / `base` / 两个模型名 / 那几个布尔开关 / `sizes`，
然后重启本地服务即可（`/stop` → `/ensure`，**不用重启 DSH**）。

### 接入时的实测注意（本项目踩过的）
- **体积上限**：约 **1.96 MiB 被接受、2.12 MiB 起被拒**（`400 form field too large or incomplete`）；
  投喂体积由**目标尺寸**决定、与源图分辨率无关；**改用 JPEG 投喂可比 PNG 小约 5 倍**。
- **尺寸不严格**：请求 `1024x1536` 实际回过 `1029x1528`；`1024x1024` 回过 `1254x1254`。
  别在其上做像素级精确假设。
- **`502 Upstream access forbidden` 是瞬时上游故障**（不是你的请求有问题），**重试**即可。
- **b64 与 url 两条返回路径的差别**：b64 直接可用；url 要求你的网络连得上那个域名
  （有的中转站结果域名还会在多个网关间轮换）。
- 有些上游**只暴露一个模型**，所以"获取模型列表"只显示一条是正常的，不是 bug。

"""

anchor = "## 5. 安装"
assert t.count(anchor) == 1, "安装节锚点不是 1 处"
t = t.replace(anchor, NEW_SECTION + "## 6. 安装")

# 后续章节顺延（从后往前替换，避免交叉命中）
renumber = [
    ("## 11. 文件清单", "## 12. 文件清单"),
    ("## 10. 附：本项目另外加的「图片」按钮（非通用）", "## 11. 附：本项目另外加的「图片」按钮（非通用）"),
    ("## 9. 转给别人时注意两点", "## 10. 转给别人时注意两点"),
    ("## 8. 已知限制", "## 9. 已知限制"),
    ("## 7. 测试（离线可跑）", "## 8. 测试（离线可跑）"),
    ("## 6. 契约：写这类挂件必须知道的事", "## 7. 契约：写这类挂件必须知道的事"),
]
for old, new in renumber:
    n = t.count(old)
    print(f"  顺延锚点命中 {n} 次：{old[:34]}")
    assert n == 1, f"锚点 {old} 命中 {n} 次 → 停止"
    t = t.replace(old, new)

# 交叉引用里的节号跟着改
xref = [
    ("对方要按第 5 节改成自己的", "对方要按第 6 节改成自己的"),
    ("这三项默认值是作者机器上的", "这三项默认值是作者机器上的（第 6 节）"),
]
for old, new in xref:
    if t.count(old) == 1:
        t = t.replace(old, new)
        print(f"  交叉引用已改：{old[:24]}")

P.write_text(t, encoding="utf-8")
print("  已写入")
