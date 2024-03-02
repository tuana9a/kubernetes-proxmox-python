import urllib3

from app.cmd.core import Cmd
from app.config import load_config
from app.logger import Logger
from app.controller.node import NodeController
from app.controller.lb import LbController


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

        nodectl = NodeController(NodeController.create_proxmox_client(**cfg,
                                                                      log=log),
                                 proxmox_node,
                                 log=log)

        lbctl = LbController(nodectl, log=log)
        lbctl.create_load_balancer(**cfg)
