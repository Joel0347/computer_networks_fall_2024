import socket
from pathlib import Path
import shutil
import tempfile

class ServerFTP:
    def __init__(self, host='0.0.0.0', port=21):
        self.host = host
        self.port = port
        self.current_user = None
        self.users = {
            "joel": "joel"
        }
        self.authenticated = False  # Nuevo atributo para rastrear la autenticación
        self.base_dir = Path.cwd()
        self.current_dir = self.base_dir
        self.commands = {
            "USER": self.handle_user,
            "PASS": self.handle_pass,
            "PWD" : self.handle_pwd,
            "CWD" : self.handle_cwd,
            "CDUP": self.handle_cdup,
            "LIST": self.handle_list,
            "QUIT": self.handle_quit,
            "MKD" : self.handle_mkd,
            "RMD" : self.handle_rmd,
            "DELE": self.handle_dele,
            "RNFR": self.handle_rnfr,
            "RNTO": self.handle_rnto,
            "SYST": self.handle_syst,
            "HELP": self.handle_help,
            "NOOP": self.handle_noop,
            "ACCT": self.handle_acct,
            "SMNT": self.handle_smnt,
            "REIN": self.handle_rein,
            "PORT": self.handle_port,
            "PASV": self.handle_pasv,
            "TYPE": self.handle_type,
            "STRU": self.handle_stru,
            "MODE": self.handle_mode,
            "RETR": self.handle_retr,
            "STOR": self.handle_stor,
            "STOU": self.handle_stou,
            "APPE": self.handle_appe,
            "ALLO": self.handle_allo,
            "REST": self.handle_rest,
            "ABOR": self.handle_abor,
            "SITE": self.handle_site,
            "STAT": self.handle_stat,
            "NLST": self.handle_nlst
        }
        self.data_port = 20
        self.transfer_type = 'A'  # ASCII por defecto
        self.structure = 'F'      # File por defecto
        self.mode = 'S'          # Stream por defecto
        self.data_socket = None
        self.structs = {
            "F": "File",
            "R": "Record",
            "P": "Page"
        }
        self.modes = {
            "S": "Stream",
            "B": "Block",
            "C": "Compressed"
        }

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"Servidor FTP iniciado en {self.host}:{self.port}")

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Cliente conectado: {client_address}")
            self.handle_client(client_socket)

    def handle_client(self, client_socket):
        client_socket.send(b"220 Bienvenido al servidor FTP\r\n")
        self.rename_from = None  # Para el comando RNFR/RNTO
        self.authenticated = False  # Reiniciar el estado de autenticación para cada cliente
        
        while True:
            try:
                data = client_socket.recv(8192).decode().strip()
                print(data)
                if not data:
                    break

                print(f"Comando recibido: {data}")
                cmd_parts = data.split()
                cmd = cmd_parts[0].upper()
                args = cmd_parts[1:] if len(cmd_parts) > 1 else []

                # Comandos permitidos sin autenticación
                if cmd in ["HELP", "QUIT", "USER", "PASS"]:
                    self.commands[cmd](client_socket, args)
                else:
                    # Verificar si el cliente está autenticado
                    if not self.authenticated:
                        client_socket.send(b"530 Por favor inicie sesion con USER y PASS.\r\n")
                        continue

                    # Ejecutar el comando si está autenticado
                    if cmd in self.commands:
                        self.commands[cmd](client_socket, args)
                    else:
                        client_socket.send(b"502 Comando no implementado\r\n")

            except Exception as e:
                print(f"Error: {e}")
                break

        client_socket.close()

    # Implementación de comandos
    def handle_user(self, client_socket, args):
        if not args or len(args) > 1:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        
        self.current_user = args[0]
        if (self.current_user in self.users):
            client_socket.send(b"331 Usuario OK, esperando contrasena\r\n")
        else:
            self.current_user = None
            client_socket.send(b"530 Usuario invalido\r\n")

    def handle_pass(self, client_socket, args):
        if not args or len(args) > 1:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        
        password = args[0]
        if self.current_user:
            if password == self.users[self.current_user]:
                self.authenticated = True  # Cliente autenticado
                client_socket.send(b"230 Usuario logueado exitosamente\r\n")
            else:
                client_socket.send(b"530 Contrasena incorrecta\r\n")
        else:
            client_socket.send(b"503 Primero ingrese el usuario\r\n")

    def handle_pwd(self, client_socket, args):
        if args:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        
        response = f"257 \"{self.current_dir.relative_to(self.base_dir)}\"\r\n"
        client_socket.send(response.encode())

    def handle_cwd(self, client_socket, args):
        print(args)
        if not args or len(args) > 1:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        try:
            if args[0] == '..':
                print('Entrando en CDUP desde CWD')
                self.handle_cdup(client_socket, [])
                return
        
            new_path = (self.current_dir / args[0]).resolve()
            if new_path.exists() and new_path.is_dir():
                self.current_dir = new_path
                client_socket.send(b"250 Directorio cambiado exitosamente\r\n")
            else:
                client_socket.send(b"550 Directorio no existe\r\n")
        except:
            client_socket.send(b"550 Error al cambiar directorio\r\n")
            
    def handle_cdup(self, client_socket, args):
        """Maneja el comando CDUP (cambiar al directorio padre)"""
        if args:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        try:
            print("Este directorio: ", self.current_dir)
            print("Directorio base: ", self.base_dir)
            if self.current_dir == self.base_dir:
                client_socket.send(b"550 No se puede subir mas. Ya estas en el directorio raiz.\r\n")
            else:
                # Cambiar al directorio padre
                new_path = self.current_dir.parent.resolve()
                
                if new_path.exists() and new_path.is_dir():
                    self.current_dir = new_path
                    client_socket.send(b"250 Directorio cambiado exitosamente\r\n")
                else:
                    client_socket.send(b"550 Directorio no existe\r\n")
        except:
            client_socket.send(b"550 Error al cambiar directorio\r\n")
                
    def handle_list(self, client_socket, args):
        """Maneja el comando LIST (listar archivos)"""
        if args and len(args) > 1:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        
        try:
            print(args)
            path = self.current_dir / args[0] if args else self.current_dir
            client_socket.send(b"150 Iniciando transferencia\r\n")
            
            print(path)
            # Aceptar la conexión de datos
            self.data_socket, _ = self.pasv_socket.accept()
            
            # Enviar la lista de archivos
            files = "\r\n".join(str(f.name) for f in path.iterdir())
            self.data_socket.send(files.encode())
            
            client_socket.send(b"226 Transferencia completa\r\n")
            self.data_socket.close()  # Cerrar el socket de datos
            self.data_socket = None  # Reiniciar el socket de datos
        except Exception as e:
            print(f"Error en LIST: {e}")
            client_socket.send(b"550 Error al listar archivos\r\n")

    def handle_mkd(self, client_socket, args):
        if not args or len(args) > 1:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        try:
            new_dir = (self.current_dir / args[0])
            new_dir.mkdir(parents=True, exist_ok=True)
            client_socket.send(f"257 \"{new_dir}\" creado\r\n".encode())
        except:
            client_socket.send(b"550 Error al crear directorio\r\n")

    def handle_rmd(self, client_socket, args):
        if not args or len(args) > 1:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        try:
            dir_to_remove = (self.current_dir / args[0])
            if dir_to_remove.is_dir():
                shutil.rmtree(dir_to_remove)
                client_socket.send(b"250 Directorio eliminado\r\n")
            else:
                client_socket.send(b"550 No es un directorio\r\n")
        except:
            client_socket.send(b"550 Error al eliminar directorio\r\n")

    def handle_dele(self, client_socket, args):
        if not args or len(args) > 1:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        try:
            file_to_delete = (self.current_dir / args[0])
            if file_to_delete.is_file():
                file_to_delete.unlink()
                client_socket.send(b"250 Archivo eliminado\r\n")
            else:
                client_socket.send(b"550 No es un archivo\r\n")
        except:
            client_socket.send(b"550 Error al eliminar archivo\r\n")

    def handle_rnfr(self, client_socket, args):
        if not args or len(args) > 1:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        file_path = (self.current_dir / args[0])
        if file_path.exists():
            self.rename_from = file_path
            client_socket.send(b"350 Listo para RNTO\r\n")
        else:
            client_socket.send(b"550 Archivo no existe\r\n")

    def handle_rnto(self, client_socket, args):
        if not self.rename_from:
            client_socket.send(b"503 Comando RNFR requerido primero\r\n")
            return
        if not args or len(args) > 1:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        try:
            new_path = (self.current_dir / args[0])
            self.rename_from.rename(new_path)
            client_socket.send(b"250 Archivo renombrado exitosamente\r\n")
        except:
            client_socket.send(b"553 Error al renombrar\r\n")
        finally:
            self.rename_from = None

    def handle_syst(self, client_socket, args):
        if args:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        client_socket.send(b"215 UNIX Type: L8\r\n")

    def handle_help(self, client_socket, args):
        commands = ", ".join(sorted(self.commands.keys()))
        response = f"214-Los siguientes comandos están disponibles:\r\n{commands}\r\n214 Fin de ayuda.\r\n"
        client_socket.send(response.encode())

    def handle_noop(self, client_socket, args):
        if args:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        client_socket.send(b"200 OK\r\n")

    def handle_quit(self, client_socket, args):
        if args:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        client_socket.send(b"221 Goodbye\r\n")
        return True

    # Nuevos manejadores de comandos
    def handle_acct(self, client_socket, args):
        if not args or len(args) > 1:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        client_socket.send(b"230 No se requiere cuenta para este servidor\r\n")

    def handle_smnt(self, client_socket, args):
        client_socket.send(b"502 SMNT no implementado\r\n")

    def handle_rein(self, client_socket, args):
        if args:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        self.current_user = None
        self.authenticated = False
        self.current_dir = self.base_dir
        client_socket.send(b"220 Servicio reiniciado\r\n")

    def handle_port(self, client_socket, args):
        """Maneja el comando PORT (modo activo)"""
        if not args:
            client_socket.send(b"501 Sintaxis: PORT h1,h2,h3,h4,p1,p2\r\n")
            return

        try:
            # Parsear la dirección IP y el puerto
            port_parts = args[0].split(',')
            if len(port_parts) != 6:
                client_socket.send(b"501 Sintaxis invalida\r\n")
                return

            # Construir la dirección IP y el puerto
            ip = ".".join(port_parts[:4])
            port = (int(port_parts[4]) << 8) + int(port_parts[5])

            # Crear un socket de datos
            self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.data_socket.connect((ip, port))

            client_socket.send(b"200 Comando PORT exitoso\r\n")
        except Exception as e:
            print(f"Error en PORT: {e}")
            client_socket.send(b"500 Error en comando PORT\r\n")

    def handle_pasv(self, client_socket, args):
        """Maneja el comando PASV (modo pasivo)"""
        try:
            # Cerrar el socket pasivo anterior si existe
            if hasattr(self, 'pasv_socket'):
                self.pasv_socket.close()
            
            # Crear un nuevo socket para la conexión de datos
            self.pasv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.pasv_socket.bind((self.host, 0))  # Puerto aleatorio
            self.pasv_socket.listen(1)
            _, port = self.pasv_socket.getsockname()

            # Obtener la dirección IP del servidor
            ip = socket.gethostbyname(socket.gethostname())
            port_bytes = [str(port >> 8), str(port & 0xff)]
            response = f"227 Entering Passive Mode ({','.join(ip.split('.'))},{','.join(port_bytes)})\r\n"
            client_socket.send(response.encode())
        except Exception as e:
            print(f"Error en PASV: {e}")
            client_socket.send(b"500 Error en modo pasivo\r\n")

    def handle_type(self, client_socket, args):
        if not args or len(args) > 1:
            client_socket.send(b"501 Sintaxis: TYPE {A,E,I,L}\r\n")
            return
        type_code = args[0].upper()
        if type_code in ['A', 'E', 'I', 'L']:
            self.transfer_type = type_code
            client_socket.send(f"200 Tipo establecido a {type_code}\r\n".encode())
        else:
            client_socket.send(b"504 Tipo no soportado\r\n")

    def handle_stru(self, client_socket, args):
        if not args or len(args) > 1:
            client_socket.send(b"501 Sintaxis: STRU {F,R,P}\r\n")
            return

        stru_code = args[0].upper()
        if stru_code in ['F', 'R', 'P']:
            self.structure = stru_code
            client_socket.send(f"200 Estructura establecida a {self.structs[stru_code]}\r\n".encode())
        else:
            client_socket.send(b"504 Estructura no soportada\r\n")


    def handle_mode(self, client_socket, args):
        if not args or len(args) > 1:
            client_socket.send(b"501 Sintaxis: MODE {S,B,C}\r\n")
            return
        
        mode_code = args[0].upper()
        if mode_code in ['S', 'B', 'C']:
            self.mode = mode_code
            client_socket.send(f"200 Modo establecido a {self.modes[mode_code]}\r\n".encode())
        else:
            client_socket.send(b"504 Modo no soportado\r\n")

    def handle_retr(self, client_socket, args):
        """Maneja el comando RETR (descargar archivo)"""
        if not args or len(args) > 1:
            client_socket.send(b"501 Sintaxis: RETR filename\r\n")
            return
        try:
            file_path = self.current_dir / args[0]
            if file_path.is_file():
                client_socket.send(b"150 Iniciando transferencia\r\n")
                
                # Aceptar la conexión de datos
                self.data_socket, _ = self.pasv_socket.accept()
                
                # Enviar el archivo
                with open(file_path, 'rb') as f:
                    while True:
                        data = f.read()
                        if not data:
                            break
                        self.data_socket.send(data)
                
                client_socket.send(b"226 Transferencia completa\r\n")
                self.data_socket.close()
                self.data_socket = None
            else:
                client_socket.send(b"550 Archivo no encontrado\r\n")
        except Exception as e:
            print(f"Error en RETR: {e}")
            client_socket.send(b"550 Error al leer archivo\r\n")

    def handle_stor(self, client_socket, args):
        """Maneja el comando STOR (subir archivo)"""
        if not args or len(args) > 1:
            client_socket.send(b"501 Sintaxis: STOR filename\r\n")
            return

        try:
            # Verificar si el archivo ya existe
            file_path = self.current_dir / Path(args[0]).name
            print(file_path)

            # Indicar al cliente que está listo para recibir el archivo
            client_socket.send(b"150 Listo para recibir datos\r\n")
            print(b"150 Listo para recibir datos\r\n")

            # Aceptar la conexión de datos
            self.data_socket, _ = self.pasv_socket.accept()
            print("Conexión de datos establecida.")

            # Recibir el archivo
            with open(file_path, 'wb') as f:
                print("Leyendo el archivo")
                while True:
                    data = self.data_socket.recv(8192)
                    print("Data recibida")
                    if b'EOF' in data:
                        f.write(data.split(b'EOF')[0])  # Escribe los datos antes del marcador EOF
                        break
                    f.write(data)
                    print("Data escrita")

            # Confirmar que la transferencia se completó
            client_socket.send(b"226 Transferencia completa\r\n")

        except Exception as e:
            print(f"Error en STOR: {e}")
            client_socket.send(b"550 Error al almacenar archivo\r\n")

        finally:
            # Cerrar el socket de datos
            if self.data_socket:
                self.data_socket.close()
                self.data_socket = None

    def handle_stou(self, client_socket, args):
        if args:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, dir=self.current_dir)
            temp_name = Path(temp_file.name).name
            client_socket.send(f"250 Archivo será almacenado como {temp_name}\r\n".encode())
            temp_file.close()
        except:
            client_socket.send(b"550 Error al almacenar archivo\r\n")

    def handle_appe(self, client_socket, args):
        if not args or len(args) > 1:
            client_socket.send(b"501 Sintaxis: APPE filename\r\n")
            return
        try:
            file_path = self.current_dir / Path(args[0]).name
            mode = 'ab' if file_path.exists() else 'wb'
            
            client_socket.send(b"150 Listo para recibir datos\r\n")
            
            self.data_socket, _ = self.pasv_socket.accept()
            print("Conexión de datos establecida.")

            with open(file_path, mode) as f:
                print("Leyendo el archivo")
                while True:
                    data = self.data_socket.recv(8192)
                    print("Data recibida")
                    if b'EOF' in data:
                        f.write(data.split(b'EOF')[0])  # Escribe los datos antes del marcador EOF
                        break
                    f.write(data)
                    print("Data escrita")
            
            client_socket.send(b"226 Transferencia completa\r\n")
        except:
            client_socket.send(b"550 Error al anexar al archivo\r\n")

    def handle_allo(self, client_socket, args):
        client_socket.send(b"200 ALLO no necesario\r\n")

    def handle_rest(self, client_socket, args):
        client_socket.send(b"502 REST no implementado\r\n")

    def handle_abor(self, client_socket, args):
        client_socket.send(b"226 ABOR procesado\r\n")

    def handle_site(self, client_socket, args):
        client_socket.send(b"200 Comando SITE no soportado\r\n")

    def handle_stat(self, client_socket, args):
        response = "211-Estado del servidor FTP\r\n"
        response += f"    Usuario: {self.current_user}\r\n"
        response += f"    Directorio actual: {self.current_dir}\r\n"
        response += "211 Fin del estado\r\n"
        client_socket.send(response.encode())

    def handle_nlst(self, client_socket, args):
        if args and len(args) > 1:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        
        try:
            print(args)
            path = self.current_dir / args[0] if args else self.current_dir
            client_socket.send(b"150 Iniciando transferencia\r\n")
            
            print(path)
            # Aceptar la conexión de datos
            self.data_socket, _ = self.pasv_socket.accept()
            
            # Enviar la lista de archivos
            files = "\r\n".join(str(f.name) for f in path.iterdir() if f.is_file())
            self.data_socket.send(files.encode())
            
            client_socket.send(b"226 Transferencia completa\r\n")
            self.data_socket.close()  # Cerrar el socket de datos
            self.data_socket = None  # Reiniciar el socket de datos
        except Exception as e:
            print(f"Error en NLST: {e}")
            client_socket.send(b"550 Error al listar archivos\r\n")

if __name__ == "__main__":
    server = ServerFTP()
    server.start()