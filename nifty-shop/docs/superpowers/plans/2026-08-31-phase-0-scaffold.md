# Phase 0 Implementation Plan — Scaffold, Config Schema, Risk Register, Kill Criteria

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking. Execute
> task-by-task, stopping at the gate at the end.

**Goal:** Stand up a `mypy --strict` clean Python 3.12 project whose configuration
schema encodes every decision in the spec, defaults to PAPER, keeps all robustness
modules OFF, and *refuses to run* while the three missing strategy rules are unresolved.

**Architecture:** A `src/`-layout uv project. Four small, independently testable
modules: integer-paisa money, a frozen Pydantic config tree, a machine-readable kill
criteria loader/evaluator, and the tooling gates that enforce the spec's
non-functional rules. No broker code, no data code, no strategy code in this phase.

**Tech Stack:** Python 3.12 (via `uv python pin`), `uv`, Pydantic v2, pytest, mypy
strict, ruff. Zero network in unit tests.

## Global Constraints

Copied verbatim from the spec; every task inherits these.

- Python **3.12**, dependency management via **`uv`**. SQLite in **WAL** mode (Phase 2+).
- **`mypy --strict`** must pass. **`ruff`** must pass. **No bare `except`. No swallowed exceptions.**
- **Timezone-aware datetimes**: `Asia/Kolkata` for logic, **UTC for storage**.
- **`pytest` against a fake broker. Zero network in unit tests. Deterministic seeds.**
- **PAPER is the default.** Live requires a config flag, an env var, a confirmation file, and a startup prompt.
- **The LLM never places orders.** Entry and exit are deterministic.
- **Every order passes the risk gate. No bypass, no `force=True`.**
- **The broker is the source of truth** for holdings, orders and funds.
- **Fail closed.** Missing candles, stale data, unknown order state, IP mismatch, clock skew → skip the day and alert.
- **No secrets in the repo.** Never log tokens, keys or session IDs, including in traces.
- **Do not add a strategy rule not in the spec.** Flag and stop instead.

---

## Verification status of this plan's code

Every code block in Tasks 1-4 was **executed** before this plan was handed over, in a
throwaway project outside the repo. Result: **22 tests pass, `mypy --strict` with the
pydantic plugin reports no issues, `ruff check` passes.**

Doing so found four defects that were fixed in place here, so the plan runs verbatim:

1. `disallow_any_explicit` is incompatible with Pydantic — `ConfigDict` is a `TypedDict`
   containing `Any`, so every `model_config` line errored. Replaced with the
   `pydantic.mypy` plugin, which is stricter about the things that actually matter.
2. `TRY003` rejects specific exception messages. Explicitly ignored, with rationale in
   the config; a message naming *which* gate is missing is worth more than the rule.
3. `N818` requires exception classes to end in `Error`. Renamed accordingly.
4. The frozen-model mutation test needed no `# type: ignore` once the plugin was on;
   under `--strict` the unused ignore was itself an error.

---

## Decisions locked before this plan

| Question | Answer | Consequence |
|---|---|---|
| Backtest data source | **Assemble from free NSE archives** | Phase 2 grows a data-acquisition sub-project; see ADR-0001 |
| Allocated capital | **₹10,00,000** | `risk.allocated_capital_inr`; KC-3 threshold is ₹8,00,000 |
| Kill criteria | **Strict** — 20% DD / 40 sessions / 80% capital | Written to the dated file, encoded in `config/kill_criteria.toml` |
| Exit target | **+5% gross, as written** | `target_basis = GROSS`; net becomes a Phase 4 sensitivity axis |

## Environment finding that reshapes the phase order

This session's egress proxy **denies CONNECT to `nseindia.com` and `firstock.in`**
(403 from the policy gateway; confirmed in `recentRelayFailures`). `pypi.org` and
`raw.githubusercontent.com` are reachable.

Consequences, folded into the roadmap below:

1. **No NSE bytes can be downloaded from this environment.** The Phase 2 downloader is
   written and unit-tested here against committed fixtures; the bulk historical pull
   runs **on the VPS**, which has unrestricted egress and the whitelisted static IP.
2. **The Firstock docs site cannot be read from here.** The spec forbids inventing a
   signature. The official SDK `the-firstock/firstock-developer-sdk-python` **is**
   readable via `raw.githubusercontent.com`, so signatures can be taken from source —
   but **rate limits and error-code semantics are documentation-only facts** and must
   come from you or from the VPS. Phase 1 stops at that boundary rather than guessing.
3. Neither of these blocks Phase 0. Phase 0 needs no network beyond PyPI.

---

## File structure

| Path | Responsibility |
|---|---|
| `nifty-shop/pyproject.toml` | Deps, `mypy --strict`, ruff rules incl. `BLE` (no bare except), pytest config |
| `nifty-shop/.python-version` | Pins 3.12 for `uv` |
| `nifty-shop/.gitignore` | Excludes `.env`, `*.db`, `data/`, secrets |
| `nifty-shop/.env.example` | Names every secret; **holds no values** |
| `nifty-shop/src/nifty_shop/money.py` | Integer-paisa money. No floats anywhere near currency |
| `nifty-shop/src/nifty_shop/config.py` | Frozen Pydantic config tree; live gate; unresolved-rule gate |
| `nifty-shop/src/nifty_shop/kill_criteria.py` | Loads `kill_criteria.toml`, evaluates breaches |
| `nifty-shop/config/kill_criteria.toml` | Machine-readable mirror of the dated criteria file |
| `nifty-shop/tests/test_money.py` | Rounding, formatting, float rejection |
| `nifty-shop/tests/test_config.py` | Defaults, live gate, unresolved-rule gate, immutability |
| `nifty-shop/tests/test_kill_criteria.py` | Breach evaluation + prose/code drift guard |
| `nifty-shop/docs/risk-register.md` | Live risk register |
| `nifty-shop/docs/decisions/ADR-0001-backtest-data-source.md` | Why free NSE archives |
| `nifty-shop/docs/decisions/ADR-0002-integer-paisa-money.md` | Why no floats |

---

### Task 1: Project scaffold and tooling gates

**Files:**
- Create: `nifty-shop/pyproject.toml`, `nifty-shop/.python-version`, `nifty-shop/.gitignore`, `nifty-shop/.env.example`, `nifty-shop/src/nifty_shop/__init__.py`
- Test: `nifty-shop/tests/test_toolchain.py`

**Interfaces:**
- Consumes: nothing.
- Produces: an installable `nifty_shop` package; `uv run pytest`, `uv run mypy`, `uv run ruff check` all green.

- [ ] **Step 1: Pin Python and create the tree**

```bash
cd /home/user/Allanpk/nifty-shop
uv python install 3.12
uv python pin 3.12
mkdir -p src/nifty_shop tests config
touch src/nifty_shop/__init__.py
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "nifty-shop"
version = "0.1.0"
description = "RSI-Filtered Nifty Shop — personal-use cash equity system on Firstock"
requires-python = ">=3.12,<3.13"
dependencies = [
    "pydantic>=2.9",
]

[dependency-groups]
dev = ["pytest>=8.3", "mypy>=1.13", "ruff>=0.8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/nifty_shop"]

[tool.mypy]
python_version = "3.12"
strict = true
files = ["src", "tests"]
warn_unreachable = true
plugins = ["pydantic.mypy"]

[tool.ruff]
line-length = 100
target-version = "py312"
src = ["src", "tests"]

[tool.ruff.lint]
# BLE = flake8-blind-except, enforcing the spec's "no bare except".
# TRY = tryceratops, catching swallowed exceptions.
select = ["E", "F", "I", "N", "UP", "B", "A", "C4", "SIM", "ARG", "PTH", "RUF", "BLE", "TRY", "DTZ"]
# Specific, actionable exception messages are worth more here than TRY003.
ignore = ["TRY003"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q --strict-markers"
```

`DTZ` is deliberate: it makes a naive `datetime.now()` a lint error, which is the
spec's timezone rule enforced by the toolchain rather than by discipline.

- [ ] **Step 3: Write `.gitignore` and `.env.example`**

```bash
cat > .gitignore <<'EOF'
.venv/
__pycache__/
*.py[cod]
.mypy_cache/
.ruff_cache/
.pytest_cache/
.env
*.db
*.db-wal
*.db-shm
data/
runs/
EOF

cat > .env.example <<'EOF'
# Values are NEVER committed. Copy to .env on the VPS and fill in there.
FIRSTOCK_USER_ID=
FIRSTOCK_PASSWORD=
FIRSTOCK_TOTP_SECRET=
FIRSTOCK_API_KEY=
FIRSTOCK_VENDOR_CODE=
EXPECTED_EGRESS_IP=
NIFTY_SHOP_ALLOW_LIVE=0
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
EOF
```

- [ ] **Step 4: Write the failing toolchain test**

```python
# nifty-shop/tests/test_toolchain.py
from __future__ import annotations

import sys
import tomllib
from pathlib import Path


def test_runs_on_python_312() -> None:
    assert sys.version_info[:2] == (3, 12)


def test_env_example_declares_no_values() -> None:
    """A committed .env.example must name secrets, never carry them."""
    lines = Path(__file__).parents[1].joinpath(".env.example").read_text().splitlines()
    for line in lines:
        if not line.strip() or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        assert value == "" or key == "NIFTY_SHOP_ALLOW_LIVE", f"{key} has a committed value"


def test_lint_config_forbids_blind_except() -> None:
    pyproject = Path(__file__).parents[1] / "pyproject.toml"
    with pyproject.open("rb") as fh:
        cfg = tomllib.load(fh)
    selected = cfg["tool"]["ruff"]["lint"]["select"]
    assert "BLE" in selected, "spec requires no bare except"
    assert "DTZ" in selected, "spec requires timezone-aware datetimes"
    assert cfg["tool"]["mypy"]["strict"] is True
```

- [ ] **Step 5: Run and verify green**

```bash
cd /home/user/Allanpk/nifty-shop
uv sync
uv run pytest tests/test_toolchain.py -v
uv run mypy
uv run ruff check .
```
Expected: 3 passed; `Success: no issues found`; `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add nifty-shop/pyproject.toml nifty-shop/.python-version nifty-shop/.gitignore \
        nifty-shop/.env.example nifty-shop/src nifty-shop/tests
git commit -m "chore(nifty-shop): scaffold uv project with strict mypy, ruff and pytest gates"
```

---

### Task 2: Integer-paisa money

Rationale: the acceptance criteria require the cost model to reconcile to a real
contract note **to the paisa**. Binary floats cannot do that. See ADR-0002.

**Files:**
- Create: `nifty-shop/src/nifty_shop/money.py`
- Test: `nifty-shop/tests/test_money.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Paisa = NewType("Paisa", int)`; `rupees(amount: str | int | Decimal) -> Paisa`;
  `format_rupees(p: Paisa) -> str`; `pct_of(p: Paisa, pct: Decimal) -> Paisa`.
  Every later module expresses currency as `Paisa`.

- [ ] **Step 1: Write the failing test**

```python
# nifty-shop/tests/test_money.py
from __future__ import annotations

from decimal import Decimal

import pytest

from nifty_shop.money import Paisa, format_rupees, pct_of, rupees


def test_whole_rupees() -> None:
    assert rupees("5000") == 500_000
    assert rupees(5000) == 500_000


def test_paise_precision() -> None:
    assert rupees("13.50") == 1350
    assert rupees(Decimal("13.50")) == 1350


def test_rounds_half_up_at_the_paisa() -> None:
    assert rupees("0.005") == 1
    assert rupees("0.004") == 0


def test_float_is_rejected_outright() -> None:
    """0.1 is not 0.1 in binary; money must never accept one."""
    with pytest.raises(TypeError, match="float"):
        rupees(0.1)  # type: ignore[arg-type]


def test_format_is_always_two_decimals() -> None:
    assert format_rupees(Paisa(1350)) == "13.50"
    assert format_rupees(Paisa(500_000)) == "5000.00"
    assert format_rupees(Paisa(-1350)) == "-13.50"
    assert format_rupees(Paisa(5)) == "0.05"


def test_pct_of_matches_the_spec_cost_table() -> None:
    """STT at 0.1% on a 5,000 rupee buy is 5.00; both legs give the ~10.30 in the spec."""
    notional = rupees("5000")
    assert pct_of(notional, Decimal("0.1")) == 500
    assert format_rupees(pct_of(notional, Decimal("0.015"))) == "0.75"
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_money.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'nifty_shop.money'`

- [ ] **Step 3: Write the implementation**

```python
# nifty-shop/src/nifty_shop/money.py
"""Currency as integer paisa.

The acceptance criteria require reconciliation to a real contract note to the paisa.
Binary floating point cannot represent 0.05 exactly, so floats are rejected at the
boundary rather than tolerated and rounded later.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import NewType

Paisa = NewType("Paisa", int)

_ONE = Decimal("1")
_HUNDRED = Decimal("100")


def rupees(amount: str | int | Decimal) -> Paisa:
    """Convert a rupee amount to integer paisa, rounding half-up at the paisa."""
    if isinstance(amount, float):
        raise TypeError("float is not an accepted money input; pass str, int or Decimal")
    value = amount if isinstance(amount, Decimal) else Decimal(amount)
    return Paisa(int((value * _HUNDRED).quantize(_ONE, rounding=ROUND_HALF_UP)))


def format_rupees(paisa: Paisa) -> str:
    """Render paisa as a rupee string with exactly two decimals."""
    sign = "-" if paisa < 0 else ""
    magnitude = abs(int(paisa))
    return f"{sign}{magnitude // 100}.{magnitude % 100:02d}"


def pct_of(paisa: Paisa, pct: Decimal) -> Paisa:
    """Percentage of an amount, rounded half-up at the paisa."""
    return Paisa(int((Decimal(int(paisa)) * pct / _HUNDRED).quantize(_ONE, rounding=ROUND_HALF_UP)))
```

- [ ] **Step 4: Run to verify it passes**

```bash
uv run pytest tests/test_money.py -v && uv run mypy && uv run ruff check .
```
Expected: 6 passed; mypy and ruff clean.

- [ ] **Step 5: Commit**

```bash
git add nifty-shop/src/nifty_shop/money.py nifty-shop/tests/test_money.py
git commit -m "feat(nifty-shop): add integer-paisa money type with float rejection"
```

---

### Task 3: Configuration schema

Every `<<CONFIGURE>>` marker in the spec appears here exactly once. Items you have not
yet decided carry a **flagged default**; the three **missing strategy rules** carry no
default at all and make the system refuse to run.

**Files:**
- Create: `nifty-shop/src/nifty_shop/config.py`
- Test: `nifty-shop/tests/test_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `AppConfig` and its sub-models; `assert_live_permitted(cfg, env, confirm_file) -> None`;
  `assert_rules_resolved(cfg) -> None`; exceptions `LiveModeNotPermittedError`, `UnresolvedStrategyRuleError`.

- [ ] **Step 1: Write the failing test**

```python
# nifty-shop/tests/test_config.py
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from nifty_shop.config import (
    AppConfig,
    LiveModeNotPermittedError,
    Mode,
    TargetBasis,
    UnresolvedStrategyRuleError,
    assert_live_permitted,
    assert_rules_resolved,
)


def test_paper_is_the_default_mode() -> None:
    assert AppConfig().ops.mode is Mode.PAPER


def test_locked_decisions_are_encoded() -> None:
    cfg = AppConfig()
    assert cfg.risk.allocated_capital_inr == 10_00_000
    assert cfg.strategy.target_basis is TargetBasis.GROSS
    assert cfg.strategy.target_pct == 5.0
    assert cfg.strategy.max_trades_per_day == 2


def test_every_robustness_module_is_off_except_r7() -> None:
    """R1-R6 and R8 change strategy behaviour and must be opt-in.
    R7 is pure cost saving with no strategy effect; the spec permits it ON."""
    r = AppConfig().robustness
    assert r.r1_time_stop_enabled is False
    assert r.r2_reentry_spacing_enabled is False
    assert r.r3_sector_cap_enabled is False
    assert r.r4_regime_scaling_enabled is False
    assert r.r5_event_exclusion_enabled is False
    assert r.r6_capital_ladder_enabled is False
    assert r.r8_cost_floor_enabled is False
    assert r.r7_exit_batching_enabled is True


def test_the_three_missing_rules_block_every_run() -> None:
    with pytest.raises(UnresolvedStrategyRuleError) as exc:
        assert_rules_resolved(AppConfig())
    message = str(exc.value)
    assert "on_index_removal" in message
    assert "on_cash_shortfall" in message
    assert "on_exit_partial_fill" in message


def test_live_refused_without_all_four_gates(tmp_path: Path) -> None:
    cfg = AppConfig.model_validate({"ops": {"mode": "live"}})
    with pytest.raises(LiveModeNotPermittedError) as exc:
        assert_live_permitted(cfg, env={}, confirm_file=tmp_path / "absent")
    message = str(exc.value)
    assert "NIFTY_SHOP_ALLOW_LIVE" in message
    assert "confirmation file" in message
    assert "expected_egress_ip" in message


def test_live_permitted_when_every_gate_is_present(tmp_path: Path) -> None:
    confirm = tmp_path / "LIVE_CONFIRMED"
    confirm.write_text("confirmed")
    cfg = AppConfig.model_validate(
        {"ops": {"mode": "live", "expected_egress_ip": "203.0.113.7"}}
    )
    assert_live_permitted(cfg, env={"NIFTY_SHOP_ALLOW_LIVE": "1"}, confirm_file=confirm)


def test_paper_mode_needs_no_gates(tmp_path: Path) -> None:
    assert_live_permitted(AppConfig(), env={}, confirm_file=tmp_path / "absent")


def test_config_is_frozen_and_rejects_unknown_keys() -> None:
    cfg = AppConfig()
    with pytest.raises(ValidationError):
        cfg.strategy.target_pct = 6.0
    with pytest.raises(ValidationError):
        AppConfig.model_validate({"strategy": {"sneaky_new_rule": True}})
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_config.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'nifty_shop.config'`

- [ ] **Step 3: Write the implementation**

```python
# nifty-shop/src/nifty_shop/config.py
"""Configuration for the RSI-Filtered Nifty Shop system.

Every <<CONFIGURE>> marker in the spec appears here exactly once. Items marked
OPEN carry a flagged default and are still awaiting a decision. The three rules the
spec never specified carry no usable default: they resolve to UNSPECIFIED and make
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
    rather than silently adopting a rule you never approved.
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


def assert_live_permitted(
    config: AppConfig, env: Mapping[str, str], confirm_file: Path
) -> None:
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
        raise LiveModeNotPermittedError(
            "live mode refused; missing gates: " + ", ".join(missing)
        )
```

- [ ] **Step 4: Run to verify it passes**

```bash
uv run pytest tests/test_config.py -v && uv run mypy && uv run ruff check .
```
Expected: 8 passed; mypy and ruff clean.

- [ ] **Step 5: Commit**

```bash
git add nifty-shop/src/nifty_shop/config.py nifty-shop/tests/test_config.py
git commit -m "feat(nifty-shop): add frozen config schema with live gate and unresolved-rule refusal"
```

---

### Task 4: Machine-readable kill criteria and breach evaluator

Rationale: prose in a dated file cannot be enforced. This makes the criteria executable
and adds a drift guard so the prose and the numbers can never disagree.

**Files:**
- Create: `nifty-shop/config/kill_criteria.toml`, `nifty-shop/src/nifty_shop/kill_criteria.py`
- Test: `nifty-shop/tests/test_kill_criteria.py`

**Interfaces:**
- Consumes: `nifty_shop.money` (not required, but breaches print rupee figures).
- Produces: `KillCriteria`, `Breach`, `load_kill_criteria(path) -> KillCriteria`,
  `evaluate(criteria, *, max_book_drawdown_pct, longest_zero_exit_sessions, peak_capital_deployed_inr) -> list[Breach]`.
  Phase 3's reporting layer calls `evaluate` first and prints breaches above the headline.

- [ ] **Step 1: Write `config/kill_criteria.toml`**

```toml
# Machine-readable mirror of
# docs/kill-criteria/2026-08-31-pre-registered-kill-criteria.md
# Frozen after the first baseline backtest run. Changes require a dated commit.
registered_on = "2026-08-31"
strictness = "strict"
allocated_capital_inr = 1000000

[kc1_book_drawdown]
max_drawdown_pct = 20.0

[kc2_zero_exit_stretch]
max_sessions = 40

[kc3_peak_capital]
max_pct_of_allocated = 80.0
```

- [ ] **Step 2: Write the failing test**

```python
# nifty-shop/tests/test_kill_criteria.py
from __future__ import annotations

from datetime import date
from pathlib import Path

from nifty_shop.kill_criteria import evaluate, load_kill_criteria

REPO = Path(__file__).parents[1]
CRITERIA_TOML = REPO / "config" / "kill_criteria.toml"
CRITERIA_DOC = REPO / "docs" / "kill-criteria" / "2026-08-31-pre-registered-kill-criteria.md"


def test_loads_the_registered_criteria() -> None:
    kc = load_kill_criteria(CRITERIA_TOML)
    assert kc.registered_on == date(2026, 8, 31)
    assert kc.allocated_capital_inr == 10_00_000
    assert kc.max_drawdown_pct == 20.0
    assert kc.max_zero_exit_sessions == 40
    assert kc.peak_capital_threshold_inr == 8_00_000


def test_clean_result_breaches_nothing() -> None:
    kc = load_kill_criteria(CRITERIA_TOML)
    assert (
        evaluate(
            kc,
            max_book_drawdown_pct=11.0,
            longest_zero_exit_sessions=22,
            peak_capital_deployed_inr=3_10_000,
        )
        == []
    )


def test_the_predicted_2008_shape_breaches_kc1_and_kc3_only() -> None:
    """Matches the prediction recorded in the dated criteria file."""
    kc = load_kill_criteria(CRITERIA_TOML)
    breaches = evaluate(
        kc,
        max_book_drawdown_pct=24.0,
        longest_zero_exit_sessions=18,
        peak_capital_deployed_inr=8_20_000,
    )
    assert [b.criterion for b in breaches] == ["KC-1", "KC-3"]


def test_boundary_is_exclusive_worse_than_not_equal_to() -> None:
    kc = load_kill_criteria(CRITERIA_TOML)
    assert (
        evaluate(
            kc,
            max_book_drawdown_pct=20.0,
            longest_zero_exit_sessions=40,
            peak_capital_deployed_inr=8_00_000,
        )
        == []
    )


def test_prose_and_numbers_cannot_drift_apart() -> None:
    """The dated file is the registration; the TOML is what the code reads.
    If they ever disagree, the registration has been quietly edited."""
    kc = load_kill_criteria(CRITERIA_TOML)
    prose = CRITERIA_DOC.read_text(encoding="utf-8")
    assert f"worse than {kc.max_drawdown_pct}%" in prose
    assert f"beyond {kc.max_zero_exit_sessions} NSE trading sessions" in prose
    assert f"exceeds {kc.max_peak_capital_pct:.0f}% of allocated capital" in prose
```

- [ ] **Step 3: Run to verify it fails**

```bash
uv run pytest tests/test_kill_criteria.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'nifty_shop.kill_criteria'`

- [ ] **Step 4: Write the implementation**

```python
# nifty-shop/src/nifty_shop/kill_criteria.py
"""Pre-registered kill criteria, made executable.

The dated markdown file is the registration. This module is what the reporting layer
actually consults, and a test asserts the two cannot drift apart.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True, slots=True)
class KillCriteria:
    registered_on: date
    strictness: str
    allocated_capital_inr: int
    max_drawdown_pct: float
    max_zero_exit_sessions: int
    max_peak_capital_pct: float

    @property
    def peak_capital_threshold_inr(self) -> int:
        return int(self.allocated_capital_inr * self.max_peak_capital_pct / 100)


@dataclass(frozen=True, slots=True)
class Breach:
    criterion: str
    description: str
    threshold: str
    observed: str

    def headline(self) -> str:
        return (
            f"{self.criterion} BREACHED — {self.description}: "
            f"{self.observed} (limit {self.threshold})"
        )


def load_kill_criteria(path: Path) -> KillCriteria:
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    return KillCriteria(
        registered_on=date.fromisoformat(raw["registered_on"]),
        strictness=raw["strictness"],
        allocated_capital_inr=raw["allocated_capital_inr"],
        max_drawdown_pct=raw["kc1_book_drawdown"]["max_drawdown_pct"],
        max_zero_exit_sessions=raw["kc2_zero_exit_stretch"]["max_sessions"],
        max_peak_capital_pct=raw["kc3_peak_capital"]["max_pct_of_allocated"],
    )


def evaluate(
    criteria: KillCriteria,
    *,
    max_book_drawdown_pct: float,
    longest_zero_exit_sessions: int,
    peak_capital_deployed_inr: int,
) -> list[Breach]:
    """Return every breached criterion. An empty list means the run survives.

    Thresholds are exclusive: the registration says "worse than" and "beyond", so
    a value exactly at the limit does not breach.
    """
    breaches: list[Breach] = []

    if max_book_drawdown_pct > criteria.max_drawdown_pct:
        breaches.append(
            Breach(
                criterion="KC-1",
                description="book drawdown marked to market including open lots",
                threshold=f"{criteria.max_drawdown_pct}%",
                observed=f"{max_book_drawdown_pct}%",
            )
        )

    if longest_zero_exit_sessions > criteria.max_zero_exit_sessions:
        breaches.append(
            Breach(
                criterion="KC-2",
                description="longest stretch with zero exits",
                threshold=f"{criteria.max_zero_exit_sessions} sessions",
                observed=f"{longest_zero_exit_sessions} sessions",
            )
        )

    if peak_capital_deployed_inr > criteria.peak_capital_threshold_inr:
        breaches.append(
            Breach(
                criterion="KC-3",
                description="peak capital deployed",
                threshold=f"INR {criteria.peak_capital_threshold_inr:,}",
                observed=f"INR {peak_capital_deployed_inr:,}",
            )
        )

    return breaches
```

- [ ] **Step 5: Run to verify it passes**

```bash
uv run pytest -v && uv run mypy && uv run ruff check .
```
Expected: 22 passed; `Success: no issues found`; `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add nifty-shop/config/kill_criteria.toml nifty-shop/src/nifty_shop/kill_criteria.py \
        nifty-shop/tests/test_kill_criteria.py
git commit -m "feat(nifty-shop): make pre-registered kill criteria executable with drift guard"
```

---

### Task 5: Risk register and architecture decision records

No test cycle; this task's gate is your review.

**Files:**
- Create: `nifty-shop/docs/risk-register.md`, `nifty-shop/docs/decisions/ADR-0001-backtest-data-source.md`, `nifty-shop/docs/decisions/ADR-0002-integer-paisa-money.md`

- [ ] **Step 1: Write the risk register** covering, at minimum, the entries in the
      "Risk register seed" section below, each with likelihood, impact, and the
      mitigation that is actually built rather than aspired to.
- [ ] **Step 2: Write ADR-0001** recording the free-NSE-archives decision, the
      alternatives rejected, and the egress finding that moves the bulk download to the VPS.
- [ ] **Step 3: Write ADR-0002** recording integer paisa and the contract-note
      reconciliation requirement that forces it.
- [ ] **Step 4: Commit**

```bash
git add nifty-shop/docs
git commit -m "docs(nifty-shop): add risk register and ADRs for data source and money representation"
```

---

## Risk register seed

| # | Risk | Impact | Mitigation built in |
|---|---|---|---|
| R-01 | NSE archive layout changes or rate-limits the VPS | Backtest cannot be rebuilt | Fixtures committed per era; downloader is resumable and idempotent; raw bytes cached before parsing |
| R-02 | Point-in-time constituent table is assembled wrong | Silent survivorship bias — the exact thing Forbidden rule 6 bans | Every add/drop cites its NSE press release; a test asserts the reconstructed list has exactly 50 names on 20 random dates |
| R-03 | Corporate action ratios missing or wrong | SMA and RSI silently corrupt; system trades confidently and wrongly | Unexplained-gap detector halts a symbol beyond the configured threshold; indicator validation gate against an independent reference |
| R-04 | Firstock rate limits and error codes are undocumented to me | Invented client behaviour | Docs host is egress-blocked here; signatures come from the official SDK source, and undocumented facts are escalated to you, never guessed |
| R-05 | 15:20 signal flips by 15:30 | Entries and exits both differ from backtest | Both values recorded; daily signal-drift metric covers exits as well as entries; no silent post-close recompute |
| R-06 | Lot ledger diverges from broker holdings | Exit decisions made on fiction | Morning reconciliation before any exit decision; run aborts on mismatch |
| R-07 | Capital exhausted mid-decline | Strategy stops when it most needs to act | Capital requirement model reported beside every return figure; KC-3 |
| R-08 | Static IP changes | Regulatory breach and refused orders | Preflight resolves egress IP, refuses to start on mismatch, re-checks before each run |
| R-09 | Session dies mid-run | Orphaned or duplicated orders | Order state machine plus idempotency key per intent; crash-resume test in the acceptance criteria |
| R-10 | Backtest overfitted by iteration | A good backtest and a bad account | Kill criteria pre-registered and frozen; one-look holdout; sensitivity surface reported even when unflattering |
| R-11 | Repo hosts an unrelated 3D animation project | Tooling and CI confusion | `nifty-shop/` is self-contained with its own `pyproject.toml` and venv |

---

## Phase roadmap and gates

Each gate stops for your review. Nothing proceeds past a red gate.

| Phase | Deliverable | Gate |
|---|---|---|
| **0** | This plan, kill criteria file, scaffold, config schema, risk register | **You approve; you close the three missing rules** |
| **1** | Firstock client from SDK source, session manager, static-IP preflight, read-only funds/holdings | Read-only calls succeed on the VPS; no invented signatures |
| **2** | NSE archive downloader, corporate actions, point-in-time constituents, calendar, indicator engine | **RSI(14) and SMA(50) match an independent reference for 5+ symbols across 3 dates, as committed fixtures. Hard stop until green.** |
| **3** | Baseline backtest, full costs, capital requirement model | Metrics 1-6 reported with breaches first; deterministic byte-identical reruns |
| **4** | Sensitivity surface, stress windows, Monte Carlo, then R1-R8 individually | Parameter collapse under ±20% reported plainly if it occurs |
| **5** | Out-of-sample holdout | **One look. No iteration after.** |
| **6** | Paper trading, lot ledger, risk gate, execution | ≥20 sessions, no unhandled exception, kill switch verified with orders resting |
| **7** | LLM event screen and daily brief, approval mode | Strict JSON schema; no execution rights |
| **8** | Live enablement checklist, 1 trade/day ramp | Manual, by you |

---

## Blocked on you before Phase 3 can start

1. **The three missing rules** (index removal / suspension / delisting; cash shortfall;
   exit partial fill). The config refuses to run until these are set — deliberately.
2. **The still-OPEN `<<CONFIGURE>>` items**, currently carrying flagged defaults:
   entry order type and limit buffer (LIMIT, 30 bps), price above ₹5,000 (SKIP),
   R1-R6/R8 parameters (modules are OFF so these are inert until Phase 4),
   paper sessions (20), live ramp sessions (20), event screen mode (advisory-only),
   corporate action gap halt (15%).
3. **Firstock rate limits and error codes**, which I cannot read from this environment.
4. **One real contract note**, for the Phase 3 cost-model reconciliation.

## Self-review against the spec

- Spec coverage: Phase 0's four named deliverables (scaffold, plan, risk register,
  config schema, kill criteria file) each map to a task. Later phases are roadmapped,
  not planned in detail, because the spec requires a review gate at each one.
- Placeholders: none. Every code step carries complete code.
- Type consistency: `Paisa`, `AppConfig`, `KillCriteria`, `Breach` and the two assert
  functions keep the same names across tasks and the roadmap.
- Deliberate omission: no strategy, indicator, broker or backtest code appears here.
  That is Phases 1-3 and each has its own gate.
