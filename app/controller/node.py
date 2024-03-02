from proxmoxer import ProxmoxAPI
from app.logger import Logger
from app.controller.vm import VmController


class NodeController:

    def __init__(self, api: ProxmoxAPI, node: str, log=Logger.DEBUG) -> None:
        self.api = api
        self.node = node
        self.log = log
        pass

    @staticmethod
    def create_proxmox_client(proxmox_host,
                              proxmox_user,
                              proxmox_password=None,
                              proxmox_token_name=None,
                              proxmox_token_value=None,
                              proxmox_verify_ssl=False,
                              log=Logger.DEBUG,
                              **kwargs):
        # TODO: verify later with ca cert
        if proxmox_token_name:
            log.debug("using proxmox_token_name")
            return ProxmoxAPI(proxmox_host,
                              user=proxmox_user,
                              token_name=proxmox_token_name,
                              token_value=proxmox_token_value,
                              verify_ssl=proxmox_verify_ssl)
        log.debug("using proxmox_password")
        return ProxmoxAPI(
            proxmox_host,
            user=proxmox_user,
            password=proxmox_password,
            verify_ssl=False,
        )

    def vm(self, vm_id):
        return VmController(self.api, self.node, vm_id, log=self.log)

    def clone(self, old_id, new_id):
        api = self.api
        node = self.node
        log = self.log
        r = api.nodes(node).qemu(old_id).clone.post(newid=new_id)
        log.debug(node, "clone", old_id, new_id)
        return r

    def list_vm(self):
        api = self.api
        node = self.node
        log = self.log
        r = api.nodes(node).qemu.get()
        vm_list = r
        log.debug(node, "list_vm", vm_list)
        return vm_list

    def describe_network(self, network: str):
        api = self.api
        node = self.node
        log = self.log
        r = api.nodes(node).network(network).get()
        log.debug(node, "describe_network", r)
        return r
