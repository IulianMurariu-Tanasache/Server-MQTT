import socket
import threading
import traceback
from Packets import *


class Session:
    def __init__(self):
        pass


class Client:
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.connected = False
        self.keepAlive = 0
        self.will = False
        self.willQoS = 0
        self.willRetain = False
        self.user = None
        self.password = None
        self.id = None
        self.willTopic = ''


class Server:
    def __init__(self, logBox, logs):
        self.handleClientsThread = threading.Thread(target=self.handle_clients, args=())
        self.listenThread = threading.Thread(target=self.listen, args=())
        self.state = False
        self.logBox = logBox
        self.logs = logs
        self.port = 1883
        self.ip = socket.gethostbyname(socket.gethostname())  # luata din tutorial
        self.socket = None
        self.clients = []

    def printLog(self, log):
        self.logs.insert(0, log)
        self.logBox.delete(1, 'end')
        self.logBox.insert(1, log)

    def listen(self):
        self.socket.listen()
        while self.state:
            try:
                # Asteapta cereri de conectare, apel blocant
                conn, addr = self.socket.accept()
                new_client = Client(conn, addr)
                self.printLog(f'Connected client with address: {new_client.addr}')
                # mai intai astept packetul de connect, apoi setez ca e connected
                # new_client.setConnected(True)
                self.clients.append(new_client)
            except OSError:
                print('Closed')
                break
            except Exception as e:
                traceback.print_exc()
                self.printLog("Eroare la pornirea thread‐ului")

    def start(self):
        if self.state:
            return
        self.state = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.ip, self.port))
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.printLog('Server starting on ip: ' + self.ip)
        self.listenThread.start()
        self.handleClientsThread.start()

    def stop(self):
        if not self.state:
            return
        self.state = False
        self.socket.close()
        self.printLog('Stopping server...')
        # print("Serverul se opreste")

    def handleClient(self, data, client):
        binary = format(int.from_bytes(data[0:1], "big"), '#010b')[2:]
        packet_type = int(binary[0:4], 2)
        packet_type = packet_types_to_string[packet_type]
        flags = binary[4:]
        print(packet_type)
        var_length, remaining_length = decodeVariableInt(data[1:])

        # aici switch/if
        ConnectPacket(client).decode(data[1 + var_length:])

        # si aici
        if packet_type == 'CONNECT':
            connack = ConnackPacket(client)
            connackData = connack.encode()
            client.conn.sendall(connackData)

    def handle_clients(self):
        # de vazut aici cu select din os, cum face profu
        while self.state:
            for client in self.clients:
                data = client.conn.recv(1024)
                data_decoded = data.decode(encoding='ascii')
                self.printLog(f'{client.addr} a trimis {data_decoded}')
                # Daca functia recv returneaza None, clientul a inchis conexiunea
                if data_decoded == 'disc':
                    client.connected = False
                    self.printLog(f'Client {client.addr} disconnected')
                    self.clients.remove(client)
                    client.conn.close()
                else:
                    self.handleClient(data, client)
            # print(addr, ' a trimis: ', data)
