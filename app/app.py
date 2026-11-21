"""Hotel Booking Cancellations dashboard (Dash).

Run from the project folder:  python app/app.py
"""
import sys
import uuid
from pathlib import Path

import pandas as pd
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

# This file lives in app/, but charts/, data/ and assets/ are one folder up.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from charts import FIGURE_LOCK, placeholder  # noqa: E402 (needs the path above)
from charts.chart1 import make_chart1
from charts.chart2 import (LEAD_MAX, LEAD_STEP, PRICE_MAX, PRICE_STEP,
                           label, lead_bin, make_chart2, price_bin)
from charts.chart3 import make_chart3
from data.clean import clean, parse_upload

SAMPLE_FILE = ROOT / "data" / "hotel_bookings.csv"

# Loaded datasets, kept on the server. The browser only stores the key.
DATA = {}

app = Dash(__name__, title="Hotel Cancellations",
           assets_folder=str(ROOT / "assets"))
server = app.server  # used by gunicorn on Render


NO_TOOLBAR = {"displayModeBar": False}
SELECT_TOOLBAR = {  # Charts 2 and 3: box select, lasso select, zoom
    "displayModeBar": True, "displaylogo": False,
    "modeBarButtons": [["select2d", "lasso2d", "zoom2d"]],
}


def chart_card(chart_id, question, caption, toolbar=None, config=NO_TOOLBAR):
    return html.Section(className="card", children=[
        html.H3(question),
        toolbar,
        dcc.Graph(id=chart_id, config=config),
        html.P(caption, className="chart-note"),
    ])


def revert_toolbar(status_id, button_id):
    return html.Div(className="card-toolbar", children=[
        html.Div(id=status_id, className="status"),
        html.Button("Revert to original", id=button_id,
                    className="btn btn-small"),
    ])


app.layout = html.Div(className="page", children=[
    dcc.Store(id="data-key"),
    dcc.Store(id="selected-months"),  # months clicked/selected in Chart 3
    dcc.Store(id="selected-cell"),    # cell clicked in Chart 2

    html.Header(children=[
        html.H1("Why do hotel bookings get canceled?"),
        html.P("For hotel revenue managers: about 1 in 3 bookings in this "
               "data is canceled. Find which bookings are riskiest, whether "
               "far-ahead or high-ADR bookings cancel more, when cancellations "
               "peak, and which weeks need the most overbooking cover.",
               className="lede"),
    ]),

    html.Section(className="controls", children=[
        dcc.Upload(id="upload", accept=".csv,.xlsx",
                   children=html.Button("Upload CSV or Excel", className="btn")),
        html.Button("Use default sample data", id="sample-btn", className="btn"),
        html.Div("Upload a hotel-bookings file, or use the default sample data.",
                 id="upload-status", className="status"),
    ]),

    html.Section(className="controls", children=[
        html.Div("Filters apply to all four charts below",
                 className="controls-heading"),
        html.Div(className="control", children=[
            html.Label("Hotel"),
            dcc.Dropdown(id="hotel-filter", multi=True,
                         placeholder="All hotels", disabled=True),
        ]),
        html.Div(className="control wide", children=[
            html.Label("Arrival year"),
            dcc.RangeSlider(id="year-filter", min=0, max=1, step=1,
                            marks={0: "", 1: ""}, disabled=True),
        ]),
    ]),

    html.Main(className="grid", children=[
        chart_card("chart1", "Chart 1: Which bookings are riskiest?",
                   "Placeholder until Chart 1 is added."),
        chart_card("chart2", "Chart 2: Are bookings made further ahead, "
                   "or at a higher average daily rate, canceled more?",
                   "Each cell is a group of bookings by lead time and average "
                   "daily rate (ADR). "
                   "Grey = fewer than 20 bookings. Hover for the numbers; "
                   "click a cell to filter Charts 1, "
                   "3 and 4 to those bookings.",
                   revert_toolbar("status-2", "revert-2")),
        chart_card("chart3", "Chart 3: When do cancellations peak?",
                   "Click a point, or box/lasso select several, to filter "
                   "Chart 2 to those months.",
                   revert_toolbar("status-3", "revert-3"),
                   config=SELECT_TOOLBAR),
        chart_card("chart4", "Chart 4: Which weeks of the year are most "
                   "at risk?",
                   "Placeholder until the custom Chart 4 is added."),
    ]),
])


# ---- Loading data ----------------------------------------------------------

@app.callback(
    Output("data-key", "data"),
    Output("upload-status", "children"),
    Input("upload", "contents"),
    Input("sample-btn", "n_clicks"),
    State("upload", "filename"),
    prevent_initial_call=True,
)
def load_data(contents, _clicks, filename):
    try:
        if ctx.triggered_id == "sample-btn":
            filename = "default sample data"
            df = clean(pd.read_csv(SAMPLE_FILE))
        else:
            df = clean(parse_upload(contents, filename))
    except Exception as error:
        return None, f"Could not load {filename}: {error}"

    key = str(uuid.uuid4())
    DATA[key] = df
    return key, f"Loaded {filename}: {len(df):,} bookings after cleaning."


@app.callback(
    Output("hotel-filter", "options"),
    Output("year-filter", "min"),
    Output("year-filter", "max"),
    Output("year-filter", "marks"),
    Output("hotel-filter", "disabled"),
    Output("year-filter", "disabled"),
    Input("data-key", "data"),
    prevent_initial_call=True,
)
def set_filter_options(key):
    df = DATA[key]
    hotels = sorted(df["hotel"].unique())
    years = sorted(int(y) for y in df["arrival_date_year"].unique())
    return (hotels, years[0], years[-1], {y: str(y) for y in years},
            False, False)


# ---- Linking and Revert ----------------------------------------------------

def points_with_data(event):
    """Points from a click/selection event that carry our customdata."""
    return [p for p in (event or {}).get("points", []) if "customdata" in p]


@app.callback(
    Output("selected-months", "data"),
    Output("selected-cell", "data"),
    Output("hotel-filter", "value"),
    Output("year-filter", "value"),
    Input("chart3", "clickData"),
    Input("chart3", "selectedData"),
    Input("chart2", "clickData"),
    Input("revert-2", "n_clicks"),
    Input("revert-3", "n_clicks"),
    Input("data-key", "data"),
    State("chart3", "figure"),
    prevent_initial_call=True,
)
def update_selection(click3, selected3, click2, _r2, _r3, key, figure3):
    """Chart 3 click/selection -> months (filters Chart 2).
    Chart 2 cell click -> cell (filters Charts 1, 3, 4).
    Revert or a new file -> back to the original view.

    A chart that redraws reports an empty selection; we ignore those, so only
    Revert clears a selection.
    """
    trigger = ctx.triggered_id
    if key not in DATA:
        return None, None, [], None

    if trigger == "chart3":
        points = points_with_data(selected3 if "chart3.selectedData"
                                  in ctx.triggered_prop_ids else click3)
        if not points:
            return no_update, no_update, no_update, no_update
        # Each point is one hotel's line (curveNumber) in one month
        months = sorted({(figure3["data"][p["curveNumber"]]["name"],
                          int(p["customdata"][0]), int(p["customdata"][1]))
                         for p in points})
        return [list(m) for m in months], no_update, no_update, no_update

    if trigger == "chart2":
        # Heatmap clicks give the cell's labels, e.g. x="120–179", y="€50–€99"
        point = (click2 or {}).get("points", [{}])[0]
        if "x" not in point or point.get("z") is None:   # empty/grey cell
            return no_update, no_update, no_update, no_update
        lead = int(point["x"].split("–")[0].rstrip("+"))
        price = int(point["y"].replace("€", "").split("–")[0].rstrip("+"))
        return no_update, {"lead": lead, "price": price}, no_update, no_update

    # Revert button or a new file
    years = DATA[key]["arrival_date_year"]
    return None, None, [], [int(years.min()), int(years.max())]


def filtered(key, hotels, years):
    """Apply the hotel and year filters. None means no data loaded yet."""
    df = DATA.get(key)
    if df is None:
        return None
    if hotels:
        df = df[df["hotel"].isin(hotels)]
    if years:
        df = df[df["arrival_date_year"].between(years[0], years[1])]
    return df


# ---- Charts ----------------------------------------------------------------

EMPTY = placeholder(pd.DataFrame(), "Upload a file to begin")


@app.callback(
    Output("chart2", "figure"),
    Input("data-key", "data"),
    Input("hotel-filter", "value"),
    Input("year-filter", "value"),
    Input("selected-months", "data"),
)
def update_chart2(key, hotels, years, months):
    """Chart 2 follows the filters and the hotel-months chosen in Chart 3."""
    df = filtered(key, hotels, years)
    if df is None:
        return EMPTY
    if months:
        keys = (df["hotel"] + "|" + df["arrival_date_year"].astype(str) + "-"
                + df["arrival_month_num"].astype(str))
        df = df[keys.isin([f"{h}|{y}-{m}" for h, y, m in months])]
    with FIGURE_LOCK:
        return make_chart2(df)


@app.callback(
    Output("chart1", "figure"),
    Output("chart3", "figure"),
    Output("chart4", "figure"),
    Input("data-key", "data"),
    Input("hotel-filter", "value"),
    Input("year-filter", "value"),
    Input("selected-cell", "data"),
)
def update_other_charts(key, hotels, years, cell):
    """Charts 1, 3, 4 follow the filters and the cell clicked in Chart 2."""
    df = filtered(key, hotels, years)
    if df is None:
        return EMPTY, EMPTY, EMPTY
    if cell:
        df = df[(lead_bin(df["lead_time"]) == cell["lead"])
                & (price_bin(df["adr"]) == cell["price"])]
    with FIGURE_LOCK:
        return (make_chart1(df), make_chart3(df),
                placeholder(df, "Chart 4 coming soon"))


@app.callback(
    Output("status-2", "children"),
    Output("status-3", "children"),
    Input("selected-months", "data"),
    Input("selected-cell", "data"),
)
def update_status(months, cell):
    """Short notes above Charts 2 and 3 saying what is selected."""
    names = [f"{h} – {pd.Timestamp(y, m, 1):%b %Y}"
             for h, y, m in (months or [])]
    status2 = f"Showing {', '.join(names)} only." if names else "Showing all months."
    status3 = "Click or select points to filter Chart 2."
    if cell:
        cell_text = (f"booked {label(cell['lead'], LEAD_STEP, LEAD_MAX)} "
                     "days ahead, "
                     f"{label(cell['price'], PRICE_STEP, PRICE_MAX, '€')} "
                     "ADR")
        status2 += f" Cell selected: {cell_text}."
        status3 = f"Showing only bookings in the Chart 2 cell: {cell_text}."
    return status2, status3


if __name__ == "__main__":
    app.run(debug=True)
