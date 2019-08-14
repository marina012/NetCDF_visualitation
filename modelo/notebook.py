#Codigo realizado por Marina López Murcia
#import APIs
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation
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


#Eliminar warnings
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()

import warnings
warnings.filterwarnings("ignore")


#Model visualization

box_layout = Layout(display='flex',
                    align_items='center',
                    width='auto',
                    justify_content='space-around')

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

#Inicialización de widgets del menu
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
    max=34,
    step=1,
    description='Layer (depth):',
    disabled=False,
    continuous_update=False,
    orientation='horizontal',
    readout=True,
    readout_format='d'
)
button_model_output = widgets.Button(
    description='Show model output',
)

out = widgets.Output()

vbox2 = VBox(children=[selection,button_model_output,out])
vbox1 = VBox()

#Menu
menu = widgets.Tab()
menu.children = [vbox1, vbox2]
menu.set_title(0,'Settings')
menu.set_title(1,'Model visualization')

#Cuando se clica el boton se carga el fichero con el modulo indicado y se muestra la info
@button_model_output.on_click
def model_on_click(b):
    global dataset, variables, propiedades, range_index, animacion_on
    animacion_on=False
    nombre_dataset= ruta+"/"+selection.value+".nc"
    dataset= Dataset(nombre_dataset, 'r', format='NETCDF4_CLASSIC')
    #variables[nombre_variable, num_dim]
    variables=[[],[]]
    #propiedades[index_var_escogida,fecha,profundidad,min_value_var, max_value_var, mean_value_var]
    propiedades=[[],[],[],[],[],[]]
    
    carga_variables()
    propiedades[0]=0
    range_index=1
    set_widgets()
    
    with out:
        propiedades[1]=drop_date.value
        propiedades[2]=depth_wid.value
        calcula_min_max()
        actualiza_layout()


#Se comprueba cual es la variable tiempo en el modelo y se cargan en "variables" las variables del modelo
def carga_variables():
    global drop_var, variables, time, tipo
    #tipo 0= calidad del agua, prof de mas profundo a menos
    #tipo 1= hidrodinamico?, prof de menos a mas 
    tipo=0
    for n in dataset.variables.keys():
        if n.find("mesh2d_OXY") >= 0:
            tipo=1
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
def set_widgets():
    global drop_var, drop_date, depth_wid, hb_3d, hb_2d, vb_ev_2d, vb_ev_3d, valor_x, valor_y, date, drop_date_range2, drop_date_range1
    
    #widgets para escoger que datos mostrar
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
    
    #cuadro de texto para donde se escoge el valor de coordenada x e y
    valor_x= widgets.BoundedFloatText(
    value=0,
    min=0,
    max=dataset.variables[variables[0][propiedades[0]]].shape[-2]-1,
    step=1,
    description='x:'
    )
    valor_y= widgets.BoundedFloatText(
        value=0,
        min=0,
        max=dataset.variables[variables[0][propiedades[0]]].shape[-1]-1,
        step=1,
        description='y:'
    )

    #widgets para ver más info
    boton_tiempo= widgets.Button(
        description='Tiempo'
    )
    
    boton_animacion= widgets.Button(
        description='Animación evolución'
    )

    boton_prof= widgets.Button(
        description='Profundidad'
    )
    
    boton_corte_lon= widgets.Button(
        description='Longitudinal'
    )
    
    boton_corte_lat= widgets.Button(
        description='Latitudinal'
    )

    Label_cor= widgets.Label("Clicar en el mapa para escoger coordenadas:")
    Label_display= widgets.Label("Mostrar:")
    Label_date= widgets.Label("Rango de fechas:")
    Label_section= widgets.Label("Mapa con corte:")
    Label_plot= widgets.Label("Diagrama con evolución en función:")
    
    
    drop_date_range1=widgets.Dropdown(
        options=[(str(date[i]), i) for i in range(0,len(date)-range_index)],
        value=0,
        description='Desde:',
    )
    
    drop_date_range2=widgets.Dropdown(
        options=[(str(date[i]), i) for i in range(range_index,len(date))],
        value=len(date)-range_index,
        description='Hasta:',
    )
    
    vb_cor=VBox([Label_cor,valor_x, valor_y])
    vb_date_range= VBox([Label_date,drop_date_range1,drop_date_range2])
    hb_options= HBox([vb_cor,vb_date_range])
    
    hb_corte= HBox([boton_corte_lat, boton_corte_lon], layout= box_layout)
    hb_plot= HBox([boton_tiempo, boton_prof], layout= box_layout)
    hb_time= HBox([boton_tiempo], layout= box_layout)
    
    vb_ev_3d= VBox([hb_options, Label_display,boton_animacion,Label_section, hb_corte, Label_plot,hb_plot])
    vb_ev_2d= VBox([hb_options, Label_display,boton_animacion,Label_plot, hb_time])
    
    widgets.interact(drop_date_range1 = drop_date_range1, drop_date_range2 = drop_date_range2)
    drop_date_range1.observe(range_on_change, names='value')
    boton_prof.on_click(on_button_clicked_ev_prof)
    boton_tiempo.on_click(on_button_clicked_ev_time)
    boton_animacion.on_click(on_button_clicked_animacion)
    boton_corte_lat.on_click(on_button_clicked_corte_lat)
    boton_corte_lon.on_click(on_button_clicked_corte_lon)


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
    if animacion_on:
        anim.event_source.stop()
    clear()
    #Mostrar estadisticas de las variables
    max_value= "Max value: "+ str(propiedades[4])
    min_value= "Min value: "+ str(propiedades[3])
    mean_value= "Mean value: "+ str(propiedades[5])

    #Muestra, si la hay, la descripcion de las variables
    des=""
    try:
        des=(variables[0][propiedades[0]]+": "+dataset.variables[variables[0][propiedades[0]]].long_name)
    except:
        des=("Variable sin descripción")
    label= widgets.Label(des)
    label_min= widgets.Label(min_value)
    label_max= widgets.Label(max_value)
    label_mean= widgets.Label(mean_value)
    hb_max_min= HBox([label_min, label_max,label_mean])
    
    
    hb_range= HBox([min_range, max_range, boton_range])
    
    #Comprueba de que depende las variables, y escoge que pasarle dependiendo de eso
    if variables[1][propiedades[0]]==4:
        depth_wid.max= dataset.variables[variables[0][propiedades[0]]].shape[-3]-1
        display(hb_3d, label, hb_max_min, hb_range)
        prof=propiedades[2]
        if tipo==0:
            dimz=dataset.variables[variables[0][propiedades[0]]].shape[-3]-1
            prof=dimz-prof
        aux=dataset.variables[variables[0][propiedades[0]]][propiedades[1],prof,:,:]
        ev=vb_ev_3d
        
    if variables[1][propiedades[0]]==3:
        display(hb_2d, label, hb_max_min, hb_range)
        aux=dataset.variables[variables[0][propiedades[0]]][propiedades[1],:,:]
        ev=vb_ev_2d
        
    aux= np.transpose(aux)
    
    
    #Convierte los valores de relleno en nan para que no se pinten en el mapa
    v_m= np.amin(aux[:])
    if v_m != np.nan and v_m <= 0:
        aux[ aux==v_m ] = np.nan
       

    fig=imshow_rango(aux,min_range.value, max_range.value)
    
    #Se crea un evento para coger las coordenadas escogidas
    cid = fig.canvas.mpl_connect('button_press_event', onclick)
    
    display(ev)
    
    
#pintar el plt.imshow con rango de valores
def imshow_rango(v1, imin, imax):
    
    #Se crea un maskarray que contenga los valores dentro del rango y otro que no, para pintarlos con rangos de colores distintos
    v1b = masked_inside(v1,imin,imax)
    v1a = masked_outside(v1,imin,imax)

    fig,ax = plt.subplots()
    pa = ax.imshow(v1a,interpolation='nearest',cmap = matplotlib.cm.jet, vmin= min_range.value, vmax= max_range.value)
    pb = ax.imshow(v1b,interpolation='nearest',cmap=matplotlib.cm.Pastel1, vmax= 3, vmin= 3)
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
    
#Se vacia el output y se cierran las figuras plt
def clear():
    clear_output()
    plt.close()
    
    
#Cuando se cambia la variable escogidase calcula las estadisticas de la variable y se actualiza lo que se muestra por pantalla
def variable_on_change(v):
    propiedades[0]=v['new']
    propiedades[3]= None
    propiedades[4]= None
    calcula_min_max()
    actualiza_layout()
    
#Calcula las estadisticas de la variable (min, max, mean)
def calcula_min_max():
    global min_range, max_range, boton_range
    
    var= dataset.variables[variables[0][propiedades[0]]][:]
    
    v_m= np.amin(var[:])
    if v_m != np.nan and v_m <= 0:
        var[ var==v_m ] = np.nan
        
        
    v_mean= np.nanmean(var[:])
    v_max= np.nanmax(var[:])
    v_min= np.nanmin(var[:])

    propiedades[3]=v_min
    propiedades[4]=v_max
    propiedades[5]=v_mean
    
    #Casillas para escoger e rango de valores que se quieren mostrar
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
    
    
#Se actualiza la profundidad y se actualiza la interfaz
def slider_on_change(v):
    
    propiedades[2]=v['new']
    actualiza_layout()
    
depth_wid.observe(slider_on_change, names='value')

#Se cambia la fecha a observar y se muestran los datos acorde a esa fecha
def date_on_change(v):
    propiedades[1]=v['new']
    actualiza_layout()
    
def range_on_change(v):
    
    range_index=v['new']
    v=drop_date_range2.value
    if range_index>v:
        v=range_index
    drop_date_range2.options=[(str(date[i]), i) for i in range(range_index+1,len(date))]
    drop_date_range2.value=v
    
    
  
    
    
#Se muestra la ev en profundidad
def muestra_ev_prof():
    dimz=dataset.variables[variables[0][propiedades[0]]].shape[-3]
    fig3= plt.figure()
    fig3.add_subplot()
    eje_y=[i for i in range(dimz)]
    eje_x=[dataset.variables[variables[0][propiedades[0]]][propiedades[1],i,valor_x.value, valor_y.value] for i in range(dimz)]
    
    plt.gca().invert_yaxis()
    
    plt.plot(eje_x,eje_y)
    
    plt.title(variables[0][propiedades[0]])
    plt.ylabel("layer")
    
    try:
        plt.xlabel(variables[0][propiedades[0]]+": "+dataset.variables[variables[0][propiedades[0]]].units)
    except:
        plt.xlabel("#")

#Se muestra la evolucion en funcion del tiempo
def muestra_ev_tiempo():
    fig3= plt.figure()
    fig3.add_subplot()
    
    drop_date_range2.value
    
    eje_x=[date[i] for i in range(drop_date_range1.value, drop_date_range2.value)]
    ax=[]
    for i in range(drop_date_range1.value, int(drop_date_range2.value/4)):
        monthinteger = date[4*i].month
        month = datetime(2000, monthinteger, 1).strftime('%B')
        d= str(month)+"-"+str(date[i*4].day)
        ax= np.append(ax, d)
        ax= np.append(ax, " ")
        ax= np.append(ax, " ")
        ax= np.append(ax, " ")
    
    if variables[1][propiedades[0]]==4:
        eje_y=[dataset.variables[variables[0][propiedades[0]]][i,propiedades[2],valor_x.value, valor_y.value] for i in range(drop_date_range1.value, drop_date_range2.value)]
    
    if variables[1][propiedades[0]]==3:
        eje_y=[dataset.variables[variables[0][propiedades[0]]][i,valor_x.value, valor_y.value] for i in range(drop_date_range1.value, drop_date_range2.value)]
    
    plt.xticks(eje_x,ax)
    plt.plot(eje_x,eje_y)
    plt.title(variables[0][propiedades[0]])
    plt.xlabel("date")
    
    try:
        plt.ylabel(variables[0][propiedades[0]]+": "+dataset.variables[variables[0][propiedades[0]]].units)
    except:
        plt.ylabel("#")
  


#Metodos de botones
def on_button_clicked_ev_prof(b):
    actualiza_layout()
    muestra_ev_prof()

def on_button_clicked_ev_time(b):
    actualiza_layout()
    muestra_ev_tiempo()
 
def on_button_clicked_range(b):
    actualiza_layout()
    
def on_button_clicked_animacion(b):
    global anim
    animacion_on=True
    actualiza_layout()
    anim=animacion()

#Muestra el corte en latitud de unas cordenadas escogidas
def on_button_clicked_corte_lat(b):
    actualiza_layout()
    dimz=dataset.variables[variables[0][propiedades[0]]].shape[-3]
    dimx=dataset.variables[variables[0][propiedades[0]]].shape[-2]
    corte_latitud(valor_y.value, dimx, dimz, min_range.value, max_range.value)
    
    
    
#Muestra el corte longitudinal de unas cordenadas escogidas
def on_button_clicked_corte_lon(b):
    actualiza_layout()
    dimz=dataset.variables[variables[0][propiedades[0]]].shape[-3]
    dimy=dataset.variables[variables[0][propiedades[0]]].shape[-1]
    corte_longitud(valor_x.value, dimy, dimz, min_range.value, max_range.value)
    
#Crea el corte longitudinal
def corte_longitud(lon, dim, dimz, imin, imax):
    corte= np.zeros((dimz, dim))
    step=1
    z0=0
    z1=dimz-1
    if tipo==0:
        z0=dimz-1
        z1=0
        step=-1
    for i in range (z0,z1,step):
        aux=dataset.variables[variables[0][propiedades[0]]][propiedades[1],i,lon,:]
        corte[i,:]=aux
        
    v_m= np.amin(corte[:])
    if v_m != np.nan and v_m <= 0:
        corte[ corte==v_m ] = np.nan
        
        
    v1b = masked_inside(corte,imin,imax)
    v1a = masked_outside(corte,imin,imax)

    fig,ax = plt.subplots()
    pa = ax.imshow(v1a,interpolation='nearest',cmap = matplotlib.cm.jet, vmin= min_range.value, vmax= max_range.value)
    pb = ax.imshow(v1b,interpolation='nearest',cmap=matplotlib.cm.Pastel1, vmax= 3, vmin= 3)
    cbar = plt.colorbar(pa,shrink=0.25)
    


#Crea el corte en latitud
def corte_latitud(lat, dim, dimz, imin, imax):
    corte= np.zeros((dimz, dim))
    step=1
    z0=0
    z1=dimz-1
    if tipo==0:
        z0=dimz-1
        z1=0
        step=-1
    for i in range (z0,z1,step):
        aux=dataset.variables[variables[0][propiedades[0]]][propiedades[1],i,:,lat]
        corte[i,:]=aux
        
    v_m= np.amin(corte[:])
    if v_m != np.nan and v_m <= 0:
        corte[ corte==v_m ] = np.nan
        
    
    v1b = masked_inside(corte,imin,imax)
    v1a = masked_outside(corte,imin,imax)

    fig,ax = plt.subplots()
    pa = ax.imshow(v1a,interpolation='nearest',cmap = matplotlib.cm.jet, vmin= min_range.value, vmax= max_range.value)
    pb = ax.imshow(v1b,interpolation='nearest',cmap=matplotlib.cm.Pastel1, vmax= 3, vmin= 3)
    cbar = plt.colorbar(pa,shrink=0.25)
    
    
def animacion():
    global snapshots, im, fig
        
    if variables[1][propiedades[0]]==4:
        prof=propiedades[2]
        if tipo==0:
            dimz=dataset.variables[variables[0][propiedades[0]]].shape[-3]-1
            prof=dimz-prof
        snapshots=[np.transpose(dataset.variables[variables[0][propiedades[0]]][i,prof,:,:]) for i in range(drop_date_range1.value, drop_date_range2.value)]
        ev=vb_ev_3d
        
    if variables[1][propiedades[0]]==3:
        snapshots=[np.transpose(dataset.variables[variables[0][propiedades[0]]][i,:,:]) for i in range(drop_date_range1.value, drop_date_range2.value)]
        
    v_m= np.amin(snapshots[0][:])
    for i in range(len(snapshots)):
        aux=snapshots[i]
        aux[ aux==v_m ] = np.nan
        snapshots[i]=aux

    fig = plt.figure()

    a = snapshots[0]
    
    im = plt.imshow(a, interpolation='none', aspect='auto', cmap = matplotlib.cm.jet,vmin= propiedades[3], vmax= propiedades[4])
    plt.colorbar()
    
    anim = animation.FuncAnimation(
                               fig, 
                               animate_func, 
                               frames = len(date),
                               interval = 500, # in ms
                                   )
    return anim

def animate_func(i):
    im.set_array(snapshots[i])
    return [im]
    
