import asyncio
import logging
import sys

import silkflow
from silkflow.html import *

import common
import race

logger = logging.getLogger(__name__)


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

def start_countdown(seconds):
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
        seq_secs.value = (
            seq_secs.value + seconds
            if seconds
            else seq_secs.value - seq_secs.value % 60
        )
        if seq_secs.value <= 0:
            race.start_timer()
            common.state.value = common.STATE_RACE

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
