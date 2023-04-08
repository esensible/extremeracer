import math
import pytest
import shapely.geometry as shapely_geom
import pyproj
import random
from fastapi.testclient import TestClient

import pi


def _result(resp, **kwargs):
    assert resp.ok
    state = resp.json()
    # assert state["timestamp"] == _time
    for key in kwargs:
        key_list = key.split("__")
        s = state
        for k in key_list[:-1]:
            s = s[k]
        assert s[key_list[-1]] == kwargs[key]

    return state


@pytest.fixture()
def client():
    return TestClient(pi.app)


_time = 0


@pytest.fixture()
def set_time():
    import time

    global _time
    _time = 0
    time.time = lambda: _time

    def _impl(ts):
        global _time
        _time = ts

    return _impl


def test_nominal(client, set_time):
    global _time

    set_time(0)

    #
    # idle state
    #
    _result(client.get("/state"), state="idle")

    set_time(10)
    _result(client.get("/state"), state="idle")

    gun_ts = 20
    set_time(gun_ts + pi.LATENCY_OFFSET)

    #
    # Kick off start sequence
    #
    resp = client.post("/start", json={"seconds": 60})
    _result(
        resp,
        state="start",
        seconds=f"0:{int(60 - pi.LATENCY_OFFSET - pi.DISPLAY_LATENCY):02}",
    )

    # from now on, move time to integer seconds from gun_ts
    set_time(gun_ts + 45 - pi.DISPLAY_LATENCY)
    _result(client.get("/state"), state="start", seconds="0:15")

    set_time(gun_ts + 58 - pi.DISPLAY_LATENCY)
    _result(client.get("/state"), state="start", seconds="0:02")

    set_time(gun_ts + 59 - pi.DISPLAY_LATENCY)
    _result(client.get("/state"), state="start", seconds="0:01")

    #
    # start time
    #
    set_time(gun_ts + 60 - pi.DISPLAY_LATENCY)
    _result(client.get("/state"), state="race", seconds="0:00")

    set_time(gun_ts + 62 - pi.DISPLAY_LATENCY)
    _result(client.get("/state"), state="race", seconds="0:02")

    #
    # finish
    #
    _result(client.post("/finish"), state="idle")
    _result(client.get("/state"), state="idle")


def test_synch(client, set_time):

    # get into the start sequence
    gun_ts = 23
    set_time(gun_ts + pi.LATENCY_OFFSET)
    resp = client.post("/start", json={"seconds": 120})
    _result(
        resp,
        state="start",
        seconds=f"1:{int(60 - pi.LATENCY_OFFSET - pi.DISPLAY_LATENCY):02}",
    )

    set_time(gun_ts - pi.DISPLAY_LATENCY)
    _result(client.get("/state"), state="start", seconds="2:00")

    # confirm bump is locked out within top 15s of the minute
    set_time(gun_ts + 10 - pi.DISPLAY_LATENCY)
    resp = client.post("/bump", json={"seconds": 0})
    _result(
        resp,
        state="start",
        seconds=f"1:50",
    )

    _result(client.get("/state"), state="start", seconds="1:50")

    correction = 20

    # confirm bump is NOT locked out outside the top 15s of the minute
    set_time(gun_ts + correction + pi.LATENCY_OFFSET)
    resp = client.post("/bump", json={"seconds": 0})
    _result(
        resp,
        state="start",
        seconds=f"0:{int(60 - pi.LATENCY_OFFSET - pi.DISPLAY_LATENCY):02}",
    )

    set_time(gun_ts + correction - pi.DISPLAY_LATENCY)
    _result(client.get("/state"), state="start", seconds="1:00")


def test_bump(client, set_time):

    # get into the start sequence
    gun_ts = 87
    set_time(gun_ts + pi.LATENCY_OFFSET)
    resp = client.post("/start", json={"seconds": 300})
    _result(
        resp,
        state="start",
        seconds=f"4:{int(60 - pi.LATENCY_OFFSET - pi.DISPLAY_LATENCY):02}",
    )

    set_time(gun_ts - pi.DISPLAY_LATENCY)
    _result(client.get("/state"), state="start", seconds="5:00")

    #
    # jump to 4:00
    # bump -1:00 - ignored
    #
    set_time(gun_ts + 60 + pi.LATENCY_OFFSET)
    resp = client.post("/bump", json={"seconds": -300})
    _result(
        resp,
        state="start",
        seconds=f"3:{int(60 - pi.LATENCY_OFFSET - pi.DISPLAY_LATENCY):02}",
    )

    set_time(gun_ts + 60 - pi.DISPLAY_LATENCY)
    _result(client.get("/state"), state="start", seconds="4:00")

    #
    # bump +5:00
    #
    set_time(gun_ts + pi.LATENCY_OFFSET)
    resp = client.post("/bump", json={"seconds": 300})
    _result(
        resp,
        state="start",
        seconds=f"9:{int(60 - pi.LATENCY_OFFSET - pi.DISPLAY_LATENCY):02}",
    )

    set_time(gun_ts - pi.DISPLAY_LATENCY)
    _result(client.get("/state"), state="start", seconds="10:00")

    # check 9:00
    set_time(gun_ts + 60 - pi.DISPLAY_LATENCY)
    _result(client.get("/state"), state="start", seconds="9:00")

    #
    # bump -5:00
    #
    set_time(gun_ts + 60 + pi.LATENCY_OFFSET)
    resp = client.post("/bump", json={"seconds": -300})
    _result(
        resp,
        state="start",
        seconds=f"3:{int(60 - pi.LATENCY_OFFSET - pi.DISPLAY_LATENCY):02}",
    )

    set_time(gun_ts + 60 - pi.DISPLAY_LATENCY)
    _result(client.get("/state"), state="start", seconds="4:00")


@pytest.fixture()
def set_gps():
    class GPS(object):
        pass

    gps = GPS()
    for field in [
        "longitude",
        "latitude",
        "true_course",
        "spd_over_grnd",
    ]:
        setattr(gps, field, getattr(pi._gps, field))
    pi._gps = gps

    def _impl(**kwargs):
        for k, v in kwargs.items():
            setattr(pi._gps, k, v)

    return _impl


geodesic = pyproj.Geod(ellps="WGS84")


def test_line(client, set_time, set_gps):

    # get into the start sequence
    gun_ts = 0
    set_time(gun_ts + pi.LATENCY_OFFSET)
    resp = client.post("/start", json={"seconds": 60})
    _result(
        resp,
        state="start",
        seconds=f"0:{int(60 - pi.LATENCY_OFFSET - pi.DISPLAY_LATENCY):02}",
    )

    set_time(gun_ts - pi.DISPLAY_LATENCY)
    _result(client.get("/state"), state="start", seconds="1:00")

    boat = (-34.957042, 138.500800)
    pin = (-34.957486, 138.500038)
    line = shapely_geom.LineString(
        [shapely_geom.Point(boat[1], boat[0]), shapely_geom.Point(pin[1], pin[0])]
    )

    # nacra1 = (-34.957616, 138.501063)
    nacra1 = (-34.958274, 138.501184)

    heading = 325
    # project forward 1000m
    endpoint = geodesic.fwd(nacra1[1], nacra1[0], heading, 1000)
    nacra_travel = shapely_geom.LineString(
        [shapely_geom.Point(nacra1[1], nacra1[0]), shapely_geom.Point(*endpoint[:2])]
    )

    cross = nacra_travel.intersection(line)

    assert type(cross) == shapely_geom.point.Point

    _, _, distance_to_cross = geodesic.inv(nacra1[1], nacra1[0], cross.x, cross.y)

    set_gps(latitude=boat[0], longitude=boat[1])
    _result(
        client.post("/line", json={"end": "boat"}), line__pin=False, line__boat=True
    )

    set_gps(latitude=pin[0], longitude=pin[1])
    # super early because we're right ont the line
    _result(client.post("/line", json={"end": "pin"}), line__seconds=-60)

    for knots in range(1, 20, 2):
        set_gps(
            latitude=nacra1[0],
            longitude=nacra1[1],
            spd_over_grnd=knots,
            true_course=heading,
        )
        result = _result(client.get("/state"))["line"]["seconds"]

        true_value = int(distance_to_cross / (knots * 0.514444)) - 60

        assert abs(result - true_value) <= 1

    # above the boat
    heading = 350

    _, _, distance_to_cross = geodesic.inv(nacra1[1], nacra1[0], boat[1], boat[0])

    knots = 10
    set_gps(
        latitude=nacra1[0],
        longitude=nacra1[1],
        spd_over_grnd=knots,
        true_course=heading,
    )
    result = _result(client.get("/state"))["line"]["seconds"]

    true_value = int(distance_to_cross / (knots * 0.514444)) - 60

    assert abs(result - true_value) <= 1

    # below the pin
    heading = 300

    _, _, distance_to_cross = geodesic.inv(nacra1[1], nacra1[0], pin[1], pin[0])

    knots = 10
    set_gps(
        latitude=nacra1[0],
        longitude=nacra1[1],
        spd_over_grnd=knots,
        true_course=heading,
    )
    result = _result(client.get("/state"))["line"]["seconds"]

    true_value = int(distance_to_cross / (knots * 0.514444)) - 60

    assert abs(result - true_value) <= 1


MAX_LATITUDE = 80
MIN_LONGITUDE = -180
MAX_LONGITUDE = 180
MIN_SPEED = 0.1
MAX_SPEED = 30


def _distance_to_line(boat, pin, nacra, heading):
    endpoint = geodesic.fwd(*nacra, heading, 1000)
    nacra_travel = shapely_geom.LineString(
        [shapely_geom.Point(*nacra), shapely_geom.Point(*endpoint[:2])]
    )
    line = shapely_geom.LineString(
        [shapely_geom.Point(*boat), shapely_geom.Point(*pin)]
    )

    cross = nacra_travel.intersection(line)
    assert type(cross) == shapely_geom.point.Point
    _, _, distance_to_cross = geodesic.inv(*nacra, cross.x, cross.y)

    return distance_to_cross


random.seed(0)


@pytest.fixture
def fuzzy_params():
    # start with a random point for the boat
    boat = (
        random.uniform(MIN_LONGITUDE, MAX_LONGITUDE),
        random.uniform(-1 * MAX_LATITUDE, MAX_LATITUDE),
    )

    # setup the line
    line_heading = random.uniform(-180, 180)
    line_heading = random.uniform(45, 135)
    # max length of 1km
    line_length = random.uniform(0, 200)
    pin = geodesic.fwd(*boat, line_heading, line_length)[:2]

    nacra_heading = random.uniform(-180, 180)
    nacra_heading = random.uniform(135, 180)
    nacra_distance = random.uniform(0, 800)
    nacra = geodesic.fwd(*boat, nacra_heading, nacra_distance)[:2]

    boat_heading, _, boat_distance = geodesic.inv(*nacra, *boat)
    pin_heading, _, pin_distance = geodesic.inv(*nacra, *pin)

    if boat_heading < pin_heading:
        heading = random.uniform(boat_heading, pin_heading)
    else:
        heading = random.uniform(pin_heading, boat_heading)

    if heading < 0:
        heading += 360

    speed = random.uniform(MIN_SPEED, MAX_SPEED)

    result = dict(
        boat=boat,
        pin=pin,
        nacra=nacra,
        heading=heading,
        speed=speed,
    )

    import json

    print(f"""
        def test_(client, set_time, set_gps):
            params = {result}

            _draw(params)

            _test_line(
                client,
                set_time,
                set_gps,
                params,
            )
    """)

    return result


def _test_line(client, set_time, set_gps, fuzzy_params):

    # reset the line from previous tests
    _result(client.post("/line"))

    # get into the start sequence
    gun_ts = 0
    set_time(gun_ts + pi.LATENCY_OFFSET)
    resp = client.post("/start", json={"seconds": 60})
    _result(
        resp,
        state="start",
        seconds=f"0:{int(60 - pi.LATENCY_OFFSET - pi.DISPLAY_LATENCY):02}",
    )

    set_time(gun_ts - pi.DISPLAY_LATENCY)
    _result(client.get("/state"), state="start", seconds="1:00")

    set_gps(longitude=fuzzy_params["boat"][0], latitude=fuzzy_params["boat"][1])
    _result(
        client.post("/line", json={"end": "boat"}), line__pin=False, line__boat=True
    )

    set_gps(longitude=fuzzy_params["pin"][0], latitude=fuzzy_params["pin"][1])
    # super early because we're right ont the line
    _result(client.post("/line", json={"end": "pin"}), line__seconds=-60)

    set_gps(
        longitude=fuzzy_params["nacra"][0],
        latitude=fuzzy_params["nacra"][1],
        spd_over_grnd=fuzzy_params["speed"],
        true_course=fuzzy_params["heading"],
    )
    result = _result(client.get("/state"))["line"]["seconds"]

    true_value = (
        int(
            _distance_to_line(
                fuzzy_params["boat"],
                fuzzy_params["pin"],
                fuzzy_params["nacra"],
                fuzzy_params["heading"],
            )
            / (fuzzy_params["speed"] * 0.514444)
        )
        - 60
    )

    assert abs((result - true_value) / true_value * 100) <= 1


@pytest.mark.parametrize("dummy", range(100))
def test_fuzz_line(client, set_time, set_gps, fuzzy_params, dummy):
    _test_line(client, set_time, set_gps, fuzzy_params)


def _draw(params):
    import plotly.graph_objects as go

    fig = go.Figure()

    fig.add_trace(
        go.Scattergeo(
            lon=[params["boat"][0], params["pin"][0]],
            lat=[params["boat"][1], params["pin"][1]],
            text=["boat", "pin"],
            mode="markers+lines",
        )
    )

    fig.add_trace(
        go.Scattergeo(
            lon=[params["nacra"][0]],
            lat=[params["nacra"][1]],
            text=["nacra"],
            mode="markers",
        )
    )

    endpoint = geodesic.fwd(*params["nacra"], params["heading"], 1000)
    fig.add_trace(
        go.Scattergeo(
            lon=[params["nacra"][0], endpoint[0]],
            lat=[params["nacra"][1], endpoint[1]],
            # text = ["nacra"],
            mode="lines",
        )
    )

    heading = params["heading"]
    heading = math.radians(heading) if heading <= 180 else math.radians(heading - 360)
    ep_lon, ep_lat = pi._fwd(*params["nacra"], heading)

    fig.add_trace(
        go.Scattergeo(
            lon=[params["nacra"][0], ep_lon],
            lat=[params["nacra"][1], ep_lat],
            # label = "estimated heading",
            mode="lines",
        )
    )

    fig.write_html("file.html")


def test_line1(client, set_time, set_gps):

    params = {
        "boat": [72.06719313187628, 43.69691586445808],
        "pin": [72.06744323497337, 43.696937162855946],
        "nacra": [72.07088103026634, 43.693103064814494],
        "heading": 325.64543127011683,
        "speed": 5.491505255737666,
        "time_to_line": 182.00244486744177,
    }

    _draw(params)

    _test_line(
        client,
        set_time,
        set_gps,
        params,
    )


def test_line2(client, set_time, set_gps):
    params = {
        "boat": [51.83576532283867, -10.879059067717314],
        "pin": [51.83581381452237, -10.879104149929766],
        "nacra": [51.835806740848696, -10.880396226297796],
        "heading": 358.50207436841873,
        "speed": 6.396237645610728,
    }

    _draw(params)

    _test_line(
        client,
        set_time,
        set_gps,
        params,
    )


def test_line3(client, set_time, set_gps):
    params = {'boat': (87.17384445234363, 0.49996926056783764), 'pin': (87.17487552066837, 0.4999653007562529), 'nacra': (87.17467487328842, 0.4945503854062914), 'heading': 2.033050964989366, 'speed': 22.43426513558897}

    _draw(params)

    _test_line(
        client,
        set_time,
        set_gps,
        params,
    )


@pytest.mark.parametrize("dummy", range(10000))
def test_fuzz_distance(client, set_time, set_gps, fuzzy_params, dummy):
    _, _, true_distance = geodesic.inv(*fuzzy_params["boat"], *fuzzy_params["pin"])
    result = pi._distance(shapely_geom.Point(*fuzzy_params["boat"]), shapely_geom.Point(*fuzzy_params["pin"]))
    assert abs((result - true_distance) / true_distance) * 100 < 1

    _, _, true_distance = geodesic.inv(*fuzzy_params["nacra"], *fuzzy_params["pin"])
    result = pi._distance(shapely_geom.Point(*fuzzy_params["nacra"]), shapely_geom.Point(*fuzzy_params["pin"]))
    assert abs((result - true_distance) / true_distance) * 100 < 1

    _, _, true_distance = geodesic.inv(*fuzzy_params["boat"], *fuzzy_params["nacra"])
    result = pi._distance(shapely_geom.Point(*fuzzy_params["boat"]), shapely_geom.Point(*fuzzy_params["nacra"]))
    assert abs((result - true_distance) / true_distance) * 100 < 1



    

@pytest.mark.parametrize("dummy", range(1000))
def test_fuzz_to_line(client, set_time, set_gps, fuzzy_params, dummy):
    print(fuzzy_params)
    true_distance = _distance_to_line(fuzzy_params["boat"], fuzzy_params["pin"], fuzzy_params["nacra"], fuzzy_params["heading"])

    line = shapely_geom.LineString([shapely_geom.Point(*fuzzy_params["boat"]), shapely_geom.Point(*fuzzy_params["pin"])])
    result = pi._distance_to_line(line, shapely_geom.Point(*fuzzy_params["nacra"]), fuzzy_params["heading"])
    assert abs((result - true_distance) / true_distance) * 100 < 10


def test_to_line1():
    params = {'boat': (-165.15037632027585, 1.7744925995611283), 'pin': (-165.1490500901752, 1.7743460088602934), 'nacra': (-165.14861358685047, 1.769476505858151), 'heading': 340.64065600606267, 'speed': 4.222677197047366}
    # {'boat': (-170.78999096316318, -68.31441898246098), 'pin': (-170.78960036670986, -68.31456077130677), 'nacra': (-170.77928289915553, -68.31871942852514), 'heading': 317.36589497720297, 'speed': 21.540908798062524}
    _draw(params)


# def test_radius():
#     import math
#     r = pi.get_radius_at_lat(math.radians(38))
#     assert r == False
