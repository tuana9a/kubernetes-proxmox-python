import time

from typing import List
from proxmoxer import ProxmoxAPI
from app.logger import Logger
from app.error import *
from app import config


class VmController:

    def __init__(self,
                 api: ProxmoxAPI,
                 node: str,
                 vm_id: str,
                 log=Logger.DEBUG) -> None:
        self.api = api
        self.node = node
        self.vm_id = vm_id
        self.log = log

    def exec(self, cmd: List[str], timeout=config.TIMEOUT, interval_check=10):
        api = self.api
        node = self.node
        vm_id = self.vm_id
        log = self.log
        duration = 0
        r = api.nodes(node).qemu(vm_id).agent.exec.post(command=cmd)
        log.info(node, vm_id, "exec", cmd, r)
        pid = r["pid"]
        exited = 0
        stdout: str = None
        stderr: str = None
        exitcode: int = None
        while True:
            log.debug(node, vm_id, "exec", pid, "WAIT", duration)
            time.sleep(interval_check)
            duration += interval_check
            if duration > timeout:
                log.error(node, vm_id, "exec", pid, "TIMEOUT")
                raise TimeoutError()
            status = api.nodes(node).qemu(vm_id).agent("exec-status").get(
                pid=pid)
            exited = status["exited"]
            stdout = status.get("out-data", None)
            stderr = status.get("err-data", None)
            exitcode = status.get("exitcode", None)
            if exited: break
        log.info(node, vm_id, "exec", pid, "duration", duration, "exitcode",
                 exitcode)
        if stdout:
            log.info(node, vm_id, "exec", pid, "stdout\n" + str(stdout))
        if stderr:
            log.error(node, vm_id, "exec", pid, "stderr\n" + str(stderr))
        return exitcode, stdout, stderr

    def wait_for_guest_agent(self, timeout=config.TIMEOUT, interval_check=15):
        api = self.api
        node = self.node
        vm_id = self.vm_id
        log = self.log
        duration = 0
        while True:
            time.sleep(interval_check)
            duration += interval_check
            if duration > timeout:
                log.error(node, vm_id, "guestagent", "TIMEOUT")
                raise TimeoutError()
            try:
                api.nodes(node).qemu(vm_id).agent.ping.post()
                break
            except Exception as err:
                log.debug(node, vm_id, "guestagent", "WAIT", duration)
        log.info(node, vm_id, "guest_agent", "UP")

    def wait_for_shutdown(self, timeout=config.TIMEOUT, interval_check=15):
        api = self.api
        node = self.node
        vm_id = self.vm_id
        log = self.log
        status = None
        duration = 0
        while True:
            log.debug(node, vm_id, "shutdown", "WAIT", duration)
            time.sleep(interval_check)
            duration += interval_check
            if duration > timeout:
                log.error(node, vm_id, "shutdown", "TIMEOUT")
                raise TimeoutError()
            try:
                r = api.nodes(node).qemu(vm_id).status.current.get()
                status = r["status"]
                if status == "stopped":
                    break
            except Exception as err:
                log.error("shutdown", err)

    def update_config(self, **kwargs):
        api = self.api
        node = self.node
        vm_id = self.vm_id
        log = self.log
        r = api.nodes(node).qemu(vm_id).config.put(**kwargs)
        log.debug(node, vm_id, "update_config", r)
        return r

    def current_config(self):
        api = self.api
        node = self.node
        vm_id = self.vm_id
        log = self.log
        r = api.nodes(node).qemu(vm_id).config.get()
        log.debug(node, vm_id, "current_config", r)
        return r

    def current_status(self):
        api = self.api
        node = self.node
        vm_id = self.vm_id
        log = self.log
        r = api.nodes(node).qemu(vm_id).status.current.get()
        log.debug(node, vm_id, "current_status", r)
        return r

    def resize_disk(self, disk: str, size: str):
        api = self.api
        node = self.node
        vm_id = self.vm_id
        log = self.log
        r = api.nodes(node).qemu(vm_id).resize.put(disk=disk, size=size)
        log.debug(node, vm_id, "resize_disk", r)
        return r

    def startup(self):
        api = self.api
        node = self.node
        vm_id = self.vm_id
        log = self.log
        r = api.nodes(node).qemu(vm_id).status.start.post()
        log.debug(node, vm_id, "startup", r)
        return r

    def shutdown(self):
        api = self.api
        node = self.node
        vm_id = self.vm_id
        log = self.log
        r = api.nodes(node).qemu(vm_id).status.current.get()
        status = r["status"]
        if status == "stopped":
            return None
        r = api.nodes(node).qemu(vm_id).status.shutdown.post()
        log.debug(node, vm_id, "shutdown", r)
        return r

    def reboot(self):
        api = self.api
        node = self.node
        vm_id = self.vm_id
        log = self.log
        r = api.nodes(node).qemu(vm_id).status.reboot.post()
        log.debug(node, vm_id, "reboot", r)
        return r

    def write_file(self, filepath: str, content: str):
        api = self.api
        node = self.node
        vm_id = self.vm_id
        log = self.log
        r = api.nodes(node).qemu(vm_id).agent("file-write").post(
            content=content, file=filepath)
        log.debug(node, vm_id, "write_file", filepath, "\n", content)
        return r

    def delete(self):
        api = self.api
        node = self.node
        vm_id = self.vm_id
        log = self.log
        r = api.nodes(node).qemu(vm_id).delete()
        log.debug(node, vm_id, "delete", r)
        return r

    def read_file(self, filepath: str):
        api = self.api
        node = self.node
        vm_id = self.vm_id
        log = self.log
        r = api.nodes(node).qemu(vm_id).agent("file-read").get(file=filepath)
        log.debug(node, vm_id, "read_file", r)
        return r
