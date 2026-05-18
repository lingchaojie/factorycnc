from __future__ import annotations

from collections import Counter
from typing import Any

from OCC.Core.Bnd import Bnd_Box
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
from OCC.Core.TopExp import TopExp_Explorer, topexp
from OCC.Core.TopTools import TopTools_IndexedMapOfShape
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
    topology = {
        name: _count_topology(shape, shape_type)
        for name, shape_type in TOPOLOGY_TYPES.items()
    }
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
    shape_map = TopTools_IndexedMapOfShape()
    topexp.MapShapes(shape, shape_type, shape_map)
    return shape_map.Size()


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
    edge_map = TopTools_IndexedMapOfShape()
    topexp.MapShapes(shape, TopAbs_EDGE, edge_map)
    for index in range(1, edge_map.Size() + 1):
        edge = topods.Edge(edge_map.FindKey(index))
        edges.append(
            {
                "index": index,
                "curve_type": _curve_type(edge),
                "length": _edge_length(edge),
            }
        )
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
