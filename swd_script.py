import telnetlib
import time

def conectar_telnet(host, usuario, contraseña, habilitar_contraseña):
    try:
        # Conexión al dispositivo mediante telnet
        tn = telnetlib.Telnet(host, timeout=5)
        print(f"Conectado a {host}")

        # Lectura de los mensajes iniciales (hasta el prompt de inicio de sesión)
        output = tn.read_until(b"Username:", timeout=5)
        print(output.decode("utf-8"))

        # Envío del nombre de usuario
        tn.write(usuario.encode("utf-8") + b"\n")

        # Lectura de los mensajes de contraseña (hasta el prompt de contraseña)
        output = tn.read_until(b"Password:", timeout=5)
        print(output.decode("utf-8"))

        # Envío de la contraseña
        tn.write(contraseña.encode("utf-8") + b"\n")

        # Lectura de la respuesta después del inicio de sesión
        output = tn.read_very_eager()
        print(output.decode("utf-8"))

        # Envío del comando "enable" para acceder al modo de privilegios ejecutivos
        tn.write(b"enable\n")

        # Lectura de la solicitud de contraseña de privilegios ejecutivos (hasta el prompt de contraseña de enable)
        output = tn.read_until(b"Password:", timeout=5)
        print(output.decode("utf-8"))

        # Envío de la contraseña de privilegios ejecutivos
        tn.write(habilitar_contraseña.encode("utf-8") + b"\n")

        # Lectura de la respuesta después de ingresar al modo de privilegios ejecutivos
        output = tn.read_very_eager()
        print(output.decode("utf-8"))

        # Configurar el terminal para que muestre toda la información sin interrupciones
        tn.write(b"terminal length 0\n")
        time.sleep(0.5)
        tn.read_very_eager()


        return tn, None  # Retornamos también None como mensaje_error si la conexión fue exitosa

    except (EOFError, ConnectionRefusedError) as e:
        mensaje_error = f"Error de conexión al sw {host}. Verifica que el SW responda al protocolo Telnet."
        return None, mensaje_error

    except TimeoutError as e:
        mensaje_error = f"SWD {host} fuera de línea."
        return None, mensaje_error

    except Exception as e:
        mensaje_error = f"Error desconocido al intentar conectarse al sw {host}: {str(e)}"
        return None, mensaje_error

def obtener_nombre_host(tn):
    tn.write(b"show run | include hostname\n")
    time.sleep(0.2)
    output = tn.read_very_eager()

    # Dividir la salida en líneas
    lines = output.decode("utf-8").splitlines()

    # Buscar el nombre del host en la salida
    for line in lines:
        if "hostname " in line:
            hostname = line.split("hostname ")[1].strip()
            return hostname

    # Si no se encontró el nombre del host, devolver una cadena vacía
    return ""

def exec_command(tn, command):
    print(f"Executing command: {command}")
    tn.write(command.encode('ascii') + b"\n")
    time.sleep(0.6)
    result = tn.read_very_eager().decode('ascii')
    print(result)  # Imprimir la respuesta del dispositivo para cada comando
    return result

def ejecutar_comandos(tn, comandos):
    for index, command in enumerate(comandos):
        exec_command(tn, command)

        # Agregar tiempo adicional después del comando "interface range po1-24"
        if command == "interface range po1-24":
            time.sleep(0.5)  # Agregar el tiempo adicional que necesites

            # Verificar si hay un comando siguiente y esperar hasta que se ejecute el comando anterior
            if index + 1 < len(comandos):
                next_command = comandos[index + 1]
                exec_command(tn, next_command)

                # Agregar tiempo adicional después de algunos comandos específicos
                if next_command == "no shutdown" or next_command == "shutdown":
                    time.sleep(7)  # Agregar el tiempo adicional que necesites

            # Enviar el comando "end" solo después de que se haya ejecutado el comando anterior
            exec_command(tn, "end")