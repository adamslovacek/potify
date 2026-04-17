from __future__ import annotations

from math import cos, pi, radians, sin, tan
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import trimesh


class ExportFormat(str, Enum):
    STL = "stl"
    THREE_MF = "3mf"
    BOTH = "both"


class TextureType(str, Enum):
    NONE = "none"
    RINGS = "rings"
    MICRO_RINGS = "micro_rings"
    SPIRAL = "spiral"
    BRAID = "braid"
    GRID = "grid"
    HEX = "hex"
    HAMMERED = "hammered"


@dataclass(frozen=True)
class GeneratorConfig:
    inner_diameter_mm: float
    height_mm: float
    wall_thickness_mm: float = 3.0
    base_thickness_mm: float = 4.0
    include_bottom: bool = True
    taper_deg: float = 1.5
    rim_lip_mm: float = 1.2
    texture_type: TextureType = TextureType.NONE
    texture_strength_mm: float = 0.6
    texture_scale: float = 2.0
    texture_rotation_deg: float = 0.0
    middle_inbound_turns: float = 0.0
    z_rotation_deg: float = 0.0
    sections: int = 192
    height_steps: int = 48

    def validate(self) -> None:
        if self.inner_diameter_mm <= 0:
            raise ValueError("inner_diameter_mm must be > 0")
        if self.height_mm <= 0:
            raise ValueError("height_mm must be > 0")
        if self.wall_thickness_mm <= 0:
            raise ValueError("wall_thickness_mm must be > 0")
        if self.base_thickness_mm < 0:
            raise ValueError("base_thickness_mm must be >= 0")
        if self.include_bottom and self.base_thickness_mm <= 0:
            raise ValueError("base_thickness_mm must be > 0 when include_bottom is enabled")
        if self.base_thickness_mm >= self.height_mm:
            raise ValueError("base_thickness_mm must be smaller than height_mm")
        if abs(self.taper_deg) >= 10:
            raise ValueError("taper_deg must be in range (-10, 10)")
        if self.rim_lip_mm < 0:
            raise ValueError("rim_lip_mm must be >= 0")
        if self.texture_strength_mm < 0:
            raise ValueError("texture_strength_mm must be >= 0")
        if self.texture_scale <= 0:
            raise ValueError("texture_scale must be > 0")
        if self.middle_inbound_turns < 0 or self.middle_inbound_turns > 50:
            raise ValueError("middle_inbound_turns must be in range [0, 50]")
        if abs(self.z_rotation_deg) > 3600:
            raise ValueError("z_rotation_deg absolute value must be <= 3600")
        if self.sections < 24:
            raise ValueError("sections must be >= 24")
        if self.height_steps < 8:
            raise ValueError("height_steps must be >= 8")


def _lerp(z0: float, r0: float, z1: float, r1: float, z: float) -> float:
    if z1 == z0:
        return r0
    t = (z - z0) / (z1 - z0)
    return r0 + (r1 - r0) * t


def _effective_base_z(config: GeneratorConfig) -> float:
    return config.base_thickness_mm if config.include_bottom else 0.0


def _middle_inbound_angle(z: float, height: float, config: GeneratorConfig) -> float:
    z_ratio = z / max(1e-6, height)
    return (2.0 * pi) * config.middle_inbound_turns * z_ratio


def _z_twist_angle(z: float, height: float, config: GeneratorConfig) -> float:
    z_ratio = z / max(1e-6, height)
    return radians(config.z_rotation_deg) * z_ratio


def _outer_base_radius(z: float, config: GeneratorConfig) -> float:
    z_base = _effective_base_z(config)
    z_top = config.height_mm
    z_lip = max(z_base, z_top - config.wall_thickness_mm)

    r_inner_at_base = config.inner_diameter_mm / 2.0
    taper = tan(radians(config.taper_deg))

    def r_inner(local_z: float) -> float:
        return r_inner_at_base + taper * (local_z - z_base)

    def r_outer(local_z: float) -> float:
        return r_inner(local_z) + config.wall_thickness_mm

    r_o0 = r_outer(0.0)
    r_ob = r_outer(z_base)
    r_ol = r_outer(z_lip)
    r_ot = r_outer(z_top)
    r_lt = r_ot + config.rim_lip_mm
    r_ll = r_ol + config.rim_lip_mm

    if z <= z_base:
        return _lerp(0.0, r_o0, z_base, r_ob, z)
    if z <= z_lip:
        return _lerp(z_base, r_ob, z_lip, r_ol, z)
    return _lerp(z_lip, r_ll, z_top, r_lt, z)


def _inner_base_radius(z: float, config: GeneratorConfig) -> float:
    z_base = _effective_base_z(config)
    z_top = config.height_mm
    r_inner_at_base = config.inner_diameter_mm / 2.0
    taper = tan(radians(config.taper_deg))

    if z < z_base:
        return r_inner_at_base
    return r_inner_at_base + taper * (z - z_base)


def _texture_offset(z: float, theta: float, config: GeneratorConfig) -> float:
    if config.texture_type == TextureType.NONE:
        return 0.0

    strength = config.texture_strength_mm
    scale = max(0.1, config.texture_scale)
    phase = radians(config.texture_rotation_deg)
    z_ratio = z / max(1e-6, config.height_mm)
    freq = max(1.0, scale)
    z_angle = 2.0 * pi * freq * z_ratio
    theta_angle = (freq * theta) + phase

    if config.texture_type == TextureType.RINGS:
        base = (
            sin(z_angle + phase)
            + 0.38 * sin((3.0 * z_angle) + (phase * 0.6))
            + 0.2 * sin((7.0 * z_angle) - (phase * 0.35))
        )
        return strength * 0.62 * base
    if config.texture_type == TextureType.MICRO_RINGS:
        base = (
            sin((2.0 * z_angle) + phase)
            + 0.52 * sin((8.0 * z_angle) + (phase * 0.5))
            + 0.18 * sin((16.0 * z_angle) - (phase * 0.25))
        )
        return strength * 0.48 * base
    if config.texture_type == TextureType.SPIRAL:
        base = sin(theta_angle + z_angle)
        detail = 0.26 * sin((2.6 * theta_angle) - (3.2 * z_angle))
        return strength * (base + detail)
    if config.texture_type == TextureType.BRAID:
        left = sin(theta_angle + (1.5 * z_angle))
        right = sin((-theta_angle) + (1.5 * z_angle) + (pi * 0.5))
        weave = 0.45 * sin((4.0 * theta_angle) + (0.7 * z_angle))
        return strength * 0.68 * (left * right + weave)
    if config.texture_type == TextureType.GRID:
        coarse = sin(theta_angle) * sin(z_angle + phase)
        fine = 0.35 * sin((3.0 * theta_angle) + phase) * sin((3.0 * z_angle) - phase)
        return strength * 0.52 * (coarse + fine)
    if config.texture_type == TextureType.HEX:
        a = abs(sin(theta_angle))
        b = abs(sin((0.58 * theta_angle) + (1.72 * z_angle)))
        c = abs(sin((0.58 * theta_angle) - (1.72 * z_angle)))
        return strength * ((a + b + c) / 3.0 - 0.5)
    if config.texture_type == TextureType.HAMMERED:
        n1 = sin((7.0 * theta_angle) + (5.0 * z_angle))
        n2 = sin((13.0 * theta_angle) - (11.0 * z_angle) + 1.7)
        n3 = sin((17.0 * theta_angle) + (3.0 * z_angle) - 0.9)
        noise = (n1 + n2 + n3) / 3.0
        return strength * 0.55 * noise

    return 0.0


def _build_wall_faces(ring_count: int, section_count: int, offset: int, reverse: bool = False) -> list[list[int]]:
    faces: list[list[int]] = []
    for i in range(ring_count - 1):
        for j in range(section_count):
            a = offset + i * section_count + j
            b = offset + i * section_count + ((j + 1) % section_count)
            c = offset + (i + 1) * section_count + ((j + 1) % section_count)
            d = offset + (i + 1) * section_count + j
            if reverse:
                faces.append([a, c, b])
                faces.append([a, d, c])
            else:
                faces.append([a, b, c])
                faces.append([a, c, d])
    return faces


def _build_planter_mesh(config: GeneratorConfig) -> trimesh.Trimesh:
    z_base = _effective_base_z(config)
    z_top = config.height_mm
    z_lip = max(z_base, z_top - config.wall_thickness_mm)
    sections = max(24, int(config.sections))
    height_steps = max(8, int(config.height_steps))
    z_levels = sorted(set([
        0.0,
        z_base,
        z_lip,
        z_top,
        *[(i / (height_steps - 1)) * z_top for i in range(height_steps)],
    ]))

    # Equivalent to linear_extrude(height=..., twist=...) around Z axis.
    outer_rings = []
    for z in z_levels:
        radius_base = _outer_base_radius(z, config)
        rotation_angle = _middle_inbound_angle(z, z_top, config)
        z_twist = _z_twist_angle(z, z_top, config)
        ring = []
        for i in range(sections):
            theta = (i / sections) * (2.0 * pi)
            offset = _texture_offset(z, theta, config)
            ring_radius = max(0.05, radius_base + offset)
            theta_rotated = theta + rotation_angle + z_twist
            # Keep Z as the vertical axis; no X/Y axis rotations are applied.
            ring.append((ring_radius * cos(theta_rotated), ring_radius * sin(theta_rotated), z))
        outer_rings.append(ring)

    inner_z_levels = sorted(set([
        z_base,
        z_top,
        *[(z_base + (i / (height_steps - 1)) * (z_top - z_base)) for i in range(height_steps)],
    ]))
    inner_rings = []
    for z in inner_z_levels:
        radius = _inner_base_radius(z, config)
        rotation_angle = _middle_inbound_angle(z, z_top, config)
        z_twist = _z_twist_angle(z, z_top, config)
        ring = [
            (
                radius * cos(((i / sections) * (2.0 * pi)) + rotation_angle + z_twist),
                radius * sin(((i / sections) * (2.0 * pi)) + rotation_angle + z_twist),
                z,
            )
            for i in range(sections)
        ]
        inner_rings.append(ring)

    vertices: list[tuple[float, float, float]] = []
    for ring in outer_rings:
        vertices.extend(ring)
    inner_offset = len(vertices)
    for ring in inner_rings:
        vertices.extend(ring)
    center_bottom_index = len(vertices)
    if config.include_bottom:
        vertices.append((0.0, 0.0, 0.0))

    faces: list[list[int]] = []
    faces.extend(_build_wall_faces(len(outer_rings), sections, 0, reverse=False))
    faces.extend(_build_wall_faces(len(inner_rings), sections, inner_offset, reverse=True))

    if config.include_bottom:
        for j in range(sections):
            a = 0 + j
            b = 0 + ((j + 1) % sections)
            faces.append([center_bottom_index, b, a])

        outer_base_index = z_levels.index(z_base)
        outer_base_start = outer_base_index * sections
        inner_base_start = inner_offset
        for j in range(sections):
            a = outer_base_start + j
            b = outer_base_start + ((j + 1) % sections)
            c = inner_base_start + ((j + 1) % sections)
            d = inner_base_start + j
            faces.append([a, b, c])
            faces.append([a, c, d])

    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    if config.include_bottom and not mesh.is_watertight:
        mesh = mesh.convex_hull
    if config.include_bottom and not mesh.is_watertight:
        raise RuntimeError("Generated mesh is not watertight.")
    return mesh


def build_planter_sleeve(config: GeneratorConfig) -> trimesh.Trimesh:
    config.validate()
    if (
        config.texture_type == TextureType.NONE
        and config.include_bottom
        and config.middle_inbound_turns == 0
        and config.z_rotation_deg == 0
    ):
        z_base = _effective_base_z(config)
        z_top = config.height_mm
        z_lip = max(z_base, z_top - config.wall_thickness_mm)

        r_inner_at_base = config.inner_diameter_mm / 2.0
        taper = tan(radians(config.taper_deg))

        def r_inner(z: float) -> float:
            return r_inner_at_base + (taper * (z - z_base))

        def r_outer(z: float) -> float:
            return r_inner(z) + config.wall_thickness_mm

        r_o0 = r_outer(0.0)
        r_ob = r_outer(z_base)
        r_ol = r_outer(z_lip)
        r_ot = r_outer(z_top)
        r_il = r_inner(z_lip)
        r_it = r_inner(z_top)
        r_lt = r_ot + config.rim_lip_mm
        r_ll = r_ol + config.rim_lip_mm

        radii = [r_o0, r_ob, r_ol, r_ot, r_il, r_it, r_lt, r_ll]
        if any(r <= 0 for r in radii):
            raise ValueError(
                "Invalid dimensions. Radii became non-positive; reduce negative taper or increase size."
            )

        profile = [
            (0.0, 0.0),
            (r_o0, 0.0),
            (r_ob, z_base),
            (r_ol, z_lip),
            (r_ll, z_lip),
            (r_lt, z_top),
            (r_it, z_top),
            (r_inner_at_base, z_base),
            (0.0, z_base),
            (0.0, 0.0),
        ]
        mesh = trimesh.creation.revolve(profile, sections=config.sections)
        if not mesh.is_watertight:
            raise RuntimeError("Generated mesh is not watertight.")
        return mesh

    return _build_planter_mesh(config)


def export_model(model: trimesh.Trimesh, output_stem: Path, fmt: ExportFormat) -> list[Path]:
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    if fmt in (ExportFormat.STL, ExportFormat.BOTH):
        stl_path = output_stem.with_suffix(".stl")
        model.export(stl_path)
        written.append(stl_path)

    if fmt in (ExportFormat.THREE_MF, ExportFormat.BOTH):
        mf_path = output_stem.with_suffix(".3mf")
        try:
            model.export(mf_path)
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "3MF export failed. Verify trimesh optional export dependencies are installed."
            ) from exc
        written.append(mf_path)

    return written
