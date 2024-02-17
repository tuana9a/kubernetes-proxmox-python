#!/usr/bin/env python3

from datetime import datetime, timedelta, timezone
from kubernetes import config, client as klient
from kubernetes.client.models import V1Secret

from app import util

config.load_kube_config()

token_id = util.KubeUtil.gen_token_id()
token_secret = util.KubeUtil.gen_token_secret()
token_string_data = {
    "token-id": token_id,
    "token-secret": token_secret,
    "usage-bootstrap-authentication": "true",
    "usage-bootstrap-signing": "true",
    "auth-extra-groups": "system:bootstrappers:kubeadm:default-node-token",
    "expiration": (datetime.now(timezone.utc) +
                   timedelta(minutes=5)).isoformat()  # 5 minute from now
}
v1_secret = V1Secret(
    type="bootstrap.kubernetes.io/token",
    metadata={"name": f"bootstrap-token-{token_id}"},
    string_data=token_string_data,
)
klient.CoreV1Api().create_namespaced_secret(
    "kube-system",
    v1_secret,
)