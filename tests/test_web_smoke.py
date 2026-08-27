import json
from io import BytesIO
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import trimesh
from lxml import html as lxml_html

import planter_generator.web as web
from planter_generator.model import DrainagePattern, ProfileType, PrintProfile, RimStyle, TextMode
from planter_generator.web import create_app


def test_index_renders():
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Planter Sleeve Generator" in response.data


def test_index_exposes_24_curated_style_presets():
    app = create_app()
    client = app.test_client()

    source = client.get("/").get_data(as_text=True)
    preset_source = source.split("const PRESETS = {", 1)[1].split(
        "const CUSTOM_PRESETS_KEY",
        1,
    )[0]
    style_names = (
        "Plain Round",
        "Soft Square",
        "Ribbed Column",
        "Hex Helix",
        "Seven Petals",
        "Pebble",
        "Fine Gear",
        "Sculpted Waist",
        "Lotus Twist",
        "Clover Bell",
        "Coral Spiral",
        "Teardrop Flow",
        "Lens Ripple",
        "Star Lantern",
        "Origami Fold",
        "Basalt Fortress",
        "Honeycomb Tower",
        "Raku Flame",
        "Nordic Vase",
        "Mechanical Bloom",
        "Zen Dune",
        "Prism Torque",
        "Moon Crater",
        "Copper Cascade",
    )

    assert preset_source.count('family: "') == 24
    assert preset_source.count('family: "calm"') == 5
    assert preset_source.count('family: "organic"') == 7
    assert preset_source.count('family: "geometric"') == 6
    assert preset_source.count('family: "dramatic"') == 6
    assert all(f'label: "{name}"' in preset_source for name in style_names)


def test_server_parser_defaults_to_local_non_debug_mode():
    parser = web._build_server_parser()

    defaults = parser.parse_args([])
    development = parser.parse_args(["--host", "0.0.0.0", "--port", "5050", "--debug"])
    secure = parser.parse_args(["--cert", "cert.pem", "--key", "key.pem"])

    assert defaults.host == "127.0.0.1"
    assert defaults.port == 5001
    assert defaults.debug is False
    assert development.host == "0.0.0.0"
    assert development.port == 5050
    assert development.debug is True
    assert secure.cert == Path("cert.pem")
    assert secure.key == Path("key.pem")


def test_saved_config_uses_automatic_middle_inbound_position():
    app = create_app()
    client = app.test_client()

    response = client.post("/save-config", data={})

    assert response.status_code == 200
    assert json.loads(response.data)["middle_inbound_z"] is None


def test_generate_smoke_returns_download(monkeypatch):
    app = create_app()
    client = app.test_client()

    def fake_build(config):
        assert config.inner_diameter_mm > 0
        return trimesh.creation.box(extents=(1, 1, 1))

    def fake_export(mesh, output_stem, fmt):
        assert mesh.is_volume
        assert fmt.value == "stl"
        target = output_stem.with_suffix(".stl")
        target.write_text("solid t\nendsolid t\n", encoding="utf-8")
        return [target]

    monkeypatch.setattr("planter_generator.web.build_planter_sleeve", fake_build)
    monkeypatch.setattr("planter_generator.web.export_model", fake_export)

    response = client.post("/generate", data={"format": "stl"})

    assert response.status_code == 200
    assert response.headers.get("Content-Disposition", "").startswith("attachment;")
    assert response.headers.get("Content-Type", "").startswith("model/stl")


def test_generate_propagates_new_geometry_and_print_fields(monkeypatch):
    app = create_app()
    client = app.test_client()
    captured = []

    def fake_build(config):
        captured.append(config)
        return trimesh.creation.box(extents=(1, 1, 1))

    def fake_export(mesh, output_stem, fmt):
        assert mesh.is_volume
        assert fmt.value == "stl"
        target = output_stem.with_suffix(".stl")
        target.write_text("solid t\nendsolid t\n", encoding="utf-8")
        return [target]

    monkeypatch.setattr("planter_generator.web.build_planter_sleeve", fake_build)
    monkeypatch.setattr("planter_generator.web.export_model", fake_export)

    response = client.post(
        "/generate",
        data={
            "format": "stl",
            "drain_hole_diameter": "3",
            "drainage_pattern": "radial",
            "drainage_hole_count": "4",
            "drainage_spacing": "12",
            "print_profile": "draft",
            "nozzle_diameter": "0.6",
            "layer_height": "0.3",
            "text_content": "POT",
            "text_mode": "engrave",
            "profile_type": "waist",
            "profile_depth": "8",
            "profile_position": "0.6",
            "rim_style": "band",
            "foot_ring": "2",
            "foot_height": "7",
            "shape_relief": "6",
        },
    )

    assert response.status_code == 200
    config = captured[0]
    assert config.drainage_pattern == DrainagePattern.RADIAL
    assert config.drainage_hole_count == 4
    assert config.print_profile == PrintProfile.DRAFT
    assert config.nozzle_diameter_mm == 0.6
    assert config.text_mode == TextMode.ENGRAVE
    assert config.profile_type == ProfileType.WAIST
    assert config.profile_depth_mm == 8.0
    assert config.rim_style == RimStyle.BAND
    assert config.foot_ring_mm == 2.0
    assert config.shape_relief_mm == 6.0


def test_repair_config_returns_form_values_and_actions():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/repair-config",
        data={
            "include_bottom": "on",
            "wall": "0.9",
            "base": "0.8",
            "taper": "6.2",
            "texture_strength": "2.0",
            "sections": "240",
            "drain_hole_diameter": "0.8",
            "print_profile": "draft",
            "nozzle_diameter": "0.6",
            "layer_height": "0.3",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["values"]["wall"] == 1.8
    assert payload["values"]["base"] == 1.8
    assert payload["values"]["sections"] == 220
    assert len(payload["repairs"]) >= 6


def test_repair_config_can_fix_initially_excessive_layer_height():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/repair-config",
        data={
            "print_profile": "custom",
            "nozzle_diameter": "0.4",
            "layer_height": "0.5",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["values"]["layer_height"] == 0.24
    assert any("Layer height" in repair for repair in payload["repairs"])


def test_batch_generate_returns_zip_with_manifest():
    app = create_app()
    client = app.test_client()
    batch = json.dumps(
        [
            {
                "name": "small",
                "pot_diameter": 40,
                "height": 45,
                "shape_type": "polygon",
                "texture_type": "none",
                "z_rotation": 0,
                "sections": 32,
                "format": "stl",
            }
        ]
    ).encode()

    response = client.post(
        "/batch-generate",
        data={"batch_file": (BytesIO(batch), "batch.json")},
    )

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/zip")
    with ZipFile(BytesIO(response.data)) as archive:
        names = archive.namelist()
        manifest = json.loads(archive.read("manifest.json"))
    assert any(name.endswith(".stl") for name in names)
    assert manifest["generated_count"] == 1


def test_generate_rejects_invalid_texture_image():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/generate",
        data={
            "format": "stl",
            "texture_type": "image",
            "texture_image": (BytesIO(b"not an image"), "texture.png"),
        },
    )

    assert response.status_code == 400
    assert b"texture_image must be a valid" in response.data


def test_generate_rejects_oversized_upload():
    app = create_app()
    assert app.config["MAX_CONTENT_LENGTH"] == 8 * 1024 * 1024
    app.config["MAX_CONTENT_LENGTH"] = 1024
    client = app.test_client()

    response = client.post(
        "/generate",
        data={
            "format": "stl",
            "texture_type": "image",
            "texture_image": (BytesIO(b"x" * 2048), "texture.png"),
        },
    )

    assert response.status_code == 413
    assert b"8 MB" in response.data


def test_index_exposes_validation_constraints_and_live_statuses():
    app = create_app()
    client = app.test_client()

    response = client.get("/")
    document = lxml_html.fromstring(response.get_data(as_text=True))

    clearance = document.xpath('//input[@name="clearance"]')[0]
    sections = document.xpath('//input[@name="sections"]')[0]
    preview_error = document.get_element_by_id("preview-error")
    export_statuses = document.xpath('//span[contains(@class, "export-status")]')

    assert clearance.get("min") == "0"
    assert sections.get("max") == "256"
    assert preview_error.get("role") == "status"
    assert preview_error.get("aria-live") == "polite"
    assert all(status.get("role") == "status" for status in export_statuses)
    assert all(status.get("aria-live") == "polite" for status in export_statuses)

    for name in (
        "drainage_pattern",
        "drainage_hole_count",
        "drainage_spacing",
        "print_profile",
        "nozzle_diameter",
        "layer_height",
        "auto_repair",
        "text_mode",
        "text_rotation_z",
        "profile_type",
        "profile_depth",
        "profile_position",
        "rim_style",
        "foot_ring",
        "foot_height",
        "shape_relief",
    ):
        assert document.xpath(f'//*[@name="{name}"]'), name

    for element_id in (
        "save-custom-preset-btn",
        "delete-custom-preset-btn",
        "share-config-btn",
        "batch-export-btn",
        "repair-config-btn",
        "preset-dialog",
        "share-dialog",
        "batch-dialog",
        "operation-status",
        "open-style-gallery-btn",
        "style-dialog",
        "style-gallery",
        "style-filter",
        "style-count",
    ):
        assert document.get_element_by_id(element_id) is not None

    error_response = client.post("/generate", data={"pot_diameter": "invalid"})
    error_document = lxml_html.fromstring(error_response.get_data(as_text=True))
    error = error_document.xpath('//div[contains(@class, "error")]')[0]
    assert error.get("role") == "alert"
