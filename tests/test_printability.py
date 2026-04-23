from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from planter_generator.model import GeneratorConfig, ShapeType, TextureType, analyze_printability


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
