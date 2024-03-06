import os
import ipaddress

from app.controller.node import NodeController
from app.logger import Logger
from app import util


class LbService:

    def __init__(self, nodectl: NodeController, log=Logger.DEBUG) -> None:
        self.nodectl = nodectl
        self.log = log
        pass

    def create_lb(self,
                  vm_network_name,
                  lb_template_id,
                  preserved_ips=[],
                  vm_id_range=[0, 9999],
                  vm_name_prefix="i-",
                  vm_username="u",
                  vm_password="1",
                  vm_ssh_keys=None,
                  haproxy_cfg=None,
                  haproxy_cfg_path="/etc/haproxy/haproxy.cfg",
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
        nodectl.clone(lb_template_id, new_vm_id)

        vmctl = nodectl.vmctl(new_vm_id)
        vmctl.update_config(
            name=new_vm_name,
            ciuser=vm_username,
            cipassword=vm_password,
            sshkeys=util.ProxmoxUtil.encode_sshkeys(vm_ssh_keys),
            agent="enabled=1,fstrim_cloned_disks=1",
            net0=f"virtio,bridge={vm_network_name}",
            ipconfig0=f"ip={new_vm_ip}/24,gw={network_gw_ip}",
        )

        vmctl.resize_disk(disk="scsi0", size="+20G")
        vmctl.startup()
        vmctl.wait_for_guest_agent()

        if not haproxy_cfg:
            msg = "haproxy_cfg is not set, skipping copy haproxy config"
            log.info(msg)
            raise Exception(msg)

        if not os.path.exists(haproxy_cfg):
            raise FileNotFoundError(haproxy_cfg)

        with open(haproxy_cfg, "r", encoding="utf8") as f:
            vmctl.write_file(haproxy_cfg_path, f.read())
        return new_vm_id
