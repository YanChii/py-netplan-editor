# Netplan Editor
This is a library for searching and/or updating netplan yaml files.

# Example Usage

```
import NetplanEditor
import logging

logger = logging.getLogger('my-netplan-editor')
logging.basicConfig(level='INFO')

try:
    netplan = NetplanEditor(target_confname='10-netplan.yml', convert_from_files=['50-cloud-init.yaml'], logger=logger)

    set_search_domains = ['my.example.com', 'example.com']

    for found in netplan.search_all_interfaces('nameservers/search'):
        found_path = found[0]
        netplan.set_val(found_path, set_search_domains)

    netplan.write()

except NetplanEditorException as e:
    logger.error(e)
    sys.exit(10)
```

The above example reads config from `10-netplan.yml` (or if it doesn't exist, it reads config from `50-cloud-init.yaml`). Then it searches all interfaces configuration under sections `[ethernets, bridges, vlans]` for `nameservers/search` settings (regardless of it's values). The returned (=found) paths are then overwritten by value of `set_search_domains`. Example ends by `netplan.write()` which checks if the resulting yaml config differs from the original one (before updating the search domains) and if it differs, it writes it to `10-netplan.yml` (if the config was read from `50-cloud-init.yaml`, this file is deleted after successfull write of `10-netplan.yml`).
