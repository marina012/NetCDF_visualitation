#import APIs
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import datetime

import re

from datetime import timedelta
from datetime import datetime
from dateutil import parser
import numpy as np
from numpy.ma import masked_array, masked_inside, masked_outside
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


#warning plot
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()



#Model visualization




#busca los ficheros netCDF en la ruta indicada
def busca_modelos(ruta):
    files= [os.path.abspath(arch.path) for arch in os.scandir(ruta) if arch.is_file()]
    lstFiles = []
    for fichero in files:
        (nombreFichero, extension) = os.path.splitext(fichero)
        if(extension == ".nc"):
            lstFiles.append(nombre_modelo(nombreFichero))
            #print (nombreFichero+extension)
    return(lstFiles)

#separo el nombre del fichero de la ruta
def nombre_modelo(nombre):
    return re.findall(r'/home/jovyan/datasets/([A-Za-z0-9\_\-]*)',nombre)[0]


#ruta donde se guardan los ficheros netCDF
ruta= "/home/jovyan/datasets"
opt = busca_modelos(ruta)

#Inicialización de widgets
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

vbox3 = VBox(children=[selection,button3,out3])
vbox1 = VBox()


#Cuando se clica el boton se carga el fichero con el modulo indicado y se muestra la info
@button3.on_click
def model_on_click(b):
    global dataset, variables, propiedades
    nombre_dataset= ruta+"/"+selection.value+".nc"
    dataset= Dataset(nombre_dataset, 'r', format='NETCDF4_CLASSIC')
    #variables[nombre_variable, num_dim]
    variables=[[],[]]
    #propiedades[index_var_escogida,fecha,profundidad,min_value_var, max_value_var]
    propiedades=[[],[],[],[],[]]
    
    carga_variables()
    set_display()
    
    with out3:
        propiedades[0]=0
        propiedades[1]=drop_date.value
        propiedades[2]=depth_wid.value
        calcula_min_max()
        actualiza_layout()


#Se comprueba cual es la variable tiempo en el modelo y se cargan en "variables" las variables del modelo
def carga_variables():
    global drop_var, variables, time
    for n in dataset.variables.keys():
        if n.find("time") >= 0:
            time=n
        dimensiones=''
        for i in dataset.variables[n].dimensions:
            dimensiones= dimensiones+" "+i
        
        dim=len(dataset.variables[n].dimensions)
        if dim > 2 and dim <5:
            variables[0]= np.append(variables[0],n)
            variables[1]= np.append(variables[1],dim)

#Se inicializan los widgets 
def set_display():
    global drop_var, drop_date, depth_wid, hb_3d, hb_2d, vb_ev_2d, vb_ev_3d, valor_x, valor_y, date
    drop_var=widgets.Dropdown(
        options=[(variables[0][n], n) for n in range(len(variables[0]))],
        value=0,
        description='Variables:',
    )
    date= set_date()
    drop_date=widgets.Dropdown(
        options=[(str(date[i]), i) for i in range(len(date))],
        value=0,
        description='Date:',
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

    Label_cor= widgets.Label("Click on the map to choose the coordinates:")

    vb_ev_text= VBox([valor_x, valor_y])
    vb_ev_bot= VBox([boton_tiempo, boton_prof])
    hb_ev_3d= HBox([vb_ev_text, vb_ev_bot, depth_wid])
    hb_ev_2d= HBox([vb_ev_text, boton_tiempo])
    vb_ev_3d= VBox([Label_cor, hb_ev_3d])
    vb_ev_2d= VBox([Label_cor, hb_ev_2d])
    
    boton_prof.on_click(on_button_clicked_ev_prof)
    boton_tiempo.on_click(on_button_clicked_ev_time)


#Se convierte de segundos a fechas
def set_date():
    date=[]
    t=dataset.variables[time].units
    year= int(re.findall(r'seconds since ([0-9]*)-',t)[0])
    month= int(re.findall(r'seconds since [0-9]*-([0-9]*)',t)[0])
    day= int(re.findall(r'seconds since [0-9]*-[0-9]*-([0-9]*)',t)[0])
    
    a = datetime(year,month,day,0,0,0)
    
    for n in dataset.variables[time]:
        b = a + timedelta(seconds=int(n))
        date=np.append(date, b)
        
    return date




#Se actualiza la interfaz para mostrar los nuevos datos despues de un cambio
def actualiza_layout():
    clear()
    des=""
    max_value= "Max value: "+ str(propiedades[4])
    min_value= "Min value: "+ str(propiedades[3])
    
    try:
        des=variables[0][propiedades[0]]+": "+dataset.variables[variables[0][propiedades[0]]].long_name
    except:
        des="Variable with no description"
        
    label= widgets.Label(des)
    label_min= widgets.Label(min_value)
    label_max= widgets.Label(max_value)
    hb_max_min= HBox([label_min, label_max])
    
    #Texto para rango de valores
    
    
    hb_range= HBox([min_range, max_range, boton_range])
    
    if variables[1][propiedades[0]]==4:
        display(hb_3d, label, hb_max_min, hb_range)
        aux=dataset.variables[variables[0][propiedades[0]]][propiedades[1],propiedades[2],:,:]
        ev=vb_ev_3d
        
    if variables[1][propiedades[0]]==3:
        display(hb_2d, label, hb_max_min, hb_range)
        aux=dataset.variables[variables[0][propiedades[0]]][propiedades[1],:,:]
        ev=vb_ev_2d
        
    aux= np.transpose(aux)
    try:
        widgets.Label(variables[0][propiedades[0]],": ",dataset.variables[variables[0][propiedades[0]]].long_name)
    except:
        widgets.Label("Variable sin descripción")
    
    v_m= np.amin(aux[:])
    if v_m != np.nan and v_m <= 0:
        aux[ aux==v_m ] = np.nan
       
    #aux[ aux==0 ] = np.nan
    #fig= plt.figure()
    #fig.add_subplot()
    #cmap = matplotlib.cm.jet
    #cmap.set_bad('white',1.)

    fig=imshow_rango(aux,min_range.value, max_range.value)
    #plt.imshow(np.transpose(aux), interpolation='nearest', vmin= propiedades[3], vmax= propiedades[4],cmap=cmap)
    
    
    cid = fig.canvas.mpl_connect('button_press_event', onclick)
    
    display(ev)
    
    
#pintar el plt.imshow con rango de valores
def imshow_rango(v1, imin, imax):
    v1b = masked_inside(v1,imin,imax)
    v1a = masked_outside(v1,imin,imax)

    fig,ax = plt.subplots()
    pa = ax.imshow(v1a,interpolation='nearest',cmap = matplotlib.cm.jet)
    pb = ax.imshow(v1b,interpolation='nearest',cmap=matplotlib.cm.gray, vmax= 3, vmin= 3)
    cbar = plt.colorbar(pa,shrink=0.25)
    
    try:
        cbar.set_label(dataset.variables[variables[0][propiedades[0]]].units)
    except:
        cbar.set_label("Unidades no especificadas")
    plt.title(variables[0][propiedades[0]])
    plt.ylabel("Latitude")
    plt.xlabel("Longitude")

    plt.show()
    
    return fig
    
#Cuando se clica en el mapa se guardan los valores de las cordenadas
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
    global min_range, max_range, boton_range
    
    var= dataset.variables[variables[0][propiedades[0]]][:]
    v_max= np.amax(var[:])
    v_m= np.amin(var[:])

    var[ var==v_m ] = v_max+10
    v_min= np.amin(var[:])

    var[ var==v_max+10 ] = v_m

    propiedades[3]=v_min
    propiedades[4]=v_max
    
    min_range= widgets.BoundedFloatText(
    value=propiedades[3],
    min=propiedades[3],
    max=propiedades[4],
    step=1,
    description='Min:'
    )
    
    max_range= widgets.BoundedFloatText(
    value=propiedades[4],
    min=propiedades[3],
    max=propiedades[4],
    step=1,
    description='Max:'
    )
    
    boton_range= widgets.Button(
        description='Change range'
    )
    boton_range.on_click(on_button_clicked_range)
    
    

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
    eje_x=[dataset.variables[variables[0][propiedades[0]]][propiedades[1],i,valor_x.value, valor_y.value] for i in range(34)]
    
    plt.plot(eje_x,eje_y)
    
    plt.title(variables[0][propiedades[0]])
    plt.ylabel("layer")
    
    try:
        plt.xlabel(variables[0][propiedades[0]]+": "+dataset.variables[variables[0][propiedades[0]]].units)
    except:
        plt.xlabel("#")
    
def muestra_ev_tiempo():
    fig3= plt.figure()
    fig3.add_subplot()
    
    eje_x=[date[i] for i in range(len(dataset.variables[time])-1)]
    ax=[]
    for i in range(int(len(dataset.variables[time])/4)):
        monthinteger = date[4].month
        month = datetime(2000, monthinteger, 1).strftime('%B')
        d= str(month)+"-"+str(date[i*4].day)
        ax= np.append(ax, d)
        ax= np.append(ax, " ")
        ax= np.append(ax, " ")
        ax= np.append(ax, " ")
    
    if variables[1][propiedades[0]]==4:
        eje_y=[dataset.variables[variables[0][propiedades[0]]][i,propiedades[2],valor_x.value, valor_y.value] for i in range(dataset.dimensions[time].size -1)]
    
    if variables[1][propiedades[0]]==3:
        eje_y=[dataset.variables[variables[0][propiedades[0]]][i,valor_x.value, valor_y.value] for i in range(dataset.dimensions[time].size -1)]
    
    plt.xticks(eje_x,ax)
    plt.plot(eje_x,eje_y)
    plt.title(variables[0][propiedades[0]])
    plt.xlabel("date")
    
    try:
        plt.ylabel(variables[0][propiedades[0]]+": "+dataset.variables[variables[0][propiedades[0]]].units)
    except:
        plt.ylabel("#")
    
def on_button_clicked_ev_prof(b):
    actualiza_layout()
    muestra_ev_prof()
   


def on_button_clicked_ev_time(b):
    actualiza_layout()
    muestra_ev_tiempo()
    
    
def on_button_clicked_range(b):
    actualiza_layout()


    
#Menu
menu = widgets.Tab()
menu.children = [vbox1, vbox3]
menu.set_title(0,'Settings')
menu.set_title(1,'Model visualization')
