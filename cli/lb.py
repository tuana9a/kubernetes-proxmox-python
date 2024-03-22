import urllib3

from cli.core import Cmd
from app.config import load_config
from app.logger import Logger
from app.ctler.node import NodeController
from app.svc.lb import LbService


class LbCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("lb",
                         childs=[CreateLbCmd(),
                                 RollLbCmd(),
                                 CopyConfigCmd()])


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


class RollLbCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("roll")

    def _setup(self):
        self.parser.add_argument("vmid", type=int)

    def _run(self):
        args = self.parsed_args
        vm_id = args.vmid
        urllib3.disable_warnings()
        log = Logger.from_env()
        log.info("vm_id", vm_id)
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        service = LbService(nodectl, log=log)
        service.roll_lb(vm_id, **cfg)


class CopyConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("copy-config", aliases=["cfg"])

    def _setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("path", type=str)

    def _run(self):
        args = self.parsed_args
        path = args.path
        vm_id = args.vmid
        urllib3.disable_warnings()
        log = Logger.from_env()
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        lbctl = nodectl.lbctl(vm_id)
        with open(path, "r", encoding="utf-8") as f:
            lbctl.write_file("/etc/haproxy/haproxy.cfg", f.read())
        lbctl.reload_haproxy()
