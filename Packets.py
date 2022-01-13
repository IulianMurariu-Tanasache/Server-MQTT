import functools as fct
from HelperFunctions import *

auth_dict = {}


def updateAuthDict():
    pass


class Session:
    def __init__(self, _id, topics):
        self.client_id = _id
        self.topics = topics
        self.noAck = {}
        self.pendingToSend = {}


class Packet:
    def __init__(self, client):
        self.client = client

    def decode(self, data, flags):
        pass

    def encode(self, data):
        pass


class ConnectPacket(Packet):
    def __init__(self, client, clients, sessions):
        super().__init__(client)
        self.clients = clients
        self.sessions = sessions
        self.connCode = 0
        self.sessionPresent = False

    def decode(self, data, flags):
        if self.client.connected is True or int(flags, 2) != 0:
            self.client.toDC = True
            self.connCode = 2;
            return

        prot_len, protocol_name, prot_version, conn_flags, keep_alive = struct.unpack('!H4sBcH', data[0:10])
        protocol_name = protocol_name.decode(encoding='utf-8')
        int_conn = int.from_bytes(conn_flags, 'big')
        connect_flags = f'{int_conn:08b}'

        if protocol_name != 'MQTT' or prot_version != 4:
            print('Eroare conectare1')
            self.client.toDC = True
            self.connCode = 1
            return

        reserved = connect_flags[7] == '1'

        if reserved:
            self.client.toDC = True
            print('Eroare conectare2')
            return

        clean_start = connect_flags[6] == '1'

        self.client.will = connect_flags[5] == '1'
        self.client.willQoS = int(connect_flags[3:5], 2)
        self.client.willRetain = connect_flags[2] == '1'
        password = connect_flags[1] == '1'
        username = connect_flags[0] == '1'
        if not username:
            self.connCode = 5
            self.client.toDC = True
            return

        self.client.keepAlive = keep_alive  # timerul  = keepAlive * 1.5 #keep alive  0 fara timer

        payload_data = data[10:]
        id_len, self.client.id = decodeUTF8(payload_data)

        payload_data = payload_data[2 + id_len:]

        for c in self.clients:
            if self.client.id == c.id and self.client != c:
                self.client.toDC = True
                self.connCode = 2
                return

        if clean_start:
            [self.sessions.remove(s) for s in self.sessions if s.client_id == self.client.id]
            self.sessions.append(Session(self.client.id, []))
        else:
            exists = False
            for s in self.sessions:
                if s.client_id == self.client.id:
                    exists = True
                    self.client.topics = s.topics
            if not exists:
                self.sessions.append(Session(self.client.id, []))
            self.sessionPresent = exists

        for s in self.sessions:
            if s.client_id == self.client.id:
                self.client.session = s
                break

        if self.client.will:
            wt_len, self.client.willTopic = decodeUTF8(payload_data[0:])
            msg_len = struct.unpack('!H', payload_data[2 + wt_len:2 + wt_len + 2])[0]
            self.client.willMsg = payload_data[wt_len + 2 + 2:wt_len + 2 + 2 + msg_len].decode()
            print(self.client.willMsg)
            payload_data = payload_data[wt_len + 2 + 2 + msg_len:]

        if username:
            user_len, self.client.user = decodeUTF8(payload_data[0:])
            self.client.user = self.client.user
            print(self.client.user)
            payload_data = payload_data[user_len + 2:]

        if password:
            pass_len, self.client.password = decodeUTF8(payload_data[0:])
            self.client.password = self.client.password
            print(self.client.password)
            payload_data = payload_data[pass_len + 2:]

        if self.client.user not in auth_dict.keys() or auth_dict[self.client.user] != self.client.password:
            self.client.toDC = True
            self.connCode = 4
            return

        self.client.connected = True


class ConnackPacket(Packet):
    def __init__(self, client):
        super().__init__(client)

    def encode(self, data):
        fixedHeader = struct.pack('!BB', 32, 2)

        sp = data[0]
        connCode = data[1]
        varHeader = struct.pack('!BB', 0 if connCode != 0 else sp, connCode)

        header = b''.join([fixedHeader, varHeader])
        return header


class SubscribePacket(Packet):
    def __init__(self, client):
        super().__init__(client)
        self.topics = []
        self.retCode = 0
        self.packet_id = None

    def decode(self, data, flags):
        if int(flags, 2) != 2:
            self.client.toDC = True
            return

        self.packet_id, = struct.unpack('!H', data[0:2])
        payload_data = data[2:]
        # pachet_id e pentru a nu prelucra acelasi pachet de prea multe ori la QoS

        payload_len = len(payload_data)
        curr = 0
        self.retCode = 0

        while curr < payload_len:
            topic_len, topic = decodeUTF8(payload_data[curr:])
            curr += 2 + topic_len
            qos_byte = format(int.from_bytes(payload_data[curr:curr + 1], 'big'), '#010b')[2:]
            good = fct.reduce(lambda a, b: a and (b == '0'), qos_byte[0:6])
            # if good == false -> malformed packet
            if not good:
                self.client.toDC = True
                return

            qos = int(qos_byte[6:], base=2)
            curr += 1
            self.retCode = qos
            self.topics.append((topic, qos))
            # print(topic, qos)


class PublishPacket(Packet):
    def __init__(self, client):
        super().__init__(client)
        self.retain = False
        self.dup = False
        self.qos = 0
        self.packet_id = None
        self.topic = ''
        self.msg = ''

    def decode(self, data, flags):
        self.retain = flags[3] == '1'
        self.dup = flags[0] == '1'
        self.qos = int(flags[1:3], 2)

        remaining_length = len(data)
        payload_data = data[0:]
        len_topic, topic_name = decodeUTF8(payload_data)

        start_payload = len_topic + 2

        if self.qos > 0:
            self.packet_id = struct.unpack('!H', data[2 + len_topic:2 + len_topic + 2])[0]
            start_payload += 2

        msgpayload = data[start_payload:remaining_length]
        msgpayload = msgpayload.decode(encoding='ascii')
        self.topic = topic_name
        self.msg = msgpayload
        print(topic_name, msgpayload)

    def encode(self, data):
        self.dup = 0

        if self.qos == 3:
            self.client.toDC = True
            return

        if self.qos > data[self.topic]:
            self.qos = data[self.topic]

        fixBits = 48 | self.dup << 3 | self.qos << 1 | self.retain
        lenVarHeader = len(self.topic) + 2 + len(self.msg)
        if self.qos > 0:
            lenVarHeader += 2
            varHeader = struct.pack('!H', len(self.topic)) + bytes(self.topic, encoding='utf-8') + struct.pack('!H',
                                                                                                               self.packet_id)
        else:
            varHeader = struct.pack('!H', len(self.topic)) + bytes(self.topic, encoding='utf-8')
        fixHeader = struct.pack('!BB', fixBits, lenVarHeader)
        payload = bytes(self.msg, encoding='utf-8')
        hearder = b''.join([fixHeader, varHeader, payload])
        return hearder


class PubackPacket(Packet):
    def __init__(self, client):
        super().__init__(client)
        self.packet_id = None

    def decode(self, data, flags):
        reserved = flags[0:4]
        if len(data) != 2:
            self.client.toDC = True
            return
        if int(reserved, 2) != 0:
            self.client.toDC = True
            return
        self.packet_id = struct.unpack('!H', data)[0]

    def encode(self, data):
        fixHeader = struct.pack('!BB', 64, 2)
        self.packet_id = data
        varheader = struct.pack('!H', data)

        header = b''.join([fixHeader, varheader])
        return header


class PubrecPacket(Packet):
    def __init__(self, client):
        super().__init__(client)
        self.packet_id = None

    def decode(self, data, flags):
        reserved = flags[0:4]
        if len(data) != 2:
            self.client.toDC = True
            return
        if int(reserved, 2) != 0:
            self.client.toDC = True
            return

        self.packet_id = struct.unpack('!H', data)[0]

    def encode(self, data):
        fixHeader = struct.pack('!BB', 80, 2)
        self.packet_id = data
        varheader = struct.pack('!H', data)

        header = b''.join([fixHeader, varheader])
        return header


class PubrelPacket(Packet):
    def __init__(self, client):
        super().__init__(client)
        self.packet_id = None

    def decode(self, data, flags):
        reserved = flags[0:4]
        if len(data) != 2:
            self.client.toDC = True
            return
        if int(reserved, 2) != 2:
            self.client.toDC = True
            return
        self.packet_id = struct.unpack('!H', data)[0]

    def encode(self, data):
        fixHeader = struct.pack('!BB', 98, 2)
        self.packet_id = data
        varheader = struct.pack('!H', data)

        header = b''.join([fixHeader, varheader])
        return header


class PubcompPacket(Packet):
    def __init__(self, client):
        super().__init__(client)
        self.packet_id = None

    def decode(self, data, flags):
        reserved = flags[0:4]
        if len(data) != 2:
            self.client.toDC = True
            return
        if int(reserved, 2) != 0:
            self.client.toDC = True
            return
        self.packet_id = struct.unpack('!H', data)[0]

    def encode(self, data):
        fixHeader = struct.pack('!BB', 112, 2)
        self.packet_id = data
        varheader = struct.pack('!H', data)

        header = b''.join([fixHeader, varheader])
        return header


class UnsubscribePacket(Packet):
    def __init__(self, client):
        super().__init__(client)
        self.packet_id = None
        self.topics = []

    def decode(self, data, flags):
        if int(flags, 2) != 2:
            self.client.toDC = True
            return
        self.packet_id, = struct.unpack('!H', data[0:2])
        payload_data = data[2:]

        payload_len = len(payload_data)
        curr = 0

        while curr < payload_len:
            topic_len, topic = decodeUTF8(payload_data[curr:])
            curr += 2 + topic_len
            self.topics.append(topic)


class SubackPacket(Packet):
    def __init__(self, client):
        super().__init__(client)

    def encode(self, data):
        # data - > (packet_id, qos)
        packet_id = data[0]
        qos = data[1]

        fixHeader = struct.pack('!BB', 144, 3)
        varheader = struct.pack('!H', packet_id)

        # failure?
        payload = struct.pack('!B', qos)

        header = b''.join([fixHeader, varheader, payload])
        return header


class UnSubackPacket(Packet):
    def __init__(self, client):
        super().__init__(client)

    def encode(self, data):
        packet_id = data

        fixHeader = struct.pack('!BB', 176, 2)
        varheader = struct.pack('!H', packet_id)

        header = b''.join([fixHeader, varheader])
        return header


class PingReqPacket(Packet):  # asta nu face nimic ptr noi
    def __init__(self, client):
        super().__init__(client)

    def decode(self, data, flags):
        pass


class PingRespPacket(Packet):
    def __init__(self, client):
        super().__init__(client)

    def encode(self, data):
        fixheader = struct.pack('!BB', 208, 0)

        header = b''.join([fixheader])
        return header


class Disconnect(Packet):
    def __init__(self, client):
        super().__init__(client)

    def decode(self, data, flags):
        pass
