import os
import json

from typing import Optional, List

DEFAULT_PROFILE_NAME = "default"


class Cfg:

    def __init__(self,
                 kubernetes_api_server: str,
                 kubernetes_discovery_token_ca_cert_hash: str,
                 proxmox_host: str,
                 proxmox_user: str,
                 proxmox_password: str,
                 proxmox_node: str,
                 proxmox_template_vm_id: str,
                 proxmox_vm_network: str,
                 proxmox_vm_username: str = "u",
                 proxmox_vm_password: str = "1",
                 proxmox_vm_id_range: List[int] = [0, 9999],
                 proxmox_vm_ssh_keys: Optional[str] = "",
                 proxmox_vm_name_prefix: Optional[str] = "i-",
                 proxmox_network_preserved_ips: Optional[List[str]] = [],
                 **kwargs) -> None:
        self.kubernetes_api_server = kubernetes_api_server
        self.kubernetes_discovery_token_ca_cert_hash = kubernetes_discovery_token_ca_cert_hash
        self.proxmox_host = proxmox_host
        self.proxmox_user = proxmox_user
        self.proxmox_password = proxmox_password
        self.proxmox_node = proxmox_node
        self.proxmox_template_vm_id = proxmox_template_vm_id
        self.proxmox_vm_username = proxmox_vm_username
        self.proxmox_vm_password = proxmox_vm_password
        self.proxmox_vm_id_range = proxmox_vm_id_range
        self.proxmox_vm_id_begin = self.proxmox_vm_id_range[0]
        self.proxmox_vm_id_end = self.proxmox_vm_id_range[1]
        self.proxmox_vm_network = proxmox_vm_network
        self.proxmox_vm_ssh_keys = proxmox_vm_ssh_keys
        self.proxmox_vm_name_prefix = proxmox_vm_name_prefix
        self.proxmox_network_preserved_ips = proxmox_network_preserved_ips
        pass


class Profiles:

    def __init__(self) -> None:
        self.db = {}
        self.selected_key: str = None

    def get(self, key: str) -> Optional[Cfg]:
        return self.db[key]

    def get_selected(self):
        return self.get(self.selected_key)

    def get_selected_key(self):
        return self.selected_key

    def set(self, key: str, c: Cfg):
        self.db[key] = c

    def set_selected_key(self, key: str):
        self.selected_key = key

    def load_from_file(self, config_path: str):
        with open(config_path, "r") as f:
            c = Cfg(**json.loads(f.read()))
            self.set(DEFAULT_PROFILE_NAME, c)
            self.set_selected_key(DEFAULT_PROFILE_NAME)
        return self

    def load_from_env(self, selected_key: str = DEFAULT_PROFILE_NAME):
        # TODO
        pass


profiles = Profiles()
