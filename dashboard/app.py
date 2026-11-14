"""Plotly Dash monitoring application - STUB (Workshop 1).

The layout fixes the four panels promised by the user stories; data wiring is
done in Workshop 4. Run: python dashboard/app.py  ->  http://localhost:8050
"""
import os

from dash import Dash, html

app = Dash(__name__, title="TC-Analog Monitor")

PANELS = [
    ("Active storms", "US-01, US-02, US-06: map with latest position, intensity, category, motion."),
    ("Historical analogs", "US-03, US-05: top-5 similar storms (SAS score) and track overlay."),
    ("Data freshness", "US-04, US-07: last successful run, record counts, provisional/rejected."),
    ("Archive explorer", "US-08: filter by basin, season and peak category."),
]

app.layout = html.Div(
    style={"fontFamily": "system-ui, sans-serif", "maxWidth": "1100px", "margin": "0 auto"},
    children=[
        html.H1("TC-Analog Monitor"),
        html.P("Team 4 - Tropical Cyclone Monitoring. Monitoring and comparison only; "
               "analogs are not forecasts."),
        *[html.Section([html.H2(t), html.P(d)],
                       style={"border": "1px solid #ccc", "borderRadius": 8, "padding": 16, "margin": "12px 0"})
          for t, d in PANELS],
        html.Footer("Data: IBTrACS v04r01 (NOAA NCEI, doi:10.25921/82ty-9e16); GDACS (UN / European Commission)."),
    ],
)

if __name__ == "__main__":
    app.run(host=os.getenv("DASH_HOST", "0.0.0.0"), port=int(os.getenv("DASH_PORT", 8050)), debug=True)
