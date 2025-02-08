import socket
import os
import re
from pathlib import Path

class FTPClient:
    def __init__(self, host='127.0.0.1', port=21):
        self.host = host
        self.port = port
        self.commands = {}
        self._register_commands()
        self.downloads_folder = str(Path.cwd() / "Downloads")  # Carpeta local Downloads
        # Crear la carpeta si no existe
        os.makedirs(self.downloads_folder, exist_ok=True)
        print(f"Carpeta de descargas: {self.downloads_folder}")

    def _register_commands(self):
        # Registro de comandos con sus descripciones
        self.add_command("USER", "Especifica el usuario")
        self.add_command("PASS", "Especifica la contraseña")
        self.add_command("PWD", "Muestra el directorio actual")
        self.add_command("CWD", "Cambia el directorio de trabajo")       
        self.add_command("CDUP", "Cambia el directorio de trabajo al directorio padre")       
        self.add_command("LIST", "Lista archivos y directorios")
        self.add_command("MKD", "Crea un directorio")
        self.add_command("RMD", "Elimina un directorio")
        self.add_command("DELE", "Elimina un archivo")
        self.add_command("RNFR", "Especifica el archivo a renombrar")
        self.add_command("RNTO", "Especifica el nuevo nombre")
        self.add_command("QUIT", "Cierra la conexión")
        self.add_command("HELP", "Muestra la ayuda")
        self.add_command("SYST", "Muestra información del sistema")
        self.add_command("NOOP", "No realiza ninguna operación")
        self.add_command("ACCT", "Especifica la cuenta del usuario")
        self.add_command("SMNT", "Monta una estructura de sistema de archivos")
        self.add_command("REIN", "Reinicia la conexión")
        self.add_command("PORT", "Especifica dirección y puerto para conexión")
        self.add_command("PASV", "Entra en modo pasivo")
        self.add_command("TYPE", "Establece el tipo de transferencia")
        self.add_command("STRU", "Establece la estructura de archivo")
        self.add_command("MODE", "Establece el modo de transferencia")
        self.add_command("RETR", "Recupera un archivo")
        self.add_command("STOR", "Almacena un archivo")
        self.add_command("STOU", "Almacena un archivo con nombre único")
        self.add_command("APPE", "Añade datos a un archivo")
        self.add_command("ALLO", "Reserva espacio")
        self.add_command("REST", "Reinicia transferencia desde punto")
        self.add_command("ABOR", "Aborta operación en progreso")
        self.add_command("SITE", "Comandos específicos del sitio")
        self.add_command("STAT", "Retorna estado actual")
        self.add_command("NLST", "Lista nombres de archivos")

    def add_command(self, cmd_name, description):
        """Añade un nuevo comando al cliente"""
        self.commands[cmd_name] = description

    def send_command(self, sock, command, *args):
        full_command = f"{command} {' '.join(args)}".strip()
        sock.send(f"{full_command}\r\n".encode())
        
        response = ""
        while True:
            data = sock.recv(1024).decode()
            if not data:  # Si no hay más datos, salir del bucle
                break
            response += data
            # Verificar si la respuesta termina con un código de estado (por ejemplo, "226")
            if re.search(r"\d{3} .*\r\n", response):
                break
        
        return response
    
    def send_command_multiresponse(self, sock, command, *args):
        full_command = f"{command} {' '.join(args)}".strip()
        sock.send(f"{full_command}\r\n".encode())
        
        response = ""
        while True:
            data = sock.recv(1024).decode()
            if not data:  # Si no hay más datos, salir del bucle
                break
            response += data
            # Verificar si la respuesta termina con un código de estado (por ejemplo, "226")
            if re.search(r"226 .*\r\n", response):
                break
        
        return response

    def send_file(self, sock, filename):
        """Envía un archivo al servidor"""
        try:
            with open(filename, 'rb') as f:
                data = f.read()
                sock.send(data)
            return True
        except:
            return False

    def receive_file(self, sock, filename):
        """Recibe un archivo del servidor en la carpeta Downloads local"""
        try:
            # Construir la ruta completa en la carpeta Downloads local
            download_path = os.path.join(self.downloads_folder, filename)
            with open(download_path, 'wb') as f:
                while True:
                    data = sock.recv(1024)
                    if not data or b"226" in data:  # Detectar fin de transferencia
                        break
                    f.write(data)
            print(f"Archivo guardado en: {download_path}")
            return True
        except Exception as e:
            print(f"Error al recibir archivo: {e}")
            return False
        
    def enter_passive_mode(self, control_sock):
        """Entra en modo pasivo y devuelve el socket de datos"""
        response = self.send_command(control_sock, "PASV")
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
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client_socket.connect((self.host, self.port))
            print(client_socket.recv(1024).decode())

            while True:
                try:
                    command = input("FTP> ").strip().split()
                    if not command:
                        continue

                    cmd = command[0].upper()
                    args = command[1:] if len(command) > 1 else []

                    if cmd == "HELP":
                        if args:
                            cmd_help = args[0].upper()
                            if cmd_help in self.commands:
                                print(f"{cmd_help}: {self.commands[cmd_help]}")
                            else:
                                print(f"Comando '{cmd_help}' no reconocido")
                        else:
                            print("\nComandos disponibles:")
                            for cmd_name, desc in sorted(self.commands.items()):
                                print(f"{cmd_name}: {desc}")
                        continue

                    if cmd in self.commands:
                        # Manejo especial para comandos que requieren modo pasivo
                        if cmd in ["LIST", "RETR", "STOR", "APPE"]:
                            data_sock = self.enter_passive_mode(client_socket)
                            if not data_sock:
                                continue

                            try:
                                if cmd == "LIST":
                                    response = self.send_command_multiresponse(client_socket, cmd)
                                    print(response)
                                    if "150" in response:
                                        data = data_sock.recv(4096).decode()
                                        print(data)
                                    data_sock.close()  # Cerrar el socket de datos

                                elif cmd in ["RETR", "STOR", "APPE"]:
                                    if len(args) < 1:
                                        print(f"Uso: {cmd} <filename>")
                                        continue

                                    filename = args[0]
                                    if cmd == "STOR":
                                        if os.path.exists(filename):
                                            response = self.send_command_multiresponse(client_socket, cmd, filename)
                                            print(response)
                                            if "150" in response:
                                                if self.send_file(data_sock, filename):
                                                    print("Archivo enviado exitosamente")
                                                else:
                                                    print("Error al enviar archivo")
                                        else:
                                            print("Archivo no encontrado")

                                    elif cmd == "RETR":
                                        response = self.send_command_multiresponse(client_socket, cmd, filename)
                                        print(response)
                                        if "150" in response:
                                            if self.receive_file(data_sock, filename):
                                                print("Archivo recibido exitosamente")
                                            else:
                                                print("Error al recibir archivo")

                                    elif cmd == "APPE":
                                        if os.path.exists(filename):
                                            response = self.send_command_multiresponse(client_socket, cmd, filename)
                                            print(response)
                                            if "150" in response:
                                                if self.send_file(data_sock, filename):
                                                    print("Archivo anexado exitosamente")
                                                else:
                                                    print("Error al anexar archivo")
                                        else:
                                            print("Archivo no encontrado")
                            finally:
                                data_sock.close()  # Cerrar el socket de datos

                        else:
                            # Comandos que no requieren modo pasivo
                            response = self.send_command(client_socket, cmd, *args)
                            print(response)
                            if cmd == "QUIT":
                                break
                    else:
                        print("Comando no reconocido")

                except Exception as e:
                    print(f"Error: {e}")

        except Exception as e:
            print(f"Error de conexión: {e}")
        finally:
            client_socket.close()
    
if __name__ == "__main__":
    client = FTPClient()
    client.start()