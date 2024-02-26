import __future__
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
    NOTHING: Self
    DEBUG: Self
    INFO: Self

    def __init__(self):
        pass

    def info(self, *msg):
        pass

    def debug(self, *msg):
        pass

    def error(self, *msg):
        pass


class NothingLogger(Logger):

    def info(self, *msg):
        pass

    def debug(self, *msg):
        pass

    def error(self, *msg):
        pass


class DebugLogger(Logger):

    def info(self, *msg):
        msg = to_string(msg)
        print(f"{now()} [INFO] {msg}")

    def debug(self, *msg):
        msg = to_string(msg)
        print(f"{now()} [DEBUG] {msg}")

    def error(self, *msg):
        msg = to_string(msg)
        print(f"{now()} [ERROR] {msg}")


class InfoLogger(Logger):

    def info(self, *msg):
        msg = to_string(msg)
        print(f"{now()} [INFO] {msg}")

    def debug(self, *msg):
        msg = to_string(msg)
        pass

    def error(self, *msg):
        msg = to_string(msg)
        print(f"{now()} [ERROR] {msg}")


Logger.NOTHING = NothingLogger()
Logger.DEBUG = DebugLogger()
Logger.INFO = InfoLogger()
