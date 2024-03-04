import os
import ipaddress

from app.controller.node import NodeController
from app.logger import Logger
from app import util
from app.error import *


class ControlPlaneController:

    def __init__(self, nodectl: NodeController, log=Logger.DEBUG) -> None:
        self.nodectl = nodectl
        self.log = log
        pass

    def copy_kube_certs(self,
                        source_id,
                        dest_id,
                        certs=[
                            "/etc/kubernetes/pki/ca.crt",
                            "/etc/kubernetes/pki/ca.key",
                            "/etc/kubernetes/pki/sa.key",
                            "/etc/kubernetes/pki/sa.pub",
                            "/etc/kubernetes/pki/front-proxy-ca.crt",
                            "/etc/kubernetes/pki/front-proxy-ca.key",
                            "/etc/kubernetes/pki/etcd/ca.crt",
                            "/etc/kubernetes/pki/etcd/ca.key",
                        ]):
        # https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/high-availability/#manual-certs
        nodectl = self.nodectl
        log = self.log
        sourcectl = nodectl.vm(source_id)
        destctl = nodectl.vm(dest_id)

        for cert in certs:
            r = sourcectl.read_file(cert)
            content = r["content"]
            # TODO: check truncated content https://pve.proxmox.com/pve-docs/api-viewer/index.html#/nodes/{node}/qemu/{vmid}/agent/file-read
            r = destctl.write_file(cert, content)

    def create_control_plane(self,
                             vm_network_name,
                             control_plane_template_id,
                             pod_cidr,
                             preserved_ips=[],
                             vm_id_range=[0, 9999],
                             vm_name_prefix="i-",
                             vm_username="u",
                             vm_password="1",
                             vm_ssh_keys=None,
                             apiserver_endpoint=None,
                             cni_manifest_file=None,
                             control_plane_vm_ids=None,
                             load_balancer_vm_id=None,
                             **kwargs):
        nodectl = self.nodectl
        log = self.log

        is_multiple_control_planes = False
        if load_balancer_vm_id:
            is_multiple_control_planes = True

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

        nodectl.clone(control_plane_template_id, new_vm_id)

        vmctl = nodectl.vm(new_vm_id)
        vmctl.update_config(
            name=new_vm_name,
            ciuser=vm_username,
            cipassword=vm_password,
            agent="enabled=1,fstrim_cloned_disks=1",
            net0=f"virtio,bridge={vm_network_name}",
            ipconfig0=f"ip={new_vm_ip}/24,gw={network_gw_ip}",
            sshkeys=util.ProxmoxUtil.encode_sshkeys(vm_ssh_keys),
        )

        vmctl.resize_disk(disk="scsi0", size="+20G")
        vmctl.startup()
        vmctl.wait_for_guest_agent(timeout=5 * 60)

        # SECTION: standalone control plane
        if not is_multiple_control_planes:
            cmd = [
                "kubeadm", "init", f"--pod-network-cidr={pod_cidr}",
                f"--control-plane-endpoint={new_vm_ip}"
            ]
            exitcode, stdout, _ = vmctl.exec(cmd, timeout=10 * 60)

            if not cni_manifest_file:
                log.debug("skip apply cni step")
                return new_vm_id

            cni_filepath = "/root/cni.yaml"
            kubeconfig_filepath = "/etc/kubernetes/admin.conf"
            with open(cni_manifest_file, "r", encoding="utf-8") as f:
                vmctl.write_file(cni_filepath, f.read())

            cmd = [
                "kubectl", "apply", f"--kubeconfig={kubeconfig_filepath}",
                "-f", cni_filepath
            ]
            vmctl.exec(cmd)
            return new_vm_id

        # SECTION: stacked control plane
        lbctl = nodectl.vm(load_balancer_vm_id)
        cmd = [
            "/usr/local/bin/add_backend_server_haproxy_cfg.py", "-c",
            "/etc/haproxy/haproxy.cfg", "-n", new_vm_id, "-e",
            f"{new_vm_ip}:6443", "--backend-name", "control-plane"
        ]

        exitcode, stdout, stderr = lbctl.exec(cmd, interval_check=3)
        if exitcode != 0:
            raise Exception(
                "some thing wrong with add_control_plane_haproxy_cmd\n" +
                str(stderr))
        lbctl.exec(["systemctl", "reload", "haproxy"], interval_check=3)

        # No previous control plane, init a new one
        if not control_plane_vm_ids or not len(control_plane_vm_ids):
            control_plane_endpoint = apiserver_endpoint
            if not control_plane_endpoint:
                lb_config = lbctl.current_config()
                lb_ifconfig0 = lb_config.get("ipconfig0", None)
                if not lb_ifconfig0:
                    raise Exception(
                        "can not detect the control_plane_endpoint")
                vm_ip = util.ProxmoxUtil.extract_ip(lb_ifconfig0)
                control_plane_endpoint = vm_ip
            cmd = [
                "kubeadm", "init", f"--pod-network-cidr={pod_cidr}",
                f"--control-plane-endpoint={control_plane_endpoint}"
            ]
            exitcode, stdout, _ = vmctl.exec(cmd, timeout=10 * 60)

            if not cni_manifest_file:
                log.debug("skip ini cni step")
                return new_vm_id

            cni_filepath = "/root/cni.yaml"
            kubeconfig_filepath = "/etc/kubernetes/admin.conf"
            with open(cni_manifest_file, "r", encoding="utf-8") as f:
                vmctl.write_file(cni_filepath, f.read())

            cmd = [
                "kubectl", "apply", f"--kubeconfig={kubeconfig_filepath}",
                "-f", cni_filepath
            ]
            vmctl.exec(cmd)
            return new_vm_id

        # There are previous control plane prepare new control plane
        is_copy_certs_success = False

        # Ensure folders
        vmctl.exec(["mkdir", "-p", "/etc/kubernetes/pki/etcd"],
                   interval_check=3)

        for id in control_plane_vm_ids:
            try:
                self.copy_kube_certs(id, new_vm_id)
                is_copy_certs_success = True
                # if it can complete without error then should break it, otherwise continue to the next control plane
                break
            except Exception as err:
                log.error(err)

        if not is_copy_certs_success:
            raise Exception("can not copy kube certs")

        join_cmd = None
        cmd = ["kubeadm", "token", "create", "--print-join-command"]
        for id in control_plane_vm_ids:
            exitcode, stdout, _ = nodectl.vm(id).exec(cmd)
            if exitcode == 0:
                join_cmd = stdout.split()
                break

        if not join_cmd:
            raise ValueError("can't get join_cmd")

        join_cmd.append("--control-plane")
        log.debug("join_cmd", " ".join(join_cmd))
        vmctl.exec(join_cmd, timeout=20 * 60)
        return new_vm_id

    def delete_control_plane(self,
                             vm_id,
                             load_balancer_vm_id=None,
                             control_plane_vm_ids=None,
                             **kwargs):
        nodectl = self.nodectl
        log = self.log

        vm_list = nodectl.list_vm()

        vm = None
        log.debug("len(vm_list)", len(vm_list))
        for x in vm_list:
            id = x["vmid"]
            if str(id) == str(vm_id):
                vm = x
                break

        if not vm:
            log.error("vmid", vm_id, "not found")
            raise VmNotFoundError(vm_id)

        log.debug("vm", vm)

        vmctl = nodectl.vm(vm_id)
        # kubeadm reset is needed when deploying stacked control plane
        # https://kubernetes.io/docs/reference/setup-tools/kubeadm/kubeadm-reset/#reset-workflow
        # Remove the control plane with etcd will avoid this error
        # https://serverfault.com/questions/1029654/deleting-a-control-node-from-the-cluster-kills-the-apiserver
        cmd = ["kubeadm", "reset", "-f"]

        try:
            vmctl.exec(cmd)
        except Exception as err:
            log.error(err)

        if load_balancer_vm_id:
            target_vm_name = vm["name"]
            kubeconfig_filepath = "/etc/kubernetes/admin.conf"
            if len(control_plane_vm_ids):
                cmd = [
                    "kubectl", f"--kubeconfig={kubeconfig_filepath}", "delete",
                    "node", target_vm_name
                ]
                for id in control_plane_vm_ids:
                    exitcode, _, _ = nodectl.vm(id).exec(cmd, interval_check=3)
                    if exitcode == 0:
                        break

            lbctl = nodectl.vm(load_balancer_vm_id)
            cmd = [
                "/usr/local/bin/delete_backend_server_haproxy_cfg.py", "-c",
                "/etc/haproxy/haproxy.cfg", "-n", vm_id, "--backend-name",
                "control-plane"
            ]
            exitcode, stdout, stderr = lbctl.exec(cmd, interval_check=3)
            if exitcode != 0:
                log.error(str(stderr))
            lbctl.exec(["systemctl", "reload", "haproxy"], interval_check=3)

        vmctl.shutdown()
        vmctl.wait_for_shutdown()
        vmctl.delete()
        return vm_id
