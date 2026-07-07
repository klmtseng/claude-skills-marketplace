---
name: code-recon
description: 分析陌生 codebase 的成本階梯(cheapest-first, verified-always)。回答「這專案怎麼組織/誰呼叫X/改X會壞什麼」時,按便宜→貴的順序選工具,貴工具的輸出用更便宜的確定性工具交叉審計,漏報就示警。觸發詞:分析這個 repo、看懂這個專案、誰呼叫、影響範圍、blast radius、impact、架構總覽、程式碼考古、trace、caller。
---

# code-recon — 陌生 codebase 分析的成本階梯

核心原則兩條(2026-07 實測於 requests/yfinance/大型私有 repo):

1. **Cheapest-first**:每個問題用能答對的最便宜工具。預設 agent 行為(把檔案一個個
   讀進 context)是最貴的一階(~43,000 tok/題),grep 一擊只要 ~185 tok——差 200 倍。
2. **Verified-always**:圖工具/索引工具會**安靜丟檔**(實測 GitNexus 1.6.3 在
   requests 丟掉 models/sessions/utils.py,50% 符號的 impact 答案必然不完整)。
   凡是不透明工具的結構性回答,用下一階更便宜的確定性工具抽驗;對不上就降階重answer。

## 階梯(按序走,能答就停)

| 階 | 問題型態 | 工具 | 實測成本 | 審計方式 |
|---|---|---|---|---|
| 0 定向 | 這專案長怎樣? | `ls`/`tree -L 2`/`wc -l`/`git log --oneline -10`/讀 README 前 50 行 | 數十 tok | 無需 |
| 1 精準問 | 誰呼叫 X?X 定義在哪?哪些檔含 Y? | `grep -rnE '\bX\s*\(' --include=*.py`(caller 要排除 `def X`/`class X` 行);`grep -rn 'def X'`;glob | ~185 tok | grep 本身就是地板 |
| 2 結構問 | 傳遞性影響?架構分群?語義搜尋? | 圖工具(codebase-memory-mcp `trace_path`/`get_architecture`;GitNexus `impact`/`context`) | ~800-1800 tok | **必審**:直接 caller 用階1 grep 重算,圖工具少報=索引缺檔,標註「不完整」再用 union |
| 3 讀段落 | 這段邏輯做什麼? | Read 指定行段(來自階1/2 的 檔案:行號),不讀全檔 | ~數百-2k tok | 無需 |
| 4 讀全檔 | 上面都答不了 | Read 整檔(最後手段,>4 檔改派 subagent) | ~43k tok/題 | 無需 |

## 階 2 的審計規則(重點,別跳過)

圖工具回答「誰呼叫 X / 改 X 影響什麼」後:
1. 跑 `grep -rnE '\bX\s*\(' <repo>` 排除定義行,得直接-caller 檔案集 G。
2. 圖工具報的檔案集為 T。若 `G - T ≠ ∅` → **圖索引缺檔**:
   - 完整答案用 `G ∪ T`;
   - 對同一 repo 的**後續所有**圖工具回答,結構性結論都要再用 grep 重驗一次
     (它的傳遞性結果也缺同樣的邊,不能只驗這一題);
   - 回報裡明說「圖工具漏報了哪些檔」。
3. 現成輔助工具:`impact_audited.py X --path <repo>
   --graph '<圖工具指令,{sym}佔位>'`(exit 2=有漏報;不帶 --graph 就是純 grep 地板)。

## 升降階判準

- 階 1 grep 兩次都撈不到重點(動態調用/字串拼名/太多同名)→ 升階 2。
- 階 2 圖工具審計失敗且缺口大 → 降回階 1+3 手工組答案,別再信該索引。
- 同名符號多定義:先 `grep -rn 'def X\|class X'` 列全部,指明檔案再問圖工具。
- 要讀 ≥4 檔或多輪搜尋 → 照 CLAUDE.md 紀律 1 派 subagent,把本 skill 的階梯寫進交辦 prompt。

## 誠實限制

- grep 地板只保「直接 caller、同 repo、靜態呼叫」;跨服務 HTTP 呼叫、反射/動態調用、
  re-export 別名不在保證內——這些正是圖工具的價值,所以是「審計它」不是「取代它」。
- 語義/概念查詢(「處理重試邏輯在哪」)沒有 grep ground truth,無法審計,直接階 2+3。
- 成本數字是 2026-07 在中型 Python repo 的實測,量級對、精確值會漂。
