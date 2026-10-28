import subprocess
from enum import Enum
class ReturnStatus(Enum):
    OK = "ok",
    ERROR = "error"
#ohne sudo
def run(cmd):
    #befehl wird ausgeführt
    run_prozess = subprocess.run(cmd, text=True, capture_output=True)

    #fehler wird überprüft
    if run_prozess.returncode != 0:
        return ReturnStatus.ERROR, run_prozess.stderr

    return ReturnStatus.OK, run_prozess.stdout
def run_sudo(cmd:list[str],sudo_passwort:str):
    #befehl wird zussamengebaut
    befehl = ["sudo","-S"] + cmd
    sudo_prozess = subprocess.run(befehl,
    input= sudo_passwort + "\n",
    capture_output=True,
    text=True
    )
    if sudo_prozess.returncode != 0:
        return ReturnStatus.ERROR, sudo_prozess.stderr
    return ReturnStatus.OK,sudo_prozess.stdout