import board
from digitalio import DigitalInOut, Direction, Pull
import adafruit_dps310
import adafruit_ahtx0
import ipaddress
import ssl
import wifi
import time
import json
import socketpool
import adafruit_requests
import displayio
import terminalio
from adafruit_display_text import label
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_bitmap_font import bitmap_font
from adafruit_funhouse import FunHouse
try:
    from secrets import secrets
except ImportError:
    print(
        """WiFi settings are kept in secrets.py, please add them there!
the secrets dictionary must contain 'ssid' and 'password' at a minimum"""
    )
    raise

LIGHT_TOGGLE_PATH = ("/api/services/light/toggle")
LIGHT_ON_PATH = ("/api/services/light/turn_on")
OFFICE_LIGHT = "<THE ENTITY ID OF THE LIGHT YOU WANT TO CONTROL>"

# Initalize the funhouse library to use the slider and buttons

funhouse = FunHouse()
display = board.DISPLAY

# load the font and create the main displayio group called splash
lfont = bitmap_font.load_font("/fonts/BebasNeueRegular-41.bdf")
lfont.load_glyphs(b'offn1234567890')
color = 0xffff00
splash = displayio.Group(max_size=10) # The Main Display Group

# create a group to hold the text to display in the popup status window
text_group = displayio.Group()
# create a rounded rectangle as a pop up window
roundrect = RoundRect(75, 70, 90, 90, 10, fill=0x0, outline=0xFF00FF, stroke=3)
notice_val_text = label.Label(lfont, color=color,max_glyphs=3)
notice_val_text.x = 105
notice_val_text.y = 115
text_group.append(roundrect)
text_group.append(notice_val_text)

# load the background image and add it to the background group

bg_bitmap_file = open("/ha.bmp", "rb") 
bg_bitmap = displayio.OnDiskBitmap(bg_bitmap_file)
bg_grid = displayio.TileGrid(bg_bitmap, pixel_shader=displayio.ColorConverter())
bg_group = displayio.Group(max_size=5)
bg_group.append(bg_grid)

# add the background group to the main group - not the text group because we will show and hide that later.

splash.append(bg_group)
display.show(splash)

# set up the headers for HA authorization - the bearer token must be added to the secrets.py file - see: https://www.home-assistant.io/docs/authentication/

headers = {"Authorization": "Bearer " + secrets["bearer_token"], "content-type": "application/json"}

# method for toggling lights - vs on and off specific methods
# pass the entity ID of the light to control
# this method returns the state of the light after it's toggled (on or off)
def toggle_light(entity_id):
	data = {}
	data['entity_id'] = entity_id
	# print(data)
	toggle_post = requests.post(secrets["ha_url"] + LIGHT_TOGGLE_PATH, headers=headers, json=data)
	json_resp = json.loads(toggle_post.text)
	print("Data received from server:", json_resp)
	print("-" * 40)
	print("State:" + json_resp[0]['state'])
	print("-" * 40)
	return json_resp[0]['state']
	toggle_post.close()

# method of changing the brightness of a light that has that attribute - not all do
# pass the entity ID and the brightness percent 0-100
def brightness(entity_id,bright_pct):
	data = {}
	data['entity_id'] = entity_id
	data['brightness_pct'] = bright_pct
	print(data)
	bright_post = requests.post(secrets["ha_url"] + LIGHT_ON_PATH, headers=headers, json=data)
	json_resp = bright_post.text
	print("Data received from server:", json_resp)
	print("-" * 40)
	bright_post.close()

# create the wifi connection and the requests handler
wifi.radio.connect(secrets["ssid"], secrets["password"])
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

# Iniatlize the last_update variable so we can do non-blocking delays
last_update = time.monotonic()
while True:
	now = time.monotonic()
	if funhouse.peripherals.button_sel:
		try:
			# show the notifier pop up box
			splash.append(text_group)
		except ValueError:
			pass
			# call the toggle function and set the notice value
		notice_val_text.text = toggle_light(OFFICE_LIGHT)
		# set a last updated value so we can hide the pop-up window after a set time
		last_update = now
		
	slider = funhouse.peripherals.slider
	if slider is not None:
		try:
			splash.append(text_group) # show the notifier pop up box
		except ValueError:
			pass
			# call the brightness function and set it to the slider value * 100
		brightness(OFFICE_LIGHT,"%1.0f" %(slider*100))
		notice_val_text.text = "%1.0f" %(slider*100)
		last_update = now
	# check to see if the pop-up has been shown for 2 seconds after the last update and then hide the pop-up and clear out the last value
	if now - last_update > 2:
		try:
			splash.remove(text_group) #hide the pop-up box
			notice_val_text.text = ""
		except ValueError:
			pass