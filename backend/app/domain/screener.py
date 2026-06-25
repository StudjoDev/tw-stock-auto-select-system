from __future__ import annotations

from datetime import date

from app.domain.models import (
    CandidateStock,
    ScreenedOutStock,
    ScreeningOutput,
    ScreeningRule,
    StockSnapshot,
    VwapEvaluation,
)


def pct_change(snapshot: StockSnapshot) -> float:
    if snapshot.previous_close <= 0:
        return 0.0
    return ((snapshot.current_price - snapshot.previous_close) / snapshot.previous_close) * 100


def volume_intensity(snapshot: StockSnapshot) -> float:
    if snapshot.avg_5d_volume <= 0:
        return 0.0
    return snapshot.intraday_volume / snapshot.avg_5d_volume


def liquidity_twd_million(snapshot: StockSnapshot) -> float:
    return sum(max(bar.turnover, 0) for bar in snapshot.bars) / 1_000_000


def distance_to_limit_up_pct(snapshot: StockSnapshot) -> float:
    if snapshot.previous_close <= 0 or snapshot.current_price <= 0:
        return 0.0
    limit_up_price = snapshot.previous_close * 1.1
    return ((limit_up_price - snapshot.current_price) / snapshot.current_price) * 100


def intraday_pullback_pct(snapshot: StockSnapshot) -> float:
    prices = [snapshot.current_price, *(bar.high for bar in snapshot.bars)]
    high_price = max(prices)
    if high_price <= 0:
        return 0.0
    return ((high_price - snapshot.current_price) / high_price) * 100


def late_session_change_pct(snapshot: StockSnapshot) -> float:
    if len(snapshot.bars) < 3:
        return 0.0
    reference_close = snapshot.bars[-3].close
    if reference_close <= 0:
        return 0.0
    return ((snapshot.bars[-1].close - reference_close) / reference_close) * 100


def had_limit_up_recently(snapshot: StockSnapshot, run_date: date, lookback_days: int) -> bool:
    return any(0 <= (run_date - limit_date).days <= lookback_days for limit_date in snapshot.limit_up_dates)


def evaluate_vwap(snapshot: StockSnapshot, rule: ScreeningRule) -> VwapEvaluation:
    if not snapshot.bars:
        return VwapEvaluation(
            above_ratio=0,
            reclaimed_within_bars=False,
            breach_count=0,
            worst_distance_pct=0,
            reason="沒有足夠分鐘資料可計算 VWAP",
        )

    cumulative_volume = 0
    cumulative_turnover = 0.0
    closes: list[float] = []
    vwaps: list[float] = []

    for bar in snapshot.bars:
        cumulative_volume += max(bar.volume, 0)
        cumulative_turnover += max(bar.turnover, 0)
        vwap = bar.close if cumulative_volume <= 0 else cumulative_turnover / cumulative_volume
        closes.append(bar.close)
        vwaps.append(vwap)

    tolerance_multiplier = 1 - (rule.vwap_tolerance_pct / 100)
    above_flags = [close >= vwap * tolerance_multiplier for close, vwap in zip(closes, vwaps)]
    above_ratio = sum(above_flags) / len(above_flags)

    breach_indexes = [index for index, is_above in enumerate(above_flags) if not is_above]
    reclaimed = True
    for index in breach_indexes:
        end = min(index + rule.vwap_reclaim_bars + 1, len(closes))
        window = range(index + 1, end)
        if not any(closes[next_index] >= vwaps[next_index] * tolerance_multiplier for next_index in window):
            reclaimed = False
            break

    distances = [((close - vwap) / vwap) * 100 if vwap else 0 for close, vwap in zip(closes, vwaps)]
    worst_distance_pct = min(distances)
    reason = (
        f"{above_ratio:.0%} 分鐘 K 收在 VWAP 容忍區上方，"
        f"跌破次數 {len(breach_indexes)}，"
        f"{'皆在規則內站回' if reclaimed else '有跌破後未在規則內站回'}"
    )

    return VwapEvaluation(
        above_ratio=above_ratio,
        reclaimed_within_bars=reclaimed,
        breach_count=len(breach_indexes),
        worst_distance_pct=worst_distance_pct,
        reason=reason,
    )


def screen_market(
    snapshots: list[StockSnapshot],
    rule: ScreeningRule,
    run_date: date,
) -> list[CandidateStock]:
    return screen_market_with_exclusions(snapshots, rule, run_date).candidates


def screen_market_with_exclusions(
    snapshots: list[StockSnapshot],
    rule: ScreeningRule,
    run_date: date,
) -> ScreeningOutput:
    candidates: list[CandidateStock] = []
    exclusions: list[ScreenedOutStock] = []

    for snapshot in snapshots:
        change = pct_change(snapshot)
        intensity = volume_intensity(snapshot)
        liquidity = liquidity_twd_million(snapshot)
        limit_up_distance = distance_to_limit_up_pct(snapshot)
        pullback = intraday_pullback_pct(snapshot)
        late_change = late_session_change_pct(snapshot)
        recent_limit_up = had_limit_up_recently(snapshot, run_date, rule.limit_up_lookback_days)
        vwap = evaluate_vwap(snapshot, rule)
        reasons: list[str] = []
        warnings = list(snapshot.warnings)
        failed_conditions: list[str] = []

        if not (rule.min_pct_change <= change <= rule.max_pct_change):
            failed_conditions.append(
                f"漲幅 {change:.2f}% 不在 {rule.min_pct_change:.1f}-{rule.max_pct_change:.1f}%"
            )
        else:
            reasons.append(f"漲幅 {change:.2f}% 落在設定區間")

        if intensity <= rule.min_volume_intensity:
            failed_conditions.append(f"成交強度量比 {intensity:.2f} 未大於 {rule.min_volume_intensity:.2f}")
        else:
            reasons.append(f"成交強度量比 {intensity:.2f} 大於 5 日均量門檻")

        if not (rule.min_turnover_rate <= snapshot.turnover_rate <= rule.max_turnover_rate):
            failed_conditions.append(
                f"換手率 {snapshot.turnover_rate:.2f}% 不在 "
                f"{rule.min_turnover_rate:.1f}-{rule.max_turnover_rate:.1f}%"
            )
        else:
            reasons.append(f"換手率 {snapshot.turnover_rate:.2f}% 落在設定區間")

        if not (rule.min_market_cap_billion <= snapshot.market_cap_billion <= rule.max_market_cap_billion):
            failed_conditions.append(
                f"市值 {snapshot.market_cap_billion:.0f} 億不在 "
                f"{rule.min_market_cap_billion:.0f}-{rule.max_market_cap_billion:.0f} 億"
            )
        else:
            reasons.append(f"市值 {snapshot.market_cap_billion:.0f} 億符合中型股範圍")

        if not recent_limit_up:
            failed_conditions.append(f"近 {rule.limit_up_lookback_days} 天內沒有漲停紀錄")
        else:
            reasons.append(f"近 {rule.limit_up_lookback_days} 天內有漲停紀錄")

        if vwap.above_ratio < rule.min_vwap_above_ratio or not vwap.reclaimed_within_bars:
            failed_conditions.append(
                f"VWAP 穩定度未通過：{vwap.reason}，最深距離 {vwap.worst_distance_pct:.2f}%"
            )
        else:
            reasons.append(vwap.reason)

        if failed_conditions:
            exclusions.append(
                ScreenedOutStock(
                    symbol=snapshot.symbol,
                    name=snapshot.name,
                    primary_reason=failed_conditions[0],
                    failed_conditions=failed_conditions,
                    pct_change=round(change, 2),
                    volume_intensity=round(intensity, 2),
                    turnover_rate=round(snapshot.turnover_rate, 2),
                    market_cap_billion=round(snapshot.market_cap_billion, 2),
                )
            )
            continue

        if vwap.worst_distance_pct < -(rule.vwap_tolerance_pct * 3):
            warnings.append(f"盤中曾低於 VWAP {abs(vwap.worst_distance_pct):.2f}%")

        risk_level, risk_notes, risk_flags = _risk_profile(
            change=change,
            intensity=intensity,
            turnover_rate=snapshot.turnover_rate,
            vwap=vwap,
            liquidity=liquidity,
            limit_up_distance=limit_up_distance,
            pullback=pullback,
            late_change=late_change,
            warnings=warnings,
        )
        candidates.append(
            CandidateStock(
                symbol=snapshot.symbol,
                name=snapshot.name,
                score=_score_candidate(change, intensity, snapshot.turnover_rate, vwap),
                reference_price=round(snapshot.current_price, 2),
                pct_change=round(change, 2),
                volume_intensity=round(intensity, 2),
                turnover_rate=round(snapshot.turnover_rate, 2),
                market_cap_billion=round(snapshot.market_cap_billion, 2),
                had_limit_up_recently=recent_limit_up,
                vwap_above_ratio=round(vwap.above_ratio, 4),
                vwap_reclaimed_within_bars=vwap.reclaimed_within_bars,
                vwap_breach_count=vwap.breach_count,
                vwap_worst_distance_pct=round(vwap.worst_distance_pct, 2),
                risk_level=risk_level,
                risk_notes=risk_notes,
                risk_flags=risk_flags,
                liquidity_twd_million=round(liquidity, 2),
                distance_to_limit_up_pct=round(limit_up_distance, 2),
                intraday_pullback_pct=round(pullback, 2),
                late_session_change_pct=round(late_change, 2),
                stop_loss_reference_pct=round(
                    max(1.5, abs(vwap.worst_distance_pct) + 1.0, pullback + 0.5),
                    2,
                ),
                max_position_pct=round(8 if risk_level == "low" else 5 if risk_level == "medium" else 3, 2),
                reasons=reasons,
                warnings=warnings,
            )
        )

    return ScreeningOutput(
        candidates=sorted(candidates, key=lambda candidate: candidate.score, reverse=True),
        exclusions=exclusions,
    )


def _score_candidate(
    change: float,
    intensity: float,
    turnover_rate: float,
    vwap: VwapEvaluation,
) -> float:
    vwap_score = min(vwap.above_ratio, 1) * 45
    intensity_score = min(intensity, 3) / 3 * 25
    turnover_score = max(0, 15 - abs(turnover_rate - 7.5) * 2)
    change_score = max(0, 15 - abs(change - 4.0) * 4)
    penalty = max(0, abs(vwap.worst_distance_pct) - 0.5) * 2
    return round(max(0, vwap_score + intensity_score + turnover_score + change_score - penalty), 2)


def _risk_profile(
    change: float,
    intensity: float,
    turnover_rate: float,
    vwap: VwapEvaluation,
    liquidity: float,
    limit_up_distance: float,
    pullback: float,
    late_change: float,
    warnings: list[str],
) -> tuple[str, list[str], list[str]]:
    risk_points = 0
    notes: list[str] = []
    flags: list[str] = []

    if change >= 4.6:
        risk_points += 1
        notes.append("漲幅接近區間上緣，避免用過大的部位追價")
        flags.append("price-change-near-upper-band")
    if intensity >= 2.2:
        risk_points += 1
        notes.append("量能加速偏高，隔日波動可能放大")
        flags.append("volume-acceleration-high")
    if turnover_rate >= 9:
        risk_points += 1
        notes.append("換手率接近上限，籌碼更容易快速翻動")
        flags.append("turnover-rate-high")
    if vwap.breach_count >= 2 or vwap.worst_distance_pct <= -0.8:
        risk_points += 1
        notes.append("VWAP 跌破次數或深度偏高")
        flags.append("vwap-breach-risk")
    if liquidity < 50:
        risk_points += 1
        notes.append("成交金額偏低，部位需要降級處理")
        flags.append("liquidity-thin")
    if limit_up_distance <= 2:
        risk_points += 1
        notes.append("距離漲停價太近，追價風險提高")
        flags.append("near-limit-up")
    if pullback >= 1.5:
        risk_points += 1
        notes.append("盤中高點回落幅度偏大，需觀察尾盤承接")
        flags.append("intraday-pullback")
    if late_change <= -0.5:
        risk_points += 1
        notes.append("尾段價格轉弱，不適合放大部位")
        flags.append("late-session-weakening")
    if warnings:
        flags.append("source-warning")

    if risk_points >= 2:
        return "high", notes, flags
    if risk_points == 1:
        return "medium", notes, flags
    return "low", ["分時結構穩定，但仍需依照個人風控限制使用"], flags
