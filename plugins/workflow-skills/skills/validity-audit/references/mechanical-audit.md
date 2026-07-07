# 領域包:軟體工程(第 1 段機械審計,寫成 `audit/mechanical_audit.md`)

## 預設假設(除非另有指定)

- **headline 必須有對應的測試/benchmark 實際跑過**;不接受「看起來應該對」或只有靜態分析。
- 評估指標:先確認 **分母是什麼**,別讓測試集混入訓練集、benchmark 套件混入生產碼。
- CI:`ddof=1`;n 小用 t 非 z;多次重跑同一 binary 共用硬體快取是**偽獨立**,要在乾淨環境重取樣。
- **建造者↔reviewer 分歧時,真相 = 實際執行結果,非權威。**
- 純正確性宣稱通常較穩,可輕量跑;效能/benchmark 宣稱最易被環境污染,必須全套。

對每一項:說明檢查什麼、怎麼驗、紅旗是什麼。可參考/移植本 skill 附帶的模板:
- `mechanical_audit_template.py`(通用起點,涵蓋 5 檢:覆蓋率/benchmark 重疊/恆真斷言/數值指標/環境依賴)

## A. 覆蓋 / 測試集污染

1. **測試覆蓋率灌水**:coverage 報告包含的是 production 碼還是把測試碼本身算進去?
   grep `omit=` / `.coveragerc` / `--source` 確認範圍。紅旗:覆蓋率忽然跳高但功能沒增。
2. **訓練-測試重疊**:ML 模型的 val/test split 是否在 fit 之前就決定?
   grep `fit(X,` 確認在 split 之後;確認 scaler/tokenizer/PCA 沒 fit 在全集上再 transform test。
3. **purge / embargo**:若資料有時間性,time-based split 前後有無緩衝?相鄰窗會不會滲漏。

## B. Benchmark / 指標選擇偏誤

4. **Benchmark 選擇偏誤**:最終報出的 benchmark 是事後從多個裡挑的嗎?
   紅旗:只報一個指標,但程式碼裡跑了十種——最終選的比平均好很多 → 必須 caveat 或 Bonferroni 修正。
5. **Benchmark 環境污染**:「比 baseline 快 X%」的硬體/OS/JIT 版本固定嗎?
   紅旗:測試在 CI 跑過一次不同機器就數字不同;「快 X%」沒寫測試環境。
6. **倖存者/cherry-pick 案例**:定性展示的例子是隨機選的還是挑最好看的?
   紅旗:qualitative 展示和定量指標描述的不是同一個分佈。

## C. ★ 算術 / 協定 bug(內部審計最常漏——重點查)

7. **指標公式**:Accuracy/Precision/Recall 分母是什麼?P@K 的 K 固定嗎?latency 是 p50/p95/mean?
   MDD 若有:除「當時 running peak」還是全域高點?
8. **平均值的平均**:把各子集的指標直接平均是否合理(子集大小差異大時要加權)?
   紅旗:micro vs macro avg 混用;把每類的 accuracy 平均當整體 accuracy。
9. **自由重組/對齊**:benchmark 評估有沒有「免費的」後處理——閾值是在 test 上調的嗎?
   pipeline 裡有沒有能看到 test 標籤的步驟?

## D. 統計效力

10. **CI 正確性**:n 小要用 t 非 z;`np.std` 用 `ddof=1`;多次跑同一個 binary 不是 n 次獨立實驗
    (pseudo-replication:共用 binary/快取 → 對不同 seed 的結果做 bootstrap 才合法)。
11. **多重比較**:試過幾種超參/架構?對「最終贏家」的 p-value 應用 Bonferroni/BH 修正,
    n_trials = 試過的設定數。紅旗:調了 30 組參數,只報最好一組的 p-value。

## E. 部署現實(宣稱「生產就緒」時必查)

12. **延遲 / 吞吐**:benchmark latency 是 cold start 還是 warm?batch size 是生產環境的 batch 嗎?
    紅旗:用 batch=1024 測吞吐,但生產是 batch=1 即時推理。
13. **依賴固定版本**:宣稱能重現的結果有沒有 `requirements.txt` / lockfile?
    CUDA/Driver 版本明確嗎?紅旗:「在我機器上跑通」沒有 reproducible build。
