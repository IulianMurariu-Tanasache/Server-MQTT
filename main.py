import tkinter
from tkinter import*
from tkinter import ttk
from tkinter.messagebox import showinfo

root =Tk()
root.title("Server MQTT")
root.geometry("630x230")


#definirea coloanelor
columns = ('subiecte','clienti','optiuni')

#treeview
trv= ttk.Treeview(root,columns=columns,show='headings')


#definire
trv.heading('subiecte',text='Subjects')
trv.heading('clienti',text='Clients')
trv.heading('optiuni',text='Options')

#generat random data
button1 = Button(root,text='disconect').place(x=300,y=200)
button2 = Button(root,text='history')

data =[]
for index in range(1,5):
    for indej in range(1,10):
        data.append(("subiect",f'clientul{indej}',f'{indej}'))


#insertia prporiu zisa
for campul in data:
    trv.insert('',tkinter.END,values=campul)

def item_data(event):
    for current_data in trv.selection():
        item = trv.item(current_data)
        record = item['values']

        showinfo(title='Info',messages=','.join(record))
trv.bind('<<Table>>',item_data)
trv.grid(row=0,column=0,sticky='nsew')

#TODO:incearca cumva sa parcurgi sub si clientii
#TODO:daca selectezi un subiect sa afisezi


#add scroll
scrollbar = ttk.Scrollbar(root,orient=VERTICAL,command=trv.yview)
trv.configure(yscroll=scrollbar.set)
scrollbar.grid(row=0,column=1,sticky='ns')
#run
root.mainloop()