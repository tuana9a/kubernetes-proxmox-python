import os
import ipaddress

from app.controller.node import NodeController
from app.logger import Logger
from app import util


class LbController:

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
        vm_network_gw = str(network_interface.ip) or r["address"]
        vm_network = network_interface.network
        vm_ip_pool = []
        for ip in vm_network.hosts():
            vm_ip_pool.append(str(ip))
        preserved_ips = preserved_ips
        preserved_ips.append(vm_network_gw)
        log.debug("preserved_ips", preserved_ips)

        vm_list = nodectl.list_vm()

        log.debug("len(vm_list)", len(vm_list))
        exist_vm_id = set()
        exist_vm_ip = set()
        exist_vm_ip.update(preserved_ips)
        for vm in vm_list:
            vm_id = vm["vmid"]
            exist_vm_id.add(vm_id)
            vm_config = nodectl.vm(vm_id).current_config()
            ifconfig0 = vm_config.get("ipconfig0", None)
            if not ifconfig0: continue
            vm_ip = util.ProxmoxUtil.extract_ip(ifconfig0)
            if vm_ip: exist_vm_ip.add(vm_ip)
        log.debug("exist_vm_id", exist_vm_id)
        log.debug("exist_vm_ip", exist_vm_ip)

        vm_id_new = util.find_missing_number(vm_id_range[0], vm_id_range[1],
                                             exist_vm_id)
        vm_name_new = f"{vm_name_prefix}{vm_id_new}"

        if not vm_id_new:
            log.error("Error: can't find new id")
            exit(1)
        log.debug("newid", vm_id_new)

        vm_ip_new = util.find_missing(vm_ip_pool, exist_vm_ip)
        if not vm_ip_new:
            log.error("Error: can't find new ip")
            exit(1)
        log.debug("new_ip", vm_ip_new)

        nodectl.clone(lb_template_id, vm_id_new)

        vmctl = nodectl.vm(vm_id_new)

        vmctl.update_config(
            name=vm_name_new,
            ciuser=vm_username,
            cipassword=vm_password,
            sshkeys=util.ProxmoxUtil.encode_sshkeys(vm_ssh_keys),
            agent="enabled=1,fstrim_cloned_disks=1",
            net0=f"virtio,bridge={vm_network_name}",
            ipconfig0=f"ip={vm_ip_new}/24,gw={vm_network_gw}",
        )

        vmctl.resize_disk(disk="scsi0", size="+20G")
        vmctl.startup()
        vmctl.wait_for_guest_agent(timeout=5 * 60)

        if not haproxy_cfg:
            log.info("haproxy_cfg is not set, skipping copy haproxy config")
            exit(0)

        if not os.path.exists(haproxy_cfg):
            raise FileNotFoundError(haproxy_cfg)

        with open(haproxy_cfg, "r", encoding="utf8") as f:
            vmctl.write_file(haproxy_cfg_path, f.read())
