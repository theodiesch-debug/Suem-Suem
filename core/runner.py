import atexit
import os
import subprocess
import tempfile
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass


@dataclass
class Result:
    ok: bool
    stdout: str
    stderr: str
    code: int  # 0 = Erfolg, >0 = Exit-Code, -1 = eigener Fehler (Timeout, nicht gefunden, ...)


class Runner:
    def __init__(self, default_timeout=30, max_workers=8):
        self.default_timeout = default_timeout
        self._background = {}          # name -> (Popen, logpfad)
        self._lock = threading.RLock()  # schuetzt _background bei Thread-Zugriff
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        atexit.register(self.shutdown)  # beim Programmende alles aufraeumen

    # ---------- blockierend ----------
    def run(self, cmd, timeout=None):
        timeout = timeout or self.default_timeout
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return Result(p.returncode == 0, p.stdout, p.stderr, p.returncode)
        except subprocess.TimeoutExpired:
            return Result(False, "", "Timeout", -1)
        except FileNotFoundError:
            return Result(False, "", f"{cmd[0]} nicht gefunden", -1)
        except OSError as e:  # z.B. PermissionError
            return Result(False, "", str(e), -1)

    def pipe(self, cmd1, cmd2, timeout=None):
        timeout = timeout or self.default_timeout
        p1 = p2 = None
        err1 = tempfile.TemporaryFile()  # verhindert volle Pipe-Puffer bei cmd1
        try:
            p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, stderr=err1)
            p2 = subprocess.Popen(cmd2, stdin=p1.stdout, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True)
            p1.stdout.close()
            out, err = p2.communicate(timeout=timeout)
            p1.wait(timeout=5)
            err1.seek(0)
            err_all = err1.read().decode(errors="replace") + err
            return Result(p2.returncode == 0, out, err_all, p2.returncode)
        except subprocess.TimeoutExpired:
            return Result(False, "", "Timeout", -1)
        except FileNotFoundError as e:
            return Result(False, "", f"{e.filename} nicht gefunden", -1)
        except OSError as e:
            return Result(False, "", str(e), -1)
        finally:
            for p in (p1, p2):
                if p and p.poll() is None:
                    p.kill()
                    p.wait()
            err1.close()

    # ---------- nicht blockierend (Thread) ----------
    def run_async(self, cmd, timeout=None, callback=None) -> Future:
        """Fuehrt run() in einem Thread aus. Gibt sofort ein Future zurueck."""
        fut = self._pool.submit(self.run, cmd, timeout)
        if callback:
            fut.add_done_callback(lambda f: callback(f.result()))
        return fut

    def pipe_async(self, cmd1, cmd2, timeout=None, callback=None) -> Future:
        fut = self._pool.submit(self.pipe, cmd1, cmd2, timeout)
        if callback:
            fut.add_done_callback(lambda f: callback(f.result()))
        return fut

    # ---------- Hintergrundprozesse ----------
    def start(self, name, cmd) -> Result:
        """Startet cmd dauerhaft im Hintergrund. stdout+stderr gehen in eine Logdatei."""
        with self._lock:
            if self.is_running(name):
                return Result(False, "", f"'{name}' laeuft bereits", -1)
            fd, path = tempfile.mkstemp(prefix=f"runner_{name}_", suffix=".log")
            try:
                with os.fdopen(fd, "wb") as log:
                    p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
            except FileNotFoundError:
                os.remove(path)
                return Result(False, "", f"{cmd[0]} nicht gefunden", -1)
            except OSError as e:
                os.remove(path)
                return Result(False, "", str(e), -1)
            self._background[name] = (p, path)
            return Result(True, "", "", 0)

    def is_running(self, name) -> bool:
        with self._lock:
            entry = self._background.get(name)
            return entry is not None and entry[0].poll() is None

    def exit_code(self, name):
        """None = laeuft noch (oder unbekannt), sonst der Exit-Code."""
        with self._lock:
            entry = self._background.get(name)
            return entry[0].poll() if entry else None

    def read_output(self, name) -> str:
        """Bisherige Ausgabe (stdout+stderr) des Hintergrundprozesses."""
        with self._lock:
            entry = self._background.get(name)
        if not entry:
            return ""
        with open(entry[1], "r", errors="replace") as f:
            return f.read()

    def stop(self, name) -> str:
        """Beendet den Prozess, raeumt auf, gibt die letzte Ausgabe zurueck."""
        with self._lock:
            entry = self._background.pop(name, None)
        if not entry:
            return ""
        p, path = entry
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
        try:
            with open(path, "r", errors="replace") as f:
                out = f.read()
            os.remove(path)
        except OSError:
            out = ""
        return out

    def stop_all(self):
        with self._lock:
            names = list(self._background)
        for n in names:
            self.stop(n)

    def shutdown(self):
        self.stop_all()
        self._pool.shutdown(wait=False, cancel_futures=True)


runner = Runner()