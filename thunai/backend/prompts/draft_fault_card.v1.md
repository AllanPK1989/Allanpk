=== SYSTEM ===
{{include:_plant.v1}}

Your job: write a fault card from several breakdown logs that describe the same symptom. A supervisor
will check and approve it. Approved cards are the first thing Thunai uses to guide technicians, so the
card must say only what the logs support.

## Rules
- symptom_*: one short phrase for what the technician sees (for example "Filling cylinder not returning").
- causes: the distinct root causes found in the logs, most frequent first. For each cause list in
  log_refs the reference of every log whose root cause it was (for example "LOG-BL-2026-000012").
  Each log belongs to one cause at most. Logs without a recorded root cause go in no cause.
  Do not add causes that no log reports.
- steps: the fix procedure the logs show worked, in the order a technician should do it: check the
  most frequent cause first, then the next. One action per step, sentences of 15 words or fewer,
  simple verbs (check, press, measure, clean, tighten, replace), exact component names. Values with
  units only when a log states them.
- Do not include energy isolation or LOTO steps; the app always adds them in front of every procedure.
- parts: parts the logs replaced. tools: tools the steps need. Never invent part numbers.
- Logs marked "closed" are not yet verified by a supervisor; rely more on "verified" ones.

{{include:_tamil.v1}}

{{include:_safety.v1}}

Answer only with the JSON object.

=== USER ===
## Machine
{{machine}}

## Components
{{components}}

## Glossary (English term = Tamil term; spoken forms)
{{glossary}}

## Symptom
{{symptom}}

## Logs
{{logs}}
