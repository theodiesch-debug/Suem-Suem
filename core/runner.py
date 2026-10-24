import subprocess
from enum import Enum
class ReturnStatus(Enum):
    OK = "ok",
    ERROR = "error"
def run(cmd):
    run_prozess = subprocess.run(cmd,text=True,capture_output=True)
    if run_prozess.stderr:
        return ReturnStatus.ERROR,run_prozess.stderr
    return ReturnStatus.OK,run_prozess.stdout