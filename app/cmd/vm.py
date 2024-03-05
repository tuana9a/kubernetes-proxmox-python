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
        self.parser.add_argument("vmid", type=int)

    def _run(self):
        urllib3.disable_warnings()
        args = self.parsed_args
        log = Logger.from_env()
        vm_id = args.vmid or os.getenv("VMID")
        if not vm_id:
            raise ValueError("vm_id is missing")
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        nodectl = NodeController(NodeController.create_proxmox_client(**cfg),
                                 proxmox_node,
                                 log=log)
        vmctl = nodectl.vmctl(vm_id)
        vmctl.reboot()


class RemoveVmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("remove", aliases=["rm"])

    def _setup(self):
        self.parser.add_argument("vmid", type=int)

    def _run(self):
        urllib3.disable_warnings()
        args = self.parsed_args
        log = Logger.from_env()
        vm_id = args.vmid or os.getenv("VMID")
        if not vm_id:
            raise ValueError("vm_id is missing")
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        nodectl = NodeController(NodeController.create_proxmox_client(**cfg),
                                 proxmox_node,
                                 log=log)
        vmctl = nodectl.vmctl(vm_id)
        vmctl.shutdown()
        vmctl.wait_for_shutdown()
        vmctl.delete()
