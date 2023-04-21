import asyncio
import logging

import common
import st_sequence

import silkflow
from silkflow.html import *

logger = logging.getLogger(__name__)

#
# Idle state handler
#

time_task = None


def start():
    global time_task

    time_task = asyncio.create_task(common.time_task())
    logger.info("State change", extra=dict(from_=common.state.value, to=common.STATE_IDLE))
    common.state.value = common.STATE_IDLE
    asyncio.create_task(silkflow.sync_poll())


def idle_handler(seconds):
    """Factory function to set the sequence timer to a number of seconds"""

    def _impl(event):
        global time_task

        if time_task is not None:
            time_task.cancel()
            time_task = None

        st_sequence.start(event["time"], seconds)

    return silkflow.callback(confirm=True)(_impl)


def render():
    return div(
        div(common.speed(), Class="gps"),
        div(common.time_of_day(), Class="gps"),
        div(
            common.render_line_buttons(),
            div(
                button("10", Class="idle", onClick=idle_handler(600)),
                button("5", Class="idle", onClick=idle_handler(300)),
                button("4", Class="idle", onClick=idle_handler(240)),
                button("1", Class="idle", onClick=idle_handler(60)),
                id="idle",
            ),
            Class="buttons",
        ),
    )
