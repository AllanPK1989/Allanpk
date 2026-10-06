# நிதி அறிவு: Tamil finance videos, one concept a day

An automated pipeline for a Tamil YouTube channel that teaches personal finance
and investing basics, one concept per video, with your approval before
anything is published.

Every day it renders **two videos per topic**:

| | Short | Long video |
|---|---|---|
| Format | 1080×1920 vertical (YouTube Shorts) | 1920×1080 horizontal |
| Length | ~45-60 s | ~2.5-4 min, with chapters |
| Extras | burned-in Tamil captions | burned-in captions, custom thumbnail, chapters |

The narration is a Tamil neural AI voice (Microsoft `ta-IN-PallaviNeural` via
[edge-tts]; switch to the male `ta-IN-ValluvarNeural` in `config.yaml`), or
**your own voice**: record the day's sentences on your phone and the videos
are re-rendered with your recording (see below). Every video ends with a spoken and on-screen disclaimer, and F&O topics also carry
SEBI's "9 out of 10 traders lose" risk statement.

## How a day works

```
07:00 IST  Daily workflow picks the next topic in curriculum.yaml
           ├─ (no script yet + ANTHROPIC_API_KEY set) → Claude writes one; the linter must pass
           ├─ compliance lint (no stock names, buy/sell calls, return promises…)
           ├─ renders Short + long video + thumbnail (about 3 minutes)
           ├─ uploads the files to a pre-release "video-NNN" for preview
           └─ opens an issue: "🎬 Approve #N: …", assigned to you

You        watch the preview on your phone, then reply on the issue (or to the email):
           /approve          → scheduled for the next free 6:00 PM IST slot
           /approve now      → published immediately
           /approve short    → only the Short (or: /approve long)
           /reject <reason>  → skipped; the next topic comes tomorrow
           /rerender         → after you edit the script on GitHub, render again
           /voice + zip      → re-render in your own recorded voice (optional)

Approval   publish.mode: manual  → the bot replies with a ready-to-post kit
                                   (download links, title, description, tags)
           publish.mode: youtube → the bot uploads and schedules it on YouTube
```

If you approve several at once, each gets its own day, so the channel still
posts one topic per day. When three videos are already waiting, the daily job
pauses until you catch up.

**First-time setup is in [docs/SETUP.md](docs/SETUP.md).**

## The English channel

A second channel posts the same lesson every day in English, from the same
curriculum and the same daily run. Each topic's Tamil script stays the source:
the English script (`content/en/NNN-*.yaml`) is an English adaptation of it
with the same scenes, numbers and charts, written by Claude
(`python -m pipeline --channel en translate NNN`) and linted with the same
rules. The English videos use an Indian English AI voice (`en-IN-NeerjaNeural`)
and English titles, descriptions, tags and disclaimers.

Everything is a per-channel setting in `channels/en.yaml`, which starts from
`config.yaml` and overrides what differs. The English channel has its own
queue (`state/en/items/`), its own preview releases (`video-en-NNN`) and its
own approval issues, titled `[EN] Approve #N`, so you can approve, reject or
re-render each language on its own. Uploads use their own refresh token
(`YT_EN_REFRESH_TOKEN`; see docs/SETUP.md, step 7). Recording your own voice
is Tamil-only for now.

## Narrating in your own voice

Each approval issue has an **Open the recorder** link. It opens a small page
(hosted on GitHub Pages) that shows one sentence at a time:

1. Tap the red **●** button, read the sentence exactly as written, tap it
   again to stop. **▶ Play** to listen; **↺ Delete take** to redo it. A topic is roughly 35-65
   sentences, about 10-15 minutes. The page remembers your takes, so you can
   stop and come back.
2. Tap **Save zip**.
3. On the approval issue, comment `/voice` and attach the zip (drag it in, or
   use the 📎 button in the GitHub app).

The bot cleans each clip (removes rumble and background hiss, trims the
silence at both ends, evens out the volume), re-renders both videos with your
recording and posts a new preview. If any sentence is missing or silent, it
lists which ones; record just those, save the zip again and resend `/voice`.
The on-screen captions, timing and animations follow your pace automatically.

Tips: record in a quiet room with soft furnishings, keep the phone about a
hand-width from your mouth, and keep the same distance and energy for every
sentence so the clips sound like one take.

## What's in here

| Path | What it is |
|---|---|
| `curriculum.yaml` | 150 topics in posting order, across 9 categories |
| `content/NNN-*.yaml` | the scripts: what's on screen and what the voice says. 001-030 are written |
| `content/en/NNN-*.yaml` | the English channel's scripts, adapted from the Tamil ones |
| `config.yaml` | channel name, voice, publish time, disclaimers, pronunciation fixes |
| `channels/en.yaml` | the English channel: what differs from `config.yaml` |
| `compliance.yaml` | the education-only guardrails (blocked phrases, named securities) |
| `categories.yaml` | category labels and colours |
| `docs/WRITING_GUIDE.md` | how to write or edit a script; also the spec Claude writes to |
| `pipeline/` | Python: TTS, Chromium frame rendering, ffmpeg, metadata, YouTube upload |
| `state/items/NNN.json` | per topic: rendered, approved, scheduled or rejected (`state/en/items/` for English) |
| `voice-scripts/NNN.json` | the sentences to record for each topic (read by the recorder page) |
| `recorder/` | the recorder page, deployed to GitHub Pages |

Topics by category: investing 28 · stocks 22 · fundamental analysis 19 ·
technical analysis 18 · futures & options 18 · basics 14 · insurance 11 ·
global investing 11 · savings 9.

## Editing content

- **Change a script:** edit `content/NNN-*.yaml` on GitHub (pencil icon). CI
  lints it and renders a voiced preview, attached to the `ci-preview`
  release. If it's already waiting for approval, comment `/rerender`.
- **Reorder topics:** move entries in `curriculum.yaml` (only ones not yet rendered).
- **Fix a mispronunciation:** add the word to `pronounce:` in `config.yaml`.
  It changes only what the voice says, not the captions.
- **Background music:** drop royalty-free `.mp3` files (for example from the
  YouTube Audio Library) into `assets/music/`.

## Staying on the education side of SEBI's rules

You are not a SEBI-registered adviser, so the channel only explains concepts.
The guardrails:

- Scripts never name a stock, fund, AMC, broker or insurer, never say
  buy/sell/target, and never promise returns. The linter blocks these, and the
  approval issue lists anything borderline for you to check.
- All numbers are made-up examples, labelled as such, and no real or recent
  market prices are used. SEBI's January 2025 circular bars education-only
  creators from using market price data from the last 3 months.
- A disclaimer is spoken, shown on screen and written in the description of
  every video.
- **Things you should avoid too:** broker or app referral links, paid
  promotions for financial products, "tips" groups, and answering "should I
  buy X?" in comments. SEBI's rules restrict regulated entities from working
  with unregistered creators who give advice or claim returns, and these are
  the easiest ways to cross that line.

This is general information, not legal advice. If you plan to monetise
heavily or work with brands, consider a quick consultation with a securities
lawyer.

## Commands (run from `finance-channel/`)

```bash
pip install -r requirements.txt && python -m playwright install chromium
python -m pipeline lint                 # check every script
python -m pipeline sheet 012            # one image of every scene (fast, no audio)
python -m pipeline render 012           # full Short + long video into out/012/
python -m pipeline render 012 --tts silent   # timing-only render, no network
python -m pipeline status               # the queue
python -m pipeline voice-script 012     # sentence list for the recorder
python -m pipeline voice-import 012 012-voice.zip   # clean a recording into .cache/voice/012/
python -m pipeline render 012 --voice-dir .cache/voice/012   # render with your voice
python -m pipeline --channel en translate 012   # English script from the Tamil one (needs ANTHROPIC_API_KEY)
python -m pipeline --channel en render 012      # any command, for the English channel (into out/en/012/)
python -m pytest tests -q
```

[edge-tts]: https://github.com/rany2/edge-tts
