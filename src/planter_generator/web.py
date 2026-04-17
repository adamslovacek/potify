from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from flask import Flask, render_template, request, send_file

from .model import ExportFormat, GeneratorConfig, TextureType, build_planter_sleeve, export_model


def _to_float(value: str, name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc


def _to_int(value: str, name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _to_bool(value: str | None) -> bool:
    if value is None:
        return False
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def create_app() -> Flask:
    template_root = Path(__file__).resolve().parent / "templates"
    app = Flask(__name__, template_folder=str(template_root))

    source_files = [Path(__file__).resolve(), template_root / "index.html"]

    def current_source_version() -> float:
        return max((p.stat().st_mtime for p in source_files if p.exists()), default=0.0)

    defaults = {
        "pot_diameter": "140",
        "clearance": "1.2",
        "height": "135",
        "wall": "3.0",
        "base": "4.0",
        "include_bottom": "on",
        "taper": "1.5",
        "rim_lip": "1.2",
        "texture_type": "none",
        "texture_strength": "0.7",
        "texture_scale": "2.0",
        "texture_rotation": "0",
        "sections": "192",
        "format": "stl",
    }

    numeric_fields = {
        "pot_diameter": _to_float,
        "clearance": _to_float,
        "height": _to_float,
        "wall": _to_float,
        "base": _to_float,
        "taper": _to_float,
        "rim_lip": _to_float,
        "texture_strength": _to_float,
        "texture_scale": _to_float,
        "texture_rotation": _to_float,
        "sections": _to_int,
    }

    def merged_form_data() -> dict[str, str]:
        form = {**defaults, **request.form.to_dict()}
        form["include_bottom"] = "on" if request.form.get("include_bottom") else ""
        return form

    def normalize_config_payload(form: dict[str, str]) -> dict[str, object]:
        payload: dict[str, object] = {}
        for key, parser in numeric_fields.items():
            payload[key] = parser(form.get(key), key)
        payload["include_bottom"] = _to_bool(form.get("include_bottom"))
        payload["texture_type"] = form.get("texture_type", "none")
        payload["material_type"] = form.get("material_type", "concrete")
        payload["format"] = form.get("format", "stl")
        return payload

    @app.get("/")
    def index():
        return render_template("index.html", values=defaults, error=None)

    @app.post("/generate")
    def generate():
        form = merged_form_data()
        export_choice = form.get("format", "stl")

        try:
            config = GeneratorConfig(
                inner_diameter_mm=_to_float(form.get("pot_diameter"), "pot_diameter")
                + (2.0 * _to_float(form.get("clearance"), "clearance")),
                height_mm=_to_float(form.get("height"), "height"),
                wall_thickness_mm=_to_float(form.get("wall"), "wall"),
                base_thickness_mm=_to_float(form.get("base"), "base"),
                include_bottom=bool(form.get("include_bottom")),
                taper_deg=_to_float(form.get("taper"), "taper"),
                rim_lip_mm=_to_float(form.get("rim_lip"), "rim_lip"),
                texture_type=TextureType(form.get("texture_type", "none")),
                texture_strength_mm=_to_float(form.get("texture_strength"), "texture_strength"),
                texture_scale=_to_float(form.get("texture_scale"), "texture_scale"),
                texture_rotation_deg=_to_float(form.get("texture_rotation"), "texture_rotation"),
                sections=_to_int(form.get("sections"), "sections"),
            )
            fmt = ExportFormat(export_choice)
        except (ValueError, KeyError) as exc:
            return render_template("index.html", values=form, error=str(exc)), 400

        try:
            mesh = build_planter_sleeve(config)
        except Exception as exc:
            return render_template("index.html", values=form, error=str(exc)), 400

        with TemporaryDirectory() as tmp:
            output_stem = (Path(tmp) / "planter_sleeve")
            try:
                exported_files = export_model(mesh, output_stem, fmt)
            except Exception as exc:
                return render_template("index.html", values=form, error=str(exc)), 500

            if len(exported_files) == 1:
                target = exported_files[0]
                mime = (
                    "model/stl"
                    if target.suffix.lower() == ".stl"
                    else "model/3mf"
                )
                payload = BytesIO(target.read_bytes())
                payload.seek(0)
                return send_file(
                    payload,
                    mimetype=mime,
                    as_attachment=True,
                    download_name=target.name,
                )

            archive = BytesIO()
            with ZipFile(archive, mode="w", compression=ZIP_DEFLATED) as zipf:
                for file_path in exported_files:
                    zipf.write(file_path, arcname=file_path.name)
            archive.seek(0)

            return send_file(
                archive,
                mimetype="application/zip",
                as_attachment=True,
                download_name="planter_exports.zip",
            )

    @app.post("/save-config")
    def save_config():
        form = merged_form_data()
        try:
            payload = normalize_config_payload(form)
            # Validate generator-specific fields before exporting config.
            GeneratorConfig(
                inner_diameter_mm=payload["pot_diameter"] + (2.0 * payload["clearance"]),
                height_mm=payload["height"],
                wall_thickness_mm=payload["wall"],
                base_thickness_mm=payload["base"],
                include_bottom=payload["include_bottom"],
                taper_deg=payload["taper"],
                rim_lip_mm=payload["rim_lip"],
                texture_type=TextureType(payload["texture_type"]),
                texture_strength_mm=payload["texture_strength"],
                texture_scale=payload["texture_scale"],
                texture_rotation_deg=payload["texture_rotation"],
                sections=payload["sections"],
            ).validate()
            ExportFormat(str(payload["format"]))
        except (ValueError, KeyError) as exc:
            return render_template("index.html", values=form, error=str(exc)), 400

        output = BytesIO(json.dumps(payload, indent=2).encode("utf-8"))
        output.seek(0)
        return send_file(
            output,
            mimetype="application/json",
            as_attachment=True,
            download_name="planter_config.json",
        )

    @app.get("/__version__")
    def version():
        return {"version": current_source_version()}

    return app


def main() -> int:
    app = create_app()
    app.run(host="0.0.0.0", port=5001, debug=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
