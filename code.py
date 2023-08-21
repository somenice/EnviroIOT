import alarm
import time
import board
import ipaddress
import ssl
import wifi
import socketpool
import adafruit_requests
from secrets import secrets
import adafruit_scd4x
import adafruit_bmp280
from adafruit_lc709203f import LC709203F
import terminalio
from adafruit_display_text import label
import displayio
import adafruit_imageload
import adafruit_il0373
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
from adafruit_bitmap_font import bitmap_font

spi = board.SPI()  # Uses SCK and MOSI
ecs = board.D9
dc = board.D10
rst = None    # set to None for FeatherWing/Shield
busy = None

displayio.release_displays()
display_bus = displayio.FourWire(spi, command=dc, chip_select=ecs, reset=rst, baudrate=1000000)

time.sleep(1)  # Wait a bit
display = adafruit_il0373.IL0373(display_bus, width=128, height=296, border=0x000000, swap_rams=False, busy_pin=busy, rotation=180, highlight_color=0xFFFFFF, black_bits_inverted=False, color_bits_inverted=False, grayscale=True, refresh_time=10)

i2c = board.STEMMA_I2C()
time.sleep(1)  # Wait a bit

bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
# Set fixed altitude otherwise set the the local bmp280.sea_level_pressure
bmp280.altitude = 695.0
bmp280.mode = adafruit_bmp280.MODE_FORCE
bmp280.overscan_pressure = adafruit_bmp280.OVERSCAN_X2
# bmp280.t_standby = STANDBY_TC_0_5
batt = LC709203F(i2c)
wifi.radio.enabled = True
print("My MAC addr:", [hex(i) for i in wifi.radio.mac_address])
wifi.radio.stop_scanning_networks()
try:
    wifi.radio.connect(secrets["ssid"], secrets["password"])
except:
    print("Cannot connect to WIFI ")
    pass
print("Connected to %s!"%secrets["ssid"])
print("My IP address is", wifi.radio.ipv4_address)
pool = socketpool.SocketPool(wifi.radio)
try:
    requests = adafruit_requests.Session(pool, ssl.create_default_context())
except:
    print("Cannot requests")

WEATHER_URL = "https://weather.gc.ca/rss/city/bc-86_e.xml"

try:
    response = requests.get(WEATHER_URL, timeout=5)
    time.sleep(1)
    forecast = [line.lstrip("  <title>").rstrip("</title>") for line in response.text.split("\n") if (line.startswith("  <title>")) or (line.startswith("    <![CDATA"))]
    print(forecast)
    try:
        outside_humidity = forecast[2].split("Humidity:</b> ")
        outside_humidity = outside_humidity[1][:3].strip()
        print(outside_humidity + "%")
    except:
        outside_humidity = forecast[1].split("Humidity:</b> ")
        outside_humidity = outside_humidity[1][:3].strip()
        print("cannot get humidity")
    try:
        outside_temp = forecast[2].split("Temperature:</b> ")
        print(outside_temp)
        outside_temp = outside_temp[1][:4].strip()
        print(outside_temp + "°C")
    except:
        outside_temp = forecast[1].split("Temperature:</b> ")
        print(outside_temp)
        outside_temp = outside_temp[1][:4].strip()
        print("Cannot get external temp")
except:
    print("Cannot fetch weather ")
    pass

scd4x = adafruit_scd4x.SCD4X(i2c)
scd4x.altitude = 695
scd4x.temperature_offset = 3.0
# scd4x.force_calibration(440)
# scd4x.factory_reset()
# scd4x.persist_settings()
time.sleep(1)  # Wait a bit
scd4x.start_periodic_measurement()

aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]
io = IO_HTTP(aio_username, aio_key, requests)

font = bitmap_font.load_font("/Helvetica-Bold-16.bdf")
font2 = bitmap_font.load_font("/IBMPlexMono-Medium-24.bdf")

TEMP_label = label.Label(font, text="TEMP", color=0x000000, scale=2)
TEMP_label.x = 28
TEMP_label.y = 15

OUTDOOR_TEMP_label = label.Label(font2, text="OUTDOOR TEMP", color=0x000000, scale=1)
OUTDOOR_TEMP_label.x = 40
OUTDOOR_TEMP_label.y = 42

HUM_label = label.Label(font, text="HUM", color=0x000000, scale=2)
HUM_label.x = 30
HUM_label.y = 75

OUTDOOR_HUM_label = label.Label(font2, text="OUTDOOR HUM", color=0x000000, scale=1)
OUTDOOR_HUM_label.x = 45
OUTDOOR_HUM_label.y = 102

C02_label = label.Label(font2, text="C02 ", color=0x000000, scale=2)
C02_label.x = 5
C02_label.y = 160

PRES_label = label.Label(font2, text="PRES", color=0x000000, scale=1)
PRES_label.x = 15
PRES_label.y = 225

ALT_label = label.Label(font2, text="ALT", color=0x000000, scale=1)
ALT_label.x = 15
ALT_label.y = 250

BATT_label = label.Label(font2, text="BATT", color=0x000000, scale=1)
BATT_label.x = 50
BATT_label.y = 280

bitmap = displayio.Bitmap(display.width, display.height, 4)
palette = displayio.Palette(4)
palette[0] = 0x000000
palette[1] = 0xFFFFFF #b'\xff\xff\xff'
palette[2] = 0x333333
palette[3] = 0x666666

# displayio.Palette.make_transparent(palette[2])

# Create a TileGrid using the Bitmap and Palette
tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)

# # Create a display group for our screen objects
g = displayio.Group()
g.append(tile_grid)

bitmap.fill(1)
g.append(C02_label)
g.append(TEMP_label)
g.append(OUTDOOR_TEMP_label)
g.append(HUM_label)
g.append(OUTDOOR_HUM_label)
g.append(PRES_label)
g.append(ALT_label)
g.append(BATT_label)

sprite_sheet, palette = adafruit_imageload.load("/spritesheet.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette)
# Example using displayio.OnDiskBitmap() vs adafruit_imageload()
# f = open("/top.bmp", "rb")
# pic = displayio.OnDiskBitmap(f)
# t = displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
# t.transpose_xy = True
# g.append(t)
sprite_bat = displayio.TileGrid(sprite_sheet, pixel_shader=palette, width = 1, height = 1, tile_width = 16, tile_height = 16)
sprite_temp = displayio.TileGrid(sprite_sheet, pixel_shader=palette, width = 1, height = 1, tile_width = 16, tile_height = 16)
sprite_humid = displayio.TileGrid(sprite_sheet, pixel_shader=palette, width = 1, height = 1, tile_width = 16, tile_height = 16)
# sprite.transpose_xy = True

sprite_bat.x = 2
sprite_bat.y = 132
if (batt.cell_percent > 95):
    sprite_bat[0] = 4
elif (batt.cell_percent < 96) and (batt.cell_percent > 50):
    sprite_bat[0] = 3
elif (batt.cell_percent < 51) and (batt.cell_percent > 35):
    sprite_bat[0] = 2
elif (batt.cell_percent < 36) and (batt.cell_percent > 5):
    sprite_bat[0] = 1
else:
    sprite_bat[0] = 0

sprite_temp.x = -2
sprite_temp.y = 6
if (bmp280.temperature > 25):
    sprite_temp[0] = 9
elif (bmp280.temperature < 26) and (bmp280.temperature > 20):
    sprite_temp[0] = 8
elif (bmp280.temperature < 21) and (bmp280.temperature > 18):
    sprite_temp[0] = 7
elif (bmp280.temperature < 19) and (bmp280.temperature > 15):
    sprite_temp[0] = 6
else:
    sprite_temp[0] = 5

sprite_humid.x = -2
sprite_humid.y = 38
if (scd4x.relative_humidity > 75):
    sprite_humid[0] = 14
elif (scd4x.relative_humidity < 76) and (scd4x.relative_humidity > 50):
    sprite_humid[0] = 13
elif (scd4x.relative_humidity < 51) and (scd4x.relative_humidity > 35):
    sprite_humid[0] = 12
elif (scd4x.relative_humidity < 36) and (scd4x.relative_humidity > 20):
    sprite_humid[0] = 11
else:
    sprite_humid[0] = 10

gfx = displayio.Group(scale=2)
gfx.append(sprite_bat)
gfx.append(sprite_temp)
gfx.append(sprite_humid)

comp = displayio.Group()
comp.append(g)
comp.append(gfx)

# # Place the display group on the screen
# display.show(comp) 
display.root_group = comp

ambient_pressure = bmp280.pressure
scd4x.set_ambient_pressure(int(ambient_pressure))

def send_multiple(self, feeds_and_data: List, timeout: int = 3, is_group: bool = False):
    pass


while True:
    bmp280.altitude = 695.0
    print("bmp280 Temperature: %0.1f°C" % bmp280.temperature)
    TEMP_label.text = "%0.1f°C" % bmp280.temperature
    OUTDOOR_TEMP_label.text = outside_temp + "°C"
    OUTDOOR_HUM_label.text = outside_humidity + ".0%"
    print("Pressure: %0.1f hPa" % bmp280.pressure)
    PRES_label.text = "%0.1fhPa" % bmp280.pressure
    print("Altitude: %0.2f meters" % bmp280.altitude)
    ALT_label.text = "%0.2fm" % bmp280.altitude
    
    # print("Calculated Sea Level Pressure: %0.1f hPa" % bmp280.p0)
    print()
    print("Battery: %0.3f Volts / %0.1f %%" % (batt.cell_voltage, batt.cell_percent))
    BATT_label.text = "%0.1f%%" % batt.cell_percent
    if scd4x.data_ready:
        print("\nCO2: %d ppm" % scd4x.CO2)
        print(" scd4x Temperature: %0.1f°C" % scd4x.temperature)
        print("Humidity: %0.1f %%" % scd4x.relative_humidity)
        C02_label.text = str(scd4x.CO2)
        bbx, bby, bbwidth, bbh = C02_label.bounding_box
        # print(bbx, bby, bbwidth, bbh)
        C02_label.x = round(display.width / 2 - bbwidth)
        
        HUM_label.text = "%0.1f%%" % scd4x.relative_humidity
        
    # io.publish_multiple([('humidity', scd4x.relative_humidity), ('temperature', bmp280.temperature),('outside-humidity', outside_humidity), ('outside-temperature', outside_temp),('pressure', bmp280.pressure),('co2', scd4x.CO2)])
    
    #Handy MQTT only function io.send_multiple([('humidity', scd4x.relative_humidity), ('temperature', bmp280.temperature),('outside-humidity', outside_humidity), ('outside-temperature', outside_temp),('pressure', bmp280.pressure),('co2', scd4x.CO2)])

    io.send_data('temperature', bmp280.temperature, precision=1)
    time.sleep(3)
    io.send_data('humidity', scd4x.relative_humidity, precision=1)
    time.sleep(3)
    io.send_data('outside-temperature', outside_temp)
    time.sleep(3)
    io.send_data('outside-humidity', outside_humidity)
    time.sleep(3)
    io.send_data('pressure', bmp280.pressure, precision=1)
    time.sleep(3)
    io.send_data('co2', scd4x.CO2)
    print("Data sent!")
    # Refresh the display to have it actually show the image
    # NOTE: Do not refresh eInk displays sooner than 180 seconds
    display.refresh()

    wifi.radio.enabled = False
    bmp280.mode = adafruit_bmp280.MODE_SLEEP
    time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 3600)
    # Exit the program, and then deep sleep until the alarm wakes us.
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)
    # Does not return, so we never get here.
    # time.sleep(300)