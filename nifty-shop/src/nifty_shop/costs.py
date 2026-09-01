"""Transaction cost model.

Built before the backtest, as the spec requires, because on a 5,000 rupee position
targeting 5% the round trip is roughly 11% of the gross target. A backtest that omits
or understates it is not measuring the strategy.

Every figure comes from config as a decimal string, so nothing enters float arithmetic
on the way in, and every amount is integer paisa. The acceptance criteria require
reconciliation to a real contract note to the paisa, which floats cannot do.

Two details that are easy to get wrong and expensive if you do:

* **GST applies to brokerage and exchange/SEBI fees only** — never to STT or stamp duty.
  Applying it to STT roughly doubles the modelled cost of a round trip.
* **The DP charge is per ISIN per day, on the sell side only.** That is the entire
  reason R7 (exit batching) saves money: two lots of one symbol exiting the same day
  pay it once, not twice.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nifty_shop.config import CostConfig
from nifty_shop.money import Paisa, pct_of, rupees


@dataclass(frozen=True, slots=True)
class ChargeBreakdown:
    brokerage: Paisa
    stt: Paisa
    stamp_duty: Paisa
    exchange_txn: Paisa
    sebi_turnover: Paisa
    gst: Paisa
    dp_charge: Paisa

    @property
    def total(self) -> Paisa:
        return Paisa(
            int(self.brokerage)
            + int(self.stt)
            + int(self.stamp_duty)
            + int(self.exchange_txn)
            + int(self.sebi_turnover)
            + int(self.gst)
            + int(self.dp_charge)
        )


def _gst_on_fees(brokerage: Paisa, exchange: Paisa, sebi: Paisa, config: CostConfig) -> Paisa:
    """GST is levied on brokerage and exchange/SEBI fees. Not on STT. Not on stamp duty."""
    base = Paisa(int(brokerage) + int(exchange) + int(sebi))
    return pct_of(base, Decimal(config.gst_pct))


def buy_charges(notional: Paisa, config: CostConfig) -> ChargeBreakdown:
    brokerage = rupees(config.brokerage_delivery_inr)
    exchange = pct_of(notional, Decimal(config.exchange_txn_pct))
    sebi = pct_of(notional, Decimal(config.sebi_turnover_pct))
    return ChargeBreakdown(
        brokerage=brokerage,
        stt=pct_of(notional, Decimal(config.stt_buy_pct)),
        stamp_duty=pct_of(notional, Decimal(config.stamp_duty_buy_pct)),
        exchange_txn=exchange,
        sebi_turnover=sebi,
        gst=_gst_on_fees(brokerage, exchange, sebi, config),
        dp_charge=Paisa(0),
    )


def sell_charges(
    notional: Paisa, config: CostConfig, include_dp: bool = True
) -> ChargeBreakdown:
    """Sell-side charges.

    `include_dp=False` is for the second and later lots of the same symbol exiting on
    the same day under R7, since the depository bills once per ISIN per day.
    """
    brokerage = rupees(config.brokerage_delivery_inr)
    exchange = pct_of(notional, Decimal(config.exchange_txn_pct))
    sebi = pct_of(notional, Decimal(config.sebi_turnover_pct))

    dp = Paisa(0)
    if include_dp:
        base = rupees(config.dp_charge_per_isin_per_day_inr)
        dp = Paisa(int(base) + int(pct_of(base, Decimal(config.gst_pct))))

    return ChargeBreakdown(
        brokerage=brokerage,
        stt=pct_of(notional, Decimal(config.stt_sell_pct)),
        stamp_duty=Paisa(0),
        exchange_txn=exchange,
        sebi_turnover=sebi,
        gst=_gst_on_fees(brokerage, exchange, sebi, config),
        dp_charge=dp,
    )


def round_trip_charges(
    entry_notional: Paisa,
    exit_notional: Paisa,
    config: CostConfig,
    include_dp: bool = True,
) -> Paisa:
    return Paisa(
        int(buy_charges(entry_notional, config).total)
        + int(sell_charges(exit_notional, config, include_dp=include_dp).total)
    )


def stcg_tax(gain: Paisa, config: CostConfig) -> Paisa:
    """Short-term capital gains under Sec 111A, plus cess. A loss attracts none.

    The rate is config, not a constant, because it has changed and will change again.
    Set-off of losses against other gains is a portfolio-level matter and is
    deliberately not modelled here.
    """
    if int(gain) <= 0:
        return Paisa(0)
    base = pct_of(gain, Decimal(config.stcg_rate_pct))
    cess = pct_of(base, Decimal(config.stcg_cess_pct))
    return Paisa(int(base) + int(cess))
