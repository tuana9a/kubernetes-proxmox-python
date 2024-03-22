#!/usr/bin/env python3

import sys
import argparse

from typing import List, Mapping


class Cmd:

    def __init__(
        self,
        name: str,
        childs: List = [],
        aliases: List[str] = [],
        parent=None,
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

    def add_child(self, name, child):
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


class MainCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("config_haproxy.py", childs=[BackendCmd()])

    def _setup(self):
        self.parser.add_argument('-c',
                                 '--config',
                                 help='Path to the haproxy configuration file',
                                 default="/etc/haproxy/haproxy.cfg")


class BackendCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("backend",
                         childs=[AddBackendCmd(),
                                 RmBackendCmd()],
                         aliases=["be"])

    def _setup(self):
        self.parser.add_argument('backend_name', help='Backend name')


class AddBackendCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("add")

    def _setup(self):
        self.parser.add_argument('name', help='Server name')
        self.parser.add_argument(
            'endpoint',
            help='Server endpoint',
        )

    def _run(self):
        config_path = self.parent.parent.parsed_args.config
        backend_name = self.parent.parsed_args.backend_name
        server_name = self.parsed_args.name
        server_endpoint = self.parsed_args.endpoint

        print("config_path", config_path)
        print("backend_name", backend_name)
        print("server_name", server_name)
        print("server_endpoint", server_endpoint)

        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        target_server_name = server_name
        target_server_endpoint = server_endpoint
        target_backend_name = backend_name

        lines = content.split("\n")
        line_count = len(lines)
        current_line_number = 0
        tab_size = " " * 2  # two spaces
        is_need_to_save = False

        while current_line_number < line_count:
            line = lines[current_line_number]
            parts = line.split()
            if len(parts) != 2:
                current_line_number += 1
                continue
            if parts[0] != "backend":
                current_line_number += 1
                continue
            if parts[1] != target_backend_name:
                current_line_number += 1
                continue
            print(
                f"found backend: \"{target_backend_name}\" at line {current_line_number}"
            )
            current_line_number += 1
            is_server_existed = False
            while (current_line_number < line_count):
                line: str = lines[current_line_number]
                if not line or line.isspace():
                    current_line_number += 1
                    continue
                if not line.startswith(tab_size):
                    break
                parts = line.split()
                if not len(parts):
                    current_line_number += 1
                    continue
                if parts[0] != "server":
                    current_line_number += 1
                    continue
                server_name = parts[1]
                server_endpoint = parts[2]
                opts = parts[3:]
                print(
                    f"found server at line {current_line_number} server_name: {server_name} server_endpoint: {server_endpoint} opts: {opts}"
                )
                if server_name != target_server_name:
                    current_line_number += 1
                    continue
                is_server_existed = True
                if server_endpoint != target_server_endpoint:
                    parts[2] = target_server_endpoint
                    # begin space is missing when doing the .split()
                    lines[current_line_number] = tab_size + " ".join(parts)
                    is_need_to_save = True
                break
            print("is_server_existed", is_server_existed)
            if not is_server_existed:
                new_line = tab_size + " ".join([
                    "server", target_server_name, target_server_endpoint,
                    "check"
                ])
                lines.insert(current_line_number, new_line)
                is_need_to_save = True
            break

        print("is_need_to_save", is_need_to_save)

        if not is_need_to_save:
            exit(0)

        new_content = "\n".join(lines).strip() + "\n"
        print(new_content)

        with open(config_path, "w") as f:
            f.write(new_content)


class RmBackendCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("delete", aliases=["rm"])

    def _setup(self):
        self.parser.add_argument('name', help='Server name')

    def _run(self):
        config_path = self.parent.parent.parsed_args.config
        backend_name = self.parent.parsed_args.backend_name
        server_name = self.parsed_args.name
        print("config_path", config_path)
        print("backend_name", backend_name)
        print("server_name", server_name)

        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        target_server_name = server_name
        target_backend_name = backend_name

        lines = content.split("\n")
        line_count = len(lines)
        current_line_number = 0
        tab_size = " " * 2  # two spaces
        is_need_to_save = False

        while current_line_number < line_count:
            line = lines[current_line_number]
            parts = line.split()
            if len(parts) != 2:
                current_line_number += 1
                continue
            if parts[0] != "backend":
                current_line_number += 1
                continue
            if parts[1] != target_backend_name:
                current_line_number += 1
                continue
            print(
                f"found backend: \"{target_backend_name}\" at line {current_line_number}"
            )
            current_line_number += 1
            while (current_line_number < line_count):
                line: str = lines[current_line_number]
                if not line or line.isspace():
                    current_line_number += 1
                    continue
                if not line.startswith(tab_size):
                    break
                parts = line.split()
                if not len(parts):
                    current_line_number += 1
                    continue
                if parts[0] != "server":
                    current_line_number += 1
                    continue
                server_name = parts[1]
                server_endpoint = parts[2]
                opts = parts[3:]
                print(
                    f"found server at line {current_line_number} server_name: {server_name} server_endpoint: {server_endpoint} opts: {opts}"
                )
                if server_name != target_server_name:
                    current_line_number += 1
                    continue
                lines.pop(current_line_number)
                is_need_to_save = True
                break
            break

        print("is_need_to_save", is_need_to_save)

        if not is_need_to_save:
            exit(0)

        new_content = "\n".join(lines).strip() + "\n"
        print(new_content)

        with open(config_path, "w") as f:
            f.write(new_content)


def main():
    MainCmd().run(sys.argv[1:])


if __name__ == "__main__":
    main()
