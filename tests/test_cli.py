import json
import math
from pathlib import Path

import pytest
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Writer

from cad_features.analyzer import analyze_shape
from cad_features.cli import main
from cad_features.loaders import load_shape


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


def test_cli_rejects_output_path_that_is_directory(tmp_path, capsys):
    input_path = tmp_path / "part.step"
    input_path.write_text("ISO-10303-21;\nEND-ISO-10303-21;\n", encoding="utf-8")

    def analyze_file(path: Path, source_format: str):
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

    exit_code = main([str(input_path), "--output", str(tmp_path)], analyze_file=analyze_file)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Output path is a directory" in captured.err
    assert tmp_path.is_dir()


def test_cli_rejects_output_path_matching_input_file(tmp_path, capsys):
    input_path = tmp_path / "part.step"
    original_content = "ISO-10303-21;\nEND-ISO-10303-21;\n"
    input_path.write_text(original_content, encoding="utf-8")

    def analyze_file(path: Path, source_format: str):
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
        [str(input_path), "--output", str(input_path)], analyze_file=analyze_file
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Output path must be different from input file" in captured.err
    assert input_path.read_text(encoding="utf-8") == original_content


def test_cli_rejects_hard_link_output_path_matching_input_file(tmp_path, capsys):
    input_path = tmp_path / "part.step"
    output_path = tmp_path / "report.step"
    original_content = "ISO-10303-21;\nEND-ISO-10303-21;\n"
    input_path.write_text(original_content, encoding="utf-8")
    output_path.hardlink_to(input_path)

    def analyze_file(path: Path, source_format: str):
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

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Output path must be different from input file" in captured.err
    assert input_path.read_text(encoding="utf-8") == original_content



def test_cli_reports_output_write_failure(tmp_path, capsys, monkeypatch):
    input_path = tmp_path / "part.step"
    input_path.write_text("ISO-10303-21;\nEND-ISO-10303-21;\n", encoding="utf-8")
    output_path = tmp_path / "report.json"

    def analyze_file(path: Path, source_format: str):
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

    def fail_write_text(self, data, *, encoding=None):
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "write_text", fail_write_text)

    exit_code = main([str(input_path), "--output", str(output_path)], analyze_file=analyze_file)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Failed to write output file" in captured.err



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
