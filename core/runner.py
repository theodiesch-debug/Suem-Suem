import subprocess
from dataclasses import dataclass


@dataclass
class Result:
    ok:bool
    stdout:str
    stderr:str
    code:int

class Runner:
    def __init__(self,default_timeout=30):
        self.default_timeout = default_timeout
        self._background = {}
    
    def run(self,cmd,timeout=None):
        timeout = timeout or self.default_timeout
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return Result(p.returncode == 0, p.stdout, p.stderr, p.returncode)
        except subprocess.TimeoutExpired:
            return Result(False, "", "Timeout", -1)
        except FileNotFoundError:
            return Result(False, "", f"{cmd[0]} nicht gefunden", -1)

    def pipe(self, cmd1, cmd2, timeout=None):
        timeout = timeout or self.default_timeout
        try:
            p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE)
            p2 = subprocess.Popen(cmd2, stdin=p1.stdout,
                                  stdout=subprocess.PIPE, text=True)
            p1.stdout.close()          
            out, _ = p2.communicate(timeout=timeout)
            return Result(p2.returncode == 0, out, "", p2.returncode)
        except subprocess.TimeoutExpired:
            p1.kill()
            p2.kill()
            return Result(False, "", "Timeout", -1)

    def start(self, name, cmd):
        self._background[name] = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )

    def stop(self, name):
        p = self._background.pop(name, None)
        if p:
            p.terminate()
            p.wait(timeout=5)

    def is_running(self, name):
        p = self._background.get(name)
        return p is not None and p.poll() is None

runner = Runner()      