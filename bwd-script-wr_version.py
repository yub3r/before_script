import os
import socket
import subprocess
from netmiko import ConnectHandler
from dotenv import load_dotenv
import time
import warnings
from cryptography.utils import CryptographyDeprecationWarning

warnings.simplefilter('ignore', CryptographyDeprecationWarning)

# Carga las variables de entorno del archivo .env
load_dotenv('pswd.env')

# Constantes de Configuración
USERNAME = os.getenv('SWITCH_USERNAME')
PASSWORD = os.getenv('SWITCH_PASSWORD')
ENABLE_PASSWORD = os.getenv('SWITCH_ENABLE_PASSWORD')
SESSION_LOG = 'netmiko_session.log'
TFTP_SERVER = '192.168.233.254'

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

def is_tftp_server_accessible(tftp_server, port=69):
    """Intenta conectar al servidor TFTP en el puerto especificado para verificar su accesibilidad."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:  # TFTP usa UDP
            sock.settimeout(10)  # Timeout después de 10 segundos
            sock.connect((tftp_server, port))
            return True
    except socket.error as e:
        print(f"No se pudo conectar al servidor TFTP {tftp_server} en el puerto {port}: {e}")
        return False

def send_default_commands(connection):
    """Enviar comandos default a las interfaces FastEthernet 0/1 a 0/46."""
    connection.send_command_expect('configure terminal', expect_string=r'\(config\)#')
    for i in range(1, 47):
        print(f"Enviando comando: default interface FastEthernet 0/{i}")
        connection.send_command_expect(f'default interface FastEthernet 0/{i}', expect_string=r'\(config\)#')
    connection.send_command_expect('end', expect_string=r'#')

def send_command_with_prompts(connection, command, prompts):
    """Enviar un comando y responder a los prompts especificados."""
    output = connection.send_command_timing(command)
    for prompt, response in prompts.items():
        if prompt in output:
            output += connection.send_command_timing(response)
    return output

def copy_config_to_device(ip_address, octet_4, username, password, secret, tftp_server):
    device = {
        'device_type': 'cisco_ios_telnet',
        'ip': ip_address,
        'username': username,
        'password': password,
        'secret': secret,
        'session_log': SESSION_LOG,  # Asegura que el registro se haga en el archivo especificado
    }

    # Sumar 320 al cuarto octeto para el nombre del archivo
    octet_4_adjusted = octet_4 + 320
    config_file = f'sw{octet_4_adjusted}.par02.bitfarms.com.ios'

    # Verificar si el servidor TFTP es accesible antes de intentar copiar el archivo
    if not is_tftp_server_accessible(tftp_server):
        print(f"El servidor TFTP {tftp_server} no es accesible. Abortando la copia del archivo de configuración.")
        return

    try:
        with ConnectHandler(**device) as connection:
            connection.enable()

            # Enviar comandos default a las interfaces
            send_default_commands(connection)

            # Comprobar la conectividad con el servidor TFTP
            ping_command = f"ping {tftp_server}"
            ping_output = connection.send_command_timing(ping_command)
            if "!!!!" not in ping_output:
                print(f"No se puede hacer ping al servidor TFTP desde {ip_address}. Abortando.")
                return

            # Iniciar el comando de copia
            print(f"Iniciando copia de configuración desde TFTP en {ip_address}")
            copy_command = 'copy tftp: running-config'
            prompts = {
                'Address or name of remote host []?': f"{tftp_server}\n",
                'Source filename []?': f"{config_file}\n",
                'Destination filename [running-config]?': '\n'
            }
            output = send_command_with_prompts(connection, copy_command, prompts)

            # Procesar y mostrar el resultado de la copia
            print(f"Resultado de la copia: {output}")
            if '[OK' in output:
                print("Copy successfully completed")

                # Guardar la configuración después de la copia
                save_command = 'write memory'
                print(f"Guardando configuración en {ip_address}")
                save_output = connection.send_command_expect(save_command, expect_string=r'#', delay_factor=5)
                if '[OK]' in save_output:
                    print("Configuración guardada exitosamente.")
                else:
                    print("Error al guardar la configuración.")
                print(save_output)  # Mostrar el output del comando wr
                
                # Ejecutar el comando show vlan
                show_vlan_output = connection.send_command_expect('show vlan', expect_string=r'#')
                print(show_vlan_output)  # Mostrar el output del comando show vlan
            else:
                print(f"Error en la copia de configuración: {output}")

    except Exception as e:
        print(f"Error al copiar el archivo de configuración al dispositivo: {e}")

def run_command(ip_address, octet_4, tftp_server):
    device = {
        'device_type': 'cisco_ios_telnet',
        'ip': ip_address,
        'username': USERNAME,
        'password': PASSWORD,
        'secret': ENABLE_PASSWORD,
        'global_delay_factor': 2,
        'session_log': SESSION_LOG,
    }

    try:
        response = subprocess.call(['ping', '-n', '2', ip_address], stdout=subprocess.DEVNULL)
        if response != 0:
            print(f"Sw no disponible en {ip_address}")
            return

        copy_config_to_device(ip_address, octet_4, USERNAME, PASSWORD, ENABLE_PASSWORD, tftp_server)

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
                print(f"Preparando para copiar configuración a: {ip_address}")

                run_command(ip_address, octet_4, TFTP_SERVER)

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
    print_log()  # Llama a esta función después de ejecutar main() para imprimir el contenido del log
