---
name: validity-audit
description: 任何「有宣稱的產出」結案/發表/交付前的自我否證機制。兩段式:內部機械審計(按受審對象載領域包:量化研究/內容教材/部署系統/文件)+ 強制獨立 reviewer(沒參與建造的 subagent 對抗式複查);可加選 T3 適用性審(為真但不夠好)。觸發詞:檢驗研究、發表前驗證、audit、leakage、overfitting、驗收教材、審這個專案、結案體檢、宣稱核實。
---

# Validity Audit — 產出自我否證機制(通用核心 + 領域包)

目標:在「下結論 / 發表 / 交付 / 結案」**之前**,主動找出產出的問題。
核心教訓:**單一建造者有盲點**(真實審計案例 2026-06);且否證宣稱 ≠ 系統健康(真實審計案例 2026-07)。
管線是領域無關的;只有「第 1 段查什麼」隨領域換包。

## 三層威脅模型(審前先決定跑到哪層)

- **T1 宣稱為假**(預設,必跑):headline 主張與實物不符——數字灌水、覆蓋不足、旗標造假、引用捏造。
- **T2 沒宣稱但會咬人**(對象=部署系統/管線/結案交付物時必跑):無備份的不可重生資料、沒實測過的交付物、無界成長。
- **T3 為真但不適其用**(使用者要求「不只驗真,還要夠好」時跑;**只出建議不擋結案**):目的有沒有被有效達成——例:教材無進度記錄/複習不對準弱點/接觸頻率不均。真實審計教訓(2026-07):T1+T2 全過的產出,6 條專業建議裡有 2 條落在 T3,原版 VA 結構性抓不到。

## 領域包路由(第 1 段機械審計查什麼,按受審對象載入)

| 受審對象 | 領域包 |
|---|---|
| 量化研究/回測/因子/ML 績效宣稱 | `references/mechanical-audit.md`(A–E:洩漏/宇宙/算術/統計/回測) |
| 內容產線/教材/資料集/生成內容 | `references/domain-content.md`(C1–C7:覆蓋/事實/捏造閘門/旗標/快樂路徑/版權) |
| 部署系統/每日管線/結案/交付物 | `references/system-review.md`(S1–S7,即 T2 層) |
| 制度檔/規則/文件 | fresh read-back + 規則互打/路徑失效/弱模型誤讀(見 judgment-rubrics R5) |
| 任一對象 + 要求 T3 | 加載 `references/fitness-review.md`(F1–F6) |

對象橫跨多類就多包並載。不確定歸哪類 → 問使用者,別硬套量化包。

## Do NOT rely on this skill for(過關 ≠ 已驗證)

過關只代表「primed reviewer 沒找到清單內的問題」,不代表產出為真/夠好。各包清單外的威脅
(regime 斷裂、data-snooping、成本樂觀、教學法本身錯誤、美學品味)仍靠人。
T3 未跑時,「為真但不夠好」類問題一律不在保證範圍。

## Required workflow

0. **分類受審對象 + 選威脅層級**:載對應領域包;T3 是否跑,聽使用者(預設不跑)。
1. **釘住宣稱。** 列出每個 headline 主張(含 meta 旗標如 human_verified、「涵蓋全部 X」)+ 對應檔案/數字。**口頭對使用者說過的宣稱也算宣稱。**
2. **回收歷史失手。** 跑 `python3 <skill>/ledger.py challenges`,把歷史失手類別當【強制挑戰】逐條答。細節見 `references/coevolution.md`。
3. **內部機械審計。** 按領域包逐項檢查+歷史挑戰,寫成 `audit/leak_audit.md`(或 `audit/content_audit.md`)。**每個 PASS 標記『建構必然(恆真)』還是『可能 FAIL』。**
4. **強制獨立 reviewer(輪換對手)。** 載 `references/independent-reviewer.md`,spawn 沒參與建造的 subagent 冷審→熱審;盡量換模型家族/framing;加一隻攻擊清單本身。**冷審不得看 ledger。**
   4b. **T2 系統體檢(條件觸發)**:載 `references/system-review.md` 跑 S1–S7。
   4c. **T3 適用性審(使用者要求時)**:載 `references/fitness-review.md`,發現一律標 P2/P3 級建議,不升級、不擋結案。
5. **重現閘門。** 每項發現必須**先重現才算數**:能跑的用唯讀檢查數值重現;不能跑的(文件/內容)必須釘到 `檔案:行號` 且引文與原文逐字相符。沒重現的只是假設。
6. **誠實更正 + 閉環。** 載 `references/correction-and-judgment.md`:修確認的 bug、撐不住的宣稱撤回、存報告;**結案 `ledger.py append` 把本次新失手寫回(附 domain 欄位)。**

## Non-negotiables

- **第 2 段獨立 reviewer 不可省**(抓建造者同型盲點的唯一防線)。
- **重現閘門不可繞**:沒被重現/釘到行號的發現不准寫進結論(擋 reviewer 幻覺)。
- **撤回是預設**,不是例外;宣稱撐不住就降級措辭,不是加解釋。
- **恆真句不得當證據**(真實審計教訓)。
- **T3 發現永遠是建議**,不得升級成 blocker、不得與 T1/T2 混在同一嚴重度尺度。
- **ledger 閉環不可省**:開審 `challenges`、結案 `append`。
- **只回報實際跑過的檢查**;每次 audit 記 hit/miss/誤報。

## Progressive references(只在該步觸發時載入)

- `references/coevolution.md` — miss-ledger/恆真句偵測/對手輪換。
- `references/mechanical-audit.md` — 量化包 A–E(含量化預設假設)。
- `references/domain-content.md` — 內容/教材包 C1–C7。
- `references/system-review.md` — T2 系統體檢 S1–S7。
- `references/fitness-review.md` — T3 適用性審 F1–F6。
- `references/independent-reviewer.md` — 冷審/熱審流程 + prompt 範本。
- `references/correction-and-judgment.md` — 更正流程 + 判讀原則。
- `meta_eval/golden_cases/` — 標竿案例(新領域包上線前先對標竿跑回收率)。

## 如何啟動

`/validity-audit`(可附專案路徑),或「幫我用 validity-audit 檢驗這個研究/教材/系統/文件」。
