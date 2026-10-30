"""Live cover position for the Shelly 2PM Gen4 on ZHA.

The Shelly Zigbee firmware only updates CurrentPositionLiftPercentage when the
cover stops. A Shelly script (shelly_script/live_position.js) sends the live
position to the coordinator while the motor runs, as a custom Window Covering
command (0xF0, payload: uint8 position, 0 = closed, 100 = open). This quirk
turns that command into a regular attribute update, so the ZHA cover entity
shows the position live and infers opening/closing on its own.

It replaces the built-in zhaquirks.shelly.wifi quirk for the 2PM only, so it
keeps the same device class and Wi-Fi setup cluster.
"""

from __future__ import annotations

from typing import Any, Final

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.foundation import ZCLCommandDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.shelly.wifi import (
    SHELLY_WIFI_SETUP_ENDPOINT_ID,
    ShellyCustomProfileDevice,
    ShellyWiFiSetupCluster,
)

LIVE_POSITION_COMMAND_ID: Final = 0xF0
COVER_ENDPOINT_ID: Final = 1
LIFT_PERCENTAGE_ID: Final = (
    WindowCovering.AttributeDefs.current_position_lift_percentage.id
)


class ShellyLivePositionWindowCovering(CustomCluster, WindowCovering):
    """Window Covering cluster that accepts live position pushes from a script."""

    class ServerCommandDefs(WindowCovering.ServerCommandDefs):
        """Add the script's live position command."""

        live_position: Final = ZCLCommandDef(
            id=LIVE_POSITION_COMMAND_ID,
            schema={"position": t.uint8_t},
            is_manufacturer_specific=False,
        )

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Store a live position pushed by the Shelly script."""
        if hdr.command_id != LIVE_POSITION_COMMAND_ID:
            super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)
            return

        position = min(int(args.position), 100)
        # ZCL lift percentage is inverted: 0 = fully open, 100 = fully closed.
        self._update_attribute(LIFT_PERCENTAGE_ID, 100 - position)

    def handle_cluster_general_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Mark the cover as stopped when the firmware reports its position."""
        super().handle_cluster_general_request(hdr, args, dst_addressing=dst_addressing)
        if hdr.command_id != foundation.GeneralCommand.Report_Attributes:
            return
        if not any(r.attrid == LIFT_PERCENTAGE_ID for r in args.attribute_reports):
            return
        # The firmware only reports the position once the cover has stopped,
        # often a few % past the last live push. ZHA reads that jump as a
        # movement; repeating the value makes it see a still cover.
        self._update_attribute(LIFT_PERCENTAGE_ID, self.get(LIFT_PERCENTAGE_ID))


(
    QuirkBuilder("Shelly", "2PM")
    .device_class(ShellyCustomProfileDevice)
    .replaces(ShellyWiFiSetupCluster, endpoint_id=SHELLY_WIFI_SETUP_ENDPOINT_ID)
    .replaces(ShellyLivePositionWindowCovering, endpoint_id=COVER_ENDPOINT_ID)
    .add_to_registry()
)
