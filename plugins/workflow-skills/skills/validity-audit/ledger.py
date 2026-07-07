#!/usr/bin/env python3
"""validity-audit 的累積式 miss-ledger(RQGM P2 anchor-from-ledger 的輕量版)。

紅皇后想法:靜態評估器會被 Goodhart。把每次 audit 的失手(miss/撤回/誤報)持久化,
下次 audit 時把歷史失手『類別 + 偵測器』當成【強制挑戰】回收出來——清單就從靜態變累進,
會隨時間變強(複利)。純標準庫、append-only、本機。

用法:
  python3 ledger.py challenges          # 列出所有歷史失手的強制挑戰(給建造者端機械審計)
  python3 ledger.py append '<json>'     # 追加一筆新失手(結案時做)
  python3 ledger.py stats               # 類別分布 / 誰抓到的統計

★ 邏輯抹除(P3):`challenges` 的輸出只餵【建造者端】的機械審計。冷審 reviewer **不得**看到
  ledger 原文(否則變 pattern-match 背答案),要維持冷、自己重推威脅模型。熱審才可給類別。
"""
import json, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "audit_ledger.jsonl")


def load():
    if not os.path.exists(LEDGER):
        return []
    with open(LEDGER, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def challenges():
    rows = load()
    if not rows:
        print("(ledger 空;尚無歷史失手)")
        return
    # 依類別去重,保留最高嚴重度的偵測器當代表(P2:從 ledger 建 anchor)
    by_cat = {}
    order = {"high": 3, "med": 2, "low": 1}
    for r in rows:
        c = r["category"]
        if c not in by_cat or order.get(r.get("severity", "low"), 0) > order.get(by_cat[c].get("severity", "low"), 0):
            by_cat[c] = r
    print("=" * 88)
    print(f"歷史失手回收 → 本次 audit 的【強制挑戰】(共 {len(by_cat)} 類,來自 {len(rows)} 筆)")
    print("每一類都要明確回答:本研究會不會犯同一個?怎麼驗證它沒犯?")
    print("=" * 88)
    for i, (cat, r) in enumerate(sorted(by_cat.items(), key=lambda kv: -order.get(kv[1].get("severity", "low"), 0)), 1):
        print(f"\n[{i}] {cat}  ({r.get('severity','?')}, 首見於 {r.get('project','?')})")
        print(f"    偵測器:{r['detector']}")
    print("\n" + "=" * 88)


def append(js):
    try:
        rec = json.loads(js)
    except json.JSONDecodeError as e:
        sys.exit(f"JSON 解析失敗:{e}")
    need = {"id", "category", "detector", "caught_by", "severity"}
    missing = need - rec.keys()
    if missing:
        sys.exit(f"缺欄位:{missing}(至少要 id/category/detector/caught_by/severity)")
    with open(LEDGER, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"已追加:{rec['id']}  [{rec['category']}]")


def stats():
    rows = load()
    print(f"總失手筆數:{len(rows)}")
    print("類別分布:", dict(Counter(r["category"] for r in rows)))
    print("誰抓到  :", dict(Counter(r.get("caught_by", "?") for r in rows)))
    print("嚴重度  :", dict(Counter(r.get("severity", "?") for r in rows)))
    internal = sum(1 for r in rows if r.get("caught_by", "").startswith("internal"))
    reviewer = sum(1 for r in rows if r.get("caught_by") == "reviewer")
    print(f"→ 自審抓到 {internal}、獨立 reviewer 抓到 {reviewer}"
          + ("(reviewer 抓到自審漏的越多,越證明第 2 段不可省)" if reviewer else ""))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "challenges"
    if cmd == "challenges":
        challenges()
    elif cmd == "append":
        if len(sys.argv) < 3:
            sys.exit("用法:python3 ledger.py append '<json>'")
        append(sys.argv[2])
    elif cmd == "stats":
        stats()
    else:
        sys.exit(f"未知指令 {cmd};可用:challenges / append / stats")
