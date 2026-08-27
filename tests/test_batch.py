import json
from pathlib import Path
import sys

import trimesh

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from planter_generator.batch import batch_job_from_mapping, generate_batch, parse_batch_data
from planter_generator.cli import main as cli_main
from planter_generator.model import DrainagePattern, ExportFormat, PrintProfile, TextMode


def test_parse_batch_json_and_csv():
    json_records = parse_batch_data(
        "models.json",
        json.dumps([{"name": "small", "pot_diameter": 40, "height": 45}]).encode(),
    )
    csv_records = parse_batch_data(
        "models.csv",
        b"name,pot_diameter,height,format\nsmall,40,45,stl\nlarge,80,90,3mf\n",
    )

    assert json_records[0]["name"] == "small"
    assert [record["format"] for record in csv_records] == ["stl", "3mf"]


def test_batch_job_normalizes_web_field_names_and_enums():
    job = batch_job_from_mapping(
        {
            "name": "radial-pot",
            "pot_diameter": "40",
            "clearance": "1.0",
            "height": "45",
            "wall": "2.4",
            "drain_hole_diameter": "3",
            "drainage_pattern": "radial",
            "drainage_hole_count": "4",
            "drainage_spacing_mm": "8",
            "text_mode": "engrave",
            "format": "stl",
        }
    )

    assert job.name == "radial-pot"
    assert job.config.inner_diameter_mm == 42.0
    assert job.config.wall_thickness_mm == 2.4
    assert job.config.drainage_pattern == DrainagePattern.RADIAL
    assert job.config.text_mode == TextMode.ENGRAVE
    assert job.export_format == ExportFormat.STL


def test_batch_profile_supplies_nozzle_and_layer_defaults():
    job = batch_job_from_mapping(
        {
            "name": "draft-pot",
            "pot_diameter": 40,
            "height": 45,
            "print_profile": "draft",
        }
    )

    assert job.config.print_profile == PrintProfile.DRAFT
    assert job.config.nozzle_diameter_mm == 0.6
    assert job.config.layer_height_mm == 0.3


def test_batch_invalid_enum_names_the_field_and_value():
    try:
        batch_job_from_mapping(
            {
                "name": "bad-profile",
                "pot_diameter": 40,
                "height": 45,
                "print_profile": "turbo",
            }
        )
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("invalid profile was accepted")

    assert "print_profile" in message
    assert "turbo" in message


def test_generate_batch_keeps_successes_and_writes_manifest(tmp_path):
    records = [
        {
            "name": "valid",
            "pot_diameter": 40,
            "height": 45,
            "shape_type": "polygon",
            "texture_type": "none",
            "z_rotation": 0,
            "sections": 32,
            "format": "stl",
        },
        {"name": "invalid", "pot_diameter": -1, "height": 45},
    ]

    manifest, files = generate_batch(records, tmp_path)

    assert manifest["generated_count"] == 1
    assert manifest["error_count"] == 1
    assert len(files) == 2
    manifest_path = tmp_path / "manifest.json"
    assert manifest_path in files
    model_path = next(path for path in files if path.suffix == ".stl")
    assert trimesh.load_mesh(model_path).is_watertight
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["errors"][0]["name"] == "invalid"


def test_batch_auto_repair_runs_before_strict_validation(tmp_path):
    records = [
        {
            "name": "repairable",
            "pot_diameter": 40,
            "height": 45,
            "print_profile": "custom",
            "nozzle_diameter": 0.4,
            "layer_height": 0.5,
            "auto_repair": True,
            "format": "stl",
        }
    ]

    manifest, files = generate_batch(records, tmp_path)

    assert manifest["generated_count"] == 1
    assert manifest["error_count"] == 0
    model = manifest["models"][0]
    assert model["config"]["layer_height_mm"] == 0.24
    assert any("Layer height" in repair for repair in model["repairs"])
    assert any(path.suffix == ".stl" for path in files)


def test_cli_batch_generates_archive_directory(tmp_path):
    batch_path = tmp_path / "batch.json"
    output_dir = tmp_path / "exports"
    batch_path.write_text(
        json.dumps(
            [
                {"name": "small", "pot_diameter": 40, "height": 45, "format": "stl"},
                {"name": "large", "pot_diameter": 60, "height": 65, "format": "stl"},
            ]
        ),
        encoding="utf-8",
    )

    result = cli_main(["--batch", str(batch_path), "--batch-output", str(output_dir)])

    assert result == 0
    assert len(list(output_dir.glob("*.stl"))) == 2
    assert json.loads((output_dir / "manifest.json").read_text())["generated_count"] == 2