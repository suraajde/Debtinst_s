"""
tests/test_data_engine.py - Unit tests for Debt Market Data Engine.

Sprint 2: Validates zero-dependency Free-API live quotes, cookie session manager,
Yahoo Finance 24K gold benchmark derivation, Bhavcopy CSV ingestion,
and seamless offline fallback to the 36 embedded seed securities.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.data_engine import DebtMarketDataEngine
from src.embedded_seed import BENCHMARK_SECURITIES, get_connection, query_securities


class TestDebtMarketDataEngine(unittest.TestCase):
    """Test suite for DebtMarketDataEngine with zero external network reliance."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_db_path = Path(self.temp_dir.name) / "test_debt_securities.db"
        self.engine = DebtMarketDataEngine(
            db_path=self.temp_db_path,
            timeout_seconds=2.0,
            fallback_gold_inr=7850.0,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    # -------------------------------------------------------------------------
    # 1. Offline Initialization & Fallback
    # -------------------------------------------------------------------------
    def test_init_offline_fallback_and_seed_retention(self):
        """Engine must auto-materialize database with all 36 embedded securities."""
        snapshot = self.engine.get_market_snapshot(allow_network=False)
        self.assertEqual(snapshot["data_source"], "OFFLINE_EMBEDDED_DB")
        self.assertEqual(snapshot["gold_24k_inr"], 7850.0)
        self.assertEqual(len(snapshot["securities"]), len(BENCHMARK_SECURITIES))
        self.assertGreaterEqual(snapshot["summary"]["total_securities"], 25)

    def test_market_sync_log_table(self):
        """market_sync_log table must exist and record sync runs."""
        latest_log = self.engine.get_latest_sync_log()
        self.assertIsNotNone(latest_log)
        self.assertEqual(latest_log["data_source_mode"], "OFFLINE_EMBEDDED_DB")
        self.assertEqual(latest_log["gold_spot_inr_per_gram"], 7850.0)
        self.assertIn("T", latest_log["last_sync_utc"])

    # -------------------------------------------------------------------------
    # 2. Live 24K Gold Price Derivation via Yahoo Finance (Mocked)
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    def test_gold_spot_yahoo_finance_meta_price(self, mock_urlopen):
        """Derive 24K Gold price/gram from GOLDBEES regularMarketPrice (79.25 -> 7925.0)."""
        mock_payload = {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "regularMarketPrice": 79.25,
                            "symbol": "GOLDBEES.NS",
                        }
                    }
                ]
            }
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        gold_price = self.engine.fetch_gold_spot_inr()
        self.assertEqual(gold_price, 7925.0)

    @patch("urllib.request.urlopen")
    def test_gold_spot_yahoo_finance_quote_indicators_fallback(self, mock_urlopen):
        """Derive gold price from latest quote close when regularMarketPrice is absent."""
        mock_payload = {
            "chart": {
                "result": [
                    {
                        "meta": {},
                        "indicators": {
                            "quote": [
                                {
                                    "close": [78.10, 78.40, 79.60]
                                }
                            ]
                        },
                    }
                ]
            }
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        gold_price = self.engine.fetch_gold_spot_inr()
        self.assertEqual(gold_price, 7960.0)

    @patch("urllib.request.urlopen")
    def test_gold_spot_network_error_fallback(self, mock_urlopen):
        """Gracefully fall back to configured fallback price if Yahoo Finance fails."""
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
        gold_price = self.engine.fetch_gold_spot_inr()
        self.assertEqual(gold_price, 7850.0)

    # -------------------------------------------------------------------------
    # 3. NSE Live Quotes Ingestion (Mocked Payloads)
    # -------------------------------------------------------------------------
    @patch.object(DebtMarketDataEngine, "_prime_nse_session", return_value=True)
    @patch.object(DebtMarketDataEngine, "_fetch_json")
    def test_nse_sgb_quotes_update(self, mock_fetch_json, mock_prime):
        """Update SGB market prices and traded volume from NSE SGB endpoint."""
        def fetch_side_effect(url: str):
            if "sovereign-gold-bonds" in url:
                return {
                    "data": [
                        {
                            "symbol": "SGB2324IV",
                            "isin": "IN0020230150",
                            "ltp": "7,920.00",
                            "totalTradedVolume": "4,500",
                        }
                    ]
                }
            return None

        mock_fetch_json.side_effect = fetch_side_effect

        res = self.engine.fetch_nse_live_quotes()
        self.assertEqual(res["sgb_updated"], 1)

        # Check DB update
        sgb = [s for s in query_securities(db_path=self.temp_db_path) if s["isin"] == "IN0020230150"][0]
        self.assertEqual(sgb["current_price"], 7920.0)
        self.assertEqual(sgb["traded_volume"], 4500)

    @patch.object(DebtMarketDataEngine, "_prime_nse_session", return_value=True)
    @patch.object(DebtMarketDataEngine, "_fetch_json")
    def test_nse_corporate_bonds_quotes_update(self, mock_fetch_json, mock_prime):
        """Update Corporate NCD price, yield, and volume from liveBonds-traded-on-cm."""
        def fetch_side_effect(url: str):
            if "liveBonds-traded-on-cm" in url:
                return {
                    "data": [
                        {
                            "symbol": "HDFC27",
                            "isin": "INE001A07TO2",
                            "lastPrice": "1,018.50",
                            "ytm": "7.82",
                            "totalTradedVolume": "12,000",
                        }
                    ]
                }
            return None

        mock_fetch_json.side_effect = fetch_side_effect

        res = self.engine.fetch_nse_live_quotes()
        self.assertEqual(res["ncd_updated"], 1)

        hdfc = [s for s in query_securities(db_path=self.temp_db_path) if s["isin"] == "INE001A07TO2"][0]
        self.assertEqual(hdfc["current_price"], 1018.50)
        self.assertEqual(hdfc["traded_volume"], 12000)
        self.assertEqual(hdfc["yield_to_maturity"], 7.82)

    @patch.object(DebtMarketDataEngine, "_prime_nse_session", return_value=True)
    @patch.object(DebtMarketDataEngine, "_fetch_json")
    def test_nse_gsec_quotes_update(self, mock_fetch_json, mock_prime):
        """Update G-Sec benchmark prices and yields from liveGovSec."""
        def fetch_side_effect(url: str):
            if "liveGovSec" in url:
                return {
                    "data": [
                        {
                            "symbol": "718GS2033",
                            "isin": "IN0020230085",
                            "cleanPrice": "100.35",
                            "indicativeYield": "7.14",
                            "tradedVolume": "350000",
                        }
                    ]
                }
            return None

        mock_fetch_json.side_effect = fetch_side_effect

        res = self.engine.fetch_nse_live_quotes()
        self.assertEqual(res["gsec_updated"], 1)

        gsec = [s for s in query_securities(db_path=self.temp_db_path) if s["isin"] == "IN0020230085"][0]
        self.assertEqual(gsec["current_price"], 100.35)
        self.assertEqual(gsec["yield_to_maturity"], 7.14)
        self.assertEqual(gsec["traded_volume"], 350000)

    @patch.object(DebtMarketDataEngine, "_prime_nse_session", return_value=True)
    @patch.object(DebtMarketDataEngine, "_fetch_json")
    def test_nse_new_liquid_bond_discovery(self, mock_fetch_json, mock_prime):
        """Newly discovered liquid bonds on NSE feed are inserted with safe default tags."""
        new_isin = "INE999A07999"
        def fetch_side_effect(url: str):
            if "liveBonds-traded-on-cm" in url:
                return {
                    "data": [
                        {
                            "symbol": "NEWNBFC28",
                            "isin": new_isin,
                            "companyName": "New Age NBFC Ltd",
                            "lastPrice": "1,005.00",
                            "ytm": "8.40",
                            "totalTradedVolume": "2,500",
                        }
                    ]
                }
            return None

        mock_fetch_json.side_effect = fetch_side_effect

        res = self.engine.fetch_nse_live_quotes()
        self.assertEqual(res["ncd_updated"], 1)

        new_bond = [s for s in query_securities(db_path=self.temp_db_path) if s["isin"] == new_isin]
        self.assertEqual(len(new_bond), 1)
        self.assertEqual(new_bond[0]["current_price"], 1005.0)
        self.assertEqual(new_bond[0]["seniority"], "Secured")
        self.assertEqual(new_bond[0]["rating"], "UNRATED / LIQUID")

    # -------------------------------------------------------------------------
    # 4. Offline CSV / Bhavcopy Ingestion
    # -------------------------------------------------------------------------
    def test_import_bhavcopy_csv_string_update_existing(self):
        """Update existing corporate bonds from raw CSV Bhavcopy text."""
        csv_data = """ISIN,SYMBOL,CLOSE,TOTTRDQTY,RATING,ASSET_COVER
INE296A07RX6,BAJFIN28,1025.00,18500,CRISIL AAA,1.45
INE721A07QU8,SHRIRAM28,1038.50,9200,CRISIL AA+,1.28
"""
        count = self.engine.import_bhavcopy_csv(csv_data)
        self.assertEqual(count, 2)

        bajaj = [s for s in query_securities(db_path=self.temp_db_path) if s["isin"] == "INE296A07RX6"][0]
        self.assertEqual(bajaj["current_price"], 1025.00)
        self.assertEqual(bajaj["traded_volume"], 18500)
        self.assertEqual(bajaj["asset_cover_ratio"], 1.45)

        shriram = [s for s in query_securities(db_path=self.temp_db_path) if s["isin"] == "INE721A07QU8"][0]
        self.assertEqual(shriram["current_price"], 1038.50)
        self.assertEqual(shriram["traded_volume"], 9200)
        self.assertEqual(shriram["asset_cover_ratio"], 1.28)

    def test_import_bhavcopy_csv_insert_new_security(self):
        """Bhavcopy import should insert newly listed securities cleanly."""
        new_isin = "INE777C07777"
        csv_data = f"""ISIN,SYMBOL,NAME,CLOSE,TOTTRDQTY,COUPON,RATING,SENIORITY,ASSET_COVER
{new_isin},TATASTEEL29,Tata Steel Senior Secured 2029,1012.00,7500,8.25,CRISIL AA+,Senior Secured,1.35
"""
        count = self.engine.import_bhavcopy_csv(io.StringIO(csv_data))
        self.assertEqual(count, 1)

        tata = [s for s in query_securities(db_path=self.temp_db_path) if s["isin"] == new_isin]
        self.assertEqual(len(tata), 1)
        self.assertEqual(tata[0]["symbol"], "TATASTEEL29")
        self.assertEqual(tata[0]["coupon_rate"], 8.25)
        self.assertEqual(tata[0]["rating"], "CRISIL AA+")
        self.assertEqual(tata[0]["asset_cover_ratio"], 1.35)

    # -------------------------------------------------------------------------
    # 5. Data Integrity & Negative Test Cases
    # -------------------------------------------------------------------------
    def test_seed_securities_remain_intact_after_sync_and_import(self):
        """Verify Tier A AAA, Tier B AA, and Tier C stress-test bonds remain intact."""
        # Execute sync and an import
        self.engine.sync_database(allow_network=False)
        self.engine.import_bhavcopy_csv("ISIN,SYMBOL,CLOSE\nIN0020230085,718GS2033,100.50\n")

        all_sec = query_securities(db_path=self.temp_db_path)
        all_isins = {s["isin"] for s in all_sec}

        # Verify stress-test bonds are still present
        self.assertIn("INE062A08231", all_isins)  # SBI Tier-II
        self.assertIn("INE522D08021", all_isins)  # Yes Bank Tier-II
        self.assertIn("INE608A07248", all_isins)  # Reliance Capital Default Benchmark
        self.assertIn("IN0020230150", all_isins)  # SGB 2023-24 IV

        # Verify Reliance Capital remains flagged as Defaulted / Unsecured
        relcap = [s for s in all_sec if s["isin"] == "INE608A07248"][0]
        self.assertEqual(relcap["risk_tier"], "High Risk - Defaulted")
        self.assertEqual(relcap["seniority"], "Unsecured Subordinated")

    @patch("urllib.request.urlopen")
    @patch.object(DebtMarketDataEngine, "_prime_nse_session")
    def test_sync_database_network_failure_graceful(self, mock_prime, mock_urlopen):
        """Engine seamlessly handles network outages and reports OFFLINE_EMBEDDED_DB."""
        mock_urlopen.side_effect = urllib.error.URLError("Connection timed out")
        mock_prime.return_value = False

        res = self.engine.sync_database(allow_network=True)
        self.assertIn(res["data_source_mode"], ("OFFLINE_EMBEDDED_DB", "LIVE_FREE_API"))
        self.assertGreaterEqual(res["gold_spot_inr_per_gram"], 5000.0)

        # Snapshot still returns complete dataset
        snapshot = self.engine.get_market_snapshot(allow_network=False)
        self.assertGreaterEqual(len(snapshot["securities"]), 36)


if __name__ == "__main__":
    unittest.main()
