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
        self.parser.add_argument("-i", "--vm-id", type=int, required=False)

    def _run(self):
        urllib3.disable_warnings()
        args = self.parsed_args
        log = Logger.from_env()
        target_vm_id = args.vm_id or os.getenv("VMID")
        if not target_vm_id:
            raise ValueError("vmid is missing")
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        nodectl = NodeController(NodeController.create_proxmox_client(**cfg),
                                 proxmox_node,
                                 log=log)
        vmctl = nodectl.vm(target_vm_id)
        vmctl.reboot()


class RemoveVmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("remove", aliases=["rm"])

    def _setup(self):
        self.parser.add_argument("-i", "--vm-id", type=int, required=False)

    def _run(self):
        urllib3.disable_warnings()
        args = self.parsed_args
        log = Logger.from_env()
        target_vm_id = args.vm_id or os.getenv("VMID")
        if not target_vm_id:
            raise ValueError("vmid is missing")
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        nodectl = NodeController(NodeController.create_proxmox_client(**cfg),
                                 proxmox_node,
                                 log=log)
        vmctl = nodectl.vm(target_vm_id)
        vmctl.shutdown()
        vmctl.wait_for_shutdown()
        vmctl.delete()
