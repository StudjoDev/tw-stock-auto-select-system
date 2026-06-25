"use client";

import {
  AlertTriangle,
  Bell,
  CalendarClock,
  CheckCircle2,
  Copy,
  CreditCard,
  Download,
  History,
  LineChart,
  Lock,
  Mail,
  Save,
  Settings2,
  ShieldCheck,
  Smartphone,
  Sparkles,
  UserRound
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  createBacktest,
  createCheckout,
  fetchDefaultRule,
  demoToday,
  fetchDefaultRiskProfile,
  fetchRunExclusions,
  fetchToday,
  saveRiskProfile,
  saveRule,
  sendTestNotification
} from "../lib/api";
import type {
  BacktestResponse,
  CandidateStock,
  PlanCode,
  RiskProfile,
  ScreenedOutStock,
  ScreeningRule,
  TodayResponse
} from "../types";

const navItems = [
  { href: "#today", label: "今日", icon: LineChart },
  { href: "#strategy", label: "策略", icon: Settings2 },
  { href: "#notifications", label: "通知", icon: Bell },
  { href: "#history", label: "紀錄", icon: History },
  { href: "#account", label: "帳號", icon: UserRound }
];

const historyRows = [
  { day: "06/25", count: 3, coverage: 68 },
  { day: "06/24", count: 5, coverage: 61 },
  { day: "06/23", count: 2, coverage: 72 },
  { day: "06/20", count: 4, coverage: 57 }
];

const fallbackRiskProfile: RiskProfile = {
  id: "default-risk-profile",
  name: "一般風控",
  mode: "balanced",
  account_capital_twd: 1_000_000,
  max_trade_risk_pct: 0.5,
  max_daily_risk_pct: 1.5,
  max_holdings: 4,
  min_liquidity_twd_million: 50,
  slippage_buffer_pct: 0.15,
  lot_size: 1000
};

export default function Home() {
  const [plan] = useState<PlanCode>("free");
  const [data, setData] = useState<TodayResponse | null>(null);
  const [draftRule, setDraftRule] = useState<ScreeningRule | null>(null);
  const [riskProfile, setRiskProfile] = useState<RiskProfile>(fallbackRiskProfile);
  const [draftRiskProfile, setDraftRiskProfile] = useState<RiskProfile>(fallbackRiskProfile);
  const [exclusions, setExclusions] = useState<ScreenedOutStock[]>([]);
  const [backtest, setBacktest] = useState<BacktestResponse | null>(null);
  const [apiError, setApiError] = useState("");
  const [destination, setDestination] = useState("demo@example.com");
  const [channel, setChannel] = useState("email");
  const [status, setStatus] = useState("");
  const [teacherNote, setTeacherNote] = useState("觀察：只做條件整理，不作為交易指令。");

  useEffect(() => {
    let active = true;
    setApiError("");
    fetchToday(plan)
      .then(async (today) => {
        if (!active) return;
        setData(today);
        setRiskProfile(today.risk_profile);
        try {
          const editableRule = await fetchDefaultRule();
          if (active) setDraftRule(editableRule);
        } catch {
          if (active) setDraftRule(today.rule);
        }
        try {
          const editableRiskProfile = await fetchDefaultRiskProfile();
          if (active) setDraftRiskProfile(editableRiskProfile);
        } catch {
          if (active) setDraftRiskProfile(today.risk_profile);
        }
        try {
          const fullExclusions = await fetchRunExclusions(today.run.id);
          if (active) setExclusions(fullExclusions);
        } catch {
          if (active) setExclusions(today.exclusions_preview);
        }
      })
      .catch((error: Error) => {
        if (!active) return;
        setData(null);
        setExclusions([]);
        setApiError(`API 無法連線：${error.message}`);
      });

    createBacktest(60)
      .then((result) => {
        if (active) setBacktest(result);
      })
      .catch(() => {
        if (active) setBacktest(null);
      });

    return () => {
      active = false;
    };
  }, [plan]);

  const visibleCandidates = data?.candidates ?? [];
  const maskedCount = visibleCandidates.filter((candidate) => candidate.masked).length;
  const avgMatch = useMemo(() => {
    if (!visibleCandidates.length) return 0;
    return Math.round(
      visibleCandidates.reduce((total, candidate) => total + candidate.match_score, 0) /
        visibleCandidates.length
    );
  }, [visibleCandidates]);

  async function handleSaveSettings() {
    if (!draftRule) return;
    setStatus("儲存中...");
    try {
      const [updatedRule, updatedRisk] = await Promise.all([saveRule(draftRule), saveRiskProfile(draftRiskProfile)]);
      setDraftRule(updatedRule);
      setDraftRiskProfile(updatedRisk);
      setStatus("策略與風控設定已儲存，將套用到下一次篩選 run。");
    } catch {
      setStatus("儲存失敗，請確認 API 是否啟動。");
    }
  }

  async function handleNotificationTest() {
    setStatus("測試通知中...");
    try {
      const result = await sendTestNotification(channel, destination);
      setStatus(result.message);
    } catch {
      setStatus("通知 API 測試失敗。");
    }
  }

  async function handleCheckout() {
    if (data?.provenance?.license_status !== "licensed" || !data?.provenance?.can_redistribute) {
      setStatus("付費 checkout 已鎖定：需完成正式行情授權、再散布條款與商用審閱。");
      return;
    }
    setStatus("建立付款連結中...");
    try {
      const checkout = await createCheckout("pro_monthly");
      window.location.href = checkout.checkout_url;
    } catch {
      setStatus("付款流程目前未開放。");
    }
  }

  function handleShowDemo() {
    const demo = demoToday(plan);
    setData(demo);
    setDraftRule(demo.rule);
    setRiskProfile(demo.risk_profile);
    setDraftRiskProfile(demo.risk_profile);
    setExclusions(demo.exclusions_preview);
    setApiError("目前顯示離線展示樣本，非正式行情資料。");
  }

  function handleExportCsv() {
    if (!data || !visibleCandidates.length) return;
    const rows = [
      [
        "section",
        "symbol",
        "name",
        "data_version",
        "provider",
        "license_status",
        "match_score",
        "reference_price",
        "pct_change",
        "volume_intensity",
        "turnover_rate",
        "liquidity_twd_million",
        "distance_to_limit_up_pct",
        "intraday_pullback_pct",
        "late_session_change_pct",
        "risk_level",
        "position_budget_twd",
        "estimated_shares",
        "estimated_lots",
        "stop_loss_reference_pct",
        "max_position_pct",
        "risk_flags",
        "risk_notes",
        "reasons",
        "warnings"
      ],
      ...visibleCandidates.map((candidate) => {
        const position = estimatePosition(candidate, riskProfile);
        return [
          "candidate",
          candidate.symbol,
          candidate.name,
          data.run.data_version,
          data.provenance?.provider ?? "unknown",
          data.provenance?.license_status ?? "unknown",
          candidate.match_score,
          candidate.reference_price,
          candidate.pct_change,
          candidate.volume_intensity,
          candidate.turnover_rate,
          candidate.liquidity_twd_million,
          candidate.distance_to_limit_up_pct,
          candidate.intraday_pullback_pct,
          candidate.late_session_change_pct,
          candidate.risk_level,
          position.budget,
          position.shares,
          position.lots,
          candidate.stop_loss_reference_pct,
          candidate.max_position_pct,
          candidate.risk_flags.join(" / "),
          candidate.risk_notes.join(" / "),
          candidate.reasons.join(" / "),
          candidate.warnings.join(" / ")
        ];
      }),
      ...exclusions.map((stock) => [
        "excluded",
        stock.symbol,
        stock.name,
        data.run.data_version,
        data.provenance?.provider ?? "unknown",
        data.provenance?.license_status ?? "unknown",
        "",
        "",
        stock.pct_change,
        stock.volume_intensity,
        stock.turnover_rate,
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        stock.failed_conditions.join(" / "),
        ""
      ]),
      [
        "risk_profile",
        "",
        riskProfile.name,
        data.run.data_version,
        data.provenance?.provider ?? "unknown",
        data.provenance?.license_status ?? "unknown",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        riskProfile.mode,
        riskProfile.account_capital_twd,
        "",
        riskProfile.max_holdings,
        riskProfile.max_trade_risk_pct,
        riskProfile.max_daily_risk_pct,
        `min_liquidity=${riskProfile.min_liquidity_twd_million}`,
        `slippage=${riskProfile.slippage_buffer_pct}`,
        `lot_size=${riskProfile.lot_size}`,
        teacherNote
      ]
    ];
    const csv = rows.map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(",")).join("\n");
    const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `screening-${data.run.run_date}.csv`;
    link.click();
    URL.revokeObjectURL(url);
    setStatus("CSV 已匯出，包含候選、排除原因、資料版本與風控設定。");
  }

  async function handleCopyShareText() {
    const text = buildShareText(visibleCandidates, data, riskProfile, teacherNote);
    try {
      await navigator.clipboard.writeText(text);
      setStatus("分享文字已複製。");
    } catch {
      setStatus(text);
    }
  }

  return (
    <div className="app-shell">
      <DesktopRail />
      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">台股 13:00 條件篩選工作台</p>
            <h1>今日 13:00 候選清單</h1>
            <p className="subtitle">
              以規則化條件整理盤中候選、排除原因、資料來源與風控上限。此產品定位為選股工具，不提供投資建議或自動下單。
            </p>
          </div>
          <PlanSwitch plan={plan} onLocked={() => setStatus("付費版需完成會員、授權與付款 gate 後才會開放。")} />
        </header>

        <section id="today" className="section">
          <div className="section-heading">
            <div>
              <h2>13:00 篩選結果</h2>
              <p>{data?.compliance_notice ?? "尚未取得今日資料，候選清單會保持鎖定。"}</p>
            </div>
            <div className="actions compact">
              <button className="button secondary" type="button" onClick={handleCopyShareText} disabled={!visibleCandidates.length}>
                <Copy size={18} />
                分享文字
              </button>
              <button className="button secondary" type="button" onClick={handleExportCsv} disabled={!visibleCandidates.length}>
                <Download size={18} />
                CSV
              </button>
            </div>
          </div>

          {apiError ? (
            <div className="error-panel">
              <AlertTriangle size={20} />
              <div>
                <strong>正式資料未載入，候選清單不會自動改用展示資料。</strong>
                <p>{apiError}</p>
                <button className="button secondary" type="button" onClick={handleShowDemo}>
                  查看離線展示樣本
                </button>
              </div>
            </div>
          ) : null}

          <QuickSummary candidates={visibleCandidates} data={data} />
          <div className="data-banner">
            <AlertTriangle size={18} />
            <span>{data?.data_notice ?? "資料來源尚未完成授權檢查。"}</span>
          </div>
          <div className="status-row">
            <span className="status-pill">
              <Lock size={16} />
              付費鎖定 / {maskedCount} 檔已遮罩
            </span>
            <span className="status-pill">
              <ShieldCheck size={16} />
              授權 {data?.provenance?.license_status ?? "pending"}
            </span>
            <span className="status-pill">
              <ShieldCheck size={16} />
              可再散布 {data?.provenance?.can_redistribute ? "是" : "否"}
            </span>
            <span className="status-pill">
              <CalendarClock size={16} />
              截止 {formatTime(data?.provenance?.cutoff_time)}
            </span>
          </div>

          <div className="status-row">
            <span className="status-pill">
              <CalendarClock size={16} />
              {data?.run.completed_at ? "13:00 已完成" : "等待資料"}
            </span>
            <span className="status-pill">
              <CheckCircle2 size={16} />
              {visibleCandidates.length} 檔候選
            </span>
            <span className="status-pill">
              <ShieldCheck size={16} />
              {data?.provenance?.provider ?? "unknown"} / {data?.provenance?.mode ?? "pending"}
            </span>
            <span className="status-pill">
              <AlertTriangle size={16} />
              排除 {exclusions.length || data?.exclusions_count || 0} 檔
            </span>
            {maskedCount > 0 ? (
              <span className="status-pill">
                <Sparkles size={16} />
                {maskedCount} 檔已遮罩
              </span>
            ) : null}
          </div>

          <CandidateList candidates={visibleCandidates} riskProfile={riskProfile} />
          <ExclusionList exclusions={exclusions.length ? exclusions : data?.exclusions_preview ?? []} total={data?.exclusions_count ?? 0} />
        </section>

        <section id="strategy" className="section">
          <div className="section-heading">
            <div>
              <h2>策略與風控</h2>
              <p>本次清單使用 run snapshot；下方表單儲存後套用到下一次篩選 run，方便通知與回測重現。</p>
            </div>
          </div>
          {draftRule ? <StrategyForm rule={draftRule} onChange={setDraftRule} /> : <div className="empty-state">策略設定尚未載入。</div>}
          <RiskProfileForm profile={draftRiskProfile} onChange={setDraftRiskProfile} />
          <label className="field" style={{ marginTop: 12 }}>
            <span>分享/教學備註</span>
            <input value={teacherNote} onChange={(event) => setTeacherNote(event.target.value)} />
          </label>
          <div className="actions">
            <button className="button" type="button" onClick={handleSaveSettings} disabled={!draftRule}>
              <Save size={18} />
              儲存設定
            </button>
            <span className="toast">{status}</span>
          </div>
        </section>

        <section id="notifications" className="section">
          <div className="section-heading">
            <div>
              <h2>通知測試</h2>
              <p>Email、LINE Official Account 與 Web Push 會在正式串接前保持展示模式，不會回報假送達。</p>
            </div>
          </div>
          <div className="strategy-grid">
            <label className="field">
              <span>通知通道</span>
              <select value={channel} onChange={(event) => setChannel(event.target.value)}>
                <option value="email">Email</option>
                <option value="line">LINE Messaging API</option>
                <option value="web_push">Web Push</option>
              </select>
            </label>
            <label className="field">
              <span>目的地</span>
              <input value={destination} onChange={(event) => setDestination(event.target.value)} />
            </label>
          </div>
          <div className="actions">
            <button className="button" type="button" onClick={handleNotificationTest}>
              <Mail size={18} />
              測試通知
            </button>
          </div>
        </section>

        <section id="history" className="section">
          <div className="section-heading">
            <div>
              <h2>紀錄與回測</h2>
              <p>{backtest?.methodology_notice ?? "回測資料尚未載入。"}</p>
            </div>
          </div>
          <div className="history-list">
            {historyRows.map((row) => (
              <div className="history-item" key={row.day}>
                <strong>{row.day}</strong>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${row.coverage}%` }} />
                </div>
                <span>{row.count} 檔</span>
              </div>
            ))}
          </div>
          {backtest ? <BacktestRows backtest={backtest} /> : null}
        </section>

        <section id="account" className="section">
          <div className="section-heading">
            <div>
              <h2>帳號與訂閱</h2>
              <p>付費流程需等正式資料授權、會員權限、ECPay webhook 與法務條款全部完成後才開放。</p>
            </div>
          </div>
          <div className="data-banner">
            <AlertTriangle size={18} />
            <span>目前是 demo/not_licensed 狀態，不能販售即時推播或完整商用服務。</span>
          </div>
          <div className="actions">
            <button className="button" type="button" onClick={handleCheckout}>
              <CreditCard size={18} />
              {data?.provenance?.license_status === "licensed" ? "NT$499/月" : "付費流程鎖定"}
            </button>
            <button className="button secondary" type="button" onClick={() => setStatus("付費名單需登入與授權後才會解除遮罩。")}>
              <Smartphone size={18} />
              付費名單需登入
            </button>
          </div>
        </section>
      </main>
      <SidePanel data={data} candidateCount={visibleCandidates.length} avgMatch={avgMatch} plan={plan} riskProfile={riskProfile} />
      <MobileNav />
    </div>
  );
}

function DesktopRail() {
  return (
    <nav className="rail" aria-label="主要導覽">
      <div className="brand-mark">13</div>
      {navItems.map((item) => {
        const Icon = item.icon;
        return (
          <a className="rail-link" href={item.href} key={item.href} title={item.label} aria-label={item.label}>
            <Icon size={22} />
          </a>
        );
      })}
    </nav>
  );
}

function MobileNav() {
  return (
    <nav className="mobile-nav" aria-label="手機導覽">
      {navItems.map((item) => {
        const Icon = item.icon;
        return (
          <a href={item.href} key={item.href} title={item.label} aria-label={item.label}>
            <Icon size={21} />
          </a>
        );
      })}
    </nav>
  );
}

function PlanSwitch({ plan, onLocked }: { plan: PlanCode; onLocked: () => void }) {
  return (
    <div className="plan-switch" aria-label="方案狀態">
      <button className={plan === "free" ? "active" : ""} type="button">
        免費
      </button>
      <button type="button" onClick={onLocked} title="付費版尚未開放">
        <Lock size={15} />
        付費
      </button>
    </div>
  );
}

function CandidateList({
  candidates,
  riskProfile
}: {
  candidates: CandidateStock[];
  riskProfile: RiskProfile;
}) {
  if (!candidates.length) {
    return <div className="empty-state">目前沒有候選股，或資料尚未完成載入。</div>;
  }

  return (
    <div className="candidate-list">
      {candidates.map((candidate) => {
        const position = estimatePosition(candidate, riskProfile);
        return (
          <article className={`candidate-row ${candidate.masked ? "masked" : ""}`} key={`${candidate.symbol}-${candidate.name}`}>
            <div className="stock-name">
              <strong>{candidate.name}</strong>
              <span>{candidate.symbol}</span>
            </div>
            <Metric label="分數" value={candidate.match_score.toFixed(1)} className="match-score" />
            <Metric label="漲幅" value={`${candidate.pct_change.toFixed(2)}%`} />
            <Metric label="量比" value={`${candidate.volume_intensity.toFixed(2)}x`} />
            <Metric label="換手" value={`${candidate.turnover_rate.toFixed(2)}%`} />
            <Metric label="VWAP" value={`${Math.round(candidate.vwap_above_ratio * 100)}%`} />
            <div className="reason-list">
              <p className={`risk risk-${candidate.risk_level}`}>
                風險 {riskLabel(candidate.risk_level)} / 單檔上限 {formatMoney(position.budget)} / 估 {formatQuantity(position, riskProfile)}
              </p>
              <p>
                停損參考 {candidate.stop_loss_reference_pct}% + 滑價 {riskProfile.slippage_buffer_pct}% / 單筆風險約 {formatMoney(position.riskAmount)}
              </p>
              <p>
                成交金額 {candidate.liquidity_twd_million.toFixed(0)} 百萬 / 距漲停 {candidate.distance_to_limit_up_pct.toFixed(2)}% / 高點回落 {candidate.intraday_pullback_pct.toFixed(2)}% / 尾段 {candidate.late_session_change_pct.toFixed(2)}%
              </p>
              {candidate.reasons.slice(0, 2).map((reason) => (
                <p key={reason}>{reason}</p>
              ))}
              {[...candidate.risk_notes, ...candidate.warnings].map((note) => (
                <p className="warning" key={note}>
                  {note}
                </p>
              ))}
            </div>
          </article>
        );
      })}
    </div>
  );
}

function QuickSummary({
  candidates,
  data
}: {
  candidates: CandidateStock[];
  data: TodayResponse | null;
}) {
  if (!candidates.length) return null;
  return (
    <div className="quick-summary">
      <div>
        <strong>今日快覽</strong>
        <span>{data?.provenance?.mode ?? "pending"} / {data?.provenance?.license_status ?? "unknown"}</span>
      </div>
      {candidates.slice(0, 3).map((candidate) => (
        <div className="quick-row" key={`quick-${candidate.symbol}`}>
          <span>{candidate.symbol} {candidate.name}</span>
          <strong>{candidate.match_score.toFixed(1)}</strong>
          <em>{riskLabel(candidate.risk_level)}風險</em>
        </div>
      ))}
    </div>
  );
}

function ExclusionList({ exclusions, total }: { exclusions: ScreenedOutStock[]; total: number }) {
  if (!exclusions.length) return null;
  return (
    <div className="exclusion-list">
      <h3>完整排除清單 {total ? `(${exclusions.length}/${total})` : ""}</h3>
      {exclusions.map((stock) => (
        <div className="exclusion-row" key={stock.symbol}>
          <strong>{stock.symbol} {stock.name}</strong>
          <span>{stock.failed_conditions.join(" / ")}</span>
        </div>
      ))}
    </div>
  );
}

function BacktestRows({ backtest }: { backtest: BacktestResponse }) {
  return (
    <>
      <div className="backtest-grid">
        {backtest.rows.map((row) => (
          <div className="field" key={row.window}>
            <label>{row.window} 風險區間</label>
            <strong>{row.candidate_days} / {row.sample_days} 個交易日有候選</strong>
            <span>中位隔日振幅 {row.median_next_day_range_pct}% / 最大不利偏移 {row.max_adverse_excursion_pct}%</span>
          </div>
        ))}
      </div>
      <div className="exclusion-list">
        <h3>逐日樣本</h3>
        {backtest.daily.slice(0, 4).map((day) => (
          <div className="exclusion-row" key={day.run_date}>
            <strong>{day.run_date}</strong>
            <span>
              候選 {day.candidate_count} / 排除 {day.excluded_count} / {day.data_version}
            </span>
          </div>
        ))}
      </div>
    </>
  );
}

function Metric({ label, value, className = "" }: { label: string; value: string; className?: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong className={className}>{value}</strong>
    </div>
  );
}

function StrategyForm({
  rule,
  onChange
}: {
  rule: ScreeningRule;
  onChange: (rule: ScreeningRule) => void;
}) {
  const fields: Array<{ key: keyof ScreeningRule; label: string; step: string }> = [
    { key: "min_pct_change", label: "最低漲幅 %", step: "0.1" },
    { key: "max_pct_change", label: "最高漲幅 %", step: "0.1" },
    { key: "min_volume_intensity", label: "最低成交強度量比", step: "0.1" },
    { key: "min_turnover_rate", label: "最低換手率 %", step: "0.1" },
    { key: "max_turnover_rate", label: "最高換手率 %", step: "0.1" },
    { key: "min_market_cap_billion", label: "最低市值 億", step: "10" },
    { key: "max_market_cap_billion", label: "最高市值 億", step: "10" },
    { key: "limit_up_lookback_days", label: "漲停回看天數", step: "1" },
    { key: "min_vwap_above_ratio", label: "VWAP 上方比例", step: "0.05" },
    { key: "vwap_reclaim_bars", label: "跌破後站回 K 數", step: "1" },
    { key: "vwap_tolerance_pct", label: "VWAP 容忍 %", step: "0.05" }
  ];

  return (
    <div className="strategy-grid">
      {fields.map((field) => (
        <label className="field" key={field.key}>
          <span>{field.label}</span>
          <input
            type="number"
            step={field.step}
            value={String(rule[field.key])}
            onChange={(event) =>
              onChange({
                ...rule,
                [field.key]: Number(event.target.value)
              })
            }
          />
        </label>
      ))}
    </div>
  );
}

function RiskProfileForm({
  profile,
  onChange
}: {
  profile: RiskProfile;
  onChange: (profile: RiskProfile) => void;
}) {
  return (
    <div className="risk-control">
      <h3>資金控管</h3>
      <div className="strategy-grid">
        <label className="field">
          <span>模式</span>
          <select value={profile.mode} onChange={(event) => onChange({ ...profile, mode: event.target.value as RiskProfile["mode"] })}>
            <option value="conservative">保守</option>
            <option value="balanced">一般</option>
            <option value="aggressive">積極</option>
          </select>
        </label>
        <label className="field">
          <span>帳戶資金 TWD</span>
          <input type="number" step="10000" value={profile.account_capital_twd} onChange={(event) => onChange({ ...profile, account_capital_twd: Number(event.target.value) })} />
        </label>
        <label className="field">
          <span>單筆最大風險 %</span>
          <input type="number" step="0.1" value={profile.max_trade_risk_pct} onChange={(event) => onChange({ ...profile, max_trade_risk_pct: Number(event.target.value) })} />
        </label>
        <label className="field">
          <span>單日最大風險 %</span>
          <input type="number" step="0.1" value={profile.max_daily_risk_pct} onChange={(event) => onChange({ ...profile, max_daily_risk_pct: Number(event.target.value) })} />
        </label>
        <label className="field">
          <span>最多持有檔數</span>
          <input type="number" step="1" value={profile.max_holdings} onChange={(event) => onChange({ ...profile, max_holdings: Number(event.target.value) })} />
        </label>
        <label className="field">
          <span>最低成交金額 百萬</span>
          <input type="number" step="10" value={profile.min_liquidity_twd_million} onChange={(event) => onChange({ ...profile, min_liquidity_twd_million: Number(event.target.value) })} />
        </label>
        <label className="field">
          <span>滑價緩衝 %</span>
          <input type="number" step="0.05" value={profile.slippage_buffer_pct} onChange={(event) => onChange({ ...profile, slippage_buffer_pct: Number(event.target.value) })} />
        </label>
        <label className="field">
          <span>每張股數</span>
          <input type="number" step="100" value={profile.lot_size} onChange={(event) => onChange({ ...profile, lot_size: Number(event.target.value) })} />
        </label>
      </div>
    </div>
  );
}

function SidePanel({
  data,
  candidateCount,
  avgMatch,
  plan,
  riskProfile
}: {
  data: TodayResponse | null;
  candidateCount: number;
  avgMatch: number;
  plan: PlanCode;
  riskProfile: RiskProfile;
}) {
  return (
    <aside className="side-panel">
      <div className="side-block">
        <h2>總覽</h2>
        <div className="kpi-stack">
          <div className="kpi">
            <span>今日候選</span>
            <strong>{candidateCount}</strong>
          </div>
          <div className="kpi">
            <span>平均分數</span>
            <strong>{avgMatch}</strong>
          </div>
          <div className="kpi">
            <span>方案</span>
            <strong>{plan === "pro" ? "Pro" : "Free"}</strong>
          </div>
        </div>
      </div>
      <div className="side-block">
        <h2>資料狀態</h2>
        <p className="notice">
          {data?.provenance
            ? `${data.provenance.provider} / ${data.provenance.license_status} / 可再散布：${data.provenance.can_redistribute ? "是" : "否"}`
            : "資料尚未載入"}
        </p>
      </div>
      <div className="side-block">
        <h2>風控設定</h2>
        <p className="notice">
          帳戶 {formatMoney(riskProfile.account_capital_twd)}，單筆 {riskProfile.max_trade_risk_pct}% ，單日 {riskProfile.max_daily_risk_pct}% ，最多 {riskProfile.max_holdings} 檔。
        </p>
      </div>
      <div className="side-block">
        <h2>風險聲明</h2>
        <p className="notice">{data?.risk_notice ?? "候選清單僅為條件整理，使用者需自行控管風險。"}</p>
      </div>
    </aside>
  );
}

function estimatePosition(candidate: CandidateStock, profile: RiskProfile) {
  const maxByAllocation = profile.account_capital_twd * (candidate.max_position_pct / 100);
  const maxRiskAmount = profile.account_capital_twd * (profile.max_trade_risk_pct / 100);
  const stopRiskPct = Math.max((candidate.stop_loss_reference_pct + profile.slippage_buffer_pct) / 100, 0.001);
  const maxByStop = maxRiskAmount / stopRiskPct;
  const maxByHoldings = profile.account_capital_twd / Math.max(profile.max_holdings, 1);
  const maxByLiquidity = candidate.liquidity_twd_million * 1_000_000 * 0.02;
  const liquidityPenalty = candidate.liquidity_twd_million < profile.min_liquidity_twd_million ? 0.5 : 1;
  const budget = Math.floor(Math.min(maxByAllocation, maxByStop, maxByHoldings, maxByLiquidity) * liquidityPenalty);
  const lotValue = Math.max(candidate.reference_price * profile.lot_size, 1);
  const lots = Math.max(0, Math.floor(budget / lotValue));
  const shares = Math.max(0, Math.floor(budget / Math.max(candidate.reference_price, 1)));
  return {
    budget,
    shares,
    lots,
    riskAmount: Math.floor(budget * stopRiskPct)
  };
}

function formatQuantity(position: ReturnType<typeof estimatePosition>, profile: RiskProfile) {
  const oddShares = position.shares % Math.max(profile.lot_size, 1);
  if (position.lots > 0 && oddShares > 0) {
    return `${position.lots} 張 + ${oddShares.toLocaleString("zh-TW")} 股`;
  }
  if (position.lots > 0) {
    return `${position.lots} 張`;
  }
  return `${position.shares.toLocaleString("zh-TW")} 股`;
}

function formatMoney(value: number) {
  return `NT$${Math.max(0, Math.floor(value)).toLocaleString("zh-TW")}`;
}

function formatTime(value: string | undefined) {
  if (!value) return "pending";
  return new Intl.DateTimeFormat("zh-TW", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Taipei"
  }).format(new Date(value));
}

function riskLabel(level: CandidateStock["risk_level"]) {
  if (level === "low") return "低";
  if (level === "medium") return "中";
  return "高";
}

function buildShareText(
  candidates: CandidateStock[],
  data: TodayResponse | null,
  riskProfile: RiskProfile,
  teacherNote: string
) {
  const lines = candidates.slice(0, 3).map((candidate) => {
    const position = estimatePosition(candidate, riskProfile);
    return `${candidate.symbol} ${candidate.name}｜分數 ${candidate.match_score.toFixed(1)}｜風險 ${riskLabel(candidate.risk_level)}｜估 ${formatQuantity(position, riskProfile)}｜停損參考 ${candidate.stop_loss_reference_pct}%`;
  });
  return [
    "13:00 條件篩選摘要",
    `資料版本：${data?.run.data_version ?? "unknown"}`,
    `資料來源：${data?.provenance?.provider ?? "unknown"} / ${data?.provenance?.license_status ?? "unknown"}`,
    `風控：單筆 ${riskProfile.max_trade_risk_pct}%、單日 ${riskProfile.max_daily_risk_pct}%、最多 ${riskProfile.max_holdings} 檔`,
    ...lines,
    teacherNote,
    "聲明：僅為條件篩選與資料整理，不提供投資建議或自動下單。"
  ].join("\n");
}
