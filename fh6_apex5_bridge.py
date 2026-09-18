import configparser
import json
import math
import os
import socket
import struct
import threading
import time
from pathlib import Path

try:
    import hid
except ImportError:
    raise SystemExit("Install dependency first: py -m pip install hidapi")


# ============================================================
# FH6 + FLYDIGI APEX 5 Adaptive Trigger Bridge
# v11
#
# IMPORTANT:
#   XInput is NOT replaced or hidden.
#   This program writes only to the APEX 5 vendor HID interface.
#
# Modes used:
#   0 Normal
#   1 Race      -> continuous pedal resistance
#   2 Vibration -> small RPM / ABS / road texture
#   3 Recoil    -> LT ONLY, tiny brake/ABS pulse
#
# No Recoil is ever sent to RT.
# ============================================================

VID = 0x37D7
PID = 0x2501
USAGE_PAGE = 0xFFA0
USAGE = 0x0001

UDP_IP = "127.0.0.1"
UDP_PORT = 5300

REPORT_ID = 0x03
CMD_SET_FORCE = 81

LEFT = 1
RIGHT = 2
STROKE = 0

UPDATE_DT = 0.01
KEEPALIVE = 0.08
TELEMETRY_TIMEOUT = 0.50
GUI_STATE_PATH = Path(os.environ.get("APEX5_GUI_STATE_PATH", Path(__file__).resolve().parent / "telemetry_state.json"))


def f(cfg, section, key):
    return float(cfg[section][key])


def i(cfg, section, key):
    return int(float(cfg[section][key]))


def clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(round(v))))


def finite(v):
    return v if math.isfinite(v) else 0.0


def write_gui_state(state):
    """Best-effort side-channel for GUI dashboard; does not affect trigger output."""
    try:
        tmp = GUI_STATE_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        tmp.replace(GUI_STATE_PATH)
    except Exception:
        pass


def f32(data, offset):
    return struct.unpack_from("<f", data, offset)[0]


def u8(data, offset):
    return data[offset]


def i32(data, offset):
    return struct.unpack_from("<i", data, offset)[0]


def lerp(a, b, x):
    x = max(0.0, min(1.0, x))
    return a + (b - a) * x


def packet(side, mode, params):
    # APEX 5 SetForceTrigger command 81.
    # [0] report id 03
    # [1..2] 5A A5
    # [3] command 81
    # [4] length 10 (decimal)
    # [5] apply flag 1
    # [6] side
    # [7] mode
    # [8..] effect parameters
    values = [side, mode] + list(params)
    values += [0] * (7 - len(values))
    values = values[:7]

    report = bytearray(32)
    report[:6] = bytes(
        (REPORT_ID, 0x5A, 0xA5, CMD_SET_FORCE, 10, 1)
    )
    report[6:13] = bytes(clamp(v) for v in values)
    return bytes(report)


def normal(side):
    return packet(side, 0, [])


def race(side, resistance):
    # Race effect starts from the beginning of trigger travel.
    return packet(side, 1, [STROKE, clamp(max(1, resistance)), 0])


def vibration(side, pressure, strength, frequency):
    # Vibration is used only for texture/engine/ABS/road.
    return packet(
        side,
        2,
        [
            STROKE,
            clamp(max(1, pressure)),
            clamp(max(1, strength)),
            clamp(max(1, frequency)),
            0,
        ],
    )


def recoil(side, recoil_stroke, strength):
    # v11: this function is intentionally called ONLY for LEFT/LT.
    return packet(
        side,
        3,
        [
            STROKE,
            clamp(recoil_stroke),
            clamp(max(1, strength)),
            0,
            0,
        ],
    )


class Telemetry:
    def __init__(self):
        self.lock = threading.Lock()
        self.last_rx = 0.0
        self.race_on = False

        self.rpm = 0.0
        self.max_rpm = 8000.0
        self.idle_rpm = 800.0
        self.speed = 0.0

        self.accel = 0
        self.brake = 0
        self.handbrake = 0
        self.gear = 0

        self.slip_combined = 0.0
        self.slip_angle_rear = 0.0
        self.surface = 0.0
        self.rumble_strip = 0.0
        self.susp_norm = [0.5, 0.5, 0.5, 0.5]

        self.gforce = 0.0
        self.smash_vel = 0.0

        self.last_gear = None
        self.shift_until = 0.0
        self.collision_until = 0.0


def parse_fh6_324(data):
    # FH6 Horizon packet is 324 bytes, little-endian.
    if len(data) != 324:
        return None

    try:
        ax = finite(f32(data, 20))
        ay = finite(f32(data, 24))
        az = finite(f32(data, 28))

        combined = [
            abs(finite(f32(data, 180))),
            abs(finite(f32(data, 184))),
            abs(finite(f32(data, 188))),
            abs(finite(f32(data, 192))),
        ]

        rear_angle = max(
            abs(finite(f32(data, 172))),
            abs(finite(f32(data, 176))),
        )

        surface = [
            max(0.0, finite(f32(data, 148))),
            max(0.0, finite(f32(data, 152))),
            max(0.0, finite(f32(data, 156))),
            max(0.0, finite(f32(data, 160))),
        ]

        rumble = [
            1.0 if i32(data, 116) != 0 else 0.0,
            1.0 if i32(data, 120) != 0 else 0.0,
            1.0 if i32(data, 124) != 0 else 0.0,
            1.0 if i32(data, 128) != 0 else 0.0,
        ]

        susp = [
            finite(f32(data, 68)),
            finite(f32(data, 72)),
            finite(f32(data, 76)),
            finite(f32(data, 80)),
        ]

        return {
            "race_on": i32(data, 0) != 0,
            "rpm": max(0.0, finite(f32(data, 16))),
            "max_rpm": max(1.0, finite(f32(data, 8))),
            "idle_rpm": max(0.0, finite(f32(data, 12))),
            "speed": max(0.0, finite(f32(data, 256))),
            "accel": u8(data, 315),
            "brake": u8(data, 316),
            "handbrake": u8(data, 318),
            "gear": u8(data, 319),
            "slip_combined": min(1.0, max(combined)),
            "slip_angle_rear": min(1.0, rear_angle),
            "surface": min(1.0, max(surface)),
            "rumble_strip": min(1.0, max(rumble)),
            "susp_norm": susp,
            "gforce": min(
                8.0,
                math.sqrt(ax * ax + ay * ay + az * az) / 9.80665,
            ),
            "smash_vel": abs(finite(f32(data, 236))),
        }
    except (IndexError, struct.error):
        return None


def telemetry_loop(tel):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.settimeout(0.10)

    print(f"FH6 UDP listening on {UDP_IP}:{UDP_PORT}")

    while True:
        try:
            data, _ = sock.recvfrom(2048)
        except socket.timeout:
            continue

        parsed = parse_fh6_324(data)
        if parsed is None:
            continue

        now = time.monotonic()

        with tel.lock:
            tel.last_rx = now
            tel.race_on = parsed["race_on"]

            tel.rpm = parsed["rpm"]
            tel.max_rpm = parsed["max_rpm"]
            tel.idle_rpm = parsed["idle_rpm"]
            tel.speed = parsed["speed"]
            tel.accel = parsed["accel"]
            tel.brake = parsed["brake"]
            tel.handbrake = parsed["handbrake"]
            tel.gear = parsed["gear"]

            tel.slip_combined = parsed["slip_combined"]
            tel.slip_angle_rear = parsed["slip_angle_rear"]
            tel.surface = parsed["surface"]
            tel.rumble_strip = parsed["rumble_strip"]
            tel.susp_norm = parsed["susp_norm"]

            tel.gforce = parsed["gforce"]
            tel.smash_vel = parsed["smash_vel"]

            # Gear-shift event is kept as a small vibration/force bump only.
            if (
                tel.last_gear is not None
                and tel.gear != tel.last_gear
                and tel.gear not in (0, 255)
            ):
                tel.shift_until = now + 0.055

            tel.last_gear = tel.gear

            # Collision is only used as a very small vibration/bump.
            if parsed["smash_vel"] >= 3.0 or (
                parsed["gforce"] >= 5.5 and parsed["speed"] > 8
            ):
                tel.collision_until = now + 0.070


def find_apex():
    for dev in hid.enumerate(VID, PID):
        if (
            dev.get("usage_page") == USAGE_PAGE
            and dev.get("usage") == USAGE
        ):
            return dev

    for dev in hid.enumerate(VID, PID):
        if dev.get("interface_number") == 2:
            return dev

    return None


def resolve_profile_path(profile_path):
    """Allow editing either profiles/<name>.ini or the root <name>.ini.
    Whichever copy was modified most recently is used, removing the
    ambiguity that caused RT tuning to appear to do nothing.
    """
    path = Path(profile_path)
    root = path.parent.parent / path.name if path.parent.name == "profiles" else None
    if root is not None and path.exists() and root.exists():
        return root if root.stat().st_mtime > path.stat().st_mtime else path
    if path.exists():
        return path
    if root is not None and root.exists():
        return root
    return path


def main(profile_path):
    profile_path = resolve_profile_path(Path(profile_path))
    cfg = configparser.ConfigParser()
    if not cfg.read(profile_path, encoding="utf-8"):
        raise SystemExit(f"Config not found: {profile_path}")

    profile_name = cfg["profile"]["name"]

    # Continuous resistance.
    gas_base = f(cfg, "resistance", "gas_base")
    gas_input = f(cfg, "resistance", "gas_input")
    gas_rpm = f(cfg, "resistance", "gas_rpm")
    brake_base = f(cfg, "resistance", "brake_base")
    brake_input = f(cfg, "resistance", "brake_input")
    brake_abs = f(cfg, "resistance", "brake_abs")
    handbrake_max = f(cfg, "resistance", "handbrake_max")

    # Vibration.
    r_vib_max = f(cfg, "vibration", "r2_max_strength")
    l_vib_max = f(cfg, "vibration", "l2_max_strength")
    r_vib_duty = f(cfg, "vibration", "r2_duty")
    l_vib_duty = f(cfg, "vibration", "l2_duty")
    r_vib_pressure = f(cfg, "vibration", "r2_pressure")
    l_vib_pressure = f(cfg, "vibration", "l2_pressure")
    r_freq_min = f(cfg, "vibration", "r2_freq_min")
    r_freq_max = f(cfg, "vibration", "r2_freq_max")
    l_freq_min = f(cfg, "vibration", "l2_freq_min")
    l_freq_max = f(cfg, "vibration", "l2_freq_max")

    # Road.
    road_max = f(cfg, "road", "max_strength")
    road_drift_reduction = f(cfg, "road", "drift_reduction")
    road_speed_scale = f(cfg, "road", "road_speed_scale")
    air_edge_low = f(cfg, "road", "airborne_susp_low")
    air_edge_high = f(cfg, "road", "airborne_susp_high")
    air_wheel_votes = i(cfg, "road", "airborne_wheel_votes")
    road_in_air = f(cfg, "road", "airborne_multiplier")
    road_in_drift = f(cfg, "road", "drift_multiplier")

    # Recoil, LT only.
    recoil_enabled = cfg["recoil"].getboolean("enabled")
    recoil_brake_threshold = i(cfg, "recoil", "brake_threshold")
    recoil_abs_threshold = f(cfg, "recoil", "abs_threshold")
    recoil_strength = f(cfg, "recoil", "strength")
    recoil_stroke = f(cfg, "recoil", "stroke")
    recoil_cooldown = f(cfg, "recoil", "cooldown_ms") / 1000.0

    device = find_apex()
    if device is None:
        raise SystemExit(
            "APEX 5 vendor HID 0xFFA0/0x0001 not found. "
            "Keep the 2.4 GHz dongle connected."
        )

    hid_dev = hid.device()
    hid_dev.open_path(device["path"])
    hid_dev.set_nonblocking(True)

    tel = Telemetry()
    threading.Thread(target=telemetry_loop, args=(tel,), daemon=True).start()

    print(f"APEX 5 FH6 Bridge v12.7 / profile={profile_name}")
    print("RT = config-driven gas resistance + separate RPM vibration; gas_* = 0 means FREE RT")
    print("LT = brake resistance + ABS/road vibration + optional recoil")
    print("Recoil is LT ONLY. Race resistance is preserved while vibration is active.")
    print("No Flydigi Space, Space Station or virtual controller is used.")
    print("FH6 must send 324-byte Car Dash telemetry to UDP 5300.")
    print(f"Config: {profile_path.resolve()}")
    print(
        f"RT config: base={gas_base:g} input={gas_input:g} rpm={gas_rpm:g} | "
        f"R2 vib={r_vib_max:g} duty={r_vib_duty:g} "
        f"freq={r_freq_min:g}-{r_freq_max:g} Hz"
    )
    print("Ctrl+C to stop.")

    sent = {
        LEFT: (None, 0.0),
        RIGHT: (None, 0.0),
    }
    t0 = time.monotonic()
    last_log = 0.0
    last_recoil = 0.0
    last_gui_state = 0.0

    def send(side, report, force=False):
        now = time.monotonic()
        old, old_t = sent[side]
        if force or report != old or now - old_t >= KEEPALIVE:
            hid_dev.write(report)
            sent[side] = (report, now)

    try:
        while True:
            now = time.monotonic()

            with tel.lock:
                age = now - tel.last_rx
                race_on = tel.race_on

                rpm = tel.rpm
                maxrpm = tel.max_rpm
                idle = tel.idle_rpm
                speed = tel.speed

                accel = tel.accel
                brake = tel.brake
                hand = tel.handbrake
                slip = tel.slip_combined
                rear_angle = tel.slip_angle_rear
                surface = tel.surface
                rumble = tel.rumble_strip
                susp = list(tel.susp_norm)

                shift_until = tel.shift_until
                collision_until = tel.collision_until

            if age > TELEMETRY_TIMEOUT:
                # Only a real telemetry timeout disables effects. The first
                # int32 in the FH6 packet is not used as a trigger-enable
                # switch, so config values remain effective whenever valid
                # 324-byte telemetry is arriving.
                send(LEFT, normal(LEFT))
                send(RIGHT, normal(RIGHT))
                time.sleep(UPDATE_DT)
                continue

            rpm_ratio = max(
                0.0,
                min(1.0, (rpm - idle) / max(1.0, maxrpm - idle)),
            )

            # ==========================================================
            # ROAD CONTACT / AIRBORNE HEURISTIC
            #
            # FH6 does not expose a simple "is airborne" boolean in the
            # 324-byte Car Dash. We use normalized suspension travel as a
            # contact heuristic and still require actual road signals.
            #
            # This deliberately affects ROAD vibration only; engine/ABS
            # effects continue to work in the air.
            # ==========================================================
            edge_votes = sum(
                1
                for x in susp
                if x <= air_edge_low or x >= air_edge_high
            )

            # Road-contact signal is based on the game's actual road fields.
            # WheelOnRumbleStrip is discrete; SurfaceRumble is continuous.
            road_signal = max(surface, rumble)

            airborne = (
                edge_votes >= air_wheel_votes
                and speed > 8.0
                and road_signal < 0.10
            )

            road_gain = road_in_air if airborne else 1.0

            # Drift attenuation: combined slip and rear slip angle.
            drift_index = max(
                0.0,
                min(1.0, max(slip, rear_angle)),
            )
            drift_factor = 1.0 - (
                road_drift_reduction * drift_index
            )
            drift_factor = max(road_in_drift, drift_factor)

            road_gain *= drift_factor

            # Road strength uses road signal only, never gas/brake.
            road_level = min(
                1.0,
                max(surface, rumble),
            )
            road_level *= min(
                1.0,
                speed / max(1.0, road_speed_scale),
            )

            road_strength = min(
                road_max,
                road_level * road_max * road_gain,
            )

            road_hz = lerp(4.0, 14.0, min(1.0, speed / 50.0))

            # ==========================================================
            # CORE:
            # Resistance and vibration are deliberately separate effects.
            #
            # The trigger never falls back to Normal while the game is
            # producing valid telemetry. Instead, the base Race force
            # continuously changes with pedal input, RPM, load, ABS and road
            # context to simulate a real pedal.
            #
            # Vibration is multiplexed in short windows, not allowed to
            # replace the Race effect for an extended time.
            # ==========================================================

            # ----- RT / GAS -----
            # RT resistance is controlled ONLY by the three gas_* values:
            #   gas_base + throttle*gas_input + rpm_ratio*gas_rpm
            # All three set to zero => RT is truly FREE.
            throttle = accel / 255.0
            rpm_ratio = max(
                0.0,
                min(1.0, (rpm - idle) / max(1.0, maxrpm - idle))
            )

            rt_control_enabled = (
                abs(gas_base) > 1e-9
                or abs(gas_input) > 1e-9
                or abs(gas_rpm) > 1e-9
            )

            rt_hz = lerp(r_freq_min, r_freq_max, rpm_ratio)
            rt_base = 0.0
            rt_resistance = 0.0
            use_r_vib = False

            if not rt_control_enabled:
                rt_packet = normal(RIGHT)
            else:
                rt_base = (
                    gas_base
                    + throttle * gas_input
                    + rpm_ratio * gas_rpm
                )

                # IMPORTANT: RT resistance is now kept completely separate
                # from RT vibration. gas_* define the Race resistance directly;
                # r2_* vibration parameters never get added to rt_resistance.
                # This makes gas_base=1 actually mean Race(1), not Race(1+vib).
                rt_resistance = max(0.0, rt_base)
                rt_packet = race(RIGHT, rt_resistance)

                # RT vibration follows RPM and is independent of how far the
                # trigger is pressed. gas_* only enable/disable the RT effect.
                r_cycle_hz = max(3.0, rt_hz)
                r_cycle = (now - t0) * r_cycle_hz
                r_frac = r_cycle - math.floor(r_cycle)
                use_r_vib = r_vib_max > 0.0 and r_frac < r_vib_duty

            # ----- LT / BRAKE -----
            brake_ratio = brake / 255.0

            # Always-on brake pedal resistance:
            # stronger than RT by design.
            abs_level = slip if brake >= 10 else 0.0

            lt_resistance = (
                brake_base
                + brake_ratio * brake_input
                + abs_level * brake_abs
            )

            # ABS vibration frequency dominates when braking/slipping.
            abs_hz = lerp(l_freq_min, l_freq_max, abs_level)
            road_hz = lerp(4.0, 14.0, min(1.0, speed / 50.0))

            if brake >= 10:
                lt_phase_hz = abs_hz * 0.82 + road_hz * 0.18
            else:
                lt_phase_hz = road_hz

            # ABS/road texture as a continuous resistance modulation.
            lt_wave_amp = 0.0
            if brake >= 10 and abs_level > 0.02:
                lt_wave_amp += l_vib_max * (
                    0.35 + 0.65 * abs_level
                )
            if speed > 5.0:
                lt_wave_amp += road_strength * 0.45

            lt_phase = 2.0 * math.pi * lt_phase_hz * (now - t0) + 0.6
            lt_resistance = lt_resistance + (
                math.sin(lt_phase) * lt_wave_amp
            )

            lt_packet = race(LEFT, max(2.0, lt_resistance))

            # ----- ACTUAL VIBRATION MODE, SHORT/DUTY-LIMITED -----
            # This is the fix for the "I don't feel the vibration on RT/LT"
            # problem. The Race effect stays dominant, while a short vibration
            # window is inserted at the frequency derived from RPM/ABS.
            # Because the vibration window is short, resistance does not vanish.
            r_cycle_hz = max(3.0, rt_hz)
            l_cycle_hz = max(4.0, lt_phase_hz)

            r_cycle = (now - t0) * r_cycle_hz
            l_cycle = (now - t0) * l_cycle_hz

            r_frac = r_cycle - math.floor(r_cycle)
            l_frac = l_cycle - math.floor(l_cycle)

            use_r_vib = throttle >= 0.03 and r_frac < r_vib_duty
            use_l_vib = brake >= 0.03 and l_frac < l_vib_duty

            if use_r_vib:
                rt_packet = vibration(
                    RIGHT,
                    r_vib_pressure,
                    r_vib_max,
                    rt_hz,
                )

            if use_l_vib:
                lt_packet = vibration(
                    LEFT,
                    l_vib_pressure,
                    l_vib_max,
                    lt_phase_hz,
                )

            # ----- OPTIONAL RECOIL: LT ONLY -----
            # Never send Recoil to RT.
            if recoil_enabled:
                can_recoil = (
                    brake >= recoil_brake_threshold
                    and slip >= recoil_abs_threshold
                    and now - last_recoil >= recoil_cooldown
                )
                if can_recoil:
                    lt_packet = recoil(
                        LEFT,
                        recoil_stroke,
                        recoil_strength,
                    )
                    last_recoil = now


            send(LEFT, lt_packet)
            send(RIGHT, rt_packet)

            # GUI telemetry side-channel. This does not modify trigger logic or HID packets.
            if now - last_gui_state >= 0.10:
                write_gui_state({
                    "timestamp": time.time(),
                    "profile": profile_name,
                    "telemetry_age_ms": age * 1000.0,
                    "speed_kmh": speed * 3.6,
                    "rpm": rpm,
                    "max_rpm": maxrpm,
                    "idle_rpm": idle,
                    "gear": tel.gear,
                    "accel": accel,
                    "brake": brake,
                    "handbrake": hand,
                    "slip": slip,
                    "surface": surface,
                    "rumble": rumble,
                    "susp_norm": susp,
                    "gforce": tel.gforce,
                    "smash_vel": tel.smash_vel,
                    "drift": drift_index,
                    "airborne": airborne,
                    "road_strength": road_strength,
                    "rt_resistance": rt_resistance,
                    "rt_base_configured": rt_base,
                    "lt_resistance": lt_resistance,
                    "rt_hz": rt_hz,
                    "lt_hz": lt_phase_hz,
                    "rt_control_enabled": rt_control_enabled,
                    "use_r_vib": use_r_vib,
                    "use_l_vib": use_l_vib,
                    "recoil_active": recoil_enabled and (brake >= recoil_brake_threshold and slip >= recoil_abs_threshold and now - last_recoil < 0.10),
                })
                last_gui_state = now

            if now - last_log >= 0.5:
                print(
                    f"\r{speed*3.6:5.1f} km/h | RPM {rpm:5.0f} | "
                    f"gas {accel:3d} brake {brake:3d} | "
                    f"Rforce {rt_resistance:4.1f} Lforce {lt_resistance:4.1f} | "
                    f"RHz {rt_hz:4.1f} ABSHz {lt_phase_hz:4.1f} | "
                    f"RT={'ON' if rt_control_enabled else 'FREE'} TEL={age*1000:4.0f}ms | "
                    f"profile={profile_name}",
                    end="",
                    flush=True,
                )
                last_log = now

            time.sleep(UPDATE_DT)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        try:
            hid_dev.write(normal(LEFT))
            hid_dev.write(normal(RIGHT))
        except Exception:
            pass
        hid_dev.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: py fh6_apex5_bridge.py profiles\\soft.ini"
        )

    main(Path(sys.argv[1]))
