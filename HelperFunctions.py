import struct

packet_types_to_int = {
    'Reserverd': 0,
    'CONNECT': 1,
    'CONNACK': 2,
    'PUBLISH': 3,
    'PUBACK': 4,
    'PUBREC': 5,
    'PUBCOMP': 6,
    'PUBREL': 7,
    'SUBSCRIBE': 8,
    'SUBACK': 9,
    'UNSUBSCRIBE': 10,
    'UNSUBACK': 11,
    'PINGREQ': 12,
    'PINGRESP': 13,
    'DISCONNECT': 14,
    'AUTH': 15
}

packet_types_to_string = dict(zip(packet_types_to_int.values(), packet_types_to_int.keys()))


def decodeUTF8(data):
    length = struct.unpack('!H', data[0:2])
    return length, struct.unpack(f'!{length[0]}s', data[2: 2 + length[0]])


def decodeVariableInt(byte):
    # variable int decodare luata din documentatia mqtt
    # returneaza cati octeti a avut lungimea si cat e rezultatul decodarii
    multiplier = 1
    val = 0
    i = 0
    binary = int.from_bytes(byte[i:i + 1], "big")
    while True:
        val += (binary & 127) * multiplier
        if binary & 128 == 0:
            break
        multiplier = multiplier * 128
        i += 1
        binary = int.from_bytes(byte[i:i + 1], "big")
    return i + 1, val
