from __future__ import annotations

import argparse
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="planter-gen",
        description="Generate a 3D-printable planter sleeve and export STL/3MF.",
    )
    parser.add_argument(
        "--batch",
        type=Path,
        help="Generate multiple models from a UTF-8 JSON or CSV configuration file.",
    )
    parser.add_argument(
        "--batch-output",
        type=Path,
        default=Path("batch_output"),
        help="Output directory for batch models and manifest (default: batch_output).",
    )
    parser.add_argument(
        "--pot-diameter",
        type=float,
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
        "--drain-hole-diameter",
        type=float,
        default=0.0,
        help="Diameter of drainage hole in bottom in mm (default: 0 = no hole).",
    )
    parser.add_argument(
        "--drainage-pattern",
        choices=["center", "radial", "grid", "hex"],
        default="center",
        help="Drainage layout (default: center).",
    )
    parser.add_argument(
        "--drainage-hole-count",
        type=int,
        default=1,
        help="Number of drainage holes for non-center patterns (default: 1).",
    )
    parser.add_argument(
        "--drainage-spacing",
        type=float,
        default=12.0,
        help="Pattern radius or grid pitch in mm (default: 12).",
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
        default=0.0,
        help="Total number of middle-inbound turns along model height in range 0..50 (default: 0).",
    )
    parser.add_argument(
        "--z-rotation",
        type=float,
        default=26.0,
        help="Twist around vertical Z axis in degrees at top height (bottom is always 0, default: 26).",
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
        default="squircle",
        help="Cross-section shape (default: squircle).",
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
        "--print-profile",
        choices=["fine", "standard", "draft", "custom"],
        default="standard",
        help="FDM print profile (default: standard).",
    )
    parser.add_argument(
        "--nozzle-diameter",
        type=float,
        help="Nozzle diameter in mm; defaults to the selected print profile.",
    )
    parser.add_argument(
        "--layer-height",
        type=float,
        help="Layer height in mm; defaults to the selected print profile.",
    )
    parser.add_argument(
        "--auto-repair",
        action="store_true",
        help="Apply conservative printability fixes before generation.",
    )
    parser.add_argument(
        "--text",
        default="",
        help="Text to emboss or engrave on the planter.",
    )
    parser.add_argument(
        "--text-mode",
        choices=["none", "emboss", "engrave"],
        default="emboss",
        help="Boolean text effect (default: emboss).",
    )
    parser.add_argument(
        "--text-height",
        type=float,
        default=5.0,
        help="Text height in mm (default: 5).",
    )
    parser.add_argument(
        "--text-depth",
        type=float,
        default=0.5,
        help="Emboss or engraving depth in mm (default: 0.5).",
    )
    parser.add_argument(
        "--text-position-z",
        type=float,
        help="Text center height in mm (default: automatic center).",
    )
    parser.add_argument(
        "--text-rotation-z",
        type=float,
        default=0.0,
        help="Text placement angle around Z in degrees (default: 0).",
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


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.batch is not None:
        from .batch import generate_batch, parse_batch_data

        try:
            records = parse_batch_data(args.batch.name, args.batch.read_bytes())
            if args.auto_repair:
                records = [{**record, "auto_repair": True} for record in records]
            manifest, exported = generate_batch(records, args.batch_output)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        print(
            f"Batch complete: {manifest['generated_count']} generated, "
            f"{manifest['error_count']} failed."
        )
        print(f"Output directory: {args.batch_output.resolve()}")
        print(f"Written files: {len(exported)}")
        return 1 if manifest["error_count"] else 0

    if args.pot_diameter is None or args.height is None:
        parser.error("--pot-diameter and --height are required unless --batch is used")

    from .model import (
        DrainagePattern,
        ExportFormat,
        GeneratorConfig,
        PrintProfile,
        ShapeType,
        TextMode,
        TextureType,
        build_planter_sleeve,
        export_model,
        repair_config_for_printability,
    )

    from .model import print_profile_dimensions

    profile = PrintProfile(args.print_profile)
    profile_nozzle, profile_layer = print_profile_dimensions(profile)
    nozzle_diameter = (
        args.nozzle_diameter if args.nozzle_diameter is not None else profile_nozzle
    )
    layer_height = args.layer_height if args.layer_height is not None else profile_layer

    inner_diameter = args.pot_diameter + (2.0 * args.clearance)

    config = GeneratorConfig(
        inner_diameter_mm=inner_diameter,
        height_mm=args.height,
        wall_thickness_mm=args.wall,
        base_thickness_mm=args.base,
        include_bottom=not args.no_bottom,
        taper_deg=args.taper,
        rim_lip_mm=args.rim_lip,
        drain_hole_diameter_mm=args.drain_hole_diameter,
        drainage_pattern=DrainagePattern(args.drainage_pattern),
        drainage_hole_count=args.drainage_hole_count,
        drainage_spacing_mm=args.drainage_spacing,
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
        print_profile=profile,
        nozzle_diameter_mm=nozzle_diameter,
        layer_height_mm=layer_height,
        text_content=args.text,
        text_mode=TextMode(args.text_mode),
        text_height_mm=args.text_height,
        text_depth_mm=args.text_depth,
        text_position_z_mm=args.text_position_z,
        text_rotation_z_deg=args.text_rotation_z,
    )

    repairs: list[str] = []
    if args.auto_repair:
        config, repairs = repair_config_for_printability(config)

    model = build_planter_sleeve(config)
    exported = export_model(model, args.output, ExportFormat(args.format))

    print("Generated planter sleeve.")
    print(f"Inner diameter: {config.inner_diameter_mm:.2f} mm")
    print(f"Height: {config.height_mm:.2f} mm")
    if repairs:
        print("Automatic repairs:")
        for repair in repairs:
            print(f" - {repair}")
    print("Written files:")
    for path in exported:
        print(f" - {path}")

    return 0
