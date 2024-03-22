import os
import urllib3

from cli.core import Cmd
from app.config import load_config
from app.logger import Logger
from app.ctler.node import NodeController
from app.svc.ctlpl import ControlPlaneService
from app import util


class ControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("control-plane",
                         childs=[
                             CreateControlPlaneCmd(),
                             DeleteControlPlaneCmd(),
                             CatKubeConfigCmd(),
                             CopyKubeCertsCmd(),
                             JoinControlPlaneCmd(),
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
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)

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
        log.info("vm_id", vm_id)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
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
        log.info("vm_id", vm_id)
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
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
        log.info("src", source_id, "dest", dest_id)
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        nodectl.ctlplvmctl(dest_id).ensure_cert_dirs()
        service = ControlPlaneService(nodectl, log=log)
        service.copy_kube_certs(source_id, dest_id)


class JoinControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("join")

    def _setup(self):
        self.parser.add_argument("ctlplid", type=int)
        self.parser.add_argument("ctlplids", nargs="+")

    def _run(self):
        urllib3.disable_warnings()
        log = Logger.from_env()
        args = self.parsed_args
        control_plane_id = args.ctlplid
        control_plane_ids = args.ctlplids
        log.info("dad", control_plane_id, "childs", control_plane_ids)
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        service = ControlPlaneService(nodectl, log=log)
        load_balancer_vm_id = cfg["load_balancer_vm_id"]
        lbctl = nodectl.lbctl(load_balancer_vm_id)
        dadctl = nodectl.ctlplvmctl(control_plane_id)
        join_cmd = dadctl.kubeadm().create_join_command(is_control_plane=True)
        for id in control_plane_ids:
            ctlplvmctl = nodectl.ctlplvmctl(id)
            ctlplvmctl.ensure_cert_dirs()
            service.copy_kube_certs(control_plane_id, id)
            current_config = ctlplvmctl.current_config()
            ifconfig0 = current_config.get("ipconfig0", None)
            if not ifconfig0:
                raise Exception("can not detect the vm ip")
            vm_ip = util.ProxmoxUtil.extract_ip(ifconfig0)
            exitcode, _, stderr = lbctl.add_backend("control-plane", id,
                                                    f"{vm_ip}:6443")
            if exitcode != 0:
                log.error(stderr)
                raise Exception("some thing wrong with add_backend")
            lbctl.reload_haproxy()
            ctlplvmctl.exec(join_cmd)
