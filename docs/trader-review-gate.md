# Trader Review Gate

本專案的交付門檻是 6 位不同交易風格 reviewer 一致通過。通過定義分兩層：

- Repo/MVP gate：功能、資料契約、RWD、風控、通知 stub、付款 gate 與測試都符合 demo/MVP 交付。
- Commercial gate：正式行情授權、再散布條款、Email/LINE/Web Push 實際送達、ECPay webhook、會員權限與法務條款完成後，才可販售即時付費服務。

## Latest Fixes

- 付費方案不再能從前端切換 `plan=pro` 自行解鎖；後端在 `not_licensed` 或 `can_redistribute=false` 時也會強制使用 free masking。
- `/api/runs/{id}/exclusions` 已接到前端，畫面與 CSV 使用完整排除清單，不只使用 preview。
- 新增 `RiskProfile` 後端模型與 `/api/risk-profiles/default` GET/PATCH，風控設定可保存並有 run snapshot/hash。
- `ScreeningRun`  now stores `rule_snapshot`, `risk_profile_snapshot`, `input_snapshot_hash`, `universe_hash`, `risk_profile_hash`, and `score_formula_version`.
- `GET /api/today/runs` now returns the rule/risk profile snapshot that belongs to the run, so editing a future risk profile does not rewrite old run context.
- `scripts/start-local.ps1` builds production runtime into `frontend/.next-runtime`, so a separate `npm run build` can update `.next` without breaking the running `next start` service.
- `npm run build` uses a locked build wrapper to prevent parallel Next builds from corrupting the active build directory; `check-runtime` verifies frontend, backend, and `/_next/static` assets.
- 候選股新增 `reference_price`, `liquidity_twd_million`, `distance_to_limit_up_pct`, `intraday_pullback_pct`, `late_session_change_pct`, `risk_flags`。
- 前端候選卡、CSV、分享文字使用同一份風控 profile，顯示單檔資金上限、股數/張數、滑價緩衝與停損參考。
- 通知服務在 demo mode 不再回報已送達；checkout 在行情授權與再散布 gate 前回傳 403。
- 新增 `/api/data/status` alias，保留 `/api/system/data-status`。
- 回測 response 新增逐日 demo 明細、資料版本、規則 hash、MAE/MFE 欄位，並明確標示仍是 demo skeleton。
- UI 文案已清理為繁體中文，手機第一屏直接顯示今日清單、快覽、授權狀態與底部導覽。
- `infra/schema.sql` links `screening_runs.market_data_batch_id` to `market_data_batches(id)` for durable provenance joins.

## Verified Commands

- `python -m pytest -q` → 12 passed
- `python -m ruff check app tests` → passed
- `npm run lint` → compliance copy check passed
- `npm run build` → Next production build passed
- `scripts/start-local.ps1` → backend + Next production frontend started
- `scripts/check-runtime.ps1` → frontend 200, backend ok, `_next/static` assets 200
- Playwright smoke test → mobile loaded, no console errors, first screen shows 今日快覽 / 付費鎖定 / `not_licensed`, candidate list present

## Remaining Commercial Gates

- 正式行情資料授權與再散布條款尚未完成。
- Email、LINE Official Account / Messaging API、Web Push 尚未完成實際送達、重試與退訂流程。
- ECPay 信用卡/定期定額、ReturnURL、PeriodReturnURL、電子發票與 webhook 尚未接入正式閉環。
- 會員登入、訂閱狀態、權限同步與遮罩解除尚未接上正式 auth/billing。
- 法務條款與頁面/通知文案仍需正式審閱。

因此目前可交付為 demo/MVP reviewer 版本，不能宣稱已可商轉販售即時推播服務。
