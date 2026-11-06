import asyncio
import logging
from cbpi.api import CBPiActor, Property, parameters

logger = logging.getLogger(__name__)

try:
    from pymodbus.client import ModbusSerialClient
except ImportError:
    logger.error("pymodbus not installed. Please run: pip install pymodbus>=3.0.0")
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
        """Инициализация при запуске CBPi4"""
        try:
            self.serial_port = self.props.get("Serial Port", "/dev/ttyUSB0")
            self.baudrate = int(self.props.get("Baudrate", 4800))
            self.slave_id = int(self.props.get("Slave ID", 1))
            self.register = int(self.props.get("Register Address", 0))
            self.max_value = int(self.props.get("Max Value", 4095))

            if ModbusSerialClient is None:
                logger.error("Cannot initialize Modbus: pymodbus library is missing")
                return

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
                logger.error(f"ModbusActor {self.id} failed to connect to {self.serial_port}")
                
        except Exception as e:
            logger.error(f"Error initializing ModbusActor {self.id}: {e}")

    async def on(self, power=None):
        """Включение актора"""
        if power is not None:
            await self.set_power(power)
        else:
            await self.set_power(100)
        self.state = True
        logger.info(f"ModbusActor {self.id} turned ON")

    async def off(self):
        """Выключение актора"""
        await self.set_power(0)
        self.state = False
        logger.info(f"ModbusActor {self.id} turned OFF")

    async def set_power(self, power):
        """Установка мощности (0-100%)"""
        self.power = int(power)
        if self.power < 0:
            self.power = 0
        if self.power > 100:
            self.power = 100

        if self.client and self.client.connected:
            # Конвертируем процент в значение регистра
            register_value = int((self.power / 100.0) * self.max_value)
            try:
                response = self.client.write_register(self.register, register_value, slave=self.slave_id)
                if response.isError():
                    logger.error(f"Modbus write error for actor {self.id}")
                else:
                    logger.debug(f"ModbusActor {self.id}: Set power {self.power}% -> Register value {register_value}")
            except Exception as e:
                logger.error(f"Modbus write exception for actor {self.id}: {e}")
        
        # Обязательно сообщаем CBPi4 об обновлении мощности для интерфейса
        await self.cbpi.actor.actor_update(self.id, self.power)

    def get_state(self):
        """Получение состояния актора"""
        return self.state

    async def run(self):
        """Фоновый цикл (обязателен для CBPiActor)"""
        while self.running:
            await asyncio.sleep(1)


def setup(cbpi):
    """Регистрация плагина при старте CBPi4"""
    cbpi.plugin.register("ModbusActor", ModbusActor)
    logger.info("ModbusActor plugin loaded")
