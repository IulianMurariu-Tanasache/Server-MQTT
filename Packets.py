from HelperFunctions import *


class Packet:
    def __init__(self, client):
        self.client = client

    def decode(self, data):
        pass

    def encode(self):
        pass


class ConnectPacket(Packet):
    def __init__(self, client):
        super().__init__(client)

    def decode(self, data):
        prot_len, protocol_name, prot_version, conn_flags, keep_alive = struct.unpack('!H4sBcH', data[0:10])

        protocol_name = protocol_name.decode(encoding='ascii')
        connect_flags = format(ord(conn_flags.decode(encoding='ascii')), '#010b')[2:]

        print(protocol_name)
        print(prot_version)
        print(keep_alive)

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

        # chestii de versiune 5.0
        # var_length, property_length = decodeVariableInt(data[10:])
        # properties_data = data[10 + var_length: 10 + var_length + property_length]
        # properties = struct.unpack('!', properties_data)

        payload_data = data[10:]
        id_len, self.client.id = decodeUTF8(payload_data)
        payload_data = payload_data[2 + id_len[0]:]

        if self.client.will:
            wt_len, self.client.willTopic = decodeUTF8(payload_data)
            msg_len = struct.unpack('!H', payload_data[2 + wt_len[0]:2 + wt_len[0] + 2])
            msg = struct.unpack(f'!{msg_len[0]}s', payload_data[wt_len[0] + 2 + 2:wt_len[0] + 2 + 2 + msg_len[0]])
            print(msg[0].decode(encoding='utf-8'))

        self.client.connected = True

        # de implementat user si parola si restul


class ConnackPacket(Packet):
    def __init__(self, client):
        super().__init__(client)

    def encode(self):
        fixedHeader = struct.pack('!BB', 32, 2)

        # sp daca are deja sesiune sau nu
        varHeader = struct.pack('!BB', 0, 0)

        header = b''.join([fixedHeader, varHeader])
        return header
