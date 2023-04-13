import fastapi
from fastapi.staticfiles import StaticFiles
import logging
from pythonjsonlogger import jsonlogger
import os

import silkflow
from silkflow.html import *

import common
import gps
import st_idle
import st_race
import st_setup
import st_sequence

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

app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)

app.include_router(silkflow.router)


def head():
    return [
        title("Extreme Racer"),
        link(href="static/style.css", rel="stylesheet"),
    ]


@app.get("/")
@silkflow.hook(render=True, head_elems=head())
def render_ui():
    if common.state.value == common.STATE_INIT:
        return st_setup.render()
    elif common.state.value == common.STATE_IDLE:
        return st_idle.render()
    elif common.state.value == common.STATE_SEQ:
        return st_sequence.render()
    elif common.state.value == common.STATE_RACE:
        return st_race.render()
    else:
        return div(h1("Unknown state"))


@app.on_event("startup")
async def app_startup():
    gps.start()
    st_setup.start()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True, log_level="debug")
