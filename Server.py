import select
import random
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
        self.session = None

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
        self.retain_messages = {}
        self.topics_history = {}
        self.trv = trv
        self.sessions = []
        self.packet_ids = []
        self.topicMaxQOS = {}

    def genPacketID(self):
        random.seed()
        id = random.randrange(1, 65534)
        while id in self.packet_ids:
            id = random.randrange(1, 65534)
        return id

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

    def keepThreadsOn(self):
        if not self.listenThread.is_alive():
            self.listenThread = threading.Thread(target=self.listen, args=())
            self.listenThread.start()
        if not self.handleClientsThread.is_alive():
            self.handleClientsThread = threading.Thread(target=self.handle_clients, args=())
            self.handleClientsThread.start()

    def start(self):
        if self.state:
            return
        self.state = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.ip, self.port))
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.printLog('Server starting on ip: ' + self.ip)
        self.listenThread = threading.Thread(target=self.listen, args=())
        self.handleClientsThread = threading.Thread(target=self.handle_clients, args=())
        self.listenThread.start()
        self.handleClientsThread.start()
        self.keepThreadsOn = threading.Thread(target=self.keepThreadsOn, args=())
        self.closeConnectionsTimer = threading.Timer(0.5, self.closeConn)
        self.closeConnectionsTimer.start()
        self.resendTimer = threading.Timer(1, self.reSendPackets)
        self.resendTimer.start()

    def stop(self):
        if not self.state:
            return
        self.state = False
        self.socket.close()
        self.listenThread.join()
        self.handleClientsThread.join()
        self.closeConnectionsTimer.cancel()
        self.printLog('Stopping server...')

    def checkTopicFilter(self, topics):
        # $ nu e implementat
        for t in topics:
            next = t
            level = t
            while next.find('/') != -1:
                level = str(next[0:next.find('/')])
                next = str(next[next.find('/') + 1:])
                if level == '' or level == '#' or any(x in ['#', '+'] for x in level):
                    return False
        return True

    def acknowledgePacket(self, ack, client):
        for packet in client.session.noAck:
            if ack.packet_id == packet.packet_id:
                client.session.noAck.remove(packet)
                return

    def publishMessage(self, who, retain, msg, topic, qos):
        if len(who) == 0:
            return
        publish = PublishPacket(who[0])
        publish.packet_id = self.genPacketID()
        publish.retain = retain
        publish.msg = msg
        publish.topic = topic
        publish.qos = qos
        publishData = publish.encode(self.topicMaxQOS)

        for c in who:
            c.conn.sendall(publishData)
            c.session.noAck.append(publish)

    def handleClient(self, data, client, packet_type, flags):
        if client.connected:
            self.resetTimer(client)
        self.printLog(f'{client.id if client.id is not None else client.addr} a trimis {packet_type}')
        if packet_type == 'CONNECT':
            # timer pentru primirea pachetului connect in timp rezonabil
            conPack = ConnectPacket(client, self.clients, self.sessions)
            conPack.decode(data[0:], flags)

            if conPack.connCode == 1:
                self.printLog('Unnaceptable protocol version!')
            if conPack.connCode == 2:
                self.printLog('Client ID rejected!')
            if conPack.connCode == 3:
                self.printLog('Server Unavailable!')
            if conPack.connCode == 4:
                self.printLog('Bad username or password!')
            if conPack.connCode == 5:
                self.printLog('Credentials missing or not authorized!')

            connack = ConnackPacket(client)
            connackData = connack.encode((conPack.sessionPresent, conPack.connCode))
            client.conn.sendall(connackData)
            if client.keepAlive != 0:
                self.resetTimer(client)

        if packet_type == 'SUBSCRIBE':
            sub = SubscribePacket(client)
            sub.decode(data[0:], flags)

            # maxQOS:
            topics = []
            for topic, qos in sub.topics:
                topics.append(topic)
                self.topicMaxQOS[topic] = qos

            if self.checkTopicFilter(topics):
                client.topics += topics
                for sess in self.sessions:
                    if sess.client_id == client.id:
                        sess.topics = client.topics
                        break
                for topic in client.topics:
                    if '#' in topic:
                        for t in self.topics.keys():
                            if t.find(topic[:-2]) == 0:
                                if client not in self.topics[t]:
                                    self.topics[t].append(client)
                                    if t not in self.topics_history.keys():
                                        self.topics_history[topic] = []
                                    try:
                                        topics.remove(topic)
                                    except:
                                        pass
                                    topics.append(t)
                    elif '+' in topic:
                        for t in self.topics.keys():
                            if t.find(topic[0:topic.find('+') - 2]) == 0 and t.find(topic[topic.find('+') + 1:]) > 0:
                                if client not in self.topics[t]:
                                    self.topics[t].append(client)
                                    if t not in self.topics_history.keys():
                                        self.topics_history[topic] = []
                                    try:
                                        topics.remove(topic)
                                    except:
                                        pass
                                    topics.append(t)
                    else:
                        if topic in self.topics and client not in self.topics[topic]:
                            self.topics[topic].append(client)
                        elif topic not in self.topics:
                            self.topics[topic] = [client]
                        if topic not in self.topics_history.keys():
                            self.topics_history[topic] = []
                self.trv.event_generate("<<Subscribe>>")
            else:
                sub.retCode = 128
            suback = SubackPacket(client)
            subackData = suback.encode((sub.packet_id, sub.retCode))
            client.conn.sendall(subackData)

            # retained messages -> send
            for t in topics:
                if t in self.retain_messages:
                    self.publishMessage([client], 1, self.retain_messages[t][0], t, self.retain_messages[t][1])

        if packet_type == 'PUBLISH':
            publish = PublishPacket(client)
            publish.decode(data[0:], flags)

            if publish.retain == 1:
                self.retain_messages[publish.topic] = (publish.msg, publish.qos)

            new_pub_id = self.genPacketID()
            old_pub_id = publish.packet_id
            self.packet_ids.append(new_pub_id)
            self.packet_ids.append(old_pub_id)

            if publish.topic not in self.topics_history.keys():
                self.topics_history[publish.topic] = [publish.msg]
            else:
                if len(self.topics_history[publish.topic]) > 10:
                    self.topics_history[publish.topic] = self.topics_history[publish.topic][
                                                         len(self.topics_history[publish.topic]) - 10:]
                self.topics_history[publish.topic].append(publish.msg)
            self.trv.event_generate("<<Publish>>")

            # forward la ceilalti clienti
            publish.retain = 0
            publishData = publish.encode(self.topicMaxQOS)
            publish.packet_id = new_pub_id
            for c in self.topics[publish.topic]:
                c.conn.sendall(publishData)
                c.session.noAck.append(publish)

            if publish.qos == 1:
                puback = PubackPacket(client)
                pubackData = puback.encode(old_pub_id)
                client.conn.sendall(pubackData)

            if publish.qos == 2:
                pubrec = PubrecPacket(client)
                pubrecData = pubrec.encode(old_pub_id)
                client.conn.sendall(pubrecData)
                client.session.noAck.append(pubrec)

        if packet_type == 'PUBACK':
            puback = PubackPacket(client)
            puback.decode(data[0:], flags)
            self.packet_ids.remove(puback.packet_id)
            self.acknowledgePacket(puback, client)

        if packet_type == 'PUBREC':
            pubrec = PubrecPacket(client)
            pubrec.decode(data[0:], flags)
            pubrel = PubrelPacket(client)
            pubrelData = pubrel.encode(pubrec.packet_id)
            client.conn.sendall(pubrelData)
            self.acknowledgePacket(pubrec, client)
            client.session.noAck.append(pubrel)

        if packet_type == 'PUBREL':
            pubrel = PubrelPacket(client)
            pubrel.decode(data[0:], flags)
            pubcomp = PubcompPacket(client)
            pubcompData = pubcomp.encode(pubrel.packet_id)
            client.conn.sendall(pubcompData)
            self.acknowledgePacket(pubrel, client)
            client.session.noAck.append(pubcomp)

        if packet_type == 'PUBCOMP':
            pubcomp = PubcompPacket(client)
            pubcomp.decode(data[0:], flags)
            self.packet_ids.remove(pubcomp.packet_id)
            self.acknowledgePacket(pubcomp, client)

        if packet_type == 'UNSUBSCRIBE':
            unsub = UnsubscribePacket(client)
            unsub.decode(data[0:], flags)
            new_topics = []
            for topic in client.topics:
                if topic not in unsub.topics:
                    new_topics.append(topic)
                else:
                    self.topics[topic].remove(client)
            client.topics = new_topics
            self.trv.event_generate("<<Subscribe>>")
            unsuback = UnSubackPacket(client)
            unsubackData = unsuback.encode(unsub.packet_id)
            client.conn.sendall(unsubackData)

        if packet_type == 'DISCONNECT':
            client.will = False
            self.fullDisconnect(client)

        if packet_type == 'PINGREQ':
            pingresp = PingRespPacket(client)
            pingrespData = pingresp.encode(None)
            client.conn.sendall(pingrespData)

    def handle_clients(self):
        while True:
            if not self.state:
                return
            if len(self.clients) == 0:
                continue
            try:
                to_read, _, _ = select.select(self.clients, [], [], 1)
            except:
                continue
            for client in to_read:
                try:
                    data = client.conn.recv(1024)
                except Exception as e:
                    print(e)
                    print('closed a socket of a client')
                    try:
                        self.fullDisconnect(client)
                    finally:
                        break
                while len(data) > 0:
                    binary = format(int.from_bytes(data[0:1], "big"), '#010b')[2:]
                    packet_type = int(binary[0:4], 2)
                    packet_type = packet_types_to_string[packet_type]
                    flags = binary[4:]

                    var_length, remaining_length = decodeVariableInt(data[1:])
                    curr_pack = data[1 + var_length: 1 + var_length + remaining_length]
                    data = data[1 + var_length + remaining_length:]
                    self.handleClient(curr_pack, client, packet_type, flags)

    def fullDisconnect(self, client):
        for topic in client.topics:
            if topic in self.topics:
                self.topics[topic].remove(client)
        self.trv.event_generate("<<Subscribe>>")
        if client.will:
            self.publishMessage(self.topics[client.willTopic], client.willRetain, client.willMsg, client.willTopic,
                                client.willQoS)
            client.will = False
        client.connected = False
        client.conn.shutdown(2)
        client.conn.close()
        self.clients.remove(client)
        self.printLog(f'{client.id if client.id is not None else client.addr} was disconnected')

    def closeConn(self):
        for client in self.clients:
            if client.toDC:
                self.fullDisconnect(client)
        self.closeConnectionsTimer.cancel()
        self.closeConnectionsTimer = threading.Timer(0.5, self.closeConn)
        self.closeConnectionsTimer.start()

    def resetTimer(self, client):
        if client.timer is not None:
            client.timer.cancel()
        client.timer = threading.Timer(1.5 * client.keepAlive, client.toDec)
        client.timer.start()

    def discClientById(self, selected_client):
        for client in self.clients:
            if client.id == selected_client:
                self.fullDisconnect(client)
                return

    def getClientByID(self, id):
        for client in self.clients:
            if client.id == id:
                return client

    def reSendPackets(self):
        for session in self.sessions:
            for packet in session.noAck:
                self.getClientByID(session.client_id).conn.sendall(packet)
            for packet in session.pendingToSend:
                self.getClientByID(session.client_id).conn.sendall(packet)
        self.resendTimer.cancel()
        self.resendTimer = threading.Timer(1, self.reSendPackets)
        self.resendTimer.start()
