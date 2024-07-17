import os
import tftpy

def list_files_in_directory(directory_path):
    """
    Lista todos los archivos en un directorio dado.

    :param directory_path: Ruta del directorio del cual listar archivos.
    :return: Lista de rutas completas de los archivos.
    """
    files = []
    for root, dirs, files_in_dir in os.walk(directory_path):
        for file_name in files_in_dir:
            files.append(os.path.join(root, file_name))
    return files

def upload_files_tftp(server_ip, server_port, directory_path, destination_path='', block_size=128, timeout=5):
    files_to_upload = list_files_in_directory(directory_path)
    client = tftpy.TftpClient(server_ip, server_port)
    
    # Configuramos el tamaño de bloque y el tiempo de espera
    client.options = {'blksize': block_size}
    client.context.timeout = timeout
    
    for file_path in files_to_upload:
        try:
            print(f"Subiendo {file_path} a {server_ip} con tamaño de bloque {block_size}...")
            client.upload(destination_path + os.path.basename(file_path), file_path)
            print("Subida completada.")
        except Exception as e:
            print(f"Error al subir {file_path}: {e}")

# Configuración del servidor TFTP
SERVER_IP = '192.168.233.254'
SERVER_PORT = 69

# Ruta de la carpeta con los archivos a subir
directory_path = 'D:\\Projetcs\\before_script\\SW_ACC\\Hidro\\'

# Llamada a la función
upload_files_tftp(SERVER_IP, SERVER_PORT, directory_path)
