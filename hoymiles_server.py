import asyncio
import logging
import struct

logger = logging.getLogger(__name__)

class HoymilesEmulatorServer:
    def __init__(self, config, state_store):
        self.config = config
        self.state_store = state_store
        
        server_config = config.get('server', {})
        self.host = server_config.get('host', '0.0.0.0')
        self.port = server_config.get('port', 10081)
        self.serial_number = server_config.get('virtual_serial_number', 'MSA-000000000000')

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        logger.info(f"Accepted connection from {addr}")
        
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                
                logger.debug(f"Received {len(data)} bytes from {addr}")
                
                # Here we would normally use the protobuf definitions from hoymiles-wifi
                # to decode the incoming request and determine what Omnibattery is asking for.
                # For this template, we will log the request and send a dummy response or 
                # a basic simulated payload if we recognize a common health check.
                
                response = self._generate_response(data)
                
                if response:
                    writer.write(response)
                    await writer.drain()
                    logger.debug(f"Sent {len(response)} bytes to {addr}")
                    
        except Exception as e:
            logger.error(f"Error handling client {addr}: {e}")
        finally:
            logger.info(f"Closing connection from {addr}")
            writer.close()
            await writer.wait_closed()

    def _generate_response(self, request_data):
        """
        Generate a fake Hoymiles protocol response.
        In a real scenario, this uses the state_store to populate protobuf structures.
        """
        # Example of using the state store:
        battery_soc = self.state_store.get('battery', {}).get('soc', 0)
        battery_power = self.state_store.get('battery', {}).get('power', 0)
        
        logger.info(f"Current State - SoC: {battery_soc}%, Power: {battery_power}W")
        
        # We return a dummy byte array to keep the connection alive.
        # This needs to be replaced with actual hoymiles-wifi protobuf encoding.
        # Format usually involves a header, payload length, payload (protobuf), and CRC.
        # For now, returning None or a basic ACK to prevent crashes if it expects valid protocol.
        return b'\xaa\x55\x00\x00' # Dummy magic bytes

    async def start_server(self):
        server = await asyncio.start_server(
            self.handle_client, self.host, self.port)

        addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
        logger.info(f"Serving Hoymiles emulator on {addrs} with Serial {self.serial_number}")

        async with server:
            await server.serve_forever()
