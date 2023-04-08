import common
import sequence

import silkflow
from silkflow.html import *

#
# Idle state
#



def idle_handler(seconds):
    """Factory function to set the sequence timer to a number of seconds"""
    def _impl(_):
        sequence.start_countdown(seconds)
        common.state.value = common.STATE_SEQ

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
