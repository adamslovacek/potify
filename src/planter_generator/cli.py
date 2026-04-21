from __future__ import annotations

import argparse
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="planter-gen",
        description="Generate a 3D-printable planter sleeve and export STL/3MF.",
    )
    parser.add_argument(
        "--pot-diameter",
        type=float,
        required=True,
        help="Outer diameter of the inner pot in mm.",
    )
    parser.add_argument(
        "--clearance",
        type=float,
        default=1.2,
        help="Radial fit clearance in mm added around the pot (default: 1.2).",
    )
    parser.add_argument(
        "--height",
        type=float,
        required=True,
        help="Sleeve height in mm.",
    )
    parser.add_argument(
        "--wall",
        type=float,
        default=3.0,
        help="Wall thickness in mm (default: 3.0).",
    )
    parser.add_argument(
        "--base",
        type=float,
        default=4.0,
        help="Base thickness in mm (default: 4.0).",
    )
    parser.add_argument(
        "--no-bottom",
        action="store_true",
        help="Generate sleeve without bottom (open-bottom variant).",
    )
    parser.add_argument(
        "--taper",
        type=float,
        default=1.9,
        help="Wall taper in degrees, positive means wider at top (default: 1.9).",
    )
    parser.add_argument(
        "--rim-lip",
        type=float,
        default=1.4,
        help="Extra outer lip around top rim in mm (default: 1.4).",
    )
    parser.add_argument(
        "--texture-type",
        choices=["none", "rings", "micro_rings", "spiral", "braid", "grid", "hex", "hammered"],
        default="braid",
        help="Surface texture pattern (default: braid).",
    )
    parser.add_argument(
        "--texture-strength",
        type=float,
        default=0.9,
        help="Texture displacement strength in mm (default: 0.9).",
    )
    parser.add_argument(
        "--texture-scale",
        type=float,
        default=2.4,
        help="Legacy uniform texture scale applied to U and V (default: 2.4).",
    )
    parser.add_argument(
        "--texture-scale-u",
        type=float,
        help="Texture scale along circumferential U axis.",
    )
    parser.add_argument(
        "--texture-scale-v",
        type=float,
        help="Texture scale along vertical V axis.",
    )
    parser.add_argument(
        "--texture-offset-u",
        type=float,
        default=0.0,
        help="Texture U offset (tile space, default: 0).",
    )
    parser.add_argument(
        "--texture-offset-v",
        type=float,
        default=0.0,
        help="Texture V offset (tile space, default: 0).",
    )
    parser.add_argument(
        "--texture-rotation",
        type=float,
        default=28.0,
        help="Texture rotation in degrees (default: 28).",
    )
    parser.add_argument(
        "--middle-inbound",
        type=float,
        default=1.8,
        help="Total number of middle-inbound turns along model height in range 0..50 (default: 1.8).",
    )
    parser.add_argument(
        "--z-rotation",
        type=float,
        default=220.0,
        help="Twist around vertical Z axis in degrees at top height (bottom is always 0, default: 220).",
    )
    parser.add_argument(
        "--twist-turns",
        dest="middle_inbound",
        type=float,
        help="Legacy alias for --middle-inbound.",
    )
    parser.add_argument(
        "--shape-type",
        choices=[
            "polygon",
            "star",
            "ellipse",
            "rounded_square",
            "diamond",
            "squircle",
            "clover",
            "scallop",
            "gear",
            "flower",
            "teardrop",
            "lens",
        ],
        default="flower",
        help="Cross-section shape (default: flower).",
    )
    parser.add_argument(
        "--star-inner-ratio",
        type=float,
        default=0.45,
        help="Inner star point radius ratio (0.1..0.9) for star shapes (default: 0.45).",
    )
    parser.add_argument(
        "--shape-aspect-ratio",
        type=float,
        default=1.0,
        help="Aspect ratio for ellipse-like shapes in range 0.4..2.5 (default: 1.0).",
    )
    parser.add_argument(
        "--shape-roundness",
        type=float,
        default=0.35,
        help="Corner softness or tooth softness in range 0..1 (default: 0.35).",
    )
    parser.add_argument(
        "--shape-wave-depth",
        type=float,
        default=0.6,
        help="Depth for clover/scallop/flower/teardrop/lens modulation in range 0..0.95 (default: 0.6).",
    )
    parser.add_argument(
        "--shape-wave-count",
        type=int,
        default=8,
        help="Wave or petal count for supported shapes in range 2..24 (default: 8).",
    )
    parser.add_argument(
        "--sections",
        type=int,
        default=7,
        help="Primary divisions or side count for shape generation (default: 7).",
    )
    parser.add_argument(
        "--format",
        choices=["stl", "3mf", "both"],
        default="both",
        help="Export format: stl, 3mf, both (default: both).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output") / "planter_sleeve",
        help="Output path without extension (default: output/planter_sleeve).",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    from .model import ExportFormat, GeneratorConfig, ShapeType, TextureType, build_planter_sleeve, export_model

    inner_diameter = args.pot_diameter + (2.0 * args.clearance)

    config = GeneratorConfig(
        inner_diameter_mm=inner_diameter,
        height_mm=args.height,
        wall_thickness_mm=args.wall,
        base_thickness_mm=args.base,
        include_bottom=not args.no_bottom,
        taper_deg=args.taper,
        rim_lip_mm=args.rim_lip,
        texture_type=TextureType(args.texture_type),
        texture_strength_mm=args.texture_strength,
        texture_scale=args.texture_scale,
        texture_scale_u=args.texture_scale_u,
        texture_scale_v=args.texture_scale_v,
        texture_offset_u=args.texture_offset_u,
        texture_offset_v=args.texture_offset_v,
        texture_rotation_deg=args.texture_rotation,
        middle_inbound_turns=args.middle_inbound,
        z_rotation_deg=args.z_rotation,
        shape_type=ShapeType(args.shape_type),
        star_inner_ratio=args.star_inner_ratio,
        shape_aspect_ratio=args.shape_aspect_ratio,
        shape_roundness=args.shape_roundness,
        shape_wave_depth=args.shape_wave_depth,
        shape_wave_count=args.shape_wave_count,
        sections=args.sections,
    )

    model = build_planter_sleeve(config)
    exported = export_model(model, args.output, ExportFormat(args.format))

    print("Generated planter sleeve.")
    print(f"Inner diameter: {config.inner_diameter_mm:.2f} mm")
    print(f"Height: {config.height_mm:.2f} mm")
    print("Written files:")
    for path in exported:
        print(f" - {path}")

    return 0
