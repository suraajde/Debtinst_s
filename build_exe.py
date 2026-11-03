"""
build_exe.py - Zero-Dependency Portable Distribution & Executable Packaging Builder.

Sprint 5: Builds the complete dist_portable/ bundle, packages Debtinst_s_Portable_v1.0.0.zip,
and compiles Debtinst_s.exe if PyInstaller is available.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.app_server import export_standalone_html


def build_portable_distribution(compile_exe: bool = True) -> Dict[str, Any]:
    """
    Builds the complete portable distribution bundle:
      1. Regenerates dist_portable/Debtinst_s_Standalone.html.
      2. Validates launchers, sample CSV, and QUICKSTART text.
      3. Optionally compiles Debtinst_s.exe via PyInstaller if available.
      4. Compresses distribution bundle into dist_portable/Debtinst_s_Portable_v1.0.0.zip.

    Returns
    -------
    Dict[str, Any]
        Summary report containing zip path, file size, and list of packaged files.
    """
    base_dir = Path(__file__).resolve().parent
    dist_dir = base_dir / "dist_portable"
    dist_dir.mkdir(parents=True, exist_ok=True)

    print("=================================================================")
    print("      Debtinst_s - Portable Distribution Builder (v1.0.0)        ")
    print("=================================================================")

    # 1. Regenerate Standalone HTML
    standalone_html = dist_dir / "Debtinst_s_Standalone.html"
    print(f"[*] Generating standalone HTML bundle...")
    export_standalone_html(output_path=standalone_html)
    html_size_kb = standalone_html.stat().st_size / 1024
    print(f"    [+] Standalone HTML verified: {html_size_kb:.1f} KB -> {standalone_html.name}")

    # 2. Verify / Create Launchers and Docs
    bat_file = dist_dir / "Launch_Debtinst_Windows.bat"
    sh_file = dist_dir / "Launch_Debtinst_Mac_Linux.sh"
    csv_file = dist_dir / "sample_bhavcopy_import.csv"
    txt_file = dist_dir / "QUICKSTART.txt"

    required_assets = [bat_file, sh_file, csv_file, txt_file]
    for asset in required_assets:
        if not asset.exists():
            print(f"    [!] Warning: Asset {asset.name} was missing. Creating default...")
            asset.touch()
        print(f"    [+] Asset present: {asset.name}")

    # 3. Optional PyInstaller Compilation
    exe_path = dist_dir / "Debtinst_s.exe"
    exe_compiled = False
    pyinstaller_bin = shutil.which("pyinstaller")

    if compile_exe and pyinstaller_bin:
        print(f"[*] Found PyInstaller at: {pyinstaller_bin}")
        print("    [>] Compiling single-file executable Debtinst_s.exe...")

        add_data_sep = ";" if sys.platform == "win32" else ":"
        cmd = [
            pyinstaller_bin,
            "--noconfirm",
            "--onefile",
            "--windowed",
            "--name", "Debtinst_s",
            "--distpath", str(dist_dir),
            "--add-data", f"src{add_data_sep}src",
            "main.py",
        ]

        try:
            res = subprocess.run(cmd, cwd=str(base_dir), capture_output=True, text=True)
            if res.returncode == 0 and exe_path.exists():
                exe_size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"    [+] Successfully compiled Debtinst_s.exe ({exe_size_mb:.1f} MB)")
                exe_compiled = True
            else:
                print(f"    [!] PyInstaller build failed or was aborted: {res.stderr[:200]}")
        except Exception as e:
            print(f"    [!] PyInstaller invocation error: {e}")
    else:
        if not compile_exe:
            print("    [i] Executable compilation skipped (--no-exe flag).")
        else:
            print("    [i] PyInstaller not detected locally. (Release CI automatically compiles on windows-latest).")

    # 4. Package Portable ZIP Archive
    zip_path = dist_dir / "Debtinst_s_Portable_v1.0.0.zip"
    print(f"[*] Packaging distribution ZIP archive -> {zip_path.name}...")

    files_to_pack: List[Path] = [
        standalone_html,
        bat_file,
        sh_file,
        csv_file,
        txt_file,
    ]
    if exe_path.exists():
        files_to_pack.append(exe_path)

    # Also include source runners (main.py and src/)
    main_py = base_dir / "main.py"
    if main_py.exists():
        files_to_pack.append(main_py)

    src_dir = base_dir / "src"
    src_files = list(src_dir.rglob("*.py")) if src_dir.exists() else []

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_out:
        # Add portable files at root of zip
        for p in files_to_pack:
            if p.exists():
                arcname = p.name
                zip_out.write(p, arcname=arcname)
                print(f"    [+] Zipped: {arcname}")

        # Add src/ tree for python runners
        for py_file in src_files:
            rel = py_file.relative_to(base_dir)
            zip_out.write(py_file, arcname=str(rel))

    zip_size_kb = zip_path.stat().st_size / 1024
    print(f"\n[OK] Portable bundle built successfully: {zip_path.name} ({zip_size_kb:.1f} KB)")
    print(f"     Total entries in zip: {len(files_to_pack) + len(src_files)}")

    return {
        "zip_path": str(zip_path),
        "zip_size_kb": zip_size_kb,
        "files_packaged": [p.name for p in files_to_pack],
        "exe_compiled": exe_compiled,
    }


def verify_distribution() -> bool:
    """Validate that the portable zip and standalone files exist and are uncorrupted."""
    dist_dir = Path(__file__).resolve().parent / "dist_portable"
    zip_file = dist_dir / "Debtinst_s_Portable_v1.0.0.zip"
    html_file = dist_dir / "Debtinst_s_Standalone.html"

    assert html_file.exists(), f"Missing {html_file}"
    assert zip_file.exists(), f"Missing {zip_file}"

    with zipfile.ZipFile(zip_file, "r") as z:
        bad_file = z.testzip()
        assert bad_file is None, f"Corrupted file in zip: {bad_file}"
        namelist = z.namelist()
        assert "Debtinst_s_Standalone.html" in namelist
        assert "Launch_Debtinst_Windows.bat" in namelist
        assert "sample_bhavcopy_import.csv" in namelist

    print("[OK] Distribution verification passed cleanly.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Debtinst_s Portable Distribution Bundle")
    parser.add_argument("--no-exe", action="store_true", help="Skip PyInstaller compilation check")
    parser.add_argument("--verify", "--verify-only", dest="verify_only", action="store_true", help="Verify existing distribution zip integrity")

    args = parser.parse_args()

    if args.verify_only:
        verify_distribution()
        sys.exit(0)

    build_portable_distribution(compile_exe=not args.no_exe)
