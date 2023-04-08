from datetime import datetime
import time
try:
    import asyncio
    import serial_asyncio
except:
    pass
import pynmea2

import silkflow


state = silkflow.State(pynmea2.parse(
    "$GPRMC,181643.000,A,3456.6333,S,13836.9472,E,0.44,140.90,211022,,,A*72"
))

class GPSProtocol(asyncio.Protocol):
    def __init__(self):
        self.buffer = ""
        self.offset_applied = False

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        self.buffer += data.decode()
        tmp = self.buffer.split("\r\n")
        if len(tmp) > 1:
            self.buffer = tmp[-1]
            for t in tmp[:-1]:
                try:
                    pos = pynmea2.parse(t)
                except:
                    continue

                if pos.identifier() == "GPRMC,":
                    if not self.offset_applied:
                        self.apply_time_offset_from_msg(pos)
                        self.offset_applied = True

                    state.value = pos

    def apply_time_offset_from_msg(self, msg):
        system_time = datetime.utcnow()
        gps_time = datetime.combine(msg.datestamp, msg.timestamp)
        time_offset = gps_time - system_time

        _original_time = time.time

        def time_with_offset():
            return _original_time() + time_offset.total_seconds()

        time.time = time_with_offset

    async def __call__(self):
        await serial_asyncio.create_serial_connection(
            asyncio.get_event_loop(), lambda: self, "/dev/serial0", baudrate=9600
        )

def start():
    gps_protocol = GPSProtocol()
    asyncio.create_task(gps_protocol())
