#!/usr/bin/env python3
"""CPU 基准：两侧跑同一段代码（注意解释器版本不同，会在报告里标注）。"""
from __future__ import annotations

import time

best = None
for _ in range(3):
    t = time.perf_counter()
    n = 0
    for i in range(3_000_000):
        n += (i * i) % 7
    d = time.perf_counter() - t
    best = d if best is None or d < best else best

print(f"{best:.3f}")
