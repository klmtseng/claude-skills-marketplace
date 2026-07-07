---
name: tokenomics
description: 專案級 LLM 成本的事前估算與全生命週期管理:立項前用參考類別(自己的歷史日誌)估 token 預算 → 配置即成本決策 → 預算閘門(含成本回歸測試)→ 超量分級應對 → 對帳校準。觸發詞:token 預算、成本估算、立項估算、tokenomics、燒多少錢、budget、成本閘門、額度、API 成本、prompt 改動成本。
---

# tokenomics — 專案級 LLM 成本工程

**核心主張**:agent 專案的成本在寫第一行 code 前就可估——用自己的歷史日誌當參考類別(外部視角),估出來的預算寫成機器閘門,跑起來後對帳校準,估算誤差本身是被追蹤的指標。

**工具箱**(全零依賴,資料與腳本見你的成本追蹤目錄):
| 工具 | 職責 |
|---|---|
| `ref_class.py` | 參考類別提取:日誌 → 專案形狀 → 四類分佈(`ref_classes.json`) |
| `budget_estimate.py` | 形狀 × 參數 → `BUDGET.md`(P10/50/90 + 閘門值 + 可否證假設) |
| `cost_regress.py` | G4b 成本回歸:golden task token 分數 vs 基線 ±容差 |
| `token_forecast.py` | 全域預測 + walk-forward 自評分 + `--snapshot` 帳本 |
| `api_cost_estimate.py` | 反事實 API 帳單(事後精算) |

**設計文件**:見你的成本追蹤目錄下的 `DESIGN.md`(地形圖/五階段/發表計畫)。

## Phase 0 — 立項估算(新專案還沒呼叫 LLM 時)

1. 若 `ref_classes.json` 超過 30 天沒更新,先重跑 `python3 ref_class.py --days 90`。
2. 跟使用者確認三件事(訪談,一次問完):
   - 專案像哪類?**interactive-dev**(重度互動開發)/ **light-interactive** /
     **cron-service**(常駐 bot/cron)/ **oneshot-pipeline**(一次性實驗)
   - 每月活躍幾天?強度相對同類中位專案是高是低(輪數/context)?
   - 價格情境:實測組合(1.0)/ Batch(0.5)/ 傾 Haiku(~0.2)
3. 產出預算:
   ```bash
   python3 budget_estimate.py --name <專案> --class <類別> \
       --active-days <N> --intensity <x> --price-scale <s> --out <專案dir>/BUDGET.md
   ```
4. `BUDGET.md` 的「可否證假設」逐條唸給使用者聽——任一條他不同意,調參數重估。

## Phase 1 — 成本設計(配置即成本決策)

寫 agent 配置時逐項過:模型路由(每角色/步驟指定,裁判用 Haiku)、快取佈局(穩定前綴,
見 claude-api skill 的 prompt-caching)、context 政策(長迴圈接 /agent-memory)、
非互動路徑評估 Batch、每呼叫 `max_tokens`/`task_budget` 封頂。
**實證提醒**:成本 ≈ 輪數 × context 長度 × 單價;cache read 佔 token 量 ~95%,
context 管理是最大槓桿,模型換便宜是第二槓桿。

## Phase 2 — 預算閘門(與 /core-gate 三閘門並列,合稱 gate.sh)

- **G4a 呼叫封頂(人工檢查項,無自動工具)**:review 時逐一確認 LLM 呼叫點有
  max_tokens/task_budget。呼叫形態太多樣,刻意不做通用掃描器——這是 checklist 不是閘門。
- **G4b 成本回歸**:`cost_regress.py --baseline golden/base.json --tolerance 0.2 -- <golden cmd>`
  管線每次 LLM 呼叫後印一行 `TOKENS {usage json}`;claude -p json 輸出用 `--scan-json`。
  基線不存在時會寫入但 exit 1(逼人看一眼再 commit)。LLM 輸出有隨機性,基線用 `--runs 3`。
- **G4c 帳本 pre-flight**:`quota_guard.py --daily-cap <BUDGET.md 的單日上限>
  [--window-hours 5 --window-cap X] --tag <cron名>`,exit 2=超限,cron 開頭掛
  `|| exit 0` 即 defer。量的是 API 等值(訂閱制=影子價格,守視窗額度)。

## Phase 3 — 運行應對(分級,寫進 BUDGET.md)

50% P90 → ledger 記錄;80% → 你的通知管道(如 bot sendMessage / webhook);
100% → 降級鏈:換便宜模型 → 縮範圍 → defer → 停機待人;
token 流速異常(loop 失控特徵)→ 斷路器直接停,通知附最後 N 輪摘要。

## Phase 4 — 對帳校準(閉環)

- 每週:`token_forecast.py --snapshot`,對照各專案 BUDGET.md;假設被打破 → 重估,不默默吸收
- 結案:重跑 `ref_class.py` 讓實際形狀回寫參考類別;分類錯了改 `overrides.json`
- 估算誤差不收斂 → 這是方法問題,升級處理(加類別/改特徵),必要時跑 /validity-audit

## 誠實邊界(對外發表時必說)

個人尺度、n 小、區間寬是事實;訂閱制下成本是影子價格(管的是額度兩本帳);
新版 tokenizer 可能多產 ~30% tokens,跨模型估算帶換算係數。
