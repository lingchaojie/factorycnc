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
