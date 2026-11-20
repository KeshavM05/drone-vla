"""Set PX4 SITL params to disable preflight checks for all 3 drone instances."""

import struct
import time
from pymavlink import mavutil

PORTS = [14541, 14542, 14543]
PARAMS = {
    "COM_RCL_EXCEPT": 4,
    "NAV_DLL_ACT": 0,
    "CBRK_SUPPLY_CHK": 894281,
    "SYS_HAS_MAG": 0,
}


def int_as_float(val):
    return struct.unpack("f", struct.pack("I", int(val)))[0]


def float_as_int(val):
    return struct.unpack("I", struct.pack("f", val))[0]


def set_params(port, drone_id):
    addr = f"udp:127.0.0.1:{port}"
    print(f"[Drone {drone_id}] Connecting on {addr}...")
    conn = mavutil.mavlink_connection(addr)
    conn.wait_heartbeat(timeout=10)
    print(f"[Drone {drone_id}] Heartbeat (sysid={conn.target_system})")

    for name, value in PARAMS.items():
        conn.mav.param_set_send(
            conn.target_system,
            conn.target_component,
            name.encode("utf-8"),
            int_as_float(value),
            mavutil.mavlink.MAV_PARAM_TYPE_INT32,
        )
        time.sleep(0.2)

    time.sleep(1.0)
    for name, expected in PARAMS.items():
        conn.mav.param_request_read_send(
            conn.target_system,
            conn.target_component,
            name.encode("utf-8"),
            -1,
        )
        msg = conn.recv_match(type="PARAM_VALUE", blocking=True, timeout=3)
        if msg:
            actual = float_as_int(msg.param_value)
            ok = "OK" if actual == expected else "MISMATCH"
            print(f"[Drone {drone_id}] {msg.param_id.rstrip(chr(0))} = {actual} ({ok})")
        else:
            print(f"[Drone {drone_id}] {name}: no response")

    conn.close()
    print(f"[Drone {drone_id}] Done\n")


if __name__ == "__main__":
    for i, port in enumerate(PORTS, 1):
        try:
            set_params(port, i)
        except Exception as e:
            print(f"[Drone {i}] Error: {e}")
