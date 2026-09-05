"""
Entry / stop-loss / target calculation (spec section 6).

Deliberately rule-based on ATR and support/resistance rather than arbitrary
percentages, so every level has a stated technical justification
(`RiskLevels.methodology`) that gets surfaced in the alert and stored with
the signal for reproducibility. R:R targets are expressed as multiples of
the ACTUAL risk taken (entry-to-stop distance) - a standard, explainable
approach - with Target 1 upgraded to the nearest resistance/support level
when that level would itself provide at least 1R of reward.

This produces an analytical estimate, not a guaranteed outcome - see the
disclaimer rendered with every alert (app.alerts.formatter).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import Direction

# R-multiples used for targets when no better structural level is available
_T1_R_MULTIPLE = 1.5
_T2_R_MULTIPLE = 2.5
_T3_R_MULTIPLE = 4.0

_ENTRY_BUFFER_ATR_MULT = 0.05
_STOP_BUFFER_ATR_MULT = 0.25


@dataclass
class RiskLevels:
    entry: float
    stop_loss: float
    target_1: float
    target_2: float
    target_3: float
    risk_per_share: float
    reward_to_t1: float
    reward_to_t2: float
    reward_to_t3: float
    rr_t1: float
    rr_t2: float
    rr_t3: float
    methodology: str


def _round(x: float) -> float:
    return round(x, 4) if x < 10 else round(x, 2)


def calculate_risk_levels(
    direction: Direction,
    current_price: float,
    atr: float,
    pattern_low: float,
    pattern_high: float,
    support: float | None,
    resistance: float | None,
    already_broken_out: bool = False,
) -> RiskLevels:
    if atr is None or atr <= 0:
        atr = max(current_price * 0.01, 1e-4)  # graceful fallback if ATR unavailable

    if direction == Direction.BULLISH:
        entry = current_price if already_broken_out else max(current_price, pattern_high + _ENTRY_BUFFER_ATR_MULT * atr)
        structural_stop = support if (support is not None and support < entry) else None
        # prefer the TIGHTER of pattern-low/support (whichever sits closer to
        # entry) as the stop basis - it's still a genuine technical level, and
        # placing the stop needlessly far away wastes risk budget
        candidate_stop = max(pattern_low, structural_stop) if structural_stop is not None else pattern_low
        stop_loss = candidate_stop - _STOP_BUFFER_ATR_MULT * atr
        risk_per_share = max(entry - stop_loss, 1e-6)

        struct_target = resistance if (resistance is not None and resistance > entry) else None
        t1 = struct_target if (struct_target is not None and (struct_target - entry) >= risk_per_share) else entry + risk_per_share * _T1_R_MULTIPLE
        t2 = entry + risk_per_share * _T2_R_MULTIPLE
        t3 = entry + risk_per_share * _T3_R_MULTIPLE

        stop_desc = (
            f"nearest support (${structural_stop:.2f})" if structural_stop is not None else f"pattern low (${pattern_low:.2f})"
        )
        entry_desc = "current confirmed close (breakout already occurred)" if already_broken_out else f"pattern high (${pattern_high:.2f}) + {_ENTRY_BUFFER_ATR_MULT} ATR confirmation buffer"
        t1_desc = f"nearest resistance (${struct_target:.2f})" if struct_target is not None and t1 == struct_target else f"{_T1_R_MULTIPLE}R"

    elif direction == Direction.BEARISH:
        entry = current_price if already_broken_out else min(current_price, pattern_low - _ENTRY_BUFFER_ATR_MULT * atr)
        structural_stop = resistance if (resistance is not None and resistance > entry) else None
        # mirror of the bullish case: prefer the tighter (lower) of
        # pattern-high/resistance as the stop basis
        candidate_stop = min(pattern_high, structural_stop) if structural_stop is not None else pattern_high
        stop_loss = candidate_stop + _STOP_BUFFER_ATR_MULT * atr
        risk_per_share = max(stop_loss - entry, 1e-6)

        struct_target = support if (support is not None and support < entry) else None
        t1 = struct_target if (struct_target is not None and (entry - struct_target) >= risk_per_share) else entry - risk_per_share * _T1_R_MULTIPLE
        t2 = entry - risk_per_share * _T2_R_MULTIPLE
        t3 = entry - risk_per_share * _T3_R_MULTIPLE

        stop_desc = (
            f"nearest resistance (${structural_stop:.2f})" if structural_stop is not None else f"pattern high (${pattern_high:.2f})"
        )
        entry_desc = "current confirmed close (breakdown already occurred)" if already_broken_out else f"pattern low (${pattern_low:.2f}) - {_ENTRY_BUFFER_ATR_MULT} ATR confirmation buffer"
        t1_desc = f"nearest support (${struct_target:.2f})" if struct_target is not None and t1 == struct_target else f"{_T1_R_MULTIPLE}R"

    else:
        raise ValueError("Risk levels are only computed for BULLISH or BEARISH signals")

    reward_to_t1 = abs(t1 - entry)
    reward_to_t2 = abs(t2 - entry)
    reward_to_t3 = abs(t3 - entry)

    methodology = (
        f"Entry at {entry_desc}. Stop placed beyond {stop_desc} with a {_STOP_BUFFER_ATR_MULT} ATR buffer "
        f"(risk/share = ${risk_per_share:.2f}). Target 1 at {t1_desc}, Target 2 at {_T2_R_MULTIPLE}R, "
        f"Target 3 at {_T3_R_MULTIPLE}R, where R = risk/share. This is an analytical estimate based on "
        f"current volatility (ATR) and price structure, not a guaranteed outcome."
    )

    return RiskLevels(
        entry=_round(entry),
        stop_loss=_round(stop_loss),
        target_1=_round(t1),
        target_2=_round(t2),
        target_3=_round(t3),
        risk_per_share=_round(risk_per_share),
        reward_to_t1=_round(reward_to_t1),
        reward_to_t2=_round(reward_to_t2),
        reward_to_t3=_round(reward_to_t3),
        rr_t1=round(reward_to_t1 / risk_per_share, 2),
        rr_t2=round(reward_to_t2 / risk_per_share, 2),
        rr_t3=round(reward_to_t3 / risk_per_share, 2),
        methodology=methodology,
    )
