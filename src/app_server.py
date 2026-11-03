"""
src/app_server.py - Zero-Dependency Local API Server, Desktop Launcher & Standalone Builder.

Part of Sprint 4 for Debtinst_s.
Provides:
  1. Local HTTP API server (Zero 3P dependencies, pure http.server & socketserver).
  2. Endpoints for live market sync, multi-criteria screening, CSV ingestion, & ladder simulation.
  3. Single-file standalone HTML export engine (dist_portable/Debtinst_s_Standalone.html).
  4. Chromeless desktop application launcher (Edge/Chrome --app mode).
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import socketserver
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Ensure project root is in sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.data_engine import DebtMarketDataEngine
from src.embedded_seed import get_default_db_path
from src.quant_engine import BondQuantEngine
from src.ui_template import render_dashboard_html


class DebtDashboardHTTPHandler(http.server.BaseHTTPRequestHandler):
    """
    HTTP request handler serving the interactive UI and JSON API endpoints.
    """

    server: DebtDashboardTCPServer

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default HTTP request logging to keep console clean."""
        pass

    def _send_json_response(self, data: Any, status: int = 200) -> None:
        """Helper to send JSON response with CORS and UTF-8 encoding."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_html_response(self, html_content: str, status: int = 200) -> None:
        """Helper to send HTML response."""
        body = html_content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        """Handle pre-flight CORS requests."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        """Handle GET requests for UI and snapshot API."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            snapshot = self.server.get_full_quant_snapshot()
            html = render_dashboard_html(json.dumps(snapshot), standalone_mode=False)
            self._send_html_response(html)
        elif path == "/api/snapshot":
            snapshot = self.server.get_full_quant_snapshot()
            self._send_json_response(snapshot)
        else:
            self.send_error(404, "Endpoint not found")

    def do_POST(self) -> None:
        """Handle POST requests for screening, ladder, sync, and CSV import."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(body_bytes.decode("utf-8", errors="replace"))
        except Exception:
            payload = {}

        if path == "/api/screen":
            # Multi-criteria screener
            results = self.server.quant_engine.screen_securities(
                categories=payload.get("categories"),
                seniority_tiers=payload.get("seniority_tiers"),
                min_rating=payload.get("min_rating", "AA"),
                min_effective_ytm=payload.get("min_effective_ytm"),
                max_modified_duration=payload.get("max_modified_duration"),
                min_asset_cover=payload.get("min_asset_cover"),
                exclude_yield_traps=payload.get("exclude_yield_traps", True),
                sort_by=payload.get("sort_by", "rays_score"),
                ascending=payload.get("ascending", False),
            )
            self._send_json_response({"securities": results, "count": len(results)})

        elif path == "/api/ladder":
            # Portfolio cash-flow ladder
            total_cap = float(payload.get("total_capital_inr", 500000.0))
            mode = payload.get("allocation_mode", "rays_weighted")
            filter_isins = set(payload.get("isins", []))

            all_screened = self.server.quant_engine.screen_securities()
            if filter_isins:
                selected = [s for s in all_screened if s["isin"] in filter_isins]
            else:
                selected = all_screened[:8]

            ladder = self.server.quant_engine.generate_cashflow_ladder(
                securities=selected,
                total_capital_inr=total_cap,
                allocation_mode=mode,
            )
            self._send_json_response(ladder)

        elif path == "/api/sync":
            # Live Free API sync
            self.server.data_engine.sync_database(allow_network=True)
            snapshot = self.server.get_full_quant_snapshot()
            self._send_json_response(snapshot)

        elif path == "/api/import-csv":
            # Bhavcopy CSV import
            csv_text = payload.get("csv_content", "")
            records_updated = self.server.data_engine.import_bhavcopy_csv(csv_text)
            snapshot = self.server.get_full_quant_snapshot()
            snapshot["records_imported"] = records_updated
            self._send_json_response(snapshot)

        else:
            self.send_error(404, "Unknown API route")


class DebtDashboardTCPServer(socketserver.ThreadingTCPServer):
    """Threading TCP Server with attached data and quant engines."""
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[http.server.BaseHTTPRequestHandler],
        db_path: Optional[Union[str, Path]] = None,
    ):
        super().__init__(server_address, RequestHandlerClass)
        self.db_path = Path(db_path) if db_path else get_default_db_path()
        self.data_engine = DebtMarketDataEngine(db_path=self.db_path)
        self.quant_engine = BondQuantEngine(db_path=self.db_path)

    def get_full_quant_snapshot(self) -> Dict[str, Any]:
        """Fetch market snapshot and enrich all securities through quant engine."""
        base_snapshot = self.data_engine.get_market_snapshot(allow_network=False)
        enriched = self.quant_engine.screen_securities(
            securities=base_snapshot["securities"],
            min_rating=None,
            exclude_yield_traps=False,  # Deliver all securities; client toggles guardrail
        )
        curve = self.quant_engine.build_sovereign_curve(enriched)

        return {
            "securities": enriched,
            "gold_24k_inr": base_snapshot["gold_24k_inr"],
            "data_source": base_snapshot["data_source"],
            "sovereign_curve": curve,
            "summary": base_snapshot["summary"],
            "last_sync_utc": base_snapshot["last_sync_utc"],
        }


class DebtDashboardServer:
    """Manager for starting, querying, and stopping the local dashboard server."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        db_path: Optional[Union[str, Path]] = None,
    ):
        self.host = host
        self.requested_port = port
        self.db_path = db_path
        self._server: Optional[DebtDashboardTCPServer] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def port(self) -> int:
        """Return actual port bound (useful when initialized with port=0)."""
        if self._server:
            return self._server.server_address[1]
        return self.requested_port

    @property
    def url(self) -> str:
        """Return base HTTP URL for the running server."""
        return f"http://{self.host}:{self.port}"

    def start(self) -> None:
        """Start the HTTP server on a daemon background thread."""
        self._server = DebtDashboardTCPServer(
            (self.host, self.requested_port),
            DebtDashboardHTTPHandler,
            db_path=self.db_path,
        )
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Shutdown and close the server socket."""
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None


def export_standalone_html(
    output_path: Union[str, Path] = "dist_portable/Debtinst_s_Standalone.html",
    db_path: Optional[Union[str, Path]] = None,
) -> str:
    """
    Generate an offline standalone HTML file with all 36+ benchmark securities,
    RAYS calculations, and cash flow simulation logic baked inside.
    Runs 100% locally when opened via file:// protocol without python or internet.
    """
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    data_eng = DebtMarketDataEngine(db_path=db_path)
    quant_eng = BondQuantEngine(db_path=db_path)

    base_snapshot = data_eng.get_market_snapshot(allow_network=False)
    enriched = quant_eng.screen_securities(
        securities=base_snapshot["securities"],
        min_rating=None,
        exclude_yield_traps=False,
    )
    curve = quant_eng.build_sovereign_curve(enriched)

    payload = {
        "securities": enriched,
        "gold_24k_inr": base_snapshot["gold_24k_inr"],
        "data_source": "OFFLINE_EMBEDDED_DB",
        "sovereign_curve": curve,
        "summary": base_snapshot["summary"],
        "last_sync_utc": base_snapshot["last_sync_utc"],
    }

    html = render_dashboard_html(json.dumps(payload), standalone_mode=True)
    out_file.write_text(html, encoding="utf-8")
    return str(out_file)


def open_desktop_window(url: str) -> bool:
    """
    Launch Microsoft Edge or Google Chrome in chromeless app mode (--app=<url>),
    falling back cleanly to system default web browser.
    """
    # Windows Edge / Chrome paths
    candidates = [
        "msedge",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "chrome",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "google-chrome",
        "chromium",
    ]

    for binary in candidates:
        try:
            subprocess.Popen([binary, f"--app={url}"])
            return True
        except (FileNotFoundError, OSError):
            continue

    # Fallback to standard web browser
    webbrowser.open(url)
    return False


def run_smoke_test() -> None:
    """Run an automated self-contained smoke test verifying local server & standalone HTML."""
    print("[*] Running Sprint 4 automated smoke test...")

    # 1. Test standalone HTML export
    export_path = export_standalone_html()
    assert os.path.exists(export_path), "Standalone HTML was not created"
    file_size_kb = os.path.getsize(export_path) / 1024
    print(f"    [+] Exported Standalone HTML ({file_size_kb:.1f} KB) -> {export_path}")
    assert file_size_kb > 25, f"File size too small: {file_size_kb} KB"

    # 2. Test ephemeral server startup and HTTP routes
    server = DebtDashboardServer(host="127.0.0.1", port=0)
    server.start()
    base_url = server.url
    print(f"    [+] Started ephemeral dashboard server at {base_url}")

    try:
        # GET /
        with urllib.request.urlopen(f"{base_url}/", timeout=3.0) as resp:
            assert resp.status == 200
            content = resp.read().decode("utf-8")
            assert "Debtinst_s Terminal" in content
            print("    [+] Verified GET / -> HTTP 200 (Dashboard UI)")

        # GET /api/snapshot
        with urllib.request.urlopen(f"{base_url}/api/snapshot", timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert len(data["securities"]) >= 25
            print(f"    [+] Verified GET /api/snapshot -> HTTP 200 ({len(data['securities'])} securities)")

        # POST /api/screen
        req = urllib.request.Request(
            f"{base_url}/api/screen",
            data=json.dumps({"min_rating": "AA", "exclude_yield_traps": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["count"] > 0
            print(f"    [+] Verified POST /api/screen -> HTTP 200 ({data['count']} screened bonds)")

        # POST /api/ladder
        req = urllib.request.Request(
            f"{base_url}/api/ladder",
            data=json.dumps({"total_capital_inr": 500000.0, "allocation_mode": "rays_weighted"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "monthly_schedule" in data
            print("    [+] Verified POST /api/ladder -> HTTP 200 (12M Schedule)")

    finally:
        server.stop()
        print("    [+] Stopped ephemeral server cleanly.")

    print("\n[OK] Sprint 4 Smoke test passed with 100% zero-dependency success.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debtinst_s Interactive Dashboard Server & Standalone Builder")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind server (default: 8765)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--export-standalone", action="store_true", help="Export portable dist_portable/Debtinst_s_Standalone.html and exit")
    parser.add_argument("--smoke-test", action="store_true", help="Execute automated self-test on ephemeral port and exit")
    parser.add_argument("--no-browser", action="store_true", help="Do not launch browser window automatically")

    args = parser.parse_args()

    if args.export-standalone if hasattr(args, "export-standalone") else args.export_standalone:
        path = export_standalone_html()
        print(f"[OK] Exported Standalone Portable HTML -> {path}")
        sys.exit(0)

    if args.smoke_test:
        run_smoke_test()
        sys.exit(0)

    # Launch interactive server
    server = DebtDashboardServer(host=args.host, port=args.port)
    server.start()
    print("=================================================================")
    print("      Debtinst_s - Interactive Fixed-Income Terminal Server      ")
    print("=================================================================")
    print(f"[+] Server running at: {server.url}")
    print(f"[+] Standalone portable bundle: dist_portable/Debtinst_s_Standalone.html")
    print("    Press Ctrl+C to terminate server.\n")

    if not args.no_browser:
        open_desktop_window(server.url)

    try:
        # Keep main thread alive
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\n[*] Shutting down server...")
        server.stop()
        print("[OK] Server stopped.")
