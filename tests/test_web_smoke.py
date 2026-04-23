from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import trimesh

from planter_generator.web import create_app


def test_index_renders():
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Planter Sleeve Generator" in response.data


def test_generate_smoke_returns_download(monkeypatch):
    app = create_app()
    client = app.test_client()

    def fake_build(_config):
        return trimesh.creation.box(extents=(1, 1, 1))

    def fake_export(_mesh, output_stem, _fmt):
        target = output_stem.with_suffix(".stl")
        target.write_text("solid t\nendsolid t\n", encoding="utf-8")
        return [target]

    monkeypatch.setattr("planter_generator.web.build_planter_sleeve", fake_build)
    monkeypatch.setattr("planter_generator.web.export_model", fake_export)

    response = client.post("/generate", data={"format": "stl"})

    assert response.status_code == 200
    assert response.headers.get("Content-Disposition", "").startswith("attachment;")
    assert response.headers.get("Content-Type", "").startswith("model/stl")
