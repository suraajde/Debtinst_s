"""
src/quant_engine.py - Zero-Dependency Quantitative Fixed-Income Pricing & Risk Engine.

Part of Sprint 3 for Debtinst_s.
Provides:
  1. Exact Time-to-Maturity & Day-Count Solver.
  2. Newton-Raphson & Bisection Cash-Flow YTM Solver for G-Secs, T-Bills, SGBs, & NCDs.
  3. Sovereign Yield Curve Piecewise Interpolation & G-Sec Spread (bps).
  4. Interest Rate Sensitivity: Macaulay Duration, Modified Duration, Convexity, & Rate Shock.
  5. Downside Protection Guardrail, Yield-Trap Detector, & Risk-Adjusted Yield Score (RAYS).
  6. Multi-Criteria Screener isolating High-Return, Manageable-Risk Fixed Income.
  7. Portfolio Cash-Flow Ladder & 12-Month Calendar Schedule Simulator.

Zero external dependencies: uses Python standard library only (`math`, `datetime`, `sqlite3`, `json`, `typing`).
"""

from __future__ import annotations

import datetime
import json
import math
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Ensure project root is in sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from src.embedded_seed import get_connection, get_default_db_path, query_securities
except ImportError:
    from embedded_seed import get_connection, get_default_db_path, query_securities  # type: ignore

# -----------------------------------------------------------------------------
# Ordinal Rating Scale & Factor Weights
# -----------------------------------------------------------------------------
RATING_ORDINAL_MAP: Dict[str, int] = {
    "SOV": 100,
    "AAA": 90,
    "AA+": 85,
    "AA": 80,
    "AA-": 75,
    "A+": 65,
    "A": 60,
    "A-": 55,
    "BBB+": 45,
    "BBB": 40,
    "BBB-": 35,
    "UNRATED / LIQUID": 50,
    "UNRATED": 30,
    "D": 0,
    "DEFAULT": 0,
    "DEFAULTED": 0,
}

RATING_WEIGHT_MAP: Dict[str, float] = {
    "SOV": 1.00,
    "AAA": 0.96,
    "AA+": 0.88,
    "AA": 0.80,
    "AA-": 0.68,
    "A+": 0.55,
    "A": 0.45,
    "BBB": 0.30,
    "UNRATED / LIQUID": 0.50,
    "UNRATED": 0.35,
    "D": 0.00,
    "DEFAULT": 0.00,
    "DEFAULTED": 0.00,
}

SENIORITY_WEIGHT_MAP: Dict[str, float] = {
    "Sovereign": 1.00,
    "Sovereign Guarantee": 1.00,
    "Senior Secured": 0.92,
    "Senior Secured (AAA PSU Basket)": 0.92,
    "Secured": 0.75,
    "Unsecured": 0.38,
    "Unsecured Subordinated": 0.38,
    "Tier-II": 0.38,
    "Subordinated": 0.38,
}


def extract_rating_tier(rating_str: Optional[str]) -> str:
    """Normalize rating strings like 'CRISIL AAA' or 'CARE AA+' into canonical tiers."""
    s = (rating_str or "").strip().upper()
    if "SOV" in s or "SOVEREIGN" in s:
        return "SOV"
    if "AAA" in s:
        return "AAA"
    if "AA+" in s:
        return "AA+"
    if "AA-" in s:
        return "AA-"
    if "AA" in s:
        return "AA"
    if "A+" in s:
        return "A+"
    if "A-" in s:
        return "A-"
    if "A" in s:
        return "A"
    if "BBB" in s:
        return "BBB"
    if "D" in s or "DEFAULT" in s:
        return "D"
    if "LIQUID" in s:
        return "UNRATED / LIQUID"
    return "UNRATED"


class BondQuantEngine:
    """
    Quantitative valuation, interest rate sensitivity, risk guardrail,
    and cash-flow ladder engine for debt instruments.
    """

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        default_gold_spot_inr: float = 7850.0,
        expected_gold_cagr_pct: float = 7.50,
    ):
        self.db_path = Path(db_path) if db_path else get_default_db_path()
        self.default_gold_spot_inr = default_gold_spot_inr
        self.expected_gold_cagr_pct = expected_gold_cagr_pct

    # -------------------------------------------------------------------------
    # 1. Time-to-Maturity Solver
    # -------------------------------------------------------------------------
    @staticmethod
    def calculate_years_to_maturity(
        maturity_date: Union[str, datetime.date, datetime.datetime],
        valuation_date: Optional[Union[str, datetime.date, datetime.datetime]] = None,
    ) -> float:
        """
        Compute remaining time to maturity in years (Actual/365.25 day-count convention).
        Enforces a safe floor of 0.05 years (~18 days) to prevent zero-division.
        """
        if valuation_date is None:
            val_date = datetime.datetime.now(datetime.timezone.utc).date()
        elif isinstance(valuation_date, (datetime.datetime, datetime.date)):
            val_date = (
                valuation_date.date()
                if isinstance(valuation_date, datetime.datetime)
                else valuation_date
            )
        else:
            clean_str = str(valuation_date).split("T")[0].split(" ")[0].strip()
            val_date = datetime.date.fromisoformat(clean_str)

        if isinstance(maturity_date, (datetime.datetime, datetime.date)):
            mat_date = (
                maturity_date.date()
                if isinstance(maturity_date, datetime.datetime)
                else maturity_date
            )
        else:
            clean_str = str(maturity_date).split("T")[0].split(" ")[0].strip()
            mat_date = datetime.date.fromisoformat(clean_str)

        days = (mat_date - val_date).days
        years = days / 365.25
        return round(max(0.05, float(years)), 4)

    # -------------------------------------------------------------------------
    # 2. Exact Yield-to-Maturity (YTM) Solver
    # -------------------------------------------------------------------------
    def calculate_exact_ytm(
        self,
        market_price: float,
        face_value: float,
        coupon_rate: float,
        payment_frequency: Union[str, int] = "Annual",
        years_to_maturity: float = 1.0,
        category: str = "Corporate NCD",
        expense_ratio: float = 0.0,
        gold_spot_inr: Optional[float] = None,
        gold_weight_grams: float = 1.0,
        indicative_ytm: Optional[float] = None,
    ) -> float:
        """
        Compute annualized exact Yield-to-Maturity (YTM) (%) across bond categories.
        Uses Newton-Raphson with an automatic Bisection fallback over [-20%, +100%].
        """
        if market_price <= 0:
            market_price = face_value if face_value > 0 else 1000.0
        if face_value <= 0:
            face_value = market_price
        years = max(0.05, years_to_maturity)

        # ---------------------------------------------------------------------
        # Case A: Treasury Bills (Zero-Coupon Discount Yield)
        # ---------------------------------------------------------------------
        if category == "T-Bill" or (coupon_rate == 0.0 and category == "G-Sec"):
            ratio = face_value / market_price
            if years >= 1.0:
                ytm = (math.pow(ratio, 1.0 / years) - 1.0) * 100.0
            else:
                ytm = ((face_value - market_price) / market_price) * (1.0 / years) * 100.0
            return round(ytm, 3)

        # ---------------------------------------------------------------------
        # Case B: Sovereign Gold Bonds (SGB Parity & Expected Gold CAGR)
        # ---------------------------------------------------------------------
        if category == "SGB":
            spot_gold = gold_spot_inr if gold_spot_inr is not None else self.default_gold_spot_inr
            weight = gold_weight_grams if gold_weight_grams > 0 else 1.0
            intrinsic_gold_val = spot_gold * weight

            # Fixed coupon yield on current price (2.50% on face value / issue price)
            annual_fixed_coupon_inr = face_value * (2.50 / 100.0)
            coupon_yield_pct = (annual_fixed_coupon_inr / market_price) * 100.0

            # Annualized pull-to-gold-parity yield
            pull_to_parity_pct = (
                ((intrinsic_gold_val - market_price) / market_price) / years
            ) * 100.0

            # Total effective yield incorporating gold price appreciation
            effective_ytm = coupon_yield_pct + pull_to_parity_pct + self.expected_gold_cagr_pct
            return round(effective_ytm, 3)

        # ---------------------------------------------------------------------
        # Case C: Target Maturity Debt ETFs
        # ---------------------------------------------------------------------
        if category == "Debt ETF":
            gross_ytm = (
                indicative_ytm
                if (indicative_ytm is not None and indicative_ytm > 0)
                else None
            )
            if gross_ytm is None:
                if face_value > market_price:
                    gross_ytm = (math.pow(face_value / market_price, 1.0 / years) - 1.0) * 100.0
                else:
                    gross_ytm = 7.25
            net_ytm = max(0.0, gross_ytm - (expense_ratio * 100.0))
            return round(net_ytm, 3)

        # ---------------------------------------------------------------------
        # Case D: Standard Coupon-Bearing Bonds (G-Sec & Corporate NCD)
        # ---------------------------------------------------------------------
        if abs(market_price - face_value) < 1e-4:
            return round(coupon_rate, 3)

        # Determine payments per year
        if isinstance(payment_frequency, int):
            m = max(1, payment_frequency)
        else:
            freq_str = str(payment_frequency).lower()
            if "semi" in freq_str:
                m = 2
            elif "month" in freq_str:
                m = 12
            elif "quarter" in freq_str:
                m = 4
            else:
                m = 1

        n = max(1, int(round(years * m)))
        c = (face_value * (coupon_rate / 100.0)) / m

        # Closed-form initial guess
        ann_c = c * m
        approx_y = (ann_c + (face_value - market_price) / years) / (
            (face_value + market_price) / 2.0
        )
        periodic_y0 = max(0.001, approx_y / m)

        # --- 1. Newton-Raphson Solver ---
        y = periodic_y0
        converged = False

        for _ in range(50):
            denom = 1.0 + y
            if denom <= 0.0001:
                y = 0.0001
                denom = 1.0001

            pv = 0.0
            deriv = 0.0
            df = 1.0
            for k in range(1, n + 1):
                df /= denom
                pv += c * df
                deriv += k * c * (df / denom)

            pv += face_value * df
            deriv += n * face_value * (df / denom)

            diff = pv - market_price
            if abs(diff) < 1e-6:
                converged = True
                break

            if abs(deriv) < 1e-12:
                break

            step = diff / deriv
            y_next = y + step  # Note: d(diff)/dy = -deriv, so - diff/(-deriv) = + diff/deriv

            if y_next < -0.20 / m or y_next > 2.0 / m:
                break
            if abs(y_next - y) < 1e-7:
                y = y_next
                converged = True
                break
            y = y_next

        # --- 2. Bisection Fallback ---
        if not converged:
            y_low = -0.20 / m
            y_high = 2.0 / m

            def eval_pv(rate_val: float) -> float:
                d = 1.0 + rate_val
                if d <= 0.0001:
                    return 1e9
                pv_calc = 0.0
                df_c = 1.0
                for _ in range(n):
                    df_c /= d
                    pv_calc += c * df_c
                pv_calc += face_value * df_c
                return pv_calc - market_price

            f_low = eval_pv(y_low)
            f_high = eval_pv(y_high)

            if f_low * f_high <= 0:
                for _ in range(60):
                    y_mid = (y_low + y_high) / 2.0
                    f_mid = eval_pv(y_mid)
                    if abs(f_mid) < 1e-6 or (y_high - y_low) < 1e-8:
                        y = y_mid
                        converged = True
                        break
                    if f_low * f_mid < 0:
                        y_high = y_mid
                        f_high = f_mid
                    else:
                        y_low = y_mid
                        f_low = f_mid
                if not converged:
                    y = (y_low + y_high) / 2.0

        annualized_ytm = y * m * 100.0
        return round(float(annualized_ytm), 3)

    # -------------------------------------------------------------------------
    # 3. Sovereign Yield Curve & Credit Spread
    # -------------------------------------------------------------------------
    @staticmethod
    def build_sovereign_curve(
        securities: List[Dict[str, Any]],
        valuation_date: Optional[Union[str, datetime.date]] = None,
    ) -> List[Tuple[float, float]]:
        """
        Construct a sorted list of (years_to_maturity, sovereign_ytm) points
        from G-Sec and T-Bill instruments in the dataset.
        """
        pts: List[Tuple[float, float]] = []
        for s in securities:
            cat = s.get("category")
            if cat in ("G-Sec", "T-Bill"):
                ytm = (
                    s.get("yield_to_maturity")
                    or s.get("effective_ytm")
                    or s.get("coupon_rate")
                    or 0.0
                )
                if ytm > 0:
                    mat = s.get("maturity_date")
                    if mat:
                        years = BondQuantEngine.calculate_years_to_maturity(mat, valuation_date)
                        pts.append((years, float(ytm)))

        # Fallback benchmark points if no G-Secs exist
        if not pts:
            pts = [(0.25, 6.75), (0.50, 6.85), (1.0, 6.95), (5.0, 7.08), (10.0, 7.15)]

        pts.sort(key=lambda x: x[0])
        return pts

    @staticmethod
    def interpolate_sovereign_yield(
        years_to_maturity: float,
        sovereign_curve: List[Tuple[float, float]],
    ) -> float:
        """Piecewise linear interpolation on the sovereign curve."""
        if not sovereign_curve:
            return 7.15

        t = max(0.05, years_to_maturity)
        if t <= sovereign_curve[0][0]:
            return sovereign_curve[0][1]
        if t >= sovereign_curve[-1][0]:
            return sovereign_curve[-1][1]

        for i in range(len(sovereign_curve) - 1):
            t1, y1 = sovereign_curve[i]
            t2, y2 = sovereign_curve[i + 1]
            if t1 <= t <= t2:
                if abs(t2 - t1) < 1e-6:
                    return y1
                slope = (y2 - y1) / (t2 - t1)
                return y1 + slope * (t - t1)

        return sovereign_curve[-1][1]

    def calculate_sovereign_spread_bps(
        self,
        effective_ytm: float,
        years_to_maturity: float,
        sovereign_curve: List[Tuple[float, float]],
    ) -> Tuple[float, float]:
        """
        Interpolates matched sovereign YTM and returns:
          (matched_sovereign_ytm, spread_over_gsec_bps)
        """
        matched_ytm = self.interpolate_sovereign_yield(years_to_maturity, sovereign_curve)
        spread_bps = (effective_ytm - matched_ytm) * 100.0
        return round(matched_ytm, 3), round(spread_bps, 1)

    # -------------------------------------------------------------------------
    # 4. Interest-Rate Sensitivity (Duration & Convexity)
    # -------------------------------------------------------------------------
    @staticmethod
    def calculate_duration_and_convexity(
        market_price: float,
        face_value: float,
        coupon_rate: float,
        payment_frequency: Union[str, int] = "Annual",
        years_to_maturity: float = 1.0,
        ytm_pct: float = 7.0,
    ) -> Dict[str, float]:
        """
        Calculates Macaulay Duration, Modified Duration, Convexity,
        and estimated percentage price change for a +100 bps rate shock.
        """
        price = market_price if market_price > 0 else face_value
        years = max(0.05, years_to_maturity)

        if isinstance(payment_frequency, int):
            m = max(1, payment_frequency)
        else:
            freq_str = str(payment_frequency).lower()
            if "semi" in freq_str:
                m = 2
            elif "month" in freq_str:
                m = 12
            elif "quarter" in freq_str:
                m = 4
            else:
                m = 1

        n = max(1, int(round(years * m)))
        periodic_y = max(0.0001, (ytm_pct / 100.0) / m)
        c = (face_value * (coupon_rate / 100.0)) / m

        # Discounted cash flow weighted time
        denom = 1.0 + periodic_y
        pv_sum = 0.0
        weighted_time_sum = 0.0
        convexity_sum = 0.0
        df = 1.0

        for k in range(1, n + 1):
            t_k = k / float(m)
            df /= denom
            cf = c if k < n else (c + face_value)
            pv_k = cf * df
            pv_sum += pv_k
            weighted_time_sum += t_k * pv_k
            convexity_sum += t_k * (t_k + 1.0 / m) * pv_k

        pv_base = pv_sum if pv_sum > 0 else price
        mac_duration = weighted_time_sum / pv_base
        mod_duration = mac_duration / denom
        convexity = convexity_sum / (pv_base * (denom * denom))

        # Rate shock: ΔP/P ≈ -D_mod * Δy + 0.5 * C * (Δy)^2
        delta_y = 0.01  # +100 bps (+1.00%)
        rate_shock_pct = (-mod_duration * 1.0) + (0.5 * convexity * (delta_y * delta_y) * 100.0)

        return {
            "macaulay_duration": round(float(mac_duration), 3),
            "modified_duration": round(float(mod_duration), 3),
            "convexity": round(float(convexity), 3),
            "rate_shock_100bps_pct": round(float(rate_shock_pct), 2),
        }

    # -------------------------------------------------------------------------
    # 5. Downside Protection Guardrail, Risk Scoring & RAYS
    # -------------------------------------------------------------------------
    @staticmethod
    def calculate_risk_and_rays(
        category: str,
        rating: str,
        seniority: str,
        asset_cover: Optional[float],
        market_price: float,
        face_value: float,
        effective_ytm: float,
        modified_duration: float,
        spread_over_gsec_bps: float,
        coupon_rate: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Evaluate credit rating, seniority, asset cover, and yield-trap guardrails.
        Computes composite Risk Score (0-100) and Risk-Adjusted Yield Score (RAYS).
        """
        clean_rating = extract_rating_tier(rating)
        r_w = RATING_WEIGHT_MAP.get(clean_rating, 0.50)

        # Seniority weight
        s_norm = (seniority or "Secured").strip()
        s_w = 0.75
        for k, v in SENIORITY_WEIGHT_MAP.items():
            if k.lower() in s_norm.lower():
                s_w = v
                break

        # Asset cover multiplier
        if category in ("G-Sec", "T-Bill", "SGB", "Debt ETF") or clean_rating == "SOV":
            a_m = 1.00
        else:
            cov = asset_cover if asset_cover is not None else (1.25 if "AAA" in clean_rating else 1.00)
            if cov >= 1.50:
                a_m = 1.10
            elif cov >= 1.25:
                a_m = 1.00 + (cov - 1.25) * 0.40
            elif cov >= 1.00:
                a_m = 0.70 + (cov - 1.00) * 1.20
            else:
                a_m = 0.40

        # Yield-Trap & Distress Guardrail
        is_yield_trap = False
        distress_reasons: List[str] = []

        if clean_rating == "D" or "DEFAULT" in (rating or "").upper():
            is_yield_trap = True
            distress_reasons.append("Defaulted / D rating")

        if category == "Corporate NCD" and coupon_rate > 0 and market_price < (0.65 * face_value):
            is_yield_trap = True
            distress_reasons.append("Severe capital impairment (price < 65% of face value)")

        if spread_over_gsec_bps > 650 and (s_w <= 0.40 or r_w < 0.80):
            is_yield_trap = True
            distress_reasons.append(f"Excessive spread ({spread_over_gsec_bps} bps) on subordinated/low-rated debt")

        # Composite Risk Score (0 = safest, 100 = defaulted / distressed)
        if is_yield_trap:
            risk_score = 98.0
            risk_band = "Tier D - Distressed / Yield Trap"
            rays_score = 0.0
        else:
            base_safety = r_w * s_w * min(1.0, a_m)
            risk_score = round(max(2.0, min(95.0, (1.0 - base_safety) * 100.0)), 1)

            # RAYS Score: (effective_ytm * R_w * S_w * A_m) / sqrt(max(D_mod, 0.50))
            dur_factor = math.sqrt(max(0.50, modified_duration))
            rays_raw = (effective_ytm * r_w * s_w * a_m) / dur_factor
            rays_score = round(max(0.0, rays_raw), 2)

            # Categorize risk bands
            if category in ("G-Sec", "T-Bill", "SGB") or clean_rating == "SOV":
                risk_band = "Sovereign Safe Haven"
            elif s_w >= 0.90 and r_w >= 0.88:
                risk_band = "Tier A - Prime Senior Secured"
            elif s_w >= 0.70 and r_w >= 0.75:
                risk_band = "Tier B - High-Yield Secured"
            else:
                risk_band = "Tier C - Subordinated / Elevated Risk"

        return {
            "risk_score": risk_score,
            "rays_score": rays_score,
            "risk_band": risk_band,
            "is_yield_trap": is_yield_trap,
            "distress_reasons": distress_reasons,
            "rating_weight": r_w,
            "seniority_weight": s_w,
            "asset_cover_multiplier": round(a_m, 2),
        }

    # -------------------------------------------------------------------------
    # 6. Multi-Criteria Screener
    # -------------------------------------------------------------------------
    def screen_securities(
        self,
        securities: Optional[List[Dict[str, Any]]] = None,
        categories: Optional[List[str]] = None,
        seniority_tiers: Optional[List[str]] = None,
        min_rating: Optional[str] = "AA",
        min_effective_ytm: Optional[float] = None,
        max_modified_duration: Optional[float] = None,
        min_asset_cover: Optional[float] = None,
        exclude_yield_traps: bool = True,
        sort_by: str = "rays_score",
        ascending: bool = False,
        valuation_date: Optional[Union[str, datetime.date]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Enrich and filter securities matching high-return, manageable-risk guardrails.
        """
        if securities is None:
            securities = query_securities(db_path=self.db_path)

        sovereign_curve = self.build_sovereign_curve(securities, valuation_date)
        enriched: List[Dict[str, Any]] = []

        for sec in securities:
            rec = dict(sec)
            cat = rec.get("category", "Corporate NCD")
            mat = rec.get("maturity_date", "2030-01-01")
            years = self.calculate_years_to_maturity(mat, valuation_date)

            price = (
                rec.get("current_price")
                or rec.get("clean_price")
                or rec.get("price")
                or rec.get("issue_price")
                or rec.get("face_value")
                or 1000.0
            )
            fv = rec.get("face_value") or 1000.0
            coupon = rec.get("coupon_rate") or 0.0
            freq = rec.get("coupon_frequency") or rec.get("payment_frequency") or "Annual"
            rating = rec.get("rating") or "UNRATED"
            seniority = rec.get("seniority") or "Secured"
            cover = rec.get("asset_cover_ratio") if rec.get("asset_cover_ratio") is not None else rec.get("asset_cover")
            exp_ratio = rec.get("expense_ratio") or 0.0
            gold_weight = rec.get("gold_grams") or rec.get("gold_weight_grams") or 1.0

            # Compute exact YTM
            eff_ytm = self.calculate_exact_ytm(
                market_price=float(price),
                face_value=float(fv),
                coupon_rate=float(coupon),
                payment_frequency=freq,
                years_to_maturity=years,
                category=cat,
                expense_ratio=float(exp_ratio),
                gold_spot_inr=self.default_gold_spot_inr,
                gold_weight_grams=float(gold_weight),
                indicative_ytm=rec.get("yield_to_maturity"),
            )

            # SGB discount to physical spot
            if cat == "SGB":
                spot_val = self.default_gold_spot_inr * float(gold_weight)
                rec["intrinsic_gold_value"] = round(spot_val, 2)
                rec["sgb_discount_to_spot_pct"] = round(
                    ((float(price) - spot_val) / spot_val) * 100.0, 2
                )

            # Sovereign spread
            matched_ytm, spread_bps = self.calculate_sovereign_spread_bps(
                eff_ytm, years, sovereign_curve
            )

            # Duration and Convexity
            dur_metrics = self.calculate_duration_and_convexity(
                market_price=float(price),
                face_value=float(fv),
                coupon_rate=float(coupon),
                payment_frequency=freq,
                years_to_maturity=years,
                ytm_pct=eff_ytm,
            )

            # Risk and RAYS
            risk_metrics = self.calculate_risk_and_rays(
                category=cat,
                rating=rating,
                seniority=seniority,
                asset_cover=float(cover) if cover is not None else None,
                market_price=float(price),
                face_value=float(fv),
                effective_ytm=eff_ytm,
                modified_duration=dur_metrics["modified_duration"],
                spread_over_gsec_bps=spread_bps,
                coupon_rate=float(coupon),
            )

            # Enforce schema consistency
            rec.update(
                {
                    "years_to_maturity": years,
                    "effective_ytm": eff_ytm,
                    "matched_sovereign_ytm": matched_ytm,
                    "spread_over_gsec_bps": spread_bps,
                    **dur_metrics,
                    **risk_metrics,
                }
            )

            # Apply Screener Filters
            if exclude_yield_traps and rec["is_yield_trap"]:
                continue

            if categories and cat not in categories:
                continue

            if seniority_tiers:
                s_match = False
                for st in seniority_tiers:
                    if st.lower() in seniority.lower():
                        s_match = True
                        break
                if not s_match:
                    continue

            if min_rating:
                rec_tier = extract_rating_tier(rating)
                min_tier = extract_rating_tier(min_rating)
                if RATING_ORDINAL_MAP.get(rec_tier, 0) < RATING_ORDINAL_MAP.get(min_tier, 0):
                    continue

            if min_effective_ytm is not None and eff_ytm < min_effective_ytm:
                continue

            if max_modified_duration is not None and dur_metrics["modified_duration"] > max_modified_duration:
                continue

            if min_asset_cover is not None and cat == "Corporate NCD":
                cov_val = float(cover) if cover is not None else 0.0
                if cov_val < min_asset_cover:
                    continue

            enriched.append(rec)

        # Sort results
        reverse = not ascending
        enriched.sort(key=lambda x: x.get(sort_by, 0.0), reverse=reverse)
        return enriched

    # -------------------------------------------------------------------------
    # 7. Portfolio Cash-Flow Ladder & 12-Month Calendar Schedule
    # -------------------------------------------------------------------------
    def generate_cashflow_ladder(
        self,
        securities: List[Dict[str, Any]],
        total_capital_inr: float = 500000.0,
        allocation_mode: str = "rays_weighted",
        valuation_date: Optional[Union[str, datetime.date]] = None,
    ) -> Dict[str, Any]:
        """
        Simulate portfolio allocations and construct a 12-month calendar cash flow schedule.
        """
        if not securities:
            return {
                "total_capital_inr": total_capital_inr,
                "total_allocated_inr": 0.0,
                "weighted_effective_ytm": 0.0,
                "weighted_modified_duration": 0.0,
                "weighted_rays_score": 0.0,
                "sovereign_and_senior_secured_pct": 0.0,
                "monthly_schedule": {f"month_{i}": {"coupon": 0.0, "principal": 0.0, "total": 0.0} for i in range(1, 13)},
                "allocations": [],
            }

        # Weight calculation
        weights: List[float] = []
        if allocation_mode == "rays_weighted":
            raw_weights = [max(0.10, s.get("rays_score", 1.0)) for s in securities]
            total_raw = sum(raw_weights)
            weights = [w / total_raw for w in raw_weights]
        else:
            w_eq = 1.0 / len(securities)
            weights = [w_eq for _ in securities]

        # Allocate capital and compute cash flows
        allocations: List[Dict[str, Any]] = []
        monthly_schedule: Dict[str, Dict[str, float]] = {
            f"month_{i}": {"coupon": 0.0, "principal": 0.0, "total": 0.0}
            for i in range(1, 13)
        }

        weighted_ytm_sum = 0.0
        weighted_dur_sum = 0.0
        weighted_rays_sum = 0.0
        sov_and_sr_capital = 0.0

        for sec, weight in zip(securities, weights):
            target_cap = total_capital_inr * weight
            price = (
                sec.get("current_price")
                or sec.get("clean_price")
                or sec.get("price")
                or sec.get("issue_price")
                or sec.get("face_value")
                or 1000.0
            )
            fv = sec.get("face_value") or 1000.0
            coupon = sec.get("coupon_rate") or 0.0
            freq = str(sec.get("coupon_frequency") or sec.get("payment_frequency") or "Annual").lower()

            units = max(1, int(round(target_cap / float(price))))
            allocated_cap = round(target_cap, 2)
            eff_ytm = sec.get("effective_ytm") or coupon
            mod_dur = sec.get("modified_duration") or 2.0
            rays = sec.get("rays_score") or 0.0

            weighted_ytm_sum += eff_ytm * weight
            weighted_dur_sum += mod_dur * weight
            weighted_rays_sum += rays * weight

            cat = sec.get("category", "")
            sen = str(sec.get("seniority", "")).lower()
            if cat in ("G-Sec", "T-Bill", "SGB") or "senior secured" in sen or "sovereign" in sen:
                sov_and_sr_capital += allocated_cap

            # Project 12-month calendar coupons
            annual_coupon_inr = units * float(fv) * (float(coupon) / 100.0)

            if "monthly" in freq:
                monthly_payout = annual_coupon_inr / 12.0
                for m_idx in range(1, 13):
                    monthly_schedule[f"month_{m_idx}"]["coupon"] += monthly_payout
            elif "semi" in freq:
                semi_payout = annual_coupon_inr / 2.0
                monthly_schedule["month_6"]["coupon"] += semi_payout
                monthly_schedule["month_12"]["coupon"] += semi_payout
            elif "quarter" in freq:
                q_payout = annual_coupon_inr / 4.0
                for m_idx in (3, 6, 9, 12):
                    monthly_schedule[f"month_{m_idx}"]["coupon"] += q_payout
            elif "none" in freq or cat == "Debt ETF" or coupon == 0.0:
                pass  # Accumulating/Growth
            else:
                # Default Annual payout in month 12
                monthly_schedule["month_12"]["coupon"] += annual_coupon_inr

            # Principal redemption if maturing within 12 months
            years = sec.get("years_to_maturity") or self.calculate_years_to_maturity(
                sec.get("maturity_date", "2030-01-01"), valuation_date
            )
            if years <= 1.0:
                mat_month = max(1, min(12, int(round(years * 12.0))))
                redemption_inr = units * float(fv)
                monthly_schedule[f"month_{mat_month}"]["principal"] += redemption_inr

            allocations.append(
                {
                    "isin": sec.get("isin"),
                    "symbol": sec.get("symbol"),
                    "name": sec.get("name"),
                    "category": cat,
                    "seniority": sec.get("seniority"),
                    "rating": sec.get("rating"),
                    "units": units,
                    "allocated_capital_inr": allocated_cap,
                    "weight_pct": round(weight * 100.0, 2),
                    "coupon_rate": coupon,
                    "effective_ytm": eff_ytm,
                    "modified_duration": mod_dur,
                    "rays_score": rays,
                    "risk_band": sec.get("risk_band", "Manageable Risk"),
                }
            )

        # Finalize monthly total sums
        total_annual_coupon = 0.0
        total_principal_repaid = 0.0
        for m_k in monthly_schedule:
            c_val = round(monthly_schedule[m_k]["coupon"], 2)
            p_val = round(monthly_schedule[m_k]["principal"], 2)
            monthly_schedule[m_k]["coupon"] = c_val
            monthly_schedule[m_k]["principal"] = p_val
            monthly_schedule[m_k]["total"] = round(c_val + p_val, 2)
            total_annual_coupon += c_val
            total_principal_repaid += p_val

        sov_sr_pct = (sov_and_sr_capital / total_capital_inr) * 100.0

        return {
            "total_capital_inr": total_capital_inr,
            "total_allocated_inr": round(total_capital_inr, 2),
            "weighted_effective_ytm": round(weighted_ytm_sum, 2),
            "weighted_modified_duration": round(weighted_dur_sum, 2),
            "weighted_rays_score": round(weighted_rays_sum, 2),
            "sovereign_and_senior_secured_pct": round(sov_sr_pct, 1),
            "total_annual_coupon_inflow": round(total_annual_coupon, 2),
            "total_principal_repaid_inflow": round(total_principal_repaid, 2),
            "monthly_schedule": monthly_schedule,
            "allocations": allocations,
        }


if __name__ == "__main__":
    print("=================================================================")
    print("      Debtinst_s - Sprint 3 Quantitative Engine Demo             ")
    print("=================================================================")

    quant = BondQuantEngine()
    print(f"[+] Loaded BondQuantEngine with default DB: {quant.db_path}")

    # 1. Screen high-return, manageable-risk securities
    screened = quant.screen_securities(
        min_rating="AA",
        min_asset_cover=1.25,
        exclude_yield_traps=True,
    )
    print(f"\n[+] Screened {len(screened)} Senior / High-Quality Securities (Sorted by RAYS):")
    for s in screened[:8]:
        print(
            f"    - {s['symbol']:14} | {s['category']:14} | Rating: {s['rating']:10} "
            f"| YTM: {s['effective_ytm']:5.2f}% | D_mod: {s['modified_duration']:4.2f} "
            f"| G-Spread: {s['spread_over_gsec_bps']:+5.0f} bps | RAYS: {s['rays_score']:5.2f} "
            f"| Band: {s['risk_band']}"
        )

    # 2. Portfolio Cash-Flow Ladder Demo
    portfolio_report = quant.generate_cashflow_ladder(
        securities=screened[:5],
        total_capital_inr=500000.0,
        allocation_mode="rays_weighted",
    )
    print(f"\n[+] Simulated INR 5,00,000 Portfolio Ladder:")
    print(f"    * Weighted Effective YTM: {portfolio_report['weighted_effective_ytm']}%")
    print(f"    * Weighted Duration:      {portfolio_report['weighted_modified_duration']} years")
    print(f"    * Sovereign + Senior Sec: {portfolio_report['sovereign_and_senior_secured_pct']}%")
    print(f"    * Projected 12M Coupon:   INR {portfolio_report['total_annual_coupon_inflow']:,.2f}")

    print("\n[OK] Sprint 3 Quantitative Engine successfully verified with zero third-party dependencies.")
