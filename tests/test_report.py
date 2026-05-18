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
