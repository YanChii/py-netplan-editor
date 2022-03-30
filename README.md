# Netplan Editor
This is a library for searching and/or updating netplan yaml files.

# Install
```
pip install git+https://github.com/YanChii/py-netplan-editor.git
```
Requirement: `dpath`

# CLI Command

```
srv# update-netplan search_params nameservers/search
FILE                                    PATH                                    VALUE
/etc/netplan/00-installer-config.yaml   network/ethernets/ens160/nameservers/search ['example.net', 'example.com']
```
```
srv# update-netplan set_all nameservers/search '["sub.example.com", "example.com"]'
```
```
srv# update-netplan get network/ethernets/ens160/nameservers/search
['sub.example.com', 'example.com']
```
Note: the new value can be plain string value (e.g. `1500` or `True`) or json value (double quotes are required in json string for successful parsing). If the value cannot be parsed, it's used as plain string.

# Example Usage

```
from netplan_editor import NetplanEditor,NetplanEditorException
import logging

logger = logging.getLogger('my-netplan-editor')
logging.basicConfig(level='INFO')

try:
    netplan = NetplanEditor(logger=logger)

    set_search_domains = ['my.example.com', 'example.com']

    for found in netplan.search_params_all_interfaces('nameservers/search'):
        found_path = found[1]
        netplan.set_val(found_path, set_search_domains)

    netplan.write()

except NetplanEditorException as e:
    logger.error(e)
    sys.exit(10)
```

The above example reads all config files from default location (`/etc/netplan`) and searches all interfaces configuration under sections `[ethernets, bridges, vlans]` for `nameservers/search` key. The returned (=found) paths are then overwritten by value of `set_search_domains`. The example code ends by `netplan.write()` which checks if the resulting yaml config differs from the original one (before updating the search domains) and if it differs, it writes all changed files.
