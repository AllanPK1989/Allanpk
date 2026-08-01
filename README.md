# 3D Animation Design Skills

Claude Code skill bundle for 3D graphics, motion, image generation, and animation design on the web.
**23 skills, 24 subagents, 43 slash commands, ~18,300 lines of guidance.**

## What's here

Installed under `.claude/`, so any Claude Code session opened in this repo picks it up automatically.

### 3D engines
| Skill | Covers |
|---|---|
| `threejs-webgl` | Three.js scenes, cameras, meshes, materials, lights, textures, WebGL/WebGPU |
| `react-three-fiber` | Declarative 3D in React (R3F), component architecture, drei abstractions |
| `babylonjs-engine` | Babylon.js engine, PBR materials, physics, shadow mapping, model loading |
| `playcanvas-engine` | Entity-component game engine, editor-first workflows, WebGL games |
| `aframe-webxr` | WebXR, VR/AR experiences, 360° media, HTML-first declarative 3D |

### Animation & motion
| Skill | Covers |
|---|---|
| `gsap-scrolltrigger` | GSAP timelines/tweens, ScrollTrigger, pinning, scrubbing, parallax |
| `motion-framer` | Motion / Framer Motion — variants, gestures, layout & exit animations |
| `react-spring-physics` | Spring dynamics, inertia, physics-based natural motion, Popmotion |
| `animejs` | Timeline choreography, stagger, SVG morphing, keyframe sequences |
| `lottie-animations` | After Effects JSON, dotLottie, animated icons, micro-interactions |
| `rive-interactive` | State-machine vector animation, runtime interactivity, data binding |

### Scroll & page transitions
| Skill | Covers |
|---|---|
| `locomotive-scroll` | Smooth scrolling, parallax, viewport detection, horizontal scroll |
| `scroll-reveal-libraries` | AOS — simple fade/slide reveals for marketing pages |
| `barba-js` | Page transitions, SPA-like navigation, transition hooks |

### 2D, effects & components
| Skill | Covers |
|---|---|
| `pixijs-2d` | WebGL-accelerated 2D, sprites, particles, filters, canvas games |
| `lightweight-3d-effects` | Zdog pseudo-3D, Vanta.js backgrounds, Vanilla-Tilt parallax |
| `animated-component-libraries` | Magic UI + React Bits pre-built animated React components |

### Asset pipeline & design
| Skill | Covers |
|---|---|
| `blender-web-pipeline` | Blender → glTF export, `bpy` scripting, LODs, compression, texture baking |
| `substance-3d-texturing` | Substance 3D Painter PBR texturing, export presets, web optimization |
| `spline-interactive` | No-code visual 3D editor, React Spline integration, scene export |
| `modern-web-design` | 2024–25 design trends, micro-interactions, accessibility, performance |
| `web3d-integration-patterns` | Meta-skill: combining the above into coherent multi-library architectures |

### Image generation
| Skill | Covers |
|---|---|
| `nano-banana` | Gemini image models (Nano Banana / Pro) — text→image, image editing, multi-image composition, text-in-image, sketch→photoreal |

### Authoring
| Skill | Covers |
|---|---|
| `skill-creator-upstream` | Scaffolding new skills — `init_skill.py` template generator, structure validator, packager |

Each skill ships `references/` (API guides, optimization checklists), `assets/` (runnable Vite starter
projects), and `scripts/` (Python code generators).

## Usage

Invoke a skill by name, or use a slash command directly. The generators run standalone too:

```bash
python3 .claude/skills/threejs-webgl/scripts/setup_scene.py \
  --renderer webgpu --lighting physical --shadows --antialias --output scene.js
```

### `nano-banana` (locally authored)

The one skill here that is not vendored. Wraps Google's Gemini image models through the
`generateContent` API — generation, image-to-image editing, multi-reference composition,
text rendering, and technical-drawing→photoreal conversion.

```bash
export GEMINI_API_KEY="..."   # https://aistudio.google.com/apikey

.claude/skills/nano-banana/scripts/nano_banana.py models          # what this key can reach
.claude/skills/nano-banana/scripts/nano_banana.py generate \
  "A weathered brass sextant on a navigator's chart, morning window light, 85mm" \
  -o out/sextant.png -a 3:2

.claude/skills/nano-banana/scripts/sketch_to_photo.py drawing.png -o out/machine.png \
  --subject "7-station automated dispensing machine" --preset factory
```

Both scripts are standard library only — no `pip install`. Slash commands:
`/nano-banana-generate`, `/nano-banana-sketch_to_photo`. Subagent:
`nano-banana-image-director`. Model IDs move as previews reach GA, so the `models`
subcommand queries the live list rather than trusting the table in the skill.

## Provenance

The 22 design/animation skills are sourced from
[freshtechbro/claudedesignskills](https://github.com/freshtechbro/claudedesignskills)
(MIT, upstream license retained at `.claude/skills/UPSTREAM-LICENSE`). Vendored rather than
referenced so the content is pinned and reviewable in-tree.

Upstream's `skill-creator` is installed as **`skill-creator-upstream`**. It is a smaller, older
variant of the `skill-creator` built into Claude Code (5 files / 209 lines vs 18 files / 485 lines;
the built-in adds eval, benchmarking, and description-optimization tooling that upstream lacks).
Because the two share a name, installing it verbatim would have collided with the built-in, so it
carries a suffixed directory and matching frontmatter `name:` — both are now usable side by side.

It is worth having for one thing the built-in does not provide: `scripts/init_skill.py`, which
scaffolds a new skill directory (SKILL.md + `scripts/`, `references/`, `assets/` examples) from a
template. Use the built-in `skill-creator` for evaluating and optimizing skills.

To install it under the bare name instead, accepting that it shadows the built-in:

```bash
git mv .claude/skills/skill-creator-upstream .claude/skills/skill-creator
sed -i 's/^name: skill-creator-upstream$/name: skill-creator/' .claude/skills/skill-creator/SKILL.md
```

## Verification

Reviewed before install: no hooks, no MCP servers, and no network, credential-access, or
prompt-injection patterns. Two flagged code sites were read and cleared as benign — a socket.io
`<script>` tag inside a *generated* multiplayer WebXR template (output, not executed at install),
and an `npm install` in the barba-js scaffolder, gated behind `--no-install` and only reachable on
explicit invocation.

Frontmatter validated across all 22 vendored skills. All 43 bundled generators were executed:

- **39** run standalone.
- **4** require a host application by design — `blender-web-pipeline` (3 scripts, need Blender's
  `bpy`) and `substance-3d-texturing/batch_export.py` (runs inside Substance 3D Painter).
- **0** broken.

### Local fixes to upstream

Two generators were shipped broken upstream and are patched here. Both were template-escaping
defects that made the files fail to parse — they could never have run as published:

- `react-three-fiber/scripts/component_generator.py` — JSX event handlers and 5 JSX comments
  (`{/* … */}`) were left unescaped inside f-strings (`SyntaxError`).
- `playcanvas-engine/scripts/component_builder.py` — the `COMPONENT_TYPES` registry was written with
  doubled braces outside an f-string, so it parsed as a set of dicts (`TypeError: unhashable type`).

Both now generate correct output, verified by running them and inspecting the emitted JSX/JS.
