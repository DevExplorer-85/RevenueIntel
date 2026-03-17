import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output, State, callback
import sys, os
import base64
import io

# ─── Load / generate data ────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from data_generator import (
    generate_customers, generate_mrr_records,
    build_monthly_summary, build_cohort_data,
)

customers = generate_customers(400)
records   = generate_mrr_records(customers)
summary   = build_monthly_summary(records)
cohort    = build_cohort_data(records, customers)

summary["month"] = pd.to_datetime(summary["month"])
records["month"]  = pd.to_datetime(records["month"])

MONTHS = summary["month"].dt.strftime("%b %Y").tolist()
MONTH_MARKS = {i: MONTHS[i] for i in range(0, len(MONTHS), 4)}

# ─── Theme ───────────────────────────────────────────────────────────────────
BG       = "#0d0f14"
CARD_BG  = "#141720"
BORDER   = "#1f2535"
ACCENT   = "#7c6ef7"
GREEN    = "#34d399"
RED      = "#f87171"
AMBER    = "#fbbf24"
BLUE     = "#60a5fa"
TEXT     = "#e2e8f0"
MUTED    = "#64748b"

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=TEXT, size=12),
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis=dict(gridcolor=BORDER, zeroline=False, tickfont=dict(size=10)),
    yaxis=dict(gridcolor=BORDER, zeroline=False, tickfont=dict(size=10)),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    hoverlabel=dict(bgcolor=CARD_BG, font_color=TEXT, bordercolor=BORDER),
)

def card(children, style=None):
    base = {
        "background": CARD_BG, "border": f"1px solid {BORDER}",
        "borderRadius": "12px", "padding": "20px",
    }
    if style:
        base.update(style)
    return html.Div(children, style=base)

def kpi(label, value, delta=None, delta_label=""):
    delta_color = GREEN if delta and delta >= 0 else RED
    delta_sign  = "▲" if delta and delta >= 0 else "▼"
    return html.Div([
        html.P(label, style={"color": MUTED, "fontSize": "11px",
                              "textTransform": "uppercase", "letterSpacing": "1px",
                              "margin": "0 0 6px 0", "fontWeight": "600"}),
        html.H3(value, style={"color": TEXT, "fontSize": "26px",
                               "fontWeight": "700", "margin": "0 0 4px 0"}),
        html.Span(
            f"{delta_sign} {abs(delta):.1f}% {delta_label}" if delta is not None else "",
            style={"color": delta_color, "fontSize": "12px", "fontWeight": "600"}
        ),
    ], style={
        "background": CARD_BG, "border": f"1px solid {BORDER}",
        "borderRadius": "12px", "padding": "20px",
    })

# ─── App ─────────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
    ],
    title="SaaS MRR Dashboard",
)

app.layout = html.Div(style={
    "background": BG, "minHeight": "100vh",
    "fontFamily": "Inter, sans-serif", "color": TEXT, "padding": "24px",
}, children=[

    # ── Header
    html.Div([
        html.Div([
            html.A(
                html.H1("Revenue Intelligence", style={
                    "margin": "0", "fontSize": "22px", "fontWeight": "700",
                    "background": f"linear-gradient(90deg, {ACCENT}, {BLUE})",
                    "-webkit-background-clip": "text", "-webkit-text-fill-color": "transparent",
                    "cursor": "pointer"
                }),
                href="http://localhost:5501/index.html",
                style={"textDecoration": "none"}
            ),
            html.P("SaaS MRR Growth Dashboard · 2022–2024", style={
                "margin": "2px 0 0 0", "fontSize": "13px", "color": MUTED
            }),
        ]),
        html.Div([
            html.Span("● LIVE DATA", style={
                "color": GREEN, "fontSize": "11px",
                "fontWeight": "700", "letterSpacing": "1px"
            }),
        ], style={"textAlign": "right"}),
    ], style={"display": "flex", "justifyContent": "space-between",
              "alignItems": "flex-start", "marginBottom": "24px"}),

    # ── Upload & Range Slider
    card([
        html.Div([
            html.Div([
                html.H4("Your Data", style={"margin": "0 0 8px 0", "fontSize": "16px", "fontWeight": "600", "color": TEXT}),
                html.P("Upload your own MRR records (.csv, .xlsx, .json) to visualize your company data natively. Or, explore the synthetic Wall Street-grade dataset below.", 
                       style={"color": MUTED, "fontSize": "13px", "margin": "0", "maxWidth": "600px", "lineHeight": "1.5"}),
                html.Div([
                    html.A("Download CSV Template", id="download-template-btn",
                           style={"color": ACCENT, "fontSize": "12px", "textDecoration": "none", "fontWeight": "600", "cursor": "pointer"}),
                ], style={"marginTop": "10px"}),
                dcc.Download(id="download-template")
            ], style={"flex": "1"}),
            html.Div([
                dcc.Upload(
                    id='upload-data',
                    accept='.csv,.xlsx,.xls,.json',
                    children=html.Div([
                        html.Span("Drop CSV/Excel/JSON or ", style={"color": MUTED}),
                        html.A("Browse Files", style={"color": ACCENT, "fontWeight": "600", "cursor": "pointer"})
                    ]),
                    style={
                        'width': '300px', 'height': '60px', 'lineHeight': '60px',
                        'borderWidth': '1.5px', 'borderStyle': 'dashed',
                        'borderRadius': '12px', 'textAlign': 'center',
                        'borderColor': BORDER, 'color': TEXT,
                        'backgroundColor': BG,
                        'transition': 'all 0.3s ease', 'cursor': 'pointer'
                    },
                    multiple=False
                )
            ]),
        ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "20px"}),
        
        html.Div(id="upload-status", style={"fontSize": "13px", "fontWeight": "600", "marginBottom": "16px"}),
    ], style={"marginBottom": "20px", "padding": "24px"}),

    html.Div(id="dashboard-content", style={"display": "none"}, children=[
        card([
            html.P("Select Date Range", style={"color": MUTED, "fontSize": "11px",
                   "textTransform": "uppercase", "letterSpacing": "1px", "margin": "0 0 12px 0"}),
            dcc.RangeSlider(
                id="month-range", min=0, max=len(MONTHS)-1,
                value=[0, len(MONTHS)-1], marks=MONTH_MARKS,
                tooltip={"placement": "bottom", "always_visible": False},
            ),
        ], style={"marginBottom": "20px", "padding": "16px 24px"}),

        # ── KPI Row
        html.Div(id="kpi-row", style={
            "display": "grid", "gridTemplateColumns": "repeat(5, 1fr)",
            "gap": "16px", "marginBottom": "20px",
        }),

    # ── Row 1: MRR Trend + Waterfall
    html.Div([
        card([
            html.H4("MRR Growth Trend", style={"margin": "0 0 12px 0",
                    "fontSize": "14px", "fontWeight": "600", "color": TEXT}),
            dcc.Graph(id="mrr-trend", config={"displayModeBar": False},
                      style={"height": "280px"}),
        ], style={"flex": "1.6"}),
        card([
            html.H4("MRR Waterfall (Last 6 Mo)", style={"margin": "0 0 12px 0",
                    "fontSize": "14px", "fontWeight": "600", "color": TEXT}),
            dcc.Graph(id="mrr-waterfall", config={"displayModeBar": False},
                      style={"height": "280px"}),
        ], style={"flex": "1"}),
    ], style={"display": "flex", "gap": "16px", "marginBottom": "20px"}),

    # ── Row 2: MRR Breakdown + MoM Growth
    html.Div([
        card([
            html.H4("MRR Breakdown by Type", style={"margin": "0 0 12px 0",
                    "fontSize": "14px", "fontWeight": "600", "color": TEXT}),
            dcc.Graph(id="mrr-breakdown", config={"displayModeBar": False},
                      style={"height": "260px"}),
        ], style={"flex": "1"}),
        card([
            html.H4("Month-over-Month Growth Rate (%)", style={"margin": "0 0 12px 0",
                    "fontSize": "14px", "fontWeight": "600", "color": TEXT}),
            dcc.Graph(id="mom-growth", config={"displayModeBar": False},
                      style={"height": "260px"}),
        ], style={"flex": "1"}),
        card([
            html.H4("ARPU & Customer Count", style={"margin": "0 0 12px 0",
                    "fontSize": "14px", "fontWeight": "600", "color": TEXT}),
            dcc.Graph(id="arpu-chart", config={"displayModeBar": False},
                      style={"height": "260px"}),
        ], style={"flex": "1"}),
    ], style={"display": "flex", "gap": "16px", "marginBottom": "20px"}),

    # ── Row 3: Cohort + Plan Pie
    html.Div([
        card([
            html.H4("Cohort MRR Retention (%)", style={"margin": "0 0 12px 0",
                    "fontSize": "14px", "fontWeight": "600", "color": TEXT}),
            dcc.Graph(id="cohort-heatmap", config={"displayModeBar": False},
                      style={"height": "300px"}),
        ], style={"flex": "2"}),
        html.Div([
            card([
                html.H4("Revenue by Plan", style={"margin": "0 0 8px 0",
                        "fontSize": "14px", "fontWeight": "600", "color": TEXT}),
                dcc.Graph(id="plan-pie", config={"displayModeBar": False},
                          style={"height": "130px"}),
            ], style={"marginBottom": "16px"}),
            card([
                html.H4("Revenue by Region", style={"margin": "0 0 8px 0",
                        "fontSize": "14px", "fontWeight": "600", "color": TEXT}),
                dcc.Graph(id="region-bar", config={"displayModeBar": False},
                          style={"height": "130px"}),
            ]),
        ], style={"flex": "1", "display": "flex", "flexDirection": "column"}),
    ], style={"display": "flex", "gap": "16px", "marginBottom": "20px"}),

    # ── Footer
        html.P(
            "Dashboard generated based on uploaded MRR records.",
            style={"color": MUTED, "fontSize": "11px", "textAlign": "center", "marginTop": "8px"}
        ),
    ]) # End of dashboard-content
])


# ─── Callbacks ───────────────────────────────────────────────────────────────

@callback(
    Output("download-template", "data"),
    Input("download-template-btn", "n_clicks"),
    prevent_initial_call=True
)
def download_template(n_clicks):
    template = """month,customer_id,plan,mrr,mrr_type,industry,region
2024-01-01,CUST-001,Pro,399,New,FinTech,Europe
2024-02-01,CUST-001,Pro,399,Retained,FinTech,Europe
2024-03-01,CUST-001,Pro,450,Expansion,FinTech,Europe
2024-04-01,CUST-001,Pro,0,Churned,FinTech,Europe"""
    return dict(content=template, filename="mrr_template.csv")

@callback(
    Output("month-range", "min"),
    Output("month-range", "max"),
    Output("month-range", "marks"),
    Output("month-range", "value"),
    Output("upload-status", "children"),
    Output("upload-status", "style"),
    Output("dashboard-content", "style"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    prevent_initial_call=True
)
def handle_upload(contents, filename):
    global summary, records, customers, cohort, MONTHS, MONTH_MARKS
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Determine file type based on extension
        name_lower = filename.lower()
        if name_lower.endswith('.csv'):
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif name_lower.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(decoded))
        elif name_lower.endswith('.json'):
            try:
                df = pd.read_json(io.StringIO(decoded.decode('utf-8')), orient='records')
            except ValueError:
                df = pd.read_json(io.StringIO(decoded.decode('utf-8')))
        else:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, "Error: Unsupported format. Please upload .csv, .xlsx, or .json", {"color": RED}, dash.no_update
        
        # Normalize column names in order to smoothly handle Excel/CSV variations
        df.columns = df.columns.str.strip().str.lower()
        
        # Fuzzy Matcher: Automatically map the user's random columns to dashboard standards
        aliases = {
            "month": ["month", "date", "time", "period", "timestamp", "created"],
            "customer_id": ["customer_id", "user_id", "client_id", "id", "email"],
            "mrr": ["mrr", "revenue", "price", "amount", "total", "value"],
            "plan": ["plan", "tier", "subscription", "product", "package"],
            "mrr_type": ["mrr_type", "type", "status", "event"],
            "industry": ["industry", "vertical", "sector", "category"],
            "region": ["region", "country", "geo", "state", "location"]
        }
        
        for std_col, possible_names in aliases.items():
            if std_col not in df.columns:
                for name in possible_names:
                    if name in df.columns:
                        df.rename(columns={name: std_col}, inplace=True)
                        break

        # Auto-fill missing optional columns so the dashboard doesn't crash
        if "plan" not in df.columns: df["plan"] = "Standard"
        if "industry" not in df.columns: df["industry"] = "Other"
        if "region" not in df.columns: df["region"] = "Global"
        if "mrr_type" not in df.columns: df["mrr_type"] = "Retained"
        
        req_cols = ["month", "customer_id", "mrr"]
        missing = [c for c in req_cols if c not in df.columns]
        if missing:
            found = list(df.columns)
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, f"Error: Core columns missing: {missing}. Found columns: {found}", {"color": RED}, dash.no_update

        df['month'] = pd.to_datetime(df['month'], errors='coerce')
        if df['month'].isna().any():
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, "Error: Invalid date format in 'month' column.", {"color": RED}, dash.no_update

        new_records = df.copy()
        
        first_months = df.groupby('customer_id')['month'].min().reset_index()
        first_months.rename(columns={'month': 'acquisition_date'}, inplace=True)
        churns = df[df['mrr_type'] == 'Churned'].copy()
        churns.rename(columns={'month': 'churn_date'}, inplace=True)
        custs = pd.merge(first_months, churns[['customer_id', 'churn_date']], on='customer_id', how='left')
        new_customers = custs.copy()
        
        new_summary = build_monthly_summary(new_records)
        new_cohort = build_cohort_data(new_records, new_customers)
        new_summary["month"] = pd.to_datetime(new_summary["month"])
        new_records["month"]  = pd.to_datetime(new_records["month"])
        
        if len(new_summary) == 0:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, "Error: Dataset yielded empty summary.", {"color": RED}, dash.no_update
        
        new_MONTHS = new_summary["month"].dt.strftime("%b %Y").tolist()
        new_MONTH_MARKS = {i: new_MONTHS[i] for i in range(0, len(new_MONTHS), max(1, len(new_MONTHS)//8))}
        
        # Commit changes to global variables only after successful processing
        records = new_records
        customers = new_customers
        summary = new_summary
        cohort = new_cohort
        MONTHS = new_MONTHS
        MONTH_MARKS = new_MONTH_MARKS
        
        return 0, len(MONTHS)-1, MONTH_MARKS, [0, len(MONTHS)-1], f"Successfully loaded {filename}! Dashboard updated.", {"color": GREEN}, {"display": "block"}

    except Exception as e:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, f"Error Processing File: {str(e)}", {"color": RED}, dash.no_update

@callback(
    Output("kpi-row", "children"),
    Output("mrr-trend", "figure"),
    Output("mrr-waterfall", "figure"),
    Output("mrr-breakdown", "figure"),
    Output("mom-growth", "figure"),
    Output("arpu-chart", "figure"),
    Output("cohort-heatmap", "figure"),
    Output("plan-pie", "figure"),
    Output("region-bar", "figure"),
    Input("month-range", "value"),
)
def update_all(month_range):
    lo, hi = month_range
    df = summary.iloc[lo:hi+1].copy()
    rec_filt = records[
        (records["month"] >= df["month"].iloc[0]) &
        (records["month"] <= df["month"].iloc[-1])
    ]
    months_x = df["month"].dt.strftime("%b %y")

    # ── KPIs
    latest = df.iloc[-1]
    prev   = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
    mrr_delta = (latest["total_mrr"] - prev["total_mrr"]) / prev["total_mrr"] * 100

    total_new_cust = customers[
        (pd.to_datetime(customers["acquisition_date"]).dt.to_period("M") >=
         pd.to_datetime(df["month"].iloc[0]).to_period("M")) &
        (pd.to_datetime(customers["acquisition_date"]).dt.to_period("M") <=
         pd.to_datetime(df["month"].iloc[-1]).to_period("M"))
    ]
    churned_count = total_new_cust[total_new_cust["churn_date"].notna()]
    churn_rate = len(churned_count) / max(len(total_new_cust), 1) * 100

    kpis = html.Div([
        kpi("Current MRR",   f"${latest['total_mrr']:,.0f}", mrr_delta, "MoM"),
        kpi("ARR Run-Rate",  f"${latest['arr']:,.0f}"),
        kpi("Active Customers", f"{int(latest['active_customers'])}",
            (latest['active_customers'] - prev['active_customers']) / max(prev['active_customers'],1) * 100, "MoM"),
        kpi("ARPU",          f"${latest['arpu']:,.0f}",
            (latest['arpu'] - prev['arpu']) / max(prev['arpu'],1) * 100, "MoM"),
        kpi("Churn Rate",    f"{churn_rate:.1f}%"),
    ], style={
        "display": "grid", "gridTemplateColumns": "repeat(5, 1fr)", "gap": "16px",
    })

    # ── MRR Trend
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=months_x, y=df["total_mrr"], name="Total MRR",
        line=dict(color=ACCENT, width=2.5), fill="tozeroy",
        fillcolor=f"rgba(124,110,247,0.08)",
        hovertemplate="<b>%{x}</b><br>MRR: $%{y:,.0f}<extra></extra>",
    ))
    fig_trend.add_trace(go.Scatter(
        x=months_x, y=df["arr"] / 12, name="ARR / 12",
        line=dict(color=BLUE, width=1.5, dash="dot"),
        hovertemplate="<b>%{x}</b><br>ARR/12: $%{y:,.0f}<extra></extra>",
    ))
    fig_trend.update_layout(**CHART_LAYOUT)
    fig_trend.update_yaxes(tickprefix="$", tickformat=",")

    # ── Waterfall (last 6 months)
    w = df.tail(6)
    wm = w["month"].dt.strftime("%b %y").tolist()
    measure = ["relative"] * len(w)
    y_vals  = w["net_new_mrr"].tolist()
    text    = [f"${v:+,.0f}" for v in y_vals]
    colors  = [GREEN if v >= 0 else RED for v in y_vals]

    fig_wf = go.Figure(go.Waterfall(
        x=wm, measure=measure, y=y_vals, text=text,
        textposition="outside",
        increasing=dict(marker_color=GREEN),
        decreasing=dict(marker_color=RED),
        connector=dict(line=dict(color=BORDER, width=1)),
        textfont=dict(size=10, color=TEXT),
    ))
    fig_wf.update_layout(**CHART_LAYOUT)
    fig_wf.update_yaxes(tickprefix="$", tickformat=",")

    # ── MRR Breakdown stacked bar
    fig_bd = go.Figure()
    fig_bd.add_trace(go.Bar(x=months_x, y=df["new_mrr"],       name="New",
                             marker_color=GREEN,  hovertemplate="New: $%{y:,.0f}<extra></extra>"))
    fig_bd.add_trace(go.Bar(x=months_x, y=df["expansion_mrr"], name="Expansion",
                             marker_color=BLUE,   hovertemplate="Expansion: $%{y:,.0f}<extra></extra>"))
    fig_bd.add_trace(go.Bar(x=months_x, y=-df["contraction_mrr"], name="Contraction",
                             marker_color=AMBER,  hovertemplate="Contraction: $%{y:,.0f}<extra></extra>"))
    fig_bd.add_trace(go.Bar(x=months_x, y=-df["churned_mrr"],  name="Churned",
                             marker_color=RED,    hovertemplate="Churned: $%{y:,.0f}<extra></extra>"))
    fig_bd.update_layout(**dict(CHART_LAYOUT, barmode="relative"))
    fig_bd.update_yaxes(tickprefix="$", tickformat=",")

    # ── MoM Growth
    colors_mom = [GREEN if v >= 0 else RED for v in df["mom_growth"].fillna(0)]
    fig_mom = go.Figure(go.Bar(
        x=months_x, y=df["mom_growth"].fillna(0),
        marker_color=colors_mom,
        hovertemplate="<b>%{x}</b><br>Growth: %{y:.1f}%<extra></extra>",
    ))
    fig_mom.add_hline(y=0, line_color=BORDER, line_width=1)
    fig_mom.update_layout(**CHART_LAYOUT)
    fig_mom.update_yaxes(ticksuffix="%")

    # ── ARPU dual axis
    fig_arpu = make_subplots(specs=[[{"secondary_y": True}]])
    fig_arpu.add_trace(go.Scatter(
        x=months_x, y=df["arpu"], name="ARPU",
        line=dict(color=AMBER, width=2),
        hovertemplate="ARPU: $%{y:,.0f}<extra></extra>",
    ), secondary_y=False)
    fig_arpu.add_trace(go.Scatter(
        x=months_x, y=df["active_customers"], name="Customers",
        line=dict(color=ACCENT, width=2, dash="dot"),
        hovertemplate="Customers: %{y:,.0f}<extra></extra>",
    ), secondary_y=True)
    fig_arpu.update_layout(**CHART_LAYOUT)
    fig_arpu.update_yaxes(tickprefix="$", secondary_y=False,
                           gridcolor=BORDER, tickfont=dict(size=10))
    fig_arpu.update_yaxes(tickformat=",", secondary_y=True,
                           gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10))

    # ── Cohort heatmap
    pivot = cohort[cohort["period"] <= 11].pivot_table(
        index="cohort", columns="period", values="retention_pct"
    )
    pivot.index = pd.to_datetime(pivot.index).strftime("%b %Y")
    # Keep latest 10 cohorts
    pivot = pivot.tail(10)

    fig_coh = go.Figure(go.Heatmap(
        z=pivot.values, x=[f"M+{c}" for c in pivot.columns],
        y=pivot.index.tolist(),
        colorscale=[[0, "#1a0a0a"], [0.5, "#7c2d12"], [0.75, AMBER], [1, GREEN]],
        text=pivot.values.round(0),
        texttemplate="%{text}%",
        showscale=True,
        colorbar=dict(tickfont=dict(color=TEXT), outlinewidth=0,
                      ticksuffix="%", thickness=12),
        hovertemplate="Cohort: %{y}<br>Period: %{x}<br>Retention: %{z:.1f}%<extra></extra>",
    ))
    fig_coh.update_layout(**{**CHART_LAYOUT, 'margin': dict(l=80, r=10, t=10, b=10)})
    fig_coh.update_xaxes(side="top")

    # ── Plan Pie
    plan_rev = rec_filt[rec_filt["mrr"] > 0].groupby("plan")["mrr"].sum()
    fig_pie = go.Figure(go.Pie(
        labels=plan_rev.index, values=plan_rev.values,
        hole=0.55,
        marker=dict(colors=[ACCENT, BLUE, GREEN, AMBER],
                    line=dict(color=BG, width=2)),
        textfont=dict(size=10, color=TEXT),
        hovertemplate="%{label}: $%{value:,.0f} (%{percent})<extra></extra>",
    ))
    fig_pie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=0, b=0),
        font=dict(color=TEXT), showlegend=True,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
    )

    # ── Region bar (horizontal)
    reg_rev = rec_filt[rec_filt["mrr"] > 0].groupby("region")["mrr"].sum().sort_values()
    fig_reg = go.Figure(go.Bar(
        x=reg_rev.values, y=reg_rev.index, orientation="h",
        marker=dict(color=reg_rev.values,
                    colorscale=[[0, BORDER], [1, ACCENT]],
                    showscale=False),
        hovertemplate="%{y}: $%{x:,.0f}<extra></extra>",
    ))
    fig_reg.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, size=10), margin=dict(l=0, r=10, t=0, b=0),
        xaxis=dict(gridcolor=BORDER, tickprefix="$", tickformat=",", tickfont=dict(size=9)),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=9)),
    )

    return (kpis, fig_trend, fig_wf, fig_bd, fig_mom,
            fig_arpu, fig_coh, fig_pie, fig_reg)


if __name__ == "__main__":
    app.run(debug=True, port=8050)
