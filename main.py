import os
import yaml
import time
import logging

from mqtt_client import SpooferMQTTClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OmnibatteryBridge")

def load_config(config_path="config.yaml"):
    ha_config_path = "/data/options.json"
    
    if os.path.exists(ha_config_path):
        logger.info(f"Loading Home Assistant Add-on config from {ha_config_path}")
        import json
        with open(ha_config_path, 'r') as f:
            return json.load(f)
            
    if os.path.exists(config_path):
        logger.info(f"Loading local config from {config_path}")
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
            
    logger.error("No configuration file found! Exiting.")
    exit(1)

def main():
    logger.info("Starting Omnibattery Hoymiles MQTT Discovery Spoofer...")
    config = load_config()
    
    mqtt_client = SpooferMQTTClient(config)
    mqtt_client.start()
    
    try:
        while True:
            # Mantener vivo el hilo principal
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        mqtt_client.stop()
        logger.info("Bridge stopped.")

if __name__ == "__main__":
    main()
