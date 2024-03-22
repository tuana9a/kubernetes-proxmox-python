import os
import json
from app.logger import Logger


def load_config(config_path=os.getenv("CONFIG_PATH"), log=Logger.DEBUG):
    log.info("config_path", config_path)
    if not config_path:
        raise ValueError("CONFIG_PATH is not set")
    if not os.path.exists(config_path):
        raise FileNotFoundError(config_path)
    with open(config_path, "r") as f:
        return json.loads(f.read())


TIMEOUT = 30 * 60  # 30 min
