from setuptools import setup, find_packages

setup(
    name='cbpi4-ModbusActor',
    version='1.0.0',
    description='CBPi4 Actor for RS485 Modbus RTU (0-10V) control',
    author='Sammy Brewery',
    packages=find_packages(),
    install_requires=[
        'pymodbus>=3.0.0',
    ],
    entry_points={
        'cbpi4.actor': [
            'ModbusActor = cbpi4_ModbusActor:ModbusActor',
        ],
    },
)