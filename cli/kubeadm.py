import urllib3

from app import util
from cli.core import Cmd
from app.config import load_config
from app.logger import Logger
from app.ctler.node import NodeController


class KubeadmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("kubeadm",
                         childs=[
                             ResetKubeCmd(),
                             InitKubeCmd(),
                         ],
                         aliases=["adm"])


class ResetKubeCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("reset")

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
        ctl = nodectl.kubeadmctl(vm_id)
        ctl.kubeadm().reset()


class InitKubeCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("init")

    def _setup(self):
        self.parser.add_argument("vmid", type=int)

    def _run(self):
        urllib3.disable_warnings()
        log = Logger.from_env()
        args = self.parsed_args
        vm_id = args.vmid
        cfg = load_config(log=log)
        log.info("vm_id", vm_id)
        proxmox_node = cfg["proxmox_node"]
        load_balancer_vm_id = cfg.get("load_balancer_vm_id", None)
        pod_cidr = cfg["pod_cidr"]
        svc_cidr = cfg.get("svc_cidr", None)
        cni_manifest_file = cfg.get("cni_manifest_file", None)
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        is_multiple_control_planes = False

        if load_balancer_vm_id:
            is_multiple_control_planes = True

        ctlplvmctl = nodectl.ctlplvmctl(vm_id)
        current_config = ctlplvmctl.current_config()
        ifconfig0 = current_config.get("ipconfig0", None)
        if not ifconfig0:
            raise Exception("can not detect the vm ip")
        vm_ip = util.ProxmoxUtil.extract_ip(ifconfig0)

        if not is_multiple_control_planes:
            exitcode, _, _ = ctlplvmctl.kubeadm().init(
                control_plane_endpoint=vm_ip,
                pod_cidr=pod_cidr,
                svc_cidr=svc_cidr)

            if not cni_manifest_file:
                log.info("skip apply cni step")
                return

            cni_filepath = "/root/cni.yaml"
            with open(cni_manifest_file, "r", encoding="utf-8") as f:
                ctlplvmctl.write_file(cni_filepath, f.read())
                ctlplvmctl.apply_file(cni_filepath)
            return

        # SECTION: stacked control plane
        lbctl = nodectl.lbctl(load_balancer_vm_id)

        exitcode, _, stderr = lbctl.add_backend("control-plane", vm_id,
                                                f"{vm_ip}:6443")
        if exitcode != 0:
            log.error(stderr)
            raise Exception("some thing wrong with add_backend")
        lbctl.reload_haproxy()

        lb_config = lbctl.current_config()
        lb_ifconfig0 = lb_config.get("ipconfig0", None)
        if not lb_ifconfig0:
            raise Exception("can not detect the control_plane_endpoint")
        vm_ip = util.ProxmoxUtil.extract_ip(lb_ifconfig0)
        control_plane_endpoint = vm_ip
        exitcode, _, _ = ctlplvmctl.kubeadm().init(
            control_plane_endpoint=control_plane_endpoint,
            pod_cidr=pod_cidr,
            svc_cidr=svc_cidr)

        if not cni_manifest_file:
            log.info("skip ini cni step")
            return

        cni_filepath = "/root/cni.yaml"
        with open(cni_manifest_file, "r", encoding="utf-8") as f:
            ctlplvmctl.write_file(cni_filepath, f.read())
            ctlplvmctl.apply_file(cni_filepath)
        return
