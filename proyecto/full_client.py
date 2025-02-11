import socket
import os
import re
from pathlib import Path

class FTPClient:
    def __init__(self, host='127.0.0.1', port=21):
        self.host = host
        self.port = port
        self.sock = None  # Inicializar el socket como None
        self.downloads_folder = str(Path.cwd() / "Downloads")  # Carpeta local Downloads
        # Crear la carpeta si no existe
        os.makedirs(self.downloads_folder, exist_ok=True)
        print(f"Carpeta de descargas: {self.downloads_folder}")

    def send_command(self, command, *args):
        """Envía un comando al servidor FTP."""
        if not self.sock:
            raise Exception("No hay conexión al servidor FTP.")
        
        full_command = f"{command} {' '.join(args)}".strip()
        self.sock.send(f"{full_command}\r\n".encode())
        
        response = ""
        while True:
            data = self.sock.recv(8192).decode()
            if not data:  # Si no hay más datos, salir del bucle
                break
            response += data
            # Verificar si la respuesta termina con un código de estado (por ejemplo, "226")
            if re.search(r"\d{3} .*\r\n", response):
                break
        
        return response

    def send_stor_command(self, data_sock, command, *args):
        """Envía un comando STOR al servidor FTP."""
        if not self.sock:
            raise Exception("No hay conexión al servidor FTP.")
        
        full_command = f"{command} {' '.join(args)}".strip()
        self.sock.send(f"{full_command}\r\n".encode())
        
        response = ""
        while True:
            data = self.sock.recv(8192).decode()
            if not data:  # Si no hay más datos, salir del bucle
                break
            if "150" in data:
                if self.send_file(data_sock, args[0]):
                    print("Archivo enviado exitosamente")
                else:
                    print("Error al enviar archivo")
            response += data
            
            # Verificar si la respuesta termina con un código de estado (por ejemplo, "226")
            if re.search(r"226 .*\r\n", response) or data.startswith("5"):
                break
        
        return response

    def send_command_multiresponse(self, command, *args):
        """Envía un comando que espera múltiples respuestas."""
        if not self.sock:
            raise Exception("No hay conexión al servidor FTP.")
        
        full_command = f"{command} {' '.join(args)}".strip()
        self.sock.send(f"{full_command}\r\n".encode())
        
        response = ""
        while True:
            data = self.sock.recv(8192).decode()
            if not data:  # Si no hay más datos, salir del bucle
                break
            response += data
            # Verificar si la respuesta termina con un código de estado (por ejemplo, "226")
            if re.search(r"226 .*\r\n", response) or data.startswith("5"):
                break
        
        return response

    def send_file(self, sock, filename):
        """Envía un archivo al servidor."""
        try:
            print(filename)
            with open(filename, 'rb') as f:
                while True:
                    data = f.read()
                    print(data)
                    if not data:
                        break
                    sock.send(data)
            sock.send(b'EOF')
            return True
        except Exception as e:
            print(f"Error al enviar archivo: {e}")
            return False

    def receive_file(self, sock, filename):
        """Recibe un archivo del servidor en la carpeta Downloads local."""
        try:
            # Construir la ruta completa en la carpeta Downloads local
            download_path = os.path.join(self.downloads_folder, filename)
            with open(download_path, 'wb') as f:
                while True:
                    data = sock.recv(8192)
                    if not data:  # Detectar fin de transferencia
                        break
                    f.write(data)
            print(f"Archivo guardado en: {download_path}")
            return True
        except Exception as e:
            print(f"Error al recibir archivo: {e}")
            return False

    def enter_passive_mode(self):
        """Entra en modo pasivo y devuelve el socket de datos."""
        response = self.send_command("PASV")
        print(response)

        # Extraer la dirección IP y el puerto de la respuesta
        match = re.search(r'(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)', response)
        if not match:
            print("No se pudo entrar en modo pasivo")
            return None

        # Construir la dirección IP y el puerto
        ip = ".".join(match.groups()[:4])
        port = (int(match.group(5)) << 8) + int(match.group(6))
        
        # Si la dirección IP es 0.0.0.0, usar la dirección IP del servidor
        if ip == "0.0.0.0":
            ip = self.host

        # Crear un nuevo socket para la conexión de datos
        data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_sock.connect((ip, port))

        return data_sock

    def start(self):
        """Inicia la conexión FTP."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.host, self.port))
            print(self.sock.recv(8192).decode())  # Recibir el mensaje de bienvenida del servidor
        except Exception as e:
            print(f"Error de conexión: {e}")
            self.sock = None
            raise e

    def close(self):
        """Cierra la conexión FTP."""
        if self.sock:
            self.sock.close()
            self.sock = None

if __name__ == "__main__":
    client = FTPClient()
    client.start()