import os
import yaml
import time
import logging
import asyncio
import threading

from mqtt_client import BridgeMQTTClient
from hoymiles_server import HoymilesEmulatorServer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OmnibatteryBridge")

# Global state store that the MQTT client writes to and the Hoymiles Server reads from.
# Example: {'battery': {'soc': 100, 'voltage': 51.2}, 'grid': {'power_import': 0}}
STATE_STORE = {}

def load_config(config_path="config.yaml"):
    # If running as Home Assistant add-on, we might want to read options.json instead
    # but for simplicity we assume options are mapped or config.yaml is used.
    # In HA, add-on config is at /data/options.json
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

async def main():
    logger.info("Starting Omnibattery Hoymiles Bridge...")
    config = load_config()
    
    # Initialize MQTT Client
    mqtt_client = BridgeMQTTClient(config, STATE_STORE)
    
    # Start MQTT loop in a separate thread (paho handles its own thread, loop_start)
    mqtt_client.start()
    
    # Initialize and run Hoymiles TCP Emulator Server
    hoymiles_server = HoymilesEmulatorServer(config, STATE_STORE)
    
    try:
        await hoymiles_server.start_server()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        mqtt_client.stop()
        logger.info("Bridge stopped.")

if __name__ == "__main__":
    asyncio.run(main())
