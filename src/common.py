import asyncio
from datetime import datetime, timedelta

import silkflow
from silkflow.html import *

import gps

STATE_INIT = 0
STATE_IDLE = 1
STATE_SEQ = 2
STATE_RACE = 3
state = silkflow.State(STATE_INIT)


@silkflow.hook
def speed():
    return f"{gps.state.value.spd_over_grnd:.1f}"

@silkflow.hook
def heading():
    return f"{gps.state.value.true_course:.0f}"

       
now = silkflow.State(datetime.now().strftime("%I:%M").lstrip('0'))

async def time_generator():
    while True:
        _now = datetime.now()
        next_minute = _now + timedelta(minutes=1)
        next_minute = next_minute.replace(second=0, microsecond=0)
        remaining_seconds = (next_minute - _now).total_seconds()
        await asyncio.sleep(remaining_seconds)
        now.value = next_minute.strftime("%I:%M").lstrip('0')

def create_clock_task():
    return asyncio.create_task(time_generator())

@silkflow.hook
def time_of_day():
    return now.value


#
# The line component is common to idle and seq states
#
LINE_NONE = 0
LINE_PIN = 1
LINE_BOAT = 2
LINE_BOTH = LINE_PIN | LINE_BOAT
line = silkflow.State(LINE_NONE)


@silkflow.callback
def click_boat(event):
    line.value = line.value | LINE_BOAT


@silkflow.callback
def click_pin(event):
    line.value = line.value | LINE_PIN


@silkflow.hook
def time_to_line():
    return span("2:03", Class="center-text")


@silkflow.hook
def render_line_buttons():
    if line.value == LINE_BOTH:
        return div(
            div(time_to_line(), Class="z-index"),
            button(
                span("Boat", Class="bottom-left"),
                Class="line trans",
                onClick=click_boat,
            ),
            button(
                span("Pin", Class="bottom-right"), Class="line trans", onClick=click_pin
            ),
            Class="wrapper",
        )

    boat_class = "line refresh" if line.value & LINE_BOAT else "line"
    pin_class = "line refresh" if line.value & LINE_PIN else "line"

    return div(
        button("Boat", Class=boat_class, onClick=click_boat),
        button("Pin", Class=pin_class, onClick=click_pin),
        Class="wrapper",
    )
