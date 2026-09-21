"""工作区收敛：把中间产物分流，让"哪张是交付件"一目了然。

原则：
  · **交付件留在原位、路径不变**——我在对话里给过你确切的交付路径，移动会让那些路径失效；
  · 中间稿 / 对照图 / 提示词 / 脚本分流到子目录（这些我从未承诺过路径）；
  · 每个 round 目录生成 README.md，**内容由真实文件清单生成**（不手写、不会与事实不符）；
  · `产图产图目录 是你自己建的取件目录（已哈希验证是本轮结果的原样副本），**不动它**，只在 README 里说明。

用法：python consolidate.py [--apply]
"""
from __future__ import annotations

import sys
from pathlib import Path

RM = Path("style-distill/round_manga")
RS = Path("style-distill/round_snow")

# 交付件：留在顶层不动（路径不变）
DELIVER_RM = {
    "out_C3.png": "黑白漫画定稿（你当时评价「这张图的效果非常可以」）",
    "out_color1.png": "上色版（黑白稿 + 图1 配色，蓝色荷叶边/粉色挂件都在）",
    "out_v12B.png": "线稿减淡的基准原图（你说「其他都不用动」的那张）",
    "out_v12B_lineLighter_s1.png": "**线稿减淡 · 轻档（你明确认可的就是这张）**",
    "out_v12B_lineLighter_s2.png": "线稿减淡 · 中档（备选，更淡）",
    "out_v12C.png": "「淡然」调子基准（tone_report 的 --ref 用它）",
    "out_final_4k_2880.png": "上者的本地放大 4K（2880×2880，内容一像素不差）",
    "out_v16_uncompressed.png": "2K 横 · 投喂未压缩（脸最像的一版，2048×1152）",
    "out_2kL_2048x1152.png": "2K 横 · 接口生成（身份参考 900px 清晰）",
    "out_4kL_3840x2160.png": "4K 横 · 接口生成（3840×2160，跳出框架）",
}
DELIVER_RS = {
    "out_A1_1k.png": "**雪景少女 · 彩色漫画稿（单幅，保留配色）**",
    "out_B1_1536x1024.png": "**雪景少女 · 三视图＋外框＋跳出框架（彩色）**",
}


def classify_rm(name: str) -> str | None:
    """返回目标子目录名，None 表示留在顶层。"""
    if name in DELIVER_RM or name == 'README.md':
        return None
    # prompt_*.txt 留在顶层：我在对话里给过用它们的完整命令，移走会让那些命令失效；
    # 它们体积很小（合计约 250 KB），且是每一轮的"配方"。
    if name.startswith("prompt_"):
        return None
    if name == "build_prompts.py":
        return "scripts"
    if name.endswith(".py"):
        return "scripts"
    if name.endswith((".md", ".json")) and name not in ("RUN.md",):
        return "reports"
    if name.endswith(".png"):
        # 对照图 / 检查图 → checks；其余生成结果 → work
        if name.startswith("_") or name.endswith(("_check.png", "_vs_ref.png", "_vs_ref2.png",
                                                   "_compare.png", "color_preview.png",
                                                   "face_proportion_compare.png",
                                                   "prep_check.png", "v3_views_vs_ref.png",
                                                   "quant8_check.png", "top_panel_grid.png",
                                                   "ref_three_views.png", "locate_object.png")):
            return "checks"
        return "work"
    return None


def main() -> int:
    apply = "--apply" in sys.argv
    plan: dict[str, list[str]] = {}
    for p in sorted(RM.iterdir()):
        if not p.is_file():
            continue
        dest = classify_rm(p.name)
        if dest:
            plan.setdefault(dest, []).append(p.name)

    print("=== 干跑：round_manga 的分流计划 ===")
    print(f"  留在顶层（交付件）: {len([p for p in RM.iterdir() if p.is_file() and classify_rm(p.name) is None])} 个")
    for d, names in sorted(plan.items()):
        print(f"  → {d}/ : {len(names)} 个  ({', '.join(names[:4])}{' …' if len(names) > 4 else ''})")
    print(f"\n  round_snow 顶层：{len([p for p in RS.iterdir() if p.is_file()])} 个文件（已经是干净状态，只补 README）")

    if not apply:
        print("\n  这是干跑（未写入）。加 --apply 执行。")
        return 0

    # 执行移动
    for d, names in plan.items():
        target = RM / d
        target.mkdir(exist_ok=True)
        for n in names:
            src = RM / n
            if src.exists():
                src.rename(target / n)

    # 生成 README（内容取自真实清单）
    def readme(folder: Path, delivers: dict[str, str], title: str) -> str:
        top = sorted(p.name for p in folder.iterdir() if p.is_file())
        lines = [f"# {title}", "",
                 "## 交付件（留在本目录，路径保持不变）", ""]
        for n, desc in delivers.items():
            f = folder / n
            flag = "✓" if f.exists() else "✗ 缺失"
            size = f"{f.stat().st_size/1048576:.2f} MB" if f.exists() else "-"
            lines.append(f"- `{n}` — {desc}  `{flag}  {size}`")
        lines += ["", "## 其余内容的位置", ""]
        subs = sorted(p.name for p in folder.iterdir() if p.is_dir())
        desc_sub = {"work": "中间生成结果（逐轮迭代版本）", "checks": "对照图 / 掩膜预览 / 坐标网格等检查用图",
                    "prompts": "该轮用过的提示词（按版本号，可复现）", "scripts": "该轮用到的脚本",
                    "reports": "指标表与原始数据", "input": "输入图（不可改动）",
                    "ref_xiami": "你提供的夏弥参考图（R1 啦啦队 / R2 游乐园 / R3 生日，含灰度裁切）"}
        for s in subs:
            n = len([p for p in (folder / s).iterdir() if p.is_file()])
            lines.append(f"- `{s}/` — {desc_sub.get(s, '')}，{n} 个文件")
        lines += ["", "## 顶层还有什么", "",
                  "```", *top, "```", "",
                  "## 复现与工具", "",
                  "- 一键跑一轮：`python style-distill/round_lib/run_round.py --help`",
                  "- 开工前预算报表：加 `--dry-run`（只报表不发送）",
                  "- 确定性操作（减淡线稿/放大/裁切/拼版/调子）：`python style-distill/round_lib/local_ops.py --help`",
                  "- 补下结果：`python style-distill/round_lib/fetch_url.py --pending`", ""]
        return "\n".join(lines)

    (RM / "README.md").write_text(readme(RM, DELIVER_RM, "round_manga · 夏弥三视图 / 线稿减淡"), encoding="utf-8")
    (RS / "README.md").write_text(readme(RS, DELIVER_RS, "round_snow · 雪景少女（彩色漫画稿 / 三视图）"), encoding="utf-8")
    print("\n  已移动文件并写出两份 README.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
