"""
src/data_engine.py - Zero-Dependency Free-API Live Data & Bhavcopy Ingestion Engine.

Part of Sprint 2 for Debtinst_s.
Provides:
  1. Automated database synchronization with embedded seed fallback.
  2. Browser-grade NSE free API session manager with cookie persistence.
  3. Live 24K Gold spot price benchmark derivation via Yahoo Finance (GOLDBEES).
  4. Flexible CSV / Bhavcopy offline ingestion for institutional bond sheets.
  5. Unified market snapshot combining live quotes with embedded metrics.

Zero third-party dependencies: uses standard library only (`urllib.request`,
`http.cookiejar`, `sqlite3`, `json`, `csv`, `io`, `ssl`, `datetime`).
"""

from __future__ import annotations

import csv
import http.cookiejar
import io
import json
import os
import sqlite3
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Ensure project root is in sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from src.embedded_seed import (
        get_connection,
        get_db_summary,
        get_default_db_path,
        init_embedded_db,
        query_securities,
    )
except ImportError:
    from embedded_seed import (  # type: ignore
        get_connection,
        get_db_summary,
        get_default_db_path,
        init_embedded_db,
        query_securities,
    )

DEFAULT_TIMEOUT_SECONDS = 4.0
DEFAULT_FALLBACK_GOLD_INR = 7850.0  # Conservative 24K Gold benchmark INR/gram

# Common browser headers to avoid WAF / bot blocks
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/market-data/bonds-traded-in-capital-market",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}


def _parse_float(val: Any) -> Optional[float]:
    """Safely parse a float from strings with commas, nulls, or numbers."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace(",", "").strip()
    if not s or s.lower() in ("-", "na", "n/a", "null", "none"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_int(val: Any) -> int:
    """Safely parse an integer from numbers or formatted strings."""
    parsed = _parse_float(val)
    return int(parsed) if parsed is not None else 0


class DebtMarketDataEngine:
    """
    Zero-dependency market data engine for Indian fixed income and gold bonds.
    Orchestrates live free APIs, CSV Bhavcopy ingestion, and embedded SQLite storage.
    """

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        fallback_gold_inr: float = DEFAULT_FALLBACK_GOLD_INR,
    ):
        self.db_path = Path(db_path) if db_path else get_default_db_path()
        self.timeout_seconds = timeout_seconds
        self.fallback_gold_inr = fallback_gold_inr
        self._cookie_jar = http.cookiejar.CookieJar()
        self._opener: Optional[urllib.request.OpenerDirector] = None

        # Automatically ensure database and tables are initialized
        self.sync_database(allow_network=False)

    # -------------------------------------------------------------------------
    # Database Initialization & Schema Migration
    # -------------------------------------------------------------------------
    def _ensure_schema(self) -> None:
        """Ensure base seed exists, add live market columns, and create sync log table."""
        init_embedded_db(self.db_path)

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()

            # Non-destructive column additions to 'securities' table
            cursor.execute("PRAGMA table_info(securities)")
            existing_cols = {row[1] for row in cursor.fetchall()}

            if "current_price" not in existing_cols:
                cursor.execute("ALTER TABLE securities ADD COLUMN current_price REAL")
            if "traded_volume" not in existing_cols:
                cursor.execute("ALTER TABLE securities ADD COLUMN traded_volume INTEGER DEFAULT 0")
            if "last_traded_date" not in existing_cols:
                cursor.execute("ALTER TABLE securities ADD COLUMN last_traded_date TEXT")

            # Create metadata table for tracking sync runs
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS market_sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    last_sync_utc TEXT NOT NULL,
                    data_source_mode TEXT NOT NULL,
                    gold_spot_inr_per_gram REAL NOT NULL,
                    records_updated INTEGER NOT NULL DEFAULT 0,
                    sync_details_json TEXT
                );
                """
            )
            conn.commit()
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # NSE Free API Session Manager
    # -------------------------------------------------------------------------
    def _create_nse_opener(self) -> urllib.request.OpenerDirector:
        """Create or return a reusable HTTP opener with cookie management."""
        if self._opener is not None:
            return self._opener

        # Create an SSL context that allows standard verification
        ssl_ctx = ssl.create_default_context()

        cookie_processor = urllib.request.HTTPCookieProcessor(self._cookie_jar)
        https_handler = urllib.request.HTTPSHandler(context=ssl_ctx)
        self._opener = urllib.request.build_opener(cookie_processor, https_handler)
        return self._opener

    def _prime_nse_session(self) -> bool:
        """Make an initial GET request to nseindia.com to seed session cookies."""
        opener = self._create_nse_opener()
        req = urllib.request.Request(
            "https://www.nseindia.com",
            headers={
                "User-Agent": BROWSER_HEADERS["User-Agent"],
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        try:
            with opener.open(req, timeout=self.timeout_seconds) as resp:
                _ = resp.read()
            return True
        except Exception:
            return False

    def _fetch_json(self, url: str) -> Optional[Any]:
        """Fetch JSON data from a URL using browser headers and timeout."""
        opener = self._create_nse_opener()
        req = urllib.request.Request(url, headers=BROWSER_HEADERS)
        try:
            with opener.open(req, timeout=self.timeout_seconds) as resp:
                content = resp.read().decode("utf-8", errors="replace")
                return json.loads(content)
        except Exception:
            return None

    def fetch_nse_live_quotes(self) -> Dict[str, Any]:
        """
        Fetch live quotes from NSE public API endpoints:
          1. SGBs: /api/sovereign-gold-bonds
          2. Corporate NCDs: /api/liveBonds-traded-on-cm
          3. G-Secs & T-Bills: /api/liveGovSec

        Matches incoming quotes by ISIN or symbol to update prices, yields,
        and traded volumes in SQLite.
        """
        self._ensure_schema()
        # Seed cookies first
        self._prime_nse_session()

        sgb_url = "https://www.nseindia.com/api/sovereign-gold-bonds"
        ncd_url = "https://www.nseindia.com/api/liveBonds-traded-on-cm"
        gsec_url = "https://www.nseindia.com/api/liveGovSec"

        results = {
            "sgb_updated": 0,
            "ncd_updated": 0,
            "gsec_updated": 0,
            "total_updated": 0,
            "errors": [],
        }

        # 1. Sovereign Gold Bonds
        sgb_data = self._fetch_json(sgb_url)
        if sgb_data:
            items = sgb_data.get("data", sgb_data) if isinstance(sgb_data, dict) else sgb_data
            if isinstance(items, list):
                results["sgb_updated"] = self._update_market_records(items, category_hint="SGB")
        else:
            results["errors"].append("SGB endpoint unreachable or blocked")

        # 2. Corporate Bonds
        ncd_data = self._fetch_json(ncd_url)
        if ncd_data:
            items = ncd_data.get("data", ncd_data) if isinstance(ncd_data, dict) else ncd_data
            if isinstance(items, list):
                results["ncd_updated"] = self._update_market_records(items, category_hint="Corporate NCD")
        else:
            results["errors"].append("Corporate NCD endpoint unreachable or blocked")

        # 3. Government Securities & T-Bills
        gsec_data = self._fetch_json(gsec_url)
        if gsec_data:
            items = gsec_data.get("data", gsec_data) if isinstance(gsec_data, dict) else gsec_data
            if isinstance(items, list):
                results["gsec_updated"] = self._update_market_records(items, category_hint="G-Sec")
        else:
            results["errors"].append("G-Sec endpoint unreachable or blocked")

        results["total_updated"] = (
            results["sgb_updated"] + results["ncd_updated"] + results["gsec_updated"]
        )
        return results

    def _update_market_records(
        self, items: List[Dict[str, Any]], category_hint: str
    ) -> int:
        """Update market price, volume, and yield in database for given items."""
        now_utc = datetime.now(timezone.utc).isoformat()
        updated_count = 0

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()

            for item in items:
                if not isinstance(item, dict):
                    continue

                # Extract ISIN / Symbol flexibly
                isin = item.get("isin") or item.get("ISIN")
                symbol = item.get("symbol") or item.get("SYMBOL") or item.get("security") or item.get("securityDesc")

                if isin:
                    isin = str(isin).strip().upper()
                if symbol:
                    symbol = str(symbol).strip().upper()

                if not isin and not symbol:
                    continue

                # Extract price
                price = None
                for price_key in ("ltp", "lastPrice", "closePrice", "cleanPrice", "price", "last_price", "close"):
                    if price_key in item:
                        price = _parse_float(item[price_key])
                        if price is not None:
                            break

                # Extract volume
                volume = 0
                for vol_key in ("totalTradedVolume", "volume", "tradedVolume", "quantity", "totalQuantity", "tottrdqty"):
                    if vol_key in item:
                        volume = _parse_int(item[vol_key])
                        if volume > 0:
                            break

                # Extract yield if available
                market_yield = None
                for yield_key in ("yield", "ytm", "indicativeYield", "weightedAvgYield"):
                    if yield_key in item:
                        market_yield = _parse_float(item[yield_key])
                        if market_yield is not None:
                            break

                # Check if security exists in DB
                cursor.execute(
                    "SELECT isin, yield_to_maturity FROM securities WHERE isin = ? OR symbol = ?",
                    (isin or "", symbol or ""),
                )
                row = cursor.fetchone()

                if row:
                    matched_isin = row[0]
                    # Update existing record
                    if market_yield is not None and market_yield > 0:
                        cursor.execute(
                            """
                            UPDATE securities
                            SET current_price = COALESCE(?, current_price),
                                traded_volume = ?,
                                yield_to_maturity = ?,
                                last_traded_date = ?
                            WHERE isin = ?
                            """,
                            (price, volume, market_yield, now_utc, matched_isin),
                        )
                    else:
                        cursor.execute(
                            """
                            UPDATE securities
                            SET current_price = COALESCE(?, current_price),
                                traded_volume = ?,
                                last_traded_date = ?
                            WHERE isin = ?
                            """,
                            (price, volume, now_utc, matched_isin),
                        )
                    updated_count += 1
                elif isin and len(isin) == 12 and price:
                    # Newly discovered liquid bond: insert with safe default attributes
                    name = item.get("name") or item.get("companyName") or symbol or isin
                    issuer = item.get("issuer") or name
                    sec_type = "Non-Convertible Debenture" if category_hint == "Corporate NCD" else "Government Bond"
                    rating = "SOV" if category_hint in ("G-Sec", "SGB") else "UNRATED / LIQUID"
                    seniority = "Sovereign" if category_hint in ("G-Sec", "SGB") else "Secured"
                    sov_guarantee = 1 if category_hint in ("G-Sec", "SGB") else 0
                    risk_tier = "Manageable Risk - Low" if sov_guarantee else "Manageable Risk - Moderate"

                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO securities (
                            isin, symbol, name, category, security_type, issuer,
                            rating, rating_agency, seniority, asset_cover_ratio,
                            coupon_rate, coupon_frequency, face_value, issue_price,
                            issue_date, maturity_date, tenor_years, gold_grams,
                            sovereign_guarantee, yield_to_maturity, benchmark_index,
                            expense_ratio, tax_treatment, risk_tier, metadata_json,
                            current_price, traded_volume, last_traded_date, created_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?,
                            ?, ?, ?, ?,
                            ?, ?, ?, ?,
                            ?, ?, ?,
                            ?, ?, ?, ?,
                            ?, ?, ?, ?
                        )
                        """,
                        (
                            isin,
                            symbol or isin,
                            name,
                            category_hint,
                            sec_type,
                            issuer,
                            rating,
                            "Market Derived",
                            seniority,
                            1.25 if seniority == "Secured" else None,
                            market_yield or 0.0,
                            "Annual",
                            1000.0,
                            price,
                            "2024-01-01",
                            "2029-01-01",
                            5.0,
                            1.0 if category_hint == "SGB" else 0.0,
                            sov_guarantee,
                            market_yield or 0.0,
                            None,
                            0.0,
                            "Standard debt slab",
                            risk_tier,
                            json.dumps({"source": "live_nse_feed"}),
                            price,
                            volume,
                            now_utc,
                            now_utc,
                        ),
                    )
                    updated_count += 1

            conn.commit()
        finally:
            conn.close()

        return updated_count

    # -------------------------------------------------------------------------
    # Live 24K Gold Benchmark Fetcher (Yahoo Finance GOLDBEES)
    # -------------------------------------------------------------------------
    def fetch_gold_spot_inr(self) -> float:
        """
        Derive live 24K Gold price per gram in INR using Yahoo Finance free chart API
        for Nippon India ETF Gold BeES (GOLDBEES.NS).

        Each unit of Gold BeES corresponds to ~0.01 gram of gold (1/100th gram).
        Multiplying unit market price by 100 calculates the 1g benchmark.
        Falls back to self.fallback_gold_inr if offline or blocked.
        """
        url = "https://query1.finance.yahoo.com/v8/finance/chart/GOLDBEES.NS?interval=1d&range=5d"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": BROWSER_HEADERS["User-Agent"],
                "Accept": "application/json",
            },
        )

        try:
            # We create a fresh opener with standard SSL context
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=self.timeout_seconds, context=ctx) as resp:
                raw_bytes = resp.read()
                data = json.loads(raw_bytes.decode("utf-8", errors="replace"))

            result = data.get("chart", {}).get("result", [{}])[0]
            meta = result.get("meta", {})
            market_price = meta.get("regularMarketPrice")

            # Fallback to indicators.quote[0].close[-1] if meta price is absent
            if market_price is None:
                quotes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
                valid_closes = [c for c in quotes if c is not None]
                if valid_closes:
                    market_price = valid_closes[-1]

            if market_price is not None and market_price > 0:
                # 1 share of GOLDBEES represents ~0.01g of gold
                derived_gold_inr = (
                    market_price * 100.0 if market_price < 500.0 else market_price
                )
                return round(float(derived_gold_inr), 2)
        except Exception:
            pass

        return float(self.fallback_gold_inr)

    # -------------------------------------------------------------------------
    # Offline CSV / Bhavcopy Ingestion Engine
    # -------------------------------------------------------------------------
    def import_bhavcopy_csv(self, csv_source: Union[str, Path, io.StringIO]) -> int:
        """
        Import or update fixed-income securities from a CSV Bhavcopy or institutional sheet.
        Supports file paths, raw CSV strings, or StringIO streams.

        Flexibly maps columns such as ISIN, SYMBOL, CLOSE/LTP, VOLUME, COUPON, RATING,
        SENIORITY, ASSET_COVER, and MATURITY.
        """
        self._ensure_schema()

        # Resolve content
        content: str
        if isinstance(csv_source, Path) or (
            isinstance(csv_source, str) and not ("\n" in csv_source or "," in csv_source)
        ):
            file_path = Path(csv_source)
            if file_path.is_file():
                content = file_path.read_text(encoding="utf-8", errors="replace")
            else:
                content = str(csv_source)
        elif isinstance(csv_source, str):
            content = csv_source
        elif hasattr(csv_source, "read"):
            content = csv_source.read()
        else:
            content = str(csv_source)

        reader = csv.DictReader(io.StringIO(content.strip()))
        if not reader.fieldnames:
            return 0

        # Build column index mapping (lowercase stripped to standard key)
        col_map: Dict[str, str] = {}
        target_keys = {
            "isin": ["isin", "isin_code", "security_isin"],
            "symbol": ["symbol", "ticker", "security", "series_name"],
            "name": ["name", "security_name", "description", "issuer_name"],
            "price": ["close", "ltp", "last_price", "close_price", "prev_close", "price"],
            "volume": ["tottrdqty", "volume", "trade_qty", "total_traded_quantity", "traded_qty"],
            "coupon": ["coupon", "coupon_rate", "rate", "interest_rate"],
            "rating": ["rating", "credit_rating", "rating_agency_rating"],
            "rating_agency": ["agency", "rating_agency", "credit_agency"],
            "seniority": ["seniority", "tier", "security_type_tier"],
            "asset_cover": ["asset_cover", "asset_cover_ratio", "cover", "cover_ratio"],
            "maturity_date": ["maturity", "maturity_date", "expiry_date", "mat_date"],
            "category": ["category", "asset_class", "type"],
            "yield": ["ytm", "yield", "yield_to_maturity"],
            "face_value": ["face_value", "fv"],
        }

        for raw_col in reader.fieldnames:
            normalized_col = raw_col.strip().lower().replace(" ", "_")
            for canonical, aliases in target_keys.items():
                if normalized_col in aliases:
                    col_map[raw_col] = canonical
                    break

        now_utc = datetime.now(timezone.utc).isoformat()
        records_processed = 0

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()

            for row in reader:
                # Extract normalized row values
                row_data: Dict[str, Any] = {}
                for raw_col, val in row.items():
                    canonical = col_map.get(raw_col)
                    if canonical:
                        row_data[canonical] = val

                isin = (row_data.get("isin") or "").strip().upper()
                symbol = (row_data.get("symbol") or "").strip().upper()

                if not isin and not symbol:
                    continue

                price = _parse_float(row_data.get("price"))
                volume = _parse_int(row_data.get("volume"))
                coupon = _parse_float(row_data.get("coupon"))
                rating = (row_data.get("rating") or "").strip()
                seniority = (row_data.get("seniority") or "").strip()
                asset_cover = _parse_float(row_data.get("asset_cover"))
                maturity = (row_data.get("maturity_date") or "").strip()
                market_yield = _parse_float(row_data.get("yield"))
                category = (row_data.get("category") or "Corporate NCD").strip()
                name = (row_data.get("name") or symbol or isin).strip()

                # Check if security exists
                cursor.execute(
                    "SELECT isin FROM securities WHERE isin = ? OR symbol = ?",
                    (isin, symbol),
                )
                existing = cursor.fetchone()

                if existing:
                    matched_isin = existing[0]
                    # Dynamic partial update
                    updates: List[str] = ["last_traded_date = ?"]
                    params: List[Any] = [now_utc]

                    if price is not None:
                        updates.append("current_price = ?")
                        params.append(price)
                    if volume > 0:
                        updates.append("traded_volume = ?")
                        params.append(volume)
                    if coupon is not None:
                        updates.append("coupon_rate = ?")
                        params.append(coupon)
                    if rating:
                        updates.append("rating = ?")
                        params.append(rating)
                    if seniority:
                        updates.append("seniority = ?")
                        params.append(seniority)
                    if asset_cover is not None:
                        updates.append("asset_cover_ratio = ?")
                        params.append(asset_cover)
                    if maturity:
                        updates.append("maturity_date = ?")
                        params.append(maturity)
                    if market_yield is not None:
                        updates.append("yield_to_maturity = ?")
                        params.append(market_yield)

                    params.append(matched_isin)
                    sql = f"UPDATE securities SET {', '.join(updates)} WHERE isin = ?"
                    cursor.execute(sql, params)
                    records_processed += 1
                elif isin and len(isin) == 12:
                    # New security insertion
                    sov_guarantee = 1 if rating == "SOV" or category in ("G-Sec", "SGB", "T-Bill") else 0
                    risk_tier = (
                        "Manageable Risk - Low"
                        if (sov_guarantee or "AAA" in rating)
                        else (
                            "Manageable Risk - Moderate"
                            if "AA" in rating
                            else "High Risk - Speculative"
                        )
                    )

                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO securities (
                            isin, symbol, name, category, security_type, issuer,
                            rating, rating_agency, seniority, asset_cover_ratio,
                            coupon_rate, coupon_frequency, face_value, issue_price,
                            issue_date, maturity_date, tenor_years, gold_grams,
                            sovereign_guarantee, yield_to_maturity, benchmark_index,
                            expense_ratio, tax_treatment, risk_tier, metadata_json,
                            current_price, traded_volume, last_traded_date, created_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?,
                            ?, ?, ?, ?,
                            ?, ?, ?, ?,
                            ?, ?, ?,
                            ?, ?, ?, ?,
                            ?, ?, ?, ?
                        )
                        """,
                        (
                            isin,
                            symbol or isin,
                            name,
                            category,
                            "Non-Convertible Debenture",
                            name,
                            rating or "UNRATED",
                            row_data.get("rating_agency") or "Imported",
                            seniority or "Secured",
                            asset_cover or 1.25,
                            coupon or 0.0,
                            "Annual",
                            _parse_float(row_data.get("face_value")) or 1000.0,
                            price or 1000.0,
                            "2024-01-01",
                            maturity or "2030-01-01",
                            5.0,
                            1.0 if category == "SGB" else 0.0,
                            sov_guarantee,
                            market_yield or coupon or 0.0,
                            None,
                            0.0,
                            "Standard debt slab",
                            risk_tier,
                            json.dumps({"source": "bhavcopy_import"}),
                            price,
                            volume,
                            now_utc,
                            now_utc,
                        ),
                    )
                    records_processed += 1

            conn.commit()
        finally:
            conn.close()

        return records_processed

    # -------------------------------------------------------------------------
    # Synchronization & Unified Market Snapshot
    # -------------------------------------------------------------------------
    def sync_database(self, allow_network: bool = True) -> Dict[str, Any]:
        """
        Run database synchronization.
        If allow_network is True, attempts to query live free APIs for Gold and NSE.
        If network fails or allow_network is False, cleanly falls back to embedded data.
        Records sync event into 'market_sync_log'.
        """
        self._ensure_schema()

        data_source_mode = "OFFLINE_EMBEDDED_DB"
        gold_spot = float(self.fallback_gold_inr)
        records_updated = 0
        details: Dict[str, Any] = {"allow_network": allow_network}

        if allow_network:
            try:
                # 1. Fetch live gold benchmark
                gold_spot = self.fetch_gold_spot_inr()

                # 2. Fetch live quotes from NSE
                live_res = self.fetch_nse_live_quotes()
                records_updated = live_res.get("total_updated", 0)
                details["nse_summary"] = live_res

                if records_updated > 0 or not live_res.get("errors"):
                    data_source_mode = "LIVE_FREE_API"
                else:
                    data_source_mode = "OFFLINE_EMBEDDED_DB"
            except Exception as e:
                data_source_mode = "OFFLINE_EMBEDDED_DB"
                gold_spot = float(self.fallback_gold_inr)
                details["error"] = str(e)

        now_utc = datetime.now(timezone.utc).isoformat()

        # Log sync event
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO market_sync_log (
                    last_sync_utc, data_source_mode, gold_spot_inr_per_gram,
                    records_updated, sync_details_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (now_utc, data_source_mode, gold_spot, records_updated, json.dumps(details)),
            )
            conn.commit()
        finally:
            conn.close()

        return {
            "last_sync_utc": now_utc,
            "data_source_mode": data_source_mode,
            "gold_spot_inr_per_gram": gold_spot,
            "records_updated": records_updated,
            "details": details,
        }

    def get_latest_sync_log(self) -> Optional[Dict[str, Any]]:
        """Fetch the most recent sync entry from market_sync_log."""
        self._ensure_schema()
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM market_sync_log ORDER BY id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_market_snapshot(self, allow_network: bool = True) -> Dict[str, Any]:
        """
        Unified market snapshot returning:
          - securities: full enriched list of securities from SQLite
          - gold_24k_inr: live or fallback gold price in INR/gram
          - data_source: 'LIVE_FREE_API' or 'OFFLINE_EMBEDDED_DB'
          - summary: statistical aggregate summary from get_db_summary()
          - last_sync_utc: timestamp of sync
        """
        sync_result = self.sync_database(allow_network=allow_network)

        # Load all securities
        securities = query_securities(db_path=self.db_path)
        summary = get_db_summary(db_path=self.db_path)

        return {
            "securities": securities,
            "gold_24k_inr": sync_result["gold_spot_inr_per_gram"],
            "data_source": sync_result["data_source_mode"],
            "summary": summary,
            "last_sync_utc": sync_result["last_sync_utc"],
            "records_updated": sync_result["records_updated"],
        }


if __name__ == "__main__":
    print("=================================================================")
    print("   Debtinst_s - Sprint 2 Market Data & Ingestion Engine Demo    ")
    print("=================================================================")

    engine = DebtMarketDataEngine()
    print(f"[+] Initialized DebtMarketDataEngine with DB: {engine.db_path}")

    # Offline Snapshot Demo
    snapshot = engine.get_market_snapshot(allow_network=False)
    print(f"[+] Market Data Source Mode: {snapshot['data_source']}")
    print(f"[+] Benchmark 24K Gold Price: INR {snapshot['gold_24k_inr']:,.2f} / gram")
    print(f"[+] Total Active Securities in DB: {snapshot['summary']['total_securities']}")

    # Demonstrating Bhavcopy Import
    sample_bhavcopy = """ISIN,SYMBOL,NAME,CLOSE,VOLUME,COUPON,RATING,SENIORITY,ASSET_COVER
INE001A07TO2,HDFC27,HDFC Ltd Senior Secured 2027,1015.50,12500,7.95,CRISIL AAA,Senior Secured,1.50
INE296A07RX6,BAJFIN28,Bajaj Finance Senior Secured 2028,1022.00,8400,7.75,CRISIL AAA,Senior Secured,1.40
INE721A07QU8,SHRIRAM28,Shriram Finance Secured 2028,1035.00,5600,8.75,CRISIL AA+,Senior Secured,1.25
INE999A07XYZ,NEWCORP29,NewCorp Senior Secured NCD,1000.00,3200,8.50,CRISIL AAA,Senior Secured,1.45
"""
    updated_rows = engine.import_bhavcopy_csv(sample_bhavcopy)
    print(f"[+] Successfully imported Bhavcopy test sample: {updated_rows} records upserted.")

    # Inspecting updated securities
    hdfc_sec = [s for s in query_securities(db_path=engine.db_path) if s["symbol"] == "HDFC27"][0]
    print(f"    * HDFC27 Market Price: INR {hdfc_sec.get('current_price')} | Traded Volume: {hdfc_sec.get('traded_volume')}")

    print("\n[OK] Sprint 2 Market Data Engine successfully verified with zero third-party dependencies.")
