########################################
# Este script funciona correctamente enviando un default a las interfaces FastEthernet 0/1 a 0/46 y copiendo la configuración de las interfaces de un 
# archivo de configuración a los switches que se encuentren en el rango de IPs ingresado por el usuario.
########################################



import os
import re
import subprocess
import socket
from netmiko import ConnectHandler
from dotenv import load_dotenv

# Carga las variables de entorno del archivo .env
load_dotenv('pswd.env')

# Constantes de Configuración
USERNAME = os.getenv('SWITCH_USERNAME')
PASSWORD = os.getenv('SWITCH_PASSWORD')
ENABLE_PASSWORD = os.getenv('SWITCH_ENABLE_PASSWORD')
SESSION_LOG = 'netmiko_session.log'

def is_valid_ip(ip):
    try:
        octets = ip.split('.')
        if len(octets) != 4:
            return False
        for octet in octets:
            if not 0 <= int(octet) <= 255:
                return False
        socket.inet_aton(ip)
        return True
    except (socket.error, ValueError):
        return False

socket.setdefaulttimeout(30)

def get_interface_config(filename):
    if not os.path.exists(filename):
        print(f"Archivo no encontrado: {filename}")
        return []

    try:
        with open(filename, 'r', encoding='utf-8') as file:
            data = file.read()
    except (PermissionError, OSError) as e:
        print(f"Error al intentar leer el archivo {filename}: {e}")
        return []

    interfaces = re.findall(r'(interface FastEthernet0/\d{1,2}.*?)(?=interface FastEthernet0/\d{1,2}|$)', data, re.DOTALL)
    config = [interface for interface in interfaces if int(interface.split('/')[1].split()[0]) <= 46]
    return config

def send_config_to_device(connection, config):
    for interface_config in config:
        commands = [cmd.strip() for cmd in interface_config.split('\n') if cmd.strip()]
        try:
            # Ingresa al modo de configuración de la interfaz
            if commands:
                print(f"Enviando comandos para: {commands[0]}")
                connection.send_command_expect(commands[0], expect_string=r'\(config-if\)#')
                for command in commands[1:]:
                    print(f"Enviando comando: {command}")
                    connection.send_command_expect(command, expect_string=r'\(config-if\)#')
        except Exception as e:
            print(f"Error al enviar el comando {command}: {e}")

def run_command(ip_address, config):
    device = {
        'device_type': 'cisco_ios_telnet',
        'ip': ip_address,
        'username': '',
        'password': PASSWORD,
        'secret': ENABLE_PASSWORD,
        'global_delay_factor': 2,  # Aumentar el tiempo de espera
        'session_log': SESSION_LOG,  # Habilitar el registro de sesión
    }

    try:
        response = subprocess.call(['ping', '-n', '2', ip_address], stdout=subprocess.DEVNULL)
        if response != 0:
            print(f"Sw no disponible en {ip_address}")
            return

        connection = ConnectHandler(**device)
        print(f"Conectado a {connection.find_prompt()}")

        connection.enable()
        connection.send_command_expect('configure terminal', expect_string=r'\(config\)#')

        for i in range(1, 47):
            print(f"Enviando comando: default interface FastEthernet 0/{i}")
            connection.send_command_expect(f'default interface FastEthernet 0/{i}', expect_string=r'\(config\)#')

        send_config_to_device(connection, config)

        connection.send_command_expect('end', expect_string=r'#')
        connection.disconnect()

        print(f"Configuración completada en {ip_address}")
    except Exception as e:
        print(f"Error al conectarse a {ip_address}: {e}")

def main():
    directorio_trabajo = os.getcwd()
    print(f"Directorio de trabajo actual: {directorio_trabajo}")

    while True:
        start_ip = input("Enter the starting IP address: ")
        if not is_valid_ip(start_ip):
            print("The entered IP is not valid. Please try again.\n")
            continue

        end_ip_input = input(f"Enter the final IP? or Press [Enter] to use the same starting IP or [C] to go back: {start_ip.rsplit('.', 1)[0]}.")
        if end_ip_input.lower() == "c":
            print("Canceling the execution.")
            return

        end_ip = start_ip if end_ip_input.strip() == "" else f"{start_ip.rsplit('.', 1)[0]}.{end_ip_input}"
        if not is_valid_ip(end_ip):
            print("The entered final IP is not valid. Please try again.\n")
            continue

        start_octets = list(map(int, start_ip.split('.')))
        end_octets = list(map(int, end_ip.split('.')))

        for octet_3 in range(start_octets[2], end_octets[2] + 1):
            for octet_4 in range(start_octets[3], end_octets[3] + 1):
                ip_address = f"{start_octets[0]}.{start_octets[1]}.{octet_3}.{octet_4}"
                filename = f"{directorio_trabajo}\\SW_ACC\\sw{octet_4}.par02.bitfarms.com.ios"
                print(f"Verificando archivo: {filename}")

                if os.path.exists(filename):
                    config = get_interface_config(filename)
                    if config:
                        run_command(ip_address, config)
                    else:
                        print(f"No se encontró configuración en el archivo: {filename}")
                else:
                    print(f"Archivo {filename} no encontrado. Omitiendo {ip_address}.")

        repeat = input("Continue with another SW(s)? (Yes/[No]): ").lower()
        if repeat not in ["yes", "y", ""]:
            break

def print_log():
    try:
        with open(SESSION_LOG, 'r', encoding='utf-8') as log_file:
            log_contents = log_file.read()
            print(log_contents)
    except FileNotFoundError:
        print(f"El archivo de log {SESSION_LOG} no se encontró.")
    except PermissionError:
        print(f"Permiso denegado para leer el archivo de log {SESSION_LOG}.")

if __name__ == "__main__":
    main()
    # print_log()  # Llama a esta función después de ejecutar main() para imprimir el contenido del log
