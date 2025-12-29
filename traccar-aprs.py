#!/usr/bin/env python3
# Traccar -> APRS-IS Gateway
# Beacons SOLO con motor encendido
# Excepcion: 1 beacon final al apagar motor

import requests
import socket
import time
from datetime import datetime

# ========= TRACCAR =========
TRACCAR_URL = "http://localhost:8082"
TRACCAR_USER = "usuario"
TRACCAR_PASS = "password"
TRACCAR_DEVICE_ID = 3

# ========= APRS =========
APRS_SERVER = "rotate.aprs2.net"
APRS_PORT = 14580
APRS_CALLSIGN = "AB0XYZ-9"
APRS_PASSCODE = "12345"

# ========= SIMBOLO APRS =========
APRS_SYMBOL_TABLE = "/"
APRS_SYMBOL_CODE = ">"

# ========= CONFIG =========
CHECK_INTERVAL = 10
STATUS_INTERVAL = 300

COMMENT_MOVING = "Vehiculo en movimiento"
COMMENT_STOPPED = "Motor OFF"

# SmartBeaconing
TURN_ANGLE = 30
TURN_MIN_SPEED = 10       # km/h
TURN_MIN_INTERVAL = 15    # segundos

# ========= ESTADO =========
last_position_id = None
last_beacon_time = 0
last_status_time = 0
last_course = None
last_ignition = None

# ========= UTILIDADES =========

def lat_aprs(lat):
    hemi = 'N' if lat >= 0 else 'S'
    lat = abs(lat)
    return f"{int(lat):02d}{(lat % 1) * 60:05.2f}{hemi}"

def lon_aprs(lon):
    hemi = 'E' if lon >= 0 else 'W'
    lon = abs(lon)
    return f"{int(lon):03d}{(lon % 1) * 60:05.2f}{hemi}"

def send_aprs(packet):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((APRS_SERVER, APRS_PORT))
        login = f"user {APRS_CALLSIGN} pass {APRS_PASSCODE} vers Traccar-APRS 3.4\n"
        s.send(login.encode())
        s.send((packet + "\n").encode())

def get_position():
    r = requests.get(
        f"{TRACCAR_URL}/api/positions?deviceId={TRACCAR_DEVICE_ID}",
        auth=(TRACCAR_USER, TRACCAR_PASS),
        timeout=10
    )
    r.raise_for_status()
    return r.json()[0]

def smartbeacon_interval(speed_kmh):
    if speed_kmh < 5:
        return 180
    elif speed_kmh < 30:
        return 60
    else:
        return 30

def angle_diff(a, b):
    diff = abs(a - b) % 360
    return diff if diff <= 180 else 360 - diff

# ========= BEACONS =========

def send_position_beacon(pos, comment):
    lat = lat_aprs(pos["latitude"])
    lon = lon_aprs(pos["longitude"])
    course = int(pos.get("course", 0))
    speed_knots = int(pos.get("speed", 0))

    packet = (
        f"{APRS_CALLSIGN}>APRS,TCPIP*:="
        f"{lat}{APRS_SYMBOL_TABLE}{lon}{APRS_SYMBOL_CODE}"
        f"{course:03d}/{speed_knots:03d}"
        f" {comment}"
    )

    print("POS:", packet)
    send_aprs(packet)

def send_status_beacon(pos, ignition):
    speed_knots = int(pos.get("speed", 0))
    speed_kmh = speed_knots * 1.852

    voltage = pos.get("attributes", {}).get("battery", None)
    volt_text = f"{voltage:.1f}V" if voltage else "N/A"

    utc = datetime.utcnow().strftime("%H:%MZ")

    status = (
        f"Motor:{'ON' if ignition else 'OFF'} "
        f"Vel:{int(speed_kmh)}km/h "
        f"Bat:{volt_text} "
        f"{utc}"
    )

    packet = f"{APRS_CALLSIGN}>APRS,TCPIP*:>{status}"

    print("STAT:", packet)
    send_aprs(packet)

# ========= LOOP PRINCIPAL =========

if __name__ == "__main__":
    print("Traccar -> APRS-IS iniciado (beacons solo con motor ON)")

    while True:
        try:
            pos = get_position()
            position_id = pos.get("id")
            ignition = pos.get("attributes", {}).get("ignition", False)

            course = int(pos.get("course", 0))
            speed_knots = pos.get("speed", 0)
            speed_kmh = speed_knots * 1.852
            now = time.time()

            # ===== CAMBIO DE ESTADO MOTOR =====
            if last_ignition is not None and ignition != last_ignition:
                # Solo enviar estado si venia encendido
                if last_ignition is True:
                    send_status_beacon(pos, ignition)

            # ===== MOTOR APAGADO =====
            if not ignition:
                # Beacon final SOLO al apagar
                if last_ignition is True:
                    send_position_beacon(pos, COMMENT_STOPPED)
                    last_position_id = position_id

                last_ignition = ignition
                time.sleep(CHECK_INTERVAL)
                continue

            # ===== MOTOR ENCENDIDO =====
            # Beacon de estado periódico
            if now - last_status_time >= STATUS_INTERVAL:
                send_status_beacon(pos, ignition)
                last_status_time = now

            # Posición sin cambios
            if position_id == last_position_id:
                last_ignition = ignition
                time.sleep(CHECK_INTERVAL)
                continue

            # SmartBeaconing por giro
            if (
                last_course is not None
                and speed_kmh >= TURN_MIN_SPEED
                and angle_diff(course, last_course) >= TURN_ANGLE
                and now - last_beacon_time >= TURN_MIN_INTERVAL
            ):
                send_position_beacon(pos, COMMENT_MOVING)
                last_beacon_time = now
                last_course = course
                last_position_id = position_id
                last_ignition = ignition
                time.sleep(CHECK_INTERVAL)
                continue

            # SmartBeaconing por tiempo
            interval = smartbeacon_interval(speed_kmh)
            if now - last_beacon_time >= interval:
                send_position_beacon(pos, COMMENT_MOVING)
                last_beacon_time = now
                last_course = course
                last_position_id = position_id
                last_ignition = ignition

        except Exception as e:
            print("Error:", e)

        time.sleep(CHECK_INTERVAL)
