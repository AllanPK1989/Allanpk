# Event codes — SD card log

The program writes an event code to `gEventCode` (D12) and pulses `gEventPulse`
(M59) for exactly one scan. The FX5U data-logging function is configured to
trigger on that bit and capture `D12`, `D13`, `D14` together with the CPU's own
real-time-clock stamp. Retention is 7 days rolling — see `cpu-parameters.md`.

| Code | Event | `gEventParam` (D13) | `gEventValue` (D14) |
|------|-------|---------------------|---------------------|
| 1 | PLC entered RUN | – | – |
| 11–16 | Slot 1–6 **started** | slot no. | – |
| 21–26 | Slot 1–6 **reached 2 h** | slot no. | – |
| 31–36 | Slot 1–6 **normal reset** (counts as an unload) | slot no. | – |
| **41–46** | Slot 1–6 **EARLY RESET** by maintenance | slot no. | **minutes elapsed when cut short** |
| 51 | Door opened | – | – |
| 52 | Door closed | – | – |
| 53 | Door signal pulsating (chatter alarm) | – | transitions counted |
| 54 | No 'door closed' signal for the watchdog period | – | seconds |
| 55 | Cure timers **paused** — oven not fit to cure | slots affected | – |
| 56 | Cure timers resumed | slots affected | – |
| 61 | Door counters reset (quality) | – | – |
| 62 | Lot counters reset (quality) | – | – |
| 71 | Manual test entered | – | – |
| 72 | Manual test exited | – | – |
| 73 | **MAINTENANCE** logged in | – | – |
| 74 | **QUALITY** logged in | – | – |
| 75 | Failed login attempt | – | attempt number |
| 76 | Login attempted while locked out | – | seconds remaining |
| 77 | Logged out | – | – |
| 81 | Heat-up watchdog — failure to reach setpoint | – | watchdog setting, min |

## The codes that matter for traceability

**41–46 are the malpractice record.** They are written only by MAINTENANCE,
and only QUALITY can clear the counters that tally them — see the separation of
duties note in `functional-description.md` §5.

Every one of them is a cure that was cut
short with the maintenance password, stamped with the slot number, the wall
clock time and how many minutes short it was. They are the only events that
increment `gCntEarlyReset` and they deliberately do **not** increment
`gCntLotsUnloaded`.

That asymmetry is what makes `gLotsUnaccounted` work:

```
gLotsUnaccounted = gCntLotsLoaded - gCntLotsUnloaded - (slots running now)
```

In an honest shift that expression is always **0**. Every non-zero value has a
matching 41–46 event in the log with a name against the time.

## One limitation, stated plainly

`gEventCode` is a single register. If two loggable events landed in the same
PLC scan (≈2 ms) the second would overwrite the first. Every event here except
51/52 originates from an HMI button press, so a collision needs two touches
inside one scan — not physically possible. If you later drive slot starts from
sensors instead of the HMI, replace this with a small FIFO.
