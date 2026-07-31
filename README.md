# 3D Animation Design Skills

Vendored Claude Code skill bundle for 3D graphics, motion, and animation design on the web.
**22 skills, 23 subagents, 41 slash commands, ~17,700 lines of guidance.**

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

Each skill ships `references/` (API guides, optimization checklists), `assets/` (runnable Vite starter
projects), and `scripts/` (Python code generators).

## Usage

Invoke a skill by name, or use a slash command directly. The generators run standalone too:

```bash
python3 .claude/skills/threejs-webgl/scripts/setup_scene.py \
  --renderer webgpu --lighting physical --shadows --antialias --output scene.js
```

## Provenance

Sourced from [freshtechbro/claudedesignskills](https://github.com/freshtechbro/claudedesignskills)
(MIT, upstream license retained at `.claude/skills/UPSTREAM-LICENSE`). Vendored rather than
referenced so the content is pinned and reviewable in-tree.

Not installed: upstream also ships a `skill-creator` skill, which is an older, less capable copy of
the one built into Claude Code (no evals or benchmarking). Installing it would shadow the better
version, so it was deliberately skipped.

## Verification

Reviewed before install: no hooks, no MCP servers, and no network, credential-access, or
prompt-injection patterns. Two flagged code sites were read and cleared as benign — a socket.io
`<script>` tag inside a *generated* multiplayer WebXR template (output, not executed at install),
and an `npm install` in the barba-js scaffolder, gated behind `--no-install` and only reachable on
explicit invocation.

Frontmatter validated across all 22 skills. All 43 bundled generators were executed:

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
