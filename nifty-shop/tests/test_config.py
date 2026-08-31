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
    cfg = AppConfig.model_validate({"ops": {"mode": "live", "expected_egress_ip": "203.0.113.7"}})
    assert_live_permitted(cfg, env={"NIFTY_SHOP_ALLOW_LIVE": "1"}, confirm_file=confirm)


def test_paper_mode_needs_no_gates(tmp_path: Path) -> None:
    assert_live_permitted(AppConfig(), env={}, confirm_file=tmp_path / "absent")


def test_config_is_frozen_and_rejects_unknown_keys() -> None:
    cfg = AppConfig()
    with pytest.raises(ValidationError):
        cfg.strategy.target_pct = 6.0
    with pytest.raises(ValidationError):
        AppConfig.model_validate({"strategy": {"sneaky_new_rule": True}})
