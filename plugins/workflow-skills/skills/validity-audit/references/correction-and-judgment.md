# 第 3 段:回應與更正(誠實)+ 判讀原則

## 回應與更正流程
1. **重現閘門(硬規則):** reviewer 的發現**必須先用可跑的唯讀檢查/數值重現**才算數;沒重現的只是假設,不是發現。
   ——這擋住 reviewer 幻覺(建造者盲點的對稱孿生),也是建造者↔reviewer 分歧時的裁判(真相 = 程式執行,非權威)。
2. **修正確認的 bug**,重跑 headline 指標確認數字是否變動。
3. **撤回是預設**:headline 宣稱撐不住或 CI 與基準重疊時,直接撤回/降級(paper/README/JOURNEY 都改),保留「沒撐過」紀錄。
4. 不可修的限制(如依賴特定硬體、樣本數不足)→ 明列為硬限制 + caveat。
5. reviewer 報告存 `audit/independent_review.md`,內部審計存 `audit/mechanical_audit.md`。
6. **閉環(共演化 P2,不可省):** 把本次每一筆失手/撤回/差點漏掉的,用
   `python3 <skill>/ledger.py append '<json>'` 寫回 `audit_ledger.jsonl`(欄位含可重用的 **detector**)。
   即使全過,也記「跑了哪些歷史挑戰、hit/miss/誤報」。不閉環,評估器就不演化,共演化層等於沒有。詳見 `references/coevolution.md`。

## 判讀原則
- **所有偏誤若都指向同一個(灌水)方向 → 高度可疑**。
- **headline 數字若同時被多項擊中 → 不可信,寧可撤回**。
- 區分:正確性宣稱通常較穩;**效能/benchmark 宣稱最易被環境污染和算術 bug 灌水**。
- 「指標看起來好 ≠ 兌現到底線」;「monitor 的 change ≠ death」。

## ⚠️ 不在範圍(過關 ≠ 已驗證)
本協定主要抓**測試集污染 + 指標算術 bug + benchmark 環境污染**。過關只代表「primed reviewer 沒找到清單內的問題」,**不代表產出為真**。
不檢查:架構選擇本身是否最優、特徵工程的 data-snooping(超出機械檢查範圍)、
容量/延遲的生產規模估計、UX 品質、**標籤定義本身的 bias**。本協定自身也經過 meta-audit(見公開 repo 的 META_AUDIT.md)。
