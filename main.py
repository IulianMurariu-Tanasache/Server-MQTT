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
    # select doar topicuri(0,25 ->200,25); h = 450
    if 0 <= x <= 200:
        tree = event.widget
        selected_topic = tree.focus()
        if selected_topic == '':
            return
        tree.event_generate("<<Publish>>")
        if selected_topic in topics:
            tree.set(selected_topic, 'clienti', topics[selected_topic])
            tree.item(selected_topic, open=True)  # not tree.item(selected_topic, 'open')
            for topic in topics:
                if topic != selected_topic:
                    tree.set(topic, 'clienti', '')


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
    Logs = Label(root, text="Logs", borderwidth=4, bg="white", relief="raised", width=49, font=('Tahoma', 10)).place(
        x=600, y=0)
    Topics = Label(root, text='Topic', borderwidth=4, bg="white", relief="raised", width=49, font=('Tahoma', 10)).place(
        x=600, y=270)

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

    def disconnectClient():
        print(f"Disconnect {selected_client}")
        server.discClientById(selected_client)

    def showLogs(event):
        if selected_topic is None or selected_topic not in server.topics_history.keys():
            return
        lisy = server.topics_history[selected_topic]
        historyList.delete(0, END)
        for i in range(len(server.topics_history[selected_topic])):
            historyList.insert(i, lisy[-1 * (1+i)])

    # drop down menu
    drop = Menu(root, tearoff=0)
    drop.add_command(label="Disconnect", command=disconnectClient)

    #drop2 = Menu(root, tearoff=0)
    #drop2.add_command(label="View Logs", command=showLogs)

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
        # if 0 <= event.x <= 200 and event.y >= 25:
        #     try:
        #         # select doar topics(0-200,25)
        #         tree = event.widget
        #         iid = tree.identify_row(event.y)
        #         if iid:
        #             tree.selection_set(iid)
        #             selected_topic = iid
        #             drop2.tk_popup(event.x_root, event.y_root)
        #     finally:
        #         drop2.grab_release()

    trv.bind("<Button-3>", do_popup)

    # definire
    trv.heading('subiecte', text='Subjects')
    trv.heading('clienti', text='Clients')
    trv.heading('optiuni', text='Options')

    server = Server(logBox, logsList, trv)

    # generat random data
    button1 = Button(root, text='Start', activebackground="green", width=20, command=server.start).place(x=80, y=670)
    button2 = Button(root, text='Stop', activebackground="red", width=20, command=server.stop).place(x=250, y=670)
    button3 = Button(root, text='Configurare', activebackground="orange", width=20, command=NewMenu).place(x=420, y=670)

    def addTopics():
        for topic in server.topics:
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
        topics = server.topics
        trv.delete(*trv.get_children())
        topics = server.topics
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
