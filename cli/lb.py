import urllib3

from cli.core import Cmd
from app.config import load_config
from app.logger import Logger
from app.controller.node import NodeController
from app.service.lb import LbService


class LbCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("lb", childs=[CreateLbCmd()])


class CreateLbCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("create")

    def _run(self):
        urllib3.disable_warnings()
        log = Logger.from_env()
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)

        service = LbService(nodectl, log=log)
        service.create_lb(**cfg)
