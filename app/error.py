class CanNotGetNewVmId(Exception):

    def __init__(self, id_range=[], exist_ids=[]) -> None:
        super().__init__("Can not get new vm id")


class CanNotGetNewVmIp(Exception):

    def __init__(self, ip_pool=[], exist_ips=[]) -> None:
        super().__init__("Can not get new vm ip")


class VmNotFoundError(Exception):

    def __init__(self, vm_id: int) -> None:
        super().__init__(f"vm {vm_id} is not found")


class FailedToCreateJoinCmd(Exception):

    def __init__(self, *args: object) -> None:
        super().__init__(*args)
