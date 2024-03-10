import sys

from app.cmd.core import Cmd
from app.cmd.ctlpl import ControlPlaneCmd
from app.cmd.lb import LbCmd
from app.cmd.help import TreeCmd
from app.cmd.worker import WorkerCmd
from app.cmd.vm import VmCmd
from app.cmd.kubeadm import KubeadmCmd


class MainCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("kp",
                         childs=[
                             ControlPlaneCmd(),
                             LbCmd(),
                             WorkerCmd(),
                             VmCmd(),
                             KubeadmCmd(),
                             TreeCmd(parent=self)
                         ])


def main():
    MainCmd().run(sys.argv[1:])


if __name__ == "__main__":
    main()
