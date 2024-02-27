# enviar archivo via socket

Envio de archivos via socket

#### Creando un socket

De manera general, cuando hiciste click en el enlace que te trajo a esta página tu navegador hizo algo como lo siguiente:

```python
# create an INET, STREAMing socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# now connect to the web server on port 80 - the normal http port
s.connect(("www.python.org", 80))
```

Cuando connect termina, el socket s puede ser usado en una petición para traer el texto de la página. El mismo socket leerá la respuesta y luego será destruido. Así es, destruido. Los sockets cliente son normalmente usados solo para un intercambio (o un pequeño numero se intercambios secuenciales).

Lo que sucede en el servidor web es un poco más complejo. Primero, el servidor web crea un «socket servidor»:

```python
# create an INET, STREAMing socket
serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# bind the socket to a public host, and a well-known port
serversocket.bind((socket.gethostname(), 80))
# become a server socket
serversocket.listen(5)
```

Un par de cosas que señalar: usamos socket.gethostname() para que el socket fuera visible al mundo exterior. Si hubiésemos usado s.bind(('localhost', 80)) o s.bind(('127.0.0.1', 80)) habríamos tenido un socket servidor pero solo habría sido visible en la misma máquina. s.bind(('', 80)) especifica que el socket es accesible desde cualquier dirección que tenga la máquina.

Algo más para señalar: los números de puerto bajos son normalmente reservados para servicios «conocidos» (HTTP, SNMP, etc.). Si estás probando los sockets usa un número grande (4 dígitos).

Finalmente, el argumento que se le pasa a listen le indica a la librería del socket que queremos poner en cola no más de 5 solicitudes de conexión (el máximo normal) antes de rechazar conexiones externas. Si el resto del código está escrito correctamente eso debería ser suficiente.

Ahora que tenemos un socket servidor escuchando en el puerto 80 ya podemos entrar al bucle principal del servidor web:

```python
while True:
    # accept connections from outside
    (clientsocket, address) = serversocket.accept()
    # now do something with the clientsocket
    # in this case, we'll pretend this is a threaded server
    ct = client_thread(clientsocket)
    ct.run()
```

Existen en realidad 3 maneras generales en las cuales este bucle puede funcionar - despachar un hilo para manejar clientsocket, crear un proceso nuevo para manejar clientsocket o reestructurar esta aplicación para usar sockets no bloqueantes y multiplexar entre nuestro «socket servidor» y cualquier clientsocket activo usando select. Más sobre esto después. Lo importante a entender ahora es: esto es todo lo que un «socket servidor hace». No manda ningún dato. No recibe ningún dato. Solo produce «sockets clientes». Cada clientsocket es creado en respuesta a algún otro «socket cliente» que hace connect() al host y al puerto al que estamos vinculados. Tan pronto como hemos credo ese clientsocket volvemos a escuchar por más conexiones. Los dos «clientes» son libres de «conversar» entre ellos - están usando algún puerto asignado dinámicamente que será reciclado cuando la conversación termine.

#### Usando un socket

Lo primero a señalar es que el «socket cliente» del navegador y el «socket cliente» del servidor web son bestias idénticas. Es decir, esta es una conversación peer to peer. O para decirlo de otra manera, como diseñador, tendrás que decidir cuáles son las reglas de etiqueta para una conversación. Normalmente, el socket que se conecta inicia la conversación, enviando una solicitud o tal vez un inicio de sesión. Pero esa es una decisión de diseño: no es una regla de los sockets.

Hay dos conjuntos de verbos que se usan para la comunicación. Puedes usar send y recv o puedes transformar tu socket cliente en algo similar a un archivo y usar read y write. Esta última es la forma en la que Java presenta sus sockets. No voy a hablar acerca de eso aquí, excepto para advertirte que necesitas usar flush en los sockets. Estos son archivos en buffer, y un error común es usar write para escribir algo y luego usar read para leer la respuesta. Sin usar flush en este caso, puedes terminar esperando la respuesta por siempre porque la petición estaría aún en el buffer de salida.

Ahora llegamos al principal problema de los sockets - send y recv operan en los buffers de red. Ellos no manejan necesariamente todos los bytes que se les entrega (o espera de ellos), porque su enfoque principal es manejar los buffers de red. En general, ellos retornan cuando los buffers de red asociados se han llenado (send) o vaciado (recv). Luego ellos dicen cuántos bytes manejaron. Es tu responsabilidad llamarlos nuevamente hasta que su mensaje haya sido tratado por completo.

Cuando recv retorna 0 bytes significa que el otro lado ha cerrado (o está en el proceso de cerrar) la conexión. No recibirás más datos de esta conexión. Nunca. Es posible que puedas mandar datos exitosamente. De eso voy a hablar más tarde.

Un protocolo como HTTP usa un socket para una sola transferencia. El cliente manda una petición, luego lee la respuesta. Eso es todo. El socket es descartado. Esto significa que un cliente puede detectar el final de la respuesta al recibir 0 bytes.

Pero si planeas reusar el socket para más transferencias, tienes que darte cuenta que no hay EOT en un socket. Repito: si la llamada a send o recv de un socket retorna después de manejar 0 bytes, la conexión se ha interrumpido. Si la conexión no se ha interrumpido, puedes esperar un recv para siempre, porque el socket no te dirá cuando no hay más nada por leer (por ahora). Ahora, si piensas sobre eso un poco, te darás cuenta de una verdad fundamental de los sockets: los mensajes deben ser de longitud fija (ouch), o ser delimitados (ouch), o indicar que tan largo son (mucho mejor), o terminar cerrando la conexión. La elección es completamente tuya (pero hay algunas vías más correctas que otras).

Asumiendo que no quieres terminar la conexión, la solución más simple es un mensaje de longitud fija:

```python
class MySocket:
    """demonstration class only
      - coded for clarity, not efficiency
    """

    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(
                            socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock

    def connect(self, host, port):
        self.sock.connect((host, port))

    def mysend(self, msg):
        totalsent = 0
        while totalsent < MSGLEN:
            sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent

    def myreceive(self):
        chunks = []
        bytes_recd = 0
        while bytes_recd < MSGLEN:
            chunk = self.sock.recv(min(MSGLEN - bytes_recd, 2048))
            if chunk == b'':
                raise RuntimeError("socket connection broken")
            chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
        return b''.join(chunks)
```

El código de envío aquí es usable para prácticamente cualquier esquema de mensajería - en Python envías cadenas y usas len() para determinar su longitud (incluso si tiene caracteres \0 incrustados). Es principalmente el código receptor el que se vuelve más complejo. (Y en C no es mucho peor, excepto que no puedes usar strlen si el mensaje tiene \0 incrustados).

La mejora más fácil es hacer que el primer caracter del mensaje un indicador del tipo de mensaje y que el tipo determine la longitud. Ahora tienes dos recv - el primero para obtener (al menos) ese primer caracter para conocer la longitud, y el segundo en un bucle para obtener el resto. Si decides ir por el camino del delimitador, estarás recibiendo un fragmento de tamaño arbitrario (4096 o 8192 son a menudo buenas elecciones para tamaños de buffers de red) y escaneando lo que recibas en busca del delimitador.

Hay una complicación de la que estar consiente: si el protocolo conversacional permite mandar múltiples mensajes consecutivos (sin ningún tipo de respuesta), y pasas a recv un tamaño de fragmento arbitrario poder terminar leyendo el inicio de un próximo mensaje. Tendrás que dejarlo aparte y guardarlo hasta que sea necesario.

Prefijar el mensaje con su longitud (por ejemplo, 5 caracteres numéricos) se vuelve más complicado porque (créalo o no), puede que no recibas los 5 caracteres en una llamada a recv. Para proyectos pequeños te saldrás con la tuya; pero con altas cargas de red, tu código se romperá rápidamente a menos que uses dos recv en bucle - el primero para determinar la longitud, el segundo para obtener la parte del mensaje. Sucio. También será cuando descubras que send no siempre logra enviar todo de una sola vez. Y a pesar de haber leído esto eventualmente te va a morder!
