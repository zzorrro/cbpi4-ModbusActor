from setuptools import setup, find_packages

setup(
    name='cbpi4-ModbusActor',
    version='1.0.2',
    description='CBPi4 Actor for RS485 Modbus RTU (0-10V) control',
    author='Sammy Brewery',
    url='https://github.com/zzorrro/cbpi4-ModbusActor',
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'pymodbus>=3.0.0',
        'pyserial>=3.5'  # <-- ДОБАВЛЕНО: критически важно для работы с /dev/ttyUSB*
    ],
    entry_points={
        'cbpi4.actor': [
            'ModbusActor = cbpi4_ModbusActor:ModbusActor',
        ],
    },
)
