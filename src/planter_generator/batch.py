from __future__ import annotations

import csv
from dataclasses import dataclass, fields
from enum import Enum
from io import StringIO
import json
from pathlib import Path
import re
from typing import Mapping

from .model import (
    DisplacementMode,
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
    print_profile_dimensions,
)


MAX_BATCH_ITEMS = 100


@dataclass(frozen=True)
class BatchJob:
    name: str
    config: GeneratorConfig
    export_format: ExportFormat
    auto_repair: bool = False


_ALIASES = {
    "wall": "wall_thickness_mm",
    "base": "base_thickness_mm",
    "taper": "taper_deg",
    "rim_lip": "rim_lip_mm",
    "drain_hole_diameter": "drain_hole_diameter_mm",
    "drainage_spacing": "drainage_spacing_mm",
    "texture_strength": "texture_strength_mm",
    "texture_rotation": "texture_rotation_deg",
    "middle_inbound_z": "middle_inbound_z_mm",
    "z_rotation": "z_rotation_deg",
    "nozzle_diameter": "nozzle_diameter_mm",
    "layer_height": "layer_height_mm",
    "text_height": "text_height_mm",
    "text_depth": "text_depth_mm",
    "text_position_z": "text_position_z_mm",
    "text_rotation_z": "text_rotation_z_deg",
}

_FLOAT_FIELDS = {
    "wall_thickness_mm",
    "base_thickness_mm",
    "taper_deg",
    "rim_lip_mm",
    "texture_strength_mm",
    "texture_scale",
    "texture_scale_u",
    "texture_scale_v",
    "texture_offset_u",
    "texture_offset_v",
    "texture_rotation_deg",
    "texture_gray_black",
    "texture_gray_white",
    "texture_gray_midpoint",
    "middle_inbound_turns",
    "middle_inbound_z_mm",
    "z_rotation_deg",
    "star_inner_ratio",
    "shape_aspect_ratio",
    "shape_roundness",
    "shape_wave_depth",
    "nozzle_diameter_mm",
    "layer_height_mm",
    "drain_hole_diameter_mm",
    "drainage_spacing_mm",
    "text_height_mm",
    "text_depth_mm",
    "text_position_z_mm",
    "text_rotation_z_deg",
}

_INT_FIELDS = {
    "shape_wave_count",
    "sections",
    "height_steps",
    "drainage_hole_count",
}

_BOOL_FIELDS = {
    "include_bottom",
    "texture_gray_invert",
}

_ENUM_FIELDS = {
    "texture_type": TextureType,
    "texture_displacement_mode": DisplacementMode,
    "shape_type": ShapeType,
    "print_profile": PrintProfile,
    "drainage_pattern": DrainagePattern,
    "text_mode": TextMode,
}


def _is_blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _as_float(value: object, name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc


def _as_int(value: object, name: str) -> int:
    try:
        parsed = float(value)
        integer = int(parsed)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if parsed != integer:
        raise ValueError(f"{name} must be an integer")
    return integer


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _safe_name(value: object) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value).strip()).strip("._-")
    return name[:64] or "planter"


def parse_batch_data(filename: str, payload: bytes) -> list[dict[str, object]]:
    suffix = Path(filename).suffix.lower()
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("batch file must use UTF-8 encoding") from exc

    if suffix == ".json":
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("batch JSON is invalid") from exc
        if isinstance(parsed, dict):
            parsed = parsed.get("configs")
        if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
            raise ValueError("batch JSON must be an array of configuration objects")
        records = [dict(item) for item in parsed]
    elif suffix == ".csv":
        reader = csv.DictReader(StringIO(text))
        if not reader.fieldnames:
            raise ValueError("batch CSV must contain a header row")
        records = [
            dict(row)
            for row in reader
            if any(not _is_blank(value) for value in row.values())
        ]
    else:
        raise ValueError("batch file must have a .json or .csv extension")

    if not records:
        raise ValueError("batch file does not contain any configurations")
    if len(records) > MAX_BATCH_ITEMS:
        raise ValueError(f"batch file may contain at most {MAX_BATCH_ITEMS} configurations")
    return records


def batch_job_from_mapping(
    record: Mapping[str, object],
    *,
    validate: bool = True,
) -> BatchJob:
    normalized: dict[str, object] = {}
    for source, target in _ALIASES.items():
        if source in record and not _is_blank(record[source]):
            normalized[target] = record[source]
    config_field_names = {field.name for field in fields(GeneratorConfig)}
    for name in config_field_names:
        if name in record and not _is_blank(record[name]):
            normalized[name] = record[name]

    if not _is_blank(record.get("inner_diameter_mm")):
        inner_diameter = _as_float(record["inner_diameter_mm"], "inner_diameter_mm")
    else:
        if _is_blank(record.get("pot_diameter")):
            raise ValueError("pot_diameter or inner_diameter_mm is required")
        pot_diameter = _as_float(record["pot_diameter"], "pot_diameter")
        clearance = _as_float(record.get("clearance", 1.2), "clearance")
        if pot_diameter <= 0:
            raise ValueError("pot_diameter must be > 0")
        if clearance < 0:
            raise ValueError("clearance must be >= 0")
        inner_diameter = pot_diameter + (2.0 * clearance)

    if _is_blank(record.get("height")) and _is_blank(record.get("height_mm")):
        raise ValueError("height is required")
    height = _as_float(record.get("height_mm", record.get("height")), "height")

    kwargs: dict[str, object] = {
        "inner_diameter_mm": inner_diameter,
        "height_mm": height,
    }
    for name, value in normalized.items():
        if name in {"inner_diameter_mm", "height_mm"}:
            continue
        if name in _FLOAT_FIELDS:
            kwargs[name] = _as_float(value, name)
        elif name in _INT_FIELDS:
            kwargs[name] = _as_int(value, name)
        elif name in _BOOL_FIELDS:
            kwargs[name] = _as_bool(value)
        elif name in _ENUM_FIELDS:
            enum_type = _ENUM_FIELDS[name]
            try:
                kwargs[name] = enum_type(str(value))
            except ValueError as exc:
                choices = ", ".join(member.value for member in enum_type)
                raise ValueError(
                    f"{name} must be one of [{choices}]; got {value!r}"
                ) from exc
        elif name == "text_content":
            kwargs[name] = str(value)

    profile = kwargs.get("print_profile", PrintProfile.STANDARD)
    if not isinstance(profile, PrintProfile):
        profile = PrintProfile(str(profile))
    profile_nozzle, profile_layer = print_profile_dimensions(profile)
    if "nozzle_diameter_mm" not in normalized:
        kwargs["nozzle_diameter_mm"] = profile_nozzle
    if "layer_height_mm" not in normalized:
        kwargs["layer_height_mm"] = profile_layer

    config = GeneratorConfig(**kwargs)
    if validate:
        config.validate()
    export_format = ExportFormat(str(record.get("format", ExportFormat.STL.value)))
    return BatchJob(
        name=_safe_name(record.get("name", "planter")),
        config=config,
        export_format=export_format,
        auto_repair=_as_bool(record.get("auto_repair", False)),
    )


def _config_payload(config: GeneratorConfig) -> dict[str, object]:
    payload: dict[str, object] = {}
    for field in fields(config):
        value = getattr(config, field.name)
        if isinstance(value, Enum):
            payload[field.name] = value.value
        elif isinstance(value, tuple):
            payload[field.name] = list(value)
        else:
            payload[field.name] = value
    return payload


def generate_batch(
    records: list[Mapping[str, object]],
    output_dir: Path,
) -> tuple[dict[str, object], list[Path]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    written: list[Path] = []

    for index, record in enumerate(records, start=1):
        record_name = _safe_name(record.get("name", f"planter_{index}"))
        try:
            job = batch_job_from_mapping(record, validate=False)
            config = job.config
            repairs: list[str] = []
            if job.auto_repair:
                config, repairs = repair_config_for_printability(config)
            config.validate()
            mesh = build_planter_sleeve(config)
            output_stem = output_dir / f"{index:03d}_{job.name}"
            model_files = export_model(mesh, output_stem, job.export_format)
            written.extend(model_files)
            generated.append(
                {
                    "index": index,
                    "name": job.name,
                    "files": [path.name for path in model_files],
                    "repairs": repairs,
                    "config": _config_payload(config),
                }
            )
        except Exception as exc:
            errors.append({"index": index, "name": record_name, "error": str(exc)})

    manifest: dict[str, object] = {
        "requested_count": len(records),
        "generated_count": len(generated),
        "error_count": len(errors),
        "models": generated,
        "errors": errors,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    written.append(manifest_path)
    return manifest, written