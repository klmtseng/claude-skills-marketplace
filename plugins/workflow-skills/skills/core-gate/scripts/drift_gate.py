#!/usr/bin/env python3
"""core-gate 漂移閘門:偵測「同一份來源被複製到多處」的副本有沒有偏離來源。

抽自 anthropics/financial-services 的 check.py（它驗證 agent-plugins/<slug>/skills/
的 bundled 副本沒偏離 vertical-plugins/ 的來源）。通用化成:任何專案只要有
「單一來源 + 多份 vendored/bundled 副本」(vendored 模組、bundled skill、設定樣板),
就用這道閘門保證副本不會偷偷跟來源分岔。

設定檔 drift.json:
{
  "pairs": [
    {"source": "path/to/source.py", "copies": ["a/vendored.py", "b/vendored.py"]},
    {"source": "skills/x/SKILL.md", "copies": ["agent/x/SKILL.md"], "normalize": "strip"}
  ]
}
normalize(選填):
  none(預設) 逐位元組比對;strip 忽略前後空白;nows 忽略所有空白(容忍換行/縮排差異)。

不一致列出 source vs copy 的 sha 與第一個分歧行,exit 1;全同 exit 0。
`--fix` 把來源覆蓋到所有副本(等同官方 sync-agent-skills.py)。
零依賴,Python >= 3.8。
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

_WS = re.compile(r"\s+")


def _canon(text, mode):
    if mode == "strip":
        return text.strip()
    if mode == "nows":
        return _WS.sub("", text)
    return text  # none


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _first_divergence(a, b):
    la, lb = a.splitlines(), b.splitlines()
    for i, (x, y) in enumerate(zip(la, lb), 1):
        if x != y:
            return i, x[:100], y[:100]
    if len(la) != len(lb):
        n = min(len(la), len(lb)) + 1
        return n, "<EOF>" if len(la) < len(lb) else la[n - 1][:100], \
                  "<EOF>" if len(lb) < len(la) else lb[n - 1][:100]
    return 0, "", ""


def run(config_path, fix):
    cfg = json.loads(Path(config_path).read_text())
    base = Path(config_path).resolve().parent
    drift = 0
    checked = 0
    for pair in cfg["pairs"]:
        src = base / pair["source"]
        mode = pair.get("normalize", "none")
        if not src.exists():
            print(f"[FAIL] source missing: {pair['source']}")
            drift += 1
            continue
        src_raw = src.read_text()
        src_c = _canon(src_raw, mode)
        for cp in pair["copies"]:
            cpp = base / cp
            checked += 1
            if fix:
                cpp.parent.mkdir(parents=True, exist_ok=True)
                cpp.write_text(src_raw)
                print(f"[FIX] {cp} ← {pair['source']}")
                continue
            if not cpp.exists():
                print(f"[FAIL] copy missing: {cp}")
                drift += 1
                continue
            cp_c = _canon(cpp.read_text(), mode)
            if _sha(src_c) != _sha(cp_c):
                drift += 1
                ln, a, b = _first_divergence(src_c, cp_c)
                print(f"[DRIFT] {cp} 偏離來源 {pair['source']} (normalize={mode})")
                if ln:
                    print(f"    第一個分歧在第 {ln} 行:")
                    print(f"      source: {a}")
                    print(f"      copy  : {b}")
    if fix:
        print(f"[FIX] 已同步 {checked} 份副本")
        return 0
    status = "PASS" if drift == 0 else "FAIL"
    print(f"[{status}] drift gate: {checked} 份副本檢查,{drift} 份偏離")
    return 1 if drift else 0


def main():
    ap = argparse.ArgumentParser(description="core-gate 漂移閘門")
    ap.add_argument("--config", default="drift.json")
    ap.add_argument("--fix", action="store_true", help="用來源覆蓋所有副本(sync)")
    args = ap.parse_args()
    sys.exit(run(args.config, args.fix))


if __name__ == "__main__":
    main()
