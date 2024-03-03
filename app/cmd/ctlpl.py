import os
import urllib3

from app.cmd.core import Cmd
from app.config import load_config
from app.logger import Logger
from app.controller.node import NodeController
from app.controller.ctlpl import ControlPlaneController


class ControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__(
            "control-plane",
            childs=[CreateControlPlaneCmd(),
                    DeleteControlPlaneCmd()],
            aliases=["cp", "ctlpl"])


class CreateControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("create")

    def _run(self):
        urllib3.disable_warnings()
        log = Logger.from_env()

        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]

        nodectl = NodeController(NodeController.create_proxmox_client(**cfg),
                                 proxmox_node,
                                 log=log)

        clusterctl = ControlPlaneController(nodectl, log=log)
        clusterctl.create_control_plane(**cfg)


class DeleteControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("delete", aliases=["remove", "rm"])

    def _setup(self):
        self.parser.add_argument("vmid", type=int)

    def _run(self):
        urllib3.disable_warnings()
        log = Logger.from_env()
        cfg = load_config(log=log)
        args = self.parsed_args
        vm_id = args.vmid or os.getenv("VMID")
        log.debug("vm_id", vm_id)

        if not vm_id:
            raise ValueError("vm_id is missing")

        proxmox_node = cfg["proxmox_node"]

        nodectl = NodeController(NodeController.create_proxmox_client(**cfg),
                                 proxmox_node,
                                 log=log)
        clusterctl = ControlPlaneController(nodectl, log=log)
        clusterctl.delete_control_plane(vm_id, **cfg)
