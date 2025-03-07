import os
import dash
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import xarray as xr
import geopandas as gpd
import pandas as pd
from dash import dcc, html, Input, Output

# Define base directory and file paths
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get the directory of app.py

file_path = os.path.join(BASE_DIR, 'aifs_forecast_heat_stress.nc')

shapefile_path_tal = os.path.join(BASE_DIR, 'karnataka_shape_files_taluk_district', 'Taluk', 'Taluk.shp')

# Load the dataset and compute daily parameters
ds = xr.open_dataset(file_path,engine="netcdf4")
min_2t = ds['2t'].resample(time='1D').min()
max_2t = ds['2t'].resample(time='1D').max()
avg_2t = ds['2t'].resample(time='1D').mean()
avg_rh = ds['rh'].resample(time='1D').mean()
max_hi = ds['hi'].resample(time='1D').max()
avg_hi = ds['hi'].resample(time='1D').mean()
dtr = max_2t - min_2t

# Get time, latitude, and longitude arrays
times = max_2t['time'].values
lon = max_2t['longitude'].values
lat = max_2t['latitude'].values

# Create date options for the slider (formatted as "Feb28", "Mar01", etc.)
date_options = [pd.to_datetime(t).strftime('%b%d') for t in times]

# Define variable options for the checkboxes
variable_options = [
    {'label': 'Max Temperature', 'value': 'max_2t'},
    {'label': 'Min Temperature', 'value': 'min_2t'},
    {'label': 'Avg Temperature', 'value': 'avg_2t'},
    {'label': 'Avg Relative Humidity', 'value': 'avg_rh'},
    {'label': 'Max Heat Index', 'value': 'max_hi'},
    {'label': 'Avg Heat Index', 'value': 'avg_hi'},
    {'label': 'Diurnal Temp Range', 'value': 'dtr'}
]

# Load taluk shapefile, ensure CRS is EPSG:4326, and simplify geometries for performance
tal = gpd.read_file(shapefile_path_tal)
tal = tal.to_crs(epsg=4326)
tal['geometry'] = tal['geometry'].simplify(tolerance=0.01)

# Initialize the Dash app
app = dash.Dash(__name__)

# Outer container: two-column layout with controls on left and graph on right.
app.layout = html.Div([
    html.H1("Taluk-level Aggregated Temperature Dashboard", 
            style={'fontSize': '32px', 'textAlign': 'center', 'marginTop': '20px', 'marginBottom': '20px'}),
    html.Div(
        children=[
            # Left column for controls
            html.Div(
                children=[
                    html.Label("Select Date:", style={'fontSize': '28px', 'marginBottom': '10px', 'display': 'block'}),
                    html.Div(
                        dcc.Slider(
                            id='date-slider',
                            className='my-slider',  # Custom CSS will adjust mark position
                            min=0,
                            max=len(date_options) - 1,
                            step=1,
                            value=0,
                            marks={i: {'label': date_options[i], 'style': {'fontSize': '12px'}} 
                                   for i in range(len(date_options))},
                            tooltip={"always_visible": True, "placement": "bottom"},
                            updatemode='drag'
                        ),
                        style={'width': '100%', 'height': '150px'}
                    ),
                    html.Br(),
                    html.Label("Select Variable(s):", style={'fontSize': '28px', 'marginBottom': '10px', 'display': 'block'}),
                    dcc.Checklist(
                        id='variable-checklist',
                        options=variable_options,
                        value=[variable_options[0]['value']],
                        labelStyle={'display': 'block', 'fontSize': '24px', 'marginBottom': '10px'}
                    )
                ],
                style={'width': '35%', 'padding': '10px', 'boxSizing': 'border-box'}
            ),
            # Right column for graph
            html.Div(
                id='graph-container',
                style={'width': '65%', 'padding': '10px', 'boxSizing': 'border-box'}
            )
        ],
        style={
            'display': 'flex',
            'justifyContent': 'center',
            'alignItems': 'flex-start',
            'border': '2px solid black',
            'margin': 'auto',
            'width': '95%'
        }
    )
])

@app.callback(
    Output('graph-container', 'children'),
    [Input('date-slider', 'value'),
     Input('variable-checklist', 'value')]
)
def update_graph(date_idx, selected_vars):
    graphs = []
    if not selected_vars:
        return [html.Div("Please select at least one variable.", style={'fontSize': '28px'})]
    
    try:
        day_label = date_options[date_idx]
    except IndexError:
        return [html.Div("Date index out of range.", style={'fontSize': '28px'})]
    
    for var in selected_vars:
        if var == 'max_2t':
            da = max_2t.isel(time=date_idx)
            var_label = "Max Temperature"
        elif var == 'min_2t':
            da = min_2t.isel(time=date_idx)
            var_label = "Min Temperature"
        elif var == 'avg_2t':
            da = avg_2t.isel(time=date_idx)
            var_label = "Avg Temperature"
        elif var == 'avg_rh':
            da = avg_rh.isel(time=date_idx)
            var_label = "Avg Relative Humidity"
        elif var == 'max_hi':
            da = max_hi.isel(time=date_idx)
            var_label = "Max Heat Index"
        elif var == 'avg_hi':
            da = avg_hi.isel(time=date_idx)
            var_label = "Avg Heat Index"
        elif var == 'dtr':
            da = dtr.isel(time=date_idx)
            var_label = "Diurnal Temp Range"
        else:
            continue

        # Create a meshgrid and flatten the data into a DataFrame
        long_grid, lat_grid = np.meshgrid(lon, lat)
        df = pd.DataFrame({
            'lon': long_grid.flatten(),
            'lat': lat_grid.flatten(),
            'value': da.values.flatten()
        }).dropna(subset=['value'])
        
        # Convert the DataFrame to a GeoDataFrame with point geometries
        gdf_points = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df.lon, df.lat),
            crs='EPSG:4326'
        )
        
        # Spatially join the points with the taluk polygons using "KGISTalukN"
        joined = gpd.sjoin(gdf_points, tal, how='inner', predicate='within')
        agg = joined.groupby('KGISTalukN')['value'].mean()
        tal_agg = tal.merge(agg, left_on='KGISTalukN', right_index=True)
        tal_agg['id'] = tal_agg['KGISTalukN']
        geojson_data = tal_agg.__geo_interface__
        
        # Create a choropleth map using Plotly Express
        fig = px.choropleth(
            tal_agg,
            geojson=geojson_data,
            locations='id',
            color='value',
            featureidkey="properties.KGISTalukN",
            color_continuous_scale='Spectral_r',
            title=f"{var_label} on {day_label}"
        )
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_traces(marker_line_width=0)
        # Update layout: large fonts; set width/height; position horizontal colorbar below
        fig.update_layout(
            margin={"r":0, "t":40, "l":0, "b":100},
            width=1200,
            height=750,
            font=dict(size=20)
        )
        fig.update_coloraxes(colorbar=dict(
            orientation="h",
            x=0.5,
            y=-0.1,
            xanchor='center',
            len=0.8,
            title=var_label,
            title_font=dict(size=28),
            tickfont=dict(size=24)
        ))
        
        graphs.append(dcc.Graph(figure=fig))
    
    return graphs


if __name__ == '__main__':
    app.run_server(debug=True, port=8067)
