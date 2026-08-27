from __future__ import annotations

from math import ceil, cos, pi, radians, sin, sqrt, tan
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path

import trimesh


MAX_SECTIONS = 256
MAX_HEIGHT_STEPS = 256
MAX_TEXT_LENGTH = 50
MAX_TEXT_HEIGHT_MM = 20.0
MAX_TEXT_DEPTH_MM = 2.0


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
    CIRCLE = "circle"
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


class ProfileType(str, Enum):
    STRAIGHT = "straight"
    WAIST = "waist"
    BELLY = "belly"
    FLARE = "flare"
    SHOULDER = "shoulder"


class RimStyle(str, Enum):
    PLAIN = "plain"
    FLARED = "flared"
    BAND = "band"


class DisplacementMode(str, Enum):
    SYMMETRIC = "symmetric"
    RAISE = "raise"
    LOWER = "lower"


class DrainagePattern(str, Enum):
    CENTER = "center"
    RADIAL = "radial"
    GRID = "grid"
    HEX = "hex"


class TextMode(str, Enum):
    NONE = "none"
    EMBOSS = "emboss"
    ENGRAVE = "engrave"


class PrintProfile(str, Enum):
    FINE = "fine"
    STANDARD = "standard"
    DRAFT = "draft"
    CUSTOM = "custom"


def print_profile_dimensions(profile: PrintProfile) -> tuple[float, float]:
    return {
        PrintProfile.FINE: (0.25, 0.12),
        PrintProfile.STANDARD: (0.4, 0.2),
        PrintProfile.DRAFT: (0.6, 0.3),
        PrintProfile.CUSTOM: (0.4, 0.2),
    }[profile]


@dataclass(frozen=True)
class GeneratorConfig:
    inner_diameter_mm: float
    height_mm: float
    wall_thickness_mm: float = 3.0
    base_thickness_mm: float = 4.0
    include_bottom: bool = True
    taper_deg: float = 1.9
    rim_lip_mm: float = 1.4
    rim_style: RimStyle = RimStyle.FLARED
    profile_type: ProfileType = ProfileType.STRAIGHT
    profile_depth_mm: float = 0.0
    profile_position: float = 0.55
    foot_ring_mm: float = 0.0
    foot_height_mm: float = 8.0
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
    middle_inbound_z_mm: float | None = None
    z_rotation_deg: float = 26.0
    shape_type: ShapeType = ShapeType.SQUIRCLE
    star_inner_ratio: float = 0.45
    shape_aspect_ratio: float = 1.0
    shape_roundness: float = 0.35
    shape_wave_depth: float = 0.6
    shape_wave_count: int = 8
    shape_relief_mm: float = 4.0
    sections: int = 7
    height_steps: int = 64
    print_profile: PrintProfile = PrintProfile.STANDARD
    nozzle_diameter_mm: float = 0.4
    layer_height_mm: float = 0.2
    drain_hole_diameter_mm: float = 0.0
    drainage_pattern: DrainagePattern = DrainagePattern.CENTER
    drainage_hole_count: int = 1
    drainage_spacing_mm: float = 12.0
    text_content: str = ""
    text_mode: TextMode = TextMode.EMBOSS
    text_height_mm: float = 5.0
    text_depth_mm: float = 0.5
    text_position_z_mm: float | None = None
    text_rotation_z_deg: float = 0.0

    def validate(self) -> None:
        if self.drain_hole_diameter_mm < 0:
            raise ValueError("drain_hole_diameter_mm must be >= 0")
        if self.drain_hole_diameter_mm > 0 and not self.include_bottom:
            raise ValueError("drain_hole_diameter_mm requires include_bottom")
        if self.drain_hole_diameter_mm > 0 and self.include_bottom:
            if self.drain_hole_diameter_mm >= self.inner_diameter_mm:
                raise ValueError(
                    "drain_hole_diameter_mm must be smaller than inner_diameter_mm"
                )
            if self.drainage_hole_count < 1 or self.drainage_hole_count > 32:
                raise ValueError("drainage_hole_count must be in range [1, 32]")
            if self.drainage_spacing_mm <= 0:
                raise ValueError("drainage_spacing_mm must be > 0")
            positions = _drainage_hole_positions(self)
            if not _drainage_holes_fit_floor(self, positions):
                raise ValueError("drainage pattern does not fit inside the planter floor")
            minimum_spacing = self.drain_hole_diameter_mm + 0.4
            for index, (x0, y0) in enumerate(positions):
                for x1, y1 in positions[index + 1:]:
                    if sqrt(((x1 - x0) ** 2) + ((y1 - y0) ** 2)) < minimum_spacing:
                        raise ValueError("drainage holes overlap; increase drainage_spacing_mm")
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
        if self.profile_depth_mm < 0 or self.profile_depth_mm > 30:
            raise ValueError("profile_depth_mm must be in range [0, 30]")
        if self.profile_position < 0.1 or self.profile_position > 0.9:
            raise ValueError("profile_position must be in range [0.1, 0.9]")
        if self.foot_ring_mm < 0 or self.foot_ring_mm > 20:
            raise ValueError("foot_ring_mm must be in range [0, 20]")
        if self.foot_ring_mm > 0 and (
            self.foot_height_mm <= 0 or self.foot_height_mm > self.height_mm
        ):
            raise ValueError("foot_height_mm must be in range (0, height_mm]")
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
        if self.shape_relief_mm < 0 or self.shape_relief_mm > 30:
            raise ValueError("shape_relief_mm must be in range [0, 30]")
        if self.sections < 3:
            raise ValueError("sections must be >= 3")
        if self.sections > MAX_SECTIONS:
            raise ValueError(f"sections must be <= {MAX_SECTIONS}")
        if self.height_steps < 8:
            raise ValueError("height_steps must be >= 8")
        if self.height_steps > MAX_HEIGHT_STEPS:
            raise ValueError(f"height_steps must be <= {MAX_HEIGHT_STEPS}")
        if self.nozzle_diameter_mm < 0.15 or self.nozzle_diameter_mm > 1.2:
            raise ValueError("nozzle_diameter_mm must be in range [0.15, 1.2]")
        if self.layer_height_mm < 0.05 or self.layer_height_mm > self.nozzle_diameter_mm * 0.8:
            raise ValueError("layer_height_mm must be between 0.05 and 80% of nozzle_diameter_mm")
        if len(self.text_content) > MAX_TEXT_LENGTH:
            raise ValueError(f"text_content must be at most {MAX_TEXT_LENGTH} characters")
        if self.text_height_mm < 0:
            raise ValueError("text_height_mm must be >= 0")
        if self.text_height_mm > MAX_TEXT_HEIGHT_MM:
            raise ValueError(f"text_height_mm must be <= {MAX_TEXT_HEIGHT_MM:g}")
        if self.text_depth_mm < 0:
            raise ValueError("text_depth_mm must be >= 0")
        if self.text_depth_mm > MAX_TEXT_DEPTH_MM:
            raise ValueError(f"text_depth_mm must be <= {MAX_TEXT_DEPTH_MM:g}")
        if self.text_content and self.text_mode != TextMode.NONE and self.text_depth_mm <= 0:
            raise ValueError("text_depth_mm must be > 0 when a text effect is enabled")
        if self.text_position_z_mm is not None and (
            self.text_position_z_mm < 0 or self.text_position_z_mm > self.height_mm
        ):
            raise ValueError("text_position_z_mm must be in range [0, height_mm]")


def _drainage_hole_positions(config: GeneratorConfig) -> list[tuple[float, float]]:
    if config.drainage_pattern == DrainagePattern.CENTER:
        return [(0.0, 0.0)]

    count = config.drainage_hole_count
    spacing = config.drainage_spacing_mm
    if config.drainage_pattern == DrainagePattern.RADIAL:
        return [
            (
                spacing * cos((2.0 * pi * index) / count),
                spacing * sin((2.0 * pi * index) / count),
            )
            for index in range(count)
        ]

    if config.drainage_pattern == DrainagePattern.GRID:
        side = ceil(sqrt(count))
        offset = (side - 1) * 0.5
        candidates = [
            ((column - offset) * spacing, (row - offset) * spacing)
            for row in range(side)
            for column in range(side)
        ]
        candidates.sort(key=lambda point: ((point[0] ** 2) + (point[1] ** 2), point[1], point[0]))
        return candidates[:count]

    candidates = [(0.0, 0.0)]
    ring = 1
    while len(candidates) < count:
        for q in range(-ring, ring + 1):
            for r in range(-ring, ring + 1):
                if max(abs(q), abs(r), abs(-q - r)) != ring:
                    continue
                candidates.append(
                    (
                        spacing * (q + (r * 0.5)),
                        spacing * (sqrt(3.0) * 0.5 * r),
                    )
                )
        ring += 1
    candidates.sort(key=lambda point: ((point[0] ** 2) + (point[1] ** 2), point[1], point[0]))
    return candidates[:count]


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


def _smoothstep(value: float) -> float:
    value = _clamp(value, 0.0, 1.0)
    return value * value * (3.0 - (2.0 * value))


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
        return sections * max(1, ceil(48 / sections))
    if config.shape_type == ShapeType.STAR:
        anchor_count = sections * 2
        return anchor_count * max(1, ceil(48 / anchor_count))
    base_count = max(48, sections * 8, int(config.shape_wave_count) * 10)
    if config.shape_type in {ShapeType.GEAR, ShapeType.CLOVER, ShapeType.SCALLOP, ShapeType.FLOWER}:
        return max(60, base_count)
    return base_count


def _polygon_radius_factor(
    theta: float,
    vertex_count: int,
    inner_ratio: float | None = None,
) -> float:
    sector = (2.0 * pi) / vertex_count
    normalized = theta % (2.0 * pi)
    edge_index = min(vertex_count - 1, int(normalized / sector))
    next_index = (edge_index + 1) % vertex_count
    angle0 = edge_index * sector
    angle1 = (edge_index + 1) * sector

    radius0 = 1.0 if inner_ratio is None or edge_index % 2 == 0 else inner_ratio
    radius1 = 1.0 if inner_ratio is None or next_index % 2 == 0 else inner_ratio
    point0 = (radius0 * cos(angle0), radius0 * sin(angle0))
    point1 = (radius1 * cos(angle1), radius1 * sin(angle1))
    edge = (point1[0] - point0[0], point1[1] - point0[1])
    direction = (cos(theta), sin(theta))
    denominator = (direction[0] * edge[1]) - (direction[1] * edge[0])
    numerator = (point0[0] * edge[1]) - (point0[1] * edge[0])
    if abs(denominator) < 1e-9:
        return radius0
    return max(0.05, numerator / denominator)


def _get_point_angle_and_radius_factor(i: int, point_count: int, config: GeneratorConfig) -> tuple[float, float]:
    angle = (i / point_count) * (2.0 * pi)
    if config.shape_type == ShapeType.POLYGON:
        return angle, _polygon_radius_factor(angle, max(3, int(config.sections)))
    if config.shape_type == ShapeType.STAR:
        return angle, _polygon_radius_factor(
            angle,
            max(3, int(config.sections)) * 2,
            config.star_inner_ratio,
        )
    return angle, _shape_radius_factor(angle, config)


def _profile_radius_offset(z: float, config: GeneratorConfig) -> float:
    height = max(1e-6, config.height_mm)
    ratio = _clamp(z / height, 0.0, 1.0)
    position = _clamp(config.profile_position, 0.1, 0.9)
    if ratio <= position:
        bell = _smoothstep(ratio / position)
    else:
        bell = _smoothstep((1.0 - ratio) / (1.0 - position))

    depth = config.profile_depth_mm
    profile_offset = 0.0
    if config.profile_type == ProfileType.WAIST:
        profile_offset = depth * (1.0 - bell)
    elif config.profile_type == ProfileType.BELLY:
        profile_offset = depth * bell
    elif config.profile_type == ProfileType.FLARE:
        profile_offset = depth * _smoothstep(ratio)
    elif config.profile_type == ProfileType.SHOULDER:
        rise = _smoothstep(ratio / position)
        settle = 1.0 - (0.35 * _smoothstep((ratio - position) / (1.0 - position)))
        profile_offset = depth * rise * settle

    foot_offset = 0.0
    if config.foot_ring_mm > 0 and z < config.foot_height_mm:
        foot_offset = config.foot_ring_mm * (
            1.0 - _smoothstep(z / config.foot_height_mm)
        )
    return profile_offset + foot_offset


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
    if z <= z_base:
        body_radius = _lerp(0.0, r_o0, z_base, r_ob, z)
    else:
        body_radius = _lerp(z_base, r_ob, z_top, r_outer(z_top), z)

    rim_offset = 0.0
    if config.rim_style != RimStyle.PLAIN and z > z_lip:
        rim_progress = (z - z_lip) / max(1e-6, z_top - z_lip)
        if config.rim_style == RimStyle.BAND:
            rim_progress = min(1.0, rim_progress * 4.0)
        rim_offset = config.rim_lip_mm * _smoothstep(rim_progress)

    return body_radius + rim_offset + _profile_radius_offset(z, config)


def _inner_base_radius(z: float, config: GeneratorConfig) -> float:
    z_base = _effective_base_z(config)
    r_inner_at_base = config.inner_diameter_mm / 2.0
    taper = tan(radians(config.taper_deg))

    if z < z_base:
        return r_inner_at_base
    return r_inner_at_base + taper * (z - z_base)


def _shape_ring_outline(
    z: float,
    config: GeneratorConfig,
    *,
    inner: bool,
) -> list[tuple[float, float]]:
    point_count = _shape_point_count(config)
    rotation = (
        _middle_inbound_angle(z, config.height_mm, config)
        + _z_twist_angle(z, config.height_mm, config)
    )
    inner_radius = _inner_base_radius(z, config)
    circle_mesh_radius = inner_radius / max(1e-6, cos(pi / point_count))
    if inner:
        return [
            (
                circle_mesh_radius * cos(((index / point_count) * (2.0 * pi)) + rotation),
                circle_mesh_radius * sin(((index / point_count) * (2.0 * pi)) + rotation),
            )
            for index in range(point_count)
        ]

    base_radius = _outer_base_radius(z, config)
    samples = [
        _get_point_angle_and_radius_factor(index, point_count, config)
        for index in range(point_count)
    ]
    factors = [radius_factor for _, radius_factor in samples]
    factor_min = min(factors)
    factor_range = max(factors) - factor_min
    points: list[tuple[float, float]] = []
    for theta, radius_factor in samples:
        texture_offset = _texture_offset(z, theta, config)
        relief = (
            (radius_factor - factor_min) / factor_range
            if factor_range > 1e-9
            else 0.0
        )
        radius = max(
            0.05,
            base_radius + (config.shape_relief_mm * relief) + texture_offset,
        )
        world_theta = theta + rotation
        points.append((radius * cos(world_theta), radius * sin(world_theta)))

    wall_allowance = base_radius - inner_radius
    minimum_outer_radius = circle_mesh_radius + wall_allowance
    actual_minimum_radius = _outline_minimum_radius(points)
    if actual_minimum_radius < minimum_outer_radius:
        radial_offset = minimum_outer_radius - actual_minimum_radius
        adjusted: list[tuple[float, float]] = []
        for x, y in points:
            radius = max(0.05, sqrt((x * x) + (y * y)))
            scale = (radius + radial_offset) / radius
            adjusted.append((x * scale, y * scale))
        points = adjusted
    return points


def _outline_minimum_radius(points: list[tuple[float, float]]) -> float:
    minimum = float("inf")
    for index, (x0, y0) in enumerate(points):
        x1, y1 = points[(index + 1) % len(points)]
        dx = x1 - x0
        dy = y1 - y0
        length_squared = (dx * dx) + (dy * dy)
        if length_squared <= 1e-12:
            distance = sqrt((x0 * x0) + (y0 * y0))
        else:
            t = _clamp(-((x0 * dx) + (y0 * dy)) / length_squared, 0.0, 1.0)
            nearest_x = x0 + (t * dx)
            nearest_y = y0 + (t * dy)
            distance = sqrt((nearest_x * nearest_x) + (nearest_y * nearest_y))
        minimum = min(minimum, distance)
    return minimum


def _outline_radius_at_angle(
    points: list[tuple[float, float]],
    angle: float,
) -> float:
    direction = (cos(angle), sin(angle))
    intersections: list[float] = []
    for index, point0 in enumerate(points):
        point1 = points[(index + 1) % len(points)]
        edge = (point1[0] - point0[0], point1[1] - point0[1])
        denominator = (direction[0] * edge[1]) - (direction[1] * edge[0])
        if abs(denominator) < 1e-9:
            continue
        distance = ((point0[0] * edge[1]) - (point0[1] * edge[0])) / denominator
        edge_ratio = ((point0[0] * direction[1]) - (point0[1] * direction[0])) / denominator
        if distance >= 0 and -1e-9 <= edge_ratio <= 1.0 + 1e-9:
            intersections.append(distance)
    if not intersections:
        raise RuntimeError("Failed to locate the planter surface at the text angle.")
    return min(intersections)


def _outline_front_radial_span(
    points: list[tuple[float, float]],
    angle: float,
    tangent_limit: float,
) -> tuple[float, float]:
    radial = (cos(angle), sin(angle))
    tangent = (-sin(angle), cos(angle))
    candidates: list[float] = []
    projected = [
        (
            (x * tangent[0]) + (y * tangent[1]),
            (x * radial[0]) + (y * radial[1]),
        )
        for x, y in points
    ]
    for index, (tangent0, radial0) in enumerate(projected):
        tangent1, radial1 = projected[(index + 1) % len(projected)]
        if abs(tangent0) <= tangent_limit and radial0 > 0:
            candidates.append(radial0)
        delta = tangent1 - tangent0
        if abs(delta) < 1e-9:
            continue
        for boundary in (-tangent_limit, tangent_limit):
            ratio = (boundary - tangent0) / delta
            if 0 <= ratio <= 1:
                value = radial0 + (ratio * (radial1 - radial0))
                if value > 0:
                    candidates.append(value)
    if not candidates:
        radius = _outline_radius_at_angle(points, angle)
        return radius, radius
    return min(candidates), max(candidates)


def _drainage_holes_fit_floor(
    config: GeneratorConfig,
    positions: list[tuple[float, float]],
) -> bool:
    from shapely.geometry import Point, Polygon

    base_z = config.base_thickness_mm
    sample_heights = sorted({0.0, base_z * 0.5, base_z})
    footprint = Polygon(_shape_ring_outline(base_z, config, inner=True)).buffer(0)
    for z in sample_heights:
        outer = Polygon(_shape_ring_outline(z, config, inner=False)).buffer(0)
        footprint = footprint.intersection(outer)
    if footprint.is_empty:
        return False

    hole_radius = config.drain_hole_diameter_mm * 0.5
    return all(
        footprint.covers(Point(x, y).buffer(hole_radius, quad_segs=32))
        for x, y in positions
    )


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

    outer_rings = []
    for z in z_levels:
        outline = _shape_ring_outline(z, config, inner=False)
        outer_rings.append([(x, y, z) for x, y in outline])

    inner_z_levels = sorted(set([
        z_base,
        z_top,
        *[(z_base + (i / (height_steps - 1)) * (z_top - z_base)) for i in range(height_steps)],
    ]))
    inner_rings = []
    for z in inner_z_levels:
        outline = _shape_ring_outline(z, config, inner=True)
        inner_rings.append([(x, y, z) for x, y in outline])

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
            bottom_outline = [(point[0], point[1]) for point in outer_rings[0]]
            bottom_triangles = _triangulate_simple_polygon(bottom_outline)
            for a, b, c in bottom_triangles:
                faces.append([c, b, a])

            inner_base_start = inner_offset
            inner_outline = [(point[0], point[1]) for point in inner_rings[0]]
            inner_triangles = _triangulate_simple_polygon(inner_outline)
            for a, b, c in inner_triangles:
                faces.append([
                    inner_base_start + a,
                    inner_base_start + b,
                    inner_base_start + c,
                ])
    else:
        faces.extend(
            _build_annulus_faces(
                point_count,
                0,
                point_count,
                inner_offset,
                reverse=True,
            )
        )

    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    mesh.process(validate=True)
    trimesh.repair.fix_normals(mesh)
    if config.include_bottom and not mesh.is_watertight:
        trimesh.repair.fill_holes(mesh)
    if not mesh.is_watertight:
        raise RuntimeError("Generated mesh is not watertight.")
    return mesh


def _apply_drainage_pattern(
    planter_mesh: trimesh.Trimesh,
    config: GeneratorConfig,
) -> trimesh.Trimesh:
    cutters: list[trimesh.Trimesh] = []
    cutter_height = config.base_thickness_mm + 2.0
    for x, y in _drainage_hole_positions(config):
        cutter = trimesh.creation.cylinder(
            radius=config.drain_hole_diameter_mm * 0.5,
            height=cutter_height,
            sections=max(32, min(96, config.sections * 2)),
        )
        cutter.apply_translation((x, y, config.base_thickness_mm * 0.5))
        cutters.append(cutter)

    cutter_mesh = cutters[0] if len(cutters) == 1 else trimesh.boolean.union(
        cutters,
        engine="manifold",
    )
    result = trimesh.boolean.difference(
        [planter_mesh, cutter_mesh],
        engine="manifold",
    )
    if not isinstance(result, trimesh.Trimesh) or not result.is_watertight:
        raise RuntimeError("Failed to create a watertight drainage pattern.")
    return result


def build_planter_sleeve(config: GeneratorConfig) -> trimesh.Trimesh:
    config.validate()
    if (
        config.drain_hole_diameter_mm > 0
        and config.drainage_pattern != DrainagePattern.CENTER
    ):
        body_config = replace(
            config,
            drain_hole_diameter_mm=0.0,
            drainage_pattern=DrainagePattern.CENTER,
            text_content="",
        )
        mesh = build_planter_sleeve(body_config)
        mesh = _apply_drainage_pattern(mesh, config)
        return engrave_text_on_planter(mesh, config)

    mesh = _build_planter_mesh(config)
    return engrave_text_on_planter(mesh, config)


def analyze_printability(config: GeneratorConfig) -> list[str]:
    """Return non-fatal printability warnings for common FDM setups."""
    warnings: list[str] = []

    nozzle_mm = config.nozzle_diameter_mm
    recommended_min_wall = nozzle_mm * 3.0
    recommended_min_base = nozzle_mm * 3.0

    if config.wall_thickness_mm < recommended_min_wall:
        warnings.append(
            f"Wall thickness {config.wall_thickness_mm:.2f} mm is thin for a {nozzle_mm:g} mm nozzle "
            f"(recommended >= {recommended_min_wall:.2f} mm)."
        )

    if config.include_bottom and config.base_thickness_mm < recommended_min_base:
        warnings.append(
            f"Base thickness {config.base_thickness_mm:.2f} mm is low for durable prints "
            f"(recommended >= {recommended_min_base:.2f} mm)."
        )

    if abs(config.taper_deg) > 5.0:
        warnings.append(
            f"Taper {config.taper_deg:.1f} deg can introduce steep overhangs and poorer first-layer stability."
        )

    if config.texture_strength_mm > (config.wall_thickness_mm * 0.65):
        warnings.append(
            "Texture strength is high relative to wall thickness; local walls may become too thin."
        )

    if config.height_mm / max(config.wall_thickness_mm, 1e-6) > 70:
        warnings.append(
            "Tall and slender geometry may wobble during print. Consider thicker walls or lower height."
        )

    if config.sections > 220:
        warnings.append(
            "Very high section count increases mesh complexity and slicer memory usage."
        )

    if config.include_bottom and 0 < config.drain_hole_diameter_mm < nozzle_mm * 3.0:
        warnings.append(
            "Drain hole diameter is very small and can close during printing."
        )

    if config.layer_height_mm > nozzle_mm * 0.6:
        warnings.append(
            "Layer height is high relative to nozzle diameter; reduce it for reliable extrusion."
        )

    return warnings


def repair_config_for_printability(
    config: GeneratorConfig,
) -> tuple[GeneratorConfig, list[str]]:
    updates: dict[str, float | int] = {}
    repairs: list[str] = []
    minimum_feature = round(config.nozzle_diameter_mm * 3.0, 4)

    wall = max(config.wall_thickness_mm, minimum_feature)
    if wall != config.wall_thickness_mm:
        updates["wall_thickness_mm"] = wall
        repairs.append(f"Wall thickness increased to {wall:.2f} mm.")

    if config.include_bottom:
        base = max(config.base_thickness_mm, minimum_feature)
        if base != config.base_thickness_mm:
            updates["base_thickness_mm"] = base
            repairs.append(f"Base thickness increased to {base:.2f} mm.")

    if 0 < config.drain_hole_diameter_mm < minimum_feature:
        updates["drain_hole_diameter_mm"] = minimum_feature
        repairs.append(f"Drain hole diameter increased to {minimum_feature:.2f} mm.")

    texture_limit = round(wall * 0.65, 4)
    if config.texture_strength_mm > texture_limit:
        updates["texture_strength_mm"] = texture_limit
        repairs.append(f"Texture strength reduced to {texture_limit:.2f} mm.")

    taper = max(-5.0, min(5.0, config.taper_deg))
    if taper != config.taper_deg:
        updates["taper_deg"] = taper
        repairs.append(f"Taper limited to {taper:.1f} degrees.")

    sections = min(config.sections, 220)
    if sections != config.sections:
        updates["sections"] = sections
        repairs.append(f"Section count reduced to {sections}.")

    layer_height = min(config.layer_height_mm, round(config.nozzle_diameter_mm * 0.6, 4))
    if layer_height != config.layer_height_mm:
        updates["layer_height_mm"] = layer_height
        repairs.append(f"Layer height reduced to {layer_height:.2f} mm.")

    return replace(config, **updates), repairs


def engrave_text_on_planter(
    planter_mesh: trimesh.Trimesh,
    config: GeneratorConfig,
) -> trimesh.Trimesh:
    if (
        not config.text_content
        or config.text_height_mm <= 0
        or config.text_mode == TextMode.NONE
    ):
        return planter_mesh

    import numpy as np
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath
    from shapely import affinity
    from shapely.geometry import Polygon

    text_path = TextPath(
        (0.0, 0.0),
        config.text_content,
        size=1.0,
        prop=FontProperties(family="DejaVu Sans"),
    )
    geometry = None
    for contour in text_path.to_polygons(closed_only=True):
        polygon = Polygon(contour)
        if not polygon.is_valid or polygon.area <= 1e-8:
            continue
        geometry = polygon if geometry is None else geometry.symmetric_difference(polygon)
    if geometry is None or geometry.is_empty:
        raise ValueError("text_content did not produce any printable glyphs")

    geometry = geometry.buffer(0)
    min_x, min_y, max_x, max_y = geometry.bounds
    source_height = max_y - min_y
    if source_height <= 1e-8:
        raise ValueError("text_content did not produce measurable glyphs")
    scale = config.text_height_mm / source_height
    geometry = affinity.scale(geometry, xfact=scale, yfact=scale, origin=(0.0, 0.0))
    min_x, min_y, max_x, max_y = geometry.bounds
    geometry = affinity.translate(
        geometry,
        xoff=-((min_x + max_x) * 0.5),
        yoff=-((min_y + max_y) * 0.5),
    )
    min_x, min_y, max_x, max_y = geometry.bounds

    text_z = (
        config.text_position_z_mm
        if config.text_position_z_mm is not None
        else config.height_mm * 0.5
    )
    local_theta = radians(config.text_rotation_z_deg)
    theta = (
        local_theta
        + _middle_inbound_angle(text_z, config.height_mm, config)
        + _z_twist_angle(text_z, config.height_mm, config)
    )
    half_width = (max_x - min_x) * 0.5
    sample_heights = [
        _clamp(
            text_z + ((index / 4.0) - 0.5) * (max_y - min_y),
            0.0,
            config.height_mm,
        )
        for index in range(5)
    ]
    spans = [
        _outline_front_radial_span(
            _shape_ring_outline(sample_z, config, inner=False),
            theta,
            half_width,
        )
        for sample_z in sample_heights
    ]
    surface_min = min(span[0] for span in spans)
    surface_max = max(span[1] for span in spans)
    if half_width >= surface_min * 0.9:
        raise ValueError("text is too wide for the selected planter diameter")
    sagitta = surface_min - sqrt(max(1e-6, (surface_min ** 2) - (half_width ** 2)))
    overlap = min(
        config.wall_thickness_mm * 0.75,
        max(0.35, sagitta + 0.25),
    )
    if config.text_mode == TextMode.EMBOSS:
        radial_start = surface_min - overlap
        radial_end = surface_max + config.text_depth_mm + 0.15
    else:
        radial_start = surface_min - config.text_depth_mm - overlap
        radial_end = surface_max + 0.15
    radial_length = radial_end - radial_start

    polygons = [geometry] if geometry.geom_type == "Polygon" else list(geometry.geoms)
    text_meshes = [
        trimesh.creation.extrude_polygon(
            polygon,
            height=radial_length,
            engine="earcut",
        )
        for polygon in polygons
        if polygon.area > 1e-8
    ]
    if not text_meshes:
        raise ValueError("text_content did not produce printable polygons")
    text_mesh = trimesh.util.concatenate(text_meshes)

    radial_x = cos(theta)
    radial_y = sin(theta)
    tangent_x = -sin(theta)
    tangent_y = cos(theta)
    vertices = np.asarray(text_mesh.vertices).copy()
    local_x = vertices[:, 0].copy()
    local_z = vertices[:, 1].copy()
    radial_offset = vertices[:, 2].copy()
    radial_distance = radial_start + radial_offset
    vertices[:, 0] = (radial_distance * radial_x) + (local_x * tangent_x)
    vertices[:, 1] = (radial_distance * radial_y) + (local_x * tangent_y)
    vertices[:, 2] = text_z + local_z
    text_mesh.vertices = vertices

    source_volume = float(planter_mesh.volume)
    if config.text_mode == TextMode.EMBOSS:
        result = trimesh.boolean.union(
            [planter_mesh, text_mesh],
            engine="manifold",
        )
    else:
        result = trimesh.boolean.difference(
            [planter_mesh, text_mesh],
            engine="manifold",
        )
    if (
        not isinstance(result, trimesh.Trimesh)
        or not result.is_watertight
        or result.body_count != 1
    ):
        raise RuntimeError("Text boolean operation did not produce one watertight body.")
    volume_tolerance = max(1e-6, abs(source_volume) * 1e-9)
    result_volume = float(result.volume)
    if config.text_mode == TextMode.EMBOSS and result_volume <= source_volume + volume_tolerance:
        raise RuntimeError("Embossed text did not intersect the planter surface.")
    if config.text_mode == TextMode.ENGRAVE and result_volume >= source_volume - volume_tolerance:
        raise RuntimeError("Engraved text did not intersect the planter surface.")
    return result


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
