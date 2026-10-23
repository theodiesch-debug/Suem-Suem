"""Beispiel: nmap im Hintergrund scannen, Ergebnis parsen, GPIO-UI laeuft weiter.

Verdrahtung (BCM-Nummern, anpassbar):
  Button START  -> GPIO 17 (gegen GND)
  Button STOP   -> GPIO 22 (gegen GND)
  LED           -> GPIO 27 (mit Vorwiderstand)
Ohne gpiozero (z.B. am PC) laeuft ein Tastatur-Fallback: s = Scan, x = Abbruch, q = Ende.
"""
import sys
import time
import xml.etree.ElementTree as ET

from runner import runner

TARGET = "192.168.1.0/24"
PIN_START, PIN_STOP, PIN_LED = 17, 22, 27


# ---------- nmap-Ergebnis parsen ----------
def parse_nmap(xml_text):
    """XML von `nmap -oX -` -> [{'ip': ..., 'ports': [(port, proto, service), ...]}]"""
    hosts = []
    root = ET.fromstring(xml_text)
    for h in root.findall("host"):
        status = h.find("status")
        if status is None or status.get("state") != "up":
            continue
        ip = next((a.get("addr") for a in h.findall("address")
                   if a.get("addrtype") == "ipv4"), "?")
        ports = []
        for p in h.findall("ports/port"):
            if p.find("state").get("state") == "open":
                svc = p.find("service")
                ports.append((int(p.get("portid")), p.get("protocol"),
                              svc.get("name") if svc is not None else "?"))
        hosts.append({"ip": ip, "ports": ports})
    return hosts


# ---------- Hardware (mit Fallback) ----------
class Hardware:
    def __init__(self):
        self.start_req = False
        self.stop_req = False
        self.quit = False
        try:
            from gpiozero import Button, LED
            self.led = LED(PIN_LED)
            b_start, b_stop = Button(PIN_START), Button(PIN_STOP)
            b_start.when_pressed = lambda: setattr(self, "start_req", True)
            b_stop.when_pressed = lambda: setattr(self, "stop_req", True)
            self._keep = (b_start, b_stop)   # Referenzen halten, sonst werden Buttons freigegeben
            self.fake = False
        except Exception:
            import threading
            self.led = None
            self.fake = True
            print("[Fallback] s = Scan, x = Abbruch, q = Ende (+Enter)")
            threading.Thread(target=self._keyboard, daemon=True).start()

    def _keyboard(self):
        for line in sys.stdin:
            c = line.strip().lower()
            if c == "s":
                self.start_req = True
            elif c == "x":
                self.stop_req = True
            elif c == "q":
                self.quit = True

    def led_set(self, on):
        if self.led:
            self.led.on() if on else self.led.off()

    def take(self, attr):
        """Flag lesen und zuruecksetzen (einmaliges Ereignis)."""
        v = getattr(self, attr)
        setattr(self, attr, False)
        return v


def main():
    hw = Hardware()
    scanning = False
    last_blink = 0.0
    led_on = False

    print("Bereit. Button START druecken.")
    while not hw.quit:                             # <- UI-Loop, wird NIE blockiert
        # 1) Eingaben
        if hw.take("start_req") and not scanning:
            runner.run_async(
                ["nmap", "-F", "-oX", "-", TARGET], tag="scan", timeout=300)
            scanning = True
            print("Scan gestartet ...")

        if hw.take("stop_req") and scanning:
            # Future.cancel() wirkt nicht mehr, wenn der Job laeuft -> hier simpel:
            # Ergebnis wird beim Eintreffen verworfen.
            print("Abbruch angefordert (Ergebnis wird verworfen)")
            scanning = "cancelled"

        # 2) Fertige Ergebnisse abholen (nicht blockierend)
        for tag, r in runner.poll_results():
            if tag == "scan":
                if scanning == "cancelled":
                    print("Scan verworfen.")
                elif not r.ok:
                    print(f"Scan fehlgeschlagen ({r.code}): {r.stderr.strip()}")
                else:
                    try:
                        hosts = parse_nmap(r.stdout)
                    except ET.ParseError:
                        print("nmap-Ausgabe nicht lesbar")
                        hosts = []
                    print(f"{len(hosts)} Host(s) gefunden:")
                    for h in hosts:
                        ports = ", ".join(f"{p}/{pr} ({s})" for p, pr, s in h["ports"]) or "-"
                        print(f"  {h['ip']}: {ports}")
                scanning = False
                hw.led_set(False)

        # 3) LED blinkt waehrend des Scans
        if scanning and time.time() - last_blink > 0.3:
            led_on = not led_on
            hw.led_set(led_on)
            last_blink = time.time()

        time.sleep(0.02)

    runner.shutdown()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        runner.shutdown()