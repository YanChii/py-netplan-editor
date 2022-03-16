
import sys

from . import netplan_editor

def update_netplan():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <target_match> <target_value>")
        return 1

    target_match = sys.argv[1]
    target_value = sys.argv[2]
    print(f"Hello world, we have target_match '{target_match}' and target_value '{target_value}'")

