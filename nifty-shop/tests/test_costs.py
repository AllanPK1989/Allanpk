from __future__ import annotations

import pytest

from nifty_shop.config import CostConfig
from nifty_shop.costs import buy_charges, round_trip_charges, sell_charges, stcg_tax
from nifty_shop.money import format_rupees, rupees


def cfg() -> CostConfig:
    return CostConfig()


def test_buy_side_matches_the_spec_line_items() -> None:
    """5,000 rupee buy: STT 5.00, stamp 0.75, exchange 0.15, SEBI 0.01, GST on fees."""
    charges = buy_charges(rupees("5000"), cfg())
    assert format_rupees(charges.stt) == "5.00"
    assert format_rupees(charges.stamp_duty) == "0.75"
    assert format_rupees(charges.brokerage) == "0.00"
    assert charges.dp_charge == 0


def test_sell_side_carries_the_dp_charge_with_gst() -> None:
    """13.50 + 18% GST = 15.93, per ISIN per day."""
    charges = sell_charges(rupees("5250"), cfg())
    assert format_rupees(charges.dp_charge) == "15.93"
    assert format_rupees(charges.stt) == "5.25"


def test_stamp_duty_is_buy_side_only() -> None:
    assert sell_charges(rupees("5250"), cfg()).stamp_duty == 0


def test_round_trip_reproduces_the_specs_own_arithmetic() -> None:
    """The spec states ~27 rupees on a 5,000 position exiting at +5%, about 11% of the
    250 rupee gross target. If this model disagrees, one of the two is wrong."""
    total = round_trip_charges(rupees("5000"), rupees("5250"), cfg())
    assert 26.50 <= int(total) / 100 <= 28.00, format_rupees(total)


def test_charges_are_about_eleven_percent_of_the_gross_target() -> None:
    gross_target = rupees("250")
    total = round_trip_charges(rupees("5000"), rupees("5250"), cfg())
    ratio = int(total) / int(gross_target)
    assert 0.10 <= ratio <= 0.12


def test_net_return_on_a_five_percent_gross_move_is_about_four_and_a_half() -> None:
    entry, exit_ = rupees("5000"), rupees("5250")
    net = int(exit_) - int(entry) - int(round_trip_charges(entry, exit_, cfg()))
    assert 4.40 <= (net / int(entry)) * 100 <= 4.55


def test_batching_a_second_lot_saves_exactly_one_dp_charge() -> None:
    """R7: the DP charge is per ISIN per day, so a batched exit pays it once."""
    unbatched = sell_charges(rupees("5250"), cfg(), include_dp=True)
    batched = sell_charges(rupees("5250"), cfg(), include_dp=False)
    assert int(unbatched.total) - int(batched.total) == int(unbatched.dp_charge)
    assert batched.dp_charge == 0


def test_gst_applies_to_fees_but_never_to_stt_or_stamp_duty() -> None:
    """GST is charged on brokerage and exchange/SEBI fees only. Applying it to STT
    would roughly double the modelled cost of a round trip."""
    charges = buy_charges(rupees("100000"), cfg())
    fees = int(charges.brokerage) + int(charges.exchange_txn) + int(charges.sebi_turnover)
    assert int(charges.gst) == pytest.approx(round(fees * 0.18), abs=1)


def test_stcg_is_charged_with_cess_on_the_gross_gain() -> None:
    """Sec 111A at 20% plus 4% cess = 20.8% effective."""
    tax = stcg_tax(rupees("250"), cfg())
    assert format_rupees(tax) == "52.00"


def test_a_loss_attracts_no_tax() -> None:
    assert stcg_tax(rupees("-100"), cfg()) == 0


def test_charges_scale_with_notional() -> None:
    small = round_trip_charges(rupees("5000"), rupees("5250"), cfg())
    large = round_trip_charges(rupees("50000"), rupees("52500"), cfg())
    assert int(large) > int(small)
    # The fixed DP charge means cost as a fraction of notional falls with size.
    assert int(large) / 50000 < int(small) / 5000
