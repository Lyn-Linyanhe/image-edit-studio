"""加"输入"页签：只装**用户自己上传的图**（按 sha256 与会话记录配对，不靠命名约定）。

索引文件：style-distill/round_lib/user_inputs.json（由 build_user_inputs_index.py 生成）
  · paths：工作区里属于用户上传的文件（13 个）
  · attachments：只在附件库里、没复制进工作区的上传（9 张）——画廊直接服务它们
分类优先级：草稿/测试残留 → **输入** → 参考 → 局部 → 对照 → 成果/候选 → 过程
"""
from __future__ import annotations

import pathlib
import py_compile
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("compose/images/mask_edit_app.py")
t = P.read_text(encoding="utf-8")

pairs = [
    # 1) 分类表加"输入"
    ('CATEGORIES = (("all", "全部"), ("deliver", "成果"), ("candidate", "候选"), ("reference", "参考"),\n'
     '              ("detail", "局部"), ("compare", "对照"), ("process", "过程"))\n'
     'CAT_LABEL = {"deliver": "成果", "candidate": "候选", "reference": "参考", "detail": "局部",\n'
     '             "compare": "对照", "process": "过程"}',
     'CATEGORIES = (("all", "全部"), ("deliver", "成果"), ("candidate", "候选"), ("input", "输入"),\n'
     '              ("reference", "参考"), ("detail", "局部"), ("compare", "对照"), ("process", "过程"))\n'
     'CAT_LABEL = {"deliver": "成果", "candidate": "候选", "input": "输入", "reference": "参考",\n'
     '             "detail": "局部", "compare": "对照", "process": "过程"}'),
    # 2) 索引读取
    ("_ACCEPTED_CACHE: dict[str, set] = {}",
     'ATTACHMENTS_DIR = os.path.join(os.path.expanduser("~"), ".dsh", "attachments")\n'
     'USER_INPUT_INDEX = os.path.join(GALLERY_REL_BASE, "style-distill", "round_lib", "user_inputs.json")\n'
     '_USER_INPUTS: dict = {}\n'
     '\n'
     '\n'
     'def user_inputs() -> dict:\n'
     '    """读"用户上传图"索引：{paths: set(工作区内相对路径, 小写), attachments: [ {id,name,…} ]}。\n'
     '\n'
     '    索引由 style-distill/build_user_inputs_index.py 生成：它从会话日志取 role=user 的图片附件，\n'
     '    再与工作区图片做 sha256 配对——所以这是**证据**，不是命名约定。\n'
     '    """\n'
     '    import json\n'
     '\n'
     '    if _USER_INPUTS:\n'
     '        return _USER_INPUTS\n'
     '    paths, atts = set(), []\n'
     '    try:\n'
     '        with open(USER_INPUT_INDEX, encoding="utf-8") as f:\n'
     '            d = json.load(f)\n'
     '        paths = {str(x).lower() for x in (d.get("paths") or [])}\n'
     '        atts = list(d.get("attachments") or [])\n'
     '    except (OSError, ValueError):\n'
     '        pass\n'
     '    _USER_INPUTS["paths"] = paths\n'
     '    _USER_INPUTS["atts"] = atts\n'
     '    return _USER_INPUTS\n'
     '\n'
     '\n'
     '_ACCEPTED_CACHE: dict[str, set] = {}'),
    # 3) 分类分支（插在草稿判定之后、参考之前）
    ('    # ---- 参考图：参考目录、名字明示、input 里的 B/D 约定',
     '    # ---- 输入：用户自己上传的图（按 sha256 与会话记录配对）\n'
     '    if rel.replace("\\\\", "/").lower() in user_inputs()["paths"]:\n'
     '        return "input"\n'
     '\n'
     '    # ---- 参考图：参考目录、名字明示、input 里的 B/D 约定'),
    # 4) 把"仅在附件库"的上传也塞进列表
    ('def gallery_select():\n'
     '    """成果与局部全取；过程只取最新 GALLERY_PROCESS_CAP 张。"""\n'
     '    rows = _gallery_scan()\n'
     '    kept, process_seen = [], 0',
     'def gallery_select():\n'
     '    """成果与局部全取；过程只取最新 GALLERY_PROCESS_CAP 张。\n'
     '\n'
     '    另外把"只存在附件库、未复制进工作区"的用户上传也作为条目列出来\n'
     '    （full = "att:<sha256>"，由 /gallery/img 直接从附件库服务）。\n'
     '    """\n'
     '    rows = _gallery_scan()\n'
     '    kept, process_seen = [], 0'),
    # 5) 追加附件库条目（放在 return 之前）
    ('    counts = {key: 0 for key, _ in CATEGORIES}\n'
     '    counts["all"] = len(kept)',
     '    for a in user_inputs()["atts"]:\n'
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
     '    counts = {key: 0 for key, _ in CATEGORIES}\n'
     '    counts["all"] = len(kept)'),
    # 6) 图片路由支持 att:
    ('        p = os.path.abspath(wanted or "")\n'
     '        allowed = False',
     '        if (wanted or "").startswith("att:"):\n'
     '            oid = wanted[4:]\n'
     '            meta = next((a for a in user_inputs()["atts"] if str(a.get("id")) == oid), None)\n'
     '            if meta is None:\n'
     '                return self._send(404, b"not found", "text/plain; charset=utf-8")\n'
     '            p = os.path.join(ATTACHMENTS_DIR, "v1", "objects", oid[:2], oid[2:])\n'
     '            if not os.path.isfile(p):\n'
     '                return self._send(404, b"not found", "text/plain; charset=utf-8")\n'
     '            ctype = meta.get("mediaType") or "image/png"\n'
     '            try:\n'
     '                with open(p, "rb") as f:\n'
     '                    return self._send(200, f.read(), ctype)\n'
     '            except OSError as e:\n'
     '                return self._send(500, str(e).encode("utf-8"), "text/plain; charset=utf-8")\n'
     '\n'
     '        p = os.path.abspath(wanted or "")\n'
     '        allowed = False'),
    # 7) 新分类配色
    ('.c-reference{color:#c9b6ff;border-color:#443a63}',
     '.c-reference{color:#c9b6ff;border-color:#443a63}'
     '.c-input{color:#ffd6a5;border-color:#5d4626}'),
]

for old, new in pairs:
    n = t.count(old)
    print(f"  锚点命中 {n} 次：{old.strip().splitlines()[0][:52]}")
    assert n == 1, f"锚点命中 {n} 次 → 停止"
    t = t.replace(old, new)

P.write_text(t, encoding="utf-8")
py_compile.compile(str(P), doraise=True)
print("  已写入并编译通过")
