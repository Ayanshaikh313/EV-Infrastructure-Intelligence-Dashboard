"""
EV Infrastructure Intelligence System
Advanced Multi-page Dashboard with Forecasting & Analytics

Models Supported:
- Linear Regression
- Polynomial Regression
- ARIMA
"""

# ======================================================
# IMPORTS
# ======================================================
import os
import streamlit as st
import pandas as pd
import numpy as np
import pickle
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

from config import *
from map_utils import create_map

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "ev_forecast_model_v2.pkl")
DATA_PATH = os.path.join(BASE_DIR, "data", "final_master_report.csv")

# ======================================================
# PAGE CONFIGURATION
# ======================================================
st.set_page_config(
    page_title="EV Infrastructure Intelligence",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================================================
# CUSTOM STYLES
# ======================================================
st.markdown("""
<style>
.metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px;
    border-radius: 10px;
    color: white;
    text-align: center;
}
.risk-high { background: #ff4444 !important; }
.risk-medium { background: #ffaa00 !important; }
.risk-low { background: #00C851 !important; }
</style>
""", unsafe_allow_html=True)

# ======================================================
# SIDEBAR – NAVIGATION
# ======================================================
st.sidebar.title("🧭 Navigation")

page = st.sidebar.radio(
    "Select Page",
    [
        "📊 Dashboard",
        "🚗 EV Adoption Analysis",
        "🔌 Infrastructure Readiness",
        "🤖 ML Predictions",
        "🏙️ City Comparison",
        "📂 Data Sources"
    ]
)

# ======================================================
# LOAD MODEL (SINGLE UNIFIED BUNDLE)
# ======================================================
@st.cache_resource
def load_model_bundle():
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)

model_data = load_model_bundle()

# ======================================================
# LOAD DATA
# ======================================================
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)
    year_cols = sorted([c for c in df.columns if c.isdigit()], key=int)

    def categorize(f):
        f = str(f).upper()
        if "EV" in f or "ELECTRIC" in f:
            return "EV"
        if "CNG" in f:
            return "CNG"
        if "HYBRID" in f:
            return "HYBRID"
        if "PETROL" in f or "GASOLINE" in f:
            return "PETROL"
        if "DIESEL" in f:
            return "DIESEL"
        return "OTHER"

    df["Category"] = df["Fuel"].apply(categorize)
    df["Total_Vehicles"] = df[year_cols].sum(axis=1)
    return df, year_cols

df, year_cols = load_data()

# ======================================================
# SIDEBAR – CONTROLS
# ======================================================
st.sidebar.header("⚙️ Controls")

model_choice = st.sidebar.selectbox(
    "Select Prediction Model",
    ["Linear Regression", "Polynomial Regression", "ARIMA"]
)

rto = st.sidebar.selectbox(
    "Select RTO Office",
    sorted(df["RTO Office"].unique())
)

forecast_years = st.sidebar.slider(
    "Forecast Horizon (Years)",
    3, 10, 5
)

# ======================================================
# GEOCODING (PUNE BUG FIXED)
# ======================================================
@st.cache_data
def get_coordinates(rto_name):
    rto_clean = rto_name.strip().upper()

    if rto_clean in RTO_COORDS:
        return RTO_COORDS[rto_clean]

    try:
        geolocator = Nominatim(user_agent="ev_infra_app")
        location = geolocator.geocode(f"{rto_clean}, Maharashtra, India", timeout=10)
        if location:
            return (location.latitude, location.longitude)
    except GeocoderTimedOut:
        pass

    return (19.7515, 75.7139)  # Maharashtra center fallback

lat, lon = get_coordinates(rto)

# ======================================================
# COMMON DATA PROCESSING
# ======================================================
rto_df = df[(df["RTO Office"] == rto) & (df["Category"] == "EV")]
all_rto_df = df[df["RTO Office"] == rto]

y_hist = rto_df[year_cols].sum().values
X_hist = np.array([int(y) for y in year_cols]).reshape(-1, 1)

# ======================================================
# STATE-LEVEL FORECAST (MODEL ROUTER)
# ======================================================
last_year = int(year_cols[-1])
future_years_arr = np.array(
    [[last_year + i] for i in range(1, forecast_years + 1)]
)

def predict_state(X):
    if model_choice == "Linear Regression":
        return model_data["linear"].predict(X)

    elif model_choice == "Polynomial Regression":
        poly = model_data["poly"]["transformer"]
        model = model_data["poly"]["model"]
        return model.predict(poly.transform(X))

    elif model_choice == "ARIMA":
        return model_data["arima"].forecast(steps=len(X))

state_pred = predict_state(future_years_arr)

# ======================================================
# RTO SHARE LOGIC
# ======================================================
state_ev_total = df[df["Category"] == "EV"]["Total_Vehicles"].sum()
rto_ev_total = rto_df["Total_Vehicles"].sum()
rto_share = rto_ev_total / state_ev_total if state_ev_total > 0 else 0

rto_pred = state_pred * rto_share

# ======================================================
# INFRASTRUCTURE CALCULATIONS
# ======================================================
estimated_state_chargers = NATIONAL_EV_CHARGERS * MAHARASHTRA_EV_SHARE
estimated_rto_chargers = int(estimated_state_chargers * rto_share)

needed_chargers = int(rto_pred[-1] / EV_CHARGER_RATIO)
gap = needed_chargers - estimated_rto_chargers

ev_per_charger = (
    rto_pred[-1] / estimated_rto_chargers
    if estimated_rto_chargers > 0 else 999
)

if ev_per_charger <= 10:
    risk_level, risk_color = "LOW", "🟢"
elif ev_per_charger <= 20:
    risk_level, risk_color = "MODERATE", "🟡"
else:
    risk_level, risk_color = "HIGH", "🔴"

# ======================================================
# PAGE 1: DASHBOARD
# ======================================================
if page == "📊 Dashboard":
    st.title("🚗 EV Infrastructure Intelligence Dashboard")
    st.markdown(f"**Selected RTO:** {rto} | **Analysis Year:** {last_year}")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Current EVs", f"{int(rto_ev_total):,}")
    col2.metric("Projected EVs", f"{int(rto_pred[-1]):,}")
    col3.metric("Existing Chargers", estimated_rto_chargers)
    col4.metric("Charger Gap", gap)
    col5.markdown(
        f"<div class='metric-card risk-{risk_level.lower()}'>"
        f"<h3>{risk_color} {risk_level}</h3><p>Infra Risk</p></div>",
        unsafe_allow_html=True
    )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=X_hist.flatten(),
        y=y_hist,
        name="Historical",
        mode="lines+markers"
    ))
    fig.add_trace(go.Scatter(
        x=future_years_arr.flatten(),
        y=rto_pred,
        name="Forecast",
        mode="lines+markers",
        line=dict(dash="dash")
    ))
    fig.update_layout(
        title="EV Adoption Trend (RTO Level)",
        xaxis_title="Year",
        yaxis_title="EV Registrations"
    )
    st.plotly_chart(fig, use_container_width=True)

    popup = f"""
    <b>RTO:</b> {rto}<br>
    <b>Projected EVs:</b> {int(rto_pred[-1]):,}<br>
    <b>Chargers Needed:</b> {needed_chargers}<br>
    <b>Gap:</b> {gap}<br>
    <b>Risk:</b> {risk_color} {risk_level}
    """
    m = create_map(lat, lon, popup, "red" if risk_level == "HIGH" else "orange")
    st_folium(m, height=450)

# ======================================================
# PAGE 2–6 (UNCHANGED)
# ======================================================
elif page == "🚗 EV Adoption Analysis":
    fuel_mix = all_rto_df.groupby("Category")["Total_Vehicles"].sum().reset_index()
    fig = px.pie(fuel_mix, values="Total_Vehicles", names="Category",
                 title="Fuel Mix Distribution")
    st.plotly_chart(fig, use_container_width=True)

elif page == "🔌 Infrastructure Readiness":
    st.metric("EVs per Charger", f"{ev_per_charger:.1f}")
    st.metric("Risk Level", f"{risk_color} {risk_level}")

elif page == "🤖 ML Predictions":
    st.json(model_data["metrics"])

elif page == "🏙️ City Comparison":
    selected_rtos = st.multiselect("Select RTOs", sorted(df["RTO Office"].unique()))
    if len(selected_rtos) >= 2:
        comp_df = pd.DataFrame([
            {"RTO": r, "EVs": df[(df["RTO Office"] == r) &
                                 (df["Category"] == "EV")]["Total_Vehicles"].sum()}
            for r in selected_rtos
        ])
        fig = px.bar(comp_df, x="RTO", y="EVs", title="EV Comparison")
        st.plotly_chart(fig, use_container_width=True)

elif page == "📂 Data Sources":
    st.markdown("""
    **Primary Sources**
    - Ministry of Road Transport & Highways – Vahan Dashboard
    - Bureau of Energy Efficiency – EV Charging Infrastructure
    - International Energy Agency – EV Benchmarks
    """)