#!/usr/bin/env python3
"""
Turn a line drawing into a photoreal render with Nano Banana.

Built for the case that trips people up most: a CAD / patent / engineering
sketch covered in leader lines and reference numerals, where a naive prompt
gives you a photo of a machine *with the numbers baked into it*. The prompt
this builds pins the geometry to the drawing and explicitly discards the
annotation layer.

Usage:
    ./sketch_to_photo.py drawing.png -o out/machine.png \
        --subject "7-station automated dispensing machine" \
        --context "factory floor, industrial lighting"

    ./sketch_to_photo.py part.jpg --preset studio --print-prompt
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

PRESETS = {
    "studio": (
        "Studio product photograph: seamless light-grey background, large softbox key light "
        "from the upper left, subtle fill, soft contact shadow on the floor, "
        "shot on a 50mm lens at f/8, even focus across the whole machine."
    ),
    "factory": (
        "In a working factory: clean epoxy-coated concrete floor, other equipment softly "
        "out of focus in the background, overhead fluorescent and daylight mix, "
        "shot on a 35mm lens at f/4."
    ),
    "workshop": (
        "In an engineering workshop: workbenches and tooling blurred in the background, "
        "warm practical lighting with daylight through a window, 35mm lens, shallow depth of field."
    ),
    "white": (
        "Isolated on a pure white background with no floor shadow, catalogue/e-commerce style, "
        "flat even lighting, every surface clearly readable."
    ),
}

MATERIALS_DEFAULT = (
    "anodised aluminium extrusion frame, brushed stainless steel panels, "
    "powder-coated steel base cabinet, clear acrylic guarding, black cable looms"
)


def build_prompt(args):
    subject = args.subject or "the machine shown in the drawing"
    scene = args.context or PRESETS[args.preset]
    materials = args.materials or MATERIALS_DEFAULT

    lines = [
        f"Produce a photorealistic photograph of {subject}, built exactly as drawn in the "
        "attached technical drawing.",
        "",
        "Geometry: reproduce the drawing's proportions, layout and part positions faithfully - "
        "same number of stations/modules, same frame structure, same placement of every component. "
        "Treat the drawing as the engineering spec, not as loose inspiration.",
        "",
        f"Materials and finish: {materials}. Real surface response - specular highlights on metal, "
        "fine brushed texture, visible panel seams, fasteners, hinges and weld lines where parts meet.",
        "",
        f"Scene and camera: {scene} Three-quarter view matching the drawing's isometric viewpoint, "
        "camera at roughly eye level.",
        "",
        "Critical: the drawing's annotation layer is NOT part of the object. Omit every reference "
        "numeral, leader line, arrow, callout, bracket, dimension line, hatching and title-block "
        "marking. Render only the physical machine itself. No text, no labels, no watermarks "
        "anywhere in the image - except any signage that would genuinely exist on real equipment.",
        "",
        "Photographic realism: natural lighting falloff and soft shadows, accurate reflections, "
        "slight surface imperfections and dust, real-world colour grading. "
        "Not a 3D render, not CGI, not an illustration - an actual photograph of real hardware.",
    ]
    if args.extra:
        lines += ["", args.extra]
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("sketch", help="path to the line drawing / CAD sketch")
    p.add_argument("-o", "--output", default="photoreal.png", help="output path")
    p.add_argument("--subject", help="what the machine is, in plain words - improves fidelity a lot")
    p.add_argument("--context", help="custom scene description (overrides --preset)")
    p.add_argument("--preset", default="studio", choices=sorted(PRESETS), help="scene preset (default: studio)")
    p.add_argument("--materials", help=f"material description (default: {MATERIALS_DEFAULT})")
    p.add_argument("--extra", help="extra instructions appended to the prompt")
    p.add_argument("-m", "--model", default="pro", help="model alias (default: pro - best at holding fine detail)")
    p.add_argument("-a", "--aspect", default="4:3", help="aspect ratio (default: 4:3)")
    p.add_argument("-s", "--size", default="2K", help="image size (default: 2K)")
    p.add_argument("-n", type=int, default=1, help="number of variants")
    p.add_argument("--print-prompt", action="store_true", help="print the prompt and exit")
    args = p.parse_args()

    prompt = build_prompt(args)
    if args.print_prompt:
        print(prompt)
        return

    if not os.path.isfile(args.sketch):
        sys.exit(f"Sketch not found: {args.sketch}")

    cmd = [
        sys.executable, os.path.join(HERE, "nano_banana.py"), "generate", prompt,
        "-i", args.sketch, "-o", args.output,
        "-m", args.model, "-a", args.aspect, "-s", args.size, "-n", str(args.n),
    ]
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
