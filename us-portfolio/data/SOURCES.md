# Sources

All figures were gathered on **5 September 2026**, the date all three statements carry.

## Positions

| Account | Source | Value | Cost | Return |
|---|---|---:|---:|---:|
| Vested · VSCH000079 | `PK_vested_account.pdf`, "Details of Holdings as of 05 Sep 2026" | $27,251.33 | $14,458.32 | +88.48% |
| Vested · Account 2 | Holdings table screenshot, same date | $20,967.75 | $13,315.02 | +57.47% |
| IBKR | "Open Positions" statement, same date | $5,548.35 | $5,237.48 | +5.94% |
| **Consolidated** | | **$53,767.41** | **$33,011.14** | **+62.88%** |

Share counts and average costs are transcribed exactly as printed. The account
totals reconcile to the totals shown on each statement.

## Market data

Prices for the 27 held names come from the statements themselves — all three
were struck on the same date and agree with each other on every overlapping
ticker (AAPL $319.97, GOOGL $338.46, META $616.77, MSFT $499.70, MU $1,016.59,
NVDA $230.36, IREN $44.68, CRWV $89.36 all match across statements), which is
the cross-check that they are the same tape.

52-week ranges, forward and trailing multiples, and consensus targets were
gathered from public market data on 5 Sep 2026 and cross-checked against market
capitalisation where a split made the raw quote ambiguous:

| Check | Resolution |
|---|---|
| CRWD | 4-for-1 split, 2 Jul 2026. Pre-split targets ($750) discarded; $213.10 confirmed against a $208B market cap. |
| NOW | 5-for-1 split, Dec 2025. $145.59 confirmed against a $150.5B cap on 1.035B shares. |
| NFLX | 10-for-1 split, Nov 2025. All figures split-adjusted. |
| KLAC | 10-for-1 split. Range estimated from "+111% over 52 weeks, ~40% below high". |
| AMD | $477.57 confirmed against a $770.87B cap. |
| LRCX | Sources spanned $292–$389; the IBKR statement's $307.65 was taken as authoritative. |

## Confidence flags

The `conf` column in the watchlist table marks how well each name's fundamentals
could be pinned down:

- **high** — price, range, multiple and target all confirmed from more than one source.
- **med** — price and range confirmed; multiple absent or single-sourced.
- **low** — only price confirmed. `AMD` is flagged low because published forward
  EPS estimates for FY27 were dispersed enough ($4.99 to figures implying several
  times that) that no honest forward P/E could be quoted. `BITQ` and `BLOK` are
  flagged low because no 52-week range was retrievable.

Where a figure could not be confirmed it is left empty and the affected column
reads "—". Nothing in this dataset is estimated silently.

## Currency

USD/INR 94.38 (4 Sep 2026). The rupee is down ~7% over twelve months, which has
flattered these dollar returns when restated in rupees.
