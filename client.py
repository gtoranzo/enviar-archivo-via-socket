import os
import socket
import struct


def send_file(sck: socket.socket, filename):
    # Obtener el tamaño del archivo a enviar.
    filesize = os.path.getsize(filename)
    # Informar primero al servidor la cantidad
    # de bytes que serán enviados.
    sck.sendall(struct.pack("<Q", filesize))
    # Enviar el archivo en bloques de 1024 bytes.
    with open(filename, "rb") as f:
        while read_bytes := f.read(1024):
            sck.sendall(read_bytes)


with socket.create_connection(("localhost", 6190)) as conn:
    print("Conectado al servidor.")
    print("Enviando archivo...")
    send_file(conn, "imagen.png")
    print("Enviado.")

print("Conexión cerrada.")
