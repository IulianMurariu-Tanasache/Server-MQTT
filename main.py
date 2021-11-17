from tkinter import *
from tkinter.ttk import Treeview
from gpiozero import LED

STATE = 0


topics = {
    'topic1': ['client1', 'client4', 'client5', 'client6'],
    'topic2': ['client2', 'client3'],
    'topic3': []
}

led_server = LED


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
            #tree.set(child, 'optiuni', 'disconnect')
        else:
            tree.set(child, 'clienti', '')
            #tree.set(child, 'optiuni', '')
    remaining = len(topics[record]) - len(tree.get_children())
    for i in range(0, remaining):
        tree.insert('', END, values=('', topics[record][len(tree.get_children()) + i], ''))
def Start():
        STATE = True
       # print(STATE)
        print("Serverul se porneste")
def Stop():
        STATE = False
        print("Serverul se opreste")
        #print(STATE)
def NewMenu():
    top = Toplevel()
    top.title("New Menu")
    top.geometry("300x300")
    buton = Button(top, text='close menu', command=top.destroy).place(x=220, y=250)

def delete(parameter):
    print(parameter)
def main():
    root = Tk()
    root.title("Server MQTT")
    root.geometry("1280x730")

    # definirea coloanelor
    columns = ('subiecte', 'clienti', 'optiuni')

    #textbox
    camp = Label(root,text="Logs",borderwidth=4,bg="white",relief="raised",width=42).place(x=600,y=0)

    #listbox

    box = Listbox(root,width=50, height=40,borderwidth=2,relief="raised").place(x=600,y=20)
    box2 = Listbox(root, bg="white", relief="raised", width=100, height=4)
    box2.insert(END,"AFISAT DE LA SERVER")
    box2.place(x=0,y=602)
    # cu insert putem pune ce vrem?
    #box2.insert(1, "AFISAM DE LA SERVER")



    # treeview
    trv = Treeview(root, columns=columns, show='headings',height=29)

    # drop down menu
    clicked = StringVar()
    drop = OptionMenu(root, clicked, "Disconnect", command=delete(trv))
    drop.place(x=500, y=600)


    # definire
    trv.heading('subiecte', text='Subjects')
    trv.heading('clienti', text='Clients')
    trv.heading('optiuni', text='Options')


    # generat random data
    button1 = Button(root, text='Start', activebackground="green",width=20,command=Start).place(x=80, y=690)
    button2 = Button(root, text='Stop',activebackground="red",width=20,command=Stop).place(x=250, y=690)
    button3 = Button(root, text='Configurare',activebackground="orange", width=20 ,command=NewMenu).place(x=420, y=690)

    for topic in topics:
        trv.insert('', END, values=(topic, '', ''))

    trv.bind('<ButtonRelease-1>', select_item)
    trv.grid(row=0, column=0, sticky='nsew')

    # add scroll
    scrollbar = Scrollbar(root, orient=VERTICAL, command=trv.yview)
    trv.configure(yscroll=scrollbar.set)
    scrollbar.grid(row=0, column=1, sticky='ns')
    # run
    root.mainloop()


if __name__ == '__main__':
    main()
