# 台股 13:00 選股系統（方案1：靜態輸出）

本專案採用「方案1」實作：  
- 每天固定時間透過排程產生一次靜態 JSON
- 前端只讀這份 JSON（無需長駐 API）
- 透過 GitHub Pages 發佈成靜態站點

---

## 專案結構

- `scripts/generate-static-feed.py`  
  每日排程執行入口：讀取規則/風險設定，跑一次選股，輸出靜態資料 JSON。
- `config/screening_rule.json`  
  選股條件（可直接改參數，不改程式）
- `config/risk_profile.json`  
  風險設定（可直接改參數）
- `frontend/public/data/today.json`  
  今日結果（前端讀取）
- `frontend/public/data/runs/{run_id}.json`  
  各日 run 快照
- `frontend/public/data/history.json`  
  最近 run 歷史
- `frontend/lib/api.ts`  
  新增 `NEXT_PUBLIC_STATIC_DATA=1` 時走靜態資料模式
- `.github/workflows/pages-static-refresh.yml`  
  GitHub Actions：排程 + 產生資料 + 建站 + 部署

---

## 本地驗證

1. 安裝套件

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .["dev"]

cd ..\frontend
npm install
```

2. 先在本機產生今日資料

```powershell
cd ..
python scripts/generate-static-feed.py
```

3. 啟動前端（靜態 API 模式）

```powershell
cd frontend
$env:NEXT_PUBLIC_STATIC_DATA="1"
$env:NEXT_PUBLIC_API_BASE_URL=""
npm run dev
```

4. 本機打包測試

```powershell
cd frontend
$env:NEXT_PUBLIC_STATIC_DATA="1"
$env:NEXT_PUBLIC_API_BASE_URL=""
npm run build
```

---

## GitHub Actions 排程（13:00 台北）

工作流檔：`.github/workflows/pages-static-refresh.yml`  
時間設定為 `0 5 * * 1-5`（UTC），等同台北時間每天 13:00（平日）。

流程：
1. Checkout
2. 安裝 backend / frontend 依賴
3. 執行 `python scripts/generate-static-feed.py`
4. `npm run build`（Next 靜態輸出）
5. 部署 `frontend/out` 到 GitHub Pages

---

## 部署到 studjo.dev 帳號（你指定）

目標帳號：`studjo.dev@gmail.com`（目前 gh CLI 顯示目前登入帳號 `StudjoDev`）

### 建立/連接遠端 repo（示範）

```bash
gh repo create StudjoDev/<repo-name> --public --source . --remote origin
```

### 上傳

```bash
git add .
git commit -m "feat: static output + GitHub Pages scheduled feed"
git push -u origin main
```

### 啟用 Pages

在 GitHub 專案設定中：
- Settings → Pages → Source：**GitHub Actions**
- 確認 Actions workflow `Refresh Static Screening Site` 已啟用
- 可先手動 `Run workflow` 驗證部署成功

完成後你會得到：
- `https://<user>.github.io/<repo-name>/`（若是 user site 為 `https://<user>.github.io/`）

---

## 註記

- 目前 `backend/app/services/market_data.py` 仍以 mock 資料為預設供應。  
- 要接到真實資料源時，只要實作 `MarketDataProvider` 並更新 `MARKET_DATA_PROVIDER` 來源設定即可，不需改前端流程。
