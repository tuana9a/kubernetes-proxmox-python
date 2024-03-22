import os
import urllib3

from cli.core import Cmd
from app.config import load_config
from app.logger import Logger
from app.ctler.node import NodeController
from app.svc.worker import WorkerService


class WorkerCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("worker",
                         childs=[
                             CreateWorkerCmd(),
                             DeleteWorkerCmd(),
                             JoinWorkerCmd(),
                         ],
                         aliases=["wk"])


class CreateWorkerCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("create")

    def _run(self):
        urllib3.disable_warnings()
        log = Logger.from_env()

        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)

        service = WorkerService(nodectl, log=log)
        service.create_worker(**cfg)


class DeleteWorkerCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("delete", aliases=["remove", "rm"])

    def _setup(self):
        self.parser.add_argument("vmid", type=int)

    def _run(self):
        urllib3.disable_warnings()
        log = Logger.from_env()
        args = self.parsed_args
        vm_id = args.vmid or os.getenv("VMID")
        log.info("vm_id", vm_id)
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        service = WorkerService(nodectl, log=log)
        service.delete_worker(vm_id, **cfg)


class JoinWorkerCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("join")

    def _setup(self):
        self.parser.add_argument("ctlplid", type=int)
        self.parser.add_argument("workerids", nargs="+")

    def _run(self):
        urllib3.disable_warnings()
        log = Logger.from_env()
        args = self.parsed_args
        worker_ids = args.workerids
        control_plane_id = args.ctlplid
        log.info("ctlpl", control_plane_id, "workers", worker_ids)
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        ctlctl = nodectl.ctlplvmctl(control_plane_id)
        join_cmd = ctlctl.kubeadm().create_join_command()
        for id in worker_ids:
            nodectl.wkctl(id).exec(join_cmd)
