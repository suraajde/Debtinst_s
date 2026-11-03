"""
src/embedded_seed.py - Zero-Dependency Embedded Bond Dataset & Auto-Materializer.

Part of Sprint 1 for Debtinst_s.
Provides an offline, self-contained dataset of 30+ benchmark debt securities
across 4 asset classes:
  1. Government Bonds (G-Sec) & Treasury Bills (T-Bill) [Sovereign Guarantee, SOV]
  2. Sovereign Gold Bonds (SGB) [2.50% coupon, Issue prices, Gold parity weight]
  3. Corporate Bonds (NCD) [Senior Secured 1.25x-1.50x, Secured, Unsecured Subordinated]
  4. Target Maturity Debt ETFs [Bharat Bond ETFs, PSU/SDL indices]

Auto-materializes into a local SQLite database (data/debt_securities.db) using
only Python's standard library (`sqlite3`). No external packages or pip installs needed.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Benchmark securities dataset (36 records)
BENCHMARK_SECURITIES: List[Dict[str, Any]] = [
    # =========================================================================
    # 1. Government Bonds (G-Sec) & Treasury Bills (T-Bill)
    # Sovereign Guarantee = 1, Rating = SOV, Seniority = Sovereign
    # =========================================================================
    {
        "isin": "IN0020230085",
        "symbol": "718GS2033",
        "name": "7.18% Government of India Sovereign Bond 2033",
        "category": "G-Sec",
        "security_type": "Government Bond",
        "issuer": "Government of India",
        "rating": "SOV",
        "rating_agency": "Government of India / RBI",
        "seniority": "Sovereign",
        "asset_cover_ratio": None,
        "coupon_rate": 7.18,
        "coupon_frequency": "Semi-Annual",
        "face_value": 100.0,
        "issue_price": 100.0,
        "issue_date": "2023-08-14",
        "maturity_date": "2033-08-14",
        "tenor_years": 10.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 1,
        "yield_to_maturity": 7.18,
        "benchmark_index": "10-Year Benchmark G-Sec Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab; capital gains indexation/flat rules apply",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"clearing_house": "CCIL", "rbi_retail_direct_eligible": True, "call_put_option": False}),
    },
    {
        "isin": "IN0020240019",
        "symbol": "710GS2034",
        "name": "7.10% Government of India Sovereign Bond 2034",
        "category": "G-Sec",
        "security_type": "Government Bond",
        "issuer": "Government of India",
        "rating": "SOV",
        "rating_agency": "Government of India / RBI",
        "seniority": "Sovereign",
        "asset_cover_ratio": None,
        "coupon_rate": 7.10,
        "coupon_frequency": "Semi-Annual",
        "face_value": 100.0,
        "issue_price": 100.0,
        "issue_date": "2024-04-08",
        "maturity_date": "2034-04-08",
        "tenor_years": 10.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 1,
        "yield_to_maturity": 7.10,
        "benchmark_index": "10-Year Benchmark G-Sec Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"clearing_house": "CCIL", "rbi_retail_direct_eligible": True, "on_the_run": True}),
    },
    {
        "isin": "IN0020230010",
        "symbol": "706GS2028",
        "name": "7.06% Government of India Sovereign Bond 2028",
        "category": "G-Sec",
        "security_type": "Government Bond",
        "issuer": "Government of India",
        "rating": "SOV",
        "rating_agency": "Government of India / RBI",
        "seniority": "Sovereign",
        "asset_cover_ratio": None,
        "coupon_rate": 7.06,
        "coupon_frequency": "Semi-Annual",
        "face_value": 100.0,
        "issue_price": 100.0,
        "issue_date": "2023-04-10",
        "maturity_date": "2028-04-10",
        "tenor_years": 5.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 1,
        "yield_to_maturity": 7.08,
        "benchmark_index": "5-Year Benchmark G-Sec Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"clearing_house": "CCIL", "rbi_retail_direct_eligible": True}),
    },
    {
        "isin": "IN0020220060",
        "symbol": "726GS2032",
        "name": "7.26% Government of India Sovereign Bond 2032",
        "category": "G-Sec",
        "security_type": "Government Bond",
        "issuer": "Government of India",
        "rating": "SOV",
        "rating_agency": "Government of India / RBI",
        "seniority": "Sovereign",
        "asset_cover_ratio": None,
        "coupon_rate": 7.26,
        "coupon_frequency": "Semi-Annual",
        "face_value": 100.0,
        "issue_price": 100.0,
        "issue_date": "2022-08-22",
        "maturity_date": "2032-08-22",
        "tenor_years": 10.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 1,
        "yield_to_maturity": 7.15,
        "benchmark_index": "G-Sec Benchmark",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"clearing_house": "CCIL", "highly_liquid": True}),
    },
    {
        "isin": "IN0020200270",
        "symbol": "664GS2035",
        "name": "6.64% Government of India Sovereign Bond 2035",
        "category": "G-Sec",
        "security_type": "Government Bond",
        "issuer": "Government of India",
        "rating": "SOV",
        "rating_agency": "Government of India / RBI",
        "seniority": "Sovereign",
        "asset_cover_ratio": None,
        "coupon_rate": 6.64,
        "coupon_frequency": "Semi-Annual",
        "face_value": 100.0,
        "issue_price": 100.0,
        "issue_date": "2020-06-16",
        "maturity_date": "2035-06-16",
        "tenor_years": 15.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 1,
        "yield_to_maturity": 7.22,
        "benchmark_index": "15-Year G-Sec Curve",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"duration_type": "Long Term"}),
    },
    {
        "isin": "IN002023X013",
        "symbol": "91DTB2024",
        "name": "Government of India 91-Day Treasury Bill",
        "category": "T-Bill",
        "security_type": "Treasury Bill",
        "issuer": "Government of India",
        "rating": "SOV",
        "rating_agency": "Government of India / RBI",
        "seniority": "Sovereign",
        "asset_cover_ratio": None,
        "coupon_rate": 0.0,
        "coupon_frequency": "At Maturity",
        "face_value": 100.0,
        "issue_price": 98.35,
        "issue_date": "2024-01-04",
        "maturity_date": "2024-04-04",
        "tenor_years": 0.25,
        "gold_grams": 0.0,
        "sovereign_guarantee": 1,
        "yield_to_maturity": 6.75,
        "benchmark_index": "FBIL 91-Day T-Bill Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Discount treated as short-term capital gain / slab income",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"zero_coupon": True, "discount_instrument": True}),
    },
    {
        "isin": "IN002023Y029",
        "symbol": "182DTB2024",
        "name": "Government of India 182-Day Treasury Bill",
        "category": "T-Bill",
        "security_type": "Treasury Bill",
        "issuer": "Government of India",
        "rating": "SOV",
        "rating_agency": "Government of India / RBI",
        "seniority": "Sovereign",
        "asset_cover_ratio": None,
        "coupon_rate": 0.0,
        "coupon_frequency": "At Maturity",
        "face_value": 100.0,
        "issue_price": 96.65,
        "issue_date": "2024-01-11",
        "maturity_date": "2024-07-11",
        "tenor_years": 0.50,
        "gold_grams": 0.0,
        "sovereign_guarantee": 1,
        "yield_to_maturity": 6.85,
        "benchmark_index": "FBIL 182-Day T-Bill Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Discount treated as short-term capital gain / slab income",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"zero_coupon": True, "discount_instrument": True}),
    },
    {
        "isin": "IN002023Z042",
        "symbol": "364DTB2024",
        "name": "Government of India 364-Day Treasury Bill",
        "category": "T-Bill",
        "security_type": "Treasury Bill",
        "issuer": "Government of India",
        "rating": "SOV",
        "rating_agency": "Government of India / RBI",
        "seniority": "Sovereign",
        "asset_cover_ratio": None,
        "coupon_rate": 0.0,
        "coupon_frequency": "At Maturity",
        "face_value": 100.0,
        "issue_price": 93.45,
        "issue_date": "2024-01-18",
        "maturity_date": "2025-01-16",
        "tenor_years": 1.00,
        "gold_grams": 0.0,
        "sovereign_guarantee": 1,
        "yield_to_maturity": 6.95,
        "benchmark_index": "FBIL 364-Day T-Bill Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Discount treated as short-term capital gain / slab income",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"zero_coupon": True, "discount_instrument": True}),
    },

    # =========================================================================
    # 2. Sovereign Gold Bonds (SGB)
    # 2.50% p.a. fixed coupon paid semi-annually, 1.0g gold parity, SOV rating
    # Capital gains exempt on redemption at maturity
    # =========================================================================
    {
        "isin": "IN0020230150",
        "symbol": "SGB2324IV",
        "name": "Sovereign Gold Bond 2023-24 Series IV",
        "category": "SGB",
        "security_type": "Sovereign Gold Bond",
        "issuer": "Reserve Bank of India on behalf of GoI",
        "rating": "SOV",
        "rating_agency": "Government of India / RBI",
        "seniority": "Sovereign",
        "asset_cover_ratio": None,
        "coupon_rate": 2.50,
        "coupon_frequency": "Semi-Annual",
        "face_value": 6263.0,
        "issue_price": 6263.0,
        "issue_date": "2024-02-21",
        "maturity_date": "2032-02-21",
        "tenor_years": 8.0,
        "gold_grams": 1.0,
        "sovereign_guarantee": 1,
        "yield_to_maturity": 2.50,
        "benchmark_index": "IBJA 999 Purity Gold Price",
        "expense_ratio": 0.0,
        "tax_treatment": "2.5% coupon taxable; 100% Capital Gains EXEMPT if held to maturity",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"gold_purity": "999 fine gold", "premature_exit_window_years": [5, 6, 7]}),
    },
    {
        "isin": "IN0020230119",
        "symbol": "SGB2324III",
        "name": "Sovereign Gold Bond 2023-24 Series III",
        "category": "SGB",
        "security_type": "Sovereign Gold Bond",
        "issuer": "Reserve Bank of India on behalf of GoI",
        "rating": "SOV",
        "rating_agency": "Government of India / RBI",
        "seniority": "Sovereign",
        "asset_cover_ratio": None,
        "coupon_rate": 2.50,
        "coupon_frequency": "Semi-Annual",
        "face_value": 6199.0,
        "issue_price": 6199.0,
        "issue_date": "2023-12-28",
        "maturity_date": "2031-12-28",
        "tenor_years": 8.0,
        "gold_grams": 1.0,
        "sovereign_guarantee": 1,
        "yield_to_maturity": 2.50,
        "benchmark_index": "IBJA 999 Purity Gold Price",
        "expense_ratio": 0.0,
        "tax_treatment": "2.5% coupon taxable; 100% Capital Gains EXEMPT if held to maturity",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"gold_purity": "999 fine gold", "discount_online_inr": 50}),
    },
    {
        "isin": "IN0020230051",
        "symbol": "SGB2324II",
        "name": "Sovereign Gold Bond 2023-24 Series II",
        "category": "SGB",
        "security_type": "Sovereign Gold Bond",
        "issuer": "Reserve Bank of India on behalf of GoI",
        "rating": "SOV",
        "rating_agency": "Government of India / RBI",
        "seniority": "Sovereign",
        "asset_cover_ratio": None,
        "coupon_rate": 2.50,
        "coupon_frequency": "Semi-Annual",
        "face_value": 5923.0,
        "issue_price": 5923.0,
        "issue_date": "2023-09-20",
        "maturity_date": "2031-09-20",
        "tenor_years": 8.0,
        "gold_grams": 1.0,
        "sovereign_guarantee": 1,
        "yield_to_maturity": 2.50,
        "benchmark_index": "IBJA 999 Purity Gold Price",
        "expense_ratio": 0.0,
        "tax_treatment": "2.5% coupon taxable; 100% Capital Gains EXEMPT if held to maturity",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"gold_purity": "999 fine gold"}),
    },
    {
        "isin": "IN0020230028",
        "symbol": "SGB2324I",
        "name": "Sovereign Gold Bond 2023-24 Series I",
        "category": "SGB",
        "security_type": "Sovereign Gold Bond",
        "issuer": "Reserve Bank of India on behalf of GoI",
        "rating": "SOV",
        "rating_agency": "Government of India / RBI",
        "seniority": "Sovereign",
        "asset_cover_ratio": None,
        "coupon_rate": 2.50,
        "coupon_frequency": "Semi-Annual",
        "face_value": 5926.0,
        "issue_price": 5926.0,
        "issue_date": "2023-06-27",
        "maturity_date": "2031-06-27",
        "tenor_years": 8.0,
        "gold_grams": 1.0,
        "sovereign_guarantee": 1,
        "yield_to_maturity": 2.50,
        "benchmark_index": "IBJA 999 Purity Gold Price",
        "expense_ratio": 0.0,
        "tax_treatment": "2.5% coupon taxable; 100% Capital Gains EXEMPT if held to maturity",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"gold_purity": "999 fine gold"}),
    },
    {
        "isin": "IN0020220136",
        "symbol": "SGB2223IV",
        "name": "Sovereign Gold Bond 2022-23 Series IV",
        "category": "SGB",
        "security_type": "Sovereign Gold Bond",
        "issuer": "Reserve Bank of India on behalf of GoI",
        "rating": "SOV",
        "rating_agency": "Government of India / RBI",
        "seniority": "Sovereign",
        "asset_cover_ratio": None,
        "coupon_rate": 2.50,
        "coupon_frequency": "Semi-Annual",
        "face_value": 5611.0,
        "issue_price": 5611.0,
        "issue_date": "2023-03-14",
        "maturity_date": "2031-03-14",
        "tenor_years": 8.0,
        "gold_grams": 1.0,
        "sovereign_guarantee": 1,
        "yield_to_maturity": 2.50,
        "benchmark_index": "IBJA 999 Purity Gold Price",
        "expense_ratio": 0.0,
        "tax_treatment": "2.5% coupon taxable; 100% Capital Gains EXEMPT if held to maturity",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"gold_purity": "999 fine gold"}),
    },
    {
        "isin": "IN0020200114",
        "symbol": "SGB2021VI",
        "name": "Sovereign Gold Bond 2020-21 Series VI",
        "category": "SGB",
        "security_type": "Sovereign Gold Bond",
        "issuer": "Reserve Bank of India on behalf of GoI",
        "rating": "SOV",
        "rating_agency": "Government of India / RBI",
        "seniority": "Sovereign",
        "asset_cover_ratio": None,
        "coupon_rate": 2.50,
        "coupon_frequency": "Semi-Annual",
        "face_value": 5117.0,
        "issue_price": 5117.0,
        "issue_date": "2020-09-08",
        "maturity_date": "2028-09-08",
        "tenor_years": 8.0,
        "gold_grams": 1.0,
        "sovereign_guarantee": 1,
        "yield_to_maturity": 2.50,
        "benchmark_index": "IBJA 999 Purity Gold Price",
        "expense_ratio": 0.0,
        "tax_treatment": "2.5% coupon taxable; 100% Capital Gains EXEMPT if held to maturity",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"gold_purity": "999 fine gold"}),
    },

    # =========================================================================
    # 3. Corporate Bonds / NCDs (Non-Convertible Debentures)
    # Tier A: Senior Secured (AAA, AA+) with 1.25x - 1.50x Asset Cover (Low/Manageable Risk)
    # Tier B: Secured (AA, AA-) with 1.25x Asset Cover (Moderate Manageable Risk)
    # Tier C: Unsecured Subordinated / Lower Rated (High Risk - Filter Targets)
    # =========================================================================
    # --- Tier A: Senior Secured AAA (Highest Safety, 1.35x - 1.50x Asset Cover) ---
    {
        "isin": "INE001A07TO2",
        "symbol": "HDFC27",
        "name": "HDFC Ltd (HDFC Bank) 7.95% Senior Secured NCD 2027",
        "category": "Corporate NCD",
        "security_type": "Non-Convertible Debenture",
        "issuer": "HDFC Bank Ltd",
        "rating": "CRISIL AAA",
        "rating_agency": "CRISIL",
        "seniority": "Senior Secured",
        "asset_cover_ratio": 1.50,
        "coupon_rate": 7.95,
        "coupon_frequency": "Annual",
        "face_value": 1000.0,
        "issue_price": 1000.0,
        "issue_date": "2022-09-24",
        "maturity_date": "2027-09-24",
        "tenor_years": 5.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 7.85,
        "benchmark_index": "CRISIL 5-Year AAA Corporate Bond Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate; TDS applicable",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"security_charge": "Exclusive charge on receivables and mortgages", "debenture_trustee": "IDBI Trusteeship"}),
    },
    {
        "isin": "INE296A07RX6",
        "symbol": "BAJFIN28",
        "name": "Bajaj Finance Ltd 7.75% Senior Secured NCD 2028",
        "category": "Corporate NCD",
        "security_type": "Non-Convertible Debenture",
        "issuer": "Bajaj Finance Ltd",
        "rating": "CRISIL AAA",
        "rating_agency": "CRISIL / ICRA",
        "seniority": "Senior Secured",
        "asset_cover_ratio": 1.40,
        "coupon_rate": 7.75,
        "coupon_frequency": "Annual",
        "face_value": 1000.0,
        "issue_price": 1000.0,
        "issue_date": "2023-06-15",
        "maturity_date": "2028-06-15",
        "tenor_years": 5.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 7.80,
        "benchmark_index": "CRISIL AAA NBFC Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"security_charge": "First ranking pari-passu charge on loan assets", "debenture_trustee": "Catalyst Trusteeship"}),
    },
    {
        "isin": "INE020B08DF4",
        "symbol": "REC29",
        "name": "REC Limited 7.54% Senior Secured NCD 2029",
        "category": "Corporate NCD",
        "security_type": "Non-Convertible Debenture",
        "issuer": "REC Limited (Maharatna PSU)",
        "rating": "CRISIL AAA",
        "rating_agency": "CRISIL / CARE",
        "seniority": "Senior Secured",
        "asset_cover_ratio": 1.50,
        "coupon_rate": 7.54,
        "coupon_frequency": "Annual",
        "face_value": 1000.0,
        "issue_price": 1000.0,
        "issue_date": "2022-12-10",
        "maturity_date": "2029-12-10",
        "tenor_years": 7.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 7.55,
        "benchmark_index": "CRISIL AAA PSU Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"psu_category": "Maharatna", "security_charge": "First charge on receivables and book debts"}),
    },
    {
        "isin": "INE134E08KY9",
        "symbol": "PFC30",
        "name": "Power Finance Corporation 7.60% Senior Secured NCD 2030",
        "category": "Corporate NCD",
        "security_type": "Non-Convertible Debenture",
        "issuer": "Power Finance Corporation Ltd (Maharatna PSU)",
        "rating": "CARE AAA",
        "rating_agency": "CARE / CRISIL",
        "seniority": "Senior Secured",
        "asset_cover_ratio": 1.50,
        "coupon_rate": 7.60,
        "coupon_frequency": "Annual",
        "face_value": 1000.0,
        "issue_price": 1000.0,
        "issue_date": "2023-07-15",
        "maturity_date": "2030-07-15",
        "tenor_years": 7.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 7.58,
        "benchmark_index": "CRISIL AAA PSU Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"psu_category": "Maharatna", "security_charge": "Pari-passu charge on immovable and movable assets"}),
    },
    {
        "isin": "INE756I07DT7",
        "symbol": "IRFC31",
        "name": "Indian Railway Finance Corporation 7.49% Senior Secured NCD 2031",
        "category": "Corporate NCD",
        "security_type": "Non-Convertible Debenture",
        "issuer": "Indian Railway Finance Corporation Ltd",
        "rating": "CRISIL AAA",
        "rating_agency": "CRISIL / ICRA",
        "seniority": "Senior Secured",
        "asset_cover_ratio": 1.50,
        "coupon_rate": 7.49,
        "coupon_frequency": "Annual",
        "face_value": 1000.0,
        "issue_price": 1000.0,
        "issue_date": "2021-03-25",
        "maturity_date": "2031-03-25",
        "tenor_years": 10.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 7.45,
        "benchmark_index": "CRISIL AAA PSU Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"ministry": "Ministry of Railways", "sovereign_ownership": 0.86}),
    },
    {
        "isin": "INE053F07936",
        "symbol": "KOTAKPRIME27",
        "name": "Kotak Mahindra Prime Ltd 7.82% Senior Secured NCD 2027",
        "category": "Corporate NCD",
        "security_type": "Non-Convertible Debenture",
        "issuer": "Kotak Mahindra Prime Ltd",
        "rating": "CRISIL AAA",
        "rating_agency": "CRISIL",
        "seniority": "Senior Secured",
        "asset_cover_ratio": 1.35,
        "coupon_rate": 7.82,
        "coupon_frequency": "Annual",
        "face_value": 1000.0,
        "issue_price": 1000.0,
        "issue_date": "2024-02-20",
        "maturity_date": "2027-11-20",
        "tenor_years": 3.75,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 7.84,
        "benchmark_index": "CRISIL AAA Corporate Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"parent": "Kotak Mahindra Bank Ltd", "security_charge": "Exclusive charge on specific standard vehicle loans"}),
    },

    # --- Tier B: Senior Secured & Secured AA+ / AA (High Return, Manageable Risk - Moderate) ---
    {
        "isin": "INE498L07BC8",
        "symbol": "LTFH28",
        "name": "L&T Finance Holdings Ltd 8.15% Senior Secured NCD 2028",
        "category": "Corporate NCD",
        "security_type": "Non-Convertible Debenture",
        "issuer": "L&T Finance Ltd",
        "rating": "CRISIL AA+",
        "rating_agency": "CRISIL / CARE",
        "seniority": "Senior Secured",
        "asset_cover_ratio": 1.30,
        "coupon_rate": 8.15,
        "coupon_frequency": "Annual",
        "face_value": 1000.0,
        "issue_price": 1000.0,
        "issue_date": "2023-03-12",
        "maturity_date": "2028-03-12",
        "tenor_years": 5.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 8.18,
        "benchmark_index": "CRISIL AA+ NBFC Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate",
        "risk_tier": "Manageable Risk - Moderate",
        "metadata_json": json.dumps({"parent": "Larsen & Toubro Ltd", "security_charge": "Hypothecation on designated retail receivables"}),
    },
    {
        "isin": "INE721A07QU8",
        "symbol": "SHRIRAM28",
        "name": "Shriram Finance Ltd 8.75% Senior Secured NCD 2028",
        "category": "Corporate NCD",
        "security_type": "Non-Convertible Debenture",
        "issuer": "Shriram Finance Ltd",
        "rating": "CRISIL AA+",
        "rating_agency": "CRISIL / India Ratings",
        "seniority": "Senior Secured",
        "asset_cover_ratio": 1.25,
        "coupon_rate": 8.75,
        "coupon_frequency": "Monthly",
        "face_value": 1000.0,
        "issue_price": 1000.0,
        "issue_date": "2023-07-28",
        "maturity_date": "2028-07-28",
        "tenor_years": 5.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 8.85,
        "benchmark_index": "CRISIL AA+ NBFC Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate",
        "risk_tier": "Manageable Risk - Moderate",
        "metadata_json": json.dumps({"security_charge": "First charge on commercial vehicle loan receivables", "monthly_payout": True}),
    },
    {
        "isin": "INE528S07094",
        "symbol": "MANAPPURAM27",
        "name": "Manappuram Finance Ltd 8.90% Secured NCD 2027",
        "category": "Corporate NCD",
        "security_type": "Non-Convertible Debenture",
        "issuer": "Manappuram Finance Ltd",
        "rating": "CRISIL AA",
        "rating_agency": "CRISIL / CARE",
        "seniority": "Secured",
        "asset_cover_ratio": 1.25,
        "coupon_rate": 8.90,
        "coupon_frequency": "Annual",
        "face_value": 1000.0,
        "issue_price": 1000.0,
        "issue_date": "2023-10-18",
        "maturity_date": "2027-10-18",
        "tenor_years": 4.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 9.05,
        "benchmark_index": "CRISIL AA NBFC Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate",
        "risk_tier": "Manageable Risk - Moderate",
        "metadata_json": json.dumps({"security_charge": "First charge on gold loan receivables book", "underlying_collateral": "Gold jewellery pledge"}),
    },
    {
        "isin": "INE556F08KB7",
        "symbol": "TATAMOTFIN26",
        "name": "Tata Motors Finance Ltd 8.45% Secured NCD 2026",
        "category": "Corporate NCD",
        "security_type": "Non-Convertible Debenture",
        "issuer": "Tata Motors Finance Ltd",
        "rating": "CRISIL AA",
        "rating_agency": "CRISIL",
        "seniority": "Secured",
        "asset_cover_ratio": 1.25,
        "coupon_rate": 8.45,
        "coupon_frequency": "Annual",
        "face_value": 1000.0,
        "issue_price": 1000.0,
        "issue_date": "2023-05-15",
        "maturity_date": "2026-05-15",
        "tenor_years": 3.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 8.52,
        "benchmark_index": "CRISIL AA Corporate Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate",
        "risk_tier": "Manageable Risk - Moderate",
        "metadata_json": json.dumps({"parent": "Tata Motors Ltd", "security_charge": "Hypothecation of vehicle loan book"}),
    },
    {
        "isin": "INE870H07212",
        "symbol": "NETWORK18_28",
        "name": "Network18 Media & Investments 8.20% Secured NCD 2028",
        "category": "Corporate NCD",
        "security_type": "Non-Convertible Debenture",
        "issuer": "Network18 Media & Investments Ltd",
        "rating": "CARE AA+",
        "rating_agency": "CARE",
        "seniority": "Secured",
        "asset_cover_ratio": 1.30,
        "coupon_rate": 8.20,
        "coupon_frequency": "Annual",
        "face_value": 1000.0,
        "issue_price": 1000.0,
        "issue_date": "2023-04-10",
        "maturity_date": "2028-04-10",
        "tenor_years": 5.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 8.25,
        "benchmark_index": "Corporate AA+ Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate",
        "risk_tier": "Manageable Risk - Moderate",
        "metadata_json": json.dumps({"group": "Reliance Industries Group"}),
    },
    {
        "isin": "INE140A07TF1",
        "symbol": "PIRAMAL26",
        "name": "Piramal Enterprises Ltd 9.10% Secured NCD 2026",
        "category": "Corporate NCD",
        "security_type": "Non-Convertible Debenture",
        "issuer": "Piramal Enterprises Ltd",
        "rating": "ICRA AA",
        "rating_agency": "ICRA / CARE",
        "seniority": "Secured",
        "asset_cover_ratio": 1.25,
        "coupon_rate": 9.10,
        "coupon_frequency": "Annual",
        "face_value": 1000.0,
        "issue_price": 1000.0,
        "issue_date": "2023-11-12",
        "maturity_date": "2026-11-12",
        "tenor_years": 3.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 9.20,
        "benchmark_index": "CRISIL AA Corporate Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate",
        "risk_tier": "Manageable Risk - Moderate",
        "metadata_json": json.dumps({"security_charge": "First ranking pari-passu charge on receivables"}),
    },

    # --- Tier C: Unsecured Subordinated / Lower Rated (High Risk - Filter Targets) ---
    {
        "isin": "INE062A08231",
        "symbol": "SBIN_TIER2_34",
        "name": "State Bank of India 7.72% Tier-II Subordinated Unsecured Bond 2034",
        "category": "Corporate NCD",
        "security_type": "Non-Convertible Debenture",
        "issuer": "State Bank of India",
        "rating": "CRISIL AAA",
        "rating_agency": "CRISIL / ICRA",
        "seniority": "Unsecured Subordinated",
        "asset_cover_ratio": 1.00,
        "coupon_rate": 7.72,
        "coupon_frequency": "Annual",
        "face_value": 10000.0,
        "issue_price": 10000.0,
        "issue_date": "2024-09-09",
        "maturity_date": "2034-09-09",
        "tenor_years": 10.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 7.72,
        "benchmark_index": "CRISIL Tier-II Bond Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate",
        "risk_tier": "Manageable Risk - Moderate",
        "metadata_json": json.dumps({"basel_iii_compliant": True, "loss_absorption_clause": True, "call_option_year": 2029}),
    },
    {
        "isin": "INE522D08021",
        "symbol": "YESBANK_TIER2_27",
        "name": "Yes Bank Ltd 9.50% Subordinated Tier-II Unsecured Bond 2027",
        "category": "Corporate NCD",
        "security_type": "Non-Convertible Debenture",
        "issuer": "Yes Bank Ltd",
        "rating": "CARE A-",
        "rating_agency": "CARE",
        "seniority": "Unsecured Subordinated",
        "asset_cover_ratio": 0.0,
        "coupon_rate": 9.50,
        "coupon_frequency": "Annual",
        "face_value": 10000.0,
        "issue_price": 10000.0,
        "issue_date": "2017-12-15",
        "maturity_date": "2027-12-15",
        "tenor_years": 10.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 11.20,
        "benchmark_index": "Subordinated Debt Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate",
        "risk_tier": "High Risk - Speculative",
        "metadata_json": json.dumps({"subordination": "Subordinate to all senior depositors and creditors", "write_down_risk": "High"}),
    },
    {
        "isin": "INE929O07010",
        "symbol": "SPANDANA26",
        "name": "Spandana Sphoorty Financial 10.75% Unsecured Subordinated NCD 2026",
        "category": "Corporate NCD",
        "security_type": "Non-Convertible Debenture",
        "issuer": "Spandana Sphoorty Financial Ltd",
        "rating": "ICRA A",
        "rating_agency": "ICRA",
        "seniority": "Unsecured Subordinated",
        "asset_cover_ratio": 0.0,
        "coupon_rate": 10.75,
        "coupon_frequency": "Annual",
        "face_value": 1000.0,
        "issue_price": 1000.0,
        "issue_date": "2023-08-20",
        "maturity_date": "2026-08-20",
        "tenor_years": 3.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 11.50,
        "benchmark_index": "MFI Subordinated Debt Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Interest taxable at slab rate",
        "risk_tier": "High Risk - Speculative",
        "metadata_json": json.dumps({"sector": "Microfinance", "subordinated_debt": True}),
    },
    {
        "isin": "INE608A07248",
        "symbol": "RELCAP_DEF",
        "name": "Reliance Capital 9.00% Unsecured NCD (Insolvency Default Benchmark)",
        "category": "Corporate NCD",
        "security_type": "Non-Convertible Debenture",
        "issuer": "Reliance Capital Ltd",
        "rating": "CARE D",
        "rating_agency": "CARE",
        "seniority": "Unsecured Subordinated",
        "asset_cover_ratio": 0.0,
        "coupon_rate": 9.00,
        "coupon_frequency": "Annual",
        "face_value": 1000.0,
        "issue_price": 1000.0,
        "issue_date": "2015-05-30",
        "maturity_date": "2025-05-30",
        "tenor_years": 10.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 0.0,
        "benchmark_index": "Defaulted Debt Index",
        "expense_ratio": 0.0,
        "tax_treatment": "Capital loss / haircut resolution",
        "risk_tier": "High Risk - Defaulted",
        "metadata_json": json.dumps({"status": "NCLT Insolvency Resolution / Resolution Applicant Hinduja", "negative_test_case": True}),
    },

    # =========================================================================
    # 4. Target Maturity Debt ETFs (Bharat Bond ETFs, SDL/Gilt ETFs)
    # Roll-down strategy, low cost, AAA PSU / Sovereign underlying
    # =========================================================================
    {
        "isin": "INF732E01086",
        "symbol": "BBETF25",
        "name": "Edelweiss BHARAT Bond ETF - April 2025",
        "category": "Debt ETF",
        "security_type": "Target Maturity ETF",
        "issuer": "Edelweiss Asset Management / Government of India",
        "rating": "CRISIL AAA",
        "rating_agency": "CRISIL",
        "seniority": "Senior Secured",
        "asset_cover_ratio": 1.40,
        "coupon_rate": 0.0,
        "coupon_frequency": "None (ETF)",
        "face_value": 1000.0,
        "issue_price": 1000.0,
        "issue_date": "2019-12-12",
        "maturity_date": "2025-04-15",
        "tenor_years": 5.34,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 7.10,
        "benchmark_index": "Nifty BHARAT Bond Index - April 2025",
        "expense_ratio": 0.0005,
        "tax_treatment": "Taxed as debt fund as per prevailing Finance Act",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({
            "target_maturity": "2025-04-15",
            "holdings": ["REC Ltd", "PFC Ltd", "PowerGrid", "NHPC", "NTPC", "IOCL"],
            "fund_category": "Target Maturity Fund",
        }),
    },
    {
        "isin": "INF732E01094",
        "symbol": "BBETF30",
        "name": "Edelweiss BHARAT Bond ETF - April 2030",
        "category": "Debt ETF",
        "security_type": "Target Maturity ETF",
        "issuer": "Edelweiss Asset Management / Government of India",
        "rating": "CRISIL AAA",
        "rating_agency": "CRISIL",
        "seniority": "Senior Secured",
        "asset_cover_ratio": 1.40,
        "coupon_rate": 0.0,
        "coupon_frequency": "None (ETF)",
        "face_value": 1000.0,
        "issue_price": 1000.0,
        "issue_date": "2019-12-12",
        "maturity_date": "2030-04-15",
        "tenor_years": 10.34,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 7.35,
        "benchmark_index": "Nifty BHARAT Bond Index - April 2030",
        "expense_ratio": 0.0005,
        "tax_treatment": "Debt fund taxation as per income slab",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({
            "target_maturity": "2030-04-15",
            "holdings": ["PFC", "REC", "PowerGrid", "NTPC", "HUDCO", "Nuclear Power Corp"],
            "etf_structure": "Open-ended target maturity",
        }),
    },
    {
        "isin": "INF732E01110",
        "symbol": "BBETF31",
        "name": "Edelweiss BHARAT Bond ETF - April 2031",
        "category": "Debt ETF",
        "security_type": "Target Maturity ETF",
        "issuer": "Edelweiss Asset Management / Government of India",
        "rating": "CRISIL AAA",
        "rating_agency": "CRISIL",
        "seniority": "Senior Secured",
        "asset_cover_ratio": 1.40,
        "coupon_rate": 0.0,
        "coupon_frequency": "None (ETF)",
        "face_value": 1000.0,
        "issue_price": 1000.0,
        "issue_date": "2020-07-14",
        "maturity_date": "2031-04-15",
        "tenor_years": 10.75,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 7.42,
        "benchmark_index": "Nifty BHARAT Bond Index - April 2031",
        "expense_ratio": 0.0005,
        "tax_treatment": "Debt fund taxation as per income slab",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({
            "target_maturity": "2031-04-15",
            "holdings": ["PFC", "REC", "PowerGrid", "IRFC", "NTPC", "NHPC"],
        }),
    },
    {
        "isin": "INF732E01128",
        "symbol": "BBETF32",
        "name": "Edelweiss BHARAT Bond ETF - April 2032",
        "category": "Debt ETF",
        "security_type": "Target Maturity ETF",
        "issuer": "Edelweiss Asset Management / Government of India",
        "rating": "CRISIL AAA",
        "rating_agency": "CRISIL",
        "seniority": "Senior Secured",
        "asset_cover_ratio": 1.40,
        "coupon_rate": 0.0,
        "coupon_frequency": "None (ETF)",
        "face_value": 1000.0,
        "issue_price": 1000.0,
        "issue_date": "2021-12-03",
        "maturity_date": "2032-04-15",
        "tenor_years": 10.37,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 7.48,
        "benchmark_index": "Nifty BHARAT Bond Index - April 2032",
        "expense_ratio": 0.0005,
        "tax_treatment": "Debt fund taxation as per income slab",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({
            "target_maturity": "2032-04-15",
            "holdings": ["PFC", "REC", "PowerGrid", "IRFC", "SAIL", "GAIL"],
        }),
    },
    {
        "isin": "INF209KB1174",
        "symbol": "NIPPON_SDL26",
        "name": "Nippon India ETF Nifty SDL - 2026 Maturity",
        "category": "Debt ETF",
        "security_type": "Target Maturity ETF",
        "issuer": "Nippon Life India Asset Management",
        "rating": "SOV",
        "rating_agency": "Government of India / RBI",
        "seniority": "Sovereign",
        "asset_cover_ratio": None,
        "coupon_rate": 0.0,
        "coupon_frequency": "None (ETF)",
        "face_value": 100.0,
        "issue_price": 100.0,
        "issue_date": "2021-06-25",
        "maturity_date": "2026-06-30",
        "tenor_years": 5.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 1,
        "yield_to_maturity": 7.25,
        "benchmark_index": "Nifty SDL Apr 2026 Top 20 Equal Weight Index",
        "expense_ratio": 0.0015,
        "tax_treatment": "Debt fund taxation as per income slab",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"underlying": "State Development Loans (SDLs)", "state_guarantee": True}),
    },
    {
        "isin": "INF200KA1UT8",
        "symbol": "SBI_CPSE_SDL26",
        "name": "SBI CPSE Bond Plus SDL ETF - 2026",
        "category": "Debt ETF",
        "security_type": "Target Maturity ETF",
        "issuer": "SBI Mutual Fund",
        "rating": "CRISIL AAA",
        "rating_agency": "CRISIL",
        "seniority": "Senior Secured",
        "asset_cover_ratio": 1.40,
        "coupon_rate": 0.0,
        "coupon_frequency": "None (ETF)",
        "face_value": 100.0,
        "issue_price": 100.0,
        "issue_date": "2021-04-20",
        "maturity_date": "2026-04-30",
        "tenor_years": 5.0,
        "gold_grams": 0.0,
        "sovereign_guarantee": 0,
        "yield_to_maturity": 7.20,
        "benchmark_index": "Nifty CPSE Bond Plus SDL 2026 Index",
        "expense_ratio": 0.0012,
        "tax_treatment": "Debt fund taxation as per income slab",
        "risk_tier": "Manageable Risk - Low",
        "metadata_json": json.dumps({"mix": "50% CPSE AAA PSU Bonds + 50% State Development Loans"}),
    },
]


def get_default_db_path() -> Path:
    """Return the absolute path to the standard debt securities SQLite database."""
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "data" / "debt_securities.db"


def init_embedded_db(
    db_path: Optional[str | Path] = None,
    force_reseed: bool = False,
) -> str:
    """
    Initialize and materialize the local SQLite database from embedded seed data.

    Parameters
    ----------
    db_path : Optional[str | Path]
        Path to the target SQLite database file. Defaults to `data/debt_securities.db`.
    force_reseed : bool
        If True, drops existing table and reseeds from scratch. If False, only creates
        and seeds if the database or table is missing.

    Returns
    -------
    str
        The absolute path of the initialized database.
    """
    target_path = Path(db_path) if db_path else get_default_db_path()

    # Ensure parent directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(target_path))
    try:
        cursor = conn.cursor()

        # Check if table already exists and has records
        cursor.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='securities'"
        )
        table_exists = cursor.fetchone()[0] > 0

        if table_exists and not force_reseed:
            cursor.execute("SELECT count(*) FROM securities")
            row_count = cursor.fetchone()[0]
            if row_count > 0:
                # Database is already initialized and populated
                return str(target_path.resolve())

        # If force_reseed or table doesn't exist, create schema
        if force_reseed and table_exists:
            cursor.execute("DROP TABLE IF EXISTS securities")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS securities (
                isin TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                security_type TEXT NOT NULL,
                issuer TEXT NOT NULL,
                rating TEXT NOT NULL,
                rating_agency TEXT NOT NULL,
                seniority TEXT NOT NULL,
                asset_cover_ratio REAL,
                coupon_rate REAL NOT NULL,
                coupon_frequency TEXT NOT NULL,
                face_value REAL NOT NULL,
                issue_price REAL NOT NULL,
                issue_date TEXT NOT NULL,
                maturity_date TEXT NOT NULL,
                tenor_years REAL NOT NULL,
                gold_grams REAL NOT NULL DEFAULT 0.0,
                sovereign_guarantee INTEGER NOT NULL DEFAULT 0,
                yield_to_maturity REAL,
                benchmark_index TEXT,
                expense_ratio REAL NOT NULL DEFAULT 0.0,
                tax_treatment TEXT,
                risk_tier TEXT NOT NULL,
                metadata_json TEXT,
                created_at TEXT NOT NULL
            );
            """
        )

        # Performance indexes for fast querying and filtering
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_securities_category ON securities(category);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_securities_rating ON securities(rating);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_securities_seniority ON securities(seniority);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_securities_maturity ON securities(maturity_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_securities_risk_tier ON securities(risk_tier);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_securities_sov ON securities(sovereign_guarantee);")

        insert_sql = """
            INSERT OR REPLACE INTO securities (
                isin, symbol, name, category, security_type, issuer,
                rating, rating_agency, seniority, asset_cover_ratio,
                coupon_rate, coupon_frequency, face_value, issue_price,
                issue_date, maturity_date, tenor_years, gold_grams,
                sovereign_guarantee, yield_to_maturity, benchmark_index,
                expense_ratio, tax_treatment, risk_tier, metadata_json, created_at
            ) VALUES (
                :isin, :symbol, :name, :category, :security_type, :issuer,
                :rating, :rating_agency, :seniority, :asset_cover_ratio,
                :coupon_rate, :coupon_frequency, :face_value, :issue_price,
                :issue_date, :maturity_date, :tenor_years, :gold_grams,
                :sovereign_guarantee, :yield_to_maturity, :benchmark_index,
                :expense_ratio, :tax_treatment, :risk_tier, :metadata_json, :created_at
            );
        """

        now_utc = datetime.now(timezone.utc).isoformat()
        records_to_insert = []
        for sec in BENCHMARK_SECURITIES:
            rec = dict(sec)
            rec["created_at"] = now_utc
            records_to_insert.append(rec)

        cursor.executemany(insert_sql, records_to_insert)
        conn.commit()
    finally:
        conn.close()

    return str(target_path.resolve())


def get_connection(db_path: Optional[str | Path] = None) -> sqlite3.Connection:
    """
    Return an open sqlite3 Connection to the initialized database.
    Auto-initializes the database if missing.
    """
    resolved_path = init_embedded_db(db_path)
    conn = sqlite3.connect(resolved_path)
    conn.row_factory = sqlite3.Row
    return conn


def query_securities(
    category: Optional[str] = None,
    seniority: Optional[str] = None,
    min_rating: Optional[str] = None,
    risk_tier: Optional[str] = None,
    sovereign_only: bool = False,
    min_asset_cover: Optional[float] = None,
    db_path: Optional[str | Path] = None,
) -> List[Dict[str, Any]]:
    """
    Filter and query debt securities with flexible criteria.
    """
    conn = get_connection(db_path)
    try:
        conditions: List[str] = []
        params: List[Any] = []

        if category:
            conditions.append("category = ?")
            params.append(category)

        if seniority:
            conditions.append("seniority = ?")
            params.append(seniority)

        if risk_tier:
            conditions.append("risk_tier = ?")
            params.append(risk_tier)

        if sovereign_only:
            conditions.append("sovereign_guarantee = 1")

        if min_asset_cover is not None:
            conditions.append("asset_cover_ratio >= ?")
            params.append(min_asset_cover)

        query = "SELECT * FROM securities"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY category, maturity_date ASC"

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_security_by_isin(isin: str, db_path: Optional[str | Path] = None) -> Optional[Dict[str, Any]]:
    """Fetch a single security by its 12-character ISIN."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM securities WHERE isin = ?", (isin.strip().upper(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_db_summary(db_path: Optional[str | Path] = None) -> Dict[str, Any]:
    """Retrieve statistical summary of the embedded debt securities database."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM securities")
        total_count = cursor.fetchone()[0]

        cursor.execute("SELECT category, COUNT(*) FROM securities GROUP BY category")
        by_category = dict(cursor.fetchall())

        cursor.execute("SELECT seniority, COUNT(*) FROM securities GROUP BY seniority")
        by_seniority = dict(cursor.fetchall())

        cursor.execute("SELECT risk_tier, COUNT(*) FROM securities GROUP BY risk_tier")
        by_risk_tier = dict(cursor.fetchall())

        cursor.execute("SELECT COUNT(*) FROM securities WHERE sovereign_guarantee = 1")
        sovereign_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT
                ROUND(AVG(coupon_rate), 2) as avg_coupon,
                ROUND(AVG(yield_to_maturity), 2) as avg_ytm,
                ROUND(MIN(maturity_date), 10) as earliest_maturity,
                ROUND(MAX(maturity_date), 10) as latest_maturity
            FROM securities
            WHERE yield_to_maturity > 0
            """
        )
        metrics = cursor.fetchone()

        return {
            "total_securities": total_count,
            "by_category": by_category,
            "by_seniority": by_seniority,
            "by_risk_tier": by_risk_tier,
            "sovereign_guaranteed_count": sovereign_count,
            "avg_coupon_rate": metrics[0],
            "avg_yield_to_maturity": metrics[1],
            "earliest_maturity": metrics[2],
            "latest_maturity": metrics[3],
        }
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    print("=================================================================")
    print("   Debtinst_s - Sprint 1 Embedded Bond Database Materializer   ")
    print("=================================================================")

    target_db = init_embedded_db(force_reseed=True)
    print(f"[+] Materialized SQLite DB at: {target_db}")

    summary = get_db_summary()
    print(f"[+] Total benchmark securities loaded: {summary['total_securities']}")
    print("\n[-] Breakdown by Category:")
    for cat, count in summary["by_category"].items():
        print(f"    * {cat:16}: {count:2} securities")

    print("\n[-] Breakdown by Seniority:")
    for sen, count in summary["by_seniority"].items():
        print(f"    * {sen:24}: {count:2} securities")

    print("\n[-] Breakdown by Risk Tier:")
    for rt, count in summary["by_risk_tier"].items():
        print(f"    * {rt:28}: {count:2} securities")

    print(f"\n[-] Sovereign Guaranteed: {summary['sovereign_guaranteed_count']}")
    print(f"[-] Average Benchmark YTM: {summary['avg_yield_to_maturity']}%")

    print("\n[+] Testing High-Return / Manageable-Risk Filter:")
    high_return_manageable = query_securities(
        category="Corporate NCD",
        min_asset_cover=1.25,
    )
    print(f"    Found {len(high_return_manageable)} Senior Secured / Secured NCDs with Asset Cover >= 1.25x:")
    for b in high_return_manageable:
        print(f"      - {b['symbol']:14} | {b['rating']:10} | Cover: {b['asset_cover_ratio']}x | Coupon: {b['coupon_rate']:.2f}% | Mat: {b['maturity_date']}")

    print("\n[OK] Embedded bond database verification successfully finished with zero third-party dependencies.")
