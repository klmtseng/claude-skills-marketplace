# 共演化層:讓 audit 自己不被 Goodhart(RQGM 輕量版)

**動機。** validity-audit 是一個**靜態評估器**(固定清單 + 固定 reviewer prompt)。RQGM
(Red Queen Gödel Machine, arXiv:2606.26294)的核心命題:靜態評估器會被 Goodhart——研究(或建造者)
會學會通過清單,而非真的變有效。本層用三個輕量機制補上共演化的另一半,**不上連續共演化迴圈**
(對人工觸發、一專案一次的協定是過度工程)。P2/P3 原語可依本文描述自行實作。

## 機制 1:累積式 miss-ledger(P2 anchor-from-ledger)

- 檔案 `audit_ledger.jsonl`(append-only)。每次 audit 結案時,把失手/撤回/差點漏掉的,
  用 `python3 ledger.py append '<json>'` 寫入(欄位:id/date/project/category/claim/miss/**detector**/caught_by/severity)。
- **開審時強制**跑 `python3 ledger.py challenges`,把歷史失手的**類別 + 偵測器**當【強制挑戰】,
  逐條回答「本研究會不會犯同一個?怎麼驗證沒犯?」——這是 P2 的 anchor:從 ledger 回收舊真值,
  逼新一輪至少不退步。清單因此**累進、隨時間變強(複利)**,不再是固定 A–E。

## 機制 2:恆真句偵測(把真實審計教訓固化)

- 一個「永遠 PASS」的檢查 measures nothing——這正是**評估器變鬆/被 Goodhart 的簽名**。
- **對每個 PASS 標記**:它有可能 FAIL 嗎?還是由建構/定義必然為真(恆真)?
  - 恆真的 → 只能標為「一致性檢查(sanity)」,**不得當實證證據**寫進 headline。
  - 例:度量指紋忽略 label、而變換只改 label → 指紋不變是定義必然,不是發現。

## 機制 3:對手輪換 + 邏輯抹除(P3)

- **輪換對手**:冷審 reviewer 盡量換模型家族 / 換 framing(同模型與建造者共享盲點)。
  額外加一隻**專職「攻擊清單本身」**的 reviewer,任務只有兩個:找**恆真的 on-check**(機制 2 漏標的)、
  找**清單外的威脅**(A–E 沒有、但這個研究特有的失效模式)。
- **邏輯抹除(P3)**:冷審 reviewer **不得**看到 ledger 原文或過去失手清單(否則變 pattern-match 背答案,
  獨立性歸零)。ledger challenges 只餵**建造者端**的機械審計。**熱審**才可把類別給 reviewer(「別重複、往更深挖」)。
  兩輪差距 = 結果有多依賴 framing。

## 收尾(閉環)

audit 結束後**務必**把本次新失手 append 進 ledger(即使這次全過,也記「跑了哪些挑戰、hit/miss」)。
沒閉環,評估器就不會演化,這一層等於沒有。
