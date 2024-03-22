from proxmoxer import ProxmoxAPI
from app.logger import Logger
from app.ctler.vm import VmController
from app.ctler.ctlpl import ControlPlaneVmController
from app.ctler.worker import WorkerVmController
from app.ctler.kube import KubeVmController
from app.ctler.lb import LbVmController
from app.error import *
from app import util


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
            log.info("using proxmox_token_name")
            return ProxmoxAPI(proxmox_host,
                              user=proxmox_user,
                              token_name=proxmox_token_name,
                              token_value=proxmox_token_value,
                              verify_ssl=proxmox_verify_ssl)
        log.info("using proxmox_password")
        return ProxmoxAPI(
            proxmox_host,
            user=proxmox_user,
            password=proxmox_password,
            verify_ssl=False,
        )

    def vmctl(self, vm_id):
        return VmController(self.api, self.node, vm_id, log=self.log)

    def ctlplvmctl(self, vm_id):
        return ControlPlaneVmController(self.api,
                                        self.node,
                                        vm_id,
                                        log=self.log)

    def wkctl(self, vm_id):
        return WorkerVmController(self.api, self.node, vm_id, log=self.log)

    def lbctl(self, vm_id):
        return LbVmController(self.api, self.node, vm_id, log=self.log)

    def kubeadmctl(self, vm_id):
        return KubeVmController(self.api, self.node, vm_id, log=self.log)

    def clone(self, old_id, new_id):
        api = self.api
        node = self.node
        log = self.log
        r = api.nodes(node).qemu(old_id).clone.post(newid=new_id)
        log.info(node, "clone", old_id, new_id)
        return r

    def list_vm(self):
        api = self.api
        node = self.node
        log = self.log
        r = api.nodes(node).qemu.get()
        vm_list = r
        log.debug(node, "list_vm", len(vm_list), vm_list)
        return vm_list

    def find_vm(self, vm_id: int):
        api = self.api
        node = self.node
        log = self.log
        r = api.nodes(node).qemu.get()
        vm_list = r
        for x in vm_list:
            id = x["vmid"]
            if str(id) == str(vm_id):
                log.debug("vm", x)
                return x

        raise VmNotFoundError(vm_id)

    def describe_network(self, network: str):
        api = self.api
        node = self.node
        log = self.log
        r = api.nodes(node).network(network).get()
        log.debug(node, "describe_network", r)
        return r

    def new_vm_id(self, id_range=[0, 9999], preserved_ids=[]):
        log = self.log
        exist_ids = set()
        exist_ids.update(preserved_ids)
        vm_list = self.list_vm()
        for vm in vm_list:
            id = vm["vmid"]
            exist_ids.add(id)
        log.debug("exist_ids", exist_ids)
        new_id = util.find_missing_number(id_range[0], id_range[1], exist_ids)
        if not new_id:
            log.error("Can't find new vm id")
            raise CanNotGetNewVmId()
        log.info("new_id", new_id)
        return new_id

    def new_vm_ip(self, ip_pool=[], preserved_ips=[]):
        log = self.log
        exist_ips = set()
        exist_ips.update(preserved_ips)
        vm_list = self.list_vm()
        for vm in vm_list:
            id = vm["vmid"]
            config = self.vmctl(id).current_config()
            ifconfig0 = config.get("ipconfig0", None)
            if not ifconfig0: continue
            ip = util.ProxmoxUtil.extract_ip(ifconfig0)
            if ip: exist_ips.add(ip)
        log.debug("exist_ips", exist_ips)
        new_ip = util.find_missing(ip_pool, exist_ips)
        if not new_ip:
            log.error("Can't find new ip")
            raise CanNotGetNewVmIp()
        log.info("new_ip", new_ip)
        return new_ip
