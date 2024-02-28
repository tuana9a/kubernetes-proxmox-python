#!/usr/bin/env python3

import argparse

parser = argparse.ArgumentParser(description='Description of your script')

# Add command line arguments
parser.add_argument('-c',
                    '--config',
                    help='Path to the HAProxy configuration file',
                    default="/etc/haproxy/haproxy.cfg")
parser.add_argument('-n', '--name', help='VM name', required=True)

args = parser.parse_args()

# Access the values of the arguments
config_path = args.config
vm_name = args.name

print("config_path", config_path)
print("vm_name", vm_name)

with open(config_path, "r", encoding="utf-8") as f:
    content = f.read()

target_server_name = vm_name

lines = content.split("\n")
line_count = len(lines)
current_line_number = 0
begin_config_line = "backend control-plane"  # TODO: parameterized it?

is_need_to_save = False
while current_line_number < line_count:
    line = lines[current_line_number]
    if line == begin_config_line:
        print(f"found \"{begin_config_line}\" at line {current_line_number}")
        current_line_number += 1
        current_servers = []
        while (current_line_number < line_count):
            line = lines[current_line_number]
            parts = line.split()
            if not len(parts):
                current_line_number += 1
                continue
            if parts[0] == "server":
                server_name = parts[1]
                server_endpoint = parts[2]
                opts = parts[3:]
                print(
                    f"found server at line {current_line_number}: server_name: {server_name} server_endpoint: {server_endpoint} opts: {opts}"
                )
                if server_name == target_server_name:
                    lines.pop(current_line_number)
                    is_need_to_save = True
                    break
            current_line_number += 1
        break
    current_line_number += 1

print("is_need_to_save", is_need_to_save)

if not is_need_to_save:
    exit(0)

new_content = "\n".join(lines).strip()
print(new_content)

with open(config_path, "w") as f:
    f.write(new_content)
