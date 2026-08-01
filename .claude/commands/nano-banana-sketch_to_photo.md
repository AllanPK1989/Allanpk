# /nano-banana-sketch_to_photo

Nano Banana - Turn a sketch or CAD drawing into a photoreal render

## Description

Converts a line drawing, patent figure, CAD export, wireframe or concept sketch into a
photorealistic image, while stripping the drawing's annotation layer (reference numerals,
leader lines, dimension arrows, callouts) instead of rendering it onto the object.

## Usage

```bash
/nano-banana-sketch_to_photo drawing.png
```

## Implementation

Runs `.claude/skills/nano-banana/scripts/sketch_to_photo.py`:

```bash
.claude/skills/nano-banana/scripts/sketch_to_photo.py drawing.png -o out/machine.png \
  --subject "7-station automated dispensing machine with pneumatic cylinders and an HMI" \
  --preset factory --model pro --size 2K
```

Presets: `studio`, `factory`, `workshop`, `white`. Use `--print-prompt` to review and tune
the generated prompt before spending a call.

## Notes

- Always pass `--subject` in plain words - naming what the machine *is* raises fidelity
  more than any other option
- `--materials` overrides the default industrial material description
- Defaults to the `pro` model, which holds fine mechanical detail best
- Requires `GEMINI_API_KEY` in the environment
