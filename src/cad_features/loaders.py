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
