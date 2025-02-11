import streamlit as st
from full_client import FTPClient  # Importa tu clase FTPClient modificada
import re
import os
import socket
from pathlib import Path

base_dir = "C:\\Users\\Joel\\Documents\\GitHub\\computer_networks_fall_2024\\proyecto"

# Función para inicializar el cliente FTP
def initialize_ftp_client():
    if 'ftp_client' not in st.session_state:
        st.session_state.ftp_client = FTPClient()  # Crea una instancia del cliente FTP
        st.session_state.ftp_client.start()  # Inicia la conexión FTP

# Función para actualizar la barra lateral
def update_sidebar():
    st.sidebar.subheader("Archivos para descargar")
    for f in Path(base_dir).iterdir():
        if f.is_file():
            st.sidebar.write(f.name)

# Función para manejar la ejecución del comando
def execute_command():
    command = st.session_state.command_input.strip()
    if command:
        # Procesar el comando
        cmd_parts = command.split()
        cmd = cmd_parts[0].upper()
        args = cmd_parts[1:] if len(cmd_parts) > 1 else []

        try:
            if cmd in ["LIST", "RETR", "STOR", "APPE", "NLST"]:
                # Enviar el comando PASV y obtener la respuesta
                response = st.session_state.ftp_client.send_command("PASV")
                st.session_state.client_responses.insert(0, response)

                if not response.startswith("227"):
                    st.session_state.client_responses.insert(0, "Error: No se pudo entrar en modo pasivo")
                else:
                    # Extraer la dirección IP y el puerto de la respuesta
                    match = re.search(r'(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)', response)
                    if not match:
                        st.session_state.client_responses.insert(0, "Error: No se pudo extraer la dirección IP y el puerto")
                    else:
                        # Construir la dirección IP y el puerto
                        ip = ".".join(match.groups()[:4])
                        port = (int(match.group(5)) << 8) + int(match.group(6))

                        # Crear un nuevo socket para la conexión de datos
                        data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        data_sock.connect((ip, port))

                        try:
                            if cmd == "LIST" or cmd == "NLST":
                                path = args[0] if args else '.'
                                response = st.session_state.ftp_client.send_command_multiresponse(cmd, path)
                                st.session_state.client_responses.insert(0, response)
                                if "150" in response:
                                    data = data_sock.recv(8192).decode()
                                    st.session_state.client_responses.insert(0, data)
                                data_sock.close()  # Cerrar el socket de datos

                            elif cmd in ["RETR", "STOR", "APPE"]:
                                if len(args) < 1:
                                    st.session_state.client_responses.insert(0, f"Uso: {cmd} <filename>")
                                else:
                                    filename = args[0]
                                    if cmd == "STOR":
                                        if os.path.exists(filename):
                                            response = st.session_state.ftp_client.send_stor_command(data_sock, "STOR", filename)
                                            st.session_state.client_responses.insert(0, response)
                                        else:
                                            st.session_state.client_responses.insert(0, "Archivo no encontrado")

                                    elif cmd == "RETR":
                                        response = st.session_state.ftp_client.send_command_multiresponse("RETR", filename)
                                        st.session_state.client_responses.insert(0, response)
                                        if "150" in response:
                                            if st.session_state.ftp_client.receive_file(data_sock, filename):
                                                st.session_state.client_responses.insert(0, "Archivo recibido exitosamente")
                                            else:
                                                st.session_state.client_responses.insert(0, "Error al recibir archivo")

                                    elif cmd == "APPE":
                                        if os.path.exists(filename):
                                            response = st.session_state.ftp_client.send_stor_command(data_sock, "APPE", filename)
                                            st.session_state.client_responses.insert(0, response)
                                        else:
                                            st.session_state.client_responses.insert(0, "Archivo no encontrado")
                        finally:
                            data_sock.close()  # Cerrar el socket de datos

            # Manejo de comandos que no requieren modo pasivo
            else:
                response = st.session_state.ftp_client.send_command(cmd, *args)
                st.session_state.client_responses.insert(0, response)
                if cmd == "QUIT":
                    st.session_state.client_responses.insert(0, "Conexión cerrada.")
                    st.session_state.ftp_client.close()

        except Exception as e:
            st.session_state.client_responses.insert(0, f"Error: {e}")

# Función principal
def main():
    st.title("Interfaz de Cliente FTP")

    # Inicializar el cliente FTP
    initialize_ftp_client()

    # Inicializar el valor del campo de texto si no existe
    if 'command_input' not in st.session_state:
        st.session_state.command_input = ""
        
    # Inicializar la lista de respuestas si no existe
    if 'client_responses' not in st.session_state:
        st.session_state.client_responses = []

    if st.button("Borrar comando"):
        st.session_state.command_input = ""

    # Entrada de comandos
    st.text_input(
        "Ingrese un comando FTP:",
        key="command_input",
        on_change=execute_command,  # Ejecutar el comando al presionar Enter
    )
        
    update_sidebar()

    # Mostrar respuestas
    if 'client_responses' in st.session_state:
        st.text_area("Respuestas:", value="\n".join(st.session_state.client_responses), height=300)

# Ejecutar la aplicación
if __name__ == "__main__":
    main()