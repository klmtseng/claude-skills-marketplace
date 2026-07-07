"""Agent 記憶 policy 層 —— 把 Unlimited-OCR 的「有界記憶 + 遺忘」搬到 agent 編排層(零訓練)。

對映:
  pinned 工作集      ←→ prefill 釘住的來源頁(目標/約束/耐久事實,永不淘汰)
  滑動窗(最近 N 步)  ←→ ring-buffer decode 視窗(逐字保留近期)
  compaction(摘要)   ←→ 光學壓縮(超窗的舊步驟壓成摘要)
  ledger + 召回        ←→ 把書頁翻回來(降級為可檢索,而非真刪)

model-agnostic:summarize_fn(你的 LLM,如 Claude)與 embed/recall 後端皆可插拔;
預設自帶可測 stub(extractive 摘要 + TF-IDF 召回),本機 CPU 即可跑、零金鑰。
"""
import json
import time
import pathlib
from collections import deque


def _approx_tokens(text):
    return max(1, len(text) // 4)


def _extractive_summary(steps):
    """預設 stub 摘要(無 LLM):取每步首句 + 截斷。正式用請傳入 summarize_fn=你的 LLM。"""
    bits = []
    for s in steps:
        first = s["text"].strip().split(". ")[0][:160]
        bits.append(f"- {s['role']}: {first}")
    return "（摘要 stub）以下 %d 步的要點:\n" % len(steps) + "\n".join(bits)


class TfidfRecall:
    """預設召回後端:TF-IDF 餘弦(sklearn,零模型下載、CPU 即時)。可換成 embedding 後端。"""
    def __init__(self):
        self._docs = []          # list[(id, text)]
        self._dirty = True
        self._vec = None
        self._mat = None

    def add(self, doc_id, text):
        self._docs.append((doc_id, text)); self._dirty = True

    def _build(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self._vec = TfidfVectorizer().fit([t for _, t in self._docs])
        self._mat = self._vec.transform([t for _, t in self._docs])
        self._dirty = False

    def search(self, query, k):
        if not self._docs:
            return []
        if self._dirty:
            self._build()
        import numpy as np
        qv = self._vec.transform([query])
        sims = (self._mat @ qv.T).toarray().ravel()
        order = np.argsort(-sims)[:k]
        return [(self._docs[i][0], self._docs[i][1], float(sims[i])) for i in order if sims[i] > 0]


class MemoryManager:
    def __init__(self, ledger_path, window=8, compact_batch=5, token_budget=4000,
                 summarize_fn=None, recall_backend=None, count_tokens=None):
        self.ledger_path = pathlib.Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.window_size = window
        self.compact_batch = compact_batch
        self.token_budget = token_budget
        self.summarize_fn = summarize_fn or _extractive_summary
        self.count_tokens = count_tokens or _approx_tokens
        self.recall = recall_backend or TfidfRecall()

        self.pinned = {}                 # key -> text(釘住,永不淘汰)
        self.window = deque()            # 最近步驟(逐字)
        self._pending = []               # 溢出待摘要的步驟
        self._n = 0                      # 步驟流水號
        self._load_ledger_into_recall()

    # ---------- 寫入 ----------
    def pin(self, key, text):
        self.pinned[key] = text

    def unpin(self, key):
        self.pinned.pop(key, None)

    def add_step(self, role, text):
        self._n += 1
        self.window.append({"id": self._n, "role": role, "text": text, "ts": time.time()})
        # 滑動窗:超過 window_size 的最舊步驟 → 進待摘要緩衝(降級,不丟)
        while len(self.window) > self.window_size:
            self._pending.append(self.window.popleft())
        if len(self._pending) >= self.compact_batch:
            self._compact()

    # ---------- 遺忘=壓縮+降級 ----------
    def _compact(self):
        if not self._pending:
            return
        batch = self._pending; self._pending = []
        ids = [s["id"] for s in batch]
        summary = self.summarize_fn(batch)
        # 摘要進 context-可用層 + 原文進 archival,兩者都可被召回(降級非刪除)
        self._ledger_append({"type": "summary", "ids": ids, "text": summary})
        for s in batch:
            self._ledger_append({"type": "step", "id": s["id"], "role": s["role"], "text": s["text"]})

    def flush(self):
        """手動把剩餘待摘要的步驟壓掉(任務收尾時用)。"""
        self._compact()

    def _ledger_append(self, entry):
        entry["ts"] = entry.get("ts", time.time())
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        rid = f"{entry['type']}:{entry.get('ids') or entry.get('id')}"
        self.recall.add(rid, entry["text"])

    def _load_ledger_into_recall(self):
        if not self.ledger_path.exists():
            return
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
                self.recall.add(f"{e['type']}:{e.get('ids') or e.get('id')}", e["text"])
            except Exception:
                pass

    # ---------- 組裝有界 context ----------
    def assemble(self, query=None, recall_k=4):
        """回傳餵給 LLM 的有界 context = pinned + (query 相關召回) + 最近窗。"""
        parts = []
        if self.pinned:
            parts.append("## PINNED(目標/約束/耐久事實)")
            parts += [f"- [{k}] {v}" for k, v in self.pinned.items()]
        if query:
            hits = self.recall.search(query, recall_k)
            if hits:
                parts.append("\n## RECALLED(與當前查詢相關的舊記憶)")
                parts += [f"- {t}" for _, t, _ in hits]
        parts.append("\n## RECENT(最近步驟,逐字)")
        parts += [f"- {s['role']}: {s['text']}" for s in self.window]
        ctx = "\n".join(parts)
        return ctx

    def stats(self):
        ledger_lines = sum(1 for _ in open(self.ledger_path, encoding="utf-8")) if self.ledger_path.exists() else 0
        return {"steps_seen": self._n, "window": len(self.window), "pending": len(self._pending),
                "pinned": len(self.pinned), "ledger_entries": ledger_lines,
                "assembled_tokens": self.count_tokens(self.assemble())}
