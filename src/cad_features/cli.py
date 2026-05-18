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
    if output_path.is_dir():
        raise OutputFileError(f"Output path is a directory: {output_path}")
    if input_path.resolve() == output_path.resolve(strict=False):
        raise OutputFileError("Output path must be different from input file")


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
        try:
            output_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise OutputFileError(f"Failed to write output file: {output_path}") from exc
    except CadFeaturesError as exc:
        print(f"cad-features: error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
