---
name: gh-vercel-publish
description: 把本地專案發佈到 GitHub 並部署到 Vercel 取得公開網址。涵蓋 gh/vercel CLI 安裝、device flow 認證、repo 建立、自動部署串接、上線驗證。適用任何要「上 GitHub + 公開網址」的專案。
---

# 發佈專案到 GitHub + Vercel

目標：本地目錄 → GitHub repo → Vercel 公開網址，並且之後 `git push` 自動重新部署。
全程用 device flow，**絕不**要使用者在對話中貼 token。

## 0. 前置檢查（一次跑完）

```bash
gh auth status          # 已認證會列出帳號 (<your-username>, keyring)
vercel whoami           # 已認證會印出帳號
git -C <專案目錄> status # 是否已是 git repo
```

- `gh` 不存在 → 下載 static binary 到 `~/.local/bin`（免 sudo）：
  從 https://github.com/cli/cli/releases 抓 linux_amd64 tar.gz，解出 `bin/gh`。
- `vercel` 不存在 → `npm install -g vercel`（npm prefix 是 `~/.npm-global`，免 sudo）。

## 1. Git repo 準備

```bash
cd <專案目錄>
git init                         # 若還不是 repo
git config user.name "<your-username>"
git config user.email "<id>+<your-username>@users.noreply.github.com"  # noreply,不暴露真實信箱
```

- 寫 `.gitignore`（至少排除 `node_modules/`、`.vercel/`、`.env*`、暫存檔）。
- 確認沒有秘密檔案後才 `git add` 指名檔案、commit。

## 2. GitHub 認證 + 建 repo

```bash
gh auth login --hostname github.com --git-protocol https --web   # device flow
```

- **把網址和八碼明白印給使用者**：`https://github.com/login/device` + 代碼。使用者說「沒看到連結」時重新印一次並確認程序還活著。
- 認證完成後**必跑** `gh auth setup-git` —— 漏掉的話 `git push` 會死在 "could not read Username"。

```bash
gh repo create <repo名> --source . --push --public   # 公開/私有先問使用者
```

## 3. Vercel 認證 + 部署

```bash
vercel login    # device flow,印出 https://vercel.com/device + 代碼給使用者
```

- **已知坑**：`vercel login` 認證成功後可能卡在互動式提問不退出。token 已寫入 keyring，直接 `pkill -f "vercel login"` 沒關係，用 `vercel whoami` 驗證。
- **不要走 Vercel 網頁版 import**：GitHub App 未安裝時會找不到 repo，CLI 流程可完全繞過。

```bash
cd <專案目錄>
vercel deploy --prod --yes      # 靜態站: framework "Other"、無 build、輸出目錄 = 根目錄
vercel git connect              # 串 GitHub → 之後 git push 自動部署
```

## 4. 上線驗證

不要長 sleep（會被擋），用背景 waiter 等部署生效：

```bash
until curl -s https://<專案>.vercel.app/<某個本次改過的檔案> | grep -q "<本次新增的字串>"; do sleep 10; done; echo "=== new version live ==="
```

（用 `run_in_background` 跑，完成會收到通知。）

## 5. 收尾回報

給使用者：
- 公開網址 `https://<專案>.vercel.app`
- GitHub repo 網址
- 一句話說明之後「`git push` 就會自動重新部署」
- 提醒可在 github.com/settings/applications 撤銷 gh CLI 授權，讓機器回到無憑證狀態（若使用者在意）。

## 已驗證狀態（2026-06-11）

- gh 已認證：`<your-username>`，keyring token，scope repo —— 認證後通常可跳過步驟 2 的 login。
- vercel 已認證：`<your-username>` —— 認證後通常可跳過步驟 3 的 login。
- 範例成功案例：`<your-project>` → https://github.com/<your-username>/<your-project> → https://<your-project>.vercel.app
