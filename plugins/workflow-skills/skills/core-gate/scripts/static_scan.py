#!/usr/bin/env python3
"""core-gate 靜態純度掃描:把「確定性核心不准碰非確定性來源」寫成機器檢查。

用法:
    python3 static_scan.py --config gates.json
    python3 static_scan.py --paths src/core src/sim --profile deterministic-core

設定檔 gates.json 範例:
{
  "layers": [
    {
      "name": "core",
      "paths": ["src/core", "src/sim"],
      "profile": "deterministic-core",
      "banned": [
        {"pattern": "\\\\brequests\\\\.", "reason": "core 不准打網路"}
      ]
    }
  ]
}

- profile 提供該層的預設禁令,banned 追加自訂禁令,兩者合併生效。
- 行尾註解 `gate-allow: 理由` 可豁免單行(理由必填,空理由不豁免)。
- 違規以 file:line 列出,exit code 1;全綠 exit 0。
零依賴,Python >= 3.8。
"""

import argparse
import json
import re
import sys
from pathlib import Path

SCAN_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs"}

# 各 profile 的預設禁令。pattern 是對「單行」的 regex。
PROFILES = {
    # 確定性核心:不准有掛鐘時間、全域亂數、環境熵、DOM、網路
    "deterministic-core": [
        # Python 非確定性來源
        (r"\brandom\.(?!Random\b)\w+\s*\(", "全域 random 呼叫(要用注入的 random.Random(seed) 實例)"),
        (r"\bnp\.random\.(?!Generator\b|default_rng\b)\w+\s*\(", "np.random 全域狀態(要用 default_rng(seed) 注入)"),
        (r"\btime\.(time|time_ns|monotonic|perf_counter)\s*\(", "掛鐘時間(核心只能用 tick 計數)"),
        (r"\bdatetime\.(now|today|utcnow)\s*\(", "掛鐘時間(核心只能用 tick 計數)"),
        (r"\bos\.urandom\s*\(", "環境熵"),
        (r"\buuid\.uuid", "uuid(用 entity id 產生器)"),
        (r"^\s*(import|from)\s+(requests|urllib|socket|http\b|aiohttp)", "核心不准打網路"),
        # JS/TS 非確定性來源
        (r"\bMath\.random\s*\(", "全域亂數(要用 seeded PRNG)"),
        (r"\bDate\.now\s*\(|\bnew\s+Date\s*\(", "掛鐘時間(核心只能用 tick 計數)"),
        (r"\bperformance\.now\s*\(", "掛鐘時間"),
        (r"\bcrypto\.(getRandomValues|randomUUID)\b", "環境熵"),
        # DOM / 渲染洩漏進核心
        (r"\b(document|window|navigator|localStorage)\s*\.", "核心不准碰 DOM/瀏覽器全域"),
        (r"\brequestAnimationFrame\s*\(", "渲染迴圈不准進核心"),
        (r"^\s*(import|from).*['\"](three|pygame|pixi\.js)['\"]?", "渲染引擎不准進核心"),
    ],
    # 內容資料層:只准資料,不准邏輯亂數/時間(比 core 鬆,禁令是子集)
    "data-layer": [
        (r"\brandom\.(?!Random\b)\w+\s*\(", "資料層不准有全域亂數"),
        (r"\bMath\.random\s*\(", "資料層不准有全域亂數"),
        (r"\btime\.(time|time_ns)\s*\(", "資料層不准有掛鐘時間"),
        (r"\bDate\.now\s*\(", "資料層不准有掛鐘時間"),
    ],
}

ALLOW_RE = re.compile(r"gate-allow\s*:\s*(\S.*)$")


def scan_file(path: Path, rules):
    violations = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as e:
        return [(path, 0, f"讀檔失敗: {e}", "")]
    for i, line in enumerate(lines, 1):
        allow = ALLOW_RE.search(line)
        for pattern, reason in rules:
            if pattern.search(line):
                if allow:
                    continue  # 有附理由的豁免
                violations.append((path, i, reason, line.strip()[:120]))
    return violations


def collect_files(paths):
    for p in paths:
        root = Path(p)
        if root.is_file() and root.suffix in SCAN_EXTENSIONS:
            yield root
        elif root.is_dir():
            for f in sorted(root.rglob("*")):
                if f.suffix in SCAN_EXTENSIONS and f.is_file():
                    if any(part in ("node_modules", ".git", "__pycache__", "dist", "build") for part in f.parts):
                        continue
                    yield f


def build_rules(profile_name, extra_banned):
    rules = []
    if profile_name:
        if profile_name not in PROFILES:
            sys.exit(f"未知 profile: {profile_name}(可用: {', '.join(PROFILES)})")
        rules += [(re.compile(p), r) for p, r in PROFILES[profile_name]]
    for item in extra_banned or []:
        rules.append((re.compile(item["pattern"]), item.get("reason", item["pattern"])))
    return rules


def run_layer(name, paths, rules):
    violations = []
    n_files = 0
    for f in collect_files(paths):
        n_files += 1
        violations += scan_file(f, rules)
    return n_files, violations


def main():
    ap = argparse.ArgumentParser(description="core-gate 靜態純度掃描")
    ap.add_argument("--config", help="gates.json 設定檔")
    ap.add_argument("--paths", nargs="*", help="不用設定檔時,直接指定要掃的路徑")
    ap.add_argument("--profile", default="deterministic-core", help="--paths 模式用的 profile")
    args = ap.parse_args()

    layers = []
    if args.config:
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
        for layer in cfg["layers"]:
            layers.append((layer["name"], layer["paths"],
                           build_rules(layer.get("profile"), layer.get("banned"))))
    elif args.paths:
        layers.append(("cli", args.paths, build_rules(args.profile, None)))
    else:
        ap.error("要嘛給 --config,要嘛給 --paths")

    total_violations = 0
    for name, paths, rules in layers:
        n_files, violations = run_layer(name, paths, rules)
        status = "PASS" if not violations else "FAIL"
        print(f"[{status}] layer={name} files={n_files} violations={len(violations)}")
        for path, lineno, reason, snippet in violations:
            print(f"  {path}:{lineno}  {reason}")
            print(f"      {snippet}")
        total_violations += len(violations)

    sys.exit(1 if total_violations else 0)


if __name__ == "__main__":
    main()
