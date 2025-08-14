import argparse
import sys
import shutil
import platform
import subprocess
from pathlib import Path


def _convert_with_inkscape(svg_path: Path, png_path: Path, width: int | None, height: int | None, inkscape_path: Path | None) -> None:
    exe = None
    candidates = []
    if inkscape_path:
        candidates.append(Path(inkscape_path))
    # Common Windows install paths
    candidates.extend([
        Path(r"C:\Program Files\Inkscape\bin\inkscape.exe"),
        Path(r"C:\Program Files\Inkscape\inkscape.com"),
        Path(r"C:\Program Files (x86)\Inkscape\bin\inkscape.exe"),
    ])
    # PATH lookup
    which = shutil.which("inkscape")
    if which:
        candidates.insert(0, Path(which))

    for c in candidates:
        if c and c.exists():
            exe = c
            break

    if not exe:
        raise RuntimeError("Inkscape not found. Install Inkscape or pass --inkscape-path.")

    cmd = [str(exe), str(svg_path), "--export-type=png", f"--export-filename={png_path}"]
    if width:
        cmd += [f"--export-width={width}"]
    if height:
        cmd += [f"--export-height={height}"]
    subprocess.run(cmd, check=True)


def _convert_with_cairosvg(svg_path: Path, png_path: Path, width: int | None, height: int | None) -> None:
    try:
        from cairosvg import svg2png  # lazy import to avoid requiring cairo on Windows unless chosen
    except Exception as e:
        raise RuntimeError("CairoSVG not available. Install with: pip install cairosvg") from e
    svg2png(url=str(svg_path), write_to=str(png_path), output_width=width, output_height=height)


def convert_all_svgs(input_dir: Path, output_dir: Path, width: int | None, height: int | None, *, engine: str = "auto", inkscape_path: Path | None = None) -> None:
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Input directory not found: {input_dir}", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    svgs = sorted(input_dir.glob("*.svg"))
    if not svgs:
        print(f"No SVG files found in {input_dir}")
        return

    # Decide engine
    chosen = engine.lower()
    if chosen == "auto":
        if platform.system().lower() == "windows":
            chosen = "inkscape"
        else:
            chosen = "cairosvg"

    for svg_path in svgs:
        png_path = output_dir / (svg_path.stem + ".png")
        try:
            if chosen == "inkscape":
                _convert_with_inkscape(svg_path, png_path, width, height, inkscape_path)
            elif chosen == "cairosvg":
                _convert_with_cairosvg(svg_path, png_path, width, height)
            else:
                raise RuntimeError(f"Unknown engine: {engine}")
            print(f"Converted: {svg_path.name} -> {png_path}")
        except Exception as exc:
            print(f"Failed: {svg_path} ({exc})", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert SVGs in a folder to PNGs.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("staticfiles") / "nutrition_images",
        help="Directory containing .svg files (default: staticfiles/nutrition_images)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("staticfiles") / "nutrition_images_png",
        help="Directory to write .png files (default: staticfiles/nutrition_images_png)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="Output PNG width in pixels (optional). If omitted, use SVG's intrinsic/auto.",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
        help="Output PNG height in pixels (optional). If omitted, use SVG's intrinsic/auto.",
    )
    parser.add_argument(
        "--engine",
        choices=["auto", "inkscape", "cairosvg"],
        default="auto",
        help="Rendering engine: auto (default), inkscape, or cairosvg.",
    )
    parser.add_argument(
        "--inkscape-path",
        type=Path,
        default=None,
        help="Path to inkscape executable (if not on PATH).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    convert_all_svgs(
        args.input_dir,
        args.output_dir,
        args.width,
        args.height,
        engine=args.engine,
        inkscape_path=args.inkscape_path,
    )


if __name__ == "__main__":
    main()


