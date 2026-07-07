---
name: agent-memory
description: 給「長時間、多步驟 LLM agent 迴圈」加上有界記憶 + 遺忘 + 召回(零訓練、編排層、本地 CPU)。把 Unlimited-OCR 的 ring-buffer 滑動窗 + 光學壓縮 + prefill 釘住 + 翻回書頁,搬到 agent 層,讓 context 不爆窗、長任務記憶體恆定。觸發詞:長 agent、context 爆窗、長迴圈、無人值守 cron agent、long-horizon、記憶體成長、多步工具呼叫累積歷史。
---

# agent-memory — 有界記憶 + 遺忘的 agent 根基

當你在**建/跑一個長時間、多步驟的 LLM agent 迴圈**(尤其無人值守 cron,如你的 cron 服務或長跑 pipeline),
歷史會把 context window 撐爆。這個 skill 把 Unlimited-OCR 的核心招式搬到編排層,**不碰模型、不重訓**。

## 何時用 / 何時不用
- ✅ 用:會累積長歷史的迴圈(數十步以上、跑很久、無人值守、多工具呼叫)。
- ❌ 不用:短任務、一兩次往返——直接塞 context 就好,別過度工程。
- ⚠️ 限制:它管的是**你建的 agent 迴圈**的 context,**不能接管 Claude 自己在對話裡的 context**(那是 harness 在壓縮)。

## 對映 Unlimited-OCR
pinned 工作集=prefill 釘住來源頁;滑動窗=ring-buffer decode 視窗;compaction 摘要=光學壓縮;
召回=翻回書頁;**遺忘=降級為可檢索,不真刪**。

## 怎麼接(整合模式 = 3 行)
模組在本 skill 目錄 `memory_manager.py`。
```python
from memory_manager import MemoryManager
mm = MemoryManager("run.jsonl", window=8, compact_batch=5,
                   summarize_fn=call_claude)      # 正式:接 Claude 做語意摘要(預設 extractive stub)
mm.pin("goal", task); mm.pin("constraints", rules)  # 釘住目標/約束(永不淘汰)
while not done:
    ctx = mm.assemble(query=current_subgoal)       # ← 取有界 context 餵 LLM(不爆窗)
    action = llm(ctx); obs = run(action)
    mm.add_step("assistant", action); mm.add_step("tool", obs)  # ← 自動滑窗+壓縮+降級
mm.flush()                                          # 收尾把剩餘待摘要壓掉
```

## 接到實際目標

- **cron 服務 / 長跑 pipeline**:在迴圈裡 import → 啟動即自動有界記憶;`ledger_path` 直接指向
  既有的 forward ledger 或 append-only log(融合最自然)。
- **多輪程式碼審查 / builder-reviewer 迴圈**:pin 規格,窗=最近 diff,舊交流壓縮,要翻舊決策時召回。

## 升級(production)
- `summarize_fn=` 接 Claude → 真語意壓縮(取代 extractive stub)
- `recall_backend=` 換 embedding(sentence-transformers all-MiniLM,CPU 可跑)或 Mem0 library → 抓改寫/同義
- `count_tokens=` 真實 tokenizer;並可在 assemble 加 token 硬上限裁切

## 啟動
打 `/agent-memory`,或說「幫這個長 agent 接上 bounded memory」;描述觸發詞見上方 frontmatter。
（軟體專案,完成後可用 `/validity-audit` 通用版做獨立審查。）
