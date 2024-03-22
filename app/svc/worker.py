import os
import ipaddress

from app.ctler.node import NodeController
from app.logger import Logger
from app.error import *
from app import util


class WorkerService:

    def __init__(self, nodectl: NodeController, log=Logger.DEBUG) -> None:
        self.nodectl = nodectl
        self.log = log
        pass

    def create_worker(self,
                      vm_network_name: str,
                      worker_template_id: int,
                      control_plane_vm_id: int,
                      preserved_ips=[],
                      vm_id_range=[0, 9999],
                      vm_name_prefix="i-",
                      vm_username="u",
                      vm_password="1",
                      vm_ssh_keys=None,
                      **kwargs):
        nodectl = self.nodectl
        log = self.log
        r = nodectl.describe_network(vm_network_name)
        network_interface = ipaddress.IPv4Interface(r["cidr"])
        network_gw_ip = str(network_interface.ip) or r["address"]
        vm_network = network_interface.network
        ip_pool = []
        for ip in vm_network.hosts():
            ip_pool.append(str(ip))
        preserved_ips.append(network_gw_ip)
        log.debug("preserved_ips", preserved_ips)

        new_vm_id = nodectl.new_vm_id(vm_id_range)
        new_vm_ip = nodectl.new_vm_ip(ip_pool, preserved_ips)
        new_vm_name = f"{vm_name_prefix}{new_vm_id}"
        nodectl.clone(worker_template_id, new_vm_id)

        wkctl = nodectl.wkctl(new_vm_id)
        wkctl.update_config(
            name=new_vm_name,
            ciuser=vm_username,
            cipassword=vm_password,
            sshkeys=util.ProxmoxUtil.encode_sshkeys(vm_ssh_keys),
            agent="enabled=1,fstrim_cloned_disks=1",
            net0=f"virtio,bridge={vm_network_name}",
            ipconfig0=f"ip={new_vm_ip}/24,gw={network_gw_ip}",
        )
        wkctl.startup()
        wkctl.wait_for_guest_agent()
        join_cmd = nodectl.ctlplvmctl(
            control_plane_vm_id).kubeadm().create_join_command()
        wkctl.exec(join_cmd)
        return new_vm_id

    def delete_worker(self,
                      vm_id,
                      control_plane_vm_id,
                      drain_first=True,
                      **kwargs):
        nodectl = self.nodectl
        log = self.log
        vm = nodectl.find_vm(vm_id)
        vm_name = vm["name"]

        if control_plane_vm_id:
            ctlplctl = nodectl.ctlplvmctl(control_plane_vm_id)
            try:
                if drain_first:
                    ctlplctl.drain_node(vm_name)
                ctlplctl.delete_node(vm_name)
            except Exception as err:
                log.error(err)

        vmctl = nodectl.vmctl(vm_id)
        vmctl.shutdown()
        vmctl.wait_for_shutdown()
        vmctl.delete()
        return vm_id
