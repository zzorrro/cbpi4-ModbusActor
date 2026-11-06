import asyncio
import logging
from cbpi.api import *
from cbpi.api.base import CBPiBase
from cbpi.api.dataclasses import Actor, Props
from pymodbus.client import ModbusSerialClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder

logger = logging.getLogger(__name__)

@parameters([
    Property.Text(label="Serial Port", configurable=True, default_value="/dev/ttyUSB0", description="Serial port (e.g., /dev/ttyUSB0)"),
    Property.Number(label="Baudrate", configurable=True, default_value=4800, description="Baudrate (4800, 9600, 19200, etc.)"),
    Property.Number(label="Slave ID", configurable=True, default_value=1, description="Modbus Slave ID (1-254)"),
    Property.Number(label="Register Address", configurable=True, default_value=0, description="Register address to write to"),
    Property.Number(label="Max Value", configurable=True, default_value=4095, description="Max value for 100% power (e.g., 4095 for 12-bit)"),
])
class ModbusActor(CBPiBase):
    
    def __init__(self, cbpi, id, *args, **kwargs):
        super().__init__(cbpi, id, *args, **kwargs)
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
            
            logger.info(f"ModbusActor {self.id} initialized: {self.serial_port}@{self.baudrate}, Slave={self.slave_id}, Register={self.register}, MaxValue={self.max_value}")
            
            # Инициализируем Modbus клиент
            self.client = ModbusSerialClient(
                port=self.serial_port,
                baudrate=self.baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1
            )
            
            if self.client.connect():
                logger.info(f"Modbus client connected to {self.serial_port}")
            else:
                logger.error(f"Failed to connect to Modbus device on {self.serial_port}")
                
        except Exception as e:
            logger.error(f"Error initializing ModbusActor {self.id}: {e}")
    
    async def on_stop(self):
        """Остановка при выключении CBPi4"""
        if self.client:
            self.client.close()
            logger.info(f"ModbusActor {self.id} stopped")
    
    async def on(self):
        """Включение актора (100% мощность)"""
        try:
            if self.client and self.client.connected:
                await self.set_power(100)
                self.state = True
                logger.info(f"ModbusActor {self.id} turned ON")
        except Exception as e:
            logger.error(f"Error turning on ModbusActor {self.id}: {e}")
    
    async def off(self):
        """Выключение актора (0% мощность)"""
        try:
            if self.client and self.client.connected:
                await self.set_power(0)
                self.state = False
                logger.info(f"ModbusActor {self.id} turned OFF")
        except Exception as e:
            logger.error(f"Error turning off ModbusActor {self.id}: {e}")
    
    async def set_power(self, power):
        """Установка мощности (0-100%)"""
        try:
            self.power = float(power)
            # Конвертируем процент в значение регистра
            register_value = int((self.power / 100.0) * self.max_value)
            
            if self.client and self.client.connected:
                # Записываем значение в регистр
                builder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
                builder.add_16bit_int(register_value)
                payload = builder.build()
                
                # Записываем holding register
                result = self.client.write_register(self.register, register_value, slave=self.slave_id)
                
                if result.isError():
                    logger.error(f"Modbus write error for actor {self.id}")
                else:
                    logger.debug(f"ModbusActor {self.id}: Set power {self.power}% -> Register value {register_value}")
                    
        except Exception as e:
            logger.error(f"Error setting power for ModbusActor {self.id}: {e}")
    
    async def get_power(self):
        """Получение текущей мощности"""
        return self.power
    
    def get_state(self):
        """Получение состояния актора"""
        return self.state


def setup(cbpi):
    """Регистрация плагина при старте CBPi4"""
    cbpi.plugin.register("ModbusActor", ModbusActor)
    logger.info("ModbusActor plugin loaded")
