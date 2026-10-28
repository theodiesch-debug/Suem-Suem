import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from core.tools import bettercap_api
import time

def zeige_wlan_nutzer():
    bettercap_api.starte("wlan0")
    time.sleep(5)
    nutzer = bettercap_api.hole_geraete()
    print(nutzer)  # <- jetzt eingerückt, innerhalb der Funktion
def stopp_bettercap():
    bettercap_api.stoppe()

zeige_wlan_nutzer()
stopp_bettercap()