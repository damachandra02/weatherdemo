import os
import dash
import plotly.express as px
import numpy as np
import xarray as xr
import pandas as pd
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
from plotly import graph_objs as go

# Define base directory and file path (update this to your file location)
BASE_DIR = '/Users/artpark/Documents/climate_x_health'
file_path = os.path.join(BASE_DIR, 'aifs_forecast_heat_stress.nc')

# Load dataset
ds = xr.open_dataset(file_path)

# Precompute daily statistics for performance
min_2t = ds['2t'].resample(time='1D').min()  # Min temperature
max_2t = ds['2t'].resample(time='1D').max()  # Max temperature
avg_2t = ds['2t'].resample(time='1D').mean()  # Avg temperature
avg_rh = ds['rh'].resample(time='1D').mean()  # Avg relative humidity
max_hi = ds['hi'].resample(time='1D').max()   # Max heat index
avg_hi = ds['hi'].resample(time='1D').mean()  # Avg heat index
dtr = max_2t - min_2t                        # Diurnal temperature range

# Extract coordinates
times = max_2t['time'].values
lats = max_2t['latitude'].values
lons = max_2t['longitude'].values

# Initialize Dash app with Bootstrap theme for styling
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Define checklist options for dates and variables
date_options = [{'label': str(date)[:10], 'value': str(date)} for date in times]
variable_options = [
    {'label': 'Max Temperature (2t)', 'value': 'max_2t'},
    {'label': 'Min Temperature (2t)', 'value': 'min_2t'},
    {'label': 'Average Temperature (2t)', 'value': 'avg_2t'},
    {'label': 'Average Relative Humidity (rh)', 'value': 'avg_rh'},
    {'label': 'Max Heat Index (hi)', 'value': 'max_hi'},
    {'label': 'Average Heat Index (hi)', 'value': 'avg_hi'},
    {'label': 'Diurnal Temperature Range (DTR)', 'value': 'dtr'}
]

# Define the app layout using Bootstrap grid
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col(html.H1("Climate Data Dashboard"), width=12, className="text-center my-3")
    ]),
    dbc.Row([
        # Sidebar for controls
        dbc.Col([
            html.Label("Select Dates:", className="fw-bold mb-2"),
            dcc.Checklist(
                id='date-checklist',
                options=date_options,
                value=[str(times[0])],  # Default to first date
                inline=True,
                className="mb-3"
            ),
            html.Label("Select Variables:", className="fw-bold mb-2"),
            dcc.Checklist(
                id='variable-checklist',
                options=variable_options,
                value=['max_2t'],  # Default to max temperature
                inline=True
            )
        ], width=3, className="bg-light p-3 rounded"),
        # Main graph area
        dbc.Col(dcc.Graph(id='climate-map'), width=9)
    ])
], fluid=True, className="py-3")

# Callback to dynamically update the heatmap based on user selections
@app.callback(
    Output('climate-map', 'figure'),
    [Input('date-checklist', 'value'),
     Input('variable-checklist', 'value')]
)
def update_map(selected_dates, selected_variables):
    # Handle empty selections
    if not selected_dates or not selected_variables:
        return go.Figure()

    # Use the first selected date and variable for simplicity
    date = selected_dates[0]
    variable = selected_variables[0]
    time_idx = np.where(times == np.datetime64(date))[0][0]

    # Select data and customize visualization based on variable
    if variable == 'max_2t':
        data = max_2t.isel(time=time_idx).values
        title = 'Max Temperature (°C)'
        colorscale = 'Hot'
    elif variable == 'min_2t':
        data = min_2t.isel(time=time_idx).values
        title = 'Min Temperature (°C)'
        colorscale = 'Blues'
    elif variable == 'avg_2t':
        data = avg_2t.isel(time=time_idx).values
        title = 'Avg Temperature (°C)'
        colorscale = 'RdBu_r'
    elif variable == 'avg_rh':
        data = avg_rh.isel(time=time_idx).values
        title = 'Avg Relative Humidity (%)'
        colorscale = 'YlGnBu'
    elif variable == 'max_hi':
        data = max_hi.isel(time=time_idx).values
        title = 'Max Heat Index'
        colorscale = 'Inferno'
    elif variable == 'avg_hi':
        data = avg_hi.isel(time=time_idx).values
        title = 'Avg Heat Index'
        colorscale = 'Magma'
    elif variable == 'dtr':
        data = dtr.isel(time=time_idx).values
        title = 'Diurnal Temp Range (°C)'
        colorscale = 'Viridis'
    else:
        data = np.zeros_like(max_2t.isel(time=0).values)
        title = 'No Data'
        colorscale = 'Greys'

    # Create heatmap with Plotly
    fig = go.Figure(data=go.Heatmap(
        z=data,
        x=lons,
        y=lats,
        colorscale=colorscale,
        colorbar=dict(title=title)
    ))

    # Customize layout
    fig.update_layout(
        title=f"{title} on {date[:10]}",
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        height=600,
        margin=dict(l=50, r=50, t=100, b=50)
    )

    return fig

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True, port=8051)
