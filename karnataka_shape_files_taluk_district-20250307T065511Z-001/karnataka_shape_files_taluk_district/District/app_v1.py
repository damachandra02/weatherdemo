import os
import dash
import plotly.express as px
import numpy as np
import xarray as xr
import geopandas as gpd
import pandas as pd
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash_bootstrap_components as dbc

# Configuration
BASE_DIR = '/Users/artpark/Documents/climate_x_health'
DATA_FILE = os.path.join(BASE_DIR, 'aifs_forecast_heat_stress.nc')
STATE_SHP = os.path.join(BASE_DIR, 'shape_files/State.shp')
DISTRICT_SHP = os.path.join(BASE_DIR, 'shape_files/District.shp')

# Load data and shapefiles
ds = xr.open_dataset(DATA_FILE)
state_gdf = gpd.read_file(STATE_SHP).to_crs(epsg=4326)
districts_gdf = gpd.read_file(DISTRICT_SHP).to_crs(epsg=4326)

# Preprocess variables
variables = {
    'Max Temperature': ds['2t'].resample(time='1D').max(),
    'Min Temperature': ds['2t'].resample(time='1D').min(),
    'Avg Temperature': ds['2t'].resample(time='1D').mean(),
    'Heat Index': ds['hi'].resample(time='1D').max(),
    'Humidity': ds['rh'].resample(time='1D').mean()
}

# Create Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CERULEAN])
app.title = "Climate Health Dashboard"

app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Karnataka Climate Analysis", className="text-center my-4"))),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Date Selection", className="h5"),
                dbc.CardBody([
                    dcc.Checklist(
                        id='date-checklist',
                        options=[{'label': pd.to_datetime(str(date)).strftime('%b %d'), 'value': i} 
                                for i, date in enumerate(variables['Max Temperature'].time.values)],
                        value=[0],
                        inline=True,
                        labelClassName="mr-3",
                        inputClassName="mr-1"
                    )
                ], style={'maxHeight': '200px', 'overflowY': 'auto'})
            ], className="mb-3"),
            
            dbc.Card([
                dbc.CardHeader("Variable Selection", className="h5"),
                dbc.CardBody([
                    dcc.Checklist(
                        id='var-checklist',
                        options=[{'label': k, 'value': k} for k in variables.keys()],
                        value=['Max Temperature'],
                        inline=True,
                        labelClassName="mr-3",
                        inputClassName="mr-1"
                    )
                ])
            ])
        ], md=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Loading(
                        id="loading-map",
                        type="circle",
                        children=dcc.Graph(id='main-map', style={'height': '75vh'})
                ])
            ])
        ], md=9)
    ])
], fluid=True)

@app.callback(
    Output('main-map', 'figure'),
    [Input('date-checklist', 'value'),
     Input('var-checklist', 'value')]
)
def update_map(selected_dates, selected_vars):
    # Create subplot grid
    n_rows = len(selected_vars)
    n_cols = len(selected_dates)
    
    fig = make_subplots(
        rows=n_rows, cols=n_cols,
        subplot_titles=[
            f"{var} - {pd.to_datetime(variables[var].time.values[date_idx]).strftime('%b %d')}" 
            for var in selected_vars for date_idx in selected_dates
        ],
        specs=[[{"type": "scattergeo"} for _ in range(n_cols)] for _ in range(n_rows)],
        vertical_spacing=0.1,
        horizontal_spacing=0.05
    )
    
    # Create colormap dictionary
    cmap = {
        'Max Temperature': 'thermal',
        'Min Temperature': 'ice',
        'Avg Temperature': 'tempo',
        'Heat Index': 'magma',
        'Humidity': 'rainbow'
    }
    
    for row_idx, var in enumerate(selected_vars, 1):
        for col_idx, date_idx in enumerate(selected_dates, 1):
            # Get data
            data = variables[var].isel(time=date_idx)
            
            # Create heatmap trace
            trace = go.Densitymapbox(
                lon=data.longitude.values.flatten(),
                lat=data.latitude.values.flatten(),
                z=data.values.flatten(),
                radius=10,
                colorscale=cmap[var],
                zmin=data.min().values,
                zmax=data.max().values,
                colorbar=dict(title=var, len=0.8/n_rows)
            )
            
            fig.add_trace(trace, row=row_idx, col=col_idx)
            
            # Add district boundaries
            for _, district in districts_gdf.iterrows():
                geom = district.geometry
                if geom.geom_type == 'Polygon':
                    x, y = geom.exterior.coords.xy
                    fig.add_trace(go.Scattermapbox(
                        lon=list(x),
                        lat=list(y),
                        mode='lines',
                        line=dict(color='#444', width=1),
                        showlegend=False,
                        hoverinfo='none'
                    ), row=row_idx, col=col_idx)
            
            # Add state boundary
            for geom in state_gdf.geometry:
                if geom.geom_type == 'Polygon':
                    x, y = geom.exterior.coords.xy
                    fig.add_trace(go.Scattermapbox(
                        lon=list(x),
                        lat=list(y),
                        mode='lines',
                        line=dict(color='red', width=2),
                        showlegend=False,
                        hoverinfo='none'
                    ), row=row_idx, col=col_idx)

    # Update map layout
    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox_zoom=5.8,
        mapbox_center={"lat": 15.3173, "lon": 75.7139},
        margin={"r":0,"t":40,"l":0,"b":0},
        height=800 + 200*(n_rows-1),
        template='plotly_white'
    )
    
    # Update subplot annotations
    fig.for_each_annotation(lambda a: a.update(text=a.text.split(" - ")[0]))
    
    return fig

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)
