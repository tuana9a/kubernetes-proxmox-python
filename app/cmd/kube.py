import os
import urllib3

from app.cmd.core import Cmd
from app.config import load_config
from app.logger import Logger
from app.controller.node import NodeController


class KubeCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("kube", childs=[CatKubeConfigCmd()])


class CatKubeConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("cat-kubeconfig", aliases=["kubeconfig"])

    def _setup(self):
        self.parser.add_argument("-i", "--vm-id", required=False, type=int)

    def _run(self):
        args = self.parsed_args
        vm_id = args.vm_id
        urllib3.disable_warnings()
        log = Logger.from_env()

        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        control_plane_vm_ids = cfg.get("control_plane_vm_ids", None)

        nodectl = NodeController(NodeController.create_proxmox_client(**cfg),
                                 proxmox_node,
                                 log=log)

        kubeconfig_filepath = "/etc/kubernetes/admin.conf"
        cmd = ["cat", kubeconfig_filepath]

        if vm_id:
            exitcode, stdout, _ = nodectl.vm(vm_id).exec(cmd, interval_check=3)
            print(stdout)
            return

        for vm_id in control_plane_vm_ids:
            exitcode, stdout, _ = nodectl.vm(vm_id).exec(cmd, interval_check=3)
            print(stdout)
