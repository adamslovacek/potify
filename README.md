# Planter Sleeve Generator (3D Print)

> **This project was built with AI assistance (GitHub Copilot / Claude).**

Python CLI and browser app for designing dimensionally accurate, 3D-printable planter sleeves and exporting watertight STL or 3MF files.

## Deployment

**[▶ Live demo: https://womfy.com:50555/](https://womfy.com:50555/)**

## Highlights

- Parametric dimensions, fit clearance, taper, wall, base, and rim lip
- Guaranteed round inner cavity for the entered pot diameter, independent of the outer shape
- Center, radial, square-grid, or hexagonal drainage layouts
- Circle, polygon, star, ellipse, squircle, flower, gear, and other cross-section shapes
- Straight, waist, belly, flare, and shoulder silhouettes with rim and foot profiles
- Bounded shape relief in millimeters for predictable material use
- Twist, procedural textures, and image-based displacement
- Grayscale mapping controls for image displacement
- Watertight boolean text embossing and engraving
- Fine, standard, draft, and custom nozzle/layer profiles with one-click repairs
- Visual gallery with 24 curated styles, named browser styles, and versioned share links
- JSON/CSV batch generation from the browser or CLI
- Live Three.js preview with model size, round-pot fit, material estimate, print time, printer-bed presets, and printability warnings
- STL, 3MF, or combined export

## How Fit Works

Enter the measured outside diameter of the plant pot. The generator calculates the sleeve cavity as:

```text
inner diameter = pot diameter + (2 x clearance)
```

The inner cavity remains round even when the outside uses a polygon, flower, gear, or another decorative shape. Shape relief and silhouette depth add material outward instead of reducing the requested round fit. Taper still applies above the base: positive values widen the cavity toward the top, while negative values narrow it.

## Requirements

- Python 3.10+
- Dependencies installed automatically by pip

## Quick Start

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
planter-web
```

Open `http://127.0.0.1:5001`.

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
planter-web
```

## Usage

### Browser UI

The editor is organized into four sections:

| Section | Controls |
| --- | --- |
| **Dimensions** | Pot diameter, clearance, height, wall, bottom, drainage, taper, and rim |
| **Shape** | Cross-section, silhouette, shape relief, profile position, foot ring, and twist |
| **Surface** | Procedural or image texture, text embossing/engraving, and preview material |
| **Print** | Nozzle/layer profile, printability warnings, and automatic repair |

The live preview reports model dimensions, guaranteed round-pot fit, estimated PLA use, estimated print time, polygon count, and compatibility with the selected printer bed. Material and time values are planning estimates; use the slicer result for the final numbers.

### Built-in Styles

Styles are complete visual starting points rather than size presets:

| Style | Family | Character |
| --- | --- | --- |
| **Plain Round** | Calm | Fast, clean cylindrical sleeve |
| **Soft Square** | Calm | Rounded-square body with a subtle belly |
| **Ribbed Column** | Geometric | Straight form with horizontal ribs |
| **Hex Helix** | Geometric | Six-sided form with a controlled twist |
| **Seven Petals** | Organic | Seven-lobed flower profile |
| **Pebble** | Organic | Wide, softly sculpted and hammered form |
| **Fine Gear** | Geometric | Restrained industrial teeth and shoulder |
| **Sculpted Waist** | Dramatic | Squircle body with waist, foot, band, and braid |
| **Lotus Twist** | Organic | Nine petals, flowing waist, and spiral motion |
| **Clover Bell** | Organic | Four-lobed body opening into a bell |
| **Coral Spiral** | Organic | Ten scallops with a marine spiral surface |
| **Teardrop Flow** | Organic | Asymmetric teardrop with a raised shoulder |
| **Lens Ripple** | Calm | Low oval lens wrapped in fine ripples |
| **Star Lantern** | Dramatic | Eight-point lantern with a subtle grid |
| **Origami Fold** | Geometric | Twisted diamond with crisp untextured faces |
| **Basalt Fortress** | Dramatic | Heavy five-sided shoulder on a broad foot |
| **Honeycomb Tower** | Geometric | Soft hexagonal body with cellular texture |
| **Raku Flame** | Dramatic | Six-point star with strong upward twist |
| **Nordic Vase** | Calm | Quiet circular waist and fine horizontal lines |
| **Mechanical Bloom** | Geometric | Twelve engineered teeth with a flared body |
| **Zen Dune** | Calm | Wide oval belly with restrained hammered grain |
| **Prism Torque** | Dramatic | Triangular prism under a strong twist |
| **Moon Crater** | Organic | Rounded squircle with a cratered shoulder |
| **Copper Cascade** | Dramatic | Braided teardrop flowing through a tall waist |

Use the `All`, `Calm`, `Organic`, `Geometric`, and `Dramatic` filters to browse the gallery.

Applying a built-in or saved style changes only shape, silhouette, rim, foot, twist, texture, and preview material. It preserves pot diameter, clearance, height, bottom, drainage, and print settings.

The top toolbar also provides:

- `Styles`: open the visual style gallery
- `Export STL` / `Export 3MF`: export the current geometry
- `More > Save style`: save visual settings in browser storage
- `More > Share`: create a versioned configuration link
- `More > Batch`: upload JSON or CSV and download a ZIP with a manifest
- `More > Repair`: apply conservative printability fixes
- `More > Load` / `Save`: import or export the complete JSON configuration

Preview material colors are visual only and are not stored in STL files.

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

Generate a flower sleeve with a soft belly, bounded shape relief, top band, and foot:

```bash
planter-gen --pot-diameter 140 --height 135 --shape-type flower --shape-wave-count 7 --shape-relief 4 --profile-type belly --profile-depth 2.5 --rim-style band --rim-lip 1.5 --foot-ring 1 --foot-height 8
```

### Batch Export

Run the included JSON example:

```bash
planter-gen --batch examples/batch.json --batch-output output/batch
```

JSON accepts an array of configuration objects. CSV uses the same field names in its header:

```csv
name,pot_diameter,height,shape_type,profile_type,shape_relief,format
small,80,90,squircle,straight,3,stl
petals,100,110,flower,belly,4,3mf
```

Batch fields use the same names as saved browser configurations. Common short aliases such as `wall`, `base`, `rim_lip`, `shape_relief`, `profile_depth`, and `foot_ring` are accepted. Batch generation keeps successful rows when another row fails and records every result in `manifest.json`. Use `--auto-repair` to repair every batch row before generation.

## Parameter Reference

### Dimensions and Bottom

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
- `--rim-style` (default `flared`): `plain`, `flared`, or `band`

### Shape and Silhouette

- `--shape-type` (default `squircle`): cross-section shape
- `--shape-relief` (default `4`): maximum decorative outer-shape relief in mm
- `--profile-type` (default `straight`): `straight`, `waist`, `belly`, `flare`, or `shoulder`
- `--profile-depth` (default `0`): silhouette strength in mm
- `--profile-position` (default `0.55`): relative vertical profile position from `0.1` to `0.9`
- `--foot-ring` (default `0`): optional widened base in mm
- `--foot-height` (default `8`): foot transition height in mm
- `--star-inner-ratio`: inner-point ratio for star, gear, and flower forms
- `--shape-aspect-ratio`: width/height ratio for ellipse-like forms
- `--shape-roundness`: corner or tooth softness
- `--shape-wave-depth` / `--shape-wave-count`: lobe depth and count
- `--z-rotation` (default `26`): total bottom-to-top twist in degrees
- `--sections` (default `7`, maximum `256`): sides, teeth, or primary divisions

### Surface and Text

- `--texture-type` (default `braid`): procedural texture pattern
- `--texture-strength` (default `0.9`): texture displacement depth in mm
- `--texture-scale` (default `2.4`): legacy uniform UV scale
- `--texture-scale-u` / `--texture-scale-v`: independent UV scaling
- `--texture-offset-u` / `--texture-offset-v`: UV tile offset
- `--texture-rotation` (default `28`): texture rotation in degrees
- `--text`: text content, up to 50 characters
- `--text-mode`: `none`, `emboss`, or `engrave`
- `--text-height` / `--text-depth`: text dimensions in mm
- `--text-position-z` / `--text-rotation-z`: text placement controls

The browser additionally supports PNG, JPG, and WebP displacement images up to 8 MB, including brightness, contrast, blur, inversion, and grayscale mapping controls.

### Print and Output

- `--print-profile` (default `standard`): `fine`, `standard`, `draft`, or `custom`
- `--nozzle-diameter` / `--layer-height`: override profile dimensions
- `--auto-repair`: adjust common fragile settings before generation
- `--batch`: UTF-8 `.json` or `.csv` configuration list
- `--batch-output`: batch output directory
- `--format` (default `both`): `stl`, `3mf`, or `both`
- `--output` (default `output/planter_sleeve`): output filename stem

## Development

Without installing the console script:

```bash
python -m planter_generator --pot-diameter 100 --height 110 --format both
```

Run the test suite:

```bash
python -m pytest -q
```

The tests cover geometry validation, watertight meshes, drainage, sculpted profiles, boolean text, batch generation, web endpoints, and configuration propagation.

## Notes For Printing

- Recommended nozzle: 0.4 mm
- Recommended layer height: 0.2 mm
- Typical wall value: 2.4 mm to 3.2 mm
- If fit is tight, increase `--clearance` by 0.3 to 0.8 mm
- Treat browser material and time values as estimates; the slicer remains authoritative
- High relief, deep silhouettes, and large feet increase material use and overall bed footprint