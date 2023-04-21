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
    while next_tick < time.time() + 0.5:
        next_tick += 1

    # initialise display to the last value that we just skipped
    # this handles a long confirm time in the UI
    seq_secs.value = _start_secs - (next_tick - _start_epoch - 1)

    while next_tick <= _start_epoch + _start_secs:
        sleep_time = next_tick - time.time()
        await asyncio.sleep(sleep_time)
        seq_secs.value = _start_secs - (next_tick - _start_epoch)
        await silkflow.sync_poll()
        next_tick += 1

    st_race.start()


def start(epoch, seconds):
    global _countdown_task
    global _start_epoch, _start_secs

    _start_epoch = epoch / 1000.0
    _start_secs = seconds

    _countdown_task = asyncio.create_task(_countdown())
    logger.info("State change", extra=dict(from_=common.state.value, to=common.STATE_SEQ, epoch=epoch, seconds=seconds))
    common.state.value = common.STATE_SEQ
    asyncio.create_task(silkflow.sync_poll())


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

        now_remaining = _start_epoch + _start_secs - now
        logger.info("Start adjust", extra=dict(seconds=seconds, init_remaining=remaining, remaining=now_remaining))
                    
        if now_remaining <= 0:
            _countdown_task.cancel()
            st_race.start()
        else:
            seq_secs.value = now_remaining

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
            Class="buttons",
        ),
    )
