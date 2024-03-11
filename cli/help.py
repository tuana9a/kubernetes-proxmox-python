from cli.core import Cmd


class TreeCmd(Cmd):

    def __init__(self, parent: Cmd) -> None:
        super().__init__("tree", parent=parent)

    def _run(self):
        self.parent.tree()
