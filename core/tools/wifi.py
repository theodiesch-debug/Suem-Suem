# core/Tools/search_wifis.py
import os
import sys

# Gehe einen Ordner hoch zu core/
CORE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

from runner import run, ReturnStatus,run_sudo

#nmcli -t -f SSID,SIGNAL device wifi list
def search_wifis():
    #liste wird erstelllt für wlan
    verfügbare_wifis = []
    #befehl wird ausgeführt
    status,output = run(["nmcli","-t","-f","SSID","device","wifi","list"])
    #error handling
    if status == ReturnStatus.ERROR:
        return None
    elif status == ReturnStatus.OK:
        #ergebnis wird geloopt und in die liste gemacht
        for lines in output.splitlines():
            if lines != "":
                verfügbare_wifis.append(lines)
        return verfügbare_wifis
#verbinden
def connectWifi(ssid: str, passwort: str):
    # altes Profil löschen
    run_sudo(["nmcli", "connection", "delete", ssid], "theo4801")

    status, output = run_sudo(
        ["nmcli", "dev", "wifi", "connect", ssid, "password", passwort],
        "theo4801"
    )

    if status == ReturnStatus.OK:
        return True, output
    else:
        return False, output
