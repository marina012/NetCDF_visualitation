#import APIs
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import datetime
from datetime import datetime
from dateutil import parser
import numpy as np
import os, shutil
import requests
import json
from netCDF4 import Dataset

#import satellite submodules
from wq_modules import sentinel
from wq_modules import landsat
from wq_modules import water
from wq_modules import clouds
from wq_modules import modeling_file

#import meteo submodules
from wq_modules import meteo

#import general submodules
from wq_modules import utils
from wq_modules import config

#widget
import ipywidgets as widgets
from ipywidgets import HBox, VBox, Layout
from IPython.display import display
from IPython.display import clear_output

import re



#Model visualization

ruta= "/home/jovyan/datasets"

def nombre_modelo(nombre):
    return re.findall(r'/home/jovyan/datasets/([A-Za-z0-9\_\-]*)',nombre)[0]

def busca_modelos(ruta):
    files= [os.path.abspath(arch.path) for arch in os.scandir(ruta) if arch.is_file()]
    lstFiles = []
    for fichero in files:
        (nombreFichero, extension) = os.path.splitext(fichero)
        if(extension == ".nc"):
            lstFiles.append(nombre_modelo(nombreFichero))
            #print (nombreFichero+extension)
    return(lstFiles)

opt = busca_modelos(ruta)

selection = widgets.Select(
    options=opt,
    value=opt[0],
    # rows=10,
    description='Models',
    disabled=False,
    layout=Layout(width='75%')
)

depth_wid = widgets.IntSlider(
    value=7,
    min=0,
    max=35,
    step=1,
    description='Layer (depth):',
    disabled=False,
    continuous_update=False,
    orientation='horizontal',
    readout=True,
    readout_format='d'
)
button3 = widgets.Button(
    description='Show model output',
)

out3 = widgets.Output()




@button3.on_click
def model_on_click(b):
    global dataset, lista, propiedades
    nombre_dataset= ruta+"/"+selection.value+".nc"
    dataset= Dataset(nombre_dataset, 'r', format='NETCDF4_CLASSIC')
    lista=[[],[],[]]
    propiedades=[[],[],[],[],[]]
    carga_variables()
    set_display()
    with out3:
        clear_output()
        propiedades[0]=0
        propiedades[1]=drop_date.value
        propiedades[2]=depth_wid.value
        propiedades[3]= None
        propiedades[4]= None
        actualiza_layout()


            
            
vbox3 = VBox(children=[selection,button3,out3])
vbox1 = VBox()



def carga_variables():
    global drop_var, lista, time
    for n in dataset.variables.keys():
        if n.find("time") >= 0:
            time=n
        dimensiones=''
        for i in dataset.variables[n].dimensions:
            dimensiones= dimensiones+" "+i
        
        dim=len(dataset.variables[n].dimensions)
        if dim > 2 and dim <5:
            lista[0]= np.append(lista[0],n)
            lista[1]= np.append(lista[1],dim)
            lista[2]= np.append(lista[2],dimensiones)

def set_display():
    global drop_var, drop_date, depth_wid, hb_3d, hb_2d, vb_ev_2d, vb_ev_3d, valor_x, valor_y, date
    drop_var=widgets.Dropdown(
        options=[(lista[0][n], n) for n in range(len(lista[0]))],
        value=0,
        description='Variables:',
    )
    date= set_date()
    drop_date=widgets.Dropdown(
        options=[(str(date[i]), i) for i in range(len(date))],
        value=0,
        description='Fecha:',
    )
    drop_date.observe(date_on_change, names='value')
    drop_var.observe(variable_on_change, names='value')
    hb_3d= HBox([drop_var, drop_date, depth_wid])
    hb_2d= HBox([drop_var, drop_date])
    
    
    valor_x= widgets.BoundedFloatText(
    value=0,
    min=0,
    max=94,
    step=1,
    description='x:'
    )
    valor_y= widgets.BoundedFloatText(
        value=0,
        min=0,
        max=121,
        step=1,
        description='y:'
    )

    boton_tiempo= widgets.Button(
        description='Time'
    )

    boton_prof= widgets.Button(
        description='Depth'
    )

    Label_cor= widgets.Label("Click on the map to choose the coordinates of which to see the evolution:")

    vb_ev_text= VBox([valor_x, valor_y])
    vb_ev_bot= VBox([boton_tiempo, boton_prof])
    hb_ev_3d= HBox([vb_ev_text, vb_ev_bot, depth_wid])
    hb_ev_2d= HBox([vb_ev_text, boton_tiempo])
    vb_ev_3d= VBox([Label_cor, hb_ev_3d])
    vb_ev_2d= VBox([Label_cor, hb_ev_2d])
    
    boton_prof.on_click(on_button_clicked_ev_prof)
    boton_tiempo.on_click(on_button_clicked_ev_time)

    
def set_date():
    date=[]
    for i in range(len(dataset.variables[time])-1):
        date=np.append(date, humanize_time(dataset.variables[time][i]))
    return date

def humanize_time(secs):
    mins, secs = divmod(secs, 60)
    hours, mins = divmod(mins, 60)
    return '%02d:%02d:%02d' % (hours, mins, secs)  




def actualiza_layout():

    clear()
    des=""
    try:
        des=lista[0][propiedades[0]]+": "+dataset.variables[lista[0][propiedades[0]]].long_name
    except:
        des="Variable sin descripción"
        
    label= widgets.Label(des)
    if lista[1][propiedades[0]]==4:
        display(hb_3d, label)
        aux=dataset.variables[lista[0][propiedades[0]]][propiedades[1],propiedades[2],:,:]
        ev=vb_ev_3d
        
    if lista[1][propiedades[0]]==3:
        display(hb_2d, label)
        aux=dataset.variables[lista[0][propiedades[0]]][propiedades[1],:,:]
        ev=vb_ev_2d
        
    try:
        widgets.Label(lista[0][propiedades[0]],": ",dataset.variables[lista[0][propiedades[0]]].long_name)
    except:
        widgets.Label("Variable sin descripción")
    
    v_m= np.amin(aux[:])
    if v_m != np.nan and v_m < 0:
        aux[ aux==v_m ] = np.nan
        
    #aux[ aux==0 ] = np.nan
    fig= plt.figure()
    fig.add_subplot()
    cmap = matplotlib.cm.jet
    cmap.set_bad('grey',1.)

    plt.imshow(np.transpose(aux), interpolation='nearest', vmin= propiedades[3], vmax= propiedades[4],cmap=cmap)
    cbar=plt.colorbar()
    try:
        cbar.set_label(dataset.variables[lista[0][propiedades[0]]].units)
    except:
        cbar.set_label("Unidades no especificadas")
    plt.title(lista[0][propiedades[0]])
    plt.ylabel("Latitude")
    plt.xlabel("Longitude")
    plt.show()
    
    cid = fig.canvas.mpl_connect('button_press_event', onclick)
    
    display(ev)
    
def onclick(event):
    global valor_x, valor_y
    valor_x.value=int(event.xdata)
    valor_y.value=int(event.ydata)
    
def clear():
    clear_output()
    plt.close()
    
    
def variable_on_change(v):
    propiedades[0]=v['new']
    propiedades[3]= None
    propiedades[4]= None
    calcula_min_max()
    actualiza_layout()
    
    
def calcula_min_max():
    var= dataset.variables[lista[0][propiedades[0]]][:]
    v_max= np.amax(var[:])
    v_m= np.amin(var[:])

    var[ var==v_m ] = v_max+10
    v_min= np.amin(var[:])

    var[ var==v_max+10 ] = v_m

    propiedades[3]=v_min
    propiedades[4]=v_max

def slider_on_change(v):
    
    propiedades[2]=v['new']
    actualiza_layout()
    
depth_wid.observe(slider_on_change, names='value')


def date_on_change(v):
    propiedades[1]=v['new']
    actualiza_layout()
    
    
def muestra_ev_prof():
    fig3= plt.figure()
    fig3.add_subplot()
    eje_y=[i for i in range(34)]
    eje_x=[dataset.variables[lista[0][propiedades[0]]][propiedades[1],i,valor_x.value, valor_y.value] for i in range(34)]
    
    plt.plot(eje_x,eje_y)
    plt.title(lista[0][propiedades[0]])
    plt.xlabel("profundidad")
    
def muestra_ev_tiempo():
    fig3= plt.figure()
    fig3.add_subplot()
    
    eje_x=[date[i] for i in range(len(dataset.variables[time])-1)]
    if lista[1][propiedades[0]]==4:
        eje_y=[dataset.variables[lista[0][propiedades[0]]][i,propiedades[2],valor_x.value, valor_y.value] for i in range(dataset.dimensions[time].size -1)]
    
    if lista[1][propiedades[0]]==3:
        eje_y=[dataset.variables[lista[0][propiedades[0]]][i,valor_x.value, valor_y.value] for i in range(dataset.dimensions[time].size -1)]
    
    plt.plot(eje_x,eje_y)
    plt.title(lista[0][propiedades[0]])
    plt.xlabel("time")
    
def on_button_clicked_ev_prof(b):
    actualiza_layout()
    muestra_ev_prof()


def on_button_clicked_ev_time(b):
    actualiza_layout()
    muestra_ev_tiempo()


    
#Menu
menu = widgets.Tab()
menu.children = [vbox1, vbox3]
menu.set_title(0,'Ajustes')
menu.set_title(1,'Model visualization')
