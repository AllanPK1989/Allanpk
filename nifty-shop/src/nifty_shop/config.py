"""Configuration for the RSI-Filtered Nifty Shop system.

Every <<CONFIGURE>> marker in the spec appears here exactly once. Items marked OPEN
carry a flagged default and are still awaiting a decision. The three rules the spec
never specified carry no usable default: they resolve to UNSPECIFIED and make
assert_rules_resolved raise, so the system refuses to trade on an invented rule.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

LIVE_ENV_VAR = "NIFTY_SHOP_ALLOW_LIVE"
UNSPECIFIED = "UNSPECIFIED"

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class ConfigError(Exception):
    """Base class for configuration refusals."""


class LiveModeNotPermittedError(ConfigError):
    """Live mode requested without every gate satisfied."""


class UnresolvedStrategyRuleError(ConfigError):
    """A rule the spec never specified is still UNSPECIFIED."""


class Mode(StrEnum):
    PAPER = "paper"
    LIVE = "live"


class TargetBasis(StrEnum):
    GROSS = "gross"
    NET = "net"


class EntryOrderType(StrEnum):
    LIMIT = "limit"
    MARKET = "market"


class PriceAboveNotional(StrEnum):
    SKIP = "skip"
    BUY_ONE_SHARE = "buy_one_share"


class R4Mode(StrEnum):
    REDUCE_TO_ONE = "reduce_to_one"
    REQUIRE_RSI_BELOW_30 = "require_rsi_below_30"
    HALT_NEW_ENTRIES = "halt_new_entries"


class EventScreenMode(StrEnum):
    ADVISORY_ONLY = "advisory_only"
    APPROVAL_REQUIRED = "approval_required"


class OnIndexRemoval(StrEnum):
    UNSPECIFIED = "UNSPECIFIED"
    EXIT_AT_EVENT = "exit_at_event"
    HOLD_TO_TRIGGERS = "hold_to_triggers"


class OnCashShortfall(StrEnum):
    UNSPECIFIED = "UNSPECIFIED"
    SKIP_BOTH = "skip_both"
    TAKE_TOP_RANKED = "take_top_ranked"


class OnExitPartialFill(StrEnum):
    UNSPECIFIED = "UNSPECIFIED"
    RETRY_NEXT_SESSION = "retry_next_session"
    RETRY_SAME_SESSION = "retry_same_session"


class StrategyConfig(BaseModel):
    """The base strategy. Implemented exactly as specified; nothing added."""

    model_config = _FROZEN

    rsi_period: int = 14
    rsi_low: float = 25.0
    rsi_high: float = 35.0
    rsi_exit_above: float = 50.0
    sma_period: int = 50
    target_pct: float = 5.0
    target_basis: TargetBasis = TargetBasis.GROSS
    lot_notional_inr: int = 5_000
    max_trades_per_day: int = 2
    near_miss_rsi_high: float = 40.0
    entry_order_type: EntryOrderType = EntryOrderType.LIMIT
    entry_limit_buffer_bps: int = 30  # OPEN: 0.30% above LTP
    price_above_notional: PriceAboveNotional = PriceAboveNotional.SKIP  # OPEN


class RobustnessConfig(BaseModel):
    """R1-R8. Each independently testable; all strategy-affecting modules OFF."""

    model_config = _FROZEN

    r1_time_stop_enabled: bool = False
    r1_time_stop_sessions: int = 30  # OPEN
    r2_reentry_spacing_enabled: bool = False
    r2_min_drop_pct: float = 5.0  # OPEN
    r2_require_lower_rsi: bool = True
    r3_sector_cap_enabled: bool = False
    r3_max_lots_per_sector: int = 3  # OPEN
    r4_regime_scaling_enabled: bool = False
    r4_mode: R4Mode = R4Mode.REDUCE_TO_ONE  # OPEN
    r5_event_exclusion_enabled: bool = False
    r5_sessions_around_results: int = 3  # OPEN
    r6_capital_ladder_enabled: bool = False
    r6_max_deployed_pct: float = 60.0  # OPEN
    r7_exit_batching_enabled: bool = True  # pure cost saving; spec permits ON
    r8_cost_floor_enabled: bool = False
    r8_max_cost_pct_of_target: float = 15.0  # OPEN


class RiskConfig(BaseModel):
    model_config = _FROZEN

    allocated_capital_inr: int = 10_00_000
    max_order_value_inr: int = 6_000
    max_trades_per_day: int = 2
    max_lots_per_symbol: int = 10
    max_open_lots: int = 200
    fat_finger_band_pct: float = 10.0
    exposure_alert_deployed_pct: float = 50.0
    exposure_alert_book_drawdown_pct: float = 12.0


class CostConfig(BaseModel):
    """Every figure verified against Firstock's charges page and one real contract
    note before Phase 3. Strings, not floats, because these feed money arithmetic."""

    model_config = _FROZEN

    brokerage_delivery_inr: str = "0.00"
    stt_buy_pct: str = "0.1"
    stt_sell_pct: str = "0.1"
    dp_charge_per_isin_per_day_inr: str = "13.50"
    gst_pct: str = "18.0"
    stamp_duty_buy_pct: str = "0.015"
    exchange_txn_pct: str = "0.00297"
    sebi_turnover_pct: str = "0.0001"
    stcg_rate_pct: str = "20.0"  # Sec 111A, verify at run time
    stcg_cess_pct: str = "4.0"


class OpsConfig(BaseModel):
    model_config = _FROZEN

    mode: Mode = Mode.PAPER
    expected_egress_ip: str | None = None
    run_time_ist: str = "15:20"
    max_orders_per_second: int = 2
    paper_sessions_required: int = 20  # OPEN: spec says 20-40
    live_ramp_single_trade_sessions: int = 20  # OPEN
    llm_event_screen_mode: EventScreenMode = EventScreenMode.ADVISORY_ONLY  # OPEN
    corp_action_gap_halt_pct: float = 15.0  # OPEN
    max_clock_skew_seconds: int = 5


class UnresolvedRules(BaseModel):
    """Rules the spec never specified. The spec says: flag and stop, do not invent.

    These default to UNSPECIFIED so that any attempt to run the strategy raises
    rather than silently adopting a rule the account owner never approved.
    """

    model_config = _FROZEN

    on_index_removal: OnIndexRemoval = OnIndexRemoval.UNSPECIFIED
    on_cash_shortfall: OnCashShortfall = OnCashShortfall.UNSPECIFIED
    on_exit_partial_fill: OnExitPartialFill = OnExitPartialFill.UNSPECIFIED

    def unresolved(self) -> list[str]:
        return [name for name, value in self if value == UNSPECIFIED]


class AppConfig(BaseModel):
    model_config = _FROZEN

    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    robustness: RobustnessConfig = Field(default_factory=RobustnessConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    costs: CostConfig = Field(default_factory=CostConfig)
    ops: OpsConfig = Field(default_factory=OpsConfig)
    rules: UnresolvedRules = Field(default_factory=UnresolvedRules)


def assert_rules_resolved(config: AppConfig) -> None:
    """Refuse to run while any unspecified rule remains unspecified."""
    outstanding = config.rules.unresolved()
    if outstanding:
        raise UnresolvedStrategyRuleError(
            "the spec never specified these rules and none may be invented: "
            + ", ".join(outstanding)
        )


def assert_live_permitted(config: AppConfig, env: Mapping[str, str], confirm_file: Path) -> None:
    """Live needs a config flag, an env var, a confirmation file and an egress IP.

    The fourth gate in the spec, the interactive startup prompt, is a runtime concern
    and is enforced by the daily job entrypoint, not here.
    """
    if config.ops.mode is not Mode.LIVE:
        return

    missing: list[str] = []
    if env.get(LIVE_ENV_VAR) != "1":
        missing.append(f"env var {LIVE_ENV_VAR}=1")
    if not confirm_file.is_file():
        missing.append(f"confirmation file at {confirm_file}")
    if config.ops.expected_egress_ip is None:
        missing.append("ops.expected_egress_ip")

    if missing:
        raise LiveModeNotPermittedError("live mode refused; missing gates: " + ", ".join(missing))
