import os
import urllib3

from app.cmd.core import Cmd
from app.config import load_config
from app.logger import Logger
from app.controller.node import NodeController


class VmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("vm", childs=[RebootVmCmd(), RemoveVmCmd()])


class RebootVmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("reboot")

    def _setup(self):
        self.parser.add_argument("ids", nargs="+")

    def _run(self):
        urllib3.disable_warnings()
        args = self.parsed_args
        log = Logger.from_env()
        ids = args.ids
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        for id in ids:
            vmctl = nodectl.vmctl(id)
            vmctl.reboot()


class RemoveVmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("remove", aliases=["rm"])

    def _setup(self):
        self.parser.add_argument("ids", nargs="+")

    def _run(self):
        urllib3.disable_warnings()
        args = self.parsed_args
        log = Logger.from_env()
        ids = args.ids
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        for id in ids:
            vmctl = nodectl.vmctl(id)
            vmctl.shutdown()
            vmctl.wait_for_shutdown()
            vmctl.delete()
