#!/bin/python3
import paho.mqtt.client as mqtt
import toml
import requests
import time
import threading
import json
from datetime import datetime
from config import config

# Load TOML mqtt configuration
toml_config = toml.load(config['mqtt_toml_file'])
mqtt_config = toml_config['snips-common']
TASMOTA_URL = "http://{}/cm".format(config['tasmota_host'])

client = mqtt.Client()

# All clock modes
MODE_TIME = 'time'
MODE_RESET = 'reset'
MODE_DATE = 'date'
MODE_INCR = 'increment'

MODE = MODE_TIME

def s_mode(smode):
    global MODE, client
    MODE = smode
    client.publish("clock/state", json.dumps({"mode": MODE, "at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}))

def s_mode_reset():
    s_mode(MODE_RESET)

def s_mode_date():
    s_mode(MODE_DATE)

def s_mode_time():
    s_mode(MODE_TIME)

def s_mode_incr():
    s_mode(MODE_INCR)

# Mqtt callbacks
def on_message(client, userdata, message):
    global MODE
    topic = message.topic

    if topic == 'clock/zero' or topic == 'clock/zeros' or topic == 'clock/zeroes' or topic == 'clock/z':
        s_mode_reset()
        requests.get(TASMOTA_URL, params={'cmnd': 'SerialSend2 r'})
    elif topic == 'clock/clear' or topic == 'clock/reset' or topic == 'clock/rst' or topic == 'clock/clr' or topic == 'clock/cls' or topic == 'clock/r':
        s_mode_reset()
        requests.get(TASMOTA_URL, params={'cmnd': 'SerialSend2 b'})
    elif topic == 'clock/increment' or topic == 'clock/i' or topic == 'clock/inc' or topic == 'clock/incr' or topic == 'clock/add':
        if MODE != MODE_INCR:
            requests.get(TASMOTA_URL, params={'cmnd': 'SerialSend2 b'})

        s_mode_incr()
        requests.get(TASMOTA_URL, params={'cmnd': 'SerialSend2 i'})
    elif topic == 'clock/time' or topic == 'clock/clock' or topic == 'clock/t':
        s_mode_time()
    elif topic == 'clock/date' or topic == 'clock/d':
        s_mode_date()

# Mqtt connect
client.username_pw_set(mqtt_config['mqtt_username'], mqtt_config['mqtt_password'])
client.connect(mqtt_config['mqtt'].split(":")[0], int(mqtt_config['mqtt'].split(":")[1]))

# Mqtt subscribe
client.subscribe("clock/#")
client.on_message = on_message

# Mqtt thread start
mqtt_thread = threading.Thread(target=client.loop_start)
mqtt_thread.start()

# Mqtt publish to configure clock at startup
start_payload = json.dumps({"at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
client.publish("clock/start", start_payload)
client.publish("clock/clear", start_payload)
client.publish("clock/time", start_payload)

# Main loop for timed events
while True:
    if MODE == MODE_TIME:
        current_time = time.strftime('%H%M%S')
        payload = {'cmnd': f'SerialSend2 {current_time}'}
        try:
            requests.get(TASMOTA_URL, params=payload)
        except requests.RequestException as e:
            print(f"Erreur de requête : {e}")
    elif MODE == MODE_DATE:
        current_date = time.strftime('%d%m%y')
        payload = {'cmnd': f'SerialSend2 {current_date}'}
        try:
            requests.get(TASMOTA_URL, params=payload)
        except requests.RequestException as e:
            print(f"Erreur de requête : {e}")
    time.sleep(1)
