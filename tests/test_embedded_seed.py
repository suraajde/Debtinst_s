"""
tests/test_embedded_seed.py - Unit tests for Debtinst_s Embedded Bond Database.

Sprint 1: Zero-dependency test suite validating benchmark debt securities,
schema constraints, data integrity, and SQLite auto-materialization.
"""

import os
import tempfile
import unittest
from pathlib import Path

from src.embedded_seed import (
    BENCHMARK_SECURITIES,
    get_connection,
    get_db_summary,
    get_security_by_isin,
    init_embedded_db,
    query_securities,
)


class TestEmbeddedSeedDataset(unittest.TestCase):
    """Test suite for embedded dataset structure, constraints, and realism."""

    def test_minimum_securities_count(self):
        """Must have 25+ benchmark securities across required categories."""
        self.assertGreaterEqual(
            len(BENCHMARK_SECURITIES),
            25,
            f"Expected at least 25 benchmark securities, found {len(BENCHMARK_SECURITIES)}",
        )

    def test_isin_uniqueness_and_format(self):
        """Every security must have a unique 12-character ISIN."""
        isins = [s["isin"] for s in BENCHMARK_SECURITIES]
        self.assertEqual(len(isins), len(set(isins)), "Duplicate ISIN detected in seed dataset")
        for isin in isins:
            self.assertEqual(len(isin), 12, f"Invalid ISIN length for {isin}")
            self.assertTrue(isin.isalnum(), f"ISIN must be alphanumeric: {isin}")

    def test_required_categories_presence(self):
        """Must cover G-Sec, T-Bill, SGB, Corporate NCD, and Debt ETF."""
        categories = {s["category"] for s in BENCHMARK_SECURITIES}
        required_categories = {"G-Sec", "T-Bill", "SGB", "Corporate NCD", "Debt ETF"}
        self.assertTrue(
            required_categories.issubset(categories),
            f"Missing required categories: {required_categories - categories}",
        )

    def test_sovereign_guarantee_and_rating(self):
        """All G-Sec, T-Bill, and SGB must have Sovereign Guarantee and SOV rating."""
        sovereign_categories = {"G-Sec", "T-Bill", "SGB"}
        for s in BENCHMARK_SECURITIES:
            if s["category"] in sovereign_categories:
                self.assertEqual(
                    s["sovereign_guarantee"],
                    1,
                    f"Expected sovereign guarantee for {s['symbol']}",
                )
                self.assertEqual(
                    s["rating"],
                    "SOV",
                    f"Expected SOV rating for {s['symbol']}",
                )

    def test_sovereign_gold_bonds_attributes(self):
        """All SGBs must have fixed 2.50% coupon, 1.0g gold parity, and maturity date."""
        sgbs = [s for s in BENCHMARK_SECURITIES if s["category"] == "SGB"]
        self.assertGreaterEqual(len(sgbs), 5, "Expected at least 5 benchmark SGB issues")
        for sgb in sgbs:
            self.assertEqual(sgb["coupon_rate"], 2.50, f"SGB coupon must be 2.50%: {sgb['symbol']}")
            self.assertEqual(sgb["gold_grams"], 1.0, f"SGB gold parity weight must be 1.0g: {sgb['symbol']}")
            self.assertGreater(sgb["issue_price"], 0.0, f"SGB must have positive issue price: {sgb['symbol']}")
            self.assertIn("20", sgb["maturity_date"], f"SGB maturity date missing: {sgb['symbol']}")

    def test_corporate_ncd_seniority_tiers(self):
        """Corporate NCDs must cover Senior Secured (1.25x-1.50x asset cover), Secured, and Unsecured."""
        ncds = [s for s in BENCHMARK_SECURITIES if s["category"] == "Corporate NCD"]
        self.assertGreaterEqual(len(ncds), 10, "Expected at least 10 Corporate NCDs")

        seniorities = {n["seniority"] for n in ncds}
        self.assertIn("Senior Secured", seniorities)
        self.assertIn("Secured", seniorities)
        self.assertIn("Unsecured Subordinated", seniorities)

        senior_secured_aaa = [
            n for n in ncds if n["seniority"] == "Senior Secured" and "AAA" in n["rating"]
        ]
        self.assertGreaterEqual(len(senior_secured_aaa), 4)
        for s in senior_secured_aaa:
            self.assertIsNotNone(s["asset_cover_ratio"])
            self.assertGreaterEqual(
                s["asset_cover_ratio"],
                1.25,
                f"Senior Secured AAA must have asset cover >= 1.25x: {s['symbol']}",
            )

    def test_target_maturity_debt_etfs(self):
        """Must include Bharat Bond and Target Maturity ETFs with underlying index."""
        etfs = [s for s in BENCHMARK_SECURITIES if s["category"] == "Debt ETF"]
        self.assertGreaterEqual(len(etfs), 4, "Expected at least 4 target maturity debt ETFs")
        for etf in etfs:
            self.assertEqual(etf["coupon_rate"], 0.0, f"ETF coupon must be 0.0: {etf['symbol']}")
            self.assertGreater(etf["yield_to_maturity"], 0.0, f"ETF YTM must be positive: {etf['symbol']}")
            self.assertTrue(bool(etf["benchmark_index"]), f"ETF must specify benchmark index: {etf['symbol']}")


class TestSQLiteDatabaseMaterialization(unittest.TestCase):
    """Test suite for SQLite initialization, idempotency, querying, and summary."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_db_path = Path(self.temp_dir.name) / "test_debt_securities.db"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_db_auto_creation_and_row_count(self):
        """Database and table must be created with all seed rows."""
        db_path = init_embedded_db(self.temp_db_path)
        self.assertTrue(os.path.exists(db_path))

        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM securities")
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, len(BENCHMARK_SECURITIES))

    def test_idempotent_init(self):
        """Calling init_embedded_db multiple times must not duplicate records."""
        init_embedded_db(self.temp_db_path)
        init_embedded_db(self.temp_db_path)  # Second call without force_reseed

        conn = get_connection(self.temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM securities")
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, len(BENCHMARK_SECURITIES))

    def test_query_filtering(self):
        """query_securities must support filtering by category, risk, and asset cover."""
        init_embedded_db(self.temp_db_path)

        # Filter by category
        sgbs = query_securities(category="SGB", db_path=self.temp_db_path)
        self.assertTrue(all(s["category"] == "SGB" for s in sgbs))
        self.assertGreaterEqual(len(sgbs), 5)

        # Filter by sovereign guarantee
        sovereigns = query_securities(sovereign_only=True, db_path=self.temp_db_path)
        self.assertTrue(all(s["sovereign_guarantee"] == 1 for s in sovereigns))

        # Filter by minimum asset cover
        high_cover = query_securities(min_asset_cover=1.40, db_path=self.temp_db_path)
        self.assertTrue(all(s["asset_cover_ratio"] >= 1.40 for s in high_cover))

    def test_get_security_by_isin(self):
        """Lookup by ISIN should return exact match or None."""
        init_embedded_db(self.temp_db_path)

        sec = get_security_by_isin("IN0020230085", db_path=self.temp_db_path)
        self.assertIsNotNone(sec)
        self.assertEqual(sec["symbol"], "718GS2033")
        self.assertEqual(sec["category"], "G-Sec")

        missing = get_security_by_isin("INVALID_ISIN", db_path=self.temp_db_path)
        self.assertIsNone(missing)

    def test_get_db_summary(self):
        """get_db_summary must return valid aggregate metrics."""
        init_embedded_db(self.temp_db_path)

        summary = get_db_summary(db_path=self.temp_db_path)
        self.assertEqual(summary["total_securities"], len(BENCHMARK_SECURITIES))
        self.assertIn("Corporate NCD", summary["by_category"])
        self.assertIn("SGB", summary["by_category"])
        self.assertGreater(summary["avg_yield_to_maturity"], 5.0)


if __name__ == "__main__":
    unittest.main()
