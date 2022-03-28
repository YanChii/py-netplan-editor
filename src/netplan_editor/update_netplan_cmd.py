
import sys
import re
from argparse import ArgumentParser
import logging

from . import netplan_editor

def print_help(exit_val=0, extra_msg=''):
    if extra_msg:
        print(f'{extra_msg}\n')

    print(f'''\
Usage:
{sys.argv[0]} search_params [target_match]
{sys.argv[0]} get           <target_path>
{sys.argv[0]} set           <target_path>  <target_value>
{sys.argv[0]} set_all       <target_match> <target_value>
{sys.argv[0]} add           <target_path>  <target_value>
{sys.argv[0]} delete        <target_path>

Examples:
{sys.argv[0]} search_params nameservers/search
{sys.argv[0]} get network/ethernets/eno1/mtu
{sys.argv[0]} set network/ethernets/eno1/mtu 1400
{sys.argv[0]} set network/ethernets/eno1/nameservers/search '["sub.example.com", "example.com"]'
{sys.argv[0]} set_all nameservers/search '["sub.example.com", "example.com"]'

Remarks:
- target_value can be either plain value or json
- set* requires the path that already exists
''')
    sys.exit(exit_val)


def update_netplan():

    loglevel = 'WARN'   # default

    for arg in sys.argv[1:]:
        if arg == '-h':
            print_help(0)
        elif arg == '-v':
            loglevel='INFO'
        elif arg == '-vv':
            loglevel='DEBUG'
        elif not re.match('^-', arg):
            # stop processing switches
            break

        del sys.argv[1]

    logger = logging.getLogger('netplan_editor')
    logging.basicConfig(level=loglevel)

    if len(sys.argv) < 2:
        print_help(1)

    cmd = sys.argv[1]

    netplan = netplan_editor.NetplanEditor(logger=logger)

    if cmd == 'search_params':
        try:
            target_match = sys.argv[2]
        except IndexError:
            # default value
            target_match = '*'

        def tabularize(row:tuple):
            entry_width = 39
            out = ""
            for x in row:
                out += str(x).ljust(entry_width) + " "
            return out

        print(tabularize(('FILE', 'PATH', 'VALUE')))
        for item in netplan.search_params_all_interfaces(target_match):
            print(tabularize(item))


    elif cmd == 'get':
        try:
            target_path = sys.argv[2]
        except IndexError:
            print_help(1)

        val = netplan.get_val(target_path)
        logger.debug(f'Type of the entry in get() is "{type(val)}"')
        if val is None:
            print(f"Error: entry not found: {target_path}", file=sys.stderr)
            sys.exit(9)

        print(val)


    elif cmd == 'delete':
        try:
            target_path = sys.argv[2]
        except IndexError:
            print_help(1)

        val = netplan.del_entry(target_path)
        netplan.write()


    elif cmd == 'set':
        try:
            target_path = sys.argv[2]
            target_val = sys.argv[3]
        except IndexError:
            print_help(1)

        netplan.set_val(target_path, target_val)
        netplan.write()


    elif cmd == 'set_all':
        try:
            target_match = sys.argv[2]
            target_val = sys.argv[3]
        except IndexError:
            print_help(1)

        for target_path in netplan.search_params_all_interfaces(target_match):
            netplan.set_val(target_path[1], target_val, in_file=target_path[0])

        netplan.write()


    elif cmd == 'add':
        try:
            target_path = sys.argv[2]
            target_val = sys.argv[3]
        except IndexError:
            print_help(1)

        netplan.new_entry(target_path, target_val)
        netplan.write()

    else:
        print_help(1, f'Unknown command: {cmd}')


    return 0
