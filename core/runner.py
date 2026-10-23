"""
runner.py

Einfache Runner-Klasse, die Shell-Befehle in einem Hintergrund-Thread
ausführt und das Ergebnis über eine Queue zurückgibt.

Grundidee:
- run() startet den Befehl NICHT blockierend (gibt sofort zurück)
- im Hintergrund läuft der Befehl in einem eigenen Thread
- wenn er fertig ist, landet das Ergebnis in einer Queue
- andere Teile deines Programms (z. B. die UI) rufen regelmäßig
  get_result() auf, um zu prüfen, ob etwas Neues da ist
"""

import subprocess
import threading
import queue


class Runner:
    def __init__(self):
        # Queue ist thread-sicher -> mehrere Threads können gleichzeitig
        # reinschreiben, ohne dass sich Daten überschreiben
        self._results = queue.Queue()

    def run(self, command, name=None):
        """
        Startet einen Befehl im Hintergrund.
        command: Liste wie bei subprocess, z.B. ["nmap", "-sn", "192.168.1.0/24"]
        name:    optionaler Name, um später zu erkennen, welcher Befehl
                 das Ergebnis geliefert hat (z.B. "nmap_scan")
        """
        if name is None:
            name = command[0]

        thread = threading.Thread(
            target=self._worker,
            args=(command, name),
            daemon=True  # Thread stirbt automatisch mit dem Hauptprogramm
        )
        thread.start()

    def _worker(self, command, name):
        """Läuft im Hintergrund-Thread, macht die eigentliche Arbeit."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True
            )
            output = result.stdout
            error = result.stderr
            success = result.returncode == 0
        except Exception as e:
            output = ""
            error = str(e)
            success = False

        # Ergebnis als Dictionary in die Queue legen
        self._results.put({
            "name": name,
            "success": success,
            "output": output,
            "error": error,
        })

    def get_result(self):
        """
        Gibt das nächste fertige Ergebnis zurück, oder None,
        wenn gerade nichts Neues da ist. Blockiert NICHT.
        """
        try:
            return self._results.get_nowait()
        except queue.Empty:
            return None

    def has_result(self):
        """Praktisch für eine UI-Schleife: gibt es etwas Neues?"""
        return not self._results.empty()