#!/usr/bin/env python3
# Traccar -> APRS-IS Gateway
# - SmartBeaconing completo (velocidad + cambio de rumbo)
# - Beacon al apagar motor
# - Envia solo posicion nueva

import requests
import socket
import time
import math

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

# ========= CONFIG =========
CHECK_INTERVAL = 10          # segundos
COMMENT_MOVING = "Vehiculo en movimiento"
COMMENT_STOPPED = "Motor OFF"

TURN_ANGLE = 30              # grados
TURN_MIN_SPEED = 10          # km/h
TURN_MIN_INTERVAL = 15       # segundos

# ========= ESTADO =========
last_position_id = None
last_beacon_time = 0
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
        login = f"user {APRS_CALLSIGN} pass {APRS_PASSCODE} vers Traccar-APRS 3.0\n"
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

def send_beacon(pos, comment):
    lat = lat_aprs(pos["latitude"])
    lon = lon_aprs(pos["longitude"])
    course = int(pos.get("course", 0))
    speed_knots = int(pos.get("speed", 0) * 1.94384)

    packet = (
        f"{APRS_CALLSIGN}>APRS,TCPIP*:="
        f"{lat}/{lon}>"
        f"{course:03d}/{speed_knots:03d}"
        f" {comment}"
    )

    print("Enviando APRS:", packet)
    send_aprs(packet)

# ========= LOOP PRINCIPAL =========

if __name__ == "__main__":
    print("Traccar -> APRS-IS con SmartBeaconing avanzado iniciado")

    while True:
        try:
            pos = get_position()
            position_id = pos.get("id")
            ignition = pos.get("attributes", {}).get("ignition", False)
            course = int(pos.get("course", 0))
            speed_kmh = pos.get("speed", 0) * 3.6
            now = time.time()

            # Beacon al apagar motor
            if last_ignition is True and ignition is False:
                print("Motor apagado, enviando beacon final")
                send_beacon(pos, COMMENT_STOPPED)
                last_position_id = position_id
                last_ignition = ignition
                time.sleep(CHECK_INTERVAL)
                continue

            # Motor apagado → nada
            if not ignition:
                last_ignition = ignition
                time.sleep(CHECK_INTERVAL)
                continue

            # Posicion no nueva
            if position_id == last_position_id:
                time.sleep(CHECK_INTERVAL)
                continue

            # Cambio de rumbo
            if (
                last_course is not None
                and speed_kmh >= TURN_MIN_SPEED
                and angle_diff(course, last_course) >= TURN_ANGLE
                and now - last_beacon_time >= TURN_MIN_INTERVAL
            ):
                print("Cambio de rumbo detectado")
                send_beacon(pos, COMMENT_MOVING)
                last_beacon_time = now
                last_course = course
                last_position_id = position_id
                last_ignition = ignition
                time.sleep(CHECK_INTERVAL)
                continue

            # Intervalo por velocidad
            interval = smartbeacon_interval(speed_kmh)
            if now - last_beacon_time >= interval:
                send_beacon(pos, COMMENT_MOVING)
                last_beacon_time = now
                last_course = course
                last_position_id = position_id
                last_ignition = ignition

        except Exception as e:
            print("Error:", e)

        time.sleep(CHECK_INTERVAL)
