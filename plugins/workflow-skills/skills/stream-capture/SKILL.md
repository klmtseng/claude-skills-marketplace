---
name: stream-capture
description: 把直播/webinar 的講話逐字稿 + 採用的投影片撈下來並對齊成筆記。決策樹分平台(公開 YouTube/Twitch vs 登入牆 webinar)選捕捉路徑,再用本地 whisper(逐字稿)+ ffmpeg 場景偵測(投影片)+ OCR 產出 synced.md。觸發詞:直播、逐字稿、webinar、投影片、錄直播、串流、live、transcript、slides、WebinarJam、Zoom 錄影、把演講記下來。
---

# stream-capture — 直播/webinar → 逐字稿 + 投影片

**目標**:給一場直播,產出 ①帶時間戳逐字稿 ②去重後的投影片 PNG ③`synced.md`(逐字稿依投影片切段:講到哪張、講了什麼)。

**全本地、零金鑰**:yt-dlp / ffmpeg / whisper.cpp / RapidOCR 都在你的工具目錄。

## 三支工具(已備好,直接用)

| 腳本 | 作用 |
|---|---|
| `tools/stream_capture.sh <url> [label]` | yt-dlp 撈公開串流 or 直接餵 m3u8 |
| `tools/stream_record_local.sh [label] [--url ...]` | 本機側錄(音訊擷取 + 螢幕錄製)——**Wayland 環境下投影片可能黑,見附錄** |
| `tools/stream_process.sh <資料夾或檔> [--model small\|medium] [--scene 0.12] [--ocr]` | 錄好的檔 → transcript.srt/.txt + slides/ + synced.md |

處理腳本吃**單一媒體檔**或**資料夾**(自動挑 `audio.*` 當音源、`screen.*`/`raw.*` 當影像源)。

## 決策樹(先問平台,別急著錄)

```
直播連結
├── 公開平台(YouTube / Twitch / 一般 HLS)
│     → yt-dlp 直接吃:  stream_capture.sh <url> 名稱
│       (live 會邊播邊錄;結束或 Ctrl-C 停)
│
├── 登入牆 webinar(WebinarJam / Zoom / Teams)
│     yt-dlp 會轉址到 /login → Unsupported URL,撈不到。走以下之一:
│     ① 【最佳】抓 m3u8:進直播間後 F12→Network→篩 m3u8→Copy URL→貼回
│           → stream_capture.sh "<m3u8>" 名稱   或   ffmpeg -i "<m3u8>" -c copy out.ts
│           乾淨拿到影音(投影片+聲音都在),繞開所有本機坑。
│     └── ②【零技術替代】用手機/平板內建螢幕錄影(含聲音)錄整場
│           → 把檔案丟回 → stream_process.sh <檔> --ocr
│
└── 只能在這台機器看、又拿不到 m3u8
      → 只能保逐字稿,投影片幾乎沒救(見附錄坑 1)。音訊路見附錄坑 2。
```

**推薦順位:公開平台 yt-dlp > webinar 抓 m3u8 > 手機側錄 > 本機側錄(最後手段)。**

## 血淚坑(通用)

1. **簽章 m3u8 會過期**:進直播間後盡快抓、盡快開錄。若 ffmpeg 報 403,重抓一次帶最新 token 的 m3u8(必要時加 `-headers`/`-cookies`)。

## 處理階段(stream_process.sh 內部,通常不用管)

1. **逐字稿**:16k mono wav → `whisper-cli`(預設 `ggml-small`,長片要準用 `--model medium`,CPU-only 會慢)→ SRT+TXT。
2. **投影片**:ffmpeg `select='gt(scene,0.12)'` 場景偵測抽候選影格(換頁時整張變、scene 飆高),依 `showinfo` 的 pts_time 命名 `slide_<mmss>.png`。抓太多/太少調 `--scene`(低=多)。
3. **OCR**(`--ocr`):`doc2text.py --backend local`(RapidOCR)每張投影片轉文字。
4. **synced.md**:解析 SRT + 投影片時間戳,把逐字稿切進每張投影片區間。

## 驗收(宣稱完成前)

- `synced.md` 存在且非空;`slides/` 張數合理(不是 0、也不是幾千張=閾值錯)。
- 抽一段逐字稿對音訊聽感沒有整段亂碼/空白(語言路由對)。
- 投影片抽驗 2~3 張不是黑畫面/重複頁。

---

## Appendix:環境相關備註(依自身環境調整)

以下坑在特定 Linux 桌面環境實測(2026-07-05),若你的環境不同請對應調整:

1. **Wayland + snap Firefox 下螢幕錄影 = 黑畫面。** `ffmpeg x11grab :0.0` 抓不到 app 視窗,只有黑底。`MOZ_ENABLE_WAYLAND=0` 對 snap Firefox 無效(且 `firefox --new-window` 會接到既有實例、忽略 env)。**結論:Wayland 環境下本機側錄拿不到投影片,別浪費 live 時間試,直接走 m3u8 或手機錄。**
2. **PipeWire 音訊要驗音量,別信檔案大小。** `pw-record` 錄的是 sink monitor;WAV 等速增長跟有沒有聲音無關。錄前/錄中務必抽驗:`ffmpeg -i 快照.wav -af volumedetect -f null /dev/null`,看到 `mean_volume: -91 dB` = 全靜音(sink 選錯 / 走 HDMI / webinar 沒在放)。預設 sink 用 `wpctl status` 星號那個。
3. **停螢幕別誤殺音訊。** `stream_record_local.sh` 的 cleanup 會連 pw-record 一起收;要單獨停一軌得改腳本,別 `pkill` 單一進程觸發 trap。
4. **某些 Linux 環境 ffmpeg 沒編 pulse 輸入**(`Unknown input format: 'pulse'`)——此時音訊只能用 `pw-record`,不能 `ffmpeg -f pulse`。
