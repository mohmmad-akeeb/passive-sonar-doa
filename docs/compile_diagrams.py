#!/usr/bin/env python3
"""
compile_diagrams.py
===================
Compiles every main.tex found under docs/image_latex_code/IMG_GEN_*/
and converts the resulting PDF to a PNG in docs/images/.

Image naming convention
-----------------------
Folder name  : IMG_GEN_01_Active_vs_Passive_SONAR
Output image : IMG_GEN_01_Active_vs_Passive_SONAR.png

Usage
-----
    # From the project root:
    python docs/compile_diagrams.py

    # Compile only specific diagrams:
    python docs/compile_diagrams.py --only IMG_GEN_01 IMG_GEN_07

    # Override output DPI (default 300):
    python docs/compile_diagrams.py --dpi 150

    # Use ImageMagick convert instead of pdftoppm:
    python docs/compile_diagrams.py --converter imagemagick

Requirements
------------
    pdflatex    — TeX Live / MiKTeX
    pdftoppm    — part of poppler-utils  (default converter)
    convert     — ImageMagick            (alternative converter)

    Install on Ubuntu/Debian:
        sudo apt install texlive-full poppler-utils imagemagick
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# ── Paths (resolved relative to this script's location) ──────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent          # docs/
LATEX_ROOT   = SCRIPT_DIR / "image_latex_code"
IMAGES_DIR   = SCRIPT_DIR / "images"

# ── Colour helpers for terminal output ───────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"

def info(msg: str)    -> None: print(f"{CYAN}[INFO]{RESET}  {msg}")
def ok(msg: str)      -> None: print(f"{GREEN}[ OK ]{RESET}  {msg}")
def warn(msg: str)    -> None: print(f"{YELLOW}[WARN]{RESET}  {msg}")
def error(msg: str)   -> None: print(f"{RED}[FAIL]{RESET}  {msg}")


# ── Tool detection ────────────────────────────────────────────────────────────
def require_tool(name: str) -> str:
    """Return the full path to *name* or abort with a helpful message."""
    path = shutil.which(name)
    if path is None:
        error(f"Required tool '{name}' not found on PATH.")
        if name == "pdflatex":
            print("  Install: sudo apt install texlive-full")
        elif name == "pdftoppm":
            print("  Install: sudo apt install poppler-utils")
        elif name == "convert":
            print("  Install: sudo apt install imagemagick")
        sys.exit(1)
    return path


# ── pdflatex compilation ──────────────────────────────────────────────────────
def compile_latex(folder: Path, pdflatex: str) -> bool:
    """
    Run pdflatex twice (for TikZ cross-references) inside *folder*.
    Returns True on success, False on failure.
    """
    cmd = [
        pdflatex,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "main.tex",
    ]
    for run in range(1, 3):          # two passes
        result = subprocess.run(
            cmd,
            cwd=folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        # pdflatex output may contain non-UTF-8 bytes; decode safely
        output = result.stdout.decode("utf-8", errors="replace")
        if result.returncode != 0:
            error(f"pdflatex pass {run} failed in {folder.name}")
            # Print last 30 lines of log for quick diagnosis
            for line in output.splitlines()[-30:]:
                print(f"    {line}")
            return False
    return True


# ── PDF → PNG conversion ──────────────────────────────────────────────────────
def pdf_to_png_pdftoppm(pdf_path: Path, out_png: Path, dpi: int) -> bool:
    """
    Use pdftoppm (poppler) to convert a single-page PDF to PNG.
    pdftoppm adds a page-number suffix; we rename it afterwards.
    """
    # pdftoppm writes <stem>-1.png (or <stem>-01.png for multi-page)
    stem    = out_png.stem          # e.g. IMG_GEN_01_Active_vs_Passive_SONAR
    out_dir = out_png.parent
    prefix  = out_dir / stem        # pdftoppm output prefix (no extension)

    cmd = [
        "pdftoppm",
        "-r", str(dpi),
        "-png",
        "-singlefile",              # avoids the page-number suffix
        str(pdf_path),
        str(prefix),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = result.stdout.decode("utf-8", errors="replace")
    if result.returncode != 0:
        error(f"pdftoppm failed: {output.strip()}")
        return False

    # -singlefile writes exactly <prefix>.png
    produced = out_dir / f"{stem}.png"
    if not produced.exists():
        error(f"Expected output not found: {produced}")
        return False
    return True


def pdf_to_png_imagemagick(pdf_path: Path, out_png: Path, dpi: int) -> bool:
    """Use ImageMagick convert to rasterise the PDF."""
    cmd = [
        "convert",
        "-density", str(dpi),
        "-quality", "95",
        "-flatten",
        str(pdf_path),
        str(out_png),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = result.stdout.decode("utf-8", errors="replace")
    if result.returncode != 0:
        error(f"ImageMagick convert failed: {output.strip()}")
        return False
    if not out_png.exists():
        error(f"Expected output not found: {out_png}")
        return False
    return True


# ── Discover diagram folders ──────────────────────────────────────────────────
def discover_folders(only: list[str] | None) -> list[Path]:
    """
    Return sorted list of IMG_GEN_* directories that contain main.tex.
    If *only* is given, restrict to folders whose name starts with any
    of the provided prefixes (e.g. ['IMG_GEN_01', 'IMG_GEN_07']).
    """
    folders = sorted(
        d for d in LATEX_ROOT.iterdir()
        if d.is_dir()
        and d.name.startswith("IMG_GEN_")
        and (d / "main.tex").exists()
    )
    if only:
        folders = [
            f for f in folders
            if any(f.name.startswith(prefix) for prefix in only)
        ]
    return folders


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile LaTeX diagrams and convert to PNG."
    )
    parser.add_argument(
        "--only", nargs="+", metavar="PREFIX",
        help="Restrict to folders matching these prefixes, e.g. IMG_GEN_01 IMG_GEN_03"
    )
    parser.add_argument(
        "--dpi", type=int, default=300,
        help="Output resolution in DPI (default: 300)"
    )
    parser.add_argument(
        "--converter", choices=["pdftoppm", "imagemagick"], default="pdftoppm",
        help="PDF-to-PNG converter to use (default: pdftoppm)"
    )
    parser.add_argument(
        "--skip-compile", action="store_true",
        help="Skip pdflatex and only (re-)convert existing PDFs"
    )
    args = parser.parse_args()

    # ── Check tools ──────────────────────────────────────────────────────────
    pdflatex = None if args.skip_compile else require_tool("pdflatex")
    if args.converter == "pdftoppm":
        require_tool("pdftoppm")
    else:
        require_tool("convert")

    # ── Ensure output directory exists ───────────────────────────────────────
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # ── Discover folders ─────────────────────────────────────────────────────
    folders = discover_folders(args.only)
    if not folders:
        warn("No IMG_GEN_* folders with main.tex found.")
        sys.exit(0)

    info(f"Found {len(folders)} diagram(s) to process.")
    info(f"Output directory: {IMAGES_DIR}")
    print()

    results: dict[str, str] = {}   # folder_name → "ok" | "latex_fail" | "png_fail"

    for folder in folders:
        name    = folder.name                      # IMG_GEN_XX_Some_Name
        pdf     = folder / "main.pdf"
        out_png = IMAGES_DIR / f"{name}.png"

        print(f"{'─'*60}")
        info(f"Processing: {name}")

        # ── Step 1: compile ───────────────────────────────────────────────
        if not args.skip_compile:
            info("  Compiling with pdflatex (2 passes)…")
            if not compile_latex(folder, pdflatex):
                results[name] = "latex_fail"
                continue
            ok("  Compilation successful.")
        else:
            if not pdf.exists():
                warn(f"  --skip-compile set but {pdf} not found, skipping.")
                results[name] = "latex_fail"
                continue
            info("  Skipping compilation (--skip-compile).")

        # ── Step 2: convert ───────────────────────────────────────────────
        info(f"  Converting PDF → PNG at {args.dpi} DPI…")
        if args.converter == "pdftoppm":
            success = pdf_to_png_pdftoppm(pdf, out_png, args.dpi)
        else:
            success = pdf_to_png_imagemagick(pdf, out_png, args.dpi)

        if not success:
            results[name] = "png_fail"
            continue

        ok(f"  Saved: {out_png.relative_to(SCRIPT_DIR.parent)}")
        results[name] = "ok"

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print("SUMMARY")
    print(f"{'═'*60}")
    succeeded = [n for n, s in results.items() if s == "ok"]
    failed    = [n for n, s in results.items() if s != "ok"]

    for name in succeeded:
        print(f"  {GREEN}✓{RESET}  {name}")
    for name in failed:
        status = results[name]
        label  = "LaTeX error" if status == "latex_fail" else "PNG conversion error"
        print(f"  {RED}✗{RESET}  {name}  ({label})")

    print(f"\n  Succeeded: {len(succeeded)}/{len(results)}")
    if failed:
        print(f"  Failed:    {len(failed)}/{len(results)}")
        sys.exit(1)
    else:
        ok("All diagrams compiled and converted successfully.")


if __name__ == "__main__":
    main()
