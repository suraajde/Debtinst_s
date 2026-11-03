"""
tests/test_packaging.py - Packaging, Portable Distribution, Launcher & Entry Point Test Suite.

Sprint 5: Tests main.py entrypoint, runtime path resolution (standard & frozen),
launcher scripts, sample Bhavcopy import, ZIP archive creation, and distribution verification.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

# Add project root to sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from build_exe import build_portable_distribution, verify_distribution
from main import resolve_runtime_paths, run_smoke_test
from src.data_engine import DebtMarketDataEngine
from src.embedded_seed import init_embedded_db


class TestPackagingAndLaunchers(unittest.TestCase):
    """Test suite for packaging, cross-platform launchers, and distribution archive."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = Path(self.temp_dir) / "test_debt.db"
        init_embedded_db(self.test_db)
        self.dist_dir = _project_root / "dist_portable"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_main_resolve_runtime_paths_standard(self) -> None:
        """Verify runtime path resolution in standard (source) environment."""
        paths = resolve_runtime_paths()
        self.assertIn("is_frozen", paths)
        self.assertIn("bundle_root", paths)
        self.assertIn("exec_root", paths)
        self.assertIn("data_dir", paths)
        self.assertIn("db_path", paths)
        self.assertIn("dist_portable_dir", paths)

        self.assertFalse(paths["is_frozen"])
        self.assertTrue(paths["bundle_root"].exists())
        self.assertTrue((paths["bundle_root"] / "src").exists())
        self.assertTrue((paths["bundle_root"] / "main.py").exists())
        self.assertTrue(paths["data_dir"].exists())

    def test_main_resolve_runtime_paths_frozen_simulation(self) -> None:
        """Simulate PyInstaller frozen environment (sys.frozen & sys._MEIPASS)."""
        temp_bundle = tempfile.mkdtemp()
        original_frozen = getattr(sys, "frozen", None)
        original_meipass = getattr(sys, "_MEIPASS", None)

        try:
            sys.frozen = True  # type: ignore[attr-defined]
            sys._MEIPASS = temp_bundle  # type: ignore[attr-defined]

            paths = resolve_runtime_paths()
            self.assertTrue(paths["is_frozen"])
            self.assertEqual(paths["bundle_root"], Path(temp_bundle).resolve())
            self.assertTrue(paths["data_dir"].exists())
        finally:
            if original_frozen is None:
                if hasattr(sys, "frozen"):
                    delattr(sys, "frozen")
            else:
                sys.frozen = original_frozen

            if original_meipass is None:
                if hasattr(sys, "_MEIPASS"):
                    delattr(sys, "_MEIPASS")
            else:
                sys._MEIPASS = original_meipass

            shutil.rmtree(temp_bundle, ignore_errors=True)

    def test_main_smoke_test_function(self) -> None:
        """Verify the internal self-check function run_smoke_test() passes cleanly."""
        # Run self-check against the temporary isolated database
        try:
            run_smoke_test(db_path=self.test_db)
        except Exception as e:
            self.fail(f"run_smoke_test failed unexpectedly: {e}")

    def test_main_cli_smoke_test_subprocess(self) -> None:
        """Execute 'python main.py --smoke-test' via subprocess to test CLI interface."""
        cmd = [sys.executable, str(_project_root / "main.py"), "--smoke-test"]
        proc = subprocess.run(cmd, cwd=str(_project_root), capture_output=True, text=True)
        self.assertEqual(
            proc.returncode,
            0,
            f"main.py --smoke-test failed with code {proc.returncode}.\nOutput: {proc.stdout}\nError: {proc.stderr}",
        )
        self.assertIn("Smoke test completed", proc.stdout)
        self.assertIn("[OK]", proc.stdout)

    def test_main_cli_export_standalone_subprocess(self) -> None:
        """Execute 'python main.py --export-standalone' via subprocess."""
        cmd = [sys.executable, str(_project_root / "main.py"), "--export-standalone"]
        proc = subprocess.run(cmd, cwd=str(_project_root), capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("[OK] Standalone HTML exported", proc.stdout)

        html_file = self.dist_dir / "Debtinst_s_Standalone.html"
        self.assertTrue(html_file.exists())
        self.assertGreater(html_file.stat().st_size, 30000)

    def test_launcher_scripts_exist_and_valid(self) -> None:
        """Verify both Windows BAT and Mac/Linux Shell launchers exist and contain fallback logic."""
        bat_file = self.dist_dir / "Launch_Debtinst_Windows.bat"
        sh_file = self.dist_dir / "Launch_Debtinst_Mac_Linux.sh"

        self.assertTrue(bat_file.exists(), "Launch_Debtinst_Windows.bat missing")
        self.assertTrue(sh_file.exists(), "Launch_Debtinst_Mac_Linux.sh missing")

        bat_content = bat_file.read_text(encoding="utf-8")
        self.assertIn("Debtinst_s_Standalone.html", bat_content)
        self.assertIn("main.py", bat_content)
        self.assertIn("msedge", bat_content)

        sh_content = sh_file.read_text(encoding="utf-8")
        self.assertIn("Debtinst_s_Standalone.html", sh_content)
        self.assertIn("python3", sh_content)
        self.assertIn("xdg-open", sh_content)

    def test_sample_bhavcopy_import(self) -> None:
        """Validate sample_bhavcopy_import.csv exists and can be imported cleanly into DB."""
        csv_file = self.dist_dir / "sample_bhavcopy_import.csv"
        self.assertTrue(csv_file.exists(), "sample_bhavcopy_import.csv missing")

        engine = DebtMarketDataEngine(db_path=self.test_db)
        imported_count = engine.import_bhavcopy_csv(csv_source=csv_file)

        self.assertEqual(imported_count, 10)

        # Confirm imported securities prices were updated in the database
        snapshot = engine.get_market_snapshot(allow_network=False)
        sec_map = {s["symbol"]: s for s in snapshot["securities"]}
        self.assertIn("718GS2033", sec_map)
        self.assertIn("HDFC27", sec_map)
        self.assertEqual(sec_map["HDFC27"]["current_price"], 1018.50)
        self.assertEqual(sec_map["718GS2033"]["current_price"], 100.25)

    def test_quickstart_documentation(self) -> None:
        """Verify dist_portable/QUICKSTART.txt contains all execution options."""
        txt_file = self.dist_dir / "QUICKSTART.txt"
        self.assertTrue(txt_file.exists(), "QUICKSTART.txt missing")

        content = txt_file.read_text(encoding="utf-8").upper()
        self.assertGreater(len(content), 200)
        self.assertIn("OPTION 1", content)
        self.assertIn("OPTION 2", content)
        self.assertIn("OPTION 3", content)
        self.assertIn("WINDOWS", content)
        self.assertIn("MAC", content)

    def test_build_portable_distribution_no_exe(self) -> None:
        """Verify build_portable_distribution() without PyInstaller creates complete bundle."""
        report = build_portable_distribution(compile_exe=False)
        self.assertIn("zip_path", report)
        self.assertIn("zip_size_kb", report)
        self.assertIn("files_packaged", report)
        self.assertGreater(report["zip_size_kb"], 20.0)

        packaged_names = report["files_packaged"]
        self.assertIn("Debtinst_s_Standalone.html", packaged_names)
        self.assertIn("Launch_Debtinst_Windows.bat", packaged_names)
        self.assertIn("Launch_Debtinst_Mac_Linux.sh", packaged_names)
        self.assertIn("sample_bhavcopy_import.csv", packaged_names)
        self.assertIn("QUICKSTART.txt", packaged_names)
        self.assertIn("main.py", packaged_names)

    def test_distribution_zip_integrity_and_contents(self) -> None:
        """Ensure distribution ZIP archive is valid, uncorrupted, and contains all required files."""
        zip_path = self.dist_dir / "Debtinst_s_Portable_v1.0.0.zip"
        self.assertTrue(zip_path.exists(), f"Distribution zip missing: {zip_path}")

        with zipfile.ZipFile(zip_path, "r") as z:
            corrupt = z.testzip()
            self.assertIsNone(corrupt, f"Corrupted file found in zip: {corrupt}")

            namelist = z.namelist()
            self.assertIn("Debtinst_s_Standalone.html", namelist)
            self.assertIn("Launch_Debtinst_Windows.bat", namelist)
            self.assertIn("Launch_Debtinst_Mac_Linux.sh", namelist)
            self.assertIn("sample_bhavcopy_import.csv", namelist)
            self.assertIn("QUICKSTART.txt", namelist)
            self.assertIn("main.py", namelist)
            # Verify source tree is packaged for python runners
            self.assertTrue(any(f.startswith("src/") for f in namelist))

    def test_verify_distribution_function(self) -> None:
        """Verify the distribution verifier function passes."""
        self.assertTrue(verify_distribution())


if __name__ == "__main__":
    unittest.main()
