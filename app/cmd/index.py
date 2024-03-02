import sys

from app.cmd.core import Cmd
from app.cmd.ctlpl import ControlPlaneCmd
from app.cmd.kube import KubeCmd
from app.cmd.lb import LbCmd
from app.cmd.help import TreeCmd
from app.cmd.worker import WorkerCmd


class MainCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("kp",
                         childs=[
                             ControlPlaneCmd(),
                             KubeCmd(),
                             LbCmd(),
                             WorkerCmd(),
                             TreeCmd(parent=self)
                         ])


def main():
    MainCmd().run(sys.argv[1:])


if __name__ == "__main__":
    main()
