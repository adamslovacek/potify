from __future__ import annotations

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
        "taper": "1.5",
        "rim_lip": "1.2",
        "texture_type": "none",
        "texture_strength": "0.7",
        "texture_scale": "2.0",
        "texture_rotation": "0",
        "sections": "192",
        "format": "both",
    }

    @app.get("/")
    def index():
        return render_template("index.html", values=defaults, error=None)

    @app.post("/generate")
    def generate():
        form = {**defaults, **request.form.to_dict()}
        export_choice = form.get("format", "both")

        try:
            config = GeneratorConfig(
                inner_diameter_mm=_to_float(form.get("pot_diameter"), "pot_diameter")
                + (2.0 * _to_float(form.get("clearance"), "clearance")),
                height_mm=_to_float(form.get("height"), "height"),
                wall_thickness_mm=_to_float(form.get("wall"), "wall"),
                base_thickness_mm=_to_float(form.get("base"), "base"),
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

    @app.get("/__version__")
    def version():
        return {"version": current_source_version()}

    return app


def main() -> int:
    app = create_app()
    app.run(host="0.0.0.0", port=5004, debug=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
