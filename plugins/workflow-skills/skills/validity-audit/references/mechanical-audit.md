# 領域包:量化研究(第 1 段機械審計,寫成 `audit/leak_audit.md`)

## 量化預設假設(除非另有指定)

- **虛無 = label-shuffle 打亂後的實測值,不是 1/n**(類別不平衡時虛無 > 1/n)。
- **headline 必須有純 OOS(lockbox)分段**;不接受 train+OOS 混合的單一數字。
- 報酬:先確認 **log vs simple**,別混用(log→`expm1(Σlog)`;simple→`prod(1+r)-1`)。
- CI:`ddof=1`;n 小用 t 非 z;多 seed 共用同一報酬路徑是**偽複製**,要 block-bootstrap。
- **建造者↔reviewer 分歧時,真相 = 程式執行結果,非權威。**
- 純橫斷面/分類結論通常較穩,可輕量跑;報酬/組合績效最易被灌水,必須全套。

對每一項:說明檢查什麼、怎麼驗、紅旗是什麼。可參考/移植本 skill 附帶的模板:
- `leak_audit_template.py`(通用起點,涵蓋 6 檢:feature audit / rolling-window grep / purged CV / **label-shuffle 虛無** / train-test 比 / val-test 一致)
- DSR/PBO 多重檢定過擬合檢查見 `leak_audit_template.py` 末段

## A. 洩漏 / Lookahead
1. **label-shuffle 虛無**:打亂標籤重訓→分數應掉到「經驗虛無」(注意類別不平衡→虛無 > 1/n,用打亂後的實測值當虛無,不是 1/n)。真標籤需**顯著高於打亂虛無**才算真訊號。
2. **特徵 point-in-time**:所有特徵/正規化只能用 `≤ as-of` 的資料。grep `StandardScaler().fit(`、`.mean()`、`corrcoef`、`LedoitWolf`、`shift(-`、全樣本 fit;確認都在訓練段或 trailing 窗。
3. **purge / embargo**:train 與 OOS 之間要有 ≥ 特徵窗長度的緩衝;檢查相鄰視窗會不會滲漏。

## B. 資料 / 宇宙偏誤
4. **倖存者偏誤**:看每檔 last-date;若 0% 已下市 → 只交易贏家 → **組合績效高估**。免費資料(yfinance)無法修,**必須 caveat**。
5. **point-in-time 宇宙與標籤**:宇宙成員是否用「全歷史」篩(預知誰活下來)?sector/country 標籤是否取自「現在」用到過去?

## C. ★ 算術 / 協定 bug(內部審計最常漏 —— 重點查)
6. **報酬複利**:報酬是 **log 還是 simple**?期報酬正確算法:log→`expm1(Σlog)`;simple→`prod(1+r)-1`。**混用會系統性灌水**(對高波動標的偏負→灌水 minvar)。
7. **指標公式**:MDD 要除「**當時** running peak」非全域高點;annualization 因子;Sharpe 的 ddof。
8. **in-sample 混入**:回測期是否含模型「訓練期」?**headline 必須有純 OOS(lockbox)分段**,不能用 train+OOS 混合的單一數字。
9. **自由重組/對齊**:換手/漂移計算有無「免費再平衡」、forward 窗對齊錯位、雙重計數。

## D. 統計效力
10. **CI 正確性**:n 小要用 t 非 z;`np.std` 用 ddof=1;別把「seed 敏感度」當「抽樣不確定性」(**偽複製**:多 seed 共用同一條報酬路徑 → 應對**報酬序列做 block-bootstrap**)。
11. **多重檢定**:試過幾種方法/設定?對最終「贏家」跑 **DSR(deflated Sharpe)+ PBO**,n_trials = 試過的策略數。

## E. 回測現實
12. **交易成本 / 換手**:gross 不算數;報 net@合理 bps;高換手策略尤其要看 net。
