
import sys
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
''')
    sys.exit(exit_val)


def update_netplan():

    logger = logging.getLogger('netplan_editor')
    #logging.basicConfig(level='WARN')
    logging.basicConfig(level='INFO')

    if len(sys.argv) < 2:
        print_help(1)

    cmd = sys.argv[1]

    #src_file = f"{netplan_editor.NetplanEditor.default_netplan_dir}/{netplan_editor.NetplanEditor.default_target_confname}"
    src_file = "/root/mynetplan/10-tachyum.yml"

    netplan = netplan_editor.NetplanEditor(target_confname=src_file, logger=logger)

    if cmd == 'search_params':
        try:
            target_match = sys.argv[2]
        except IndexError:
            # default value
            target_match = '*'

        print("%s\t\t\t\t%s" % ('PATH', 'VALUE'))
        for item in netplan.search_params_all_interfaces(target_match):
            print("%s\t%s" % (item[0], item[1]))


    elif cmd == 'get':
        try:
            target_path = sys.argv[2]
        except IndexError:
            print_help(1)

        val = netplan.get_val(target_path)
        print(val, str(type(val)))


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
            netplan.set_val(target_path[0], target_val)

        netplan.write()


    else:
        print_help(1, f'Unknown command: {cmd}')


    return 0