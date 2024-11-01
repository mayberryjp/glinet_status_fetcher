import requests
import paho.mqtt.client as mqtt
import logging
import json
import re
import logging
import time
import os
from random import randrange
import datetime

from const import IS_CONTAINER, VERSION, SLEEP_INTERVAL, ENTITIES

# Suppress only the single InsecureRequestWarning from urllib3 needed
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)



if (IS_CONTAINER):
    GLINET_HOST = os.getenv("GLINET_HOST","")
    GLINET_PASSWORD=os.getenv("GLINET_PASSWORD","")
    GLINET_DEVICE=os.getenv("GLINET_DEVICE","hiace")
    MQTT_HOST = os.getenv("MQTT_HOST","")
    MQTT_PASSWORD=os.getenv("MQTT_PASSWORD","")
    MQTT_USERNAME=os.getenv("MQTT_USERNAME","")   

class GLInetSensor:
    def __init__(self, name_constant):
        name_replace=name_constant
        name_object=ENTITIES[name_constant]
        self.name = f"glinet_{name_replace}"
        self.device_class = name_object['type'],
        self.unit_of_measurement = name_object['unit'],
        test = name_object.get('attribute')
        if (test != None):
           self.state_class = name_object['attribute']
        else:
            self.state_class = "measurement"
        self.state_topic = f"homeassistant/sensor/glinet_{GLINET_DEVICE}_{name_replace}/state"
        self.unique_id = f"glinet_{name_replace}"
        self.device = {
            "identifiers": [f"glinet_{GLINET_DEVICE}_{name_replace}"][0],
            "name": f"GLInet {name_replace} for {GLINET_DEVICE}",
        }

    def to_json(self):
        return {
            "name": self.name,
            "device_class": self.device_class[0],
            "unit_of_measurement": self.unit_of_measurement[0],
            "state_class": self.state_class,
            "state_topic": self.state_topic,
            "unique_id": self.unique_id,
            "device": self.device
        }


def initialize():
    logger = logging.getLogger(__name__)
    logger.info(f"Initialization starting...")
    print("Initialization starting...")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USERNAME,MQTT_PASSWORD)


    try:
      client.connect(MQTT_HOST, 1883)
    except Exception as e:
        print("Error connecting to MQTT Broker: " + str(e))

    client.loop_start()

    for entity in ENTITIES:
        glinet_sensor=GLInetSensor(entity)
        # Convert dictionary to JSON string
        serialized_message = json.dumps(glinet_sensor.to_json())
        print(f"Sending sensor -> {serialized_message}")
        logger.info(f"Sending sensor -> {serialized_message}")
        print(f"entity: homeassistant/sensor/glinet_{entity}/config")

        try:
            ret = client.publish(f"homeassistant/sensor/glinet_{GLINET_DEVICE}_{entity}/config", payload=serialized_message, qos=2, retain=True)
            ret.wait_for_publish()
            if ret.rc == mqtt.MQTT_ERR_SUCCESS:
                pass
            else:
                print("Failed to queue message with error code " + str(ret))
        except Exception as e:
            print("Error publishing message: " + str(e))   

    client.loop_stop()        
    try:
        client.disconnect()
    except Exception as e:
        print("Error disconnecting from MQTT Broker: " + str(e))
    logger.info(f"Initialization complete...")
    print("Initialization complete...")

def request_and_publish():

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USERNAME,MQTT_PASSWORD)

    logger = logging.getLogger(__name__)

    # Perform login and save the cookies
    login_url = f"{GLINET_HOST}/cgi-bin/api/router/login"

    headers = {
    #    'Accept': 'application/json, text/javascript, */*; q=0.01',
    #    'Accept-Language': 'en-US,en;q=0.9,ja-JP;q=0.8,ja;q=0.7',
        'Authorization': 'undefined',
        'Connection': 'keep-alive',
    #    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
  #      'Origin': 'http://192.168.8.1',
     #   'Referer': 'http://192.168.8.1/',
     #   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
    }


    data = {
        'pwd': GLINET_PASSWORD
    }

    epoch_time=int(time.time())

    session = requests.Session()
    response = session.post(login_url, headers=headers, data=data, verify=False)

    print(response.json())
    data = response.json()
    token=data['token']


    # Use the token to make the next request and process the response
    info_url = f"{GLINET_HOST}/cgi-bin/api/mcu/get?_=" + str(epoch_time)

    headers = {
      #  'Accept': 'application/json, text/javascript, */*; q=0.01',
       # 'Accept-Language': 'en-US,en;q=0.9,ja-JP;q=0.8,ja;q=0.7',
        'Authorization': token,
        'Connection': 'keep-alive',
        'Cookie': 'Admin-Token=' + token,
        'Referer': GLINET_HOST,
      #  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
    }


    response = session.get(info_url, headers=headers, verify=False)

    data = response.json()

    try:
        client.connect(MQTT_HOST, 1883)
    except Exception as e:
        print("Error connecting to MQTT Broker: " + str(e))

    client.loop_start()

    for entity in ENTITIES:

        value=data[entity]

        print(f"{entity} -> {value}")
        try:
            ret = client.publish(f"homeassistant/sensor/glinet_{GLINET_DEVICE}_{entity}/state", payload=value, qos=2, retain=False)  
            ret.wait_for_publish()
            if ret.rc == mqtt.MQTT_ERR_SUCCESS:
                pass
            else:
                print("Failed to queue message with error code " + str(ret))
        except Exception as e:
            print("Error publishing message: " + str(e))

    client.loop_stop()
    try:
        client.disconnect()
    except Exception as e:
        print("Error disconnecting from MQTT Broker: " + str(e))


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logger.info(f"I am glinet_status_fetcher running version {VERSION}")
    print(f"I am glinet_status_fetcher running version {VERSION}")
    initialize()

    while True:
        request_and_publish()
        logger.info(f"It is {datetime.datetime.now()} .. I am sleeping for {SLEEP_INTERVAL}")
        print(f"It is {datetime.datetime.now()} ... I am sleeping for {SLEEP_INTERVAL}")
        time.sleep(SLEEP_INTERVAL)