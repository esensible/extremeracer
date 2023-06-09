import asyncio
from datetime import datetime, timedelta
import logging

import silkflow
from silkflow.html import *

import common

logger = logging.getLogger(__name__)

#
# Race state handler
#

race_timer = silkflow.Signal("0")

_race_start = None
_race_timer_task = None


async def _timer():
    now = datetime.now()
    race_seconds = (now - _race_start).total_seconds()
    race_timer.value = str(int(race_seconds / 60))

    while True:
        now = datetime.now()
        race_seconds = (now - _race_start).total_seconds()
        remaining_seconds = 60 - (race_seconds % 60)

        await asyncio.sleep(remaining_seconds)
        race_timer.value = str(int(race_seconds / 60))
        await silkflow.sync_effects()


def start():
    global _race_timer_task
    global _race_start

    _race_start = datetime.now()
    _race_timer_task = asyncio.create_task(_timer())
    logger.info("State change", extra=dict(from_=common.state.value, to=common.STATE_RACE))
    common.state.value = common.STATE_RACE
    asyncio.create_task(silkflow.sync_effects())


@silkflow.effect
def elapsed_time():
    return race_timer.value


@silkflow.callback(confirm=2)
def finish(_):
    _race_timer_task.cancel()
    common.state.value = common.STATE_IDLE


def render():
    return div(
        div(common.speed(), Class="gps"),
        div(common.heading(), Class="gps"),
        div(
            button(elapsed_time(), onClick=finish, Class="refresh finish"),
            Class="buttons",
        ),
    )
