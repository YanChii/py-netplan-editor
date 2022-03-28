#!/usr/bin/env python3
#
# Janci 2.2.2022
#

import yaml
import json
import re
import os
import sys
import copy
import dpath.util
import logging


def yaml_str_representer(dumper, data):
    if type(data) == str:
        if data.isdigit():
            # if data is number, represent it as number to avoid quotes around value
            # (netplan parser doesn't actually care, it interprets everything as string...
            # but we don't want to change variable formatting in the yaml output)
            return dumper.represent_scalar('tag:yaml.org,2002:int', data, style=None)

        elif re.match('^true$|^false$', data, re.IGNORECASE):
            # avoid quoting bool
            return dumper.represent_scalar('tag:yaml.org,2002:bool', data, style=None)

    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style=None)


class NetplanEditorException(Exception):
    pass


class NetplanEditor():
    netplan: dict       # main conf
    netplan_orig: dict  # for tracking changes
    netplan_dir: str    # base netplan directory
    logger: logging.RootLogger

    # defaults:
    default_netplan_dir='/etc/netplan'


    def __init__(self, conf_file=None, netplan_dir=None, logger=None):
        """
        Initializes netplan object, reads and parses netplan conf files.
        Args:
        netplan_dir - base directory for netplan files. Default: /etc/netplan
        conf_file   - file to read the conf from and save the conf to.
                      Default: None -> search all files in netplan_dir.
        logger      - logger object. If not provided, a new default one is created.
        """
        self._init_logging(logger)

        self.netplan_dir = netplan_dir if netplan_dir else self.default_netplan_dir

        conf_files = []

        if conf_file:
            # explicit file was specified, skip searching other files
            if not conf_file.startswith('/'):
                conf_file = f'{self.netplan_dir}/{conf_file}'
            conf_files.append(conf_file)

        else:
            # search for all *.yaml files in netplan_dir
            for f in os.listdir(self.netplan_dir):
                # make the full path
                ff = os.path.join(self.netplan_dir, f)
                if os.path.isfile(ff) and (ff.endswith('.yml') or ff.endswith('.yaml')):
                    conf_files.append(ff)

        if not conf_files:
            raise NetplanEditorException(f'No netplan config was found (searched dir: {self.netplan_dir})')

        self.netplan = {}
        for conf in conf_files:
            self.netplan[conf] = self.parse(conf)
            
        self._start_tracking_conf_changes()

        # interpreter to remove quotes from numbers
        yaml.add_representer(str, yaml_str_representer)

    @property
    def log(self) -> logging.RootLogger:
        return self.logger

    def _init_logging(self, logger):
        if logger:
            self.logger = logger
            return

        self.logger = logging.getLogger('netplan-editor')
        logging.basicConfig(level='INFO')

    def _start_tracking_conf_changes(self):
        self.netplan_orig = copy.deepcopy(self.netplan)

    def changed(self, conf):
        return self.netplan[conf] != self.netplan_orig[conf]

    def parse(self, conffile):

        with open(conffile) as file:
            self.log.debug(f'Parsing {conffile}')
            return yaml.load(file, Loader=yaml.FullLoader)

        raise NetplanEditorException(f'Error reading netplan file "{conffile}"')


    def write(self):

        for conf in self.netplan.keys():
            if not self.changed(conf):
                self.log.debug(f'No changes. Not writing netplan file.')
                continue
            with open(conf, "w") as file:
                self.log.info(f'Writing netplan file "{conf}"')
                yaml.dump(self.netplan[conf], file, sort_keys=False, default_style=None, default_flow_style=False)

        # reset conf changed state
        self._start_tracking_conf_changes()

    @property
    def conf(self):
        """
        Retuns raw netplan conf in form of dict.
        """
        return self.netplan

    def search_raw(self, search_string: str) -> list:
        """
        Search raw path in yaml file.
        
        Example:
        search_raw('/network/ethernets/*')
        search_raw('/network/ethernets/*/addresses')
        search_raw('/network/ethernets/*/nameservers/search')
        search_raw('/network/*/*/nameservers/search')

        Return value: iterator to list of tuples (found_path, path_content)
        [
        ('network/ethernets/eth0/addresses', ['10.20.30.40/24'])
        ('network/bridges/admin/addresses', ['10.20.25.40/24'])
        ]

        For more info see
        https://github.com/dpath-maintainers/dpath-python#searching
        """

        result = []
        for netplan_file in self.netplan.keys():
            for x in dpath.util.search(self.netplan[netplan_file], search_string, yielded=True):
                result.append((netplan_file,)+x)

        return result

    def search_params_all_interfaces(self, key_glob: str) -> list:
        """
        Searches the netplan interfaces config in sections [ethernets, bridges, vlans] 
        and returns paths that match key_glob parameter (e.g. addresses, nameservers/addresses, 
        nameservers/search, gateway4, mtu, etc).

        Params:
        key_glob: glob pattern to match keys in all defined interfaces config

        Examples:
        search_params_all_interfaces('addresses') - return all interfaces that have IP address configured
        search_params_all_interfaces('nameservers/search') - return all interfaces that have dns search domains configured

        Return value:
        tuple of filename that contains the match, the key (a path that can be used to edit the value) and the current value under the found key.

        Example return value:
        [
        ('/etc/netplan/30-netplan.yaml', 'network/bridges/admin/addresses', ['10.20.25.40/24'])
        ]
        """
        sections = ['ethernets', 'bridges', 'vlans']

        found_paths = []
        for section in sections:
            for x in self.search_raw(f'/network/{section}/*/{key_glob}'):
                found_paths.append(x)

        return found_paths

    @staticmethod
    def _convert_input_val(new_val):
        """
        Try to find json in the input. It recognizes dicts, lists and plain numbers (as int).
        If unable to parse, regard value as plain string regardless the content.
        """
        try:
            return json.loads(new_val)
        except json.decoder.JSONDecodeError:
            # if json parsing fails, leave the original input unchanged
            return new_val


    def _match_1st_source_file(self, path):
        for conf in self.netplan.keys():
            try:
                dpath.util.get(self.netplan[conf], path)
                return conf
            except KeyError:
                pass

        # no path was found in any file
        return None


    def get_val(self, path):
        for netplan in self.netplan.values():
            try:
                return dpath.util.get(netplan, path)
            except KeyError:
                pass
        # no path was found in any file
        return None

    def set_val(self, path, new_val, in_file=''):
        """
        Conf files with alphabetically higher number have a precedence (they override the earlier ones).

        Params:
        path: full dpath to variable. The variable must already exist.
        new_val: plain value or json
        in_file: force file where to change the value.
        """
        if in_file:
            if not os.path.isfile(in_file):
                raise NetplanEditorException(f'File "{in_file}" was not found"')
            conf = in_file

        else:
            conf = self._match_1st_source_file(path)

        if conf:
            old_val = dpath.util.get(self.netplan[conf], path)
            new_val = self._convert_input_val(new_val)
            self.log.info(f'Changing "{path}" in file "{conf}" from "{old_val}" to "{new_val}" as type "{type(new_val)}"')
            dpath.util.set(self.netplan[conf], path, new_val)
            return True

        return False

    def new_entry(self, new_path, new_val, in_file=''):
        """
        Params:
        new_path: full dpath to new variable. The variable must not exist yet.
        new_val: plain value or json
        in_file: force file where to change the value.
        """

        # parent path to the new variable (so we can write it to the file that contains simmilar items)
        base_path = os.path.dirname(new_path)
        element_name = os.path.basename(new_path)
        existing_entries = self.search_raw(base_path)

        if in_file:
            if not os.path.isfile(in_file):
                raise NetplanEditorException(f'File "{in_file}" was not found"')
            conf_file = in_file

        elif existing_entries:
            for items in existing_entries:
                if element_name in items[2]:
                    # don't allow adding an entry that already exists anywhere in config files
                    raise NetplanEditorException(f'Entry "{new_path}" already exists in file "{items[0]}"')

            # sort matched base_path entries by filename (search_raw() returns sorted by keys, not by filenames) 
            # then pick first match and retrieve the conf filename
            conf_file = sorted(existing_entries, key=lambda tup: tup[0], reverse=True)[0][0]

        else:
            # no match for upper path... add the element to the alphabetically last filename
            conf_file = max(self.netplan.keys())
        
        val = self._convert_input_val(new_val)
        self.log.info(f'Creating "{new_path}" with value "{new_val}" as type "{type(new_val)}" in file "{conf_file}"')
        return dpath.util.new(self.netplan[conf_file], new_path, new_val)

    def del_entry(self, glob, in_file=''):
        """
        Deletes first match of the `glob`.
        Conf files with alphabetically higher number have a precedence (they override the earlier ones).

        Params:
        glob - wildcard match of the dict path !!within one yaml file!!
        in_file: force file where to change the value.
        """
        if in_file:
            if not os.path.isfile(in_file):
                raise NetplanEditorException(f'File "{in_file}" was not found"')
            conf = in_file

        else:
            conf = self._match_1st_source_file(path)

        if conf:
            old_val = dpath.util.get(self.netplan[conf], glob)
            self.log.info(f'Deleting entry "{glob}" from file "{conf}" with value "{old_val}"')
            return dpath.util.delete(self.netplan[conf], glob)

        return False



