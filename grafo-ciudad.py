import osmnx as ox
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import warnings
import sklearn
from pathlib import Path
import pandas as pd
from time import time
import folium
import webbrowser

warnings.filterwarnings("ignore")

# Configuración de osmnx
ox.settings.use_cache = True 
ox.settings.log_console = False

def crear_grafo(ciudad = "Montgomery County, Pennsylvania, USA"):
    G = ox.graph_from_place(ciudad, network_type="drive")
    # Agregar velocidades y tiempos de viaje
    # osmnx asigna velocidades según el tipo de vía (highway tag de OSM)
    # y calcula travel_time en segundos para cada arista
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)

    print(f"Nodos: {G.number_of_nodes():,}")
    print(f"Aristas: {G.number_of_edges():,}")
    return G
G = crear_grafo()

def verificar_grafo(G):
    # Verificar que se asignaron
    ejemplo = list(G.edges(data=True))[0]
    print(f"Ejemplo de arista:")
    print(f"  Longitud: {ejemplo[2].get('length', '?'):.0f} m")
    print(f"  Velocidad: {ejemplo[2].get('speed_kph', '?')} km/h")
    print(f"  Tiempo: {ejemplo[2].get('travel_time', '?'):.1f} seg")
    return G

EXCEL_ANALISIS = Path(__file__).resolve().parent / "analisis.xlsx"

def leer_analisis(
    ruta: Path | str = EXCEL_ANALISIS,
    hoja: str | int = 0,
) -> pd.DataFrame:
    """Lee analisis.xlsx.
    """
    df = pd.read_excel(ruta, sheet_name=hoja, usecols="A:D")
    df.insert(0, "Punto", [f"P{i}" for i in range(1, len(df) + 1)])
    return df

df_puntos = leer_analisis()


def puntos_cercanos_grafo(df_puntos, G = crear_grafo()):
    # Cada coordenada se asocia al nodo más cercano del grafo
    df_puntos["nodo_osm"] = df_puntos.apply(
    lambda row: ox.nearest_nodes(G, X=row["lng"], Y=row["lat"]),
    axis=1)
    return df_puntos

df_puntos = puntos_cercanos_grafo(df_puntos, G)


def matriz_tiempos(df_puntos, G):

    ids = df_puntos["Punto"].tolist()
    nodos_lista = df_puntos["nodo_osm"].tolist()
    n = len(nodos_lista)
    matriz = np.full((n, n), np.inf)

    inicio = time()

    for i in range(n):
        # Dijkstra desde el nodo i a TODOS los nodos del grafo (una sola vez)
        tiempos = nx.single_source_dijkstra_path_length(
            G, nodos_lista[i], weight="travel_time"
        )
        for j in range(n):
            if i == j:
                matriz[i][j] = 0
            elif nodos_lista[j] in tiempos:
                matriz[i][j] = tiempos[nodos_lista[j]] / 60  # a minutos

    print(f"Tiempo de cálculo: {time() - inicio:.1f} seg")

    df_matriz = pd.DataFrame(matriz, index=ids, columns=ids).round(2)
    return df_matriz


df_matriz = matriz_tiempos(df_puntos, G)
df_matriz.to_csv("matriz_tiempos_30x30.csv")

def mapa_rutas(G, df_puntos, df_matriz, origen="P37"):
    """
    Dibuja rutas sobre el mapa.
    - Si origen es un ID (ej "E1"), dibuja solo las rutas desde ese punto.
    - Si origen es None, dibuja todas las rutas.
    
    Requiere:
      G:          grafo de osmnx (en memoria)
      puntos:     DataFrame con columnas id, lat, lon, nodo
      df_matriz:  DataFrame con la matriz de tiempos (index y columns = ids)
    """
    ids = df_matriz.index.tolist()
    centro = [df_puntos["lat"].mean(), df_puntos["lng"].mean()]
    
    m = folium.Map(location=centro, zoom_start=12, tiles="CartoDB positron")
    
    # Marcar puntos
    for _, row in df_puntos.iterrows():
        if row["desc"].startswith("HOSPITAL"):
            color, icono = "green", "plus"
        elif row["desc"].startswith("DEPOSITO"):
            color, icono = "green", "plus"
        else:
            color, icono = "purple", "flag"
        
        folium.CircleMarker(
            location=[row["lat"], row["lng"]],
            radius=8, color=color, fill=True, fill_opacity=0.8,
            tooltip=row["Punto"]
        ).add_to(m)
    
    # Definir pares a dibujar
    if origen is not None:
        origenes = [origen]
    else:
        origenes = ids
    
    colores_linea = ["blue", "red", "orange", "darkgreen", "purple",
                     "cadetblue", "darkred", "pink", "darkblue", "green"]
    
    rutas_dibujadas = 0
    rutas_fallidas = 0
    
    for idx_o, o in enumerate(origenes):
        nodo_o = df_puntos.loc[df_puntos["Punto"] == o, "nodo_osm"].values[0]
        color_linea = colores_linea[idx_o % len(colores_linea)]
        
        for d in ids:
            if o == d:
                continue
            
            tiempo = df_matriz.loc[o, d]
            if tiempo == np.inf or np.isnan(tiempo):
                continue
            
            nodo_d = df_puntos.loc[df_puntos["Punto"] == d, "nodo_osm"].values[0]
            
            try:
                ruta = nx.shortest_path(G, nodo_o, nodo_d, weight="travel_time")
                coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in ruta]
                
                folium.PolyLine(
                    coords,
                    weight=3,
                    opacity=0.5 if not origen else 0.7,
                    color=color_linea,
                    tooltip=f"{o} → {d}: {tiempo:.1f} min"
                ).add_to(m)
                rutas_dibujadas += 1
            except nx.NetworkXNoPath:
                rutas_fallidas += 1
    
    print(f"Rutas dibujadas: {rutas_dibujadas}")
    if rutas_fallidas:
        print(f"Rutas sin camino: {rutas_fallidas}")
    
    return m

m = mapa_rutas(G, df_puntos, df_matriz, origen="P37")
m.save("mapa_rutas.html")
webbrowser.open("mapa_rutas.html")