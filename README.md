# 3D Animation Design Skills

Vendored Claude Code skill bundle for 3D graphics, motion, and animation design on the web.

## What's here

Installed under `.claude/`, so any Claude Code session opened in this repo picks it up automatically.

| Skill | Covers |
|---|---|
| `threejs-webgl` | Three.js scenes, cameras, meshes, materials, lights, textures, WebGL/WebGPU |
| `react-three-fiber` | Declarative 3D in React (R3F), component architecture, drei abstractions |
| `babylonjs-engine` | Babylon.js engine, PBR materials, physics, shadow mapping, model loading |
| `gsap-scrolltrigger` | GSAP timelines/tweens, ScrollTrigger, pinning, scrubbing, parallax |
| `motion-framer` | Motion / Framer Motion — variants, gestures, layout & exit animations, springs |

Also included: **6 subagents** (`.claude/agents/`) and **9 slash commands** (`.claude/commands/`), e.g.
`/threejs-webgl-setup_scene`, `/react-three-fiber-scene_setup`, `/gsap-scrolltrigger-timeline_builder`,
`/motion-framer-variant_builder`, `/babylonjs-engine-mesh_builder`.

Each skill ships `references/` (API guides, optimization checklists), `assets/` (runnable Vite starter
projects), and `scripts/` (Python code generators).

## Usage

Invoke a skill by name, or use a slash command directly. The generators run standalone too:

```bash
python3 .claude/skills/threejs-webgl/scripts/setup_scene.py \
  --renderer webgpu --lighting physical --shadows --antialias --output scene.js
```

## Provenance

Sourced from the `core-3d-animation` bundle of
[freshtechbro/claudedesignskills](https://github.com/freshtechbro/claudedesignskills) (MIT, upstream
license retained at `.claude/skills/UPSTREAM-LICENSE`). Vendored rather than referenced so the
content is pinned and reviewable in-tree.

Reviewed before install: no hooks, no MCP servers, and no network, subprocess, filesystem-escape,
credential-access, or prompt-injection patterns found in the bundle. All five `SKILL.md` files were
validated for correct frontmatter, and a bundled generator was executed to confirm it runs.
