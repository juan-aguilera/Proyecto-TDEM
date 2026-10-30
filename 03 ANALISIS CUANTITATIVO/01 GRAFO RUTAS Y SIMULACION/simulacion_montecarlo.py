import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import time
import copy




"""Monte Carlo de las matrices de distancia y de tiempo.

Cada celda equivale a esta fórmula de Excel:
    =INV.NORM(ALEATORIO(); media_ij; 0,10 * media_ij)
La media es el valor original de la posición (i, j).
La desviación estándar es el 10 % de ese mismo valor.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

CARPETA = Path(__file__).resolve().parent
N_ITERACIONES = 30
COEF_DESV = 0.10

distancias = pd.read_csv(CARPETA / "matriz_distancias_nxn.csv", index_col=0)
tiempos = pd.read_csv(CARPETA / "matriz_tiempos_nxn.csv", index_col=0)

media_dist = distancias.to_numpy(dtype=float)
media_tiempo = tiempos.to_numpy(dtype=float)
desv_dist = COEF_DESV * media_dist
desv_tiempo = COEF_DESV * media_tiempo

rng = np.random.default_rng(42)
matrices_distancia = []
matrices_tiempo = []

for iteracion in range(N_ITERACIONES):
    # Si la celda vale 0, la desviación también es 0 y el resultado se queda en 0.
    sim_dist = media_dist.copy()
    sim_tiempo = media_tiempo.copy()

    hay_desv_dist = desv_dist > 0
    hay_desv_tiempo = desv_tiempo > 0

    # =INV.NORM(ALEATORIO(); media; desviación)
    sim_dist[hay_desv_dist] = norm.ppf(
        rng.random(hay_desv_dist.sum()),
        loc=media_dist[hay_desv_dist],
        scale=desv_dist[hay_desv_dist],
    )
    sim_tiempo[hay_desv_tiempo] = norm.ppf(
        rng.random(hay_desv_tiempo.sum()),
        loc=media_tiempo[hay_desv_tiempo],
        scale=desv_tiempo[hay_desv_tiempo],
    )

    matrices_distancia.append(
        pd.DataFrame(sim_dist, index=distancias.index, columns=distancias.columns)
    )
    matrices_tiempo.append(
        pd.DataFrame(sim_tiempo, index=tiempos.index, columns=tiempos.columns)
    )


###############################################

insta = 5
np.random.seed(126)

depcentral = pd.read_excel(r"DATOS.xlsx", sheet_name='deposito central')
pacientes  = pd.read_excel(r"DATOS.xlsx", sheet_name='Pacientes', index_col=2)
eco        = pd.read_excel(r"DATOS.xlsx", sheet_name='eco capital')

durserv = pd.read_excel(r"DATOS.xlsx", sheet_name='Tiempo de servicio', index_col=0)
durserv.columns = ['t']

tiempos = pd.read_excel(r'TIEMPOS.xlsx', sheet_name='tiempos', index_col=0)


distancias_km = pd.read_excel(r'DISTANCIA.xlsx', sheet_name='distancia', index_col=0) 

limtiemp =  6*60
limkits  = 36         

#################################################

#################FUNCIONES IMPLEMENTADAS EN EL CODIGO################################

def rta_asig(rutas_optmizadas_2, rta_rutas_optmizadas_2):
    filas = []
    for i in range(len(rutas_optmizadas_2)):
        rut   = rutas_optmizadas_2[i][1]
        costo = rutas_optmizadas_2[i][0]

        for j in range(rut.shape[0]):
            cliente = rut.iat[j, 0]
            ruta    = rut.iat[j, 1]

            print(cliente)
            print(ruta)

            filas.append({
                'cliente': cliente,
                'costo':   costo,
                'ruta':    ruta
            })

    nuevo_df = pd.DataFrame(filas, columns=['cliente', 'costo', 'ruta'])

    return pd.concat([rta_rutas_optmizadas_2, nuevo_df], ignore_index=True)


#########################################################################################################

def rta_asig_costos(rutas_optmizadas, rta_rutas_optmizadas_costos):

    filas = []
    for i in range(len(rutas_optmizadas)):
        rut   = rutas_optmizadas[i][1]
        costo = rutas_optmizadas[i][0]

        cliente = rut.iat[0, 0]
        ruta    = rut.iat[0, 1]

        print(cliente, costo, ruta)

        filas.append({
            'cliente': cliente,
            'costo':   costo,
            'ruta':    ruta
        })

    nuevo_df = pd.DataFrame(filas, columns=['cliente', 'costo', 'ruta'])
    return pd.concat([rta_rutas_optmizadas_costos, nuevo_df], ignore_index=True)

#########################################################################################################

def swap(Cost, temp, eps=1e-6):

    newRoute = copy.deepcopy(temp)
    n = newRoute.shape[0]
    D = distancias[num_HOSPITAL][0]

    delta = 0.0
    bestI = -1
    bestJ = -1

    for i in range(1, n - 2):
        nodoI = newRoute.iat[i, 0]
        predI = newRoute.iat[i - 1, 0]
        sucI  = newRoute.iat[i + 1, 0]

        for j in range(i + 1, n - 2):
            nodoJ = newRoute.iat[j, 0]
            predJ = newRoute.iat[j - 1, 0]
            sucJ  = newRoute.iat[j + 1, 0]

            if j == i + 1:
                d = (D.loc[predI, nodoJ] + D.loc[nodoJ, nodoI] + D.loc[nodoI, sucJ]
                     - D.loc[predI, nodoI] - D.loc[nodoI, nodoJ] - D.loc[nodoJ, sucJ])
            else:
                d = (D.loc[predI, nodoJ] + D.loc[nodoJ, sucI]
                     + D.loc[predJ, nodoI] + D.loc[nodoI, sucJ]
                     - D.loc[predI, nodoI] - D.loc[nodoI, sucI]
                     - D.loc[predJ, nodoJ] - D.loc[nodoJ, sucJ])

            if d < delta - eps:
                delta = d
                bestI = i
                bestJ = j

    if bestI == -1:
        return [Cost, newRoute, False]

    newRoute.iat[bestI, 0], newRoute.iat[bestJ, 0] = \
        newRoute.iat[bestJ, 0], newRoute.iat[bestI, 0]

    return [Cost + delta, newRoute, True]

#########################################################################################################
def suma_costo(R_optmizadas):
    costo_total = 0
    for i in range(len(R_optmizadas)):
        costo_total += R_optmizadas[i][0]
    return costo_total
#########################################################################################################

def conteo_split(I, J, newRoute):
    dif = J - I
    costo_split = 0
    for i in range(dif):
        d = distancias[num_HOSPITAL][0].loc[newRoute.iat[I + i, 0], newRoute.iat[I + i + 1, 0]]
        costo_split += d
    return costo_split

#########################################################################################################

def conteo_quieto(I, J, newRoute):
    dif = J - I
    costo_split = 0
    for i in range(dif):
        d = distancias[num_HOSPITAL][0].loc[newRoute.iat[I + i, 0], newRoute.iat[I + i + 1, 0]]
        costo_split += d
    return costo_split

#########################################################################################################
def twoOptimal_1(Cost, ruta):

    newRoute = copy.deepcopy(ruta)
    n = newRoute.shape[0]
    D = distancias[num_HOSPITAL][0]

    delta = 0.0
    bestI = -1
    bestJ = -1

    for i in range(1, n - 3):
        predTail = ruta.iat[i,     0]
        tail     = ruta.iat[i + 1, 0]

        for j in range(i + 2, n - 2):
            head    = ruta.iat[j,     0]
            sucHead = ruta.iat[j + 1, 0]

            delta_cand = (D.loc[predTail, head]
                          + D.loc[tail,     sucHead]
                          - D.loc[predTail, tail]
                          - D.loc[head,     sucHead])

            if delta_cand < delta:
                delta = delta_cand
                bestI = i + 1
                bestJ = j

    if bestI == -1:
        return [Cost, newRoute, False]

    newCost = Cost + delta

    lo = bestI
    hi = bestJ
    while lo < hi:
        newRoute.iat[lo, 0], newRoute.iat[hi, 0] = \
            newRoute.iat[hi, 0], newRoute.iat[lo, 0]
        lo += 1
        hi -= 1

    if newCost >= Cost:
        return [Cost, copy.deepcopy(ruta), False]

    return [newCost, newRoute, True]
#########################################################################################################

def _append_coords(Ruta, COOD_X, COOD_Y):
    for j in range(Ruta.shape[0]):
        client = Ruta.iat[j, 0]

        if client in pacientes.index:
            COOD_X.append(pacientes.loc[client, 'Latitud'])
            COOD_Y.append(pacientes.loc[client, 'Longitud'])

        elif client in ['H1', 'H2', 'H3']:

            col_lat = next((c for c in ['Latitud', 'Latitude', 'lat', 'LAT']
                            if c in depcentral.columns), None)
            col_lon = next((c for c in ['Longitud', 'Longitude', 'lon', 'LON']
                            if c in depcentral.columns), None)

            if col_lat is None or col_lon is None:
                print(f"[AVISO] No se encontraron columnas de Latitud/Longitud "
                      f"en 'deposito central'. Columnas: {depcentral.columns.tolist()}")
                return

            fila = None

            col_id = next((c for c in depcentral.columns
                           if depcentral[c].astype(str).isin(['H1', 'H2', 'H3']).any()),
                          None)
            if col_id is not None:
                match = depcentral[depcentral[col_id].astype(str) == client]
                if not match.empty:
                    fila = match.iloc[0]

            if fila is None and client in depcentral.index:
                fila = depcentral.loc[client]

            if fila is None:
                try:
                    pos = ['H1', 'H2', 'H3'].index(client)
                    if pos < len(depcentral):
                        fila = depcentral.iloc[pos]
                except ValueError:
                    pass

            if fila is not None:
                COOD_X.append(fila[col_lat])
                COOD_Y.append(fila[col_lon])
            else:
                print(f"[AVISO] No se encontraron coordenadas para {client} "
                      f"en 'deposito central'.")

        elif client == 'Eco':
            col_lat = next((c for c in ['Latitud', 'Latitude', 'lat', 'LAT']
                            if c in eco.columns), None)
            col_lon = next((c for c in ['Longitud', 'Longitude', 'lon', 'LON']
                            if c in eco.columns), None)
            if col_lat is not None and col_lon is not None:
                COOD_X.append(eco[col_lat].iloc[0])
                COOD_Y.append(eco[col_lon].iloc[0])
            else:
                print(f"[AVISO] No se encontraron columnas de Latitud/Longitud "
                      f"en 'eco capital'. Columnas: {eco.columns.tolist()}")

####################################################
####ASIGNACION DE CLIENTES A HOSPITAL
distancias = []

tabdistan = tiempos.loc[:, ['H1', 'H2', 'H3']].copy()
lista = []
for cliente in tabdistan.index:
    a = tabdistan.loc[cliente, :].idxmin()
    lista.append(a)
tabdistan['hospital asignado'] = lista
tabdistan.loc['Eco', 'hospital asignado'] = 'H1'


# FILTRAR ASIGNACION PARA CADA HOSPITAL
tabdistan.iloc[-1, -1] = 'H1'
b1clie = tabdistan[tabdistan['hospital asignado'] == 'H1']

tabdistan.iloc[-1, -1] = 'H2'
b2clie = tabdistan[tabdistan['hospital asignado'].isna() | (tabdistan['hospital asignado'] == 'H2')]

tabdistan.iloc[-1, -1] = 'H3'
b3clie = tabdistan[tabdistan['hospital asignado'].isna() | (tabdistan['hospital asignado'] == 'H3')]

globa = [b1clie, b2clie, b3clie]

# ============================================================
# MATRIZ DE COSTOS (km) 
distancias = []
for hospital in globa:
    matrix = []
    for cust in hospital.index:
        parcial = []
        for othercust in hospital.index:
            if cust == othercust:
                distan = np.nan
            else:
                distan = distancias_km.loc[cust, othercust]   # ← CAMBIO: km
            parcial.append(distan)
        matrix.append(parcial)

    matrix = pd.DataFrame(matrix)
    matrix.index = hospital.index
    matrix.columns = hospital.index
    distancias.append([matrix])

# ============================================================
# MATRIZ DE TIEMPOS (min) 
distancias_t = []
for hospital in globa:
    matrix = []
    for cust in hospital.index:
        parcial = []
        for othercust in hospital.index:
            if cust == othercust:
                distan = np.nan
            else:
                distan = tiempos.loc[cust, othercust]      
            parcial.append(distan)
        matrix.append(parcial)

    matrix = pd.DataFrame(matrix)
    matrix.index = hospital.index
    matrix.columns = hospital.index
    distancias_t.append([matrix])

#CREACION DE LAS 3 GRANDES RUTAS
subrutas = []
i = 1
for datos in distancias:
    ruta = []
    costoRuta = 0
    primerNodo = 'H' + str(i)
    costo0 = datos[0].copy()
    costo0 = costo0.drop(primerNodo, axis=1)
    nodoActual = primerNodo
    ruta.append(primerNodo)
    while costo0.shape[1] > 0:
        candidato = costo0.loc[nodoActual, :].idxmin()
        if costo0.shape[1] != 1 and candidato == 'Eco':
            costo0.loc[nodoActual, 'Eco'] = np.nan
            candidato = costo0.loc[nodoActual, :].idxmin()

        costo = costo0.loc[nodoActual, candidato]
        ruta.append(candidato)
        costoRuta += costo
        nodoActual = candidato
        costo0 = costo0.drop(nodoActual, axis=1)
    subrutas.append([ruta, costoRuta])
    i += 1

names = ['cliente']
rta_subrutas = pd.DataFrame(columns=names)

for i in range(len(subrutas)):
    for j in range(len(subrutas[i][0])):
        nueva_fila = pd.DataFrame([{'cliente': subrutas[i][0][j]}])
        rta_subrutas = pd.concat([rta_subrutas, nueva_fila], ignore_index=True)

    nodo_inicial = subrutas[i][0][0]
    nueva_fila = pd.DataFrame([{'cliente': nodo_inicial}])
    rta_subrutas = pd.concat([rta_subrutas, nueva_fila], ignore_index=True)

# GENERACION DE SUBRUTAS MEDIANTE VECINO MAS CERCANO

ambulancias = []
rutaamb = []
asignacion = []

for rutas in range(len(subrutas)):
    rutaamb = []
    j = 1
    tiempo = 0
    temporal = []

    for i in range(len(subrutas[rutas][0]) - 2):
        if i == 0:
            temporal.append([subrutas[rutas][0][0], j])

        if (subrutas[rutas][0][i + 1]) == 'Eco':
            continue

        cliente_sig = subrutas[rutas][0][i + 1]
        servicio    = pacientes.loc[cliente_sig, 'Servicio']
        tiempo_serv = durserv.loc[servicio, 't']

        # ── TIEMPO en minutos: usar distancias_t     # ← CAMBIO
        tiempo = (distancias_t[rutas][0].loc[subrutas[rutas][0][i], cliente_sig]
                  + tiempo_serv
                  + tiempo)

        # ── Evaluación contra limtiemp en minutos    # ← CAMBIO
        if (tiempo + (distancias_t[rutas][0].loc[cliente_sig, 'Eco']) > limtiemp) \
                or len(temporal) * 3 > limkits - 1:
            tiempo = 0
            temporal.append(['Eco', j])
            j += 1
            rutaamb.append(temporal)
            temporal = []
            temporal.append([subrutas[rutas][0][0], j])

            temporal.append([cliente_sig, j])
            # ── Recalcular tiempo con distancias_t   # ← CAMBIO
            tiempo = tiempo_serv + distancias_t[rutas][0].loc[subrutas[rutas][0][0], cliente_sig]
        else:
            temporal.append([cliente_sig, j])

    if len(temporal) > 1:
        temporal.append(['Eco', j])
        rutaamb.append(temporal)

    asignacion.append(rutaamb)


filas = []
for rutas in asignacion:
    for dias in rutas:
        filas.extend(dias)

asig_ambulancias = pd.DataFrame(filas, columns=['cliente', 'ruta'])
asig_ambulancias

# GENERACION DE FORMATO DE LA HEURISTICA CONSTRUCTIVA (TSP)

costList = []
numero = 1

rutas_optmizadas = []
names = ['cliente', 'ruta']
temp = pd.DataFrame(columns=names)

for i in range(asig_ambulancias.shape[0]):
    if numero != asig_ambulancias.iloc[i, 1] and 0 != i:
        numero = asig_ambulancias.iloc[i, 1]
        ##### ruta completa
        num_HOSPITAL = -4
        if temp.iat[0, 0] == 'H1':
            num_HOSPITAL = 0
        elif temp.iat[0, 0] == 'H2':
            num_HOSPITAL = 1
        else:
            num_HOSPITAL = 2

        costo = 0
        for j in range(temp.shape[0] - 1):
            costo += distancias[num_HOSPITAL][0].loc[temp.iat[j, 0], temp.iat[j + 1, 0]]

        nueva_fila = pd.DataFrame(
            [{'cliente': temp.iat[0, 0], 'ruta': temp.iat[0, 1]}],
            columns=names
        )
        temp = pd.concat([temp, nueva_fila], ignore_index=True)

        costo += distancias[num_HOSPITAL][0].loc[temp.iat[j + 1, 0], temp.iat[0, 0]]

        mySol = [costo, temp]
        rutas_optmizadas.append(mySol)

        names = ['cliente', 'ruta']
        temp = pd.DataFrame(columns=names)

    nueva_fila = pd.DataFrame(
        [{'cliente': asig_ambulancias.iloc[i, 0],
          'ruta':    asig_ambulancias.iloc[i, 1]}],
        columns=names
    )
    temp = pd.concat([temp, nueva_fila], ignore_index=True)

##### ruta completa 
num_HOSPITAL = -4
if temp.iat[0, 0] == 'H1':
    num_HOSPITAL = 0
elif temp.iat[0, 0] == 'H2':
    num_HOSPITAL = 1
else:
    num_HOSPITAL = 2

costo = 0
for j in range(temp.shape[0] - 1):
    costo += distancias[num_HOSPITAL][0].loc[temp.iat[j, 0], temp.iat[j + 1, 0]]

nueva_fila = pd.DataFrame(
    [{'cliente': temp.iat[0, 0], 'ruta': temp.iat[0, 1]}],
    columns=names
)
temp = pd.concat([temp, nueva_fila], ignore_index=True)
costo += distancias[num_HOSPITAL][0].loc[temp.iat[j + 1, 0], temp.iat[0, 0]]

mySol = [costo, temp]
rutas_optmizadas.append(mySol)

costo_total = suma_costo(rutas_optmizadas)
costList.append(costo_total)

names = ['cliente', 'costo', 'ruta']
rta_rutas_optmizadas = pd.DataFrame(columns=names)
rta_rutas_optmizadas = rta_asig(rutas_optmizadas, rta_rutas_optmizadas)

names = ['cliente', 'costo', 'ruta']
rta_rutas_optmizadas_costos = pd.DataFrame(columns=names)
rta_rutas_optmizadas_costos = rta_asig_costos(rutas_optmizadas, rta_rutas_optmizadas_costos)


mport copy
import pandas as pd

#APLICACIÓN DE LA HEURISTICA DE MEJORA (SWAP)
new_rutas_optmizadas = []
new_rutas_optmizadas = copy.deepcopy(rutas_optmizadas)
rutas_optmizadas_2 = []

costo_total_inicial = costList[len(costList) - 1]

print(f"--- INICIANDO OPTIMIZACIÓN SWAP ---")
print(f"Costo total inicial: {costo_total_inicial}")

for i in range(len(new_rutas_optmizadas)):
    print(f"\n>>> Procesando ruta {i+1} de {len(new_rutas_optmizadas)}...", flush=True)
    mySol = new_rutas_optmizadas[i]
    costo = mySol[0]
    temp  = copy.deepcopy(mySol[1])

    num_HOSPITAL = -4
    if temp.iat[0, 0] == 'H1':
        num_HOSPITAL = 0
    elif temp.iat[0, 0] == 'H2':
        num_HOSPITAL = 1
    else:
        num_HOSPITAL = 2

    bandera = True
    iteracion = 0
    
    while bandera == True:
        iteracion += 1
        print(f"  [Ruta {i+1}] Iteración {iteracion} | Costo actual: {costo:.2f}", end="\r", flush=True)
        
        myNewSol = swap(costo, temp)

        if myNewSol[2] == False:
            print(f"  [Ruta {i+1}] No se encontraron más mejoras en la iteración {iteracion}. Saliendo del bucle.", flush=True)
            bandera = False
        else:
            costo_anterior = costo
            costo = myNewSol[0]
            temp  = copy.deepcopy(myNewSol[1])
            costo_despues = costo
            diferencia_costo = costo_despues - costo_anterior
            costo_total_inicial += diferencia_costo
            costList.append(costo_total_inicial)
            
            # Imprimir cuando hay una mejora
            print(f"\n  [Ruta {i+1}] ¡Mejora encontrada! Costo anterior: {costo_anterior:.2f} -> Nuevo costo: {costo_despues:.2f} (Diferencia: {diferencia_costo:.2f})", flush=True)

    rutas_optmizadas_2.append([costo, temp])

print(f"\n--- OPTIMIZACIÓN TERMINADA ---")
print(f"Costo total final: {costo_total_inicial}")
print(f"Total de rutas optimizadas: {len(rutas_optmizadas_2)}")

print("\nGenerando DataFrames...")
names = ['cliente', 'costo', 'ruta']
rta_rutas_optmizadas_2 = pd.DataFrame(columns=names)
rta_rutas_optmizadas_2 = rta_asig(rutas_optmizadas_2, rta_rutas_optmizadas_2)

print(rta_rutas_optmizadas_2)

names = ['cliente', 'costo', 'ruta']
rta_rutas_optmizadas_costos_2 = pd.DataFrame(columns=names)
rta_rutas_optmizadas_costos_2 = rta_asig_costos(rutas_optmizadas_2, rta_rutas_optmizadas_costos_2)

print(rta_rutas_optmizadas_costos_2)

APLICACIÓN DE LA HEURISTICA DE MEJORA (TWO OPTIMAL)
rutas_optmizadas_3 = []
costo_total_inicial = costList[len(costList) - 1]

for i in range(len(rutas_optmizadas_2)):
    mySol = rutas_optmizadas_2[i]
    Bestcost = mySol[0]

    temp_rut = copy.deepcopy(mySol[1])
    num_HOSPITAL = -5
    if mySol[1].iat[0, 0] == 'H1':
        num_HOSPITAL = 0
    elif mySol[1].iat[0, 0] == 'H2':
        num_HOSPITAL = 1
    else:
        num_HOSPITAL = 2

    xcon = 0

    bandera = True
    while bandera == True:
        myNewSol = twoOptimal_1(Bestcost, temp_rut)
        if myNewSol[2] == False:
            bandera = False
        else:
            costo_anterior = Bestcost
            Bestcost = myNewSol[0]
            temp_rut = copy.deepcopy(myNewSol[1])
            costo_despues = Bestcost
            diferencia_costo = costo_despues - costo_anterior
            costo_total_inicial += diferencia_costo
            costList.append(costo_total_inicial)

    rutas_optmizadas_3.append([Bestcost, temp_rut])

names = ['cliente', 'costo', 'ruta']
rta_rutas_optmizadas_3 = pd.DataFrame(columns=names)
rta_rutas_optmizadas_3 = rta_asig(rutas_optmizadas_3, rta_rutas_optmizadas_3)

names = ['cliente', 'costo', 'ruta']
rta_rutas_optmizadas_costos_3 = pd.DataFrame(columns=names)
print(rta_rutas_optmizadas_costos)
rta_rutas_optmizadas_costos_3 = rta_asig_costos(rutas_optmizadas_3, rta_rutas_optmizadas_costos_3)

print(rta_rutas_optmizadas_costos_3)
print(rutas_optmizadas_3)

import json
import os

KITS_POR_PACIENTE = 3


def metricas_solucion(lista_rutas):
    """Resume la solución final: distancia (km), tiempo (min), viajes y kits."""
    distancia_total = 0.0
    tiempo_total = 0.0
    kits_usados = 0

    for costo, df_ruta in lista_rutas:
        distancia_total += float(costo)
        nodos = df_ruta["cliente"].tolist()

        for origen, destino in zip(nodos[:-1], nodos[1:]):
            tiempo_total += float(tiempos.loc[origen, destino])

        for nodo in nodos:
            if not str(nodo).startswith("C"):
                continue
            kits_usados += KITS_POR_PACIENTE
            servicio = pacientes.loc[nodo, "Servicio"]
            tiempo_total += float(durserv.loc[servicio, "t"])

    return {
        "distancia_total": distancia_total,
        "tiempo_total": tiempo_total,
        "viajes_ambulancia": len(lista_rutas),
        "kits_usados": kits_usados,
    }


salida_heuristica = metricas_solucion(rutas_optmizadas_3)
print(salida_heuristica)

ruta_json = os.path.join(os.getcwd(), "salida_heuristica.json")
with open(ruta_json, "w", encoding="utf-8") as f:
    json.dump(salida_heuristica, f, ensure_ascii=False, indent=2)
print(f"Guardado en: {ruta_json}")