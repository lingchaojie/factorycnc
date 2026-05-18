# CAD Geometry Feature Extraction MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that reads STEP/IGES CAD files and writes a deterministic JSON report with geometry and topology statistics.

**Architecture:** The package has a thin CLI layer, a format-aware CAD loading layer, an OpenCascade analysis layer, and a JSON report layer. The CLI validates paths and delegates all CAD work to focused modules so future feature-recognition logic can be added without rewriting the command interface.

**Tech Stack:** Python 3.11, Conda, conda-forge `pythonocc-core`, pytest, setuptools console scripts.

---

## File Structure

Create these files:

- `environment.yml` — Conda environment with Python, pythonOCC, pytest, and pip.
- `pyproject.toml` — package metadata, pytest config, and `cad-features` console script.
- `src/cad_features/__init__.py` — package version.
- `src/cad_features/errors.py` — user-facing exception types.
- `src/cad_features/report.py` — extension detection and report dictionary helpers that do not import OpenCascade.
- `src/cad_features/cli.py` — argument parsing, path validation, report writing, and exit codes.
- `src/cad_features/loaders.py` — STEP/IGES loading into `TopoDS_Shape`.
- `src/cad_features/analyzer.py` — OpenCascade topology traversal and geometry statistics.
- `tests/test_report.py` — pure unit tests for extension detection and report building.
- `tests/test_cli.py` — CLI validation tests and generated STEP integration test.

The implementation is intentionally small. `report.py` stays CAD-kernel-free so basic schema tests can run even if pythonOCC is not importable. `loaders.py` and `analyzer.py` are the only modules that import `OCC`.

---

### Task 1: Project Skeleton and Pure Report Helpers

**Files:**
- Create: `environment.yml`
- Create: `pyproject.toml`
- Create: `src/cad_features/__init__.py`
- Create: `src/cad_features/errors.py`
- Create: `src/cad_features/report.py`
- Test: `tests/test_report.py`

- [ ] **Step 1: Write failing report tests**

Create `tests/test_report.py`:

```python
import pytest

from cad_features.errors import UnsupportedFormatError
from cad_features.report import build_report, detect_format


def test_detect_format_accepts_step_and_iges_extensions():
    assert detect_format("part.step") == "step"
    assert detect_format("part.stp") == "step"
    assert detect_format("part.iges") == "iges"
    assert detect_format("part.igs") == "iges"
    assert detect_format("PART.STEP") == "step"


def test_detect_format_rejects_unsupported_extension():
    with pytest.raises(UnsupportedFormatError) as exc_info:
        detect_format("part.dxf")

    assert ".step" in str(exc_info.value)
    assert ".iges" in str(exc_info.value)


def test_build_report_contains_stable_schema():
    report = build_report(
        source_path="sample.step",
        source_format="step",
        model={
            "is_null": False,
            "bounding_box": {
                "min": [0.0, 0.0, 0.0],
                "max": [1.0, 2.0, 3.0],
                "size": [1.0, 2.0, 3.0],
            },
            "area": 22.0,
            "volume": 6.0,
        },
        topology={
            "solids": 1,
            "shells": 1,
            "faces": 6,
            "wires": 6,
            "edges": 12,
            "vertices": 8,
        },
        geometry={
            "face_surface_types": {"plane": 6},
            "edge_curve_types": {"line": 12},
        },
        faces=[{"index": 1, "surface_type": "plane", "area": 1.0}],
        edges=[{"index": 1, "curve_type": "line", "length": 1.0}],
    )

    assert report == {
        "schema_version": "0.1",
        "source": {"path": "sample.step", "format": "step"},
        "model": {
            "is_null": False,
            "bounding_box": {
                "min": [0.0, 0.0, 0.0],
                "max": [1.0, 2.0, 3.0],
                "size": [1.0, 2.0, 3.0],
            },
            "area": 22.0,
            "volume": 6.0,
        },
        "topology": {
            "solids": 1,
            "shells": 1,
            "faces": 6,
            "wires": 6,
            "edges": 12,
            "vertices": 8,
        },
        "geometry": {
            "face_surface_types": {"plane": 6},
            "edge_curve_types": {"line": 12},
        },
        "faces": [{"index": 1, "surface_type": "plane", "area": 1.0}],
        "edges": [{"index": 1, "curve_type": "line", "length": 1.0}],
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_report.py -v
```

Expected: FAIL during import because `cad_features` or its modules do not exist.

- [ ] **Step 3: Add project metadata and environment**

Create `environment.yml`:

```yaml
name: cad-features
channels:
  - conda-forge
dependencies:
  - python=3.11
  - pythonocc-core
  - pytest
  - pip
  - pip:
      - -e .
```

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "cad-features"
version = "0.1.0"
description = "Extract deterministic geometry and topology statistics from STEP and IGES CAD files."
requires-python = ">=3.11"

[project.scripts]
cad-features = "cad_features.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

Create `src/cad_features/__init__.py`:

```python
__version__ = "0.1.0"
```

- [ ] **Step 4: Add errors module**

Create `src/cad_features/errors.py`:

```python
class CadFeaturesError(Exception):
    """Base class for expected user-facing errors."""


class UnsupportedFormatError(CadFeaturesError):
    pass


class InputFileError(CadFeaturesError):
    pass


class OutputFileError(CadFeaturesError):
    pass


class CadReadError(CadFeaturesError):
    pass


class CadAnalysisError(CadFeaturesError):
    pass
```

- [ ] **Step 5: Add pure report helpers**

Create `src/cad_features/report.py`:

```python
from pathlib import Path
from typing import Any

from cad_features.errors import UnsupportedFormatError

SUPPORTED_FORMATS = {
    ".step": "step",
    ".stp": "step",
    ".iges": "iges",
    ".igs": "iges",
}


def detect_format(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()
    try:
        return SUPPORTED_FORMATS[suffix]
    except KeyError as exc:
        supported = ", ".join(sorted(SUPPORTED_FORMATS))
        raise UnsupportedFormatError(
            f"Unsupported CAD format '{suffix or '<none>'}'. Supported extensions: {supported}."
        ) from exc


def build_report(
    *,
    source_path: str,
    source_format: str,
    model: dict[str, Any],
    topology: dict[str, int],
    geometry: dict[str, dict[str, int]],
    faces: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "source": {"path": source_path, "format": source_format},
        "model": model,
        "topology": topology,
        "geometry": geometry,
        "faces": faces,
        "edges": edges,
    }
```

- [ ] **Step 6: Run tests to verify they pass**

Run:

```bash
pytest tests/test_report.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 7: Commit**

If the project has been initialized as a git repository, run:

```bash
git add environment.yml pyproject.toml src/cad_features/__init__.py src/cad_features/errors.py src/cad_features/report.py tests/test_report.py
git commit -m "feat: add CAD report skeleton"
```

If the project is still not a git repository, skip the commit and note that this step was not applicable.

---

### Task 2: CLI Validation and JSON Writing

**Files:**
- Create: `src/cad_features/cli.py`
- Modify: `src/cad_features/report.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI validation tests**

Create `tests/test_cli.py`:

```python
import json
from pathlib import Path

import pytest

from cad_features.cli import main


def test_cli_rejects_missing_input_file(tmp_path, capsys):
    output_path = tmp_path / "report.json"

    exit_code = main([str(tmp_path / "missing.step"), "--output", str(output_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Input file does not exist" in captured.err
    assert not output_path.exists()


def test_cli_rejects_unsupported_extension(tmp_path, capsys):
    input_path = tmp_path / "part.dxf"
    input_path.write_text("0\nEOF\n", encoding="utf-8")
    output_path = tmp_path / "report.json"

    exit_code = main([str(input_path), "--output", str(output_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Unsupported CAD format" in captured.err
    assert not output_path.exists()


def test_cli_rejects_missing_output_parent(tmp_path, capsys):
    input_path = tmp_path / "part.step"
    input_path.write_text("ISO-10303-21;\nEND-ISO-10303-21;\n", encoding="utf-8")
    output_path = tmp_path / "missing" / "report.json"

    exit_code = main([str(input_path), "--output", str(output_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Output directory does not exist" in captured.err
    assert not output_path.exists()


def test_cli_writes_json_report_from_injected_analyzer(tmp_path):
    input_path = tmp_path / "part.step"
    input_path.write_text("ISO-10303-21;\nEND-ISO-10303-21;\n", encoding="utf-8")
    output_path = tmp_path / "report.json"

    def analyze_file(path: Path, source_format: str):
        assert path == input_path
        assert source_format == "step"
        return {
            "model": {
                "is_null": False,
                "bounding_box": {
                    "min": [0.0, 0.0, 0.0],
                    "max": [1.0, 2.0, 3.0],
                    "size": [1.0, 2.0, 3.0],
                },
                "area": 22.0,
                "volume": 6.0,
            },
            "topology": {
                "solids": 1,
                "shells": 1,
                "faces": 6,
                "wires": 6,
                "edges": 12,
                "vertices": 8,
            },
            "geometry": {
                "face_surface_types": {"plane": 6},
                "edge_curve_types": {"line": 12},
            },
            "faces": [],
            "edges": [],
        }

    exit_code = main(
        [str(input_path), "--output", str(output_path)], analyze_file=analyze_file
    )

    assert exit_code == 0
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == "0.1"
    assert report["source"] == {"path": str(input_path), "format": "step"}
    assert report["topology"]["faces"] == 6
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_cli.py -v
```

Expected: FAIL during import because `cad_features.cli` does not exist.

- [ ] **Step 3: Add CLI implementation**

Create `src/cad_features/cli.py`:

```python
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cad_features.errors import CadFeaturesError, InputFileError, OutputFileError
from cad_features.report import build_report, detect_format

AnalyzeFile = Callable[[Path, str], dict[str, Any]]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="cad-features",
        description="Extract geometry and topology statistics from STEP and IGES CAD files.",
    )
    parser.add_argument("input", help="Path to a .step, .stp, .iges, or .igs CAD file.")
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the JSON report to write. The parent directory must exist.",
    )
    return parser.parse_args(argv)


def validate_paths(input_path: Path, output_path: Path) -> None:
    if not input_path.is_file():
        raise InputFileError(f"Input file does not exist: {input_path}")
    if not output_path.parent.is_dir():
        raise OutputFileError(f"Output directory does not exist: {output_path.parent}")


def default_analyze_file(path: Path, source_format: str) -> dict[str, Any]:
    from cad_features.analyzer import analyze_shape
    from cad_features.loaders import load_shape

    shape = load_shape(path, source_format)
    return analyze_shape(shape)


def main(
    argv: list[str] | None = None,
    *,
    analyze_file: AnalyzeFile | None = None,
) -> int:
    args = parse_args(argv)
    input_path = Path(args.input)
    output_path = Path(args.output)
    analyze = analyze_file or default_analyze_file

    try:
        source_format = detect_format(input_path)
        validate_paths(input_path, output_path)
        analysis = analyze(input_path, source_format)
        report = build_report(
            source_path=str(input_path),
            source_format=source_format,
            model=analysis["model"],
            topology=analysis["topology"],
            geometry=analysis["geometry"],
            faces=analysis["faces"],
            edges=analysis["edges"],
        )
        output_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except CadFeaturesError as exc:
        print(f"cad-features: error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI tests**

Run:

```bash
pytest tests/test_cli.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Run report and CLI tests together**

Run:

```bash
pytest tests/test_report.py tests/test_cli.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

If the project has been initialized as a git repository, run:

```bash
git add src/cad_features/cli.py tests/test_cli.py
git commit -m "feat: add CAD feature CLI"
```

If the project is still not a git repository, skip the commit and note that this step was not applicable.

---

### Task 3: STEP and IGES Loading

**Files:**
- Create: `src/cad_features/loaders.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add generated STEP helper and failing loader integration test**

Append this code to `tests/test_cli.py`:

```python
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCC.Core.IFSelect import IFSelect_RetDone

from cad_features.loaders import load_shape


def write_step_box(path: Path, x: float = 10.0, y: float = 20.0, z: float = 30.0) -> None:
    shape = BRepPrimAPI_MakeBox(x, y, z).Shape()
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    status = writer.Write(str(path))
    assert status == IFSelect_RetDone


def test_load_shape_reads_generated_step_box(tmp_path):
    input_path = tmp_path / "box.step"
    write_step_box(input_path)

    shape = load_shape(input_path, "step")

    assert not shape.IsNull()
```

- [ ] **Step 2: Run loader test to verify it fails**

Run:

```bash
pytest tests/test_cli.py::test_load_shape_reads_generated_step_box -v
```

Expected: FAIL during import because `cad_features.loaders` does not exist. If the environment lacks pythonOCC, it will fail importing `OCC`; create the Conda environment before continuing:

```bash
conda env create -f environment.yml
conda activate cad-features
```

- [ ] **Step 3: Implement STEP/IGES loader**

Create `src/cad_features/loaders.py`:

```python
from pathlib import Path

from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.IGESControl import IGESControl_Reader
from OCC.Core.STEPControl import STEPControl_Reader

from cad_features.errors import CadReadError


def load_shape(path: Path, source_format: str):
    if source_format == "step":
        return _load_step(path)
    if source_format == "iges":
        return _load_iges(path)
    raise CadReadError(f"Unsupported loader format: {source_format}")


def _load_step(path: Path):
    reader = STEPControl_Reader()
    status = reader.ReadFile(str(path))
    if status != IFSelect_RetDone:
        raise CadReadError(f"Failed to read STEP file: {path}")
    reader.TransferRoots()
    shape = reader.OneShape()
    if shape.IsNull():
        raise CadReadError(f"STEP file did not contain a valid shape: {path}")
    return shape


def _load_iges(path: Path):
    reader = IGESControl_Reader()
    status = reader.ReadFile(str(path))
    if status != IFSelect_RetDone:
        raise CadReadError(f"Failed to read IGES file: {path}")
    reader.TransferRoots()
    shape = reader.OneShape()
    if shape.IsNull():
        raise CadReadError(f"IGES file did not contain a valid shape: {path}")
    return shape
```

- [ ] **Step 4: Run loader test**

Run:

```bash
pytest tests/test_cli.py::test_load_shape_reads_generated_step_box -v
```

Expected: PASS.

- [ ] **Step 5: Run existing tests**

Run:

```bash
pytest tests/test_report.py tests/test_cli.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

If the project has been initialized as a git repository, run:

```bash
git add src/cad_features/loaders.py tests/test_cli.py
git commit -m "feat: load STEP and IGES shapes"
```

If the project is still not a git repository, skip the commit and note that this step was not applicable.

---

### Task 4: OpenCascade Shape Analyzer

**Files:**
- Create: `src/cad_features/analyzer.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add failing analyzer integration test**

Append this code to `tests/test_cli.py`:

```python
import math

from cad_features.analyzer import analyze_shape


def test_analyze_shape_reports_generated_box_geometry(tmp_path):
    input_path = tmp_path / "box.step"
    write_step_box(input_path, x=10.0, y=20.0, z=30.0)
    shape = load_shape(input_path, "step")

    analysis = analyze_shape(shape)

    assert analysis["model"]["is_null"] is False
    assert analysis["topology"]["solids"] == 1
    assert analysis["topology"]["faces"] == 6
    assert analysis["topology"]["edges"] == 12
    assert analysis["geometry"]["face_surface_types"] == {"plane": 6}
    assert analysis["geometry"]["edge_curve_types"] == {"line": 12}
    assert analysis["model"]["bounding_box"]["size"] == pytest.approx(
        [10.0, 20.0, 30.0], abs=1e-6
    )
    assert analysis["model"]["volume"] == pytest.approx(6000.0, rel=1e-6)
    assert analysis["model"]["area"] == pytest.approx(2200.0, rel=1e-6)
    assert len(analysis["faces"]) == 6
    assert len(analysis["edges"]) == 12
    assert all(face["surface_type"] == "plane" for face in analysis["faces"])
    assert all(edge["curve_type"] == "line" for edge in analysis["edges"])
    assert all(math.isfinite(face["area"]) for face in analysis["faces"])
    assert all(math.isfinite(edge["length"]) for edge in analysis["edges"])
```

- [ ] **Step 2: Run analyzer test to verify it fails**

Run:

```bash
pytest tests/test_cli.py::test_analyze_shape_reports_generated_box_geometry -v
```

Expected: FAIL during import because `cad_features.analyzer` does not exist.

- [ ] **Step 3: Implement analyzer**

Create `src/cad_features/analyzer.py`:

```python
from __future__ import annotations

from collections import Counter
from typing import Any

from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GProp import GProp_GProps
from OCC.Core.GeomAbs import (
    GeomAbs_BSplineCurve,
    GeomAbs_BSplineSurface,
    GeomAbs_BezierCurve,
    GeomAbs_BezierSurface,
    GeomAbs_Circle,
    GeomAbs_Cone,
    GeomAbs_Cylinder,
    GeomAbs_Ellipse,
    GeomAbs_Hyperbola,
    GeomAbs_Line,
    GeomAbs_OffsetSurface,
    GeomAbs_OtherCurve,
    GeomAbs_OtherSurface,
    GeomAbs_Parabola,
    GeomAbs_Plane,
    GeomAbs_Sphere,
    GeomAbs_SurfaceOfExtrusion,
    GeomAbs_SurfaceOfRevolution,
    GeomAbs_Torus,
)
from OCC.Core.TopAbs import (
    TopAbs_EDGE,
    TopAbs_FACE,
    TopAbs_SHELL,
    TopAbs_SOLID,
    TopAbs_VERTEX,
    TopAbs_WIRE,
)
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import topods

SURFACE_TYPES = {
    GeomAbs_Plane: "plane",
    GeomAbs_Cylinder: "cylinder",
    GeomAbs_Cone: "cone",
    GeomAbs_Sphere: "sphere",
    GeomAbs_Torus: "torus",
    GeomAbs_BezierSurface: "bezier_surface",
    GeomAbs_BSplineSurface: "bspline_surface",
    GeomAbs_SurfaceOfRevolution: "surface_of_revolution",
    GeomAbs_SurfaceOfExtrusion: "surface_of_extrusion",
    GeomAbs_OffsetSurface: "offset_surface",
    GeomAbs_OtherSurface: "other_surface",
}

CURVE_TYPES = {
    GeomAbs_Line: "line",
    GeomAbs_Circle: "circle",
    GeomAbs_Ellipse: "ellipse",
    GeomAbs_Hyperbola: "hyperbola",
    GeomAbs_Parabola: "parabola",
    GeomAbs_BezierCurve: "bezier_curve",
    GeomAbs_BSplineCurve: "bspline_curve",
    GeomAbs_OtherCurve: "other_curve",
}

TOPOLOGY_TYPES = {
    "solids": TopAbs_SOLID,
    "shells": TopAbs_SHELL,
    "faces": TopAbs_FACE,
    "wires": TopAbs_WIRE,
    "edges": TopAbs_EDGE,
    "vertices": TopAbs_VERTEX,
}


def analyze_shape(shape) -> dict[str, Any]:
    topology = {name: _count_topology(shape, shape_type) for name, shape_type in TOPOLOGY_TYPES.items()}
    faces = _face_summaries(shape)
    edges = _edge_summaries(shape)
    face_type_counts = Counter(face["surface_type"] for face in faces)
    edge_type_counts = Counter(edge["curve_type"] for edge in edges)

    return {
        "model": {
            "is_null": bool(shape.IsNull()),
            "bounding_box": _bounding_box(shape),
            "area": _surface_area(shape),
            "volume": _volume(shape),
        },
        "topology": topology,
        "geometry": {
            "face_surface_types": dict(sorted(face_type_counts.items())),
            "edge_curve_types": dict(sorted(edge_type_counts.items())),
        },
        "faces": faces,
        "edges": edges,
    }


def _count_topology(shape, shape_type) -> int:
    count = 0
    explorer = TopExp_Explorer(shape, shape_type)
    while explorer.More():
        count += 1
        explorer.Next()
    return count


def _bounding_box(shape) -> dict[str, list[float]]:
    box = Bnd_Box()
    brepbndlib.Add(shape, box)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    return {
        "min": [float(xmin), float(ymin), float(zmin)],
        "max": [float(xmax), float(ymax), float(zmax)],
        "size": [float(xmax - xmin), float(ymax - ymin), float(zmax - zmin)],
    }


def _surface_area(shape) -> float | None:
    props = GProp_GProps()
    brepgprop.SurfaceProperties(shape, props)
    return float(props.Mass())


def _volume(shape) -> float | None:
    props = GProp_GProps()
    brepgprop.VolumeProperties(shape, props)
    return float(props.Mass())


def _face_summaries(shape) -> list[dict[str, Any]]:
    faces: list[dict[str, Any]] = []
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    index = 1
    while explorer.More():
        face = topods.Face(explorer.Current())
        faces.append(
            {
                "index": index,
                "surface_type": _surface_type(face),
                "area": _face_area(face),
            }
        )
        index += 1
        explorer.Next()
    return faces


def _edge_summaries(shape) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    explorer = TopExp_Explorer(shape, TopAbs_EDGE)
    index = 1
    while explorer.More():
        edge = topods.Edge(explorer.Current())
        edges.append(
            {
                "index": index,
                "curve_type": _curve_type(edge),
                "length": _edge_length(edge),
            }
        )
        index += 1
        explorer.Next()
    return edges


def _surface_type(face) -> str:
    try:
        surface = BRepAdaptor_Surface(face)
        return SURFACE_TYPES.get(surface.GetType(), "unknown")
    except Exception:
        return "unknown"


def _curve_type(edge) -> str:
    try:
        curve = BRepAdaptor_Curve(edge)
        return CURVE_TYPES.get(curve.GetType(), "unknown")
    except Exception:
        return "unknown"


def _face_area(face) -> float | None:
    try:
        props = GProp_GProps()
        brepgprop.SurfaceProperties(face, props)
        return float(props.Mass())
    except Exception:
        return None


def _edge_length(edge) -> float | None:
    try:
        props = GProp_GProps()
        brepgprop.LinearProperties(edge, props)
        return float(props.Mass())
    except Exception:
        return None
```

- [ ] **Step 4: Run analyzer test**

Run:

```bash
pytest tests/test_cli.py::test_analyze_shape_reports_generated_box_geometry -v
```

Expected: PASS.

If import errors occur for `brepbndlib` or `brepgprop`, inspect the installed pythonOCC API and adjust only those import/call names. Keep the public output schema unchanged.

- [ ] **Step 5: Run all tests**

Run:

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

If the project has been initialized as a git repository, run:

```bash
git add src/cad_features/analyzer.py tests/test_cli.py
git commit -m "feat: analyze CAD geometry and topology"
```

If the project is still not a git repository, skip the commit and note that this step was not applicable.

---

### Task 5: End-to-End CLI Integration

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add failing end-to-end CLI test**

Append this code to `tests/test_cli.py`:

```python

def test_cli_analyzes_generated_step_box_end_to_end(tmp_path):
    input_path = tmp_path / "box.step"
    output_path = tmp_path / "report.json"
    write_step_box(input_path, x=10.0, y=20.0, z=30.0)

    exit_code = main([str(input_path), "--output", str(output_path)])

    assert exit_code == 0
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == "0.1"
    assert report["source"] == {"path": str(input_path), "format": "step"}
    assert report["topology"]["solids"] == 1
    assert report["topology"]["faces"] == 6
    assert report["geometry"]["face_surface_types"] == {"plane": 6}
    assert report["model"]["bounding_box"]["size"] == pytest.approx(
        [10.0, 20.0, 30.0], abs=1e-6
    )
    assert report["model"]["volume"] == pytest.approx(6000.0, rel=1e-6)
```

- [ ] **Step 2: Run end-to-end test to verify it passes through real CLI path**

Run:

```bash
pytest tests/test_cli.py::test_cli_analyzes_generated_step_box_end_to_end -v
```

Expected: PASS. If it fails, fix the connection among `cli.py`, `loaders.py`, and `analyzer.py` without changing the JSON schema.

- [ ] **Step 3: Run all tests**

Run:

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 4: Run the installed console script manually**

Run:

```bash
python -m cad_features.cli --help
```

Expected: output includes `Extract geometry and topology statistics from STEP and IGES CAD files.` and mentions `--output`.

Then run:

```bash
cad-features --help
```

Expected: the same help text appears. If the shell cannot find `cad-features`, run `pip install -e .` inside the Conda environment and retry.

- [ ] **Step 5: Commit**

If the project has been initialized as a git repository, run:

```bash
git add tests/test_cli.py
git commit -m "test: cover end-to-end CAD feature CLI"
```

If the project is still not a git repository, skip the commit and note that this step was not applicable.

---

### Task 6: Final Verification and README-Free Usage Notes

**Files:**
- Modify: `docs/superpowers/specs/2026-05-18-cad-features-design.md` only if implementation reveals a necessary correction to the approved design.
- Modify: `docs/superpowers/plans/2026-05-18-cad-features.md` only if task instructions were inaccurate during execution.

- [ ] **Step 1: Verify file layout**

Run:

```bash
find . -maxdepth 4 -type f | sort
```

Expected output includes:

```text
./docs/superpowers/plans/2026-05-18-cad-features.md
./docs/superpowers/specs/2026-05-18-cad-features-design.md
./environment.yml
./pyproject.toml
./src/cad_features/__init__.py
./src/cad_features/analyzer.py
./src/cad_features/cli.py
./src/cad_features/errors.py
./src/cad_features/loaders.py
./src/cad_features/report.py
./tests/test_cli.py
./tests/test_report.py
```

- [ ] **Step 2: Run full test suite**

Run:

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 3: Verify CLI help**

Run:

```bash
python -m cad_features.cli --help
```

Expected: exit code 0 and help text including `cad-features` and `--output`.

- [ ] **Step 4: Report usage to the user**

Tell the user:

```text
Create the environment with:
conda env create -f environment.yml
conda activate cad-features

Run the CLI with:
cad-features path/to/part.step --output report.json
```

- [ ] **Step 5: Commit final adjustments**

If the project has been initialized as a git repository and Task 6 changed any files, run:

```bash
git add docs/superpowers/specs/2026-05-18-cad-features-design.md docs/superpowers/plans/2026-05-18-cad-features.md
git commit -m "docs: finalize CAD feature extraction plan"
```

If no files changed or the project is still not a git repository, skip the commit and note why.

---

## Self-Review

- Spec coverage: The plan covers STEP/IGES input, explicit `--output`, Conda dependencies, deterministic JSON schema, topology counts, bbox, area, volume, face/edge type distributions, per-entity summaries, generated STEP test fixture, and user-facing CLI errors.
- Placeholder scan: The plan contains no TBD/TODO/fill-later placeholders. Each code-writing step includes complete file contents or exact appended test code.
- Type consistency: The CLI calls `load_shape(path, source_format)` and `analyze_shape(shape)`, then passes `model`, `topology`, `geometry`, `faces`, and `edges` into `build_report`. Test expectations use the same JSON keys defined in the spec.