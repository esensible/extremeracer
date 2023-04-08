import silkflow
from silkflow.html import *

import common

@silkflow.callback
def push_off(_):
    common.state.value = common.STATE_IDLE

def render():
    return div(
            img(src="/static/pissing.jpg"),
            div(common.time_of_day(), Class="z-index"),
            div(
                button("Push off", onClick=push_off, Class="finish"),
                Class="buttons"
            )
        )
