# GitHub Pages 部署到 `studjo.dev@gmail.com`

這份文件整理你要把「台股 13:00 靜態候選清單」放到指定 GitHub 帳號（email
`studjo.dev@gmail.com`）名下的步驟。  
請先在該帳號登入 GitHub 後完成。

## 1. 建立/確認專案歸屬

1. 以 `studjo.dev@gmail.com` 身分登入 GitHub
2. 將此專案 push 到該帳號擁有的 repository
   - 推薦：`https://github.com/studjo-dev/studjo.github.io`
3. 確認 repo 已包含：
   - `.github/workflows/pages-static-refresh.yml`
   - `scripts/generate-static-feed.py`
   - `frontend/public/data/today.json`（第一次上線可先 commit 一份）

## 2. 啟用 Pages

1. 開啟 repo → Settings → Pages
2. Source 選 **GitHub Actions**
3. 在 Actions 中確認 `Refresh Static Screening Site` 已跑通

## 3. 權限/觸發

- 建議保留 `schedule: 0 5 * * 1-5`（UTC）  
  代表台北時間 13:00 左右自動更新
- 可先手動點 **Run workflow** 驗證一次
- `main` 分支 push 後會自動觸發

## 4. 設定（如為 repo page）

若你使用 `studjo.dev.github.io/<repo>`，在 GitHub Pages/Workflow 中把
`NEXT_PUBLIC_BASE_PATH` 設為 `/<repo>`，否則可留空。

## 5. 啟動後檢查

- 確認站點顯示 `/data/today.json` 最新資料
- `frontend/public/data/history.json` 是否有每次執行紀錄
- 遇到資料沒更新，多半是 workflow 未成功或 `Generate daily static dataset` 步驟失敗
