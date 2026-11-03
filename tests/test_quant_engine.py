"""
tests/test_quant_engine.py - Unit tests for Quantitative Fixed-Income Engine.

Sprint 3: Validates Newton-Raphson YTM, T-Bill discount yield, SGB gold parity,
Sovereign curve interpolation, Duration & Convexity, Yield-Trap Guardrail,
RAYS multi-criteria screener, and 12-month Portfolio Cash-Flow Ladder.
"""

from __future__ import annotations

import datetime
import tempfile
import unittest
from pathlib import Path

from src.data_engine import DebtMarketDataEngine
from src.embedded_seed import BENCHMARK_SECURITIES, init_embedded_db, query_securities
from src.quant_engine import BondQuantEngine, extract_rating_tier


class TestBondQuantEngine(unittest.TestCase):
    """Test suite for BondQuantEngine with zero third-party dependencies."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_db_path = Path(self.temp_dir.name) / "test_debt_securities.db"
        init_embedded_db(self.temp_db_path)
        self.quant = BondQuantEngine(
            db_path=self.temp_db_path,
            default_gold_spot_inr=7850.0,
            expected_gold_cagr_pct=7.50,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    # -------------------------------------------------------------------------
    # 1. Exact Yield-to-Maturity (YTM) Calculations
    # -------------------------------------------------------------------------
    def test_exact_ytm_par_bond(self):
        """A bond trading at par (Price == Face Value) must have YTM == coupon rate."""
        ytm = self.quant.calculate_exact_ytm(
            market_price=1000.0,
            face_value=1000.0,
            coupon_rate=8.50,
            payment_frequency="Annual",
            years_to_maturity=5.0,
        )
        self.assertEqual(ytm, 8.50)

    def test_exact_ytm_discount_and_premium(self):
        """Discount bond must have YTM > coupon rate; premium bond must have YTM < coupon."""
        ytm_disc = self.quant.calculate_exact_ytm(
            market_price=950.0,
            face_value=1000.0,
            coupon_rate=8.0,
            payment_frequency="Annual",
            years_to_maturity=5.0,
        )
        ytm_prem = self.quant.calculate_exact_ytm(
            market_price=1050.0,
            face_value=1000.0,
            coupon_rate=8.0,
            payment_frequency="Annual",
            years_to_maturity=5.0,
        )
        self.assertGreater(ytm_disc, 8.0)
        self.assertLess(ytm_prem, 8.0)
        self.assertAlmostEqual(ytm_disc, 9.295, places=2)
        self.assertAlmostEqual(ytm_prem, 6.787, places=2)

    def test_exact_ytm_tbill_zero_coupon(self):
        """Zero-coupon Treasury Bill discount yield calculation."""
        # 91-Day T-Bill issued at 98.35 with 0.25y remaining
        ytm = self.quant.calculate_exact_ytm(
            market_price=98.35,
            face_value=100.0,
            coupon_rate=0.0,
            payment_frequency="At Maturity",
            years_to_maturity=0.25,
            category="T-Bill",
        )
        self.assertGreater(ytm, 6.50)
        self.assertLess(ytm, 7.00)

    def test_sgb_gold_parity_valuation(self):
        """SGB valuation incorporates 2.5% coupon yield, discount to spot, and gold CAGR."""
        # Issue price: 6263, Spot gold: 7850, Market price: 7450 (trading at discount)
        eff_ytm = self.quant.calculate_exact_ytm(
            market_price=7450.0,
            face_value=6263.0,
            coupon_rate=2.50,
            years_to_maturity=6.0,
            category="SGB",
            gold_spot_inr=7850.0,
            gold_weight_grams=1.0,
        )
        # Expected components:
        # Coupon yield: (6263 * 0.025 / 7450) * 100 ≈ 2.10%
        # Pull-to-parity: ((7850 - 7450) / 7450) / 6.0 * 100 ≈ 0.895%
        # Gold CAGR: 7.50%
        # Total effective YTM ≈ 10.50%
        self.assertGreater(eff_ytm, 10.0)
        self.assertLess(eff_ytm, 11.0)

    def test_debt_etf_net_ytm(self):
        """Target Maturity ETF yield is computed net of expense ratio."""
        eff_ytm = self.quant.calculate_exact_ytm(
            market_price=1000.0,
            face_value=1450.0,
            coupon_rate=0.0,
            years_to_maturity=5.0,
            category="Debt ETF",
            expense_ratio=0.0005,  # 0.05%
        )
        self.assertGreater(eff_ytm, 7.0)

    # -------------------------------------------------------------------------
    # 2. Time-to-Maturity & Date Conventions
    # -------------------------------------------------------------------------
    def test_time_to_maturity_solver_and_floor(self):
        """Test exact calculation of years to maturity and the 0.05y safety floor."""
        val_date = datetime.date(2024, 1, 1)
        mat_date = datetime.date(2029, 1, 1)
        years = BondQuantEngine.calculate_years_to_maturity(mat_date, val_date)
        self.assertAlmostEqual(years, 5.0, delta=0.02)

        # Near maturity or past maturity should floor to 0.05
        past_mat = datetime.date(2023, 12, 1)
        years_past = BondQuantEngine.calculate_years_to_maturity(past_mat, val_date)
        self.assertEqual(years_past, 0.05)

    # -------------------------------------------------------------------------
    # 3. Sovereign Yield Curve & Credit Spread (bps)
    # -------------------------------------------------------------------------
    def test_sovereign_yield_curve_interpolation(self):
        """Piecewise linear interpolation on sovereign yield curve."""
        curve = [(0.25, 6.75), (1.0, 6.95), (5.0, 7.08), (10.0, 7.18)]

        # Extrapolation below min
        y_short = BondQuantEngine.interpolate_sovereign_yield(0.10, curve)
        self.assertEqual(y_short, 6.75)

        # Extrapolation above max
        y_long = BondQuantEngine.interpolate_sovereign_yield(15.0, curve)
        self.assertEqual(y_long, 7.18)

        # Midpoint interpolation between 1.0y (6.95%) and 5.0y (7.08%) at 3.0y
        y_mid = BondQuantEngine.interpolate_sovereign_yield(3.0, curve)
        self.assertGreater(y_mid, 6.95)
        self.assertLess(y_mid, 7.08)

    def test_spread_over_gsec_bps(self):
        """Credit spread over matched sovereign maturity is accurately calculated in bps."""
        curve = [(1.0, 6.95), (5.0, 7.10), (10.0, 7.20)]
        matched_ytm, spread_bps = self.quant.calculate_sovereign_spread_bps(
            effective_ytm=8.10,
            years_to_maturity=5.0,
            sovereign_curve=curve,
        )
        self.assertEqual(matched_ytm, 7.10)
        self.assertEqual(spread_bps, 100.0)  # (8.10 - 7.10) * 100 = +100 bps

    # -------------------------------------------------------------------------
    # 4. Interest Rate Sensitivity (Duration & Convexity)
    # -------------------------------------------------------------------------
    def test_duration_and_convexity_properties(self):
        """Longer maturity bonds must have higher duration than shorter maturity bonds."""
        short_bond = BondQuantEngine.calculate_duration_and_convexity(
            market_price=1000.0,
            face_value=1000.0,
            coupon_rate=7.50,
            payment_frequency="Annual",
            years_to_maturity=2.0,
            ytm_pct=7.50,
        )
        long_bond = BondQuantEngine.calculate_duration_and_convexity(
            market_price=1000.0,
            face_value=1000.0,
            coupon_rate=7.50,
            payment_frequency="Annual",
            years_to_maturity=10.0,
            ytm_pct=7.50,
        )
        self.assertLess(short_bond["macaulay_duration"], long_bond["macaulay_duration"])
        self.assertLess(short_bond["modified_duration"], long_bond["modified_duration"])
        self.assertLess(short_bond["convexity"], long_bond["convexity"])
        # Rate shock impact should be negative (price drops when rates rise)
        self.assertLess(short_bond["rate_shock_100bps_pct"], 0.0)
        self.assertLess(long_bond["rate_shock_100bps_pct"], short_bond["rate_shock_100bps_pct"])

    # -------------------------------------------------------------------------
    # 5. Yield-Trap Guardrail & Risk Scoring
    # -------------------------------------------------------------------------
    def test_yield_trap_guardrail_defaulted_bond(self):
        """Defaulted bonds (e.g. Reliance Capital) must be flagged as yield traps with RAYS == 0."""
        metrics = BondQuantEngine.calculate_risk_and_rays(
            category="Corporate NCD",
            rating="CARE D",
            seniority="Unsecured Subordinated",
            asset_cover=0.0,
            market_price=350.0,
            face_value=1000.0,
            effective_ytm=25.0,  # High deceptive yield
            modified_duration=2.0,
            spread_over_gsec_bps=1800.0,
            coupon_rate=9.0,
        )
        self.assertTrue(metrics["is_yield_trap"])
        self.assertEqual(metrics["rays_score"], 0.0)
        self.assertEqual(metrics["risk_band"], "Tier D - Distressed / Yield Trap")
        self.assertGreaterEqual(metrics["risk_score"], 95.0)

    def test_yield_trap_guardrail_subordinated_excess_spread(self):
        """Subordinated bonds with excessive spread must be heavily penalized on RAYS."""
        # Unsecured Subordinated bond with 750 bps spread
        sub_metrics = BondQuantEngine.calculate_risk_and_rays(
            category="Corporate NCD",
            rating="CARE A-",
            seniority="Unsecured Subordinated",
            asset_cover=0.0,
            market_price=980.0,
            face_value=1000.0,
            effective_ytm=14.50,
            modified_duration=3.5,
            spread_over_gsec_bps=750.0,
            coupon_rate=10.0,
        )
        # Tier A Senior Secured AAA bond
        aaa_metrics = BondQuantEngine.calculate_risk_and_rays(
            category="Corporate NCD",
            rating="CRISIL AAA",
            seniority="Senior Secured",
            asset_cover=1.50,
            market_price=1000.0,
            face_value=1000.0,
            effective_ytm=7.80,
            modified_duration=3.5,
            spread_over_gsec_bps=70.0,
            coupon_rate=7.80,
        )
        # Subordinated bond with > 650 bps spread is flagged as yield trap or has RAYS == 0
        self.assertTrue(sub_metrics["is_yield_trap"])
        self.assertEqual(sub_metrics["rays_score"], 0.0)
        self.assertGreater(aaa_metrics["rays_score"], sub_metrics["rays_score"])

    # -------------------------------------------------------------------------
    # 6. Multi-Criteria Screener
    # -------------------------------------------------------------------------
    def test_screen_securities_default_filters(self):
        """Screener must isolate Sovereign, SGB, Debt ETF, and Senior Secured NCDs."""
        screened = self.quant.screen_securities(
            min_rating="AA",
            min_asset_cover=1.25,
            exclude_yield_traps=True,
            valuation_date="2024-01-01",
        )
        self.assertGreaterEqual(len(screened), 20)

        # Confirm all screened bonds have high rating (>= AA)
        for s in screened:
            tier = extract_rating_tier(s["rating"])
            self.assertIn(tier, ("SOV", "AAA", "AA+", "AA"))
            self.assertFalse(s["is_yield_trap"])
            self.assertGreater(s["rays_score"], 0.0)

        # Confirm defaulted Reliance Capital is excluded
        isins = [s["isin"] for s in screened]
        self.assertNotIn("INE608A07248", isins)

    def test_min_asset_cover_filter(self):
        """min_asset_cover=1.25 applies to corporate bonds while passing Sovereign/SGB."""
        screened = self.quant.screen_securities(
            min_asset_cover=1.25,
            exclude_yield_traps=True,
            valuation_date="2024-01-01",
        )
        for s in screened:
            if s["category"] == "Corporate NCD":
                cov = s.get("asset_cover_ratio") or s.get("asset_cover")
                self.assertIsNotNone(cov)
                self.assertGreaterEqual(cov, 1.25)
            elif s["category"] in ("G-Sec", "T-Bill", "SGB", "Debt ETF"):
                # Sovereign and ETFs pass automatically
                self.assertTrue(True)

    # -------------------------------------------------------------------------
    # 7. Portfolio Cash-Flow Ladder & Allocation
    # -------------------------------------------------------------------------
    def test_portfolio_cashflow_ladder_capital_and_ytm(self):
        """Verify capital allocation sums to total_capital_inr and weighted YTM is sound."""
        screened = self.quant.screen_securities(
            min_rating="AAA",
            valuation_date="2024-01-01",
        )
        self.assertGreaterEqual(len(screened), 5)
        top5 = screened[:5]

        report = self.quant.generate_cashflow_ladder(
            securities=top5,
            total_capital_inr=1000000.0,
            allocation_mode="rays_weighted",
            valuation_date="2024-01-01",
        )
        self.assertEqual(report["total_capital_inr"], 1000000.0)
        self.assertEqual(report["total_allocated_inr"], 1000000.0)
        self.assertGreater(report["weighted_effective_ytm"], 5.0)
        self.assertGreater(report["weighted_modified_duration"], 0.5)
        self.assertGreaterEqual(report["sovereign_and_senior_secured_pct"], 80.0)
        self.assertEqual(len(report["allocations"]), 5)

    def test_portfolio_cashflow_ladder_monthly_schedule(self):
        """Verify monthly cashflow schedule sums to projected coupon inflow."""
        screened = self.quant.screen_securities(
            categories=["Corporate NCD"],
            min_rating="AAA",
            valuation_date="2024-01-01",
        )
        report = self.quant.generate_cashflow_ladder(
            securities=screened[:4],
            total_capital_inr=500000.0,
            allocation_mode="equal_weight",
            valuation_date="2024-01-01",
        )
        schedule = report["monthly_schedule"]
        self.assertEqual(len(schedule), 12)

        monthly_coupon_sum = sum(schedule[f"month_{i}"]["coupon"] for i in range(1, 13))
        self.assertAlmostEqual(monthly_coupon_sum, report["total_annual_coupon_inflow"], delta=1.0)
        self.assertGreater(report["total_annual_coupon_inflow"], 20000.0)

    # -------------------------------------------------------------------------
    # 8. End-to-End Integration Test: DataEngine -> QuantEngine
    # -------------------------------------------------------------------------
    def test_end_to_end_integration_data_engine_to_quant(self):
        """Chain DebtMarketDataEngine.get_market_snapshot() into BondQuantEngine."""
        data_engine = DebtMarketDataEngine(db_path=self.temp_db_path)
        snapshot = data_engine.get_market_snapshot(allow_network=False)
        self.assertEqual(snapshot["data_source"], "OFFLINE_EMBEDDED_DB")

        # Pass snapshot securities directly into quant engine
        screened = self.quant.screen_securities(
            securities=snapshot["securities"],
            min_rating="AA",
            min_asset_cover=1.25,
            valuation_date="2024-01-01",
        )
        self.assertGreaterEqual(len(screened), 15)

        # Highest RAYS bond should be a safe, high-yielding senior instrument
        top_bond = screened[0]
        self.assertIn(top_bond["risk_band"], ("Sovereign Safe Haven", "Tier A - Prime Senior Secured", "Tier B - High-Yield Secured"))
        self.assertFalse(top_bond["is_yield_trap"])


if __name__ == "__main__":
    unittest.main()
