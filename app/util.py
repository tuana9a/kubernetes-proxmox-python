import time
import urllib
import random
import string

from datetime import datetime, timedelta, timezone
from kubernetes.client.models import V1Secret as _V1Secret
from proxmoxer import ProxmoxAPI as _ProxmoxAPI

from app.logger import Logger as _Logger

characters = string.ascii_lowercase + string.digits  # includes uppercase letters, lowercase letters, and digits


def find_missing_number(start, end, existed: set):
    i = start
    while i <= end:
        if i not in existed:
            return i
        i = i + 1
    return None


def find_missing(arr: list, existed: set):
    i = 0
    end = len(arr)
    while i < end:
        value = arr[i]
        if value not in existed:
            return value
        i = i + 1
    return None


def gen_characters(length: int):
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string


class ProxmoxUtil:

    @staticmethod
    def extract_ip(ifconfig_n: str):
        """
        Example: "ip=192.168.56.123/24,gw=192.168.56.1"
        """
        parts = ifconfig_n.split(",")
        parts = parts[0].split("=")
        parts = parts[1].split("/")
        ip = parts[0]
        return ip

    @staticmethod
    def encode_sshkeys(sshkeys: str):
        if not sshkeys: return None
        # NOTE: https://github.com/proxmoxer/proxmoxer/issues/153
        return urllib.parse.quote(sshkeys, safe="")

    @staticmethod
    def start_vm(api: _ProxmoxAPI, node: str, vm_id: str):
        return api.nodes(node).qemu(vm_id).status.start.post()

    @staticmethod
    def wait_qemu_guest_agent(api: _ProxmoxAPI,
                              node: str,
                              vm_id: str,
                              log=_Logger.DEBUG,
                              timeout=5 * 60,
                              interval_check=10):
        duration = 0
        while True:
            time.sleep(interval_check)
            duration += interval_check
            if duration > timeout:
                log.debug(node, vm_id, "wait_qemu_guest_agent", "timeout")
                raise TimeoutError()
            try:
                api.nodes(node).qemu(vm_id).agent.ping.post()
                break
            except Exception as err:
                log.debug(node, vm_id, "wait_qemu_guest_agent", err)
        log.debug(node, vm_id, "wait_qemu_guest_agent", "READY")


class KubeUtil:

    @staticmethod
    def gen_token_id():
        return gen_characters(6)

    @staticmethod
    def gen_token_secret():
        return gen_characters(16)

    @staticmethod
    def gen_join_token(ttl_minutes=5):
        token_id = KubeUtil.gen_token_id()
        token_secret = KubeUtil.gen_token_secret()
        token_string_data = {
            "token-id":
            token_id,
            "token-secret":
            token_secret,
            "usage-bootstrap-authentication":
            "true",
            "usage-bootstrap-signing":
            "true",
            "auth-extra-groups":
            "system:bootstrappers:kubeadm:default-node-token",
            "expiration":
            (datetime.now(timezone.utc) +
             timedelta(minutes=ttl_minutes)).isoformat()  # 5 minute from now
        }
        v1_secret = _V1Secret(
            type="bootstrap.kubernetes.io/token",
            metadata={"name": f"bootstrap-token-{token_id}"},
            string_data=token_string_data,
        )
        return token_id, token_secret, v1_secret
