import os
import urllib3

from app.cmd.core import Cmd
from app.config import load_config
from app.logger import Logger
from app.controller.node import NodeController
from app.service.worker import WorkerService


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

        nodectl = NodeController(NodeController.create_proxmox_client(**cfg,
                                                                      log=log),
                                 proxmox_node,
                                 log=log)

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
        log.debug("vm_id", vm_id)

        if not vm_id:
            raise ValueError("vm_id is missing")

        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        nodectl = NodeController(NodeController.create_proxmox_client(**cfg),
                                 proxmox_node,
                                 log=log)

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
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        nodectl = NodeController(NodeController.create_proxmox_client(**cfg),
                                 proxmox_node,
                                 log=log)

        join_cmd = nodectl.ctlplvmctl(
            control_plane_id).kubeadm().create_join_command()
        for id in worker_ids:
            nodectl.wkctl(id).exec(join_cmd)
