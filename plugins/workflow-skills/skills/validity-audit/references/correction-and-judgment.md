# 第 3 段:回應與更正(誠實)+ 判讀原則

## 回應與更正流程
1. **重現閘門(硬規則):** reviewer 的發現**必須先用可跑的唯讀檢查/數值重現**才算數;沒重現的只是假設,不是發現。
   ——這擋住 reviewer 幻覺(建造者盲點的對稱孿生),也是建造者↔reviewer 分歧時的裁判(真相 = 程式執行,非權威)。
2. **修正確認的 bug**,**只 OOS 重跑** headline。
3. **撤回是預設**:OOS 某段失敗或 CI 與基準重疊時,直接撤回/降級(paper/README/JOURNEY 都改),保留「沒撐過」紀錄。
4. 不可修的(如倖存者)→ 明列為硬限制 + caveat。
5. reviewer 報告存 `audit/independent_review.md`,內部審計存 `results/leak_audit.md`(或 `audit/leak_audit.md`)。
6. **閉環(共演化 P2,不可省):** 把本次每一筆失手/撤回/差點漏掉的,用
   `python3 <skill>/ledger.py append '<json>'` 寫回 `audit_ledger.jsonl`(欄位含可重用的 **detector**)。
   即使全過,也記「跑了哪些歷史挑戰、hit/miss/誤報」。不閉環,評估器就不演化,共演化層等於沒有。詳見 `references/coevolution.md`。

## 判讀原則
- **所有偏誤若都指向同一個(灌水)方向 → 高度可疑**。
- **headline 數字若同時被多項擊中 → 不可信,寧可撤回**。
- 區分:橫斷面/分類結論通常較穩;**報酬/組合績效最易被算術 + 倖存者灌水**。
- 「指標看起來好 ≠ 兌現到底線」;「monitor 的 change ≠ death」。

## ⚠️ 不在範圍(過關 ≠ 已驗證)
本協定主要抓**洩漏 + 報酬/組合指標的灌水算術**。過關只代表「primed reviewer 沒找到灌水算術 bug」,**不代表研究為真**。
不檢查:regime/結構斷裂、特徵工程的 data-snooping、用宇宙/日期區間 p-hacking、交易成本/容量/流動性樂觀、
**標籤定義本身的 lookahead**、非平穩使測試窗失效。本協定自身也經過 meta-audit(見公開 repo 的 META_AUDIT.md)。
