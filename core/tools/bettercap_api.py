"""
bettercap_api.py

Anders als nmap_tool.py: bettercap laeuft hier DAUERHAFT im
Hintergrund (nicht einmal ausfuehren und fertig). Deshalb zwei
getrennte Funktionen statt einer:

1. starte()       -> einmal aufrufen, startet bettercap im Hintergrund
2. hole_geraete()  -> beliebig oft aufrufen, gibt aktuellen Stand zurueck
3. stoppe()        -> beendet bettercap wieder
"""

import os
import signal
import subprocess
import requests

API_URL = "http://127.0.0.1:8081/api/session"
API_USER = "user"
API_PASS = "pass"
SUDO_PASSWORT = "theo4801"

_prozess = None  # merkt sich den laufenden bettercap-Prozess


def starte(interface="wlan0"):
    """Startet bettercap im Hintergrund mit aktivierter REST-API."""
    global _prozess

    befehl = [
        "sudo","-S", "bettercap", "-iface", interface, "-eval",
        f"set api.rest.username {API_USER}; "
        f"set api.rest.password {API_PASS}; "
        f"api.rest on; "
        f"net.probe on"
    ]
    _prozess = subprocess.Popen(
        befehl,
        stdin=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    _prozess.stdin.write(SUDO_PASSWORT + "\n")
    _prozess.stdin.flush()


def hole_geraete():
    """
    Fragt den aktuellen Stand ab und gibt ein Dict zurueck:
    {"Gerätename": "IP", ...}

    Kann beliebig oft aufgerufen werden, waehrend bettercap im
    Hintergrund laeuft - jedes Mal der aktuellste Stand.
    """
    try:
        antwort = requests.get(API_URL, auth=(API_USER, API_PASS), timeout=3)
        daten = antwort.json()
    except requests.exceptions.RequestException:
        # z.B. bettercap noch nicht bereit oder nicht gestartet
        return {}

    geraete = {}
    for host in daten.get("lan", {}).get("hosts", []):
        name = host.get("hostname") or "unbekannt"
        geraete[name] = host.get("ipv4", "")

    return geraete


def stoppe():
    """Beendet den bettercap-Hintergrundprozess wieder."""
    global _prozess
    if _prozess is not None:
        try:
            os.killpg(os.getpgid(_prozess.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        _prozess = None