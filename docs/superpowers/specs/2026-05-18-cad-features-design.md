# CAD Geometry Feature Extraction MVP Design

## Goal

Build a lightweight Python CLI that reads STEP or IGES 3D CAD files and writes a JSON report with deterministic geometry and topology statistics.

The first version focuses on foundational extraction, not manufacturing-feature recognition. It should prove the OpenCascade parsing and reporting pipeline before adding hole, fillet, chamfer, pocket, slot, or ML-based recognition.

## Scope

### Included

- Input formats: `.step`, `.stp`, `.iges`, `.igs`.
- CLI usage: `cad-features <input-file> --output <report.json>`.
- Dependency path: Conda environment using conda-forge, with `pythonocc-core` and `pytest`.
- Output: UTF-8 formatted JSON report.
- Geometry/topology data:
  - Model bounding box.
  - Model surface area and volume.
  - Counts of solids, shells, faces, wires, edges, and vertices.
  - Face surface type distribution.
  - Edge curve type distribution.
  - Per-face summary with index, surface type, and area when available.
  - Per-edge summary with index, curve type, and length when available.
- Tests using a generated temporary STEP box model, not committed binary CAD fixtures.

### Excluded

- DXF/DWG extraction.
- Native commercial CAD formats.
- Manufacturing feature recognition such as holes, pockets, slots, chamfers, or fillets.
- Mesh generation, UV-grid extraction, face adjacency graph export, or ML pipelines.
- Web service or frontend.

## Architecture

The project is a small Python package with a CLI entry point.

### CLI Layer

Responsibilities:

- Parse `cad-features <input> --output <json>` arguments.
- Validate input path, output parent directory, and supported extension.
- Call the CAD loading and analysis pipeline.
- Serialize the report to JSON.
- Convert expected user-facing errors into clear non-zero CLI exits.

The CLI does not directly traverse OpenCascade topology.

### CAD Loading Layer

Responsibilities:

- Select a STEP or IGES reader based on file extension.
- Read the file into an OpenCascade `TopoDS_Shape`.
- Report read failures with explicit messages.

Supported extension mapping:

- STEP: `.step`, `.stp`
- IGES: `.iges`, `.igs`

### Analysis Layer

Responsibilities:

- Traverse OpenCascade topology using `TopExp_Explorer` or equivalent APIs.
- Count topology entities by type.
- Compute model-level bounding box, area, and volume.
- Classify each face's surface type.
- Classify each edge's curve type.
- Compute local face area and edge length when possible.

Unknown or unsupported OpenCascade geometry types are reported as `unknown` rather than failing the whole command.

### Report Model Layer

Responsibilities:

- Build a stable Python dictionary that can be serialized directly to JSON.
- Keep schema versioned from the start with `schema_version: "0.1"`.
- Use plain lists and numbers so downstream services can consume the output without CAD-specific bindings.

## Data Flow

```text
CLI arguments
  -> validate input path, output path, extension
  -> load STEP/IGES into TopoDS_Shape
  -> traverse topology
  -> compute geometry statistics
  -> build report dictionary
  -> write UTF-8 JSON
```

## JSON Report Shape

```json
{
  "schema_version": "0.1",
  "source": {
    "path": "part.step",
    "format": "step"
  },
  "model": {
    "is_null": false,
    "bounding_box": {
      "min": [0.0, 0.0, 0.0],
      "max": [10.0, 20.0, 30.0],
      "size": [10.0, 20.0, 30.0]
    },
    "area": 2200.0,
    "volume": 6000.0
  },
  "topology": {
    "solids": 1,
    "shells": 1,
    "faces": 6,
    "wires": 6,
    "edges": 12,
    "vertices": 8
  },
  "geometry": {
    "face_surface_types": {
      "plane": 6
    },
    "edge_curve_types": {
      "line": 12
    }
  },
  "faces": [
    {
      "index": 1,
      "surface_type": "plane",
      "area": 100.0
    }
  ],
  "edges": [
    {
      "index": 1,
      "curve_type": "line",
      "length": 10.0
    }
  ]
}
```

Per-face and per-edge output is included in the MVP. If large models make reports too big later, a separate summary-only mode can be added.

## Error Handling

- Missing input file: fail with a clear CLI error.
- Unsupported extension: fail with the supported extension list.
- Reader failure: fail with a read/parse error for the chosen format.
- Null shape after import: fail with a clear invalid-model error.
- Missing output parent directory: fail without creating directories automatically.
- Local face or edge measurement failure: set that local numeric field to `null` and continue.
- Unknown surface or curve type: use `unknown` and continue.

## Testing

### Unit Tests

- Extension-to-format detection.
- Input/output path validation behavior.
- Basic report shape and required keys.
- Unsupported extension handling.

### Integration Test

- Generate a temporary STEP box model with pythonOCC during the test.
- Run the CLI against that file.
- Assert the generated JSON contains:
  - `schema_version == "0.1"`
  - `topology.solids == 1`
  - `topology.faces == 6`
  - `geometry.face_surface_types.plane == 6`
  - Bounding box size close to the generated box dimensions.
  - Volume close to the generated box volume.

## Project Files

Expected files:

- `environment.yml` — Conda environment definition.
- `pyproject.toml` — Python package metadata and CLI entry point.
- `src/cad_features/__init__.py`
- `src/cad_features/cli.py`
- `src/cad_features/loaders.py`
- `src/cad_features/analyzer.py`
- `src/cad_features/report.py`
- `src/cad_features/errors.py`
- `tests/test_cli.py`
- `tests/test_report.py`

## Success Criteria

- A user can create the Conda environment and run the CLI.
- `cad-features sample.step --output report.json` writes a JSON report.
- The generated STEP box integration test passes.
- Expected user errors return non-zero exits with readable messages.
- The implementation remains scoped to deterministic geometry/topology extraction.