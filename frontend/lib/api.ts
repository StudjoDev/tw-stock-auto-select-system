import type {
  BacktestResponse,
  PlanCode,
  RiskProfile,
  ScreenedOutStock,
  ScreeningRule,
  TodayResponse
} from "../types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
const STATIC_TODAY_DATA = `${BASE_PATH || ""}${BASE_PATH.endsWith("/") ? "" : "/"}data/today.json`;
const STATIC_MODE = process.env.NEXT_PUBLIC_STATIC_DATA === "1";

type StaticTodayResponse = TodayResponse & { exclusions?: ScreenedOutStock[] };

let cachedStaticToday: Promise<StaticTodayResponse> | null = null;

function hasWindowStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function staticRuleKey() {
  return "tw-stock-static-default-rule";
}

function staticProfileKey() {
  return "tw-stock-static-default-risk-profile";
}

function loadStaticPayload() {
  if (!cachedStaticToday) {
    cachedStaticToday = (async () => {
      const response = await fetch(STATIC_TODAY_DATA, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("Static data not available");
      }
      return (await response.json()) as StaticTodayResponse;
    })();
  }
  return cachedStaticToday;
}

export async function fetchToday(plan: PlanCode): Promise<TodayResponse> {
  if (STATIC_MODE) {
    const today = await loadStaticPayload();
    return {
      ...today,
      plan,
      candidates:
        plan === "pro" ? today.candidates : today.candidates.map((candidate, index) => ({ ...candidate, ...(index >= 2 ? {
          symbol: `${candidate.symbol.slice(0, 2)}**`,
          name: "待補（靜態）",
          reasons: ["此為靜態展示結果，完整資料僅在後台更新後呈現"],
          risk_notes: ["風險提示略縮（靜態模式）"],
          risk_flags: ["masked", ...candidate.risk_flags],
          masked: true
        } : {}) })),
    };
  }

  const response = await fetch(`${API_BASE_URL}/api/today/runs?plan=${plan}`, {
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`API returned ${response.status}`);
  }
  return (await response.json()) as TodayResponse;
}

export async function fetchRunExclusions(runId: string): Promise<ScreenedOutStock[]> {
  if (STATIC_MODE) {
    const today = await loadStaticPayload();
    return today.exclusions ?? today.exclusions_preview ?? [];
  }

  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}/exclusions`, {
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error("Unable to fetch exclusions");
  }
  return (await response.json()) as ScreenedOutStock[];
}

export async function fetchDefaultRule(): Promise<ScreeningRule> {
  if (STATIC_MODE) {
    const today = await loadStaticPayload();
    const stored = hasWindowStorage()
      ? window.localStorage.getItem(staticRuleKey())
      : null;
    if (stored) {
      return (JSON.parse(stored) as ScreeningRule);
    }
    return today.rule;
  }

  const response = await fetch(`${API_BASE_URL}/api/rules/default`, {
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error("Unable to fetch default rule");
  }
  return (await response.json()) as ScreeningRule;
}

export async function fetchDefaultRiskProfile(): Promise<RiskProfile> {
  if (STATIC_MODE) {
    const today = await loadStaticPayload();
    const stored = hasWindowStorage()
      ? window.localStorage.getItem(staticProfileKey())
      : null;
    if (stored) {
      return (JSON.parse(stored) as RiskProfile);
    }
    return today.risk_profile;
  }

  const response = await fetch(`${API_BASE_URL}/api/risk-profiles/default`, {
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error("Unable to fetch risk profile");
  }
  return (await response.json()) as RiskProfile;
}

export async function saveRule(rule: ScreeningRule): Promise<ScreeningRule> {
  if (STATIC_MODE && hasWindowStorage()) {
    window.localStorage.setItem(staticRuleKey(), JSON.stringify(rule));
    return rule;
  }

  const response = await fetch(`${API_BASE_URL}/api/rules/${rule.id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(rule)
  });
  if (!response.ok) {
    throw new Error("Unable to save rule");
  }
  return (await response.json()) as ScreeningRule;
}

export async function saveRiskProfile(profile: RiskProfile): Promise<RiskProfile> {
  if (STATIC_MODE && hasWindowStorage()) {
    window.localStorage.setItem(staticProfileKey(), JSON.stringify(profile));
    return profile;
  }

  const response = await fetch(`${API_BASE_URL}/api/risk-profiles/default`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(profile)
  });
  if (!response.ok) {
    throw new Error("Unable to save risk profile");
  }
  return (await response.json()) as RiskProfile;
}

export async function sendTestNotification(channel: string, destination: string) {
  if (STATIC_MODE) {
    return {
      delivered: false,
      message: "Static demo mode: 通知只在本機測試顯示，尚未連接服務"
    };
  }

  const response = await fetch(`${API_BASE_URL}/api/notifications/test`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ channel, destination })
  });
  if (!response.ok) {
    throw new Error("Unable to send notification");
  }
  return (await response.json()) as { delivered: boolean; message: string };
}

export async function createCheckout(plan: "pro_monthly" | "pro_yearly") {
  if (STATIC_MODE) {
    return {
      id: "static-checkout-disabled",
      checkout_url: "#",
      amount_twd: 0
    };
  }

  const response = await fetch(`${API_BASE_URL}/api/billing/checkout`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ plan })
  });
  if (!response.ok) {
    throw new Error("Unable to create checkout");
  }
  return (await response.json()) as { id: string; checkout_url: string; amount_twd: number };
}

export async function createBacktest(tradingDays = 60): Promise<BacktestResponse> {
  if (STATIC_MODE) {
    const today = await fetchToday("free");
    return {
      rule_id: today.rule.id,
      data_mode: "static_demo",
      trading_days: tradingDays,
      methodology_notice: "Static demo mode: history not available in static build.",
      rows: [],
      daily: []
    };
  }

  const response = await fetch(`${API_BASE_URL}/api/backtests`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ trading_days: tradingDays })
  });
  if (!response.ok) {
    throw new Error("Unable to create backtest");
  }
  return (await response.json()) as BacktestResponse;
}

export function demoToday(plan: PlanCode): TodayResponse {
  const masked = plan === "free";
  return {
    plan,
    run: {
      id: "offline-demo",
      rule_id: "default-rule",
      run_date: "2026-06-25",
      status: "completed",
      data_version: "offline-demo-13:00",
      started_at: "2026-06-25T05:00:00Z",
      completed_at: "2026-06-25T05:00:08Z",
      rule_snapshot: {},
      risk_profile_snapshot: {},
      input_snapshot_hash: "offline-demo",
      universe_hash: "offline-demo",
      risk_profile_hash: "offline-demo",
      score_formula_version: "match-score-v1",
      error_message: null
    },
    rule: {
      id: "default-rule",
      name: "13:00 盤中篩選",
      min_pct_change: 3,
      max_pct_change: 5,
      min_volume_intensity: 1,
      min_turnover_rate: 5,
      max_turnover_rate: 10,
      min_market_cap_billion: 200,
      max_market_cap_billion: 1000,
      limit_up_lookback_days: 20,
      min_vwap_above_ratio: 0.8,
      vwap_reclaim_bars: 3,
      vwap_tolerance_pct: 0.2,
      notification_time: "13:00:00",
      enabled: true
    },
    risk_profile: {
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
    },
    provenance: {
      ingestion_batch_id: "offline-demo",
      provider: "offline",
      mode: "offline-demo",
      license_status: "unknown",
      can_redistribute: false,
      cutoff_time: "2026-06-25T13:00:00+08:00",
      generated_at: "2026-06-25T13:00:08+08:00",
      data_version: "offline-demo",
      raw_snapshot_hash: "offline-demo",
      raw_storage_pointer: "offline://demo",
      provider_version: "offline-demo",
      corporate_action_version: "offline-demo",
      calendar_version: "offline-demo",
      symbol_universe_hash: "offline-demo",
      bar_interval: "1m-demo",
      usage_notice: "離線展示樣本，不代表正式行情資料。"
    },
    candidates: [
      {
        symbol: "3037",
        name: "欣興",
        match_score: 92.4,
        reference_price: 170.8,
        pct_change: 4.15,
        volume_intensity: 1.7,
        turnover_rate: 8.8,
        market_cap_billion: 262,
        had_limit_up_recently: true,
        vwap_above_ratio: 0.9,
        vwap_reclaimed_within_bars: true,
        vwap_breach_count: 1,
        vwap_worst_distance_pct: -0.18,
        risk_level: "medium",
        risk_notes: ["換手率偏高，部位需比低風險檔更保守"],
        risk_flags: ["turnover-rate-high"],
        liquidity_twd_million: 1980,
        distance_to_limit_up_pct: 5.6,
        intraday_pullback_pct: 0.4,
        late_session_change_pct: 0.35,
        stop_loss_reference_pct: 1.5,
        max_position_pct: 5,
        reasons: ["漲幅 4.15% 落在設定區間", "成交強度量比 1.70 大於門檻", "VWAP 穩定度 90%"],
        warnings: [],
        masked: false
      },
      {
        symbol: "2345",
        name: "智邦",
        match_score: 89.6,
        reference_price: 852,
        pct_change: 3.9,
        volume_intensity: 1.36,
        turnover_rate: 7.2,
        market_cap_billion: 472,
        had_limit_up_recently: true,
        vwap_above_ratio: 1,
        vwap_reclaimed_within_bars: true,
        vwap_breach_count: 0,
        vwap_worst_distance_pct: 0.12,
        risk_level: "low",
        risk_notes: ["分時結構穩定，但仍需依照個人風控限制使用"],
        risk_flags: [],
        liquidity_twd_million: 1480,
        distance_to_limit_up_pct: 5.9,
        intraday_pullback_pct: 0.25,
        late_session_change_pct: 0.47,
        stop_loss_reference_pct: 1.5,
        max_position_pct: 8,
        reasons: ["市值符合中型股範圍", "近 20 天內有漲停紀錄", "全天多數時間站在 VWAP 容忍區上方"],
        warnings: [],
        masked: false
      },
      {
        symbol: masked ? "64**" : "6446",
        name: masked ? "付費版揭露" : "藥華藥",
        match_score: 84.2,
        reference_price: 631,
        pct_change: 3.44,
        volume_intensity: 1.21,
        turnover_rate: 5.4,
        market_cap_billion: 214,
        had_limit_up_recently: true,
        vwap_above_ratio: 0.9,
        vwap_reclaimed_within_bars: true,
        vwap_breach_count: 1,
        vwap_worst_distance_pct: -0.22,
        risk_level: "medium",
        risk_notes: masked ? ["升級後可查看完整風控註記"] : ["成交金額較集中，需確認委買委賣深度"],
        risk_flags: masked ? ["masked"] : ["source-warning"],
        liquidity_twd_million: 510,
        distance_to_limit_up_pct: 6.28,
        intraday_pullback_pct: 0.35,
        late_session_change_pct: 0.8,
        stop_loss_reference_pct: 1.5,
        max_position_pct: 5,
        reasons: masked ? ["升級後可查看完整入選原因"] : ["VWAP 條件通過"],
        warnings: [],
        masked
      }
    ],
    exclusions_preview: [
      {
        symbol: "2330",
        name: "台積電",
        primary_reason: "市值不在設定區間",
        failed_conditions: ["市值不在 200-1000 億", "換手率不在 5-10%"],
        pct_change: 3.61,
        volume_intensity: 1.16,
        turnover_rate: 0.8,
        market_cap_billion: 38000
      }
    ],
    exclusions_count: 1,
    upgrade: {
      title: "解鎖完整 13:00 名單、策略參數與通知工作流",
      price: "NT$499/月",
      cta: "申請付費權限"
    },
    compliance_notice: "本服務僅提供條件篩選工具與資料整理，不提供投資建議、績效承諾或自動下單。",
    risk_notice: "系統會顯示風險因子、停損參考與部位上限；實際操作仍需使用者自行判斷並控管資金。",
    data_notice: "離線展示樣本，不代表正式行情資料。"
  };
}
