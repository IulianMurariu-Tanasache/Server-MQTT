import struct

from HelperFunctions import *
import functools as fct


# de mutat in server


class Session:
    def __init__(self, _id, topics):
        self.client_id = _id
        self.topics = topics


class Packet:
    def __init__(self, client):
        self.client = client

    def decode(self, data):
        pass

    def encode(self, data):
        pass


class ConnectPacket(Packet):
    def __init__(self, client, clients, sessions):
        super().__init__(client)
        self.clients = clients
        self.sessions = sessions

    def decode(self, data):
        prot_len, protocol_name, prot_version, conn_flags, keep_alive = struct.unpack('!H4sBcH', data[0:10])

        protocol_name = protocol_name.decode(encoding='utf-8')
        connect_flags = bin(int.from_bytes(conn_flags, 'big')).lstrip('0b')

        # print(protocol_name)
        # print(prot_version)
        # print(keep_alive)

        if protocol_name != 'MQTT' or prot_version != 4:
            print('Eroare conectare1')
            return

        reserved = connect_flags[7] == '1'
        print(reserved, connect_flags[0], connect_flags, connect_flags[1])

        if reserved:
            print('Eroare conectare2')
            return

        clean_start = connect_flags[6] == '1'
        # TODO: implementare sesiune, will message, QoS, willRetain, password, username, keep alive, session expiry, user prop?, auth method?, auth data?

        self.client.will = connect_flags[5] == '1'
        self.client.willQoS = int(connect_flags[3:5], 2)
        self.client.willRetain = connect_flags[2] == '1'
        password = connect_flags[1] == '1'
        username = connect_flags[0] == '1'
        self.client.keepAlive = keep_alive

        payload_data = data[10:]
        id_len, self.client.id = decodeUTF8(payload_data)
        payload_data = payload_data[2 + id_len:]

        for c in self.clients:
            if self.client.id == c.id and self.client != c:
                c.conn.shutdown(2)
                c.conn.close()

        if self.client.will:
            wt_len, self.client.willTopic = decodeUTF8(payload_data[0:])
            msg_len = struct.unpack('!H', payload_data[2 + wt_len:2 + wt_len + 2])[0]
            msg = struct.unpack(f'!{msg_len}s', payload_data[wt_len + 2 + 2:wt_len + 2 + 2 + msg_len])[0]
            payload_data = payload_data[wt_len + 2 + 2 + msg_len:]
            print(msg)

        # de implementat user si parola si restul
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

        if clean_start:
            [self.sessions.remove(s) for s in self.sessions if s.client_id == self.client.id]
            self.sessions.append(Session(self.client.id, []))
            self.sessionPresent = False
        else:
            exists = False
            for s in self.sessions:
                if s.client_id == self.client.id:
                    exists = True
                    self.client.topics = s.topics
            if not exists:
                self.sessions.append(Session(self.client.id, []))
            self.sessionPresent = exists

        self.client.connected = True


class ConnackPacket(Packet):
    # de revenit pentru sesiune si raspuns negativ
    def __init__(self, client):
        super().__init__(client)

    def encode(self, data):
        fixedHeader = struct.pack('!BB', 32, 2)

        # sp daca are deja sesiune sau nu
        varHeader = struct.pack('!BB', data, 0)

        header = b''.join([fixedHeader, varHeader])
        return header


class SubscribePacket(Packet):
    def __init__(self, client):
        super().__init__(client)

    def decode(self, data):
        packet_id, = struct.unpack('!H', data[0:2])
        payload_data = data[2:]
        # pachet_id e pentru a nu prelucra acelasi pachet de prea multe ori la QoS

        # if data is gol -> protocol violation
        payload_len = len(payload_data)
        curr = 0

        while curr < payload_len:
            topic_len, topic = decodeUTF8(payload_data[curr:])
            curr += 2 + topic_len
            qos_byte = format(int.from_bytes(payload_data[curr:curr + 1], 'big'), '#010b')[2:]
            good = fct.reduce(lambda a, b: a and (b == '0'), qos_byte[0:6])
            print(good)
            # if good == false -> malformed packet
            qos = int(qos_byte[6:], base=2)

            # if qos > 2 -> malformed packet
            curr += 1

            self.client.topics.append(topic)
            print(topic, qos)


class PublishPacket(Packet):
    def __init__(self, client):
        super().__init__(client)

    def decode(self, data):
        remaining_length = len(data)
        payload_data = data[0:]
        len_topic, topic_name = decodeUTF8(payload_data)

        start_payload = len_topic + 2

        # Packet.packet_indentifer = struct.unpack('!H', data[5:7])

        msgpayload = data[start_payload:remaining_length]
        msgpayload = msgpayload.decode(encoding='utf-8')  # struct.unpack(f'!{len_payload}s', msgpayload)
        self.topic = topic_name
        self.msg = msgpayload
        print(topic_name, msgpayload)


# cumva pe interfata


class PubackPacket(Packet):
    def __init__(self, client):
        super().__init__(client)

    def encode(self, data):
        fixHeader = struct.pack('!BB', 64, 2)

        varheader = struct.pack('!H', data)  # nu se stie ce aere

        header = b''.join([fixHeader, varheader])
        return header


class PubrecPacket(Packet):
    def __init__(self, client):
        super().__init__(client)

    def encode(self, data):
        fixHeader = struct.pack('!BB', 80, 2)

        varheader = struct.pack('!BB', 0, 0)  # idnet variable?

        header = b''.join([fixHeader, varheader])
        return header


class PubrelPacket(Packet):
    def __init__(self, client):
        super().__init__(client)

    def encode(self, data):  # asta era dee decodat
        fixHeader = struct.pack('!BB', 98, 2)

        varheader = struct.pack('!BB', 0, 0)  # idnet variable?

        header = b''.join([fixHeader, varheader])
        return header


class PubcompPacket(Packet):
    def __init__(self, client):
        super().__init__(client)

    def encode(self, data):
        fixHeader = struct.pack('!BB', 112, 2)

        varheader = struct.pack('!BB', 0, 0)  # idnet variable?

        header = b''.join([fixHeader, varheader])
        return header


class UnsubscribePacket(Packet):
    def __init__(self, client):
        super().__init__(client)

    def decode(self, data):
        pass


class SubackPacket(Packet):  # encode
    def __init__(self, client):
        super().__init__(client)

    def encode(self, data):
        pass


class UnSubackPacket(Packet):  # encode
    def __init__(self, client):
        super().__init__(client)

    def encode(self, data):
        pass


class PingReqPacket(Packet):
    def __init__(self, client):
        super().__init__(client)

    def decode(self, data):
        pass


class PingRespPacket(Packet):
    def __init__(self, client):
        super().__init__(client)

    def encode(self, data):
        pass


class Disconnect(Packet):
    def __init__(self, client):
        super().__init__(client)

    def decode(self, data):
        pass
