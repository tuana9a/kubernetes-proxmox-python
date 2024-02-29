#!/usr/bin/env python3

import argparse

parser = argparse.ArgumentParser(description='Description of your script')

# Add command line arguments
parser.add_argument('-c',
                    '--config',
                    help='Path to the haproxy configuration file',
                    default="/etc/haproxy/haproxy.cfg")
parser.add_argument('--backend-name', help='Backend name', required=True)
parser.add_argument('-n', '--name', help='Server name', required=True)
parser.add_argument('-e', '--endpoint', help='Server endpoint', required=True)

args = parser.parse_args()

# Access the values of the arguments
config_path = args.config
server_name = args.name
server_endpoint = args.endpoint
backend_name = args.backend_name

print("config_path", config_path)
print("backend_name", backend_name)
print("server_name", server_name)
print("server_endpoint", server_endpoint)

with open(config_path, "r", encoding="utf-8") as f:
    content = f.read()

target_server_name = server_name
target_server_endpoint = server_endpoint
target_backend_name = backend_name

lines = content.split("\n")
line_count = len(lines)
current_line_number = 0
tab_size = " " * 2  # two spaces
is_need_to_save = False
found_backend_line_number = None

while current_line_number < line_count:
    line = lines[current_line_number]
    parts = line.split()
    if len(parts) != 2:
        current_line_number += 1
        continue
    if parts[0] != "backend":
        current_line_number += 1
        continue
    if parts[1] != backend_name:
        current_line_number += 1
        continue
    print(f"found backend: \"{backend_name}\" at line {current_line_number}")
    found_backend_line_number = current_line_number
    current_line_number += 1
    current_servers = []
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
        new_line = tab_size + " ".join(
            ["server", target_server_name, target_server_endpoint, "check"])
        lines.insert(current_line_number, new_line)
        is_need_to_save = True
    break

print("is_need_to_save", is_need_to_save)

if not is_need_to_save:
    exit(0)

new_content = "\n".join(lines).strip()
print(new_content)

with open(config_path, "w") as f:
    f.write(new_content)
