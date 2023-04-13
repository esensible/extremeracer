import asyncio
import logging
import math
import time

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

# number of seconds from common.sync time to the start
_start_epoch = None
_start_secs = None

# state used to update display
seq_secs = silkflow.State(0)
_countdown_task = None

async def _countdown():
    global _start_epoch, _start_secs

    next_tick = _start_epoch + 1
    if ((next_tick - time.time()) % 1) < 0.5:
        next_tick += 1

    while next_tick < _start_epoch + _start_secs:
        sleep_time = next_tick - time.time()
        await asyncio.sleep(sleep_time)
        seq_secs.value = _start_epoch + _start_secs - next_tick
        await silkflow.sync_poll()
        next_tick += 1

    st_race.start()


def _handler(task):
    if task.exception() is not None:
        logger.error(f"Countdown task exception: {task.exception()}")

def start(seconds):
    global _countdown_task
    global _start_epoch, _start_secs

    #TODO: This should come from the client
    _start_epoch = time.time()
    _start_secs = seconds
    seq_secs.value = seconds

    _countdown_task = asyncio.create_task(_countdown())
    _countdown_task.add_done_callback(_handler)

    common.state.value = common.STATE_SEQ
    silkflow.sync_poll()


@silkflow.hook
def time_to_start():
    seconds = seq_secs.value
    return f"{int(seconds/60)}:{int(seconds)%60:02}"

def seq_handler(seconds):
    """Factory function to offset the sequence timer by a number of seconds"""
    def _impl(_):
        global _start_epoch, _start_secs

        now = time.time()
        remaining = _start_epoch + _start_secs - now

        if seconds == 0:
            if remaining % 60 > 60 - SYNC_MASK_SECONDS:
                return
            else:
                _start_epoch -= remaining % 60
        elif remaining > -1 * seconds:
            _start_secs += seconds

        if remaining <= 0:
            _countdown_task.cancel()
            st_race.start()
        else:
            seq_secs.value = _start_epoch + _start_secs - now

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
