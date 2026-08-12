"""
Streamlit dashboard over the gold layer. To close the dashboard, hit Ctrl-C in the terminal. 
One scrollable page with the two things the gold layer is built for:
  1. Multi-dimensional sales analysis (from gold.fact_order_items + gold.fact_orders)
  2. Market basket analysis (from the gold basket / group facts)
Run either way (both work, just like duckdb_ui.py):
    python dashboard.py          # relaunches itself under streamlit
    streamlit run dashboard.py
Reads the warehouse read-only, so it never locks the DB against the pipeline.
"""
import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st
from config import DB_PATH


def _ensure_streamlit() -> None:
    """Let `python dashboard.py` behave like duckdb_ui.py: if we're not already
    inside a Streamlit runtime, relaunch this file under `streamlit run`."""
    import streamlit.runtime
    if streamlit.runtime.exists():
        return  # already running under `streamlit run` — carry on and render
    import sys
    from pathlib import Path
    from streamlit.web import cli as stcli
    sys.argv = ["streamlit", "run", str(Path(__file__).resolve())]
    raise SystemExit(stcli.main())


_ensure_streamlit()

# ---- design-system palette (fixed categorical hue order) -------------------
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
               "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
BLUE, MUTED, GRID, AXIS = "#2a78d6", "#898781", "#e1e0d9", "#c3c2b7"
CUSTOMER_COLORS = {"new": "#2a78d6", "returning": "#eb6834", "guest": "#1baf7a"}

st.set_page_config(page_title="Chozen — Gold Layer Dashboard", layout="wide")


# ---- data access (read-only + cached) --------------------------------------
@st.cache_resource
def get_con():
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data
def load(table: str) -> pd.DataFrame:
    return get_con().execute(f"SELECT * FROM gold.{table}").df()


items = load("fact_order_items")
items["order_date"] = pd.to_datetime(items["order_date"])
product_pairs = load("fact_product_pairs")
vendor_pairs = load("fact_vendor_pairs")
product_groups = load("fact_product_groups")
vendor_groups = load("fact_vendor_groups")


def style(fig, horizontal: bool = False):
    """Consistent chrome: recessive grid/axes, system font, tidy margins."""
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif',
                  color="#0b0b0b", size=13),
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
        hoverlabel=dict(font_size=12),
    )
    grid_axis, plain_axis = fig.update_yaxes, fig.update_xaxes
    if horizontal:
        grid_axis, plain_axis = fig.update_xaxes, fig.update_yaxes
    grid_axis(showgrid=True, gridcolor=GRID, zeroline=False, color=MUTED)
    plain_axis(showgrid=False, linecolor=AXIS, tickcolor=AXIS, color=MUTED)
    return fig


# ---- header ----------------------------------------------------------------
st.title("Chozen — Gold Layer Dashboard")
st.caption("Shopify sales & market-basket analysis, served from the DuckDB gold schema.")

# ---- sidebar filters (apply to the sales section) --------------------------
st.sidebar.header("Filters")
dmin, dmax = items["order_date"].min().date(), items["order_date"].max().date()
picked_dates = st.sidebar.date_input("Order date range", (dmin, dmax),
                                     min_value=dmin, max_value=dmax)
if isinstance(picked_dates, tuple) and len(picked_dates) == 2:
    start, end = picked_dates
else:
    start, end = dmin, dmax

all_sources = sorted(items["source"].unique())
picked_sources = st.sidebar.multiselect("Marketing source", all_sources, default=all_sources)
st.sidebar.caption("Filters apply to the sales section. Basket tables are pre-aggregated over all orders.")

mask = (
    (items["order_date"].dt.date >= start)
    & (items["order_date"].dt.date <= end)
    & (items["source"].isin(picked_sources))
)
fi = items[mask]

# ============================================================================
# 1. SALES ANALYSIS
# ============================================================================
st.header("Sales analysis")

if fi.empty:
    st.info("No rows for the current filters.")
else:
    revenue = fi["line_revenue"].sum()
    orders = fi["order_id"].nunique()
    units = int(fi["quantity"].sum())
    customers = fi["customer_id"].nunique()
    aov = revenue / orders if orders else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Revenue", f"${revenue:,.0f}")
    k2.metric("Orders", f"{orders:,}")
    k3.metric("Units", f"{units:,}")
    k4.metric("Avg order value", f"${aov:,.0f}")
    k5.metric("Customers", f"{customers:,}")

    # revenue over time (monthly)
    st.subheader("Revenue over time")
    monthly = (fi.assign(month=fi["order_date"].dt.to_period("M").dt.to_timestamp())
                 .groupby("month", as_index=False)["line_revenue"].sum())
    fig = px.line(monthly, x="month", y="line_revenue", markers=True,
                  color_discrete_sequence=[BLUE],
                  labels={"month": "", "line_revenue": "Revenue ($)"})
    fig.update_traces(line_width=2, marker_size=7)
    st.plotly_chart(style(fig), use_container_width=True)

    c_left, c_right = st.columns(2)

    # revenue by marketing source
    with c_left:
        st.subheader("Revenue by source")
        by_source = (fi.groupby("source", as_index=False)["line_revenue"].sum()
                       .sort_values("line_revenue", ascending=False))
        fig = px.bar(by_source, x="source", y="line_revenue",
                     color="source", color_discrete_sequence=CATEGORICAL,
                     labels={"source": "", "line_revenue": "Revenue ($)"})
        fig.update_layout(showlegend=False)
        st.plotly_chart(style(fig), use_container_width=True)

    # new vs returning
    with c_right:
        st.subheader("Revenue by customer type")
        by_type = (fi.groupby("customer_type", as_index=False)["line_revenue"].sum()
                     .sort_values("line_revenue", ascending=False))
        fig = px.bar(by_type, x="customer_type", y="line_revenue",
                     color="customer_type", color_discrete_map=CUSTOMER_COLORS,
                     labels={"customer_type": "", "line_revenue": "Revenue ($)"})
        fig.update_layout(showlegend=False)
        st.plotly_chart(style(fig), use_container_width=True)

    c_left, c_right = st.columns(2)

    # top categories
    with c_left:
        st.subheader("Top categories by revenue")
        by_cat = (fi.groupby("category", as_index=False)["line_revenue"].sum()
                    .sort_values("line_revenue", ascending=True).tail(10))
        fig = px.bar(by_cat, x="line_revenue", y="category", orientation="h",
                     color_discrete_sequence=[BLUE],
                     labels={"line_revenue": "Revenue ($)", "category": ""})
        st.plotly_chart(style(fig, horizontal=True), use_container_width=True)

    # top products
    with c_right:
        st.subheader("Top products by revenue")
        by_prod = (fi.groupby("title", as_index=False)["line_revenue"].sum()
                     .sort_values("line_revenue", ascending=True).tail(10))
        fig = px.bar(by_prod, x="line_revenue", y="title", orientation="h",
                     color_discrete_sequence=[BLUE],
                     labels={"line_revenue": "Revenue ($)", "title": ""})
        st.plotly_chart(style(fig, horizontal=True), use_container_width=True)

# ============================================================================
# 2. MARKET BASKET ANALYSIS
# ============================================================================
st.header("Market basket analysis")
st.caption("Synthetic orders use random baskets, so lift sits near 1.0 (chance). "
           "The pipeline is the deliverable; real associations are expected on live Chozen data.")

basket_tab = st.radio("Basket by", ["Products", "Vendors"], horizontal=True)

if basket_tab == "Products":
    pairs, groups = product_pairs, product_groups
    label_a, label_b = "product_a", "product_b"
    group_members = "member_titles"
else:
    pairs, groups = vendor_pairs, vendor_groups
    label_a, label_b = "vendor_a", "vendor_b"
    group_members = "members"

# --- pairs ---
st.subheader("Top pairs bought together")
if pairs.empty:
    st.info("No pairs cleared the minimum-support cutoff.")
else:
    lo, hi = int(pairs["pair_orders"].min()), int(pairs["pair_orders"].max())
    min_orders = st.slider("Minimum orders together", lo, hi, lo) if hi > lo else lo
    p = pairs[pairs["pair_orders"] >= min_orders].copy()
    p["pair"] = p[label_a].astype(str) + "  +  " + p[label_b].astype(str)
    top = p.sort_values("lift", ascending=True).tail(12)
    fig = px.bar(top, x="lift", y="pair", orientation="h",
                 color_discrete_sequence=[CATEGORICAL[1]],
                 labels={"lift": "Lift (1 = chance)", "pair": ""})
    fig.add_vline(x=1.0, line_dash="dash", line_color=MUTED)
    st.plotly_chart(style(fig, horizontal=True), use_container_width=True)
    st.dataframe(
        p.sort_values("lift", ascending=False)[
            [label_a, label_b, "pair_orders", "support", "confidence_a_to_b",
             "confidence_b_to_a", "lift"]
        ].reset_index(drop=True),
        use_container_width=True, hide_index=True,
    )

# --- groups (size-selectable) ---
st.subheader("Frequent groups")
if groups.empty:
    st.info("No groups cleared the minimum-support cutoff.")
else:
    sizes = sorted(groups["group_size"].unique())
    size = st.selectbox("Group size", sizes, index=0)
    g = groups[groups["group_size"] == size].sort_values("group_orders", ascending=False)
    st.write(f"{len(g)} groups of size {size}")
    top = g.head(12).sort_values("group_orders", ascending=True)
    fig = px.bar(top, x="group_orders", y=group_members, orientation="h",
                 color_discrete_sequence=[BLUE],
                 labels={"group_orders": "Orders containing the group", group_members: ""})
    st.plotly_chart(style(fig, horizontal=True), use_container_width=True)
    st.dataframe(
        g[[group_members, "group_orders", "support", "lift"]].reset_index(drop=True),
        use_container_width=True, hide_index=True,
    )
