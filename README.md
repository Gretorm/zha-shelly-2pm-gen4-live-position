# Live cover position for Shelly 2PM Gen4 on ZHA

With the Zigbee firmware, the Shelly 2PM Gen4 (cover profile) only updates its Zigbee position when the motor stops. In Home Assistant the cover jumps from the old position to the final one.

This adds a live position (about one update per second while moving), without changing the firmware:

- `shelly_script/live_position.js` runs on the Shelly. While the cover moves, it sends the current position to the coordinator as a custom Window Covering command (`0xF0`).
- `zha_quirks/shelly_2pm_live_position.py` is a ZHA custom quirk that turns this command into a position update. ZHA then shows opening/closing and the live percentage.

It works for moves started from Home Assistant, the wall switch or the Shelly itself.

Tested with Home Assistant 2026.9, ZHA (EZSP coordinator) and Shelly firmware 2.1.1 (Zigbee).

## Install

1. Copy `zha_quirks/shelly_2pm_live_position.py` to a custom quirks folder in your Home Assistant config, and enable it in `configuration.yaml`:

   ```yaml
   zha:
     custom_quirks_path: /config/custom_zha_quirks/
   ```

   Restart Home Assistant.

2. Install the script on each Shelly (reachable over Wi-Fi):

   ```bash
   python deploy_shelly_script.py SHELLY_IP [SHELLY_IP ...]
   ```

   The script starts at boot. Running the command again updates it.

## Optional: Shelly Wi-Fi over Zigbee

The Shelly does not need Wi-Fi for this. `shelly_zigbee_wifi.py` turns the Wi-Fi of the Shelly devices paired in ZHA on or off, over Zigbee, keeping the stored password (useful for firmware updates or redeploying the script):

```bash
HA_URL=http://homeassistant.local:8123 HA_TOKEN=... python shelly_zigbee_wifi.py list|on|off [IEEE ...]
```

## Settings

In `CONFIG` at the top of `live_position.js`: `intervalMs` (default 1000) and `minStep` (minimum change in % before sending, default 1).

## Limitations

- Unofficial workaround. zigpy accepts the command but logs it as having an unexpected direction; a future release could drop it, and the position would then update at stop only.
- The quirk replaces the built-in Shelly quirk for the `2PM` model (it keeps its Wi-Fi setup cluster).
- Switching the Shelly firmware (Wi-Fi ↔ Zigbee) erases scripts: redeploy.
- ZHA only.

## License

MIT
