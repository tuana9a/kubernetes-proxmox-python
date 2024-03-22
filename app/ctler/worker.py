from app.ctler.kube import KubeVmController
from proxmoxer import ProxmoxAPI
from app.logger import Logger


class WorkerVmController(KubeVmController):

    def __init__(self,
                 api: ProxmoxAPI,
                 node: str,
                 vm_id: str,
                 log=Logger.DEBUG) -> None:
        super().__init__(api, node, vm_id, log)
