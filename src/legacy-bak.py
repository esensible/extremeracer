import asyncio
import datetime
import fastapi
import fastapi.staticfiles
import fastapi.responses

try:
    import gpiozero
except:
    # mock for dev testing on laptop
    import gpiomock as gpiozero
try:
    import asyncio
    import serial_asyncio
except:
    pass
import logging
import math
import pynmea2
from pythonjsonlogger import jsonlogger
import os
import platform
import random
import shapely.geometry as shapely_geom
import time
import typing

# This parameter represents button press latency
# from the kindle
LATENCY_OFFSET = 0.3
DISPLAY_LATENCY = 1
# confirm timeout of 5s
CONFIRM_TIMEOUT = 5

# number of seconds past the minute boundary for which SYNC is ignored
SYNC_IGNORE = 5

SCREEN_WIDTH = 1272
SCREEN_HEIGHT = 1474

# size of confirmation button
CONFIRM_SIZE = 100

# 400 is total of bottom buttons
TOTAL_BUTTON_HEIGHT = 500

logger = logging.getLogger("mine")
logHandler = logging.FileHandler(filename="trace.json")

# logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(timestamp=True)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.DEBUG)

switches = [5, 6, 13, 19]
states = {}

app = fastapi.FastAPI()

dirname = os.path.dirname(__file__)
app.mount(
    "/static",
    fastapi.staticfiles.StaticFiles(directory=os.path.join(dirname, "static")),
    name="static",
)

MS_TO_KNOTS = 1.94384


class States:
    idle = 0
    start = 1
    race = 2


_state = States.idle
_start_timestamp = None
_line = {"boat": None, "pin": None, "line": None, "uuid": 0}
_gps = pynmea2.parse(
    "$GPRMC,181643.000,A,3456.6333,S,13836.9472,E,0.44,140.90,211022,,,A*72"
)
_msg_id = 0
_confirm = None
_knots_to_mps = 0.514444


def _win_beep():
    os.system('powershell.exe "[console]::beep(500,10)"')


_start_gun = None


async def test_start():
    global _start_gun
    global _start_timestamp

    await asyncio.sleep(10)
    _start_gun = time.time()
    _win_beep()
    await asyncio.sleep(10 - (time.time() - _start_gun))
    print(f"Offset: {_start_timestamp - _start_gun}")
    await asyncio.sleep(60 - (time.time() - _start_gun))

    _win_beep()
    await asyncio.sleep(70 - (time.time() - _start_gun))
    print(f"Offset: {_start_timestamp - _start_gun}")
    await asyncio.sleep(120 - (time.time() - _start_gun))

    _win_beep()


def _confirm_point():
    return [
        random.randint(CONFIRM_SIZE, SCREEN_WIDTH - CONFIRM_SIZE),
        random.randint(
            CONFIRM_SIZE, SCREEN_HEIGHT - TOTAL_BUTTON_HEIGHT - CONFIRM_SIZE
        ),
    ]


def get_radius_at_lat(lat):  # radians
    WGS_ELLIPSOID = (6378137.0, 6356752.314)

    f1 = math.pow((math.pow(WGS_ELLIPSOID[0], 2) * math.cos(lat)), 2)
    f2 = math.pow((math.pow(WGS_ELLIPSOID[1], 2) * math.sin(lat)), 2)
    f3 = math.pow((WGS_ELLIPSOID[0] * math.cos(lat)), 2)
    f4 = math.pow((WGS_ELLIPSOID[1] * math.sin(lat)), 2)

    radius = math.sqrt((f1 + f2) / (f3 + f4))

    return radius


def _distance(pt1, pt2, R=6371000):
    lon1, lat1, lon2, lat2 = map(math.radians, [pt1.x, pt1.y, pt2.x, pt2.y])

    # R = get_radius_at_lat((lat1 + lat2) / 2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
    )

    c = 2 * math.asin(math.sqrt(a))
    return R * c


def _fwd(lon1, lat1, heading_radians, distance=1000, R=6371000):
    lon1, lat1 = map(math.radians, [lon1, lat1])

    # R = get_radius_at_lat(lat1)

    lat2 = math.asin(
        math.sin(lat1) * math.cos(distance / R)
        + math.cos(lat1) * math.sin(distance / R) * math.cos(heading_radians)
    )

    lon2 = lon1 + math.atan2(
        math.sin(heading_radians) * math.sin(distance / R) * math.cos(lat1),
        math.cos(distance / R) - math.sin(lat1) * math.sin(lat2),
    )

    return map(math.degrees, [lon2, lat2])


def _bearing(pt1, pt2):
    lon1, lat1, lon2, lat2 = map(math.radians, [pt1.x, pt1.y, pt2.x, pt2.y])

    dL = lon2 - lon1
    X = math.cos(lat2) * math.sin(dL)
    Y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dL)
    return math.atan2(X, Y)


def _distance_to_line(line, nacra_pt, heading):
    # R = get_radius_at_lat(math.radians(nacra[1]))

    heading = math.radians(heading) if heading <= 180 else math.radians(heading - 360)
    ep_lon, ep_lat = _fwd(nacra_pt.x, nacra_pt.y, heading)

    # nacra_pt = shapely_geom.Point(*nacra)
    nacra_travel = shapely_geom.LineString(
        [nacra_pt, shapely_geom.Point(ep_lon, ep_lat)]
    )
    cross = nacra_travel.intersection(line)

    if type(cross) == shapely_geom.point.Point:
        return _distance(nacra_pt, cross)
    else:
        line0_heading = _bearing(nacra_pt, shapely_geom.Point(*line.coords[0]))
        line1_heading = _bearing(nacra_pt, shapely_geom.Point(*line.coords[1]))

        if abs(heading - line0_heading) < abs(heading - line1_heading):
            return _distance(nacra_pt, shapely_geom.Point(*line.coords[0]))
        else:
            return _distance(nacra_pt, shapely_geom.Point(*line.coords[1]))


def seconds_to_line(line, location, heading, speed, **kwargs):
    logger.info(
        "gate",
        extra=dict(
            line=str(line), location=str(location), heading=heading, speed=speed
        ),
    )
    return _distance_to_line(line, location, heading) / ((speed + 1e-5) * _knots_to_mps)


def current_state():
    global _msg_id
    global _state
    global _start_timestamp
    global _confirm

    now = time.time()
    _msg_id += 1

    gps = {"speed": f"{_gps.spd_over_grnd:.1f}", "heading": f"{_gps.true_course:.0f}"}

    if _confirm is not None and _confirm["timeout"] < time.time():
        logger.info("confirm timeout", extra={"confirm": _confirm})

        _confirm = None

    if _state == States.idle:
        return {
            "id": _msg_id,
            "timestamp": now,
            "state": "idle",
            "line": {
                "uuid": _line["uuid"],
                "boat": _line["boat"] is not None,
                "pin": _line["pin"] is not None,
            }
            if _line["line"] is None
            else {
                "uuid": _line["uuid"],
                "seconds": int(
                    seconds_to_line(
                        _line["line"],
                        shapely_geom.Point(_gps.longitude, _gps.latitude),
                        _gps.true_course,
                        _gps.spd_over_grnd,
                    )
                ),
            },
            "confirm": _confirm["response"] if _confirm is not None else False,
            "seconds": None,
            "gps": gps,
        }
    if _state == States.start:
        seconds = _start_timestamp - now - DISPLAY_LATENCY
        if seconds > 0:
            return {
                "id": _msg_id,
                "timestamp": now,
                "state": "start",
                "line": {
                    "uuid": _line["uuid"],
                    "boat": _line["boat"] is not None,
                    "pin": _line["pin"] is not None,
                }
                if _line["line"] is None
                else {
                    "uuid": _line["uuid"],
                    # determine early/late
                    "seconds": int(
                        seconds_to_line(
                            _line["line"],
                            shapely_geom.Point(_gps.longitude, _gps.latitude),
                            _gps.true_course,
                            _gps.spd_over_grnd,
                        )
                        - seconds
                    ),
                },
                "seconds": f"{int(seconds/60)}:{int(seconds)%60:02}",
                "gps": gps,
            }
        _state = States.race

    if _state == States.race:
        seconds = now - _start_timestamp + DISPLAY_LATENCY
        return {
            "id": _msg_id,
            "timestamp": now,
            "state": "race",
            "line": None,
            "confirm": _confirm["response"] if _confirm is not None else False,
            "seconds": f"{int(seconds/60)}:{int(seconds)%60:02}",
            "gps": gps,
        }

    return {"id": _msg_id, "timestamp": now, "state": "ERROR"}


# async def show_start():
#     global _start_timestamp

#     while True:
#         print()


@app.post("/start")
async def seq(
    seconds: int = fastapi.Body(embed=True, ge=0),
    confirm: bool = fastapi.Body(embed=True, default=False),
):
    global _start_timestamp
    global _state
    global _confirm

    logger.info("/start", extra={"confirm": confirm, "seconds": seconds})

    if confirm:
        _start_timestamp = seconds
        _state = States.start
        _confirm = None
    else:
        _confirm = {
            "timeout": time.time() + CONFIRM_TIMEOUT,
            "response": {
                "point": _confirm_point(),
                "uri": "/start",
                "data": {
                    "confirm": True,
                    "seconds": time.time() + seconds - LATENCY_OFFSET,
                },
            },
        }

    # asyncio.create_task(show_start())

    return current_state()


@app.post("/bump")
async def bump(seconds: int = fastapi.Body(embed=True)):
    global _start_timestamp

    print(seconds)
    if seconds == 0:
        # ignore sync requests for 15s after the minute rolls over.
        # the purpose of this is to minimise impact of lag
        current = _start_timestamp - time.time() + LATENCY_OFFSET
        if (current % 60) < (60 - SYNC_IGNORE):
            _start_timestamp -= current % 60
        else:
            print(f"rejected: {current % 60}")
    else:
        if 0 < seconds + _start_timestamp - time.time():  # + LATENCY_OFFSET:
            _start_timestamp += seconds
        else:
            print(f"rejected: {seconds} > {_start_timestamp - time.time()}")

    return current_state()


@app.post("/finish")
async def finish(confirm: bool = fastapi.Body(embed=True, default=False)):
    global _state
    global _confirm

    logger.info("/finish", extra={"confirm": confirm})

    if confirm:
        _state = States.idle
        _confirm = None
    else:
        _confirm = {
            "timeout": time.time() + CONFIRM_TIMEOUT,
            "response": {
                "point": _confirm_point(),
                "uri": "/finish",
                "data": {"confirm": True},
            },
        }
    return current_state()


@app.get("/state")
async def state(
    ts: int = fastapi.Query(embed=True, default=None),
    last: int = fastapi.Query(embed=True, default=None),
):
    # add additional timestamp for NTP correction
    received = time.time()
    # if ts is not None:
    #     # logger.info("/state", extra=dict(data=data))
    #     print(ts)
    # if last is not None:
    #     # logger.info("/state", extra=dict(data=data))
    #     print(last)
    result = current_state()
    result["received"] = received
    return result


@app.post("/line")
async def line(end: typing.Union[str, None] = fastapi.Body(default=None, embed=True)):
    global _line

    if end is None:
        _line = {"boat": None, "pin": None, "line": None}
        logger.info("/line", extra={"end": None})
    else:
        _line[end] = shapely_geom.Point(_gps.longitude, _gps.latitude)
        logger.info(
            "/line", extra={"end": end, "lat": _gps.latitude, "lon": _gps.longitude}
        )
        if _line["boat"] is not None and _line["pin"] is not None:
            _line["line"] = shapely_geom.LineString([_line["boat"], _line["pin"]])
    _line["uuid"] = int(time.time())
    return current_state()


@app.post("/log")
async def create_log(msg: str = fastapi.Body(embed=True)):
    print(msg)
    return None


class InputChunkProtocol(asyncio.Protocol):
    def __init__(self):
        self.buffer = ""

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        global _gps

        self.buffer += data.decode()
        tmp = self.buffer.split("\r\n")
        if len(tmp) > 1:
            # print('\n'.join(tmp[:-1]))
            self.buffer = tmp[-1]
            for t in tmp[:-1]:
                try:
                    pos = pynmea2.parse(t)
                except:
                    continue
                if pos.identifier() == "GPRMC,":
                    logger.info(
                        "gps",
                        extra=dict(
                            latitude=pos.latitude,
                            longitude=pos.longitude,
                            speed=pos.spd_over_grnd,
                            heading=pos.true_course,
                        ),
                    )
                    _gps = pos

        # stop callbacks again immediately
        self.pause_reading()

    def pause_reading(self):
        # This will stop the callbacks to data_received
        self.transport.pause_reading()

    def resume_reading(self):
        # This will start the callbacks to data_received again with all data that has been received in the meantime.
        self.transport.resume_reading()


async def gps():
    transport, protocol = await serial_asyncio.create_serial_connection(
        asyncio.get_event_loop(), InputChunkProtocol, "/dev/serial0", baudrate=9600
    )

    while True:
        await asyncio.sleep(0.3)
        protocol.resume_reading()


@app.on_event("startup")
async def app_startup():
    asyncio.create_task(gps())

    if "WSL" in platform.uname().release:
        asyncio.create_task(test_start())


#
##
#


@app.get("/{item_id}/on/{seconds}")
async def on(
    background_tasks: fastapi.BackgroundTasks,
    item_id: int = fastapi.Path(ge=0, lt=len(switches)),
    seconds: int = fastapi.Path(ge=0),
):
    if item_id not in states:
        states[item_id] = gpiozero.LED(switches[item_id])
    states[item_id].on()
    background_tasks.add_task(delay_off, item_id, seconds)


@app.get("/{item_id}/off")
async def off(item_id: int = fastapi.Path(ge=0, lt=len(switches))):
    if item_id not in states:
        states[item_id] = gpiozero.LED(switches[item_id])
    states[item_id].off()


@app.get("/time", response_class=fastapi.responses.HTMLResponse)
async def gettime():
    return datetime.datetime.now().strftime("%H:%M:%S")


async def delay_off(item_id: int, seconds: int):
    print(f"delay {seconds}")
    await asyncio.sleep(seconds)
    if item_id not in states:
        states[item_id] = gpiozero.LED(switches[item_id])
    states[item_id].off()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("pi:app", host="0.0.0.0", port=8080, reload=True, log_level="debug")
