"""
src/ui_template.py - Zero-Dependency Interactive Dashboard HTML & UI Generator.

Part of Sprint 4 for Debtinst_s.
Generates an institutional-grade, zero-CDN, standalone fixed-income terminal UI
with inline CSS, SVG charting, and dual-mode JavaScript (API-connected + 100% offline).
"""

from __future__ import annotations

import json
from typing import Any, Dict


def render_dashboard_html(
    initial_payload_json: str,
    standalone_mode: bool = False,
) -> str:
    """
    Renders the complete self-contained HTML document for the Debtinst_s terminal.

    Parameters
    ----------
    initial_payload_json : str
        JSON string containing initial market snapshot, securities, sovereign curve,
        and cash-flow ladder data.
    standalone_mode : bool
        If True, marks the document as a portable offline bundle.
    """
    # Safe embedding of JSON data into the script tag
    safe_json = initial_payload_json.replace("</script>", "<\\/script>")

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Debtinst_s | Institutional Fixed-Income & Gold Bond Terminal</title>
  <style>
    :root {{
      --bg-base: #090d16;
      --bg-surface: #111827;
      --bg-card: #1f2937;
      --bg-card-hover: #283548;
      --border: #374151;
      --border-focus: #3b82f6;
      --text-main: #f9fafb;
      --text-muted: #9ca3af;
      --text-dim: #6b7280;
      --accent-blue: #38bdf8;
      --accent-green: #10b981;
      --accent-amber: #f59e0b;
      --accent-rose: #f43f5e;
      --accent-gold: #fbbf24;
      --accent-purple: #a855f7;
      --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }}

    [data-theme="light"] {{
      --bg-base: #f3f4f6;
      --bg-surface: #ffffff;
      --bg-card: #f9fafb;
      --bg-card-hover: #f3f4f6;
      --border: #e5e7eb;
      --border-focus: #2563eb;
      --text-main: #111827;
      --text-muted: #4b5563;
      --text-dim: #9ca3af;
      --accent-blue: #0284c7;
      --accent-green: #059669;
      --accent-amber: #d97706;
      --accent-rose: #e11d48;
      --accent-gold: #d97706;
      --accent-purple: #7c3aed;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: var(--font-family);
      background-color: var(--bg-base);
      color: var(--text-main);
      line-height: 1.5;
      font-size: 14px;
      overflow-x: hidden;
    }}

    /* Top Navigation Header */
    header {{
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border);
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
    }}

    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .brand-logo {{
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, var(--accent-blue), var(--accent-green));
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      color: #ffffff;
      font-size: 16px;
    }}
    .brand-title h1 {{
      font-size: 16px;
      font-weight: 700;
      letter-spacing: -0.02em;
    }}
    .brand-title p {{
      font-size: 11px;
      color: var(--text-muted);
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 11px;
      font-weight: 600;
      font-family: var(--font-mono);
      border: 1px solid transparent;
    }}
    .badge-live {{ background: rgba(16, 185, 129, 0.15); color: var(--accent-green); border-color: rgba(16, 185, 129, 0.3); }}
    .badge-offline {{ background: rgba(56, 189, 248, 0.15); color: var(--accent-blue); border-color: rgba(56, 189, 248, 0.3); }}
    .badge-guard {{ background: rgba(244, 63, 94, 0.15); color: var(--accent-rose); border-color: rgba(244, 63, 94, 0.3); }}

    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--bg-card);
      color: var(--text-main);
      border: 1px solid var(--border);
      padding: 6px 14px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
      transition: all 0.15s ease;
    }}
    .btn:hover {{
      background: var(--bg-card-hover);
      border-color: var(--border-focus);
    }}
    .btn-primary {{
      background: #2563eb;
      color: #ffffff;
      border-color: #1d4ed8;
    }}
    .btn-primary:hover {{
      background: #1d4ed8;
    }}

    /* Executive KPI Ribbon */
    .kpi-ribbon {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      padding: 16px 24px;
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border);
    }}
    .kpi-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .kpi-label {{
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 600;
      letter-spacing: 0.05em;
      margin-bottom: 4px;
    }}
    .kpi-value {{
      font-size: 20px;
      font-weight: 700;
      font-family: var(--font-mono);
      letter-spacing: -0.02em;
    }}
    .kpi-subtext {{
      font-size: 11px;
      color: var(--text-dim);
      margin-top: 4px;
    }}

    /* Main Terminal Layout */
    .terminal-container {{
      display: grid;
      grid-template-columns: 310px 1fr;
      min-height: calc(100vh - 145px);
    }}

    /* Left Sidebar Controls */
    .sidebar {{
      background: var(--bg-surface);
      border-right: 1px solid var(--border);
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 20px;
      overflow-y: auto;
    }}
    .filter-section {{
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .filter-title {{
      font-size: 12px;
      font-weight: 700;
      color: var(--text-main);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .checkbox-group {{
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .checkbox-label {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: var(--text-muted);
      cursor: pointer;
      user-select: none;
    }}
    .checkbox-label input[type="checkbox"] {{
      accent-color: #2563eb;
      width: 15px;
      height: 15px;
      cursor: pointer;
    }}
    .slider-group {{
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .slider-header {{
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: var(--text-muted);
    }}
    .slider-header span:last-child {{
      font-family: var(--font-mono);
      font-weight: 600;
      color: var(--accent-blue);
    }}
    input[type="range"] {{
      width: 100%;
      accent-color: #2563eb;
      cursor: pointer;
    }}
    select {{
      background: var(--bg-card);
      color: var(--text-main);
      border: 1px solid var(--border);
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-family: var(--font-family);
      width: 100%;
      cursor: pointer;
    }}
    select:focus {{
      border-color: var(--border-focus);
      outline: none;
    }}

    /* Main Content Area */
    .main-workspace {{
      padding: 20px 24px;
      display: flex;
      flex-direction: column;
      gap: 24px;
      overflow-x: hidden;
    }}

    /* Charts Row */
    .charts-row {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }}
    @media (max-width: 1100px) {{
      .terminal-container {{ grid-template-columns: 1fr; }}
      .charts-row {{ grid-template-columns: 1fr; }}
    }}
    .chart-panel {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .chart-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .chart-title {{
      font-size: 13px;
      font-weight: 700;
      letter-spacing: -0.01em;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .chart-legend {{
      display: flex;
      gap: 12px;
      font-size: 11px;
      color: var(--text-muted);
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      gap: 5px;
    }}
    .legend-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }}
    .chart-svg-container {{
      width: 100%;
      height: 260px;
      position: relative;
    }}
    svg {{
      width: 100%;
      height: 100%;
      overflow: visible;
    }}

    /* Table Panel */
    .table-panel {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }}
    .table-toolbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }}
    .search-input {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      width: 280px;
    }}
    .search-input:focus {{
      border-color: var(--border-focus);
      outline: none;
    }}
    .table-wrap {{
      overflow-x: auto;
      max-height: 480px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      text-align: left;
    }}
    th {{
      background: var(--bg-card);
      color: var(--text-muted);
      font-weight: 600;
      padding: 8px 12px;
      border-bottom: 1px solid var(--border);
      white-space: nowrap;
      cursor: pointer;
      user-select: none;
      position: sticky;
      top: 0;
      z-index: 10;
    }}
    th:hover {{
      color: var(--text-main);
    }}
    td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--border);
      white-space: nowrap;
      font-family: var(--font-mono);
      font-size: 12px;
    }}
    tr:hover td {{
      background: var(--bg-card);
    }}
    .col-text {{ font-family: var(--font-family); }}

    /* Cash Flow Ladder Section */
    .ladder-panel {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    .ladder-controls {{
      display: flex;
      gap: 20px;
      align-items: center;
      flex-wrap: wrap;
      background: var(--bg-card);
      padding: 14px 16px;
      border-radius: 8px;
    }}
    .ladder-metric {{
      display: flex;
      flex-direction: column;
    }}
    .ladder-metric span:first-child {{
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
    }}
    .ladder-metric span:last-child {{
      font-size: 16px;
      font-weight: 700;
      font-family: var(--font-mono);
      color: var(--accent-green);
    }}

    /* Tooltip */
    #tooltip {{
      position: absolute;
      background: #0f172a;
      color: #ffffff;
      border: 1px solid #334155;
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 11px;
      font-family: var(--font-mono);
      pointer-events: none;
      display: none;
      z-index: 200;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    }}

    /* Modal for Bhavcopy import */
    .modal-backdrop {{
      position: fixed;
      top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(4px);
      display: none;
      justify-content: center;
      align-items: center;
      z-index: 1000;
    }}
    .modal-box {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      width: 520px;
      max-width: 90%;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    textarea.csv-area {{
      width: 100%;
      height: 160px;
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 10px;
      font-family: var(--font-mono);
      font-size: 11px;
      border-radius: 6px;
      resize: vertical;
    }}
  </style>
</head>
<body>

  <!-- Header -->
  <header>
    <div class="brand">
      <div class="brand-logo">₹</div>
      <div class="brand-title">
        <h1>Debtinst_s Terminal</h1>
        <p>Institutional Fixed-Income & Gold Bond Analytics</p>
      </div>
    </div>
    <div class="header-actions">
      <span id="badge-source" class="badge badge-live">● LIVE API FEED</span>
      <button class="btn btn-primary" onclick="triggerSync()">🔄 Sync Free APIs</button>
      <button class="btn" onclick="openImportModal()">📂 Import Bhavcopy CSV</button>
      <button class="btn" onclick="toggleTheme()">🌓 Theme</button>
    </div>
  </header>

  <!-- Executive KPI Ribbon -->
  <section class="kpi-ribbon">
    <div class="kpi-card">
      <span class="kpi-label">10Y Benchmark Sovereign Yield</span>
      <span class="kpi-value" id="kpi-10y-gsec">7.18%</span>
      <span class="kpi-subtext">Government of India 7.18 GS 2033</span>
    </div>
    <div class="kpi-card">
      <span class="kpi-label">Top Risk-Adjusted Pick (RAYS)</span>
      <span class="kpi-value" id="kpi-top-pick" style="color: var(--accent-green);">-</span>
      <span class="kpi-subtext" id="kpi-top-pick-sub">Max Risk-Adjusted Yield</span>
    </div>
    <div class="kpi-card">
      <span class="kpi-label">Screened Portfolio Avg YTM</span>
      <span class="kpi-value" id="kpi-screened-ytm" style="color: var(--accent-blue);">-</span>
      <span class="kpi-subtext" id="kpi-screened-spread">+0 bps vs G-Sec</span>
    </div>
    <div class="kpi-card">
      <span class="kpi-label">24K Gold Spot Benchmark</span>
      <span class="kpi-value" id="kpi-gold-spot" style="color: var(--accent-gold);">₹7,850.00</span>
      <span class="kpi-subtext">Derived via GOLDBEES / 1g Parity</span>
    </div>
  </section>

  <!-- Main Grid -->
  <div class="terminal-container">

    <!-- Sidebar Controls -->
    <aside class="sidebar">
      <div class="filter-section">
        <div class="filter-title">
          <span>Asset Categories</span>
        </div>
        <div class="checkbox-group">
          <label class="checkbox-label"><input type="checkbox" id="cat-gsec" checked onchange="runFilter()"> Government Bonds (G-Sec)</label>
          <label class="checkbox-label"><input type="checkbox" id="cat-tbill" checked onchange="runFilter()"> Treasury Bills (T-Bill)</label>
          <label class="checkbox-label"><input type="checkbox" id="cat-sgb" checked onchange="runFilter()"> Sovereign Gold Bonds (SGB)</label>
          <label class="checkbox-label"><input type="checkbox" id="cat-ncd" checked onchange="runFilter()"> Corporate Bonds (NCD)</label>
          <label class="checkbox-label"><input type="checkbox" id="cat-etf" checked onchange="runFilter()"> Target Maturity ETFs</label>
        </div>
      </div>

      <div class="filter-section">
        <div class="filter-title">
          <span>Seniority & Security Tier</span>
          <button class="btn" style="padding: 2px 6px; font-size: 10px;" onclick="resetSafePreset()">Safe Preset</button>
        </div>
        <div class="checkbox-group">
          <label class="checkbox-label"><input type="checkbox" id="sen-sov" checked onchange="runFilter()"> Sovereign Guarantee</label>
          <label class="checkbox-label"><input type="checkbox" id="sen-sr" checked onchange="runFilter()"> Senior Secured (AAA/AA+)</label>
          <label class="checkbox-label"><input type="checkbox" id="sen-sec" onchange="runFilter()"> Secured Corporate</label>
          <label class="checkbox-label"><input type="checkbox" id="sen-unsec" onchange="runFilter()"> Unsecured Subordinated</label>
        </div>
      </div>

      <div class="filter-section">
        <div class="filter-title">Minimum Credit Rating</div>
        <select id="select-rating" onchange="runFilter()">
          <option value="AA" selected>AA or Higher (Institutional Sweet Spot)</option>
          <option value="AA+">AA+ or Higher</option>
          <option value="AAA">AAA / Sovereign Only</option>
          <option value="SOV">Sovereign (SOV) Only</option>
          <option value="ALL">All Ratings (Include Speculative)</option>
        </select>
      </div>

      <div class="filter-section">
        <div class="slider-group">
          <div class="slider-header">
            <span>Min Effective YTM</span>
            <span id="val-min-ytm">6.50%</span>
          </div>
          <input type="range" id="slide-min-ytm" min="0" max="12" step="0.25" value="6.5" oninput="updateSliderLabels(); runFilter()">
        </div>

        <div class="slider-group">
          <div class="slider-header">
            <span>Max Duration (Years)</span>
            <span id="val-max-dur">6.5 yrs</span>
          </div>
          <input type="range" id="slide-max-dur" min="0.5" max="10" step="0.5" value="6.5" oninput="updateSliderLabels(); runFilter()">
        </div>

        <div class="slider-group">
          <div class="slider-header">
            <span>Min Corporate Asset Cover</span>
            <span id="val-min-cover">1.25x</span>
          </div>
          <input type="range" id="slide-min-cover" min="1.0" max="1.50" step="0.05" value="1.25" oninput="updateSliderLabels(); runFilter()">
        </div>

        <div class="slider-group">
          <div class="slider-header">
            <span>Expected Gold CAGR</span>
            <span id="val-gold-cagr">7.50%</span>
          </div>
          <input type="range" id="slide-gold-cagr" min="0" max="15" step="0.5" value="7.5" oninput="updateSliderLabels(); runFilter()">
        </div>
      </div>

      <div class="filter-section">
        <label class="checkbox-label" style="font-weight: 600; color: var(--accent-rose);">
          <input type="checkbox" id="check-guardrail" checked onchange="runFilter()">
          🛡️ Exclude Yield Traps (Guardrail Active)
        </label>
        <p style="font-size: 11px; color: var(--text-dim);">
          Automatically drops distressed bonds (e.g. Reliance Capital default benchmark) or unsecured debt with excessive spreads.
        </p>
      </div>
    </aside>

    <!-- Main Analytics Workspace -->
    <main class="main-workspace">

      <!-- Charts Row -->
      <section class="charts-row">
        <!-- Efficient Frontier Chart -->
        <div class="chart-panel">
          <div class="chart-header">
            <div class="chart-title">
              <span>📈 Debt Efficient Frontier</span>
              <span style="font-size: 11px; font-weight: normal; color: var(--text-muted);">(Risk Score vs. YTM %)</span>
            </div>
            <div class="chart-legend">
              <div class="legend-item"><span class="legend-dot" style="background: var(--accent-blue);"></span> Sov</div>
              <div class="legend-item"><span class="legend-dot" style="background: var(--accent-green);"></span> Sr Secured</div>
              <div class="legend-item"><span class="legend-dot" style="background: var(--accent-amber);"></span> Secured</div>
              <div class="legend-item"><span class="legend-dot" style="background: var(--accent-rose);"></span> Trap</div>
            </div>
          </div>
          <div class="chart-svg-container">
            <svg id="svg-frontier" viewBox="0 0 500 250"></svg>
          </div>
        </div>

        <!-- Sovereign Yield Curve & Credit Spreads -->
        <div class="chart-panel">
          <div class="chart-header">
            <div class="chart-title">
              <span>📉 Sovereign Curve & Term Structure</span>
              <span style="font-size: 11px; font-weight: normal; color: var(--text-muted);">(Maturity vs. YTM %)</span>
            </div>
            <div class="chart-legend">
              <div class="legend-item"><span class="legend-dot" style="background: var(--accent-blue);"></span> G-Sec Curve</div>
              <div class="legend-item"><span class="legend-dot" style="background: var(--accent-green);"></span> NCD Spreads</div>
            </div>
          </div>
          <div class="chart-svg-container">
            <svg id="svg-curve" viewBox="0 0 500 250"></svg>
          </div>
        </div>
      </section>

      <!-- Institutional Screener Table -->
      <section class="table-panel">
        <div class="table-toolbar">
          <div style="display: flex; align-items: center; gap: 12px;">
            <input type="text" id="table-search" class="search-input" placeholder="Search issuer, symbol, or ISIN..." oninput="runFilter()">
            <span id="screened-count" style="font-size: 12px; color: var(--text-muted);">Showing 0 securities</span>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn" onclick="toggleSelectAll(true)">Select All for Ladder</button>
            <button class="btn" onclick="toggleSelectAll(false)">Deselect All</button>
          </div>
        </div>

        <div class="table-wrap">
          <table id="bonds-table">
            <thead>
              <tr>
                <th style="width: 30px;">✓</th>
                <th onclick="sortTable('symbol')">Symbol / ISIN ⬍</th>
                <th onclick="sortTable('issuer')">Issuer ⬍</th>
                <th onclick="sortTable('category')">Category ⬍</th>
                <th onclick="sortTable('seniority')">Seniority ⬍</th>
                <th onclick="sortTable('rating')">Rating ⬍</th>
                <th onclick="sortTable('effective_ytm')">Effective YTM ⬍</th>
                <th onclick="sortTable('spread_over_gsec_bps')">Spread (bps) ⬍</th>
                <th onclick="sortTable('modified_duration')">D_mod (Yrs) ⬍</th>
                <th onclick="sortTable('asset_cover_ratio')">Asset Cover ⬍</th>
                <th onclick="sortTable('risk_band')">Risk Band ⬍</th>
                <th onclick="sortTable('rays_score')">RAYS Score ⬍</th>
              </tr>
            </thead>
            <tbody id="bonds-tbody">
              <!-- Rendered via JS -->
            </tbody>
          </table>
        </div>
      </section>

      <!-- Portfolio Cash Flow Ladder Section -->
      <section class="ladder-panel">
        <div class="chart-header">
          <div class="chart-title">
            <span>🗓️ 12-Month Portfolio Cash-Flow & Coupon Ladder Simulator</span>
          </div>
        </div>

        <div class="ladder-controls">
          <div class="ladder-metric">
            <span>Total Capital (₹)</span>
            <input type="number" id="ladder-capital" value="500000" step="50000" style="background: var(--bg-surface); border: 1px solid var(--border); color: var(--text-main); padding: 4px 8px; border-radius: 4px; font-family: var(--font-mono); font-size: 14px; width: 140px;" onchange="computeLadder()">
          </div>
          <div class="ladder-metric">
            <span>Allocation Mode</span>
            <select id="ladder-mode" onchange="computeLadder()" style="width: 160px; padding: 4px 8px;">
              <option value="rays_weighted" selected>RAYS-Weighted (Optimal)</option>
              <option value="equal_weight">Equal-Weight</option>
            </select>
          </div>
          <div class="ladder-metric">
            <span>Weighted YTM</span>
            <span id="ladder-weighted-ytm">0.00%</span>
          </div>
          <div class="ladder-metric">
            <span>Portfolio Duration</span>
            <span id="ladder-weighted-dur" style="color: var(--accent-blue);">0.0 yrs</span>
          </div>
          <div class="ladder-metric">
            <span>Sov + Sr Secured %</span>
            <span id="ladder-sov-pct" style="color: var(--accent-gold);">0%</span>
          </div>
          <div class="ladder-metric">
            <span>12M Coupon Inflow</span>
            <span id="ladder-coupon-inflow">₹0.00</span>
          </div>
        </div>

        <!-- 12-Month Bar Chart -->
        <div style="background: var(--bg-card); border-radius: 8px; padding: 14px;">
          <div style="font-size: 12px; font-weight: 600; margin-bottom: 8px; color: var(--text-muted);">
            Projected Monthly Cash Inflows (Month 1 to Month 12)
          </div>
          <div class="chart-svg-container" style="height: 180px;">
            <svg id="svg-ladder-bars" viewBox="0 0 600 160"></svg>
          </div>
        </div>

        <!-- Allocated Units Table -->
        <div class="table-wrap" style="max-height: 250px;">
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Units / Lots</th>
                <th>Capital Deployed (₹)</th>
                <th>Portfolio Weight</th>
                <th>Coupon Rate</th>
                <th>Effective YTM</th>
                <th>RAYS</th>
              </tr>
            </thead>
            <tbody id="ladder-allocations-tbody"></tbody>
          </table>
        </div>
      </section>

    </main>
  </div>

  <!-- Tooltip Element -->
  <div id="tooltip"></div>

  <!-- Bhavcopy Import Modal -->
  <div id="modal-import" class="modal-backdrop">
    <div class="modal-box">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <h3 style="font-size: 14px; font-weight: 700;">📂 Ingest Daily Bhavcopy CSV</h3>
        <button class="btn" style="padding: 2px 8px;" onclick="closeImportModal()">✕</button>
      </div>
      <p style="font-size: 12px; color: var(--text-muted);">
        Paste or upload an institutional bond sheet (NSE/BSE corporate bond bhavcopy, RBI SGB sheet, or custom CSV).
      </p>
      <input type="file" id="csv-file-input" accept=".csv,.txt" onchange="handleFileUpload(event)" style="font-size: 12px;">
      <textarea id="csv-paste-area" class="csv-area" placeholder="ISIN,SYMBOL,CLOSE,TOTTRDQTY,RATING,ASSET_COVER
INE001A07TO2,HDFC27,1018.50,15400,CRISIL AAA,1.50
INE296A07RX6,BAJFIN28,1022.00,8200,CRISIL AAA,1.40"></textarea>
      <div style="display: flex; justify-content: flex-end; gap: 10px;">
        <button class="btn" onclick="closeImportModal()">Cancel</button>
        <button class="btn btn-primary" onclick="submitBhavcopy()">Ingest & Update Database</button>
      </div>
    </div>
  </div>

  <!-- Embedded Dataset & Client Logic -->
  <script>
    // Injected initial state from server / builder
    const INITIAL_PAYLOAD = {safe_json};
    let globalState = {{
      securities: INITIAL_PAYLOAD.securities || [],
      goldSpot: INITIAL_PAYLOAD.gold_24k_inr || 7850.0,
      sovereignCurve: INITIAL_PAYLOAD.sovereign_curve || [],
      dataSource: INITIAL_PAYLOAD.data_source || "OFFLINE_EMBEDDED_DB",
      selectedIsins: new Set(),
      sortCol: "rays_score",
      sortAsc: false,
    }};

    // Initialize selected ISINs
    globalState.securities.forEach(s => {{
      if (!s.is_yield_trap) globalState.selectedIsins.add(s.isin);
    }});

    // Rating ranking weights
    const RATING_WEIGHTS = {{
      "SOV": 1.00, "AAA": 0.96, "AA+": 0.88, "AA": 0.80, "AA-": 0.68,
      "A+": 0.55, "A": 0.45, "BBB": 0.30, "UNRATED / LIQUID": 0.50, "D": 0.00
    }};
    const RATING_ORDINAL = {{
      "SOV": 100, "AAA": 90, "AA+": 85, "AA": 80, "AA-": 75,
      "A+": 65, "A": 60, "BBB": 40, "D": 0
    }};

    // On Load
    window.addEventListener("DOMContentLoaded", () => {{
      updateSourceBadge();
      updateKpis();
      runFilter();
    }});

    function updateSourceBadge() {{
      const b = document.getElementById("badge-source");
      if (globalState.dataSource === "LIVE_FREE_API") {{
        b.className = "badge badge-live";
        b.innerText = "● LIVE FREE API";
      }} else {{
        b.className = "badge badge-offline";
        b.innerText = "● OFFLINE EMBEDDED DB";
      }}
    }}

    function toggleTheme() {{
      const html = document.documentElement;
      const current = html.getAttribute("data-theme");
      html.setAttribute("data-theme", current === "dark" ? "light" : "dark");
      renderFrontierChart(currentFilteredSecurities);
      renderCurveChart(currentFilteredSecurities);
      renderLadderChart();
    }}

    function resetSafePreset() {{
      document.getElementById("cat-gsec").checked = true;
      document.getElementById("cat-tbill").checked = true;
      document.getElementById("cat-sgb").checked = true;
      document.getElementById("cat-ncd").checked = true;
      document.getElementById("cat-etf").checked = true;

      document.getElementById("sen-sov").checked = true;
      document.getElementById("sen-sr").checked = true;
      document.getElementById("sen-sec").checked = false;
      document.getElementById("sen-unsec").checked = false;

      document.getElementById("select-rating").value = "AA";
      document.getElementById("slide-min-ytm").value = "6.5";
      document.getElementById("slide-max-dur").value = "6.5";
      document.getElementById("slide-min-cover").value = "1.25";
      document.getElementById("check-guardrail").checked = true;

      updateSliderLabels();
      runFilter();
    }}

    function updateSliderLabels() {{
      document.getElementById("val-min-ytm").innerText = parseFloat(document.getElementById("slide-min-ytm").value).toFixed(2) + "%";
      document.getElementById("val-max-dur").innerText = parseFloat(document.getElementById("slide-max-dur").value).toFixed(1) + " yrs";
      document.getElementById("val-min-cover").innerText = parseFloat(document.getElementById("slide-min-cover").value).toFixed(2) + "x";
      document.getElementById("val-gold-cagr").innerText = parseFloat(document.getElementById("slide-gold-cagr").value).toFixed(2) + "%";
    }}

    let currentFilteredSecurities = [];

    // Client-side filtering & dynamic RAYS computation
    function runFilter() {{
      const allowedCats = new Set();
      if (document.getElementById("cat-gsec").checked) allowedCats.add("G-Sec");
      if (document.getElementById("cat-tbill").checked) allowedCats.add("T-Bill");
      if (document.getElementById("cat-sgb").checked) allowedCats.add("SGB");
      if (document.getElementById("cat-ncd").checked) allowedCats.add("Corporate NCD");
      if (document.getElementById("cat-etf").checked) allowedCats.add("Debt ETF");

      const allowedSen = new Set();
      if (document.getElementById("sen-sov").checked) allowedSen.add("sovereign");
      if (document.getElementById("sen-sr").checked) allowedSen.add("senior secured");
      if (document.getElementById("sen-sec").checked) allowedSen.add("secured");
      if (document.getElementById("sen-unsec").checked) allowedSen.add("unsecured");

      const minRatingTier = document.getElementById("select-rating").value;
      const minRatingScore = RATING_ORDINAL[minRatingTier] || 0;
      const minYtm = parseFloat(document.getElementById("slide-min-ytm").value);
      const maxDur = parseFloat(document.getElementById("slide-max-dur").value);
      const minCover = parseFloat(document.getElementById("slide-min-cover").value);
      const goldCagr = parseFloat(document.getElementById("slide-gold-cagr").value);
      const guardrail = document.getElementById("check-guardrail").checked;
      const search = (document.getElementById("table-search").value || "").toLowerCase().trim();

      currentFilteredSecurities = globalState.securities.filter(s => {{
        // Category
        if (!allowedCats.has(s.category)) return false;

        // Seniority
        const senLower = (s.seniority || "").toLowerCase();
        let matchSen = false;
        if (allowedSen.has("sovereign") && (senLower.includes("sovereign") || s.sovereign_guarantee)) matchSen = true;
        if (allowedSen.has("senior secured") && senLower.includes("senior secured")) matchSen = true;
        if (allowedSen.has("secured") && !senLower.includes("senior") && senLower.includes("secured")) matchSen = true;
        if (allowedSen.has("unsecured") && (senLower.includes("unsecured") || senLower.includes("tier-ii"))) matchSen = true;
        if (!matchSen) return false;

        // Guardrail
        if (guardrail && s.is_yield_trap) return false;

        // Rating
        if (minRatingTier !== "ALL") {{
          const cleanRating = extractRating(s.rating);
          const score = RATING_ORDINAL[cleanRating] || 0;
          if (score < minRatingScore) return false;
        }}

        // Dynamic SGB YTM update with slider Gold CAGR
        let effectiveYtm = s.effective_ytm;
        if (s.category === "SGB") {{
          const couponYield = (2.50 * (s.face_value || 6263) / (s.current_price || s.face_value));
          const pull = ((globalState.goldSpot - (s.current_price || s.face_value)) / (s.current_price || s.face_value)) / Math.max(0.5, s.years_to_maturity);
          effectiveYtm = couponYield + pull * 100 + goldCagr;
        }}

        if (effectiveYtm < minYtm) return false;
        if ((s.modified_duration || 1.0) > maxDur) return false;

        // Asset cover (only for corporate NCDs)
        if (s.category === "Corporate NCD") {{
          const cov = s.asset_cover_ratio || s.asset_cover || 1.0;
          if (cov < minCover) return false;
        }}

        // Search text
        if (search) {{
          const txt = (s.symbol + " " + s.isin + " " + (s.issuer || "") + " " + (s.name || "")).toLowerCase();
          if (!txt.includes(search)) return false;
        }}

        return true;
      }});

      // Sort
      currentFilteredSecurities.sort((a, b) => {{
        let v1 = a[globalState.sortCol];
        let v2 = b[globalState.sortCol];
        if (typeof v1 === "string") return globalState.sortAsc ? v1.localeCompare(v2) : v2.localeCompare(v1);
        v1 = v1 || 0; v2 = v2 || 0;
        return globalState.sortAsc ? v1 - v2 : v2 - v1;
      }});

      renderTable(currentFilteredSecurities);
      renderFrontierChart(currentFilteredSecurities);
      renderCurveChart(currentFilteredSecurities);
      updateKpis();
      computeLadder();
    }}

    function extractRating(r) {{
      if (!r) return "UNRATED";
      const u = r.toUpperCase();
      if (u.includes("SOV")) return "SOV";
      if (u.includes("AAA")) return "AAA";
      if (u.includes("AA+")) return "AA+";
      if (u.includes("AA-")) return "AA-";
      if (u.includes("AA")) return "AA";
      if (u.includes("A+")) return "A+";
      if (u.includes("A")) return "A";
      if (u.includes("BBB")) return "BBB";
      if (u.includes("D") || u.includes("DEFAULT")) return "D";
      return "UNRATED";
    }}

    // Render Table
    function renderTable(securities) {{
      const tbody = document.getElementById("bonds-tbody");
      document.getElementById("screened-count").innerText = `Showing ${{securities.length}} of ${{globalState.securities.length}} securities`;
      tbody.innerHTML = "";

      securities.forEach(s => {{
        const tr = document.createElement("tr");
        const checked = globalState.selectedIsins.has(s.isin) ? "checked" : "";
        const isTrap = s.is_yield_trap;
        const price = s.current_price || s.clean_price || s.face_value || 1000.0;
        const spread = s.spread_over_gsec_bps !== undefined ? s.spread_over_gsec_bps : "+0";
        const cover = s.asset_cover_ratio || s.asset_cover ? (s.asset_cover_ratio || s.asset_cover).toFixed(2) + "x" : "N/A (Sov)";

        let senBadge = "badge-live";
        if ((s.seniority || "").toLowerCase().includes("unsecured")) senBadge = "badge-guard";
        else if ((s.seniority || "").toLowerCase().includes("sovereign")) senBadge = "badge-offline";

        tr.innerHTML = `
          <td><input type="checkbox" ${{checked}} onchange="toggleSelectBond('${{s.isin}}')"></td>
          <td class="col-text" style="font-weight: 700;">${{s.symbol}}<br><span style="font-size: 10px; color: var(--text-dim);">${{s.isin}}</span></td>
          <td class="col-text">${{s.issuer || s.name || s.symbol}}</td>
          <td>${{s.category}}</td>
          <td><span class="badge ${{senBadge}}">${{s.seniority}}</span></td>
          <td style="font-weight: 700;">${{s.rating}}</td>
          <td>₹${{price.toFixed(2)}}</td>
          <td style="font-weight: 700; color: var(--accent-green);">${{s.effective_ytm.toFixed(2)}}%</td>
          <td>${{spread >= 0 ? "+" + spread : spread}}</td>
          <td>${{(s.modified_duration || 0).toFixed(2)}}</td>
          <td>${{cover}}</td>
          <td>
            ${{isTrap
              ? '<span class="badge badge-guard" title="Yield Trap / Distressed">⚠️ Trap</span>'
              : '<span class="badge badge-live">' + (s.risk_band || 'Safe') + '</span>'}}
          </td>
          <td style="font-weight: 700; color: var(--accent-blue);">${{(s.rays_score || 0).toFixed(2)}}</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    function toggleSelectBond(isin) {{
      if (globalState.selectedIsins.has(isin)) globalState.selectedIsins.delete(isin);
      else globalState.selectedIsins.add(isin);
      computeLadder();
    }}

    function toggleSelectAll(select) {{
      currentFilteredSecurities.forEach(s => {{
        if (select) globalState.selectedIsins.add(s.isin);
        else globalState.selectedIsins.delete(s.isin);
      }});
      renderTable(currentFilteredSecurities);
      computeLadder();
    }}

    function sortTable(col) {{
      if (globalState.sortCol === col) globalState.sortAsc = !globalState.sortAsc;
      else {{ globalState.sortCol = col; globalState.sortAsc = false; }}
      runFilter();
    }}

    // Update Executive KPIs
    function updateKpis() {{
      document.getElementById("kpi-gold-spot").innerText = "₹" + globalState.goldSpot.toLocaleString("en-IN", {{minimumFractionDigits: 2}});
      if (currentFilteredSecurities.length > 0) {{
        const top = currentFilteredSecurities[0];
        document.getElementById("kpi-top-pick").innerText = `${{top.symbol}} (${{top.effective_ytm.toFixed(2)}}%)`;
        document.getElementById("kpi-top-pick-sub").innerText = `RAYS: ${{top.rays_score.toFixed(2)}} | ${{top.seniority}}`;

        const avgYtm = currentFilteredSecurities.reduce((a, b) => a + b.effective_ytm, 0) / currentFilteredSecurities.length;
        const avgSpread = currentFilteredSecurities.reduce((a, b) => a + (b.spread_over_gsec_bps || 0), 0) / currentFilteredSecurities.length;
        document.getElementById("kpi-screened-ytm").innerText = avgYtm.toFixed(2) + "%";
        document.getElementById("kpi-screened-spread").innerText = `${{avgSpread >= 0 ? "+" : ""}}${{avgSpread.toFixed(0)}} bps vs G-Sec`;
      }}
    }}

    // ------------------------------------------------------------------------
    // SVG Chart 1: Debt Efficient Frontier
    // ------------------------------------------------------------------------
    function renderFrontierChart(securities) {{
      const svg = document.getElementById("svg-frontier");
      svg.innerHTML = "";
      if (!securities || securities.length === 0) return;

      const w = 500, h = 250, padL = 40, padR = 20, padT = 20, padB = 30;
      const plotW = w - padL - padR;
      const plotH = h - padT - padB;

      // X: Risk score 0 to 100, Y: YTM 0 to 15%
      const maxY = Math.max(12.0, ...securities.map(s => s.effective_ytm)) + 1.0;

      // Axes gridlines
      for (let yVal = 0; yVal <= maxY; yVal += 3) {{
        const y = padT + plotH - (yVal / maxY) * plotH;
        svg.innerHTML += `<line x1="${{padL}}" y1="${{y}}" x2="${{w - padR}}" y2="${{y}}" stroke="var(--border)" stroke-width="1" stroke-dasharray="2,2"/>`;
        svg.innerHTML += `<text x="${{padL - 6}}" y="${{y + 4}}" fill="var(--text-dim)" font-size="9" text-anchor="end">${{yVal.toFixed(0)}}%</text>`;
      }}

      // Sovereign Benchmark Floor Line (7.18%)
      const gsecY = padT + plotH - (7.18 / maxY) * plotH;
      svg.innerHTML += `<line x1="${{padL}}" y1="${{gsecY}}" x2="${{w - padR}}" y2="${{gsecY}}" stroke="var(--accent-blue)" stroke-width="1.5" stroke-dasharray="4,4"/>`;
      svg.innerHTML += `<text x="${{w - padR - 4}}" y="${{gsecY - 4}}" fill="var(--accent-blue)" font-size="9" text-anchor="end">10Y G-Sec Floor (7.18%)</text>`;

      // Points
      securities.forEach(s => {{
        const x = padL + (Math.min(100, s.risk_score || 10) / 100.0) * plotW;
        const y = padT + plotH - (Math.min(maxY, s.effective_ytm) / maxY) * plotH;

        let col = "var(--accent-green)";
        if (s.is_yield_trap) col = "var(--accent-rose)";
        else if (s.category === "G-Sec" || s.category === "T-Bill" || s.category === "SGB") col = "var(--accent-blue)";
        else if ((s.seniority || "").toLowerCase().includes("senior")) col = "var(--accent-green)";
        else col = "var(--accent-amber)";

        svg.innerHTML += `<circle cx="${{x}}" cy="${{y}}" r="5" fill="${{col}}" stroke="#ffffff" stroke-width="1" style="cursor: pointer;"
          onmouseover="showTip(evt, '${{s.symbol}} | YTM: ${{s.effective_ytm.toFixed(2)}}% | Risk: ${{s.risk_score || 0}} | RAYS: ${{s.rays_score.toFixed(2)}}')"
          onmouseout="hideTip()"/>`;
      }});

      // X-Axis Label
      svg.innerHTML += `<text x="${{padL + plotW / 2}}" y="${{h - 5}}" fill="var(--text-dim)" font-size="10" text-anchor="middle">Composite Risk Score (0 = Safest, 100 = Distressed)</text>`;
    }}

    // ------------------------------------------------------------------------
    // SVG Chart 2: Sovereign Curve & Credit Spreads
    // ------------------------------------------------------------------------
    function renderCurveChart(securities) {{
      const svg = document.getElementById("svg-curve");
      svg.innerHTML = "";
      const w = 500, h = 250, padL = 40, padR = 20, padT = 20, padB = 30;
      const plotW = w - padL - padR;
      const plotH = h - padT - padB;

      const maxT = 12.0;
      const maxY = Math.max(12.0, ...securities.map(s => s.effective_ytm)) + 1.0;

      // Draw Sovereign curve points
      const curve = globalState.sovereignCurve || [(0.25, 6.75), (1.0, 6.95), (5.0, 7.08), (10.0, 7.18)];
      let pathD = "";
      curve.forEach((pt, idx) => {{
        const t = pt[0], ytm = pt[1];
        const x = padL + (t / maxT) * plotW;
        const y = padT + plotH - (ytm / maxY) * plotH;
        pathD += (idx === 0 ? `M ${{x}} ${{y}}` : ` L ${{x}} ${{y}}`);
      }});

      svg.innerHTML += `<path d="${{pathD}}" fill="none" stroke="var(--accent-blue)" stroke-width="2.5"/>`;

      // Plot bond points
      securities.forEach(s => {{
        const t = Math.min(maxT, s.years_to_maturity || 5.0);
        const x = padL + (t / maxT) * plotW;
        const y = padT + plotH - (Math.min(maxY, s.effective_ytm) / maxY) * plotH;
        const col = s.category.includes("Sec") ? "var(--accent-blue)" : "var(--accent-green)";

        svg.innerHTML += `<circle cx="${{x}}" cy="${{y}}" r="4" fill="${{col}}" opacity="0.85" style="cursor: pointer;"
          onmouseover="showTip(evt, '${{s.symbol}} (${{t.toFixed(1)}}y) | YTM: ${{s.effective_ytm.toFixed(2)}}% | Spread: ${{s.spread_over_gsec_bps || 0}} bps')"
          onmouseout="hideTip()"/>`;
      }});

      svg.innerHTML += `<text x="${{padL + plotW / 2}}" y="${{h - 5}}" fill="var(--text-dim)" font-size="10" text-anchor="middle">Maturity Horizon (Years)</text>`;
    }}

    // ------------------------------------------------------------------------
    // Portfolio Ladder Simulation & SVG Bar Chart
    // ------------------------------------------------------------------------
    function computeLadder() {{
      const totalCap = parseFloat(document.getElementById("ladder-capital").value) || 500000;
      const mode = document.getElementById("ladder-mode").value;

      // Pick selected bonds from current filtered set
      const selected = currentFilteredSecurities.filter(s => globalState.selectedIsins.has(s.isin));
      const tbody = document.getElementById("ladder-allocations-tbody");
      tbody.innerHTML = "";

      if (selected.length === 0) {{
        document.getElementById("ladder-weighted-ytm").innerText = "0.00%";
        document.getElementById("ladder-weighted-dur").innerText = "0.0 yrs";
        document.getElementById("ladder-sov-pct").innerText = "0%";
        document.getElementById("ladder-coupon-inflow").innerText = "₹0.00";
        renderLadderBars({{}});
        return;
      }}

      // Compute weights
      let weights = [];
      if (mode === "rays_weighted") {{
        const rawW = selected.map(s => Math.max(0.1, s.rays_score || 1.0));
        const sumW = rawW.reduce((a, b) => a + b, 0);
        weights = rawW.map(w => w / sumW);
      }} else {{
        weights = selected.map(() => 1.0 / selected.length);
      }}

      let weightedYtm = 0;
      let weightedDur = 0;
      let sovSrCap = 0;
      let totalAnnualCoupon = 0;
      const monthlySchedule = {{}};
      for (let m = 1; m <= 12; m++) monthlySchedule[`month_${{m}}`] = {{ coupon: 0, principal: 0, total: 0 }};

      selected.forEach((s, idx) => {{
        const w = weights[idx];
        const cap = totalCap * w;
        const price = s.current_price || s.clean_price || s.face_value || 1000.0;
        const units = Math.max(1, Math.round(cap / price));
        const deployed = units * price;

        weightedYtm += s.effective_ytm * w;
        weightedDur += (s.modified_duration || 2.0) * w;

        const sen = (s.seniority || "").toLowerCase();
        if (s.category === "G-Sec" || s.category === "T-Bill" || s.category === "SGB" || sen.includes("senior") || sen.includes("sovereign")) {{
          sovSrCap += deployed;
        }}

        // Monthly coupon projection
        const fv = s.face_value || 1000.0;
        const annualCoupon = units * fv * ((s.coupon_rate || 0) / 100.0);
        totalAnnualCoupon += annualCoupon;

        const freq = (s.coupon_frequency || s.payment_frequency || "Annual").toLowerCase();
        if (freq.includes("month")) {{
          for (let m = 1; m <= 12; m++) monthlySchedule[`month_${{m}}`].coupon += annualCoupon / 12;
        }} else if (freq.includes("semi")) {{
          monthlySchedule["month_6"].coupon += annualCoupon / 2;
          monthlySchedule["month_12"].coupon += annualCoupon / 2;
        }} else if (freq.includes("quarter")) {{
          [3, 6, 9, 12].forEach(m => monthlySchedule[`month_${{m}}`].coupon += annualCoupon / 4);
        }} else if (!freq.includes("none") && s.coupon_rate > 0) {{
          monthlySchedule["month_12"].coupon += annualCoupon;
        }}

        // Maturity within 12 months
        if (s.years_to_maturity <= 1.0) {{
          const matM = Math.max(1, Math.min(12, Math.round(s.years_to_maturity * 12)));
          monthlySchedule[`month_${{matM}}`].principal += units * fv;
        }}

        // Add to allocation table
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="col-text" style="font-weight: 700;">${{s.symbol}}</td>
          <td>${{units}}</td>
          <td>₹${{deployed.toLocaleString("en-IN", {{minimumFractionDigits: 2}})}}</td>
          <td>${{(w * 100).toFixed(1)}}%</td>
          <td>${{(s.coupon_rate || 0).toFixed(2)}}%</td>
          <td style="color: var(--accent-green); font-weight: 700;">${{s.effective_ytm.toFixed(2)}}%</td>
          <td style="color: var(--accent-blue); font-weight: 700;">${{(s.rays_score || 0).toFixed(2)}}</td>
        `;
        tbody.appendChild(tr);
      }});

      document.getElementById("ladder-weighted-ytm").innerText = weightedYtm.toFixed(2) + "%";
      document.getElementById("ladder-weighted-dur").innerText = weightedDur.toFixed(2) + " yrs";
      document.getElementById("ladder-sov-pct").innerText = ((sovSrCap / totalCap) * 100).toFixed(0) + "%";
      document.getElementById("ladder-coupon-inflow").innerText = "₹" + totalAnnualCoupon.toLocaleString("en-IN", {{minimumFractionDigits: 2}});

      renderLadderBars(monthlySchedule);
    }}

    function renderLadderBars(schedule) {{
      const svg = document.getElementById("svg-ladder-bars");
      svg.innerHTML = "";
      const w = 600, h = 160, padL = 40, padR = 20, padT = 15, padB = 25;
      const plotW = w - padL - padR;
      const plotH = h - padT - padB;

      const totals = Object.keys(schedule).map(k => (schedule[k].coupon || 0) + (schedule[k].principal || 0));
      const maxVal = Math.max(5000, ...totals) * 1.15;

      const barWidth = (plotW / 12) * 0.65;
      const step = plotW / 12;

      for (let i = 1; i <= 12; i++) {{
        const k = `month_${{i}}`;
        const cVal = schedule[k] ? schedule[k].coupon : 0;
        const pVal = schedule[k] ? schedule[k].principal : 0;
        const x = padL + (i - 1) * step + (step - barWidth) / 2;

        const cHeight = (cVal / maxVal) * plotH;
        const pHeight = (pVal / maxVal) * plotH;

        const cY = padT + plotH - cHeight;
        const pY = cY - pHeight;

        // Coupon bar (Green)
        if (cHeight > 0) {{
          svg.innerHTML += `<rect x="${{x}}" y="${{cY}}" width="${{barWidth}}" height="${{cHeight}}" fill="var(--accent-green)" rx="2"
            onmouseover="showTip(evt, 'Month ${{i}}: Coupon ₹${{cVal.toFixed(2)}}')" onmouseout="hideTip()"/>`;
        }}
        // Principal bar (Gold)
        if (pHeight > 0) {{
          svg.innerHTML += `<rect x="${{x}}" y="${{pY}}" width="${{barWidth}}" height="${{pHeight}}" fill="var(--accent-gold)" rx="2"
            onmouseover="showTip(evt, 'Month ${{i}}: Principal ₹${{pVal.toFixed(2)}}')" onmouseout="hideTip()"/>`;
        }}

        // Month label
        svg.innerHTML += `<text x="${{x + barWidth / 2}}" y="${{h - 8}}" fill="var(--text-dim)" font-size="9" text-anchor="middle">M${{i}}</text>`;
      }}
    }}

    // Tooltip Helper
    function showTip(evt, text) {{
      const tip = document.getElementById("tooltip");
      tip.innerText = text;
      tip.style.left = (evt.pageX + 10) + "px";
      tip.style.top = (evt.pageY - 25) + "px";
      tip.style.display = "block";
    }}
    function hideTip() {{
      document.getElementById("tooltip").style.display = "none";
    }}

    // Free API Sync Trigger
    async function triggerSync() {{
      const btn = event.target;
      const orig = btn.innerText;
      btn.innerText = "⏳ Syncing...";
      btn.disabled = true;

      try {{
        const resp = await fetch("/api/sync", {{ method: "POST" }});
        if (resp.ok) {{
          const data = await resp.json();
          globalState.securities = data.securities;
          globalState.goldSpot = data.gold_24k_inr;
          globalState.dataSource = data.data_source;
          updateSourceBadge();
          runFilter();
          alert("Market data synchronized successfully!");
        }} else {{
          alert("API server unavailable (running in offline mode).");
        }}
      }} catch (e) {{
        alert("Running in zero-install offline mode (no local server active). Local data remains intact.");
      }} finally {{
        btn.innerText = orig;
        btn.disabled = false;
      }}
    }}

    // Bhavcopy Import Handlers
    function openImportModal() {{
      document.getElementById("modal-import").style.display = "flex";
    }}
    function closeImportModal() {{
      document.getElementById("modal-import").style.display = "none";
    }}
    function handleFileUpload(evt) {{
      const file = evt.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = e => {{
        document.getElementById("csv-paste-area").value = e.target.result;
      }};
      reader.readAsText(file);
    }}
    async function submitBhavcopy() {{
      const raw = document.getElementById("csv-paste-area").value;
      if (!raw.trim()) return;

      try {{
        const resp = await fetch("/api/import-csv", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ csv_content: raw }}),
        }});
        if (resp.ok) {{
          const data = await resp.json();
          globalState.securities = data.securities;
          runFilter();
          closeImportModal();
          alert("Bhavcopy CSV ingested and quant engine re-calculated successfully!");
        }} else {{
          alert("Failed to submit Bhavcopy to local server.");
        }}
      }} catch (e) {{
        alert("Server not responding. Please run via 'python -m src.app_server' to enable dynamic CSV ingestion.");
      }}
    }}
  </script>
</body>
</html>"""
