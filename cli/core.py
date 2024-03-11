from __future__ import annotations

import argparse

from typing import List, Mapping


class Cmd:

    def __init__(
        self,
        name: str,
        childs: List[Cmd] = [],
        aliases: List[str] = [],
        parent: Cmd = None,
        sub_level=0,
    ) -> None:
        self.name = name
        self.aliases = aliases
        self.has_child = len(childs) > 0
        self.parent = parent
        self.childs = childs
        self.child_map: Mapping[str, Cmd] = {}
        self.parser = argparse.ArgumentParser()
        self.sub_level = sub_level
        self._setup()
        for child in childs:
            self.add_child(child.name, child)
            for child_alias in child.aliases:
                self.add_child(child_alias, child)
        if self.has_child:
            self.parser.add_argument("subcommand",
                                     type=str,
                                     choices=self.child_map.keys())
            self.parser.add_argument("remains",
                                     type=str,
                                     nargs=argparse.REMAINDER)
            self.correct_child_info()

    def add_child(self, name, child: Cmd):
        if self.child_map.get(name, False):
            raise KeyError(f"parent '{self.name}' already has child '{name}'")
        self.child_map[name] = child

    def correct_child_info(self):
        for child in self.childs:
            child.parent = self
            child.sub_level = self.sub_level + 1
            child.parser.prog = " ".join([self.parser.prog, child.name])
            child.correct_child_info()

    def _setup(self):
        """
        implement this
        """
        pass

    def run(self, args: List[str]):
        self.args = args
        self.parsed_args = self.parser.parse_args(args)
        self._run()
        if self.has_child:
            self.run_child()

    def run_child(self):
        child = self.child_map.get(self.parsed_args.subcommand, None)
        if not child:
            raise KeyError(self.parsed_args.subcommand)
        child.run(self.parsed_args.remains)
        pass

    def _run(self):
        """
        implement this
        """
        pass

    def tree(self, current_level=0, recursive=True):
        name = self.name
        if len(self.aliases):
            name += f" ({','.join(self.aliases)})"
        print(
            current_level * "    ",
            name,
        )
        if recursive:
            for child in self.childs:
                child.tree(current_level + 1)
