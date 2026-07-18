# golden_cases — 標竿回收率案例

每個案例是一個 JSON:對某個「已知有 N 條真問題」的產出跑 VA,量測回收率。
欄位:`case_id`、`target`(受審對象)、`domain_packs`、`context`、`usage`、
`expected_findings[]`(每條含 id/tier/checklist/severity/描述)。
規則:審計者不得先看 expected_findings;recall = hits / N。

跑法見 `../injected_bug_recall.py`。

## 現有案例

| 案例 | 領域包 | 題庫大小 | v2 cold recall |
|---|---|---|---|
| `study-forge-2026-07` | content+systems+fitness | 6 | **5/6** + 3 bonus findings (2 confirmed gate bugs) |
| `rules-docs-2026-07` | docs | 5 | 5/5; P1 = upgrade-threshold conflict in always-loaded layer |

**`study-forge-2026-07`**: T1+T2 全部通過的語言學習教材,T3 適用性審多抓出 2 條建議。
Bonus findings(冷審額外找到):gate 接受空字串、gate 漏跨項目標記——兩項均重現並修正。

**`rules-docs-2026-07`**: 多檔 AI agent 規則集文件域首測。R1(P1)= 常載層升級門檻與 dispatch 文件互斥,
影響範圍最高(每次 agent 委派都在跑這條規則)。24/25 路徑抽驗存在;長度上限基線全過。

## 加入你自己的案例

用你的專案中「人工/強模型評審已找到 N 條確認問題」的產出建第一個標竿:

```json
{
  "case_id": "your-project-YYYY-MM",
  "target": "brief description of what was audited",
  "domain_packs": ["content"],
  "context": "how the ground-truth findings were established",
  "usage": "run VA; compare against expected_findings; recall = hits/N",
  "expected_findings": [
    {"id": "P1", "tier": "T1", "checklist": "C1", "severity": "high",
     "finding": "...", "reproduce": "..."}
  ],
  "grading_notes": "..."
}
```
