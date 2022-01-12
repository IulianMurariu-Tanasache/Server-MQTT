from tkinter import *
from tkinter.ttk import Treeview

from Server import *

topics = {}

selected_client = None
selected_topic = None


def select_item(event):
    global selected_topic
    x, y = event.x, event.y
    if y < 25:
        return
    if 0 <= x <= 200:
        tree = event.widget
        selected_topic = tree.focus()
        if selected_topic == '':
            return
        tree.event_generate("<<Publish>>")
        if selected_topic in topics:
            tree.set(selected_topic, 'clienti', topics[selected_topic])
            tree.item(selected_topic, open=True)
            for topic in topics:
                if topic != selected_topic:
                    tree.set(topic, 'clienti', '')


def NewMenu():
    top = Tk()
    top.title("New Menu")
    top.geometry("400x400")

    #coloane
    colums = ('username', 'password')
    #treeview
    tree = Treeview(top, columns=colums, show='headings')
    tree.heading('username', text="user")
    tree.heading('password', text='pass')
    tree.place(x=0, y=0)

    #citesc din fisier?
    f = open('clients.txt', mode='r')
    print(f.read())

    #campurile ptr select?
    e_name = Entry(top).place(x=50, y=300)
    e_pass = Entry(top).place(x=200, y=300)

    buton = Button(top, text='close menu', command=top.destroy).place(x=300, y=350)
    button1 = Button(top, text='update client', command=modefly).place(x=200, y=350)
    button2 = Button(top, text='delete client', command=delete).place(x=100, y=350)
    button3 = Button(top, text='add client', command=add).place(x=1, y=350)
    f.close()




def add():
    pass


def delete():
    pass


def modefly():
    pass


def main():
    root = Tk()
    root.title("Server MQTT")
    root.geometry("1024x730")

    # definirea coloanelor
    columns = ('subiecte', 'clienti')

    # textboxs
    Logs = Label(root, text="Logs", borderwidth=4, bg="white", relief="raised", width=49, font=('Tahoma', 10))
    Logs.place(x=600, y=0)
    Topics = Label(root, text='Topic', borderwidth=4, bg="white", relief="raised", width=49, font=('Tahoma', 10))
    Topics.place(x=600, y=270)

    # listbox
    logsList = Listbox(root, width=50, height=13, relief="raised", font=('Tahoma', 10))
    logsList.place(x=600, y=26)

    historyList = Listbox(root, width=50, height=11, relief="raised", font=('Tahoma', 10))
    historyList.place(x=600, y=300)

    logBox = Listbox(root, relief="raised", width=125, height=2, font=('Tahoma', 14))
    logBox.insert(0, "  AFISAT DE LA SERVER\n")
    logBox.place(x=0, y=590)

    # treeview
    trv = Treeview(root, columns=columns, show='headings', height=28)
    trv.column('clienti', minwidth=0, width=390, stretch=False)

    def disconnectClient():
        print(f"Disconnect {selected_client}")
        server.discClientById(selected_client)

    def showLogs(event):
        if selected_topic is None or selected_topic not in server.topics_history.keys():
            return
        lisy = server.topics_history[selected_topic]
        Topics.config(text=selected_topic)
        historyList.delete(0, END)
        for i in range(len(server.topics_history[selected_topic])):
            historyList.insert(i, lisy[-1 * (1 + i)])

    drop = Menu(root, tearoff=0)
    drop.add_command(label="Disconnect", command=disconnectClient)

    def do_popup(event):
        global selected_client, selected_topic
        if 201 <= event.x <= 400 and event.y >= 25:
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

    server = Server(logBox, logsList, trv)

    button1 = Button(root, text='Start', activebackground="green", width=20, command=server.start).place(x=80, y=670)
    button2 = Button(root, text='Stop', activebackground="red", width=20, command=server.stop).place(x=250, y=670)
    button3 = Button(root, text='Configurare', activebackground="orange", width=20, command=NewMenu).place(x=420, y=670)

    def addTopics():
        global topics
        for topic in topics:
            if '/' in topic:
                pid = ''
                index = 0
                t = topic[0:topic.find('/')]
                next = topic[topic.find('/') + 1:]
                if t not in trv.get_children():
                    trv.insert(pid, END, iid=t, values=(t, '', ''))
                pid = t
                while '/' in next:
                    index += 1
                    t = next[0:next.find('/')]
                    next = next[next.find('/') + 1:]
                    id = pid + '/' + t
                    if id not in trv.get_children(pid):
                        trv.insert(pid, END, iid=id, values=(index * '   ' + t, '', ''))
                    pid += '/' + t
                t = next
                index += 1
                id = pid + '/' + t
                if id not in trv.get_children(pid):
                    trv.insert(pid, END, iid=id, values=(index * '   ' + t, '', ''))
            else:
                if topic not in trv.get_children():
                    trv.insert('', END, iid=topic, values=(topic, '', ''))

    def onSub(event):
        global topics
        topics = {}
        for t in server.topics.keys():
            clients = []
            for c in server.topics[t]:
                clients.append(c.id)
            topics[t] = clients
        trv.delete(*trv.get_children())
        addTopics()

    trv.bind('<ButtonRelease-1>', select_item)
    trv.bind('<<Subscribe>>', onSub)
    trv.bind('<<Publish>>', showLogs)
    trv.grid(row=0, column=0, sticky='nsew')

    def on_closing():
        server.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()
