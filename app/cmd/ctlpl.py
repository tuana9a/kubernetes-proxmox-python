import os
import urllib3

from app.cmd.core import Cmd
from app.config import load_config
from app.logger import Logger
from app.controller.node import NodeController
from app.service.ctlpl import ControlPlaneService


class ControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("control-plane",
                         childs=[
                             CreateControlPlaneCmd(),
                             DeleteControlPlaneCmd(),
                             CatKubeConfigCmd(),
                             CopyKubeCertsCmd(),
                         ],
                         aliases=["ctlpl"])


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

        service = ControlPlaneService(nodectl, log=log)
        service.create_control_plane(**cfg)


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
        clusterctl = ControlPlaneService(nodectl, log=log)
        clusterctl.delete_control_plane(vm_id, **cfg)


class CatKubeConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("cat-kubeconfig", aliases=["kubeconfig"])

    def _setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("-f",
                                 "--file-path",
                                 default="/etc/kubernetes/admin.conf")

    def _run(self):
        args = self.parsed_args
        vm_id = args.vmid
        filepath = args.file_path
        urllib3.disable_warnings()
        log = Logger.from_env()

        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        nodectl = NodeController(NodeController.create_proxmox_client(**cfg),
                                 proxmox_node,
                                 log=log)
        ctlplvmctl = nodectl.ctlplvmctl(vm_id)
        _, stdout, _ = ctlplvmctl.cat_kubeconfig(filepath)
        print(stdout)


class CopyKubeCertsCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("copy-certs")

    def _setup(self):
        self.parser.add_argument("source", type=int)
        self.parser.add_argument("dest", type=int)

    def _run(self):
        args = self.parsed_args
        source_id = args.source
        dest_id = args.dest
        urllib3.disable_warnings()
        log = Logger.from_env()

        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]

        nodectl = NodeController(NodeController.create_proxmox_client(**cfg),
                                 proxmox_node,
                                 log=log)

        nodectl.ctlplvmctl(dest_id).ensure_cert_dirs()

        service = ControlPlaneService(nodectl, log=log)
        service.copy_kube_certs(source_id, dest_id)
