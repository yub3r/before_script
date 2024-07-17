import os
import socket
import subprocess
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

def copy_config_to_device(ip_address, octet_4, username, password, secret, tftp_server):
    device = {
        'device_type': 'cisco_ios_telnet',
        'ip': ip_address,
        'username': username,
        'password': password,
        'secret': secret,
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

            # Comprobar la conectividad con el servidor TFTP
            ping_command = f"ping {tftp_server}"
            ping_output = connection.send_command_timing(ping_command)
            if "!!!!" not in ping_output:
                print(f"No se puede hacer ping al servidor TFTP desde {ip_address}. Abortando.")
                return

            # Iniciar el comando de copia
            copy_command = 'copy tftp: running-config'
            output = connection.send_command_timing(copy_command)
            if 'Address or name of remote host []?' in output:
                output += connection.send_command_timing(tftp_server + '\n')
            if 'Source filename []?' in output:
                output += connection.send_command_timing(config_file + '\n')
            if 'Destination filename [running-config]?' in output:
                output += connection.send_command_timing('\n')  # Enter para confirmar el destino por defecto

            # Procesar y mostrar el resultado de la copia
            if 'Accessing' in output and 'Loading' in output and '[OK' in output:
                access_line = output.split('\n')[0]
                loading_line = output.split('\n')[1]
                ok_line = [line for line in output.split('\n') if '[OK' in line][0]
                print(f"{access_line}")
                print(f"{loading_line}")
                print(f"{ok_line}")
                print("Copy successfully completed")
            else:
                print(f"Resultado de la copia: {output}")

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

    # Solicitar al usuario la IP del servidor TFTP
    while True:
        tftp_server = input("Ingrese la IP del servidor TFTP: ")
        if is_valid_ip(tftp_server):
            break
        else:
            print("La IP ingresada no es válida. Por favor, intente nuevamente.")

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

                run_command(ip_address, octet_4, tftp_server)

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
