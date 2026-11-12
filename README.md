# EV Infrastructure Intelligence

A Streamlit dashboard for exploring electric-vehicle registrations and estimating charging-infrastructure needs across Regional Transport Office (RTO) areas in Maharashtra, India. The app combines a historical vehicle-registration CSV, a serialized forecast-model bundle, planning assumptions, interactive charts, and an RTO map.

> **Use as a planning prototype, not an official forecast.** Charger counts are inferred from statewide assumptions and each RTO's share of historical EV registrations. The model is trained on only four annual observations (2022–2025), and its displayed fit metrics are in-sample. Validate the data, definitions, and assumptions before using results for investment or policy decisions.

## What it does

- Shows historical EV registrations and a selectable 3–10 year model forecast for an RTO.
- Offers Linear Regression, degree-2 Polynomial Regression, and ARIMA forecasts.
- Estimates charger demand, an estimated charger allocation, the resulting gap, and a simple EVs-per-charger risk band.
- Displays fuel-category mix, a basic RTO comparison chart, model-bundle metrics, and an interactive map.
- Uses cached Streamlit data/model loading to avoid reloading those resources on every interaction.

## Quick start

### Requirements

- Python 3.10 or later (Python 3.10/3.11 is a practical choice for the pinned scientific Python dependencies).
- The files in `data/` and `models/` included in this repository.
- Network access is only needed if the selected RTO has no configured coordinates and the app must use Nominatim geocoding. The map also needs access to its map tile provider to render tiles.

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app/app.py
```

If PowerShell prevents environment activation, run the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app/app.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app/app.py
```

Streamlit prints a local URL (usually `http://localhost:8501`) when the app is ready.

## Using the dashboard

1. Choose a page from the navigation radio in the sidebar.
2. Select a forecasting model, an RTO office, and a forecast horizon (3–10 years).
3. On **Dashboard**, review current-period totals, the forecast, estimated chargers, the gap and risk band, the historical/forecast chart, and map.
4. Use **EV Adoption Analysis** to inspect the selected RTO's fuel-category mix.
5. Use **Infrastructure Readiness** for the estimated EVs-per-charger ratio and risk label.
6. Use **City Comparison** to select at least two RTOs and compare their summed EV counts.
7. Use **ML Predictions** to inspect metrics saved inside the loaded model bundle.

The CSV and model are read when the app runs. Streamlit caches the CSV with `st.cache_data` and the model object with `st.cache_resource`.

## Data and model artifacts

### Registration data

[`data/final_master_report.csv`](data/final_master_report.csv) is the dashboard's main input. It has 970 rows and six columns: `Fuel`, `RTO Office`, and annual columns `2022`, `2023`, `2024`, and `2025`. It represents 62 distinct RTO labels. The app calculates category totals by summing the annual columns; the annual EV totals under the app's current fuel-classification rule are:

| Year | EV-classified registrations |
|---|---:|
| 2022 | 159,291 |
| 2023 | 224,549 |
| 2024 | 284,521 |
| 2025 | 320,581 |

These are totals derived from the checked-in CSV using the app's rule, not independently verified official statistics. The repository does not include row-level source URLs or a data-refresh pipeline. The app's **Data Sources** page lists VAHAN, BEE, and IEA as references, but does not establish that every CSV value was retrieved directly from those sources.

The annual columns are added together into `Total_Vehicles`. Consequently, the dashboard's **Current EVs** KPI and the **City Comparison** bars use the sum across 2022–2025, not just 2025 and not a deduplicated count of vehicles currently on the road. They should be interpreted as totals of the supplied annual registration counts.

### Fuel classification

In `app/app.py`, a fuel value is assigned to `EV` if its uppercase text contains `EV` or `ELECTRIC`; otherwise it is checked for CNG, hybrid, petrol/gasoline, and diesel, with unmatched values assigned `OTHER`. As a result, labels such as `PLUG-IN HYBRID EV` and `STRONG HYBRID EV` are included in the app's EV totals. This is a string-matching convention, not a fully validated vehicle taxonomy.

### Forecast model bundle

[`models/ev_forecast_model_v2.pkl`](models/ev_forecast_model_v2.pkl) is the bundle loaded by the application. [`notebooks/train_model1.ipynb`](notebooks/train_model1.ipynb) documents the bundle structure: linear regression, polynomial regression with a degree-2 `PolynomialFeatures` transformer, an ARIMA fit, model metrics, training years, and training timestamp. The app routes the selected model to forecast state-level totals, then allocates that forecast to an RTO using its historical share.

[`models/model_metrics.json`](models/model_metrics.json) is a separate metrics file; the app's ML Predictions page reads `model_data["metrics"]` from the pickle bundle rather than loading this JSON file. The JSON reports R² 0.9847, MAE 7,299.5, RMSE 7,590.74, and MAPE 3.03% for years 2022–2025. These should not be interpreted as holdout performance: the training notebook calculates these metrics on the same four annual points used to fit the linear model.

The older [`models/ev_forecast_model.pkl`](models/ev_forecast_model.pkl) is not the path selected by the current app.

## How the calculations work

### Data preparation

1. Read the CSV with pandas.
2. Detect year columns by checking which column names contain digits only; sort them chronologically.
3. Categorize each fuel label and sum the year columns into `Total_Vehicles`.
4. Filter the selected RTO for EV-classified rows; separately retain all fuel categories for the fuel-mix chart.

### Forecast and RTO allocation

1. Create future year inputs from the last data year plus the selected horizon.
2. Predict statewide values using the chosen fitted model.
3. Calculate the selected RTO's share as its sum of EV registrations across all available years divided by the corresponding statewide sum.
4. Multiply each statewide forecast by that fixed historical share to produce the RTO forecast.

This is a fixed-share allocation, not an independently trained model for each RTO. It assumes the RTO's relative share remains unchanged over the forecast horizon.

### Charger planning estimate

The current constants in `app/config.py` are:

- `NATIONAL_EV_CHARGERS = 12,000`
- `MAHARASHTRA_EV_SHARE = 0.18`
- `EV_CHARGER_RATIO = 10`

The app estimates 2,160 chargers statewide (`12,000 × 0.18`), allocates those chargers to the RTO using the same historical EV share, and calculates required chargers as projected RTO EVs divided by 10. The displayed gap is required chargers minus estimated allocated chargers. The risk band uses projected EVs per estimated charger: at most 10 is LOW, at most 20 is MODERATE, and above 20 is HIGH. When the estimated charger count is zero, the app uses 999 as a sentinel ratio, resulting in HIGH risk.

These are scenario calculations based on fixed assumptions, not a live charger inventory, a capacity/usage model, or a geospatial site plan. The computed gap is not clamped to zero, so a negative value means the estimate exceeds the modelled requirement.

## Project structure

```text
.
├── app/
│   ├── app.py             # Streamlit pages, data/model orchestration, calculations
│   ├── config.py          # Constants, RTO coordinates, source references, paths
│   ├── map_utils.py       # Folium map construction and map controls
│   └── utils.py           # Reusable formatting, risk, investment, and action helpers
├── data/
│   └── final_master_report.csv
├── models/
│   ├── ev_forecast_model.pkl
│   ├── ev_forecast_model_v2.pkl
│   └── model_metrics.json
├── notebooks/
│   ├── train_model.ipynb  # Earlier linear-regression training workflow
│   └── train_model1.ipynb # Multi-model bundle training workflow
├── docs/
│   └── ev-infrastructure-intelligence-interview-prep.pdf
├── requirements.txt
└── README.md
```

### Main dependencies

The dependency versions are listed in [`requirements.txt`](requirements.txt). The app uses Streamlit for the interface, pandas/NumPy for tabular calculations, scikit-learn and statsmodels for forecasting, Plotly for charts, Folium with `streamlit-folium` for maps, and geopy for fallback geocoding.

## Limitations and responsible interpretation

- **Very short time series:** the model has four annual observations (2022–2025). A high in-sample R² on four points does not demonstrate reliable future forecasting. Compare against simple baselines and use time-based holdouts or rolling-origin validation before relying on forecasts.
- **Metric/model scope:** the JSON metrics correspond to a linear model fit over the historical years. They are not clearly identified as a holdout test set and should not be treated as evidence that all three selectable models perform equally well.
- **Hybrid taxonomy:** current substring matching counts some hybrid-labelled vehicles as EVs. Confirm the intended definition (battery electric only versus plug-in/other hybrids) and normalize categories with a documented mapping.
- **Fixed RTO share:** future RTO forecasts inherit the historical share over all years. Local adoption trajectories may change, and the shares are not forecast separately.
- **Infrastructure assumptions:** national public charger count and Maharashtra share are constants. The app does not load an RTO-level operational charger inventory; its "Existing Chargers" value is an allocation estimate.
- **Potential negatives/scale mismatch:** model forecasts and gaps are not constrained to non-negative values. The share denominator uses totals over all supplied years, not only the latest year.
- **Mapping:** only configured coordinate keys that match the normalized RTO string are used directly. Other names trigger a network geocoding request and then fall back to a Maharashtra-centre coordinate if no result is returned.
- **Model artifact trust:** Python pickle files can execute code when loaded. Load only model artifacts from a trusted source.
- **Production readiness:** the app currently has no automated test suite, explicit schema validation, or documented update/monitoring workflow for the data and model artifacts.

## Interview preparation

The accompanying [EV Infrastructure Intelligence Interview Prep PDF](docs/ev-infrastructure-intelligence-interview-prep.pdf) contains project-specific questions, concise answer frameworks, model-metric explanations, and limitations to discuss candidly.

For a strong project explanation, cover the full path: CSV and model bundle → category/annual aggregation → model forecast → historical RTO-share allocation → charger scenario calculations → Streamlit charts and map. Be clear about which numbers are observed in the CSV and which are estimates generated from assumptions.

## References shown by the app

- VAHAN Dashboard — <https://vahan.parivahan.gov.in/vahan4dashboard/>
- Bureau of Energy Efficiency — <https://beeindia.gov.in/>
- IEA Global EV Outlook 2024 — <https://www.iea.org/reports/global-ev-outlook-2024>

These are reference links configured in the app, not an audited data lineage for each CSV field.
