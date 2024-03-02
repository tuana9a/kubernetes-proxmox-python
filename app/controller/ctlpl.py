import os
import ipaddress

from app.controller.node import NodeController
from app.logger import Logger
from app import util


class ControlPlaneController:

    def __init__(self, nodectl: NodeController, log=Logger.DEBUG) -> None:
        self.nodectl = nodectl
        self.log = log
        pass

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
        vm_network_gw = str(network_interface.ip) or r["address"]
        vm_network = network_interface.network
        vm_ip_pool = []
        for ip in vm_network.hosts():
            vm_ip_pool.append(str(ip))
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
            log.debug("Error: can't find new id")
            exit(1)
        log.debug("new_id", vm_id_new)

        vm_ip_new = util.find_missing(vm_ip_pool, exist_vm_ip)
        if not vm_ip_new:
            log.debug("Error: can't find new ip")
            exit(1)
        log.debug("new_ip", vm_ip_new)

        nodectl.clone(control_plane_template_id, vm_id_new)

        vmctl = nodectl.vm(vm_id_new)

        vmctl.update_config(
            name=vm_name_new,
            ciuser=vm_username,
            cipassword=vm_password,
            agent="enabled=1,fstrim_cloned_disks=1",
            net0=f"virtio,bridge={vm_network_name}",
            ipconfig0=f"ip={vm_ip_new}/24,gw={vm_network_gw}",
            sshkeys=util.ProxmoxUtil.encode_sshkeys(vm_ssh_keys),
        )

        vmctl.resize_disk(disk="scsi0", size="+20G")
        vmctl.startup()
        vmctl.wait_for_guest_agent(timeout=5 * 60)

        if not is_multiple_control_planes:
            # standalone control plane
            cmd = [
                "kubeadm", "init", f"--pod-network-cidr={pod_cidr}",
                f"--control-plane-endpoint={vm_ip_new}"
            ]
            exitcode, stdout, _ = vmctl.exec(cmd, timeout=10 * 60)

            if not cni_manifest_file:
                log.debug("skip ini cni step")
                exit(0)

            cni_filepath = "/root/cni.yaml"
            kubeconfig_filepath = "/etc/kubernetes/admin.conf"
            with open(cni_manifest_file, "r", encoding="utf-8") as f:
                vmctl.write_file(cni_filepath, f.read())

            cmd = [
                "kubectl", "apply", f"--kubeconfig={kubeconfig_filepath}",
                "-f", cni_filepath
            ]
            vmctl.exec(cmd)
            exit(0)

        # SECTION: multiple control plane

        lbctl = nodectl.vm(load_balancer_vm_id)

        cmd = [
            "/usr/local/bin/add_backend_server_haproxy_cfg.py", "-c",
            "/etc/haproxy/haproxy.cfg", "-n", vm_id_new, "-e",
            f"{vm_ip_new}:6443", "--backend-name", "control-plane"
        ]

        exitcode, stdout, stderr = lbctl.exec(cmd, interval_check=3)
        if exitcode != 0:
            raise Exception(
                "some thing wrong with add_control_plane_haproxy_cmd\n" +
                str(stderr))
        lbctl.exec(["systemctl", "reload", "haproxy"], interval_check=3)

        if not control_plane_vm_ids or not len(control_plane_vm_ids):
            # no previous control plane, init a new one
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
                exit(0)

            cni_filepath = "/root/cni.yaml"
            kubeconfig_filepath = "/etc/kubernetes/admin.conf"
            with open(cni_manifest_file, "r", encoding="utf-8") as f:
                vmctl.write_file(cni_filepath, f.read())

            cmd = [
                "kubectl", "apply", f"--kubeconfig={kubeconfig_filepath}",
                "-f", cni_filepath
            ]
            vmctl.exec(cmd)
            exit(0)

        # https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/high-availability/#manual-certs
        kube_certs = [
            "/etc/kubernetes/pki/ca.crt",
            "/etc/kubernetes/pki/ca.key",
            "/etc/kubernetes/pki/sa.key",
            "/etc/kubernetes/pki/sa.pub",
            "/etc/kubernetes/pki/front-proxy-ca.crt",
            "/etc/kubernetes/pki/front-proxy-ca.key",
            "/etc/kubernetes/pki/etcd/ca.crt",
            "/etc/kubernetes/pki/etcd/ca.key",
        ]

        # make sure the folder is exists
        vmctl.exec(["mkdir", "-p", "/etc/kubernetes/pki/etcd"],
                   interval_check=3)

        is_copy_certs_success = False
        for vm_id in control_plane_vm_ids:
            try:
                ctlpl_ctl = nodectl.vm(vm_id)
                for kube_cert in kube_certs:
                    r = ctlpl_ctl.read_file(kube_cert)
                    content = r["content"]
                    # TODO: check truncated content https://pve.proxmox.com/pve-docs/api-viewer/index.html#/nodes/{node}/qemu/{vmid}/agent/file-read
                    r = vmctl.write_file(kube_cert, content)
                is_copy_certs_success = True
                # if it can complete without error then should break it, otherwise continue to the next control plane
                break
            except Exception as err:
                log.error(err)

        if not is_copy_certs_success:
            raise Exception("can not copy kube certs")

        join_cmd = None
        cmd = ["kubeadm", "token", "create", "--print-join-command"]
        for vm_id in control_plane_vm_ids:
            exitcode, stdout, _ = nodectl.vm(vm_id).exec(cmd)
            if exitcode == 0:
                join_cmd = stdout.split()
                break

        if not join_cmd:
            raise ValueError("can't get join_cmd")

        join_cmd.append("--control-plane")
        log.debug("join_cmd", " ".join(join_cmd))
        vmctl.exec(join_cmd, timeout=20 * 60)

    def delete_control_plane(self,
                             target_vm_id,
                             load_balancer_vm_id=None,
                             control_plane_vm_ids=None,
                             **kwargs):
        nodectl = self.nodectl
        log = self.log

        vm_list = nodectl.list_vm()

        target_vm = None
        log.debug("len(vm_list)", len(vm_list))
        for vm in vm_list:
            vmid = vm["vmid"]
            if str(vmid) == str(target_vm_id):
                target_vm = vm
                break

        if not target_vm:
            log.debug("vmid", target_vm_id, "not found")
            exit(1)

        log.debug("vm", target_vm)

        vmctl = nodectl.vm(target_vm_id)
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
            target_vm_name = target_vm["name"]
            kubeconfig_filepath = "/etc/kubernetes/admin.conf"
            if len(control_plane_vm_ids):
                cmd = [
                    "kubectl", f"--kubeconfig={kubeconfig_filepath}", "delete",
                    "node", target_vm_name
                ]
                for vm_id in control_plane_vm_ids:
                    exitcode, _, _ = nodectl.vm(vm_id).exec(cmd,
                                                            interval_check=3)
                    if exitcode == 0:
                        break

            lbctl = nodectl.vm(load_balancer_vm_id)
            cmd = [
                "/usr/local/bin/delete_backend_server_haproxy_cfg.py", "-c",
                "/etc/haproxy/haproxy.cfg", "-n", target_vm_id,
                "--backend-name", "control-plane"
            ]
            exitcode, stdout, stderr = lbctl.exec(cmd, interval_check=3)
            if exitcode != 0:
                log.error(str(stderr))
            lbctl.exec(["systemctl", "reload", "haproxy"], interval_check=3)

        vmctl.shutdown()
        vmctl.wait_for_shutdown()
        vmctl.delete()
