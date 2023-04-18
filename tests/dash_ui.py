import asyncio
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
import dash_leaflet as dl
import math
from fastapi import FastAPI
import threading
import uvicorn

import sys
sys.path.append("src")
import main
import gps
import utils
import common
import silkflow


# Global variable to store the GPS data
gps_data = (0, 0, 0, 0, 0)

class Pos:
    def __init__(self, lat, lon, heading, speed):
        self.latitude = lat
        self.longitude = lon
        self.true_course = heading
        self.spd_over_grnd = speed

# Function to update GPS
def update_gps(lat1, lon1, lat2, lon2, speed):

    bearing = utils.bearing(math.radians(lat1), math.radians(lon1), math.radians(lat2), math.radians(lon2))
    print(math.degrees(bearing))
    gps.state.value = Pos(lat1, lon1, math.degrees(bearing), speed)
    event.set()
   

def get_buoys():
    result = []
    print(common.line.value)
    if common.line.value & common.LINE_PORT:
        result.append(dl.Marker(position=[math.degrees(common.line_port[0]), math.degrees(common.line_port[1])]))

    if common.line.value & common.LINE_STBD:
        result.append(dl.Marker(position=[math.degrees(common.line_stbd[0]), math.degrees(common.line_stbd[1])]))

    print(result)
    return result

# Dash app setup
app = dash.Dash(__name__)

icon = {
    "iconUrl": "https://dash-leaflet.herokuapp.com/assets/icon_plane.png",
    "iconAnchor": [16, 16]
}

west_beach_lat = -34.947222
west_beach_lon = 138.502778

app.layout = html.Div([
    dl.Map(id="map", center=[west_beach_lat, west_beach_lon], zoom=13, children=[
        dl.TileLayer(),
        dl.Marker(id="marker1", position=[west_beach_lat, west_beach_lon], draggable=True),
        dl.Marker(id="marker2", position=[west_beach_lat - 0.02, west_beach_lon - 0.02], draggable=True),
        dl.Polyline(id="line", positions=[[west_beach_lat, west_beach_lon], [west_beach_lat - 0.02, west_beach_lon - 0.02]], color="green")
    ], style={'width': '100%', 'height': '1000px'}),
    html.Div([
        html.Label("Speed (knots)"),
        dcc.Input(id="speed_input", type="number", min=0, max=50, value=0),
    ], style={'width': '100%'}),
    html.Button("Refresh", id="refresh_button", n_clicks=0, style={'width': '10%', }),
])


@app.callback(
    [Output("marker1", "position"),
     Output("marker2", "position"),
     Output("line", "positions"),
     Output("map", "children")],
    [Input("marker1", "position"),
     Input("marker2", "position"),
     Input("refresh_button", "n_clicks"),
     Input("speed_input", "value")]
)
def update_gps_data(marker1_center, marker2_center, refresh_button_clicks, speed):
    ctx = dash.callback_context
    if not ctx.triggered or ctx.triggered[0]["prop_id"] == "refresh_button.n_clicks":
        print("Refresh button clicked")

    lat1, lon1 = marker1_center
    lat2, lon2 = marker2_center
    update_gps(lat1, lon1, lat2, lon2, speed)

    # Update the map with the new markers
    map_children = [
        dl.TileLayer(),
        dl.Marker(id="marker1", position=marker1_center, draggable=True),
        dl.Marker(id="marker2", position=marker2_center, draggable=True),
        dl.Polyline(id="line", positions=[marker1_center, marker2_center], color="green"),
    ] + get_buoys()

    return marker1_center, marker2_center, [marker1_center, marker2_center], map_children


event = None

def run_dash_app():
    app.run_server(port=8050)


async def silk_proxy():
    while True:
        await event.wait()
        await silkflow.sync_poll()
        event.clear()
        

@main.app.on_event("startup")
async def process_event():
    global event
    event = asyncio.Event()
    asyncio.create_task(silk_proxy())

def run_api_app():
    uvicorn.run(main.app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    dash_thread = threading.Thread(target=run_dash_app)
    api_thread = threading.Thread(target=run_api_app)

    dash_thread.start()
    api_thread.start()

    dash_thread.join()
    api_thread.join()
