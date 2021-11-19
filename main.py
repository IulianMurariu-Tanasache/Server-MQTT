import socket
import threading
import traceback
from tkinter import *
from tkinter.ttk import Treeview
import struct

# TODO:
#   -clase separate pentru fiecare pachet si mosteneste packet
#   -pack()/unpack() cu struct
#   -imlpementare un switch/multe if-uri care sa aleaga ce pachet sa fie decodat/encodat
#   -implementare toate prostiile alea


topics = {
    'topic1': ['client1', 'client4', 'client5', 'client6'],
    'topic2': ['client2', 'client3'],
    'topic3': []
}

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


def decodeFixedHeader(data, client):
    binary = format(int.from_bytes(data[0:1], "big"), '#010b')[2:]
    packet_type = int(binary[0:4], 2)
    flags = binary[4:]
    print(packet_types_to_string[packet_type])
    var_length, remaining_length = decodeVariableInt(data[1:])
    ConnectPacket(client).decode(data[1 + var_length:])


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


class Packet:
    def __init__(self, client):
        self.client = client

     # def decode(self, data):
     #     pass


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

        if protocol_name != 'MQTT' or prot_version != 5:
            print('Eroare conectare1')
            return

        reserved = connect_flags[7] == '1'
        print(reserved, connect_flags[0], connect_flags, connect_flags[1])

        if reserved:
            print('Eroare conectare2')
            return

        clean_start = connect_flags[6] == '1'
        #TODO: implementare sesiune, will message, QoS, willRetain, password, username, keep alive, session expiry, user prop?, auth method?, auth data?

        self.client.will = connect_flags[5] == '1'
        self.client.willQoS = int(connect_flags[3:5], 2)
        self.client.willRetain = connect_flags[2] == '1'
        password = connect_flags[1] == '1'
        username = connect_flags[0] == '1'
        self.client.keepAlive = keep_alive

        var_length, property_length = decodeVariableInt(data[10:])
        properties = data[10 + var_length: 10 + var_length + property_length]

        # unpack properties

        payload = data[10 + var_length + property_length:]

        # unpack payload


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
        self.willDelay = 0
        self.messageExpiry = 0
        self.lastWill = ''

    def setConnected(self, con):
        self.connected = con


class Server:
    def __init__(self, logBox, logs):
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
                new_client.setConnected(True)
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
        self.listenThread = threading.Thread(target=self.listen, args=())
        self.listenThread.start()
        self.handleClientsThread = threading.Thread(target=self.handle_clients, args=())
        self.handleClientsThread.start()

    def stop(self):
        if not self.state:
            return
        self.state = False
        self.socket.close()
        self.printLog('Stopping server...')
        # print("Serverul se opreste")

    def handle_clients(self):
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
                    decodeFixedHeader(data, client)
            # print(addr, ' a trimis: ', data)


def select_item(event):
    tree = event.widget
    selected = tree.focus()
    record = tree.item(selected)['values'][0]
    if record == '':
        return
    print(topics[record])
    # print(tree.item(tree.get_children()[0]))
    for i in range(0, len(tree.get_children())):
        # item = tree.item(child)
        child = tree.get_children()[i]
        if i < len(topics[record]):
            tree.set(child, 'clienti', topics[record][i])
            # tree.set(child, 'optiuni', 'disconnect')
        else:
            tree.set(child, 'clienti', '')
            # tree.set(child, 'optiuni', '')
    remaining = len(topics[record]) - len(tree.get_children())
    for i in range(0, remaining):
        tree.insert('', END, values=('', topics[record][len(tree.get_children()) + i], ''))


def NewMenu():
    top = Toplevel()
    top.title("New Menu")
    top.geometry("300x300")
    buton = Button(top, text='close menu', command=top.destroy).place(x=200, y=250)


def delete(parameter):
    print(parameter)


def main():
    root = Tk()
    root.title("Server MQTT")
    root.geometry("1024x730")

    # definirea coloanelor
    columns = ('subiecte', 'clienti', 'optiuni')

    # textbox
    camp = Label(root, text="Logs", borderwidth=4, bg="white", relief="raised", width=49, font=('Tahoma', 10)).place(
        x=600, y=0)

    # listbox
    logsList = Listbox(root, width=47, height=10, relief="raised", font=('Tahoma', 10))
    logsList.place(x=622, y=30)
    logBox = Listbox(root, relief="raised", width=125, height=2, font=('Tahoma', 14))
    logBox.insert(0, "AFISAT DE LA SERVER\n")
    logBox.place(x=0, y=600)

    # treeview
    trv = Treeview(root, columns=columns, show='headings', height=28)

    # drop down menu
    clicked = StringVar()
    drop = OptionMenu(root, clicked, "Disconnect", command=delete(trv))
    drop.place(x=900, y=690)

    # definire
    trv.heading('subiecte', text='Subjects')
    trv.heading('clienti', text='Clients')
    trv.heading('optiuni', text='Options')

    server = Server(logBox, logsList)

    # generat random data
    button1 = Button(root, text='Start', activebackground="green", width=20, command=server.start).place(x=80, y=690)
    button2 = Button(root, text='Stop', activebackground="red", width=20, command=server.stop).place(x=250, y=690)
    button3 = Button(root, text='Configurare', activebackground="orange", width=20, command=NewMenu).place(x=420, y=690)

    for topic in topics:
        trv.insert('', END, values=(topic, '', ''))

    trv.bind('<ButtonRelease-1>', select_item)
    trv.grid(row=0, column=0, sticky='nsew')

    # add scroll
    scrollbar = Scrollbar(root, orient=VERTICAL, command=trv.yview)
    trv.configure(yscroll=scrollbar.set)
    scrollbar.grid(row=0, column=1, sticky='ns')

    def on_closing():
        server.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()
