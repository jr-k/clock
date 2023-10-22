#!/bin/python3
import paho.mqtt.client as mqtt
import toml
import requests
import time
import threading
import json
from datetime import datetime
from config import config

topic = config['topic']

# Util functions
def pad_with_zeros(s):
    s = ''.join(filter(str.isdigit, s))
    return s.zfill(6)[:6]

# Load TOML mqtt configuration
toml_config = toml.load(config['mqtt_toml_file'])
mqtt_config = toml_config['snips-common']
TASMOTA_URL = "http://{}/cm".format(config['tasmota_host'])

# Load MQTT client
client = mqtt.Client()

def notify_state():
    global MODE, DISPLAY, config
    client.publish(config['topic'] + "/state", json.dumps({
        "mode": MODE,
        "at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "display": DISPLAY
    }))

# All clock modes and display state
MODE_TIME = 'time'
MODE_RESET = 'reset'
MODE_DATE = 'date'
MODE_INCR = 'increment'
MODE_CUST = 'custom'

MODE = MODE_TIME

def s_display(msg):
    global DISPLAY
    DISPLAY = pad_with_zeros(str(msg))
    print(f'Display: {DISPLAY}')

def s_mode(smode):
    global MODE, DISPLAY, client
    print(f'Mode: {smode}')
    MODE = smode
    notify_state()

def s_mode_reset():
    s_mode(MODE_RESET)

def s_mode_date():
    s_mode(MODE_DATE)

def s_mode_time():
    s_mode(MODE_TIME)

def s_mode_incr():
    s_mode(MODE_INCR)

def s_mode_cust():
    s_mode(MODE_CUST)

# Mqtt callbacks
def on_message(client, userdata, message):
    global MODE, DISPLAY
    fulltopic = message.topic
    topic = '/'.join(fulltopic.split('/')[1:])
    payload = str(message.payload.decode("utf-8"))

    if topic == 'zero' or topic == 'zeros' or topic == 'zeroes' or topic == 'z':
        s_display('000000')
        s_mode_reset()
        requests.get(TASMOTA_URL, params={'cmnd': 'SerialSend2 r'})
    elif topic == 'clear' or topic == 'reset' or topic == 'rst' or topic == 'clr' or topic == 'cls' or topic == 'r':
        s_display('000000')
        s_mode_reset()
        requests.get(TASMOTA_URL, params={'cmnd': 'SerialSend2 b'})
    elif topic == 'increment' or topic == 'i' or topic == 'inc' or topic == 'incr' or topic == 'add':
        if MODE != MODE_INCR:
            s_display('000001')
            requests.get(TASMOTA_URL, params={'cmnd': 'SerialSend2 b'})
        else:
            s_display(int(DISPLAY) + 1)

        s_mode_incr()
        requests.get(TASMOTA_URL, params={'cmnd': 'SerialSend2 i'})
    elif topic == 'time' or topic == 'clock' or topic == 't':
        s_display(time.strftime('%H%M%S'))
        s_mode_time()
    elif topic == 'date' or topic == 'd':
        s_display(time.strftime('%d%m%y'))
        s_mode_date()
    elif topic == 'info' or topic == 'v' elif topic == 'infos':
        notify_state()
    elif topic == 'show' or topic == 'display' or topic == 'set' or topic == 's':
        requests.get(TASMOTA_URL, params={'cmnd': 'SerialSend2 b'})
        s_display(payload)
        s_mode_cust()
        payload = {'cmnd': f'SerialSend2 {DISPLAY}'}
        try:
            requests.get(TASMOTA_URL, params=payload)
        except requests.RequestException as e:
            print(f"Erreur de requête : {e}")

def on_log(client, userdata, level, buf):
    if level == mqtt.MQTT_LOG_ERR:
        print("Error:", buf)

# Mqtt connect
client.username_pw_set(mqtt_config['mqtt_username'], mqtt_config['mqtt_password'])
client.connect(mqtt_config['mqtt'].split(":")[0], int(mqtt_config['mqtt'].split(":")[1]))

# Mqtt subscribe
client.subscribe(config['topic'] + "/#")
client.on_message = on_message
client.on_log = on_log

# Mqtt thread start
mqtt_thread = threading.Thread(target=client.loop_start)
mqtt_thread.start()

# Startup configuration
start_payload = json.dumps({"at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
client.publish(config['topic'] + "/start", start_payload)
client.publish(config['topic'] + "/clear", start_payload)
client.publish(config['topic'] + "/time", start_payload)
s_display(0)

# Main loop for timed events
while True:
    if MODE == MODE_TIME:
        current_time = time.strftime('%H%M%S')
        s_display(current_time)
        payload = {'cmnd': f'SerialSend2 {current_time}'}
        try:
            requests.get(TASMOTA_URL, params=payload)
        except requests.RequestException as e:
            print(f"Erreur de requête : {e}")
    elif MODE == MODE_DATE:
        current_date = time.strftime('%d%m%y')
        s_display(current_date)
        payload = {'cmnd': f'SerialSend2 {current_date}'}
        try:
            requests.get(TASMOTA_URL, params=payload)
        except requests.RequestException as e:
            print(f"Erreur de requête : {e}")
    time.sleep(1)
