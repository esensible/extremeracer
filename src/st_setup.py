import asyncio

import silkflow
from silkflow.html import *

import common
import st_idle

#
# Setup state handler
#

time_task = None


def start():
    global time_task

    time_task = asyncio.create_task(common.time_task())
    common.state.value = common.STATE_INIT
    asyncio.create_task(silkflow.sync_poll())


@silkflow.callback
def push_off(_):
    global time_task

    if time_task is not None:
        time_task.cancel()
        time_task = None

    st_idle.start()


def render():
    return div(
        img(src="/static/pissing.jpg"),
        div(common.time_of_day(), Class="z-index"),
        div(button("Push off", onClick=push_off, Class="finish"), Class="buttons"),
    )
