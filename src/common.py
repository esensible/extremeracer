import asyncio
from datetime import datetime, timedelta
import math
import utils

import silkflow
from silkflow.html import *

import gps

STATE_INIT = 0
STATE_IDLE = 1
STATE_SEQ = 2
STATE_RACE = 3
state = silkflow.State(STATE_INIT)

sync_condition = None


@silkflow.hook
def speed():
    return f"{gps.state.value.spd_over_grnd:.1f}"


@silkflow.hook
def heading():
    return f"{gps.state.value.true_course:.0f}"


now = silkflow.State(datetime.now().strftime("%I:%M").lstrip("0"))


async def time_task():
    while True:
        _now = datetime.now()
        next_minute = _now + timedelta(minutes=1)
        next_minute = next_minute.replace(second=0, microsecond=0)
        remaining_seconds = (next_minute - _now).total_seconds()
        await asyncio.sleep(remaining_seconds)
        now.value = next_minute.strftime("%I:%M").lstrip("0")
        await silkflow.sync_poll()


@silkflow.hook
def time_of_day():
    return now.value


#
# The line component is common to idle and seq states
#
LINE_NONE = 0
LINE_PORT = 1
LINE_STBD = 2
LINE_BOTH = LINE_PORT | LINE_STBD
line = silkflow.State(LINE_NONE)


line_stbd = None
line_port = None
line_heading = None


@silkflow.callback
def click_stbd(event):
    global line_stbd

    line.value = line.value | LINE_STBD
    line_stbd = (
        math.radians(gps.state.value.latitude),
        math.radians(gps.state.value.longitude),
    )

    if line.value == LINE_BOTH:
        global line_heading
        line_heading = utils.bearing(
            line_stbd[0], line_stbd[1], line_port[0], line_port[1]
        )


@silkflow.callback
def click_port(event):
    global line_port

    line.value = line.value | LINE_PORT
    line_port = (
        math.radians(gps.state.value.latitude),
        math.radians(gps.state.value.longitude),
    )

    if line.value == LINE_BOTH:
        global line_heading
        line_heading = utils.bearing(
            line_stbd[0], line_stbd[1], line_port[0], line_port[1]
        )


@silkflow.hook
def time_to_line():
    boat = (
        math.radians(gps.state.value.latitude),
        math.radians(gps.state.value.longitude),
        math.radians(gps.state.value.true_course),
        gps.state.value.spd_over_grnd,
    )
    _, seconds = utils.seconds_to_line(*boat, *line_stbd, *line_port, line_heading)

    if state.value == STATE_SEQ:
        seconds -= seq_secs.value

    neg = True if seconds < 0 else False
    seconds = abs(seconds)

    return "~" if seconds > 3600 else f"{'-' if neg else ''}{int(seconds/60)}:{int(abs(seconds))%60:02}"


@silkflow.hook
def render_line_buttons():
    if line.value == LINE_BOTH:
        return div(
            div(span(time_to_line(), Class="center-text"), Class="z-index"),
            button(
                span("Boat", Class="bottom-left"),
                Class="line trans",
                onClick=click_stbd,
            ),
            button(
                span("Pin", Class="bottom-right"), Class="line trans", onClick=click_port
            ),
            Class="wrapper",
        )

    boat_class = "line refresh" if line.value & LINE_STBD else "line"
    pin_class = "line refresh" if line.value & LINE_PORT else "line"

    return div(
        button("Boat", Class=boat_class, onClick=click_stbd),
        button("Pin", Class=pin_class, onClick=click_port),
        Class="wrapper",
    )
