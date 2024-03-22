from app.ctler.vm import VmController
from proxmoxer import ProxmoxAPI
from app.logger import Logger


class LbVmController(VmController):

    def __init__(self,
                 api: ProxmoxAPI,
                 node: str,
                 vm_id: str,
                 log=Logger.DEBUG) -> None:
        super().__init__(api, node, vm_id, log)

    def add_backend(self, backend_name: str, server_name: str,
                    server_endpoint):
        cmd = [
            "/usr/local/bin/config_haproxy.py", "-c",
            "/etc/haproxy/haproxy.cfg", "backend", backend_name, "add",
            server_name, server_endpoint
        ]
        return self.exec(cmd)

    def rm_backend(self, backend_name: str, server_name: str):
        cmd = [
            "/usr/local/bin/config_haproxy.py", "-c",
            "/etc/haproxy/haproxy.cfg", "backend", backend_name, "rm",
            server_name
        ]
        return self.exec(cmd)

    def reload_haproxy(self):
        self.exec(["systemctl", "reload", "haproxy"], interval_check=3)
