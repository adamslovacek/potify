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
    IMAGE = "image"
    RINGS = "rings"
    MICRO_RINGS = "micro_rings"
    SPIRAL = "spiral"
    BRAID = "braid"
    GRID = "grid"
    HEX = "hex"
    HAMMERED = "hammered"


class ShapeType(str, Enum):
    POLYGON = "polygon"
    STAR = "star"
    ELLIPSE = "ellipse"
    ROUNDED_SQUARE = "rounded_square"
    DIAMOND = "diamond"
    SQUIRCLE = "squircle"
    CLOVER = "clover"
    SCALLOP = "scallop"
    GEAR = "gear"
    FLOWER = "flower"
    TEARDROP = "teardrop"
    LENS = "lens"


class DisplacementMode(str, Enum):
    SYMMETRIC = "symmetric"
    RAISE = "raise"
    LOWER = "lower"


@dataclass(frozen=True)
class GeneratorConfig:
    inner_diameter_mm: float
    height_mm: float
    wall_thickness_mm: float = 3.0
    base_thickness_mm: float = 4.0
    include_bottom: bool = True
    taper_deg: float = 1.9
    rim_lip_mm: float = 1.4
    texture_type: TextureType = TextureType.BRAID
    texture_strength_mm: float = 0.9
    texture_scale: float = 2.4
    texture_scale_u: float | None = None
    texture_scale_v: float | None = None
    texture_offset_u: float = 0.0
    texture_offset_v: float = 0.0
    texture_rotation_deg: float = 28.0
    texture_displacement_mode: DisplacementMode = DisplacementMode.SYMMETRIC
    texture_gray_black: float = 0.0
    texture_gray_white: float = 1.0
    texture_gray_midpoint: float = 0.5
    texture_gray_invert: bool = False
    texture_image_data: tuple[float, ...] | None = None
    texture_image_width: int = 0
    texture_image_height: int = 0
    middle_inbound_turns: float = 0.0
    middle_inbound_z_mm: float | None = 50.0
    z_rotation_deg: float = 26.0
    shape_type: ShapeType = ShapeType.SQUIRCLE
    star_inner_ratio: float = 0.45
    shape_aspect_ratio: float = 1.0
    shape_roundness: float = 0.35
    shape_wave_depth: float = 0.6
    shape_wave_count: int = 8
    sections: int = 7
    height_steps: int = 64
    drain_hole_diameter_mm: float = 0.0

    def validate(self) -> None:
        if self.drain_hole_diameter_mm < 0:
            raise ValueError("drain_hole_diameter_mm must be >= 0")
        if self.drain_hole_diameter_mm > 0 and self.include_bottom:
            if self.drain_hole_diameter_mm >= self.inner_diameter_mm:
                raise ValueError(
                    "drain_hole_diameter_mm must be smaller than inner_diameter_mm"
                )
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
        if self.texture_scale_u is not None and self.texture_scale_u <= 0:
            raise ValueError("texture_scale_u must be > 0")
        if self.texture_scale_v is not None and self.texture_scale_v <= 0:
            raise ValueError("texture_scale_v must be > 0")
        if self.texture_gray_black < 0 or self.texture_gray_black > 1:
            raise ValueError("texture_gray_black must be in range [0, 1]")
        if self.texture_gray_white < 0 or self.texture_gray_white > 1:
            raise ValueError("texture_gray_white must be in range [0, 1]")
        if self.texture_gray_midpoint <= 0 or self.texture_gray_midpoint >= 1:
            raise ValueError("texture_gray_midpoint must be in range (0, 1)")
        if self.texture_gray_white <= self.texture_gray_black:
            raise ValueError("texture_gray_white must be greater than texture_gray_black")
        if self.texture_type == TextureType.IMAGE:
            if self.texture_image_data is None:
                raise ValueError("texture_image_data is required when texture_type is image")
            if self.texture_image_width <= 0 or self.texture_image_height <= 0:
                raise ValueError("texture_image_width and texture_image_height must be > 0")
        if self.middle_inbound_turns < 0 or self.middle_inbound_turns > 50:
            raise ValueError("middle_inbound_turns must be in range [0, 50]")
        if self.middle_inbound_z_mm is not None and (
            self.middle_inbound_z_mm < 0 or self.middle_inbound_z_mm > self.height_mm
        ):
            raise ValueError("middle_inbound_z_mm must be in range [0, height_mm]")
        if abs(self.z_rotation_deg) > 3600:
            raise ValueError("z_rotation_deg absolute value must be <= 3600")
        if self.star_inner_ratio < 0.1 or self.star_inner_ratio > 0.9:
            raise ValueError("star_inner_ratio must be in range [0.1, 0.9]")
        if self.shape_aspect_ratio < 0.4 or self.shape_aspect_ratio > 2.5:
            raise ValueError("shape_aspect_ratio must be in range [0.4, 2.5]")
        if self.shape_roundness < 0.0 or self.shape_roundness > 1.0:
            raise ValueError("shape_roundness must be in range [0, 1]")
        if self.shape_wave_depth < 0.0 or self.shape_wave_depth > 0.95:
            raise ValueError("shape_wave_depth must be in range [0, 0.95]")
        if self.shape_wave_count < 2 or self.shape_wave_count > 24:
            raise ValueError("shape_wave_count must be in range [2, 24]")
        if self.sections < 3:
            raise ValueError("sections must be >= 3")
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
    anchor_z = config.middle_inbound_z_mm
    if anchor_z is None:
        anchor_z = height * 0.5
    z_ratio = (z - anchor_z) / max(1e-6, height)
    return (2.0 * pi) * config.middle_inbound_turns * z_ratio


def _z_twist_angle(z: float, height: float, config: GeneratorConfig) -> float:
    z_ratio = z / max(1e-6, height)
    return radians(config.z_rotation_deg) * z_ratio


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _superellipse_radius_factor(theta: float, aspect_ratio: float, exponent: float) -> float:
    aspect = max(1e-6, aspect_ratio)
    denom = ((abs(cos(theta)) / aspect) ** exponent) + (abs(sin(theta)) ** exponent)
    return 1.0 / max(1e-6, (denom ** (1.0 / exponent)) * max(1.0, aspect))


def _shape_radius_factor(theta: float, config: GeneratorConfig) -> float:
    aspect = _clamp(config.shape_aspect_ratio, 0.4, 2.5)
    roundness = _clamp(config.shape_roundness, 0.0, 1.0)
    depth = _clamp(config.shape_wave_depth, 0.0, 0.95)
    wave_count = max(2, int(config.shape_wave_count))
    inner_ratio = _clamp(config.star_inner_ratio, 0.1, 0.9)

    if config.shape_type == ShapeType.ELLIPSE:
        return _superellipse_radius_factor(theta, aspect, 2.0)
    if config.shape_type == ShapeType.ROUNDED_SQUARE:
        exponent = 8.0 - (5.0 * roundness)
        return _superellipse_radius_factor(theta, aspect, exponent)
    if config.shape_type == ShapeType.DIAMOND:
        return _superellipse_radius_factor(theta, aspect, 1.0)
    if config.shape_type == ShapeType.SQUIRCLE:
        exponent = 5.0 - (2.2 * roundness)
        return _superellipse_radius_factor(theta, aspect, exponent)
    if config.shape_type == ShapeType.CLOVER:
        lobe = 0.5 + (0.5 * cos(wave_count * theta))
        return max(0.05, (1.0 - depth) + (depth * lobe))
    if config.shape_type == ShapeType.SCALLOP:
        scallop = abs(sin((wave_count * theta) * 0.5)) ** (0.65 + (0.85 * roundness))
        return max(0.05, 1.0 - (depth * scallop))
    if config.shape_type == ShapeType.GEAR:
        tooth = 0.5 + (0.5 * cos(config.sections * theta))
        sharpened = tooth ** (1.3 + (4.0 * (1.0 - roundness)))
        return max(0.05, inner_ratio + ((1.0 - inner_ratio) * sharpened))
    if config.shape_type == ShapeType.FLOWER:
        petal = 0.5 + (0.5 * cos(wave_count * theta))
        bloom = petal ** (0.9 + (1.6 * (1.0 - roundness)))
        valley = max(0.05, inner_ratio * (1.0 - (0.45 * depth)))
        return max(0.05, valley + ((1.0 - valley) * bloom))
    if config.shape_type == ShapeType.TEARDROP:
        base = _superellipse_radius_factor(theta, aspect, 2.0)
        return max(0.05, base * ((1.0 - (depth * sin(theta))) / (1.0 + depth)))
    if config.shape_type == ShapeType.LENS:
        base = _superellipse_radius_factor(theta, aspect, 2.0)
        return max(0.05, base * ((1.0 - depth) + (depth * abs(cos(theta)))))
    return 1.0


def _shape_point_count(config: GeneratorConfig) -> int:
    sections = max(3, int(config.sections))
    if config.shape_type == ShapeType.POLYGON:
        return sections
    if config.shape_type == ShapeType.STAR:
        return sections * 2
    base_count = max(48, sections * 8, int(config.shape_wave_count) * 10)
    if config.shape_type in {ShapeType.GEAR, ShapeType.CLOVER, ShapeType.SCALLOP, ShapeType.FLOWER}:
        return max(60, base_count)
    return base_count


def _get_point_angle_and_radius_factor(i: int, point_count: int, config: GeneratorConfig) -> tuple[float, float]:
    if config.shape_type == ShapeType.POLYGON:
        angle = (i / point_count) * (2.0 * pi)
        return angle, 1.0
    if config.shape_type == ShapeType.STAR:
        angle = (i / point_count) * (2.0 * pi)
        is_inner = (i % 2) == 1
        radius_factor = config.star_inner_ratio if is_inner else 1.0
        return angle, radius_factor
    angle = (i / point_count) * (2.0 * pi)
    return angle, _shape_radius_factor(angle, config)


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


def _texture_uv(z: float, theta: float, config: GeneratorConfig) -> tuple[float, float]:
    scale_u = config.texture_scale_u if config.texture_scale_u is not None else config.texture_scale
    scale_v = config.texture_scale_v if config.texture_scale_v is not None else config.texture_scale

    u = (theta / (2.0 * pi)) * max(0.1, scale_u) + config.texture_offset_u
    v = (z / max(1e-6, config.height_mm)) * max(0.1, scale_v) + config.texture_offset_v

    # Rotate around texture-space center to mimic UV transform controls.
    angle = radians(config.texture_rotation_deg)
    c = cos(angle)
    s = sin(angle)
    du = u - 0.5
    dv = v - 0.5
    u_rot = (du * c) - (dv * s) + 0.5
    v_rot = (du * s) + (dv * c) + 0.5
    return u_rot, v_rot


def _sample_texture_image(u: float, v: float, config: GeneratorConfig) -> float:
    if config.texture_image_data is None:
        return 0.5

    width = config.texture_image_width
    height = config.texture_image_height
    if width <= 0 or height <= 0:
        return 0.5

    u = u % 1.0
    v = v % 1.0

    x = u * (width - 1)
    y = v * (height - 1)
    x0 = int(x)
    y0 = int(y)
    x1 = min(x0 + 1, width - 1)
    y1 = min(y0 + 1, height - 1)
    tx = x - x0
    ty = y - y0

    def px(ix: int, iy: int) -> float:
        idx = iy * width + ix
        return config.texture_image_data[idx]

    a = px(x0, y0)
    b = px(x1, y0)
    c = px(x0, y1)
    d = px(x1, y1)
    top = (a * (1.0 - tx)) + (b * tx)
    bottom = (c * (1.0 - tx)) + (d * tx)
    return (top * (1.0 - ty)) + (bottom * ty)


def _map_gray_to_displacement(sample: float, config: GeneratorConfig) -> float:
    if config.texture_gray_invert:
        sample = 1.0 - sample

    black = config.texture_gray_black
    white = config.texture_gray_white
    normalized = (sample - black) / max(1e-6, white - black)
    normalized = max(0.0, min(1.0, normalized))

    if config.texture_displacement_mode == DisplacementMode.RAISE:
        return normalized
    if config.texture_displacement_mode == DisplacementMode.LOWER:
        return -normalized

    mid = config.texture_gray_midpoint
    if normalized >= mid:
        return (normalized - mid) / max(1e-6, 1.0 - mid)
    return -((mid - normalized) / max(1e-6, mid))


def _texture_offset(z: float, theta: float, config: GeneratorConfig) -> float:
    if config.texture_type == TextureType.NONE:
        return 0.0

    strength = config.texture_strength_mm
    u, v = _texture_uv(z, theta, config)
    theta_angle = 2.0 * pi * u
    z_angle = 2.0 * pi * v
    phase = 0.0

    if config.texture_type == TextureType.IMAGE:
        sample = _sample_texture_image(u, v, config)
        return strength * _map_gray_to_displacement(sample, config)

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


def _signed_area_2d(points: list[tuple[float, float]]) -> float:
    area = 0.0
    for i, (x0, y0) in enumerate(points):
        x1, y1 = points[(i + 1) % len(points)]
        area += (x0 * y1) - (x1 * y0)
    return area * 0.5


def _point_in_triangle(
    point: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
) -> bool:
    px, py = point
    ax, ay = a
    bx, by = b
    cx, cy = c

    v0x = cx - ax
    v0y = cy - ay
    v1x = bx - ax
    v1y = by - ay
    v2x = px - ax
    v2y = py - ay

    dot00 = (v0x * v0x) + (v0y * v0y)
    dot01 = (v0x * v1x) + (v0y * v1y)
    dot02 = (v0x * v2x) + (v0y * v2y)
    dot11 = (v1x * v1x) + (v1y * v1y)
    dot12 = (v1x * v2x) + (v1y * v2y)

    denom = (dot00 * dot11) - (dot01 * dot01)
    if abs(denom) <= 1e-9:
        return False

    inv = 1.0 / denom
    u = ((dot11 * dot02) - (dot01 * dot12)) * inv
    v = ((dot00 * dot12) - (dot01 * dot02)) * inv
    eps = 1e-9
    return (u >= -eps) and (v >= -eps) and ((u + v) <= 1.0 + eps)


def _triangulate_simple_polygon(points: list[tuple[float, float]]) -> list[tuple[int, int, int]]:
    if len(points) < 3:
        return []

    ccw = _signed_area_2d(points) > 0
    remaining = list(range(len(points)))
    triangles: list[tuple[int, int, int]] = []
    guard = 0

    while len(remaining) > 3 and guard < len(points) * len(points):
        ear_found = False
        for i, current in enumerate(remaining):
            prev = remaining[i - 1]
            nxt = remaining[(i + 1) % len(remaining)]
            ax, ay = points[prev]
            bx, by = points[current]
            cx, cy = points[nxt]
            cross = ((bx - ax) * (cy - ay)) - ((by - ay) * (cx - ax))
            if ccw:
                if cross <= 1e-9:
                    continue
            elif cross >= -1e-9:
                continue

            triangle = (points[prev], points[current], points[nxt])
            contains_point = False
            for candidate in remaining:
                if candidate in (prev, current, nxt):
                    continue
                if _point_in_triangle(points[candidate], *triangle):
                    contains_point = True
                    break
            if contains_point:
                continue

            triangles.append((prev, current, nxt))
            del remaining[i]
            ear_found = True
            break

        if not ear_found:
            break
        guard += 1

    if len(remaining) == 3:
        triangles.append((remaining[0], remaining[1], remaining[2]))

    if not triangles:
        raise RuntimeError("Failed to triangulate bottom cap for the generated shape.")
    return triangles

def _build_annulus_faces(
    n_outer: int,
    outer_start: int,
    n_inner: int,
    inner_start: int,
    reverse: bool = False,
) -> list[list[int]]:
    """Triangulate annular region between two concentric rings.

    Both rings have vertices at evenly-spaced angles going CCW from above.
    Returns faces wound CCW from above (normal up) unless *reverse* is True.
    """
    faces: list[list[int]] = []
    oi = 0
    ii = 0
    o_steps = 0
    i_steps = 0
    while o_steps < n_outer or i_steps < n_inner:
        o_next = (oi + 1) % n_outer
        i_next = (ii + 1) % n_inner
        can_outer = o_steps < n_outer
        can_inner = i_steps < n_inner
        if not can_inner or (can_outer and (o_steps / n_outer) <= (i_steps / n_inner)):
            tri = [outer_start + oi, outer_start + o_next, inner_start + ii]
            oi = o_next
            o_steps += 1
        else:
            tri = [outer_start + oi, inner_start + i_next, inner_start + ii]
            ii = i_next
            i_steps += 1
        if reverse:
            faces.append([tri[2], tri[1], tri[0]])
        else:
            faces.append(tri)
    return faces


def _build_planter_mesh(config: GeneratorConfig) -> trimesh.Trimesh:
    z_base = _effective_base_z(config)
    z_top = config.height_mm
    z_lip = max(z_base, z_top - config.wall_thickness_mm)
    height_steps = max(8, int(config.height_steps))
    z_levels = sorted(set([
        0.0,
        z_base,
        z_lip,
        z_top,
        *[(i / (height_steps - 1)) * z_top for i in range(height_steps)],
    ]))

    point_count = _shape_point_count(config)

    # Equivalent to linear_extrude(height=..., twist=...) around Z axis.
    outer_rings = []
    for z in z_levels:
        radius_base = _outer_base_radius(z, config)
        rotation_angle = _middle_inbound_angle(z, z_top, config)
        z_twist = _z_twist_angle(z, z_top, config)
        ring = []
        for i in range(point_count):
            theta, radius_factor = _get_point_angle_and_radius_factor(i, point_count, config)
            offset = _texture_offset(z, theta, config)
            ring_radius = max(0.05, (radius_base + offset) * radius_factor)
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
        ring = []
        for i in range(point_count):
            theta, radius_factor = _get_point_angle_and_radius_factor(i, point_count, config)
            inner_radius = radius * radius_factor
            ring.append((
                inner_radius * cos(theta + rotation_angle + z_twist),
                inner_radius * sin(theta + rotation_angle + z_twist),
                z,
            ))
        inner_rings.append(ring)

    vertices: list[tuple[float, float, float]] = []
    for ring in outer_rings:
        vertices.extend(ring)
    inner_offset = len(vertices)
    for ring in inner_rings:
        vertices.extend(ring)

    # Drain hole rings (only when bottom is present and hole diameter is set)
    r_hole = (
        config.drain_hole_diameter_mm / 2.0
        if (config.drain_hole_diameter_mm > 0 and config.include_bottom)
        else 0.0
    )
    hole_point_count = point_count

    def _build_hole_ring(z: float) -> list[tuple[float, float, float]]:
        rotation_angle = _middle_inbound_angle(z, z_top, config)
        z_twist = _z_twist_angle(z, z_top, config)
        ring: list[tuple[float, float, float]] = []
        for i in range(hole_point_count):
            theta = (i / hole_point_count) * (2.0 * pi)
            theta_rotated = theta + rotation_angle + z_twist
            ring.append((r_hole * cos(theta_rotated), r_hole * sin(theta_rotated), z))
        return ring

    hole_bottom_offset = 0
    hole_top_offset = 0
    if r_hole > 0:
        hole_bottom_offset = len(vertices)
        vertices.extend(_build_hole_ring(0.0))
        hole_top_offset = len(vertices)
        vertices.extend(_build_hole_ring(z_base))

    faces: list[list[int]] = []
    faces.extend(_build_wall_faces(len(outer_rings), point_count, 0, reverse=False))
    faces.extend(_build_wall_faces(len(inner_rings), point_count, inner_offset, reverse=True))

    outer_top_index = z_levels.index(z_top)
    outer_top_start = outer_top_index * point_count
    inner_top_start = inner_offset + ((len(inner_rings) - 1) * point_count)
    for j in range(point_count):
        a = outer_top_start + j
        b = outer_top_start + ((j + 1) % point_count)
        c = inner_top_start + ((j + 1) % point_count)
        d = inner_top_start + j
        faces.append([a, c, b])
        faces.append([a, d, c])

    if config.include_bottom:
        if r_hole > 0:
            # Annular outer bottom face at z=0 (normal pointing down)
            faces.extend(
                _build_annulus_faces(point_count, 0, hole_point_count, hole_bottom_offset, reverse=True)
            )
            # Annular inner floor at z=z_base (normal pointing up)
            faces.extend(
                _build_annulus_faces(
                    point_count, inner_offset, hole_point_count, hole_top_offset, reverse=False
                )
            )
            # Hole cylinder wall (inward normals)
            faces.extend(_build_wall_faces(2, hole_point_count, hole_bottom_offset, reverse=True))
        else:
            bottom_outline = [(x, y) for x, y, _z in outer_rings[0]]
            bottom_triangles = _triangulate_simple_polygon(bottom_outline)
            for a, b, c in bottom_triangles:
                faces.append([c, b, a])

            inner_base_start = inner_offset
            inner_outline = [(x, y) for x, y, _z in inner_rings[0]]
            inner_triangles = _triangulate_simple_polygon(inner_outline)
            for a, b, c in inner_triangles:
                faces.append([
                    inner_base_start + a,
                    inner_base_start + b,
                    inner_base_start + c,
                ])

    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    mesh.process(validate=True)
    trimesh.repair.fix_normals(mesh)
    if config.include_bottom and not mesh.is_watertight:
        trimesh.repair.fill_holes(mesh)
    if config.include_bottom and not mesh.is_watertight:
        raise RuntimeError("Generated mesh is not watertight.")
    return mesh


def build_planter_sleeve(config: GeneratorConfig) -> trimesh.Trimesh:
    config.validate()
    if (
        config.shape_type == ShapeType.POLYGON
        and
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
        if config.drain_hole_diameter_mm > 0:
            r_hole_fast = config.drain_hole_diameter_mm / 2.0
            profile = [
                (r_hole_fast, 0.0),
                (r_o0, 0.0),
                (r_ob, z_base),
                (r_ol, z_lip),
                (r_ll, z_lip),
                (r_lt, z_top),
                (r_it, z_top),
                (r_inner_at_base, z_base),
                (r_hole_fast, z_base),
                (r_hole_fast, 0.0),
            ]
        else:
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
