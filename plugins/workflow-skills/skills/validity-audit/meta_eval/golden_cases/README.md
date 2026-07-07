# golden_cases — 標竿回收率案例(自行累積)

每個案例是一個 JSON:對某個「已知有 N 條真問題」的產出跑 VA,量測回收率。
欄位:`case_id`、`target`(受審對象)、`domain_packs`、`context`、`usage`、
`expected_findings[]`(每條含 id/tier/checklist/severity/描述)。
規則:審計者不得先看 expected_findings;recall = hits / N。
本分享版不含原作者的私人案例——用你自己專案的「人工評審已找到問題」的產出建第一個標竿。
跑法見 `../injected_bug_recall.py`。
