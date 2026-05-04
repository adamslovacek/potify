from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from flask import Flask, render_template, request, send_file


def _load_model_symbols():
    # Lazy-load heavy geometry stack so the web server can start even if mesh deps are unavailable.
    from .model import (
        DisplacementMode,
        ExportFormat,
        GeneratorConfig,
        ShapeType,
        TextureType,
        build_planter_sleeve,
        export_model,
    )

    return {
        "DisplacementMode": DisplacementMode,
        "ExportFormat": ExportFormat,
        "GeneratorConfig": GeneratorConfig,
        "ShapeType": ShapeType,
        "TextureType": TextureType,
        "build_planter_sleeve": build_planter_sleeve,
        "export_model": export_model,
    }


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


def _extract_texture_image_payload(max_size: int = 768) -> tuple[tuple[float, ...], int, int] | None:
    file = request.files.get("texture_image")
    if file is None or not file.filename:
        return None
    try:
        from PIL import Image
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Pillow is required for image displacement textures.") from exc

    try:
        image = Image.open(file.stream).convert("L")
    except Exception as exc:
        raise ValueError("texture_image must be a valid PNG/JPG/WebP image") from exc

    w, h = image.size
    if w <= 0 or h <= 0:
        raise ValueError("texture_image must have non-zero dimensions")

    # Keep memory and processing bounded for interactive use.
    if max(w, h) > max_size:
        if w >= h:
            new_w = max_size
            new_h = max(1, int(round((h / w) * max_size)))
        else:
            new_h = max_size
            new_w = max(1, int(round((w / h) * max_size)))
        image = image.resize((new_w, new_h), Image.Resampling.BILINEAR)

    w, h = image.size
    pixels = tuple((px / 255.0) for px in image.getdata())
    return pixels, w, h


def create_app() -> Flask:
    template_root = Path(__file__).resolve().parent / "templates"
    app = Flask(__name__, template_folder=str(template_root))

    module_root = Path(__file__).resolve().parent
    source_files = [Path(__file__).resolve(), module_root / "model.py", template_root / "index.html"]

    def current_source_version() -> float:
        return max((p.stat().st_mtime for p in source_files if p.exists()), default=0.0)

    defaults = {
        "pot_diameter": "140",
        "clearance": "1.2",
        "height": "135",
        "wall": "3.0",
        "base": "4.0",
        "include_bottom": "on",
        "taper": "1.9",
        "rim_lip": "1.4",
        "drain_hole_diameter": "0.0",
        "texture_type": "braid",
        "texture_strength": "0.9",
        "texture_scale": "2.4",
        "texture_scale_u": "2.4",
        "texture_scale_v": "2.4",
        "texture_offset_u": "0.0",
        "texture_offset_v": "0.0",
        "texture_rotation": "28",
        "texture_displacement_mode": "symmetric",
        "texture_gray_black": "0.0",
        "texture_gray_white": "1.0",
        "texture_gray_midpoint": "0.5",
        "texture_gray_invert": "",
        "middle_inbound_turns": "0.0",
        "middle_inbound_z": "50.0",
        "z_rotation": "26.0",
        "shape_type": "squircle",
        "star_inner_ratio": "0.45",
        "shape_aspect_ratio": "1.0",
        "shape_roundness": "0.35",
        "shape_wave_depth": "0.6",
        "shape_wave_count": "8",
        "sections": "7",
        "material_type": "concrete",
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
        "drain_hole_diameter": _to_float,
        "texture_strength": _to_float,
        "texture_scale": _to_float,
        "texture_scale_u": _to_float,
        "texture_scale_v": _to_float,
        "texture_offset_u": _to_float,
        "texture_offset_v": _to_float,
        "texture_rotation": _to_float,
        "texture_gray_black": _to_float,
        "texture_gray_white": _to_float,
        "texture_gray_midpoint": _to_float,
        "middle_inbound_turns": _to_float,
        "middle_inbound_z": _to_float,
        "z_rotation": _to_float,
        "star_inner_ratio": _to_float,
        "shape_aspect_ratio": _to_float,
        "shape_roundness": _to_float,
        "shape_wave_depth": _to_float,
        "shape_wave_count": _to_int,
        "sections": _to_int,
    }

    def merged_form_data() -> dict[str, str]:
        form = {**defaults, **request.form.to_dict()}
        form["include_bottom"] = "on" if request.form.get("include_bottom") else ""
        form["texture_gray_invert"] = "on" if request.form.get("texture_gray_invert") else ""
        if (not form.get("middle_inbound_turns")) and form.get("twist_turns"):
            form["middle_inbound_turns"] = form.get("twist_turns", "0")
        if (not form.get("texture_scale_u")) and form.get("texture_scale"):
            form["texture_scale_u"] = form.get("texture_scale", "2.0")
        if (not form.get("texture_scale_v")) and form.get("texture_scale"):
            form["texture_scale_v"] = form.get("texture_scale", "2.0")
        return form

    def normalize_config_payload(form: dict[str, str]) -> dict[str, object]:
        payload: dict[str, object] = {}
        for key, parser in numeric_fields.items():
            payload[key] = parser(form.get(key), key)
        payload["include_bottom"] = _to_bool(form.get("include_bottom"))
        payload["texture_type"] = form.get("texture_type", "none")
        payload["texture_displacement_mode"] = form.get("texture_displacement_mode", "symmetric")
        payload["texture_gray_invert"] = _to_bool(form.get("texture_gray_invert"))
        payload["shape_type"] = form.get("shape_type", "polygon")
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
        image_payload = _extract_texture_image_payload()
        symbols = _load_model_symbols()

        GeneratorConfig = symbols["GeneratorConfig"]
        TextureType = symbols["TextureType"]
        DisplacementMode = symbols["DisplacementMode"]
        ShapeType = symbols["ShapeType"]
        ExportFormat = symbols["ExportFormat"]
        build_planter_sleeve = symbols["build_planter_sleeve"]
        export_model = symbols["export_model"]

        image_data = None
        image_w = 0
        image_h = 0
        if image_payload is not None:
            image_data, image_w, image_h = image_payload

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
                drain_hole_diameter_mm=_to_float(form.get("drain_hole_diameter"), "drain_hole_diameter"),
                texture_type=TextureType(form.get("texture_type", "none")),
                texture_strength_mm=_to_float(form.get("texture_strength"), "texture_strength"),
                texture_scale=_to_float(form.get("texture_scale"), "texture_scale"),
                texture_scale_u=_to_float(form.get("texture_scale_u"), "texture_scale_u"),
                texture_scale_v=_to_float(form.get("texture_scale_v"), "texture_scale_v"),
                texture_offset_u=_to_float(form.get("texture_offset_u"), "texture_offset_u"),
                texture_offset_v=_to_float(form.get("texture_offset_v"), "texture_offset_v"),
                texture_rotation_deg=_to_float(form.get("texture_rotation"), "texture_rotation"),
                texture_displacement_mode=DisplacementMode(
                    form.get("texture_displacement_mode", "symmetric")
                ),
                texture_gray_black=_to_float(form.get("texture_gray_black"), "texture_gray_black"),
                texture_gray_white=_to_float(form.get("texture_gray_white"), "texture_gray_white"),
                texture_gray_midpoint=_to_float(form.get("texture_gray_midpoint"), "texture_gray_midpoint"),
                texture_gray_invert=_to_bool(form.get("texture_gray_invert")),
                texture_image_data=image_data,
                texture_image_width=image_w,
                texture_image_height=image_h,
                middle_inbound_turns=_to_float(form.get("middle_inbound_turns"), "middle_inbound_turns"),
                middle_inbound_z_mm=_to_float(form.get("middle_inbound_z"), "middle_inbound_z"),
                z_rotation_deg=_to_float(form.get("z_rotation"), "z_rotation"),
                shape_type=ShapeType(form.get("shape_type", "polygon")),
                star_inner_ratio=_to_float(form.get("star_inner_ratio"), "star_inner_ratio"),
                shape_aspect_ratio=_to_float(form.get("shape_aspect_ratio"), "shape_aspect_ratio"),
                shape_roundness=_to_float(form.get("shape_roundness"), "shape_roundness"),
                shape_wave_depth=_to_float(form.get("shape_wave_depth"), "shape_wave_depth"),
                shape_wave_count=_to_int(form.get("shape_wave_count"), "shape_wave_count"),
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
        symbols = _load_model_symbols()

        GeneratorConfig = symbols["GeneratorConfig"]
        TextureType = symbols["TextureType"]
        DisplacementMode = symbols["DisplacementMode"]
        ShapeType = symbols["ShapeType"]
        ExportFormat = symbols["ExportFormat"]

        try:
            payload = normalize_config_payload(form)
            texture_type_value = TextureType(payload["texture_type"])
            validate_texture_type = (
                TextureType.NONE if texture_type_value == TextureType.IMAGE else texture_type_value
            )
            # Validate generator-specific fields before exporting config.
            GeneratorConfig(
                inner_diameter_mm=payload["pot_diameter"] + (2.0 * payload["clearance"]),
                height_mm=payload["height"],
                wall_thickness_mm=payload["wall"],
                base_thickness_mm=payload["base"],
                include_bottom=payload["include_bottom"],
                taper_deg=payload["taper"],
                rim_lip_mm=payload["rim_lip"],
                drain_hole_diameter_mm=payload["drain_hole_diameter"],
                texture_type=validate_texture_type,
                texture_strength_mm=payload["texture_strength"],
                texture_scale=payload["texture_scale"],
                texture_scale_u=payload["texture_scale_u"],
                texture_scale_v=payload["texture_scale_v"],
                texture_offset_u=payload["texture_offset_u"],
                texture_offset_v=payload["texture_offset_v"],
                texture_rotation_deg=payload["texture_rotation"],
                texture_displacement_mode=DisplacementMode(payload["texture_displacement_mode"]),
                texture_gray_black=payload["texture_gray_black"],
                texture_gray_white=payload["texture_gray_white"],
                texture_gray_midpoint=payload["texture_gray_midpoint"],
                texture_gray_invert=payload["texture_gray_invert"],
                middle_inbound_turns=payload["middle_inbound_turns"],
                middle_inbound_z_mm=payload["middle_inbound_z"],
                z_rotation_deg=payload["z_rotation"],
                shape_type=ShapeType(payload["shape_type"]),
                star_inner_ratio=payload["star_inner_ratio"],
                shape_aspect_ratio=payload["shape_aspect_ratio"],
                shape_roundness=payload["shape_roundness"],
                shape_wave_depth=payload["shape_wave_depth"],
                shape_wave_count=payload["shape_wave_count"],
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
    import argparse
    import ssl
    parser = argparse.ArgumentParser(description="Run the Planter Generator web server.")
    parser.add_argument('--port', type=int, default=5001, help='Port to run the server on (default: 5001)')
    parser.add_argument('--cert', type=str, help='Path to SSL certificate file')
    parser.add_argument('--key', type=str, help='Path to SSL key file')
    args = parser.parse_args()
    app = create_app()
    
    # Configure SSL if cert and key are provided
    ssl_context = None
    if args.cert and args.key:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(args.cert, args.key)
    
    app.run(host="0.0.0.0", port=args.port, debug=True, ssl_context=ssl_context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
