import json
import logging
import asyncio
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

class SpooferMQTTClient:
    def __init__(self, config):
        self.config = config
        
        mqtt_config = config.get('mqtt', {})
        self.broker = mqtt_config.get('broker', 'localhost')
        self.port = mqtt_config.get('port', 1883)
        self.username = mqtt_config.get('username')
        self.password = mqtt_config.get('password')
        self.client_id = mqtt_config.get('client_id', 'omnibattery_bridge_spoofer')
        
        # Virtual Hoymiles settings
        server_config = config.get('server', {})
        self.serial_number = server_config.get('virtual_serial_number', 'MSA-280024341346')
        
        # User mapped topics
        self.topics = config.get('topics', {})
        self.topic_map = self._build_topic_map()
        
        self.client = mqtt.Client(client_id=self.client_id)
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
            
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        # Internal state to combine before publishing MS-A2 payload
        self.current_state = {
            "bat_p": 0.0,
            "soc": 0.0,
            "power_ctrl": 0,
            "ems_mode": "general"
        }

    def _build_topic_map(self):
        """Map topics to state store keys"""
        mapping = {}
        for category, sensors in self.topics.items():
            for sensor_name, topic in sensors.items():
                mapping[topic] = {
                    'category': category,
                    'sensor': sensor_name
                }
        return mapping

    def start(self):
        logger.info(f"Connecting to MQTT Broker at {self.broker}:{self.port}...")
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def publish_discovery(self):
        """Publish Home Assistant MQTT Discovery payloads for the fake Hoymiles device"""
        logger.info(f"Publishing MQTT Discovery payloads for device {self.serial_number}...")
        
        device_info = {
            "identifiers": [self.serial_number],
            "name": f"Hoymiles {self.serial_number}",
            "manufacturer": "Hoymiles",
            "model": "MS-A2"
        }
        
        state_topic = f"homeassistant/sensor/{self.serial_number}/quick/state"
        
        # 1. Sensor: Battery Power
        bat_p_config = {
            "name": "Battery Power",
            "state_topic": state_topic,
            "value_template": "{{ value_json.bat_p }}",
            "unique_id": f"{self.serial_number}_bat_p",
            "device_class": "power",
            "unit_of_measurement": "W",
            "device": device_info
        }
        self.client.publish(f"homeassistant/sensor/{self.serial_number}/bat_p/config", json.dumps(bat_p_config), retain=True)

        # 2. Sensor: SOC
        soc_config = {
            "name": "Battery SOC",
            "state_topic": state_topic,
            "value_template": "{{ value_json.soc }}",
            "unique_id": f"{self.serial_number}_soc",
            "device_class": "battery",
            "unit_of_measurement": "%",
            "device": device_info
        }
        self.client.publish(f"homeassistant/sensor/{self.serial_number}/soc/config", json.dumps(soc_config), retain=True)
        
        # 3. Number: Power Control (so Omnibattery can send commands)
        power_ctrl_config = {
            "name": "Power Control",
            "state_topic": state_topic,
            "command_topic": f"homeassistant/number/{self.serial_number}/power_ctrl/set",
            "value_template": "{{ value_json.power_ctrl }}",
            "unique_id": f"{self.serial_number}_power_ctrl",
            "min": -5000,
            "max": 5000,
            "step": 1,
            "unit_of_measurement": "W",
            "device": device_info
        }
        self.client.publish(f"homeassistant/number/{self.serial_number}/power_ctrl/config", json.dumps(power_ctrl_config), retain=True)
        
        # 4. Select: EMS Mode
        ems_mode_config = {
            "name": "EMS Mode",
            "state_topic": state_topic,
            "command_topic": f"homeassistant/select/{self.serial_number}/ems_mode/set",
            "value_template": "{{ value_json.ems_mode }}",
            "unique_id": f"{self.serial_number}_ems_mode",
            "options": ["general", "mqtt_ctrl"],
            "device": device_info
        }
        self.client.publish(f"homeassistant/select/{self.serial_number}/ems_mode/config", json.dumps(ems_mode_config), retain=True)

        # Publish initial state
        self._publish_state()

    def _publish_state(self):
        """Publish the current state to the MS-A2 state topic"""
        state_topic = f"homeassistant/sensor/{self.serial_number}/quick/state"
        payload = json.dumps(self.current_state)
        self.client.publish(state_topic, payload, retain=False)
        logger.debug(f"Published fake MS-A2 state: {payload}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT Broker!")
            self.publish_discovery()
            
            # Subscribe to the user's mapped topics
            for topic in self.topic_map.keys():
                logger.info(f"Subscribing to mapped topic: {topic}")
                self.client.subscribe(topic)
                
            # Subscribe to command topics so we can echo state back
            self.client.subscribe(f"homeassistant/number/{self.serial_number}/power_ctrl/set")
            self.client.subscribe(f"homeassistant/select/{self.serial_number}/ems_mode/set")
        else:
            logger.error(f"Failed to connect, return code {rc}")

    def on_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected from MQTT Broker with result code: {rc}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        # Handle commands from Omnibattery
        if topic == f"homeassistant/number/{self.serial_number}/power_ctrl/set":
            try:
                self.current_state["power_ctrl"] = float(payload)
                self._publish_state()
            except:
                pass
            return
            
        if topic == f"homeassistant/select/{self.serial_number}/ems_mode/set":
            self.current_state["ems_mode"] = payload
            self._publish_state()
            return
        
        # Handle incoming data from user's sensors
        try:
            try:
                data = json.loads(payload)
                value = data.get('value', payload) if isinstance(data, dict) else payload
            except json.JSONDecodeError:
                value = payload
                
            value = float(value)
            
            if topic in self.topic_map:
                map_info = self.topic_map[topic]
                category = map_info['category']
                sensor = map_info['sensor']
                
                state_changed = False
                
                # Map to MS-A2 variables
                if category == 'battery' and sensor == 'power':
                    self.current_state['bat_p'] = value
                    state_changed = True
                elif category == 'battery' and sensor == 'soc':
                    self.current_state['soc'] = value
                    state_changed = True
                    
                if state_changed:
                    self._publish_state()
        
        except ValueError:
            pass
