"""Install or update the live position script on one or more Shelly devices.

Usage: python deploy_shelly_script.py SHELLY_IP [SHELLY_IP ...]

Uses the Shelly local RPC API over Wi-Fi. The script is created if missing,
its code replaced, set to start at boot, then (re)started.
"""

import json
import sys
import urllib.request
from pathlib import Path

SCRIPT_NAME = "zigbee-live-position"
SCRIPT_PATH = Path(__file__).parent / "shelly_script" / "live_position.js"
CHUNK_SIZE = 1024


def rpc(host: str, method: str, params: dict | None = None) -> dict:
    body = json.dumps({"id": 1, "method": method, "params": params or {}}).encode()
    req = urllib.request.Request(f"http://{host}/rpc", data=body, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        reply = json.load(resp)
    if "error" in reply:
        raise RuntimeError(f"{host} {method}: {reply['error']}")
    return reply["result"]


def find_or_create_script(host: str) -> int:
    for script in rpc(host, "Script.List")["scripts"]:
        if script["name"] == SCRIPT_NAME:
            return script["id"]
    return rpc(host, "Script.Create", {"name": SCRIPT_NAME})["id"]


def deploy(host: str, code: str) -> None:
    script_id = find_or_create_script(host)
    if rpc(host, "Script.GetStatus", {"id": script_id})["running"]:
        rpc(host, "Script.Stop", {"id": script_id})
    for offset in range(0, len(code), CHUNK_SIZE):
        rpc(
            host,
            "Script.PutCode",
            {"id": script_id, "code": code[offset : offset + CHUNK_SIZE], "append": offset > 0},
        )
    rpc(host, "Script.SetConfig", {"id": script_id, "config": {"enable": True}})
    rpc(host, "Script.Start", {"id": script_id})
    status = rpc(host, "Script.GetStatus", {"id": script_id})
    print(f"{host}: script {script_id} running={status['running']} errors={status.get('errors', [])}")


def main() -> None:
    hosts = sys.argv[1:]
    if not hosts:
        sys.exit(__doc__)
    code = SCRIPT_PATH.read_text(encoding="utf-8")
    for host in hosts:
        deploy(host, code)


if __name__ == "__main__":
    main()
