import select
import socket
import threading
import traceback
from Packets import *


class Client:
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.connected = False
        self.keepAlive = 0
        self.will = False
        self.willQoS = 0
        self.willRetain = False
        self.willMsg = ''
        self.user = None
        self.password = None
        self.id = None
        self.willTopic = ''
        self.topics = []
        self.toDC = False
        self.timer = None

    def fileno(self):
        return self.conn.fileno()
    def toDec(self):
        self.toDC = True


class Server:
    def __init__(self, logBox, logs, trv):
        self.state = False
        self.logBox = logBox
        self.logs = logs
        self.port = 1883
        self.ip = '127.0.0.1'  # socket.gethostbyname(socket.gethostname())
        self.socket = None
        self.clients = []
        self.topics = {}
        self.topics_history = {}
        self.trv = trv
        self.sessions = []
        self.packet_ids = []

    #de vazut
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
        self.handleClientsThread = threading.Thread(target=self.handle_clients, args=())
        self.listenThread = threading.Thread(target=self.listen, args=())
        self.listenThread.start()
        self.handleClientsThread.start()
        self.closeConnectionsTimer = threading.Timer(0.5, self.closeConn)
        self.closeConnectionsTimer.start()

    def stop(self):
        if not self.state:
            return
        self.state = False
        self.socket.close()
        self.listenThread.join()
        self.handleClientsThread.join()
        self.closeConnectionsTimer.cancel()
        self.printLog('Stopping server...')

    def handleClient(self, data, client, packet_type, flags):
        # aici if/switch

        # reset timer keepAlive
        if client.connected:
            self.resetTimer(client)
        if packet_type == 'CONNECT':
            # timer pentru primirea pachetului connect in timp rezonabil
            conPack = ConnectPacket(client, self.clients, self.sessions)
            conPack.decode(data[0:], flags)
            connack = ConnackPacket(client)
            connackData = connack.encode((conPack.sessionPresent, conPack.connCode))
            client.conn.sendall(connackData)
            # pornire timer
            # verificare keep alv
            if client.keepAlive != 0:
                self.resetTimer(client)

        if packet_type == 'SUBSCRIBE':

            def dfsDictAll(dic):
                if type(dic) is list:
                    dic.append(client.id)
                    return
                for _keys in dic.keys():
                    dfsDictAll(dic[_keys])

            def dfsDictAny(dic, topic):
                if '/' not in topic:
                    if topic not in dic.keys():
                        dic[level] = [client.id]
                    else:
                        if client.id not in dic[level]:
                            dic[level].append(client.id)
                    return
                if type(dic) is list:
                    return
                for _keys in dic.keys():
                    currdic = dic[_keys]
                    dfsDictAny(dic[_keys], topic[topic])

            sub = SubscribePacket(client)
            sub.decode(data[0:], flags)
            if sub.retCode != 128:
                for t in client.topics:
                    # wildcards -> ce fac cu $?
                    topic = t
                    level = t
                    currdic = self.topics
                    while topic.find('/') != -1:
                        level = str(topic[0:topic.find('/')])
                        topic = str(topic[topic.find('/') + 1:])
                        if level == '+':
                            pass
                        if level not in currdic.keys():
                            currdic[level] = {}
                        currdic = currdic[level]

                    level = str(topic)
                    if level == '+':
                        pass
                    elif level == '#':
                        # dfsDict(currdic)
                        pass
                    elif level not in currdic.keys():
                        currdic[level] = [client.id]
                    else:
                        if client.id not in currdic[level]:
                            if type(currdic[level]) is list:
                                currdic[level].append(client.id)
                            else:
                                currdic[level]['#'] = [client.id]
                self.trv.event_generate("<<Subscribe>>")

            suback = SubackPacket(client)
            subackData = suback.encode((sub.packet_id, sub.retCode))
            client.conn.sendall(subackData)

        if packet_type == 'PUBLISH':
            publish = PublishPacket(client)
            publish.decode(data[0:], flags)
            self.packet_ids.append(publish.packet_identifier)
            if publish.topic not in self.topics_history.keys():
                self.topics_history[publish.topic] = [publish.msg]
            else:
                self.topics_history[publish.topic].append(publish.msg)
            # forward la ceilalti clienti
            self.packet_ids.remove(publish.packet_identifier)

            if publish.qos == 1:
                puback = PubackPacket(client)
                pubackData = puback.encode(publish.packet_identifier)
                client.conn.sendall(pubackData)

            if publish.qos == 2:
                pubrec = PubrecPacket(client)
                pubrecData = pubrec.encode(publish.packet_identifier)
                client.conn.sendall(pubrecData)

        if packet_type == 'DISCONNECT':
            client.toDC = True  # am inchis conexiune? si acum Will mesage?

        if packet_type == 'PINGREQ':
            pingresp = PingRespPacket(client)
            pingrespData = pingresp.encode(None)
            client.conn.sendall(pingrespData)

    def handle_clients(self):
        while self.state:
            if len(self.clients) == 0:
                continue
            to_read, _, _ = select.select(self.clients, [], [], 1)
            for client in to_read:
                self.printLog(f'{client.id if client.id is not None else client.addr} a trimis un pachet')
                data = client.conn.recv(1024)
                if data == b'':
                    client.toDC = True
                    return
                while len(data) > 0:
                    binary = format(int.from_bytes(data[0:1], "big"), '#010b')[2:]
                    packet_type = int(binary[0:4], 2)
                    packet_type = packet_types_to_string[packet_type]
                    flags = binary[4:]
                    print(packet_type)

                    var_length, remaining_length = decodeVariableInt(data[1:])
                    curr_pack = data[1 + var_length: 1 + var_length + remaining_length]
                    data = data[1 + var_length + remaining_length:]
                    self.handleClient(curr_pack, client, packet_type, flags)

    def discClient(self, id):
        for client in self.clients:
            if client.id == id:
                client.toDC = True
                return

    def closeConn(self):
        to_remove = []
        for client in self.clients:
            if client.toDC:
                client.connected = False
                client.conn.shutdown(2)
                client.conn.close()
                to_remove.append(client)
        [self.clients.remove(client) for client in to_remove]
        # fac din nou si start
        self.closeConnectionsTimer = threading.Timer(0.5, self.closeConn)
        self.closeConnectionsTimer.start()


    def resetTimer(self, client):
        client.timer = threading.Timer(1.5 * client.keepAlive, client.toDec)
        client.timer.start()

