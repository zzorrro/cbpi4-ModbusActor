from setuptools import setup, find_packages

setup(
    name='cbpi4-ModbusActor',
    version='1.0.3',
    description='CBPi4 Actor for RS485 Modbus RTU (0-10V) control',
    author='Sammy Brewery',
    url='https://github.com/zzorrro/cbpi4-ModbusActor',
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'pymodbus>=3.0.0',
        'pyserial>=3.5'
    ]
    # Убрали entry_points, так как cbpi.plugin.register в __init__.py достаточно
)
