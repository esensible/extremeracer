import fastapi
from fastapi.staticfiles import StaticFiles
import logging
from pythonjsonlogger import jsonlogger
import os

import silkflow
from silkflow.html import *

import common
import gps
import idle
import race
import setup
import sequence

# Configure the root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

log_handler = logging.FileHandler(filename="trace.json")
# log_handler = logging.StreamHandler()

formatter = jsonlogger.JsonFormatter(timestamp=True)
log_handler.setFormatter(formatter)
root_logger.addHandler(log_handler)

logger = logging.getLogger(__name__)


app = fastapi.FastAPI()

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

app.include_router(silkflow.router)


def head():
    return [
        silkflow.html.title("Extreme Racer"),
        silkflow.html.link(href="static/style.css", rel="stylesheet"),
    ]

@app.get("/")
@silkflow.hook(render=True, head_elems=head())
def render_ui():
    if common.state.value == common.STATE_INIT:
        return setup.render()
    elif common.state.value == common.STATE_IDLE:
        return idle.render()
    elif common.state.value == common.STATE_SEQ:
        return sequence.render()
    elif common.state.value == common.STATE_RACE:
        return race.render()
    else:
        return div("Unknown state")



@app.on_event("startup")
async def app_startup():
    gps.create_task()
    common.create_clock_task()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True, log_level="debug")
