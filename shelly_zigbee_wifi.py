"""Turn the Wi-Fi of Shelly Zigbee devices on or off, over Zigbee (through ZHA).

Usage:
    python shelly_zigbee_wifi.py list
    python shelly_zigbee_wifi.py on  [IEEE ...]
    python shelly_zigbee_wifi.py off [IEEE ...]

Without IEEE addresses, acts on every Shelly paired in ZHA. Needs the HA_URL
(e.g. http://homeassistant.local:8123) and HA_TOKEN (long-lived access token)
environment variables. Uses the Shelly Wi-Fi
Setup cluster (0xFC02): reload the current config, set "enable", apply. The
stored Wi-Fi password is kept.
"""

import json
import os
import sys
import time
import urllib.request

HA_URL = os.environ.get("HA_URL", "http://homeassistant.local:8123")
SHELLY_MANUFACTURER_CODE = 0x1490
WIFI_SETUP_ENDPOINT = 239
WIFI_SETUP_CLUSTER = 0xFC02
ATTR_ACTION = 0x0002
ATTR_ENABLE = 0x0004
ACTION_RELOAD = 0
ACTION_APPLY = 1

LIST_TEMPLATE = """
{%- set ns = namespace(out=[]) -%}
{%- for id in integration_entities('zha') | map('device_id') | unique -%}
  {%- if id and device_attr(id, 'manufacturer') == 'Shelly' -%}
    {%- set ieee = (device_attr(id, 'identifiers') | list)[0][1] -%}
    {%- set ns.out = ns.out + [[ieee, device_attr(id, 'name_by_user') or device_attr(id, 'name')]] -%}
  {%- endif -%}
{%- endfor -%}
{{ ns.out | tojson }}
"""


def ha_post(path: str, payload: dict) -> str:
    req = urllib.request.Request(
        f"{HA_URL}/api/{path}",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['HA_TOKEN']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode()


def list_shellies() -> list[tuple[str, str]]:
    return [tuple(d) for d in json.loads(ha_post("template", {"template": LIST_TEMPLATE}))]


def write_attribute(ieee: str, attribute: int, value: int | bool) -> None:
    ha_post(
        "services/zha/set_zigbee_cluster_attribute",
        {
            "ieee": ieee,
            "endpoint_id": WIFI_SETUP_ENDPOINT,
            "cluster_id": WIFI_SETUP_CLUSTER,
            "cluster_type": "in",
            "attribute": attribute,
            "value": value,
            "manufacturer": SHELLY_MANUFACTURER_CODE,
        },
    )
    time.sleep(1)


def set_wifi(ieee: str, enable: bool) -> None:
    write_attribute(ieee, ATTR_ACTION, ACTION_RELOAD)
    write_attribute(ieee, ATTR_ENABLE, enable)
    write_attribute(ieee, ATTR_ACTION, ACTION_APPLY)


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in ("list", "on", "off"):
        sys.exit(__doc__)
    shellies = list_shellies()
    if sys.argv[1] == "list":
        for ieee, name in shellies:
            print(f"{ieee}  {name}")
        return
    targets = sys.argv[2:] or [ieee for ieee, _ in shellies]
    for ieee in targets:
        set_wifi(ieee, sys.argv[1] == "on")
        print(f"{ieee}: Wi-Fi {sys.argv[1]} sent (takes about 10 s)")


if __name__ == "__main__":
    main()
