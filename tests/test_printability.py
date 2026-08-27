from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from planter_generator.model import (
    DrainagePattern,
    GeneratorConfig,
    PrintProfile,
    ShapeType,
    TextMode,
    TextureType,
    analyze_printability,
    build_planter_sleeve,
    repair_config_for_printability,
)


def make_config(**overrides):
    base = {
        "inner_diameter_mm": 140.0,
        "height_mm": 135.0,
        "wall_thickness_mm": 3.0,
        "base_thickness_mm": 4.0,
        "include_bottom": True,
        "taper_deg": 1.9,
        "rim_lip_mm": 1.4,
        "texture_type": TextureType.BRAID,
        "texture_strength_mm": 0.9,
        "texture_scale": 2.4,
        "texture_scale_u": 2.4,
        "texture_scale_v": 2.4,
        "texture_offset_u": 0.0,
        "texture_offset_v": 0.0,
        "texture_rotation_deg": 28.0,
        "middle_inbound_turns": 0.0,
        "middle_inbound_z_mm": 50.0,
        "z_rotation_deg": 26.0,
        "shape_type": ShapeType.SQUIRCLE,
        "star_inner_ratio": 0.45,
        "shape_aspect_ratio": 1.0,
        "shape_roundness": 0.35,
        "shape_wave_depth": 0.6,
        "shape_wave_count": 8,
        "sections": 7,
        "height_steps": 64,
        "drain_hole_diameter_mm": 0.0,
    }
    base.update(overrides)
    return GeneratorConfig(**base)


def test_analyze_printability_returns_empty_for_reasonable_config():
    warnings = analyze_printability(make_config())
    assert warnings == []


def test_short_model_uses_automatic_middle_inbound_position():
    config = GeneratorConfig(inner_diameter_mm=40.0, height_mm=45.0)

    config.validate()

    assert config.middle_inbound_z_mm is None


def test_analyze_printability_flags_common_risks():
    cfg = make_config(
        wall_thickness_mm=0.9,
        base_thickness_mm=0.8,
        taper_deg=6.2,
        texture_strength_mm=1.0,
        height_mm=160.0,
        sections=260,
        drain_hole_diameter_mm=1.0,
    )
    warnings = analyze_printability(cfg)

    assert any("Wall thickness" in item for item in warnings)
    assert any("Base thickness" in item for item in warnings)
    assert any("Taper" in item for item in warnings)
    assert any("Texture strength" in item for item in warnings)
    assert any("Tall and slender" in item for item in warnings)
    assert any("section count" in item for item in warnings)
    assert any("Drain hole" in item for item in warnings)


def test_print_profile_drives_warnings_and_auto_repair():
    config = make_config(
        print_profile=PrintProfile.DRAFT,
        nozzle_diameter_mm=0.6,
        layer_height_mm=0.3,
        wall_thickness_mm=0.9,
        base_thickness_mm=0.8,
        taper_deg=6.2,
        texture_strength_mm=2.0,
        sections=240,
        drain_hole_diameter_mm=0.8,
    )

    warnings = analyze_printability(config)
    repaired, repairs = repair_config_for_printability(config)

    assert any("0.6 mm nozzle" in warning for warning in warnings)
    assert repaired.wall_thickness_mm == pytest.approx(1.8)
    assert repaired.base_thickness_mm == pytest.approx(1.8)
    assert repaired.drain_hole_diameter_mm == pytest.approx(1.8)
    assert repaired.texture_strength_mm <= repaired.wall_thickness_mm * 0.65
    assert repaired.taper_deg == pytest.approx(5.0)
    assert repaired.sections == 220
    assert len(repairs) >= 6


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"sections": 257}, "sections must be <= 256"),
        ({"height_steps": 257}, "height_steps must be <= 256"),
        ({"text_content": "x" * 51}, "text_content must be at most 50 characters"),
        ({"text_height_mm": 20.1}, "text_height_mm must be <= 20"),
        ({"text_depth_mm": 2.1}, "text_depth_mm must be <= 2"),
        (
            {"include_bottom": False, "drain_hole_diameter_mm": 4.0},
            "drain_hole_diameter_mm requires include_bottom",
        ),
    ],
)
def test_validate_rejects_unbounded_mesh_inputs(overrides, message):
    with pytest.raises(ValueError, match=message):
        make_config(**overrides).validate()


@pytest.mark.parametrize(
    "pattern",
    [DrainagePattern.RADIAL, DrainagePattern.GRID, DrainagePattern.HEX],
)
def test_multi_hole_drainage_patterns_produce_watertight_lower_volume_mesh(pattern):
    center_mesh = build_planter_sleeve(make_config(
        shape_type=ShapeType.POLYGON,
        texture_type=TextureType.NONE,
        z_rotation_deg=0.0,
        sections=48,
        drain_hole_diameter_mm=4.0,
        drainage_pattern=DrainagePattern.CENTER,
    ))
    drained_mesh = build_planter_sleeve(
        make_config(
            shape_type=ShapeType.POLYGON,
            texture_type=TextureType.NONE,
            z_rotation_deg=0.0,
            sections=48,
            drain_hole_diameter_mm=4.0,
            drainage_pattern=pattern,
            drainage_hole_count=4,
            drainage_spacing_mm=16.0,
        )
    )

    assert drained_mesh.is_watertight
    assert center_mesh.is_watertight
    assert drained_mesh.volume < center_mesh.volume - 100.0


def test_drainage_pattern_rejects_overlapping_holes():
    with pytest.raises(ValueError, match="drainage holes overlap"):
        make_config(
            drain_hole_diameter_mm=5.0,
            drainage_pattern=DrainagePattern.GRID,
            drainage_hole_count=4,
            drainage_spacing_mm=3.0,
        ).validate()


def test_drainage_pattern_rejects_holes_outside_star_floor():
    with pytest.raises(ValueError, match="drainage pattern does not fit inside the planter floor"):
        GeneratorConfig(
            inner_diameter_mm=60.0,
            height_mm=60.0,
            shape_type=ShapeType.STAR,
            sections=4,
            star_inner_ratio=0.45,
            drain_hole_diameter_mm=4.0,
            drainage_pattern=DrainagePattern.RADIAL,
            drainage_hole_count=8,
            drainage_spacing_mm=12.0,
        ).validate()


def test_boolean_text_modes_produce_watertight_volume_changes():
    common = {
        "shape_type": ShapeType.POLYGON,
        "texture_type": TextureType.NONE,
        "z_rotation_deg": 0.0,
        "sections": 64,
        "text_content": "POT",
        "text_height_mm": 8.0,
        "text_depth_mm": 0.8,
        "text_position_z_mm": 60.0,
    }
    base_mesh = build_planter_sleeve(make_config(**common, text_mode=TextMode.NONE))
    embossed_mesh = build_planter_sleeve(make_config(**common, text_mode=TextMode.EMBOSS))
    engraved_mesh = build_planter_sleeve(make_config(**common, text_mode=TextMode.ENGRAVE))

    assert embossed_mesh.is_watertight
    assert engraved_mesh.is_watertight
    assert embossed_mesh.volume > base_mesh.volume
    assert engraved_mesh.volume < base_mesh.volume


def test_boolean_text_modes_work_on_default_textured_squircle():
    plain = build_planter_sleeve(
        GeneratorConfig(
            inner_diameter_mm=80.0,
            height_mm=90.0,
            text_content="POT",
            text_mode=TextMode.NONE,
        )
    )
    embossed = build_planter_sleeve(
        GeneratorConfig(
            inner_diameter_mm=80.0,
            height_mm=90.0,
            text_content="POT",
            text_mode=TextMode.EMBOSS,
        )
    )
    engraved = build_planter_sleeve(
        GeneratorConfig(
            inner_diameter_mm=80.0,
            height_mm=90.0,
            text_content="POT",
            text_mode=TextMode.ENGRAVE,
        )
    )

    assert embossed.is_watertight and embossed.body_count == 1
    assert engraved.is_watertight and engraved.body_count == 1
    assert embossed.volume > plain.volume
    assert engraved.volume < plain.volume


def test_open_bottom_sleeve_is_watertight_and_supports_boolean_text():
    mesh = build_planter_sleeve(
        GeneratorConfig(
            inner_diameter_mm=60.0,
            height_mm=65.0,
            include_bottom=False,
            shape_type=ShapeType.POLYGON,
            texture_type=TextureType.NONE,
            z_rotation_deg=0.0,
            sections=64,
            text_content="OPEN",
            text_mode=TextMode.EMBOSS,
            text_height_mm=6.0,
        )
    )

    assert mesh.is_watertight
    assert mesh.body_count == 1
