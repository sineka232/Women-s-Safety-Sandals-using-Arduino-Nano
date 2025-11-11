# main.py - MicroPython for ESP32
import time
import machine
import ubinascii
import urequests
import ujson
from machine import UART, Pin

# === CONFIG ===
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASS = "YOUR_WIFI_PASSWORD"
SERVER_URL = "https://your-server.example.com/sos"  # Flask server endpoint
DEVICE_ID = ubinascii.hexlify(machine.unique_id()).decode()
SOS_PIN = 14        # GPIO for SOS button (pull-down or pull-up config depends on wiring)
LED_PIN = 2         # onboard LED (change if different)
GPS_UART_NUM = 1
GPS_TX = 17         # pins depend on wiring
GPS_RX = 16
GPS_BAUD = 9600
DEBOUNCE_MS = 300

# ===== helpers =====
def connect_wifi(ssid, pw, timeout=15):
    import network
    wlan = network.WLAN(network.STA_IF)
    if not wlan.active():
        wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(ssid, pw)
        start = time.time()
        while not wlan.isconnected():
            if time.time() - start > timeout:
                return False
            time.sleep(0.5)
    return True

# simple GPS parse: look for GPRMC or GPGGA lat/lon
def parse_nmea_latlon(nmea):
    # returns (lat, lon) as decimal degrees or (None, None)
    try:
        parts = nmea.split(',')
        if parts[0].find("GPRMC") != -1 or parts[0].find("GPGGA") != -1:
            # GPRMC: lat in parts[3], N/S in [4], lon in [5], E/W in [6]
            if "GPRMC" in parts[0]:
                lat_raw = parts[3]; lat_dir = parts[4]
                lon_raw = parts[5]; lon_dir = parts[6]
            else:
                lat_raw = parts[2]; lat_dir = parts[3]
                lon_raw = parts[4]; lon_dir = parts[5]

            if not lat_raw or not lon_raw:
                return None, None

            def dm_to_dd(dm):
                # dm like ddmm.mmmm or dddmm.mmmm
                dot = dm.find('.')
                if dot == -1:
                    return None
                deg_len = dot - 2
                deg = float(dm[:deg_len])
                minutes = float(dm[deg_len:])
                return deg + minutes/60.0

            lat = dm_to_dd(lat_raw)
            lon = dm_to_dd(lon_raw)
            if lat is None or lon is None:
                return None, None
            if lat_dir == 'S':
                lat = -lat
            if lon_dir == 'W':
                lon = -lon
            return lat, lon
    except Exception:
        pass
    return None, None

# ===== init =====
led = Pin(LED_PIN, Pin.OUT)
sos_btn = Pin(SOS_PIN, Pin.IN, Pin.PULL_UP)  # assumes button pulls low when pressed
gps_uart = UART(GPS_UART_NUM, baudrate=GPS_BAUD, tx=GPS_TX, rx=GPS_RX, timeout=2000)

# connect wifi once
if not connect_wifi(WIFI_SSID, WIFI_PASS):
    # blink to indicate wifi failed
    for _ in range(6):
        led.value(not led.value()); time.sleep(0.4)

last_press = 0

def read_gps_location(timeout=3.0):
    # read serial lines for up to timeout seconds and return first valid lat/lon
    deadline = time.time() + timeout
    buf = b""
    while time.time() < deadline:
        if gps_uart.any():
            chunk = gps_uart.read()
            if not chunk:
                continue
            buf += chunk
            # split to lines
            lines = buf.split(b'\n')
            if len(lines) > 1:
                for line in lines[:-1]:
                    try:
                        sline = line.decode('ascii', 'ignore').strip()
                        lat, lon = parse_nmea_latlon(sline)
                        if lat is not None:
                            return lat, lon
                    except Exception:
                        pass
                buf = lines[-1]
    return None, None

def send_sos(lat, lon):
    payload = {
        "device_id": DEVICE_ID,
        "timestamp": time.time(),
        "latitude": lat,
        "longitude": lon
    }
    try:
        r = urequests.post(SERVER_URL, data=ujson.dumps(payload), headers={'Content-Type': 'application/json'})
        r.close()
        return True
    except Exception as e:
        print("send failed", e)
        return False

# main loop: detect button press and send SOS
print("Device id:", DEVICE_ID)
while True:
    if sos_btn.value() == 0:  # pressed (if pull-up)
        tnow = time.ticks_ms()
        if tnow - last_press > DEBOUNCE_MS:
            last_press = tnow
            print("SOS pressed")
            led.value(1)
            lat, lon = read_gps_location(timeout=5.0)
            if lat is None:
                print("GPS fix not found - sending without location")
                lat, lon = None, None
            ok = send_sos(lat, lon)
            if ok:
                print("SOS sent")
                # flash LED quickly to confirm
                for _ in range(6):
                    led.value(not led.value()); time.sleep(0.12)
            else:
                # indicate failure slowly
                for _ in range(4):
                    led.value(1); time.sleep(0.5); led.value(0); time.sleep(0.5)
            led.value(0)
    time.sleep(0.05)
