# Planter Sleeve Generator (3D Print)

> **This project was built with AI assistance (GitHub Copilot / Claude).**

Python CLI and browser app for generating customizable, 3D-printable planter sleeves and exporting STL or 3MF files.

## Deployment

**[▶ Live demo: https://womfy.com:50555/](https://womfy.com:50555/)**

## Features

- Parametric dimensions, fit clearance, taper, wall, base, and rim lip
- Center, radial, square-grid, or hexagonal drainage layouts
- Polygon, star, ellipse, squircle, flower, gear, and other cross-section shapes
- Twist, procedural textures, and image-based displacement
- Grayscale mapping controls for image displacement
- Watertight boolean text embossing and engraving
- Fine, standard, draft, and custom nozzle/layer profiles with one-click repairs
- Named browser presets and versioned share links
- JSON/CSV batch generation from the browser or CLI
- Live Three.js preview, printer-bed presets, and printability warnings
- STL, 3MF, or combined export

## Requirements

- Python 3.10+
- Dependencies installed automatically by pip

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

For development and tests:

```bash
pip install -e ".[dev]"
pytest
```

## Usage

### Browser UI

```bash
planter-web
```

Open `http://127.0.0.1:5001`, adjust the model, and choose an export button.

The top toolbar also provides:

- `Preset +` / `Preset -`: save and remove named presets in browser storage
- `Share`: create a URL that restores the complete current configuration
- `Batch`: upload a JSON or CSV list and download all outputs with a manifest in one ZIP
- `Repair`: apply conservative fixes for the selected nozzle and layer profile

The server binds only to localhost by default. Use `planter-web --host 0.0.0.0` to expose it on the local network, or add `--debug` during development.

### CLI

```bash
planter-gen --pot-diameter 140 --height 135 --format both --output output/my_planter
```

This creates `output/my_planter.stl` and `output/my_planter.3mf`.

Generate four radial drainage holes and engraved text:

```bash
planter-gen --pot-diameter 100 --height 110 --shape-type polygon --texture-type none --z-rotation 0 --sections 64 --drain-hole-diameter 3 --drainage-pattern radial --drainage-hole-count 4 --drainage-spacing 18 --text GROW --text-mode engrave --text-height 8 --text-depth 0.6 --format stl --output output/radial_engraved
```

Apply draft-profile printability repairs before export:

```bash
planter-gen --pot-diameter 140 --height 135 --print-profile draft --auto-repair
```

### Batch Export

Run the included JSON example:

```bash
planter-gen --batch examples/batch.json --batch-output output/batch
```

JSON accepts an array of configuration objects. CSV uses the same field names in its header:

```csv
name,pot_diameter,height,format,drainage_pattern,drainage_hole_count
small,80,90,stl,center,1
draining,100,110,3mf,radial,4
```

Batch generation keeps successful rows when another row fails and records every result in `manifest.json`. Use `--auto-repair` to repair every batch row before generation.

## Main Parameters

- `--pot-diameter` (required): real pot outer diameter in mm
- `--clearance` (default `1.2`): radial fit allowance in mm
- `--height` (required): sleeve height in mm
- `--wall` (default `3.0`): wall thickness in mm
- `--base` (default `4.0`): base thickness in mm
- `--no-bottom`: generate an open-bottom sleeve
- `--drain-hole-diameter` (default `0`): diameter of each drainage hole; requires a bottom
- `--drainage-pattern`: `center`, `radial`, `grid`, or `hex`
- `--drainage-hole-count` (default `1`, maximum `32`): holes in non-center layouts
- `--drainage-spacing` (default `12`): radial offset or grid pitch in mm
- `--taper` (default `1.9`): sidewall taper in degrees
- `--rim-lip` (default `1.4`): extra top lip width in mm
- `--shape-type` (default `squircle`): cross-section shape
- `--texture-type` (default `braid`): procedural texture pattern
- `--texture-strength` (default `0.9`): texture displacement depth in mm
- `--texture-scale` (default `2.4`): legacy uniform UV scale
- `--texture-scale-u` / `--texture-scale-v`: independent UV scaling
- `--texture-offset-u` / `--texture-offset-v`: UV tile offset
- `--texture-rotation` (default `28`): texture rotation in degrees
- `--sections` (default `7`, maximum `256`): primary divisions or side count
- `--print-profile`: `fine`, `standard`, `draft`, or `custom`
- `--nozzle-diameter` / `--layer-height`: override profile dimensions
- `--auto-repair`: adjust common fragile settings before generation
- `--text`: text content, up to 50 characters
- `--text-mode`: `none`, `emboss`, or `engrave`
- `--text-height` / `--text-depth`: text dimensions in mm
- `--text-position-z` / `--text-rotation-z`: text placement controls
- `--batch`: UTF-8 `.json` or `.csv` configuration list
- `--batch-output`: batch output directory
- `--format` (default `both`): `stl`, `3mf`, or `both`
- `--output` (default `output/planter_sleeve`): output filename stem

The browser UI also supports PNG, JPG, and WebP displacement images up to 8 MB.

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