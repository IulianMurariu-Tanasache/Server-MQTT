from tkinter import *
from tkinter.ttk import Treeview

topics = {
    'topic1': ['client1', 'client4', 'client5', 'client6'],
    'topic2': ['client2', 'client3'],
    'topic3': []
}


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


def main():
    root = Tk()
    root.title("Server MQTT")
    root.geometry("1024x720")

    # definirea coloanelor
    columns = ('subiecte', 'clienti', 'optiuni')

    # treeview
    trv = Treeview(root, columns=columns, show='headings')

    # definire
    trv.heading('subiecte', text='Subjects')
    trv.heading('clienti', text='Clients')
    trv.heading('optiuni', text='Options')

    # generat random data
    # button2 = Button(root, text='history')

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
