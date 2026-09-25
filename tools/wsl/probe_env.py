#!/usr/bin/env python3
"""WSL 通道环境探针：只回显布尔值与路径，**绝不回显凭据值**。

调用方式（经 wslrun.sh，环境已按通道规则设置好）：
    wslrun.sh -- python3 tools/wsl/probe_env.py          # 给人看（JSON）
    wslrun.sh -- python3 tools/wsl/probe_env.py --plain  # 给 doctor.sh 解析（key=value）

为什么不是重新实现一遍读凭据的逻辑：本探针 import 的正是流水线自己用的
`compose/images/mask_edit_app.py` 的 `env_cred()`，测的是**真实代码路径**，
而不是"我以为它会怎么读"。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

WS = Path("/mnt/c/Users/typ/Desktop/mantu")
COMPOSE = WS / "compose" / "images"

out: dict[str, object] = {
    "home": os.environ.get("HOME"),
    "workspace_exists": WS.exists(),
    "skill_audit_exists": (Path.home() / ".agents" / "skills" / "style-distill"
                           / "scripts" / "audit_and_check.py").exists(),
    "dsh_attachments_exists": (Path.home() / ".dsh" / "attachments").exists(),
    "session_dir_exists": (Path.home() / ".dsh" / "sessions"
                           / "--C-Users-typ-Desktop-mantu--").exists(),
}

try:
    sys.path.insert(0, str(COMPOSE))
    import mask_edit_app as app  # noqa: E402

    out["import_ok"] = True
    out["relay_key"] = bool(app.env_cred("RELAY_API_KEY"))
    out["relay_key_hd"] = bool(app.env_cred("RELAY_API_KEY_HD"))
    out["relay_base_url"] = app.env_cred("RELAY_BASE_URL") or ""
except Exception as e:  # noqa: BLE001
    out["import_ok"] = False
    out["import_error"] = f"{type(e).__name__}: {e}"


def as_text(v: object) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


if "--plain" in sys.argv[1:]:
    for k, v in out.items():
        print(f"{k}={as_text(v)}")
else:
    print(json.dumps({k: as_text(v) for k, v in out.items()}, ensure_ascii=False, indent=2))
