#!/usr/bin/env python3
"""core-gate 確定性閘門:同一條 headless 指令跑 N 次,輸出必須逐位元一致。

用法:
    python3 determinism_gate.py --runs 3 -- python3 sim.py --seed 7 --headless
    python3 determinism_gate.py --extract "CHECKSUM=(\\w+)" -- python3 sim.py --seed 7

- 預設比對完整 stdout 的 SHA-256。
- --extract REGEX 只比對匹配行(例如每 tick 的 checksum 行),忽略其他輸出
  (計時、進度條等本來就允許不確定的雜訊)。
- 不一致時印出第一個分歧行,exit 1;一致 PASS exit 0。
- --seeds 7,8,9 逐 seed 各跑 N 次(指令中的 {seed} 佔位符會被代換),
  順便驗證「不同 seed 產生不同結果」(防 seed 根本沒接上的假確定性)。
零依賴,Python >= 3.8。
"""

import argparse
import hashlib
import re
import subprocess
import sys


def run_once(cmd, timeout):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        print(f"[FAIL] 指令本身失敗 (exit {r.returncode}): {' '.join(cmd)}")
        sys.stderr.write(r.stderr[-2000:])
        sys.exit(2)
    return r.stdout


def digest(text, extract_re):
    if extract_re:
        lines = [m.group(0) for m in extract_re.finditer(text)]
        material = "\n".join(lines)
        if not lines:
            print("[FAIL] --extract 沒匹配到任何行——閘門空轉不算通過")
            sys.exit(2)
    else:
        material = text
    return hashlib.sha256(material.encode()).hexdigest(), material


def first_divergence(a, b):
    la, lb = a.splitlines(), b.splitlines()
    for i, (x, y) in enumerate(zip(la, lb), 1):
        if x != y:
            return i, x, y
    return min(len(la), len(lb)) + 1, "<EOF>", "<EOF>"


def check_seed(cmd_template, seed, runs, extract_re, timeout):
    cmd = [arg.replace("{seed}", str(seed)) if seed is not None else arg
           for arg in cmd_template]
    digests, materials = [], []
    for i in range(runs):
        out = run_once(cmd, timeout)
        d, m = digest(out, extract_re)
        digests.append(d)
        materials.append(m)
    if len(set(digests)) == 1:
        label = f"seed={seed} " if seed is not None else ""
        print(f"[PASS] {label}runs={runs} digest={digests[0][:16]}…")
        return digests[0]
    print(f"[FAIL] seed={seed}: {runs} 次執行出現 {len(set(digests))} 種輸出")
    i, x, y = first_divergence(materials[0], materials[1])
    print(f"  第一個分歧在第 {i} 行:")
    print(f"    run1: {x[:150]}")
    print(f"    run2: {y[:150]}")
    return None


def main():
    ap = argparse.ArgumentParser(description="core-gate 確定性閘門",
                                 usage="determinism_gate.py [options] -- CMD ...")
    ap.add_argument("--runs", type=int, default=2, help="每個 seed 重跑次數(預設 2)")
    ap.add_argument("--extract", help="只比對匹配此 regex 的內容(如 checksum 行)")
    ap.add_argument("--seeds", help="逗號分隔 seed 清單,指令用 {seed} 佔位")
    ap.add_argument("--timeout", type=int, default=600, help="單次執行秒數上限")
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="-- 之後接 headless 指令")
    args = ap.parse_args()

    cmd = args.cmd[1:] if args.cmd and args.cmd[0] == "--" else args.cmd
    if not cmd:
        ap.error("要在 -- 之後給 headless 指令")
    extract_re = re.compile(args.extract, re.MULTILINE) if args.extract else None

    if args.seeds:
        seeds = [s.strip() for s in args.seeds.split(",") if s.strip()]
        if not any("{seed}" in a for a in cmd):
            ap.error("--seeds 模式下指令要含 {seed} 佔位符")
        per_seed = {}
        for s in seeds:
            d = check_seed(cmd, s, args.runs, extract_re, args.timeout)
            if d is None:
                sys.exit(1)
            per_seed[s] = d
        if len(seeds) > 1 and len(set(per_seed.values())) == 1:
            print("[FAIL] 所有 seed 輸出完全相同——seed 很可能根本沒接上(假確定性)")
            sys.exit(1)
        print(f"[PASS] {len(seeds)} 個 seed 全部確定性,且互不相同")
    else:
        if check_seed(cmd, None, args.runs, extract_re, args.timeout) is None:
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
