---
name: core-gate
description: AI 量產中大型程式碼(遊戲/模擬/引擎/回測核心)的工程等級工作流:確定性核心契約 → 閘門先於功能 → 量產 → 機器驗收(靜態純度掃描+N-run 確定性+headless 情境閘門)→ 對抗審查。觸發詞:工程等級、確定性核心、headless 驗收、merge gate、AI 生成大專案、模擬引擎、lockstep、replay、checksum。
---

# core-gate — AI 量產程式碼的工程等級工作流

**問題**:AI 一次能生一兩萬行,人看不完。沒有機器閘門,品質靠運氣;瘋傳的 one-shot 案例是倖存者,不是工作流。

**解法**(源自 tigercosmos/aoe-mini 的實證做法 + 我們自己的分層原則):把紀律寫成機器檢查,讓「閘門常綠」取代「人工細讀」成為合併標準。

**適用**:遊戲、模擬、敘事引擎、ALife、回測核心——任何「有一個該確定性的核心 + 一圈允許髒的外殼」的系統。
**不適用**:一次性腳本、純 UI 玩具、爬蟲膠水碼(直接寫就好,別套流程)。

## 工作流五階段

### Phase 0:契約先行(還沒寫任何功能碼之前)

跟使用者釘死這份「核心契約」,寫進專案 `PROGRESS.md` 或 `CONTRACT.md`:

1. **分層**:哪些目錄是確定性核心(sim/core/content),哪些是允許髒的外殼(render/ui/io)。核心永不 import 外殼。
2. **時間模型**:固定時步(如 20Hz tick 計數),核心內禁止掛鐘時間。
3. **亂數政策**:單一 seeded PRNG 注入,禁止全域亂數。
4. **世界指紋**:每 tick(或每 N tick)輸出 world checksum——同 seed + 同指令流 → 逐位元一致。
5. **headless 驗收命題**:一條指令、無互動、跑出可重現的決定性結果(一場對戰分出勝負、一段劇情跑到結局、一次回測出帳)。這是 merge gate 的定義。
6. **內容=資料**:單位/事件/規則寫成 data rows + 通用 Modifier,不寫成散落的 if。

寫 `gates.json` 把第 1-3 條變成機器可查:

```json
{
  "layers": [
    {"name": "core", "paths": ["src/core", "src/sim", "src/content"],
     "profile": "deterministic-core"},
    {"name": "content", "paths": ["data/"], "profile": "data-layer"}
  ]
}
```

### Phase 1:閘門先於功能

先搭骨架(空的分層目錄 + 最小 tick 迴圈 + checksum 輸出),然後**立刻**把三道閘門接進測試指令,確認全綠才開始寫功能:

```bash
# 閘門一:靜態純度掃描(核心碰了亂數/掛鐘/DOM/網路就 FAIL)
python3 <本 skill 目錄>/scripts/static_scan.py --config gates.json

# 閘門二:確定性(同 seed 跑 N 次逐位元一致;多 seed 互異防「seed 沒接上」)
python3 <本 skill 目錄>/scripts/determinism_gate.py \
  --runs 2 --seeds 7,8,9 --extract 'CHECKSUM \S+' -- \
  python3 -m sim.headless --seed {seed} --ticks 500

# 閘門三:headless 情境閘門(專案自己的驗收命題,如 AI-vs-AI 跑出決定性勝負)
python3 -m sim.headless --seed 7 --until-victory
```

把三條包成一個 `make gate` 或 `./gate.sh`。骨架+閘門全綠 = 第一個 commit。

### Phase 2:量產

- 放手讓 AI 生成功能,但**每個里程碑收尾必跑 `./gate.sh`,全綠才 auto-commit**(local-only,不 push,遵守既有 git 紀律)。
- 新功能若需要新的非確定性(如音效),放外殼層;真的要進核心就在該行加 `gate-allow: 理由`(理由必填,會留在 code review 的視野裡)。
- 內容擴充走資料表,不走新 if。加內容不該讓核心 diff 超過幾行。

### Phase 3:驗收

merge gate = 四樣全綠,缺一不可:

| 閘門 | 指令 | 抓什麼 |
|---|---|---|
| 靜態純度 | `static_scan.py --config gates.json` | 核心層的非確定性洩漏、DOM/網路/渲染滲入 |
| 確定性 | `determinism_gate.py --seeds ... --extract ...` | 掛鐘漂移、迭代序不定、浮點聚合序、假確定性 |
| headless 情境 | 專案自訂 | 系統作為整體能跑出有意義的決定性結局 |
| 漂移(選用) | `drift_gate.py --config drift.json` | vendored 模組/bundled skill/設定樣板的副本偏離來源(有「單一來源+多份副本」時才需要) |
| 單元測試 | pytest / vitest | 常規正確性 |

> **漂移閘門**(抽自 anthropics/financial-services 的 `check.py`):專案若把一份來源複製到多處(vendored 零依賴模組、bundled skill、設定樣板),`drift.json` 宣告 source→copies,閘門保證副本不偷偷分岔;`--fix` 用來源覆蓋副本(=官方 sync-agent-skills.py)。

### Phase 4:對抗審查(選用但建議)

- 程式碼:gstack `/review` 對抗式審查(local-only repo 記得手動跑它的對抗核心)。
- 若專案產出研究宣稱(「重現了 XX 現象」):跑 `/validity-audit` 再下結論。

## 坑與心法

- **determinism_gate 的 `--extract` 沒匹配到任何行會直接 FAIL**——閘門空轉不算通過,別靜默。
- 多 seed 全同輸出 = seed 沒接上,工具會抓;但「seed 接上了、只影響無關緊要的角落」它抓不到,headless 情境閘門才是後盾。
- Python 浮點在同機同版是確定的;跨機器要逐位元一致才需要定點數,個人專案別過度設計。
- 平行化(threads/multiprocessing)是確定性頭號殺手,核心保持單執行緒,慢了再談。
- 這套跟 `/agent-memory`(長迴圈記憶)、分層設計原則(確定性地板+LLM天花板)是同一族:**保證來自確定性層,彈性放外殼**。
