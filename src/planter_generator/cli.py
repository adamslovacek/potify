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
        default=1.5,
        help="Wall taper in degrees, positive means wider at top (default: 1.5).",
    )
    parser.add_argument(
        "--rim-lip",
        type=float,
        default=1.2,
        help="Extra outer lip around top rim in mm (default: 1.2).",
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
        default=0.0,
        help="Rotate generated geometry around vertical Z axis in degrees (default: 0).",
    )
    parser.add_argument(
        "--twist-turns",
        dest="middle_inbound",
        type=float,
        help="Legacy alias for --middle-inbound.",
    )
    parser.add_argument(
        "--sections",
        type=int,
        default=192,
        help="Circular resolution segments (default: 192).",
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

    from .model import ExportFormat, GeneratorConfig, build_planter_sleeve, export_model

    inner_diameter = args.pot_diameter + (2.0 * args.clearance)

    config = GeneratorConfig(
        inner_diameter_mm=inner_diameter,
        height_mm=args.height,
        wall_thickness_mm=args.wall,
        base_thickness_mm=args.base,
        include_bottom=not args.no_bottom,
        taper_deg=args.taper,
        rim_lip_mm=args.rim_lip,
        middle_inbound_turns=args.middle_inbound,
        z_rotation_deg=args.z_rotation,
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
