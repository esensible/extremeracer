import asyncio
from datetime import datetime, timedelta
import logging
import math
import utils

import silkflow
from silkflow.html import *

STATE_INIT = 0
STATE_IDLE = 1
STATE_SEQ = 2
STATE_RACE = 3
state = silkflow.Signal(STATE_INIT)

logger = logging.getLogger(__name__)

class GpsData:
    __slots__ = ["latitude", "longitude", "heading", "heading_deg", "speed", "unwrapped_heading"]
    _last_heading = None

    def __init__(self, latitude, longitude, heading, speed):
        self.latitude = math.radians(latitude)
        self.longitude = math.radians(longitude)
        self.heading = math.radians(heading)
        self.heading_deg = heading
        self.speed = speed
        
        if GpsData._last_heading is None:
            self.unwrapped_heading = self.heading
        else:
            diff = self.heading - GpsData._last_heading
            if diff > math.pi:
                diff -= 2 * math.pi
            elif diff < -math.pi:
                diff += 2 * math.pi
                
            self.unwrapped_heading = GpsData._last_heading + diff
        
        GpsData._last_heading = self.unwrapped_heading

    def to_tupple(self):
        return (self.latitude, self.longitude, self.unwrapped_heading, self.speed)


gps = silkflow.Signal(GpsData(1e-5, 1e-5, 1e-5, 1e-5))


@silkflow.effect
def speed():
    return f"{gps.value.speed:.1f}"


@silkflow.effect
def heading():
    return f"{gps.value.heading_deg:.0f}"


now = silkflow.Signal(datetime.now().strftime("%I:%M").lstrip("0"))


async def time_task():
    while True:
        _now = datetime.now()
        next_minute = _now + timedelta(minutes=1)
        next_minute = next_minute.replace(second=0, microsecond=0)
        remaining_seconds = (next_minute - _now).total_seconds()
        await asyncio.sleep(remaining_seconds)
        now.value = next_minute.strftime("%I:%M").lstrip("0")
        await silkflow.sync_effects()


@silkflow.effect
def time_of_day():
    return now.value


#
# The line component is common to idle and seq states
#
LINE_NONE = 0
LINE_PORT = 1
LINE_STBD = 2
LINE_BOTH = LINE_PORT | LINE_STBD
line = silkflow.Signal(LINE_NONE)


line_stbd = None
line_port = None
line_heading = None
line_length = None

line_cross_seconds = silkflow.Signal(0)
line_cross_point = silkflow.Signal(0)


def update_gps(latitude, longitude, heading, speed, sync=True):
    pos = GpsData(latitude, longitude, heading, speed)
    gps.value = pos

    if state.value != STATE_INIT:
        logger.info("gps", extra=dict(pos=pos.to_tupple(), state=state.value))

    if line.value == LINE_BOTH:
        cross, tmp, line_cross_seconds.value = utils.seconds_to_line(
            pos.latitude,
            pos.longitude,
            pos.heading,
            pos.speed,
            *line_stbd,
            *line_port,
            line_heading,
            line_length,
        )
        line_cross_point.value = tmp * 100

    if sync and state.value in (STATE_IDLE, STATE_RACE):
        # idle and race are just chillin, waiting for 1m boundaries
        asyncio.create_task(silkflow.sync_effects())


@silkflow.callback
def click_stbd(event):
    global line_stbd

    line.value = line.value | LINE_STBD
    line_stbd = (
        gps.value.latitude,
        gps.value.longitude,
    )

    logger.info("click_stbd", extra=dict(loc=line_stbd, line=line.value))

    if line.value == LINE_BOTH:
        global line_heading
        global line_length
        line_heading = utils.bearing(
            line_stbd[0], line_stbd[1], line_port[0], line_port[1]
        )
        line_length = utils.distance(*line_stbd, *line_port)
        logger.info("line", extra=dict(stbd=line_stbd, port=line_port, heading=line_heading, length=line_length))


@silkflow.callback
def click_port(event):
    global line_port

    line.value = line.value | LINE_PORT
    line_port = (
        gps.value.latitude,
        gps.value.longitude,
    )
    logger.info("click_port", extra=dict(loc=line_port, line=line.value))

    if line.value == LINE_BOTH:
        global line_heading
        global line_length
        line_heading = utils.bearing(
            line_stbd[0], line_stbd[1], line_port[0], line_port[1]
        )
        line_length = utils.distance(*line_stbd, *line_port)
        logger.info("line", extra=dict(stbd=line_stbd, port=line_port, heading=line_heading, length=line_length))


@silkflow.effect
def time_to_line():
    seconds = line_cross_seconds.value
    # if state.value == STATE_SEQ:
    #     #FIXME: this is a foot gun
    #     seconds -= seq_secs.value

    neg = True if seconds < 0 else False
    seconds = abs(seconds)

    return (
        "~"
        if seconds > 3600
        else f"{'-' if neg else ''}{int(seconds/60)}:{int(abs(seconds))%60:02}"
    )


MARGIN = 5


@silkflow.effect
def line_cross():
    cross_value = int(line_cross_point.value)
    return (
        f"left: {cross_value}%"
        if cross_value < 50 - MARGIN
        else f"right: {100-cross_value}%"
    )


@silkflow.effect
def render_line_buttons():
    if line.value == LINE_BOTH:
        return div(
            div(span(time_to_line(), Class="center-text"), Class="z-index"),
            div(Class="floating-square", style=line_cross()),
            button(
                span("Port", Class="bottom-left"),
                Class="line trans",
                onClick=click_port,
            ),
            button(
                span("Stbd", Class="bottom-right"),
                Class="line trans",
                onClick=click_stbd,
            ),
            Class="wrapper",
        )

    stbd_class = "line refresh" if line.value & LINE_STBD else "line"
    port_class = "line refresh" if line.value & LINE_PORT else "line"

    return div(
        button("Port", Class=port_class, onClick=click_port),
        button("Stbd", Class=stbd_class, onClick=click_stbd),
        Class="wrapper",
    )
