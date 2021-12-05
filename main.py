import tkinter.ttk
from tkinter import *
from tkinter.ttk import Treeview
from Server import *

# !!!!!!!!!!!!
# Am trecut pe versiune 3.1.1 de MQTT
# !!!!!!!!!!!!
# TODO:
#   -clase separate pentru fiecare pachet si mosteneste packet
#   -pack()/unpack() cu struct
#   -imlpementare un switch/multe if-uri care sa aleaga ce pachet sa fie decodat/encodat in handleClient


# topics = {
#     'topic1': ['client1', 'client4', 'client5', 'client6'],
#     'topic2': ['client2', 'client3'],
#     'topic3': []
# }

topics = {}

selected_client = None
selected_topic = None


def select_item(event):
    global selected_topic
    x, y = event.x, event.y
    # print(x, y)
    if y < 25:
        return
    # select doar topicuri(0,25 ->200,25); h = 45
    if 0 <= x <= 200:
        tree = event.widget
        selected = tree.focus()
        selected_topic = tree.item(selected)['values'][0]
        record = tree.item(selected)['values'][0]
        record = record.strip()
        record = record.replace('/','')
        if record == '':
            return
        elif type(topics[record]) is dict:
            tree.item(selected, open=True)
            return
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


def delete():
    print(f"Disconnect {selected_client}")
    # DISCONNECT


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
    logsList.place(x=632, y=30)
    logBox = Listbox(root, relief="raised", width=125, height=2, font=('Tahoma', 14))
    logBox.insert(0, "AFISAT DE LA SERVER\n")
    logBox.place(x=0, y=600)

    # treeview
    trv = Treeview(root, columns=columns, show='headings', height=28)

    # drop down menu
    clicked = StringVar()
    drop = Menu(root, tearoff=0)
    drop.add_command(label="Disconnect", command=delete)

    def do_popup(event):
        global selected_client
        if not (201 <= event.x <= 400 and event.y >= 25):
            return
        try:
            # select doar clienti(201,25->400,25)

            tree = event.widget
            # select row under mouse
            iid = tree.identify_row(event.y)
            if iid:
                # mouse pointer over item
                tree.selection_set(iid)
                selected_client = tree.item(iid)['values'][1]
                drop.tk_popup(event.x_root, event.y_root)
        finally:
            drop.grab_release()

    trv.bind("<Button-3>", do_popup)

    # definire
    trv.heading('subiecte', text='Subjects')
    trv.heading('clienti', text='Clients')
    trv.heading('optiuni', text='Options')

    server = Server(logBox, logsList, trv)

    # generat random data
    button1 = Button(root, text='Start', activebackground="green", width=20, command=server.start).place(x=80, y=690)
    button2 = Button(root, text='Stop', activebackground="red", width=20, command=server.stop).place(x=250, y=690)
    button3 = Button(root, text='Configurare', activebackground="orange", width=20, command=NewMenu).place(x=420, y=690)

    def dfsDict(dic, key, id, indent):
        if type(dic) is not dict:
            return
        for keys in dic.keys():
            id = id + key
            name = ' ' * 2 * indent + keys
            if type(dic[keys]) is dict:
                name = name + '/'
            trv.insert(id, END, iid=id + keys, values=(name, '', ''))
            dfsDict(dic[keys], keys, id, indent + 1)

    def onSub(event):
        global topics
        topics = server.topics
        trv.delete(*trv.get_children())
        dfsDict(topics, '', '', 0)

    trv.bind('<ButtonRelease-1>', select_item)
    trv.bind('<<Subscribe>>', onSub)
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
