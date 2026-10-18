# Script writing guide

Every video is one YAML file in `content/` named `NNN-slug.yaml`, where `NNN`
is the topic id from `curriculum.yaml`. The generator follows this guide, and
human edits should too.

## Who we're talking to

Tamil speakers (Tamil Nadu, Puducherry, Sri Lanka, the diaspora) who are new to
money matters: students, first-job salaried people, small business owners,
homemakers. Assume no finance background. One idea per video, explained
so clearly that a 16-year-old and a 60-year-old both get it.

## Voice and language

- Spoken, warm, respectful Tamil (use "நீங்கள்"). Not literary, not slang.
- Finance terms people actually say in English stay in English, written in
  Latin script: Mutual Fund, SIP, Stock, Share, Insurance, Term plan, Index
  Fund, EMI, Credit Score. Give the Tamil meaning once ("பணவீக்கம், அதாவது
  Inflation").
- Sentences in `say` are short: aim for under 20 words. Each sentence becomes
  one caption and one voice clip, so a sentence that's too long makes a wall of
  caption text.
- In `say`, prefer numbers in Tamil words ("ஐந்து லட்சம் ரூபாய்") when the
  voice might stumble; on-screen text uses digits and ₹ ("₹5 லட்சம்").
- Indian context: ₹, lakh/crore, Indian products (PPF, EPF, NPS, FD, RD, ELSS),
  Indian regulators (SEBI, RBI, IRDAI, PFRDA, AMFI).

## Structure

**Short (vertical, target 40-60 seconds):**
1. `hook`: a question or surprising fact in the first 3 seconds
2. 1-2 explanation scenes (`define`, `stat`, `points`, `steps`, a chart)
3. `takeaway`: the one thing to remember

**Long (horizontal, target 2.5-4 minutes):** opens with an auto-generated
intro card (`intro_say` is its narration), then about 6-9 scenes. Give each
major scene a `chapter:` label (they become YouTube chapters). Include at least
one worked example with hypothetical numbers, common mistakes or myths, and a
final `takeaway`.

The disclaimer scene (and the SEBI F&O risk statement for `fno` topics) is
added automatically. Do not write disclaimers into scripts.

## Compliance: educator, not adviser

The channel owner is **not** SEBI-registered. Scripts must stay education:

- Never name a specific stock, company, mutual fund scheme, AMC, broker,
  insurer or app. Use "Company A", "ஒரு நிறுவனம்", "Fund X".
- Never say buy, sell, hold, accumulate, exit, target, or "this will go up".
- Never promise or imply returns ("guaranteed", "double your money", "sure
  profit"). Market returns are always "for example" and hypothetical.
- Never quote current or recent market prices or index levels. Charts use
  made-up, round numbers.
- For products whose rates change (PPF, FD, EPF, tax slabs), explain the
  mechanism. If a number is needed, say it's an example, or tell viewers to
  check the current rate on the official website.
- No links, Telegram, WhatsApp or paid groups. The pipeline adds the
  description.
- Risky topics (F&O, intraday, leverage, crypto) must state the risks plainly.

Run `python -m pipeline lint` to check a script. Errors block rendering.

## Text styling (on-screen fields only)

- `**text**` shows in the category accent colour
- `__text__` shows in yellow
- `++text++` shows in green (good), `--text--` in red (bad)
- `\n` forces a line break

## Scene reference

Every scene has a `type`. Narration goes in `say` (string or list of
sentences), and in item-level `say` for list scenes, where each item appears
as its sentence is spoken. `after` is narration spoken once everything is
visible. `chapter` (long only) starts a YouTube chapter.

| type | fields | notes |
|---|---|---|
| `hook` | `heading`, `sub`?, `icon`? | big opening question |
| `define` | `term`, `term_en`?, `text`, `label`? | definition card |
| `points` | `heading`, `items[{text, sub?, say}]`, `marker`: num/check/cross/dot, `columns`: 2? | list revealed item by item |
| `compare` | `heading`, `left{title,color?}`, `right{title,color?}`, `rows[{left,right,say}]` | two-column comparison |
| `steps` | `heading`, `lines[{text,say}]`, `result{text,say}`?, `tag`? | worked example (tag defaults to "உதாரணம் (கற்பனை எண்கள்)") |
| `stat` | `label`, `value`, `to`?, `to_say`?, `caption`? | big number, optionally "value → to" |
| `bars` | `heading`, `bars[{label,value,display?,color?,say}]`, `note`? | bar chart revealed bar by bar |
| `donut` | `heading`, `slices[{label,value,display?,say}]`, `center`? | allocation donut |
| `flow` | `heading`, `nodes[{text,sub?,say}]` | process chain with arrows |
| `formula` | `heading`, `formula`, `legend[{sym,text,say}]` | formula and its symbols |
| `takeaway` | `text`, `label`? | key lesson card |
| `line` | `heading`, `series[{name,points:[[x,y]...],at,color?}]`, `xticks`, `yticks`, `notes[{x,y,text,at}]`, `hlines` | line chart; `at` = which `say` sentence reveals it |
| `payoff` | `heading`, `option{kind: call/put, side: buy/sell, strike, premium}`, `from`, `to`, `marks[{k: strike/breakeven/maxloss/maxprofit, at, label?}]` | option payoff at expiry |
| `candles` | `heading`, `candles: [[o,h,l,c]...]` or `preset`, `highlight: [i]`, `highlight_at`, `hlines[{y,kind: support/resistance,label,at}]`, `ma`, `ma_at` | candlestick chart |

Candle presets: `hammer`, `doji`, `bullish_engulfing`, `bearish_engulfing`,
`shooting_star`, `uptrend`, `range`.

Icons: rupee, piggy, shield, up, down, candles, globe, bank, calc, alert,
bulb, clock, umbrella, target, scale, home, card, percent, coins, wallet, pie,
layers, question, check, x, book, heart, users, calendar, flame, lock,
briefcase, building, chart, swap, hourglass, doc, rocket, eye.

## Top-level fields

```yaml
id: "001"                 # matches curriculum.yaml
category: basics          # see categories.yaml
title_ta: "..."           # Tamil title (under ~50 characters)
title_en: "..."           # English title
thumb_ta: "..."           # optional punchier thumbnail text; **word** = accent colour
icon: flame               # thumbnail and intro icon
keywords: [..]            # YouTube tags
summary: [..]             # 3-5 bullet lines for the description
allow_names: []           # rare: names the linter may allow (with a reason comment)
short: {scenes: [..]}
long: {intro_say: "...", scenes: [..]}
```
