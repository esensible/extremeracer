import asyncio
import logging
import sys

import silkflow
from silkflow.html import *

import common
import st_race

logger = logging.getLogger(__name__)

#
# Start sequence state handler
#

# disables the sync button for some seconds after the minute rollover
# to prevent accidental syncs due to display latency
SYNC_MASK_SECONDS = 10

seq_secs = silkflow.State(0)
_countdown_task = None

async def _countdown():
    while seq_secs.value > 0:
        await asyncio.sleep(1)
        seq_secs.value -= 1
    race.start()

def _handler(task):
    exception = task.exception()
    if exception:
        logging.error("Countdown task exception: %s", exception, exc_info=sys.exc_info())

def start(seconds):
    global _countdown_task
    _countdown_task = asyncio.create_task(_countdown())
    _countdown_task.add_done_callback(_handler)

    seq_secs.value = seconds

@silkflow.hook
def time_to_start():
    seconds = seq_secs.value
    return f"{int(seconds/60)}:{int(seconds)%60:02}"

def seq_handler(seconds):
    """Factory function to offset the sequence timer by a number of seconds"""
    def _impl(_):
        if seconds == 0:
            if seq_secs.value % 60 > 60 - SYNC_MASK_SECONDS:
                return
            else:
                seq_secs.value = seq_secs.value - seq_secs.value % 60
        elif seq_secs.value > -1 * seconds:
            seq_secs.value = seq_secs.value + seconds

        if seq_secs.value <= 0:
            st_race.start()

    return silkflow.callback(_impl)


def render():
    return div(
        div(common.speed(), Class="gps"),
        div(time_to_start(), Class="gps"),
        div(
            common.render_line_buttons(),
            div(
                button("5", onClick=seq_handler(-300), Class="five"),
                button("1", onClick=seq_handler(-60), Class="one"),
                button("Sync", onClick=seq_handler(0), Class="zero"),
                button("1", onClick=seq_handler(60), Class="one"),
                button("5", onClick=seq_handler(300), Class="five"),
            ),
            Class="buttons"
        )
    )
