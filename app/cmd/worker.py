import os
import urllib3

from app.cmd.core import Cmd
from app.config import load_config
from app.logger import Logger
from app.controller.node import NodeController
from app.controller.worker import WorkerController


class WorkerCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("worker",
                         childs=[CreateWorkerCmd(),
                                 DeleteWorkerCmd()],
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

        workerctl = WorkerController(nodectl, log=log)
        workerctl.create_worker(**cfg)


class DeleteWorkerCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("delete", aliases=["remove", "rm"])

    def _setup(self):
        self.parser.add_argument("-i", "--vm-id", type=int, required=False)

    def _run(self):
        urllib3.disable_warnings()
        log = Logger.from_env()
        args = self.parsed_args
        target_vm_id = args.vm_id or os.getenv("VMID")
        log.debug("target_vm_id", target_vm_id)

        if not target_vm_id:
            raise ValueError("env: VMID is missing")

        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        nodectl = NodeController(NodeController.create_proxmox_client(**cfg),
                                 proxmox_node,
                                 log=log)

        workerctl = WorkerController(nodectl, log=log)
        workerctl.delete_worker(target_vm_id, **cfg)
