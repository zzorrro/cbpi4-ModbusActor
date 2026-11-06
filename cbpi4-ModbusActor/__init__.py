import asyncio
import logging
from cbpi.api import CBPiActor, Property, parameters

logger = logging.getLogger(__name__)

try:
    from pymodbus.client import ModbusSerialClient
except ImportError:
    logger.error("pymodbus not installed.")
    ModbusSerialClient = None

@parameters([
    Property.Text(label="Serial Port", configurable=True, default_value="/dev/ttyUSB0", description="Serial port (e.g., /dev/ttyUSB0)"),
    Property.Number(label="Baudrate", configurable=True, default_value=4800, description="Baudrate (4800, 9600, 19200, etc.)"),
    Property.Number(label="Slave ID", configurable=True, default_value=1, description="Modbus Slave ID (1-254)"),
    Property.Number(label="Register Address", configurable=True, default_value=0, description="Register address to write to"),
    Property.Number(label="Max Value", configurable=True, default_value=4095, description="Max value for 100% power (e.g., 4095 for 12-bit)"),
])
class ModbusActor(CBPiActor):

    def __init__(self, cbpi, id, props):
        super(ModbusActor, self).__init__(cbpi, id, props)
        self.client = None
        self.power = 0
        self.state = False

    async def on_start(self):
        """Инициализация. Закрываем старый порт, если он был, чтобы избежать Exclusive Lock."""
        try:
            self.serial_port = self.props.get("Serial Port", "/dev/ttyUSB0")
            self.baudrate = int(self.props.get("Baudrate", 4800))
            self.slave_id = int(self.props.get("Slave ID", 1))
            self.register = int(self.props.get("Register Address", 0))
            self.max_value = int(self.props.get("Max Value", 4095))

            if ModbusSerialClient is None:
                logger.error("Cannot initialize Modbus: pymodbus library is missing")
                return

            # КРИТИЧНО: Закрываем предыдущее подключение, если оно было
            if self.client is not None:
                try:
                    self.client.close()
                except Exception:
                    pass

            await asyncio.sleep(0.2) # Даем ОС время освободить порт

            self.client = ModbusSerialClient(
                port=self.serial_port,
                baudrate=self.baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1
            )
            
            if self.client.connect():
                logger.info(f"ModbusActor {self.id} connected to {self.serial_port}")
            else:
                logger.warning(f"ModbusActor {self.id} could not connect to {self.serial_port}")
                
        except Exception as e:
            logger.error(f"Error initializing ModbusActor {self.id}: {e}")

    async def on(self, power=None):
        if power is not None:
            await self.set_power(power)
        else:
            await self.set_power(100)
        self.state = True

    async def off(self):
        await self.set_power(0)
        self.state = False

    async def set_power(self, power):
        self.power = int(power)
        if self.power < 0: self.power = 0
        if self.power > 100: self.power = 100

        # Пытаемся переподключиться, если связь оборвалась
        if self.client is None or not self.client.connected:
            try:
                if self.client: self.client.close()
                self.client = ModbusSerialClient(
                    port=self.serial_port, baudrate=self.baudrate, bytesize=8, parity='N', stopbits=1, timeout=1
                )
                self.client.connect()
            except Exception as e:
                logger.debug(f"Reconnection failed: {e}")

        if self.client and self.client.connected:
            register_value = int((self.power / 100.0) * self.max_value)
            try:
                response = self.client.write_register(self.register, register_value, slave=self.slave_id)
                if response.isError():
                    logger.debug(f"Modbus write error (Device may be unplugged)")
                else:
                    logger.info(f"ModbusActor {self.id}: Power {self.power}% -> Register {register_value}")
            except Exception as e:
                logger.debug(f"Modbus write exception: {e}")
        
        await self.cbpi.actor.actor_update(self.id, self.power)

    def get_state(self):
        return self.state

    async def run(self):
        while self.running:
            await asyncio.sleep(1)

    async def on_stop(self):
        """Корректное закрытие порта при остановке"""
        if self.client:
            try:
                self.client.close()
            except:
                pass
            logger.info(f"ModbusActor {self.id} stopped and port closed")


def setup(cbpi):
    cbpi.plugin.register("ModbusActor", ModbusActor)
    logger.info("ModbusActor plugin loaded")
