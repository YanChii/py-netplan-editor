#!/usr/bin/env python3
#
# Janci 2.2.2022
#

import yaml
import os
import sys
import copy
import dpath.util
import logging


class NetplanEditorException(Exception):
    pass


class NetplanEditor():
    netplan: dict       # main conf
    netplan_orig: dict  # for tracking changes
    srcfile: str        # where was the main conf read from
    confname: str       # where will be the main conf saved
    netplan_dir: str    # base netplan directory
    logger: logging.RootLogger

    # defaults:
    default_netplan_dir='/etc/netplan'
    default_target_confname='10-netplan.yml'


    def __init__(self, target_confname=None, netplan_dir=None, convert_from_files=[], logger=None):
        """
        Initializes netplan object, reads and parses netplan conf files.
        Args:
        target_confname - file to read the conf from and save the conf to. If it doesn't
                          exist, convert_from_files argument is examined for netplan source.
                          It can be relative or absolute path.
                          Default: 10-netplan.yml
        netplan_dir - base directory for netplan files. Default: /etc/netplan
        convert_from_files - list of filenames to search for when target_confname is not present.
                             First existing file is read as config and no further files are checked.
                             During Netplan.write() the source file is deleted and replaced by
                             target_confname.
        logger - logger object. If not provided, a new default one is created.
        """
        self._init_logging(logger)

        self.confname = target_confname if target_confname else self.default_target_confname
        self.netplan_dir = netplan_dir if netplan_dir else self.default_netplan_dir

        if not self.confname.startswith('/'):
            self.confname = f'{self.netplan_dir}/{self.confname}'
            
        self.srcfile = self.get_netplan_srcfile(convert_from_files)
        self.parse()

    @property
    def log(self) -> logging.RootLogger:
        return self.logger

    def _init_logging(self, logger):
        if logger:
            self.logger = logger
            return

        self.logger = logging.getLogger('netplan-editor')
        logging.basicConfig(level='INFO')

    def get_netplan_srcfile(self, also_search_files=[]):
        srcfiles = [self.confname]
        for f in also_search_files:
            if not f.startswith('/'):
                f = f'{self.netplan_dir}/{f}'
            srcfiles.append(f)

        for srcfile in srcfiles:
            if os.path.isfile(srcfile):
                return srcfile

        raise NetplanException(f'No netplan config was found (searched files: {srcfiles})')

    def _start_tracking_conf_changes(self):
        self.netplan_orig = copy.deepcopy(self.netplan)

    def changed(self):
        return self.netplan != self.netplan_orig

    def parse(self):
        self.log.info(f'Parsing {self.srcfile}')

        with open(self.srcfile) as file:
            self.netplan = yaml.load(file, Loader=yaml.FullLoader)
            self._start_tracking_conf_changes()
            return

        raise NetplanException('Error reading netplan')


    def write(self, outfile=''):
        if not self.changed():
            self.log.info(f'No changes. Not writing netplan file.')
            return

        if not outfile:
            # default outfile
            outf = self.confname
        elif outfile.startswith('/'):
            # full path, take as given
            outf = outfile
        else:
            # relative path, add netplan_dir
            outf = f'{self.netplan_dir}/{outfile}'

        self.log.info(f'Writing netplan to {outf}')
        with open(outf, "w") as file:
            docs = yaml.dump(self.netplan, file, sort_keys=False)

        # Write was successfull. Do we need to delete source file? (see convert_from_files 
        # argument of init()).
        if self.srcfile != self.confname:
            self.log.info(f'Removing original netplan file "{self.srcfile}"')
            os.remove(self.srcfile)
            # now we have only one source file
            self.srcfile = self.confname

        # reset conf changed state
        self._start_tracking_conf_changes()

    #def search_interface_conf(self, key:str):
    #    """
    #    Searches the netplan interfaces config in sections [ethernets, bridges, vlans] 
    #    and returns path that has KEY present (e.g. addresses, nameservers.addresses, 
    #    nameservers.search, gateway4, mtu, etc)
    #    Params:
    #    key: key to search under interfaces config
    #    Example:
    #    search_interface_conf(addresses) - return all interfaces that have IP address configured
    #    """
    #    sections = ['ethernets', 'bridges', 'vlans']

    #    found_paths = []
    #    for subsection in [x for x in sections if x in self.netplan['network']]:
    #        for interface in self.netplan['network'][subsection]:
    #            if key in self.netplan['network'][subsection][interface]:
    #                found_path = ('network', subsection, interface, key)
    #                #self.log.debug(f"Found section {found_path}")
    #                found_paths.append(found_path)

    #    return found_paths

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
        return dpath.util.search(self.netplan, search_string, yielded=True)

    def search_all_interfaces(self, key_glob: str) -> list:
        """
        Searches the netplan interfaces config in sections [ethernets, bridges, vlans] 
        and returns paths that match key_glob parameter (e.g. addresses, nameservers/addresses, 
        nameservers/search, gateway4, mtu, etc).
        Params:
        key: key to search under interfaces config
        Examples:
        search_interface_conf('addresses') - return all interfaces that have IP address configured
        search_interface_conf('nameservers/search') - return all interfaces that have dns search domains configured
        Return value:
        tuple of path (that can be used to edit the content) and the current content under the found key.
        Example return value:
        [
        ('network/bridges/admin/addresses', ['10.20.25.40/24'])
        ]
        """
        sections = ['ethernets', 'bridges', 'vlans']

        found_paths = []
        for section in sections:
            for x in self.search_raw(f'/network/{section}/*/{key_glob}'):
                found_paths.append(x)

        return found_paths

    def get_val(self, path):
        return dpath.util.values(self.netplan, path)

    def set_val(self, path, new_val):
        self.log.info(f'Setting "{path}" to "{new_val}"')
        return dpath.util.set(self.netplan, path, new_val)

    def new_entry(self, new_path, val):
        self.log.info(f'Creating "{new_path}" with value "{val}"')
        return dpath.util.new(self.netplan, path, new_val)

    def del_entry(self, glob):
        self.log.info(f'Deleting entry "{glob}"')
        return dpath.util.delete(self.netplan, glob)



