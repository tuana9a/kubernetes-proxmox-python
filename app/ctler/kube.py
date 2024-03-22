from typing import List
from app.ctler.vm import VmController
from proxmoxer import ProxmoxAPI
from app.logger import Logger
from app import config
from app.error import *


class _KubeadmExecutor():

    def __init__(self, vmctl: VmController) -> None:
        self.vmctl = vmctl

    def reset(self, cmd=["kubeadm", "reset", "-f"]):
        vmctl = self.vmctl
        return vmctl.exec(cmd)

    def init(self,
             control_plane_endpoint,
             pod_cidr,
             svc_cidr=None,
             timeout=10 * 60):
        vmctl = self.vmctl
        cmd = [
            "kubeadm",
            "init",
            f"--control-plane-endpoint={control_plane_endpoint}",
            f"--pod-network-cidr={pod_cidr}",
        ]
        if svc_cidr:
            cmd.append(f"--service-cidr={svc_cidr}")
        return vmctl.exec(cmd, timeout=timeout)

    def create_join_command(
            self,
            cmd=["kubeadm", "token", "create", "--print-join-command"],
            is_control_plane=False,
            timeout=config.TIMEOUT,
            interval_check=3):
        vmctl = self.vmctl
        log = vmctl.log
        exitcode, stdout, stderr = vmctl.exec(cmd,
                                              timeout=timeout,
                                              interval_check=interval_check)
        if exitcode != 0:
            raise FailedToCreateJoinCmd(stderr)
        join_cmd: List[str] = stdout.split()
        if is_control_plane:
            join_cmd.append("--control-plane")
        log.info("join_cmd", join_cmd)
        return join_cmd


class KubeVmController(VmController):

    def __init__(self,
                 api: ProxmoxAPI,
                 node: str,
                 vm_id: str,
                 log=Logger.DEBUG) -> None:
        super().__init__(api, node, vm_id, log)
        self._kubeadm = _KubeadmExecutor(self)

    def kubeadm(self):
        return self._kubeadm
