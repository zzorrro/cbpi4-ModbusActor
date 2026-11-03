# -*- coding: utf-8 -*-
import asyncio
import logging
from cbpi.api import *
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException, ConnectionException

logger = logging.getLogger(__name__)

@parameters([
    Property.Text(label="Serial Port", configurable=True, default_value="/dev/ttyUSB0", description="RS485 порт (например, /dev/ttyUSB0)"),
    Property.Number(label="Baudrate", configurable=True, default_value=4800, description="Скорость передачи (обычно 4800, 9600 или 115200)"),
    Property.Number(label="Slave ID", configurable=True, default_value=1, description="Адрес Modbus устройства (1-254)"),
    Property.Number(label="Register Address", configurable=True, default_value=0, description="Адрес регистра (0=OUT0, 1=OUT1, 2=OUT2, 3=OUT3)"),
    Property.Number(label="Max Value", configurable=True, default_value=4095, description="Макс. значение (4095 для 12-бит, 10000 для 16-бит)")
])
class ModbusActor(CBPiActor):

    def __init__(self, cbpi):
        super().__init__(cbpi)
        self.client = None
        self.current_power = 0
        self.is_connected = False
        
        # Читаем настройки из интерфейса
        self.port = self.props.get("Serial Port", "/dev/ttyUSB0")
        self.baudrate = int(self.props.get("Baudrate", 4800))
        self.slave_id = int(self.props.get("Slave ID", 1))
        self.register = int(self.props.get("Register Address", 0))
        self.max_value = int(self.props.get("Max Value", 4095))

    async def start(self):
        """Инициализация подключения при старте системы"""
        try:
            self.client = ModbusSerialClient(
                method='rtu',
                port=self.port,
                baudrate=self.baudrate,
                timeout=1,
                stopbits=1,
                bytesize=8,
                parity='N'
            )
            
            if self.client.connect():
                self.is_connected = True
                logger.info(f"ModbusActor connected to {self.port}")
                self.cbpi.notify("ModbusActor", f"Connected to {self.port}", NotificationType.SUCCESS)
            else:
                self.is_connected = False
                logger.error(f"Failed to connect to {self.port}")
                self.cbpi.notify("ModbusActor", f"Failed to connect to {self.port}", NotificationType.ERROR)
        except Exception as e:
            self.is_connected = False
            logger.error(f"ModbusActor start error: {e}")
            self.cbpi.notify("ModbusActor", f"Start error: {str(e)}", NotificationType.ERROR)

    async def stop(self):
        """Безопасное отключение при остановке"""
        await self.set_power(0)
        if self.client:
            try:
                self.client.close()
                self.is_connected = False
            except Exception as e:
                logger.error(f"Error closing Modbus connection: {e}")

    async def set_power(self, power):
        """Главный метод: преобразование % в значение регистра и отправка"""
        self.current_power = power
        
        # Преобразуем 0-100% в диапазон регистра (например, 0-4095)
        modbus_value = int((power / 100.0) * self.max_value)
        modbus_value = max(0, min(modbus_value, self.max_value)) # Защита от выхода за границы
        
        logger.debug(f"ModbusActor: power={power}% -> register value={modbus_value}")
        
        if self.client and self.is_connected:
            try:
                result = self.client.write_register(
                    address=self.register,
                    value=modbus_value,
                    slave=self.slave_id
                )
                
                if result.isError():
                    logger.error(f"Modbus write error: {result}")
                    self.cbpi.notify("ModbusActor", "Write error", NotificationType.ERROR)
                    await self.set_power(0) # Безопасность: выключаем при ошибке
            except (ModbusException, ConnectionException) as e:
                logger.error(f"Modbus connection lost: {e}")
                self.is_connected = False
                self.cbpi.notify("ModbusActor", "Connection lost", NotificationType.ERROR)
                await self.set_power(0) # Безопасность: выключаем при обрыве связи
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                await self.set_power(0)
        else:
            logger.warning("ModbusActor not connected")

    async def on(self, power=0):
        """Включение на полную мощность"""
        logger.info("ModbusActor: turning ON (100%)")
        await self.set_power(100)

    async def off(self):
        """Выключение"""
        logger.info("ModbusActor: turning OFF (0%)")
        await self.set_power(0)
    
    async def run(self):
        """Пустой метод, требуется интерфейсом CBPiActor"""
        pass


def setup(cbpi):
    """Регистрация плагина в системе"""
    cbpi.plugin.register("ModbusActor", ModbusActor)
    logger.info("ModbusActor plugin registered successfully")