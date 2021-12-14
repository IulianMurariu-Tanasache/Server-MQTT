import tkinter.ttk
from tkinter import *
from tkinter.ttk import Treeview
from Server import *

topics = {}

#lol

selected_client = None
selected_topic = None


def select_item(event):
    global selected_topic
    x, y = event.x, event.y
    if y < 25:
        return
    # select doar topicuri(0,25 ->200,25); h = 45
    if 0 <= x <= 200:
        tree = event.widget
        selected = tree.focus()
        selected_topic = selected[1:]
        if selected_topic == '':
            return
        lvl = selected_topic
        dic = topics
        while '/' in lvl:
            dic = dic[lvl[0:lvl.find('/')]]
            lvl = lvl[lvl.find('/') + 1:]
        record = dic[lvl]
        if type(record) is dict:
            tree.item(selected, open=True)
            for i in range(0, len(tree.get_children())):
                child = tree.get_children()[i]
                if '#' in record.keys() and i < len(record['#']):
                    tree.set(child, 'clienti', record['#'][i])
                else:
                    tree.set(child, 'clienti', '')
            return
        for i in range(0, len(tree.get_children())):
            child = tree.get_children()[i]
            if i < len(record):
                tree.set(child, 'clienti', record[i])
            else:
                tree.set(child, 'clienti', '')
        remaining = len(record) - len(tree.get_children())
        for i in range(0, remaining):
            tree.insert('', END, values=('', record[len(tree.get_children()) + i], ''))


def NewMenu():
    top = Toplevel()
    top.title("New Menu")
    top.geometry("300x300")
    buton = Button(top, text='close menu', command=top.destroy).place(x=200, y=250)


def main():
    root = Tk()
    root.title("Server MQTT")
    root.geometry("1024x730")

    # definirea coloanelor
    columns = ('subiecte', 'clienti', 'optiuni')

    # textboxs
    Logs = Label(root, text="Logs", borderwidth=4, bg="white", relief="raised", width=49, font=('Tahoma', 10)).place(x=600, y=0)
    Topics = Label(root, text='Topic', borderwidth=4, bg="white", relief="raised", width=49, font=('Tahoma', 10)).place(x=600, y=250)

    # listbox
    logsList = Listbox(root, width=50, height=13, relief="raised", font=('Tahoma', 10))
    logsList.place(x=600, y=26)

    historyList = Listbox(root, width=50, height=13, relief="raised", font=('Tahoma', 10))
    historyList.place(x=600, y=274)

    logBox = Listbox(root, relief="raised", width=125, height=2, font=('Tahoma', 14))
    logBox.insert(0, "  AFISAT DE LA SERVER\n")
    logBox.place(x=0, y=590)

    # treeview
    trv = Treeview(root, columns=columns, show='headings', height=28)

    def disconnectClient():
        print(f"Disconnect {selected_client}")
        server.discClient(selected_client)

    def showLogs():
        print(f"show logs for {selected_topic}")
        print(server.topics_history[selected_topic])

    # drop down menu
    drop = Menu(root, tearoff=0)
    drop.add_command(label="Disconnect", command=disconnectClient)

    drop2 = Menu(root, tearoff=0)
    drop2.add_command(label="View Logs", command=showLogs)

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
        if 0 <= event.x <= 200 and event.y >= 25:
            try:
                # select doar topics(0-200,25)
                tree = event.widget
                iid = tree.identify_row(event.y)
                if iid:
                    tree.selection_set(iid)
                    selected_topic = iid[1:]
                    drop2.tk_popup(event.x_root, event.y_root)
            finally:
                drop2.grab_release()

    trv.bind("<Button-3>", do_popup)

    # definire
    trv.heading('subiecte', text='Subjects')
    trv.heading('clienti', text='Clients')
    trv.heading('optiuni', text='Options')

    server = Server(logBox, logsList, historyList,trv)

    # generat random data
    button1 = Button(root, text='Start', activebackground="green", width=20, command=server.start).place(x=80, y=670)
    button2 = Button(root, text='Stop', activebackground="red", width=20, command=server.stop).place(x=250, y=670)
    button3 = Button(root, text='Configurare', activebackground="orange", width=20, command=NewMenu).place(x=420, y=670)

    def dfsDict(dic, pid, indent):
        if type(dic) is not dict:
            return
        for _keys in dic.keys():
            if _keys not in ['#', '+']:
                name = ' ' * 2 * indent + str(_keys)
                if type(dic[_keys]) is dict:
                    name = name + '/'
                trv.insert(pid, END, iid=pid + '/' + str(_keys), values=(name, '', ''))
                dfsDict(dic[_keys], pid + '/' + str(_keys), indent + 1)

    def onSub(event):
        global topics
        topics = server.topics
        trv.delete(*trv.get_children())
        dfsDict(topics, '', 0)

    trv.bind('<ButtonRelease-1>', select_item)
    trv.bind('<<Subscribe>>', onSub)
    trv.grid(row=0, column=0, sticky='nsew')

    # add scroll
   # scrollbar = Scrollbar(root, orient=VERTICAL, command=trv.yview)
    #trv.configure(yscroll=scrollbar.set)
    #scrollbar.grid(row=0, column=1, sticky='ns')

    def on_closing():
        server.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()
