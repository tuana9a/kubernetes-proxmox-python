from app.ctler.kube import KubeVmController
from proxmoxer import ProxmoxAPI
from app.logger import Logger
from app import config


class ControlPlaneVmController(KubeVmController):

    def __init__(self,
                 api: ProxmoxAPI,
                 node: str,
                 vm_id: str,
                 log=Logger.DEBUG) -> None:
        super().__init__(api, node, vm_id, log)

    def drain_node(self,
                   node_name: str,
                   kubeconfig_filepath="/etc/kubernetes/admin.conf"):
        cmd = [
            "kubectl", f"--kubeconfig={kubeconfig_filepath}", "drain",
            "--ignore-daemonsets", node_name
        ]
        # 30 mins should be enough
        return self.exec(cmd, interval_check=5, timeout=30 * 60)

    def delete_node(self,
                    node_name,
                    kubeconfig_filepath="/etc/kubernetes/admin.conf"):
        cmd = [
            "kubectl", f"--kubeconfig={kubeconfig_filepath}", "delete", "node",
            node_name
        ]
        return self.exec(cmd, interval_check=5)

    def ensure_cert_dirs(self, dirs=["/etc/kubernetes/pki/etcd"]):
        for d in dirs:
            self.exec(["mkdir", "-p", d], interval_check=3)

    def cat_kubeconfig(self, filepath="/etc/kubernetes/admin.conf"):
        cmd = ["cat", filepath]
        return self.exec(cmd)

    def apply_file(self,
                   filepath: str,
                   kubeconfig_filepath="/etc/kubernetes/admin.conf"):
        cmd = [
            "kubectl", "apply", f"--kubeconfig={kubeconfig_filepath}", "-f",
            filepath
        ]
        return self.exec(cmd)
