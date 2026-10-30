// Live cover position over Zigbee (Shelly 2PM Gen4, Zigbee firmware).
//
// The Zigbee firmware only updates its Window Covering position when the
// cover stops. While the motor runs, this script reads the live position and
// sends it to the coordinator as a custom Window Covering command (0xF0,
// payload: position 0-100, 100 = open). The ZHA quirk
// zha_quirks/shelly_2pm_live_position.py turns it into a position update.

let CONFIG = {
  coverId: 0,
  intervalMs: 1000, // how often to sample the position while moving
  minStep: 1, // only send when the position changed by at least this much
  coordinatorAddr: 0, // coordinator network address is always 0x0000
  coordinatorEp: 1,
  windowCoveringCluster: 0x0102,
  livePositionCmd: 0xf0,
  timeoutMs: 800, // ZHA sends no reply; don't keep calls pending
};

let HEX = "0123456789abcdef";
let timer = null;
let lastSent = -1;

function toHexByte(n) {
  return HEX[(n >> 4) & 15] + HEX[n & 15];
}

function sendPosition(pos) {
  lastSent = pos;
  Shelly.call("Zigbee.SendCommand", {
    dst_addr: CONFIG.coordinatorAddr,
    dst_ep: CONFIG.coordinatorEp,
    cluster: CONFIG.windowCoveringCluster,
    cmd: CONFIG.livePositionCmd,
    payload: toHexByte(pos),
    timeout_ms: CONFIG.timeoutMs,
  });
}

function isMoving(state) {
  return state === "opening" || state === "closing";
}

function stopTimer() {
  if (timer !== null) {
    Timer.clear(timer);
    timer = null;
  }
}

function tick() {
  let st = Shelly.getComponentStatus("cover", CONFIG.coverId);
  if (!st || !isMoving(st.state)) {
    stopTimer();
    return;
  }
  if (typeof st.current_pos !== "number") return; // not calibrated
  let pos = Math.round(st.current_pos);
  if (Math.abs(pos - lastSent) >= CONFIG.minStep) sendPosition(pos);
}

function startTimer() {
  if (timer !== null) return;
  lastSent = -1;
  timer = Timer.set(CONFIG.intervalMs, true, tick);
}

Shelly.addStatusHandler(function (ev) {
  if (ev.component !== "cover:" + JSON.stringify(CONFIG.coverId)) return;
  if (ev.delta && isMoving(ev.delta.state)) startTimer();
});

// Covers a script restart in the middle of a movement.
let initial = Shelly.getComponentStatus("cover", CONFIG.coverId);
if (initial && isMoving(initial.state)) startTimer();
