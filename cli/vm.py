import os
import urllib3

from cli.core import Cmd
from app.config import load_config
from app.logger import Logger
from app.ctler.node import NodeController


class VmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__(
            "vm",
            childs=[RebootVmCmd(),
                    RemoveVmCmd(),
                    StartVmCmd(),
                    CopyFileCmd()])


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
        log.info("vm_ids", ids)
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
        log.info("vm_ids", ids)
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        for id in ids:
            vmctl = nodectl.vmctl(id)
            vmctl.shutdown()
            vmctl.wait_for_shutdown()
            vmctl.delete()


class StartVmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("start", aliases=["run", "up"])

    def _setup(self):
        self.parser.add_argument("ids", nargs="+")

    def _run(self):
        urllib3.disable_warnings()
        args = self.parsed_args
        log = Logger.from_env()
        ids = args.ids
        log.info("vm_ids", ids)
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        for id in ids:
            vmctl = nodectl.vmctl(id)
            vmctl.startup()
            vmctl.wait_for_guest_agent()


class CopyFileCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("copy-file", aliases=["cp"])

    def _setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("localpath", type=str)
        self.parser.add_argument("path", type=str)

    def _run(self):
        args = self.parsed_args
        localpath = args.localpath
        path = args.path
        vm_id = args.vmid
        urllib3.disable_warnings()
        log = Logger.from_env()
        log.info("vm_id", vm_id)
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        vmctl = nodectl.vmctl(vm_id)
        log.info(localpath, "->", path)
        with open(localpath, "r", encoding="utf-8") as f:
            vmctl.write_file(path, f.read())
