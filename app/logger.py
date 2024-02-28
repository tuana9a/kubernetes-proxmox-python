import os

from datetime import datetime
from typing_extensions import Self


def now():
    current = datetime.now()
    formatted = current.strftime("%Y-%m-%d %H:%M:%S")
    return formatted


def to_string(msg):
    out = " ".join(list(map(lambda x: str(x), msg)))
    return out


class Logger:
    ERROR: Self
    WARN: Self
    INFO: Self
    DEBUG: Self

    @staticmethod
    def from_env():
        level = (os.getenv("LOGGER") or "").upper()
        if level == "DEBUG": return Logger.DEBUG
        if level == "INFO": return Logger.INFO
        if level == "WARN": return Logger.WARN
        return Logger.ERROR

    def __init__(self):
        pass

    def error(self, *msg):
        msg = to_string(msg)
        print(f"{now()} [ERROR] {msg}")

    def warn(self, *msg):
        pass

    def info(self, *msg):
        pass

    def debug(self, *msg):
        pass


class WarnLogger(Logger):

    def warn(self, *msg):
        msg = to_string(msg)
        print(f"{now()} [WARM] {msg}")


class InfoLogger(WarnLogger):

    def info(self, *msg):
        msg = to_string(msg)
        print(f"{now()} [INFO] {msg}")


class DebugLogger(InfoLogger):

    def debug(self, *msg):
        msg = to_string(msg)
        print(f"{now()} [DEBUG] {msg}")


Logger.ERROR = Logger()
Logger.WARN = WarnLogger()
Logger.INFO = InfoLogger()
Logger.DEBUG = DebugLogger()
