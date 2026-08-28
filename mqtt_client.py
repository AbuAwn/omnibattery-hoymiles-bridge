import json
import logging
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

class BridgeMQTTClient:
    def __init__(self, config, state_store):
        self.config = config
        self.state_store = state_store
        
        mqtt_config = config.get('mqtt', {})
        self.broker = mqtt_config.get('broker', 'localhost')
        self.port = mqtt_config.get('port', 1883)
        self.username = mqtt_config.get('username')
        self.password = mqtt_config.get('password')
        self.client_id = mqtt_config.get('client_id', 'omnibattery_bridge')
        
        self.topics = config.get('topics', {})
        self.topic_map = self._build_topic_map()
        
        self.client = mqtt.Client(client_id=self.client_id)
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
            
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

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

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT Broker!")
            # Subscribe to all configured topics
            for topic in self.topic_map.keys():
                logger.info(f"Subscribing to: {topic}")
                self.client.subscribe(topic)
        else:
            logger.error(f"Failed to connect, return code {rc}")

    def on_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected from MQTT Broker with result code: {rc}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        try:
            # If payload is JSON (e.g. from victron or HA), parse it, otherwise cast to float
            try:
                data = json.loads(payload)
                # Some systems publish {"value": 12.3}
                value = data.get('value', payload) if isinstance(data, dict) else payload
            except json.JSONDecodeError:
                value = payload
                
            value = float(value)
            
            if topic in self.topic_map:
                map_info = self.topic_map[topic]
                category = map_info['category']
                sensor = map_info['sensor']
                
                # Update global state
                if category not in self.state_store:
                    self.state_store[category] = {}
                self.state_store[category][sensor] = value
                
                logger.debug(f"Updated {category}.{sensor} = {value}")
        
        except ValueError:
            logger.warning(f"Could not parse payload '{payload}' from topic '{topic}' as number.")
        except Exception as e:
            logger.error(f"Error processing message on {topic}: {e}")
