# Planter Sleeve Generator (3D Print)

> **This project was built with AI assistance (GitHub Copilot / Claude).**

Python tool with both CLI and browser UI to generate a customizable planter sleeve (cachepot) model and export to:

- STL
- 3MF

All source code and docs are in English.

## Deployment

The web UI is deployed on a Raspberry Pi 3 and accessible at:

**[▶ Live demo: https://womfy.com:50555/](https://womfy.com:50555/)**

Uses a valid Let's Encrypt TLS certificate (auto-renewed via certbot). The service starts automatically on boot via systemd.

## Features

- Parametric cylindrical sleeve for standard nursery pots
- Adjustable fit clearance, wall/base thickness, and taper
- Optional top rim lip for cleaner visual finish
- Surface texture displacement with stlTexturizer-style UV controls
- Optional custom image displacement that bakes into STL/3MF geometry
- Grayscale mapping controls: black/white levels, neutral gray midpoint, invert, and raise/lower mode
- Export to STL, 3MF, or both in one command
- Browser-based form UI for non-CLI usage

## Requirements

- Python 3.10+
- Trimesh export dependencies (installed automatically via pip)

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## Usage

### Browser UI

Start the local web app:

```bash
planter-web
```

Then open:

```text
http://127.0.0.1:5000
```

Set parameters in the form and click **Generate And Download**.

### CLI

```bash
planter-gen --pot-diameter 140 --height 135 --format both --output output/my_planter
```

This command creates:

- `output/my_planter.stl`
- `output/my_planter.3mf`

## Parameters

- `--pot-diameter` (required): real pot outer diameter in mm
- `--clearance` (default `1.2`): radial fit allowance in mm
- `--height` (required): sleeve height in mm
- `--wall` (default `3.0`): wall thickness in mm
- `--base` (default `4.0`): base thickness in mm
- `--taper` (default `1.5`): sidewall taper in degrees
- `--rim-lip` (default `1.2`): extra top lip width in mm
- `--texture-type` (default `none`): `none`, `rings`, `micro_rings`, `spiral`, `braid`, `grid`, `hex`, or `hammered`
- `--texture-strength` (default `0.6`): texture displacement depth in mm
- `--texture-scale` (default `2.0`): legacy uniform UV scale
- `--texture-scale-u` / `--texture-scale-v`: independent UV scaling (stlTexturizer-style)
- `--texture-offset-u` / `--texture-offset-v`: shift texture in UV tile space
- `--texture-rotation` (default `0`): rotate texture in degrees
- In web UI, set texture type to `image` and upload PNG/JPG/WebP to displace the mesh surface from grayscale values
- Grayscale mapping is configurable: choose `symmetric`, `raise`, or `lower`, then tune black/white levels and midpoint
- `--sections` (default `192`): circular mesh resolution
- `--format` (default `both`): `stl`, `3mf`, or `both`
- `--output` (default `output/planter_sleeve`): output filename stem

## Development Run

Without installing the console script:

```bash
python -m planter_generator --pot-diameter 100 --height 110 --format both
```

## Notes For Printing

- Recommended nozzle: 0.4 mm
- Recommended layer height: 0.2 mm
- Typical wall value: 2.4 mm to 3.2 mm
- If fit is tight, increase `--clearance` by 0.3 to 0.8 mm