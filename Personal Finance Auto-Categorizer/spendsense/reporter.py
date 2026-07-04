"""
Analytics and visual reporting module for SpendSense.

Computes spending aggregations and generates a standalone interactive
HTML report using Plotly with donut chart, bar chart, and summary stats.
"""

from pathlib import Path

import pandas as pd

from spendsense.logger import get_logger

logger = get_logger("reporter")

# ── Color palette — curated for readability and visual appeal ───────
CATEGORY_COLORS = [
    "#6366F1",  # Indigo
    "#F43F5E",  # Rose
    "#10B981",  # Emerald
    "#F59E0B",  # Amber
    "#3B82F6",  # Blue
    "#8B5CF6",  # Violet
    "#EC4899",  # Pink
    "#14B8A6",  # Teal
    "#EF4444",  # Red
    "#06B6D4",  # Cyan
    "#84CC16",  # Lime
    "#D946EF",  # Fuchsia
    "#FB923C",  # Orange
    "#64748B",  # Slate (for Uncategorized)
]


def compute_analytics(df: pd.DataFrame) -> dict:
    """Compute spending analytics from the categorized DataFrame.

    Args:
        df: Categorized DataFrame with columns ['date', 'description',
            'amount', 'category'].

    Returns:
        Dictionary containing all computed analytics:
        - total_spend: Sum of all transaction amounts.
        - spend_by_category: Dict of {category: total_amount}, sorted descending.
        - category_percentages: Dict of {category: percentage_of_total}.
        - avg_daily_spend: Average spend per unique day.
        - top_transactions: Top 5 individual transactions by amount.
        - uncategorized_count: Number of uncategorized transactions.
        - uncategorized_pct: Percentage of total spend that is uncategorized.
        - transaction_count: Total number of transactions.
        - date_range: Tuple of (earliest_date, latest_date).
        - unique_days: Number of unique transaction days.
    """
    logger.info("Computing spending analytics...")

    total_spend = float(df["amount"].sum())
    transaction_count = len(df)

    # ── Spend by category ────────────────────────────────────────────
    category_totals = (
        df.groupby("category")["amount"]
        .sum()
        .sort_values(ascending=False)
    )
    spend_by_category = category_totals.to_dict()

    # ── Category percentages ─────────────────────────────────────────
    category_percentages = {}
    for cat, amount in spend_by_category.items():
        pct = (amount / total_spend * 100) if total_spend > 0 else 0.0
        category_percentages[cat] = round(pct, 1)

    # ── Daily average ────────────────────────────────────────────────
    unique_days = df["date"].dt.date.nunique()
    avg_daily_spend = total_spend / unique_days if unique_days > 0 else 0.0

    # ── Top transactions ─────────────────────────────────────────────
    top_5 = df.nlargest(5, "amount")[["date", "description", "amount", "category"]]
    top_transactions = top_5.to_dict("records")

    # ── Uncategorized stats ──────────────────────────────────────────
    uncategorized_mask = df["category"] == "Uncategorized"
    uncategorized_count = int(uncategorized_mask.sum())
    uncategorized_spend = float(df.loc[uncategorized_mask, "amount"].sum())
    uncategorized_pct = (
        round(uncategorized_spend / total_spend * 100, 1) if total_spend > 0 else 0.0
    )

    # ── Date range ────────────────────────────────────────────────────
    date_range = (
        df["date"].min().strftime("%Y-%m-%d"),
        df["date"].max().strftime("%Y-%m-%d"),
    )

    analytics = {
        "total_spend": round(total_spend, 2),
        "spend_by_category": spend_by_category,
        "category_percentages": category_percentages,
        "avg_daily_spend": round(avg_daily_spend, 2),
        "top_transactions": top_transactions,
        "uncategorized_count": uncategorized_count,
        "uncategorized_pct": uncategorized_pct,
        "transaction_count": transaction_count,
        "date_range": date_range,
        "unique_days": unique_days,
    }

    logger.info(
        "Analytics complete: $%.2f total across %d transactions over %d days",
        total_spend,
        transaction_count,
        unique_days,
    )

    return analytics


def generate_report(
    analytics: dict,
    output_dir: str = "output",
) -> str:
    """Generate a standalone interactive HTML report.

    Creates a visually rich HTML file with:
    - A donut chart showing spending breakdown by category.
    - A horizontal bar chart comparing category totals.
    - A summary statistics card.

    Args:
        analytics: Dictionary from compute_analytics().
        output_dir: Directory to save the report (created if needed).

    Returns:
        Absolute path to the generated HTML report file.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Use date range for filename
    start_date = analytics["date_range"][0][:7]  # YYYY-MM
    report_filename = f"spending_report_{start_date}.html"
    report_path = output_path / report_filename

    try:
        html_content = _generate_plotly_report(analytics)
        logger.info("Generated interactive Plotly report")
    except ImportError:
        logger.warning("Plotly not available, falling back to static Matplotlib report")
        html_content = _generate_matplotlib_fallback(analytics, output_path)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    abs_path = str(report_path.resolve())
    logger.info("Report saved: %s", abs_path)
    return abs_path


def _generate_plotly_report(analytics: dict) -> str:
    """Generate a premium interactive HTML report using Plotly.

    Args:
        analytics: Analytics dictionary.

    Returns:
        Complete HTML string for the report.
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    categories = list(analytics["spend_by_category"].keys())
    amounts = list(analytics["spend_by_category"].values())
    percentages = [analytics["category_percentages"][c] for c in categories]

    colors = CATEGORY_COLORS[: len(categories)]
    max_amount = max(amounts) if amounts else 1

    # ── Donut Chart (standalone, no subplots for cleaner control) ────
    donut_fig = go.Figure(
        go.Pie(
            labels=categories,
            values=amounts,
            hole=0.55,
            marker=dict(
                colors=colors,
                line=dict(color="rgba(0,0,0,0)", width=2.5),
            ),
            textinfo="none",
            hovertemplate=(
                "<b style='font-size:14px'>%{label}</b><br>"
                "<span style='color:#a78bfa'>$%{value:,.2f}</span><br>"
                "<span style='color:#94a3b8'>%{percent}</span>"
                "<extra></extra>"
            ),
            showlegend=False,
            direction="clockwise",
            sort=False,
        )
    )
    donut_fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0", family="Inter, sans-serif"),
        height=380,
        margin=dict(t=20, b=20, l=20, r=20),
        annotations=[
            dict(
                text=(
                    f"<b style='font-size:28px;color:#f1f5f9'>"
                    f"${analytics['total_spend']:,.0f}</b><br>"
                    f"<span style='font-size:12px;color:#64748b'>Total Spend</span>"
                ),
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14),
            )
        ],
    )
    donut_html = donut_fig.to_html(
        full_html=False, include_plotlyjs=False,
        config={"displayModeBar": False},
    )

    # ── Bar Chart ────────────────────────────────────────────────────
    bar_categories = categories[::-1]
    bar_amounts = amounts[::-1]
    bar_colors = colors[::-1]

    bar_fig = go.Figure(
        go.Bar(
            x=bar_amounts,
            y=bar_categories,
            orientation="h",
            marker=dict(
                color=bar_colors,
                line=dict(width=0),
                cornerradius=4,
            ),
            text=[f"${a:,.0f}" for a in bar_amounts],
            textposition="outside",
            textfont=dict(size=11, color="#94a3b8", family="Inter"),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "<span style='color:#a78bfa'>$%{x:,.2f}</span>"
                "<extra></extra>"
            ),
            showlegend=False,
        )
    )
    bar_fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", family="Inter, sans-serif", size=12),
        height=380,
        margin=dict(t=20, b=20, l=10, r=80),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(148,163,184,0.06)",
            gridwidth=1,
            tickprefix="$",
            tickformat=",",
            tickfont=dict(color="#475569", size=10),
            zeroline=False,
        ),
        yaxis=dict(
            showgrid=False,
            tickfont=dict(color="#cbd5e1", size=11),
        ),
        bargap=0.35,
    )
    bar_html = bar_fig.to_html(
        full_html=False, include_plotlyjs=False,
        config={"displayModeBar": False},
    )

    # ── Date formatting ──────────────────────────────────────────────
    date_range = analytics["date_range"]
    from datetime import datetime
    try:
        d1 = datetime.strptime(date_range[0], "%Y-%m-%d")
        d2 = datetime.strptime(date_range[1], "%Y-%m-%d")
        date_display = f"{d1.strftime('%b %d')} - {d2.strftime('%b %d, %Y')}"
        month_display = d1.strftime("%B %Y")
    except ValueError:
        date_display = f"{date_range[0]} to {date_range[1]}"
        month_display = "Monthly Report"

    # ── Top transactions HTML ────────────────────────────────────────
    top_txns_html = ""
    for rank, txn in enumerate(analytics["top_transactions"], 1):
        date_str = (
            txn["date"].strftime("%b %d")
            if hasattr(txn["date"], "strftime")
            else str(txn["date"])[:10]
        )
        desc = txn["description"][:38]
        cat = txn["category"]
        amt = txn["amount"]

        # Find the category color
        cat_color = "#64748b"
        for ci, c in enumerate(categories):
            if c == cat:
                cat_color = CATEGORY_COLORS[ci % len(CATEGORY_COLORS)]
                break

        top_txns_html += f"""
            <div class="txn-row" style="animation-delay: {0.08 * rank}s">
                <div class="txn-rank">#{rank}</div>
                <div class="txn-info">
                    <div class="txn-desc">{desc}</div>
                    <div class="txn-meta">
                        <span class="txn-date">{date_str}</span>
                        <span class="txn-cat-badge" style="background: {cat_color}18; color: {cat_color}; border: 1px solid {cat_color}30">{cat}</span>
                    </div>
                </div>
                <div class="txn-amount">-${amt:,.2f}</div>
            </div>"""

    # ── Category breakdown HTML with progress bars ───────────────────
    cat_breakdown_html = ""
    for i, (cat, amt) in enumerate(analytics["spend_by_category"].items()):
        color = CATEGORY_COLORS[i % len(CATEGORY_COLORS)]
        pct = analytics["category_percentages"][cat]
        bar_width = (amt / max_amount * 100) if max_amount > 0 else 0
        count = 0
        # We don't have per-category transaction count in analytics easily,
        # so we show percentage and amount
        cat_breakdown_html += f"""
            <div class="cat-item" style="animation-delay: {0.05 * i}s">
                <div class="cat-header">
                    <div class="cat-left">
                        <span class="cat-dot" style="background: {color}; box-shadow: 0 0 8px {color}40"></span>
                        <span class="cat-name">{cat}</span>
                    </div>
                    <div class="cat-right">
                        <span class="cat-amount">${amt:,.2f}</span>
                        <span class="cat-pct">{pct}%</span>
                    </div>
                </div>
                <div class="cat-bar-track">
                    <div class="cat-bar-fill" style="width: {bar_width}%; background: linear-gradient(90deg, {color}, {color}88)" data-width="{bar_width}"></div>
                </div>
            </div>"""

    # ── Stat cards data ──────────────────────────────────────────────
    top_cat = categories[0] if categories else "N/A"
    top_cat_amt = amounts[0] if amounts else 0
    top_cat_color = CATEGORY_COLORS[0] if CATEGORY_COLORS else "#6366F1"

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpendSense - {month_display} Spending Report</title>
    <meta name="description" content="Interactive spending analysis for {month_display}. Track expenses across {len(categories)} categories.">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-3.0.1.min.js"></script>
    <style>
        :root {{
            --bg-primary: #06080f;
            --bg-card: rgba(15, 18, 30, 0.65);
            --bg-card-hover: rgba(20, 24, 40, 0.8);
            --border: rgba(148, 163, 184, 0.08);
            --border-hover: rgba(148, 163, 184, 0.15);
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #475569;
            --accent: #818cf8;
            --accent-glow: rgba(129, 140, 248, 0.15);
            --surface-glass: rgba(255, 255, 255, 0.03);
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}

        /* ── Animated gradient mesh background ───────────────── */
        .bg-mesh {{
            position: fixed;
            inset: 0;
            z-index: -1;
            overflow: hidden;
        }}
        .bg-mesh::before {{
            content: '';
            position: absolute;
            width: 600px; height: 600px;
            background: radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 70%);
            top: -10%; left: -5%;
            animation: drift1 25s ease-in-out infinite;
        }}
        .bg-mesh::after {{
            content: '';
            position: absolute;
            width: 500px; height: 500px;
            background: radial-gradient(circle, rgba(236,72,153,0.06) 0%, transparent 70%);
            bottom: -10%; right: -5%;
            animation: drift2 30s ease-in-out infinite;
        }}
        @keyframes drift1 {{
            0%, 100% {{ transform: translate(0, 0) scale(1); }}
            33% {{ transform: translate(100px, 50px) scale(1.1); }}
            66% {{ transform: translate(-50px, 100px) scale(0.95); }}
        }}
        @keyframes drift2 {{
            0%, 100% {{ transform: translate(0, 0) scale(1); }}
            33% {{ transform: translate(-80px, -60px) scale(1.05); }}
            66% {{ transform: translate(60px, -80px) scale(1.1); }}
        }}

        /* ── Container ───────────────────────────────────────── */
        .dashboard {{
            max-width: 1280px;
            margin: 0 auto;
            padding: 2.5rem 2rem;
        }}

        /* ── Header ──────────────────────────────────────────── */
        .dash-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 2.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border);
            animation: fadeSlideDown 0.6s ease-out;
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        .brand-icon {{
            width: 42px; height: 42px;
            border-radius: 12px;
            background: linear-gradient(135deg, #6366F1, #a78bfa);
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 4px 20px rgba(99,102,241,0.25);
        }}
        .brand-icon svg {{ width: 22px; height: 22px; }}
        .brand-text h1 {{
            font-size: 1.35rem;
            font-weight: 700;
            color: var(--text-primary);
            letter-spacing: -0.02em;
        }}
        .brand-text p {{
            font-size: 0.78rem;
            color: var(--text-muted);
            font-weight: 400;
            margin-top: 1px;
        }}
        .date-pill {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            background: var(--surface-glass);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 0.55rem 1rem;
            font-size: 0.82rem;
            color: var(--text-secondary);
            backdrop-filter: blur(10px);
        }}
        .date-pill svg {{ width: 15px; height: 15px; color: var(--text-muted); flex-shrink: 0; }}

        /* ── Stats grid ──────────────────────────────────────── */
        .stats-row {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        @media (max-width: 1024px) {{
            .stats-row {{ grid-template-columns: repeat(3, 1fr); }}
        }}
        @media (max-width: 640px) {{
            .stats-row {{ grid-template-columns: repeat(2, 1fr); }}
        }}

        .kpi {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.35rem 1.25rem;
            backdrop-filter: blur(16px);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            animation: fadeSlideUp 0.5s ease-out backwards;
            position: relative;
            overflow: hidden;
        }}
        .kpi::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--accent), transparent);
            opacity: 0;
            transition: opacity 0.3s;
        }}
        .kpi:hover {{
            background: var(--bg-card-hover);
            border-color: var(--border-hover);
            transform: translateY(-3px);
            box-shadow: 0 12px 40px rgba(0,0,0,0.3), 0 0 0 1px var(--border-hover);
        }}
        .kpi:hover::before {{ opacity: 1; }}
        .kpi-icon {{
            width: 36px; height: 36px;
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            margin-bottom: 0.9rem;
        }}
        .kpi-icon svg {{ width: 18px; height: 18px; }}
        .kpi-value {{
            font-size: 1.65rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            color: var(--text-primary);
            line-height: 1.1;
        }}
        .kpi-label {{
            font-size: 0.72rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-top: 0.35rem;
            font-weight: 500;
        }}

        /* ── Charts area ─────────────────────────────────────── */
        .charts-grid {{
            display: grid;
            grid-template-columns: 380px 1fr;
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        @media (max-width: 900px) {{
            .charts-grid {{ grid-template-columns: 1fr; }}
        }}

        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(16px);
            animation: fadeSlideUp 0.6s ease-out backwards;
            transition: border-color 0.3s;
        }}
        .card:hover {{ border-color: var(--border-hover); }}

        .card-title {{
            font-size: 0.72rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .card-title svg {{ width: 14px; height: 14px; color: var(--accent); }}

        /* ── Bottom panels ───────────────────────────────────── */
        .bottom-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        @media (max-width: 768px) {{
            .bottom-grid {{ grid-template-columns: 1fr; }}
        }}

        /* ── Category breakdown ──────────────────────────────── */
        .cat-item {{
            padding: 0.65rem 0;
            animation: fadeSlideUp 0.4s ease-out backwards;
        }}
        .cat-item + .cat-item {{
            border-top: 1px solid rgba(148,163,184,0.04);
        }}
        .cat-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.4rem;
        }}
        .cat-left {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }}
        .cat-dot {{
            width: 8px; height: 8px;
            border-radius: 50%;
            flex-shrink: 0;
        }}
        .cat-name {{
            font-size: 0.82rem;
            font-weight: 500;
            color: var(--text-secondary);
        }}
        .cat-right {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        .cat-amount {{
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--text-primary);
            font-variant-numeric: tabular-nums;
        }}
        .cat-pct {{
            font-size: 0.7rem;
            font-weight: 500;
            color: var(--text-muted);
            min-width: 36px;
            text-align: right;
        }}
        .cat-bar-track {{
            width: 100%;
            height: 4px;
            background: rgba(148,163,184,0.06);
            border-radius: 4px;
            overflow: hidden;
        }}
        .cat-bar-fill {{
            height: 100%;
            border-radius: 4px;
            width: 0%;
            transition: width 1.2s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        /* ── Top transactions ────────────────────────────────── */
        .txn-row {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.7rem 0;
            animation: fadeSlideUp 0.4s ease-out backwards;
            transition: background 0.2s;
            border-radius: 8px;
            margin: 0 -0.5rem;
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }}
        .txn-row:hover {{
            background: rgba(148,163,184,0.04);
        }}
        .txn-row + .txn-row {{
            border-top: 1px solid rgba(148,163,184,0.04);
        }}
        .txn-rank {{
            font-size: 0.7rem;
            font-weight: 700;
            color: var(--text-muted);
            min-width: 24px;
        }}
        .txn-info {{ flex: 1; min-width: 0; }}
        .txn-desc {{
            font-size: 0.82rem;
            font-weight: 500;
            color: var(--text-secondary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .txn-meta {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-top: 0.2rem;
        }}
        .txn-date {{
            font-size: 0.68rem;
            color: var(--text-muted);
        }}
        .txn-cat-badge {{
            font-size: 0.62rem;
            font-weight: 600;
            padding: 1px 7px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }}
        .txn-amount {{
            font-size: 0.88rem;
            font-weight: 600;
            color: #f87171;
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
        }}

        /* ── Footer ──────────────────────────────────────────── */
        .dash-footer {{
            text-align: center;
            padding: 2rem 0 1rem;
            border-top: 1px solid var(--border);
        }}
        .footer-brand {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            font-size: 0.72rem;
            color: var(--text-muted);
            font-weight: 500;
        }}
        .footer-brand svg {{ width: 13px; height: 13px; color: var(--accent); }}
        .footer-sub {{
            font-size: 0.65rem;
            color: rgba(71,85,105,0.6);
            margin-top: 0.3rem;
        }}

        /* ── Animations ──────────────────────────────────────── */
        @keyframes fadeSlideUp {{
            from {{ opacity: 0; transform: translateY(16px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes fadeSlideDown {{
            from {{ opacity: 0; transform: translateY(-12px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* ── Plotly container overrides ───────────────────────── */
        .js-plotly-plot .plotly .modebar {{ display: none !important; }}
    </style>
</head>
<body>
    <div class="bg-mesh"></div>

    <div class="dashboard">
        <!-- ── Header ──────────────────────────────────────── -->
        <header class="dash-header">
            <div class="brand">
                <div class="brand-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                    </svg>
                </div>
                <div class="brand-text">
                    <h1>SpendSense</h1>
                    <p>Personal Finance Report</p>
                </div>
            </div>
            <div class="date-pill">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
                </svg>
                {date_display}
            </div>
        </header>

        <!-- ── KPI Cards ───────────────────────────────────── -->
        <div class="stats-row">
            <div class="kpi" style="animation-delay: 0.05s">
                <div class="kpi-icon" style="background: rgba(129,140,248,0.1)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="#818cf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                    </svg>
                </div>
                <div class="kpi-value">${analytics['total_spend']:,.2f}</div>
                <div class="kpi-label">Total Spend</div>
            </div>
            <div class="kpi" style="animation-delay: 0.1s">
                <div class="kpi-icon" style="background: rgba(52,211,153,0.1)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="#34d399" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                    </svg>
                </div>
                <div class="kpi-value">{analytics['transaction_count']}</div>
                <div class="kpi-label">Transactions</div>
            </div>
            <div class="kpi" style="animation-delay: 0.15s">
                <div class="kpi-icon" style="background: rgba(251,146,60,0.1)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="#fb923c" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                    </svg>
                </div>
                <div class="kpi-value">${analytics['avg_daily_spend']:,.2f}</div>
                <div class="kpi-label">Daily Average</div>
            </div>
            <div class="kpi" style="animation-delay: 0.2s">
                <div class="kpi-icon" style="background: rgba(96,165,250,0.1)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="#60a5fa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
                    </svg>
                </div>
                <div class="kpi-value">{analytics['unique_days']}</div>
                <div class="kpi-label">Active Days</div>
            </div>
            <div class="kpi" style="animation-delay: 0.25s">
                <div class="kpi-icon" style="background: rgba(248,113,113,0.1)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="#f87171" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                    </svg>
                </div>
                <div class="kpi-value">{analytics['uncategorized_count']}<span style="font-size:0.65em;color:var(--text-muted);font-weight:400;margin-left:2px">/ {analytics['transaction_count']}</span></div>
                <div class="kpi-label">Unmatched ({analytics['uncategorized_pct']}%)</div>
            </div>
        </div>

        <!-- ── Charts ──────────────────────────────────────── -->
        <div class="charts-grid">
            <div class="card" style="animation-delay: 0.3s">
                <div class="card-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/></svg>
                    Spending Breakdown
                </div>
                {donut_html}
            </div>
            <div class="card" style="animation-delay: 0.35s">
                <div class="card-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
                    Category Comparison
                </div>
                {bar_html}
            </div>
        </div>

        <!-- ── Bottom Panels ───────────────────────────────── -->
        <div class="bottom-grid">
            <div class="card" style="animation-delay: 0.4s">
                <div class="card-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                    Category Breakdown
                </div>
                {cat_breakdown_html}
            </div>
            <div class="card" style="animation-delay: 0.45s">
                <div class="card-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>
                    Top Transactions
                </div>
                {top_txns_html}
            </div>
        </div>

        <!-- ── Footer ──────────────────────────────────────── -->
        <footer class="dash-footer">
            <div class="footer-brand">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                </svg>
                Generated by SpendSense
            </div>
            <div class="footer-sub">Personal Finance Auto-Categorizer &middot; {month_display}</div>
        </footer>
    </div>

    <script>
        // Animate progress bars on load
        window.addEventListener('load', () => {{
            setTimeout(() => {{
                document.querySelectorAll('.cat-bar-fill').forEach(bar => {{
                    bar.style.width = bar.dataset.width + '%';
                }});
            }}, 300);
        }});
    </script>
</body>
</html>"""

    return full_html


def _generate_matplotlib_fallback(analytics: dict, output_path: Path) -> str:
    """Fallback: generate a static PNG chart using Matplotlib.

    Used only when Plotly is not installed.

    Args:
        analytics: Analytics dictionary.
        output_path: Directory to save the PNG.

    Returns:
        HTML string embedding the saved PNG image.
    """
    import base64
    from io import BytesIO

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    categories = list(analytics["spend_by_category"].keys())
    amounts = list(analytics["spend_by_category"].values())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor("#0f0f23")

    # Donut chart
    colors = CATEGORY_COLORS[: len(categories)]
    wedges, texts, autotexts = ax1.pie(
        amounts,
        labels=categories,
        autopct="%1.1f%%",
        colors=colors,
        pctdistance=0.75,
        wedgeprops=dict(width=0.4, edgecolor="#0f0f23"),
    )
    for text in texts + autotexts:
        text.set_color("#e0e0e0")
        text.set_fontsize(8)
    ax1.set_title("Spending Breakdown", color="#e0e0e0", fontsize=14)

    # Bar chart
    ax2.barh(categories[::-1], amounts[::-1], color=colors[::-1], edgecolor="#0f0f23")
    ax2.set_facecolor("#0f0f23")
    ax2.tick_params(colors="#c0c0c0")
    ax2.set_title("Category Comparison", color="#e0e0e0", fontsize=14)
    for spine in ax2.spines.values():
        spine.set_color("#2a2a4a")

    plt.tight_layout()

    # Save to bytes
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=150, facecolor="#0f0f23")
    plt.close(fig)
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode("utf-8")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SpendSense — Spending Report</title>
    <style>
        body {{ background: #0f0f23; color: #e0e0e0; text-align: center;
               font-family: sans-serif; padding: 2rem; }}
        img {{ max-width: 100%; border-radius: 12px; }}
        h1 {{ color: #6366F1; }}
    </style>
</head>
<body>
    <h1>SpendSense — Spending Report</h1>
    <p>{analytics['date_range'][0]} to {analytics['date_range'][1]}
     | Total: ${analytics['total_spend']:,.2f}
     | {analytics['transaction_count']} transactions</p>
    <img src="data:image/png;base64,{img_base64}" alt="Spending Report Chart">
</body>
</html>"""
