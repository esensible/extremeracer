try:
    import asyncio
    import serial_asyncio
except:
    pass
from datetime import datetime
import time
import pynmea2

import common


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

                    common.update_gps(
                        pos.latitude, pos.longitude, pos.true_course, pos.spd_over_grnd
                    )

        # stop callbacks again immediately
        self.pause_reading()

    def pause_reading(self):
        # This will stop the callbacks to data_received
        self.transport.pause_reading()

    def resume_reading(self):
        # This will start the callbacks to data_received again with all data that has been received in the meantime.
        self.transport.resume_reading()

    def apply_time_offset_from_msg(self, msg):
        system_time = datetime.utcnow()
        gps_time = datetime.combine(msg.datestamp, msg.timestamp)
        time_offset = gps_time - system_time

        _original_time = time.time

        def time_with_offset():
            return _original_time() + time_offset.total_seconds()

        time.time = time_with_offset

    async def __call__(self):
        transport, protocol = await serial_asyncio.create_serial_connection(
            asyncio.get_event_loop(), lambda: self, "/dev/serial0", baudrate=9600
        )

        while True:
            await asyncio.sleep(0.3)
            protocol.resume_reading()


def start():
    gps_protocol = GPSProtocol()
    asyncio.create_task(gps_protocol())
