import gzip
import logging
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger

class GzipRotatingFileHandler(RotatingFileHandler):
    def _open(self):
        return gzip.open(self.baseFilename, self.mode, encoding=self.encoding)


def configure_logging():
    log_handler = logging.FileHandler(filename="trace.json")
    # log_handler = GzipRotatingFileHandler("trace.gz", maxBytes=512 * 1024, backupCount=5)
    formatter = jsonlogger.JsonFormatter(timestamp=True)
    log_handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(log_handler)

