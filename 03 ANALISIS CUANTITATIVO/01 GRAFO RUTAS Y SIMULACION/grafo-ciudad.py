import osmnx as ox
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import warnings
import sklearn
from pathlib import Path
import pandas as pd
from time import time
from collections import defaultdict
import random
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


def verificar_grafo(G):
    # Verificar que se asignaron
    ejemplo = list(G.edges(data=True))[0]
    print(f"Ejemplo de arista:")
    print(f"  Longitud: {ejemplo[2].get('length', '?'):.0f} m")
    print(f"  Velocidad: {ejemplo[2].get('speed_kph', '?')} km/h")
    print(f"  Tiempo: {ejemplo[2].get('travel_time', '?'):.1f} seg")
    return G


EXCEL_ANALISIS = (
    Path(__file__).resolve().parent.parent
    / "02 OPTIMIZACION VRP"
    / "puntos_vrp.xlsx"
)
def leer_analisis(
    ruta: Path | str = EXCEL_ANALISIS,
    hoja: str | int = 0,
) -> pd.DataFrame:
    """Lee analisis.xlsx.
    """
    df = pd.read_excel(ruta, sheet_name=hoja, usecols="A:D")
    df.insert(0, "Punto", [f"P{i}" for i in range(1, len(df) + 1)])
    return df




def puntos_cercanos_grafo(df_puntos, G = crear_grafo()):
    # Cada coordenada se asocia al nodo más cercano del grafo
    df_puntos["nodo_osm"] = df_puntos.apply(
    lambda row: ox.nearest_nodes(G, X=row["lng"], Y=row["lat"]),
    axis=1)
    return df_puntos




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
    df_matriz_tiempos=pd.DataFrame(matriz, index=ids, columns=ids).round(2)
    return df_matriz_tiempos
    



def matriz_distancias(df_puntos, G):
    ids = df_puntos["Punto"].tolist()
    nodos_lista = df_puntos["nodo_osm"].tolist()
    n = len(nodos_lista)
    matriz = np.full((n, n), np.inf)

    inicio = time()

    for i in range(n):
        distancias = nx.single_source_dijkstra_path_length(G, nodos_lista[i], weight="length")
        for j in range(n):
            if i == j:
                matriz[i, j] = 0
            elif nodos_lista[j] in distancias:
                matriz[i, j] = distancias[nodos_lista[j]] / 1000  # a kilómetros
    print(f"Tiempo de cálculo: {time() - inicio:.1f} seg")

    df_matriz_distancias = pd.DataFrame(matriz, index=ids, columns=ids).round(2)
    return df_matriz_distancias



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


def topografia_grafo(G, ruta="topografia_grafo.html"):
    """Exporta la topografía del grafo (nodos y aristas) a un mapa HTML.

    Cada nodo es una intersección y cada arista es el tramo de calle que
    las une. El mapa pinta la geometría real de la red. Las aristas se
    colorean según el tipo de vía (highway de OSM). Entre dos nodos se
    dibuja un solo tramo, aunque el grafo tenga la arista en ambos sentidos.

    El HTML se guarda junto a este script, no en el directorio desde el
    que se lanzó Python.

    Parametros:
        G (networkx.MultiDiGraph): grafo creado por crear_grafo.
        ruta (str): archivo HTML de salida. Si es relativo, se guarda
            en la misma carpeta que grafo-ciudad.py.

    Retorna:
        pathlib.Path: ruta del HTML guardado.
    """
    import json

    destino = Path(ruta)
    if not destino.is_absolute():
        destino = Path(__file__).resolve().parent / destino

    print("Generando topografía del grafo...")

    def a_texto(valor):
        if isinstance(valor, list):
            return ", ".join(str(v) for v in valor)
        if valor is None or (isinstance(valor, float) and np.isnan(valor)):
            return ""
        return str(valor)

    def coords_arista(u, v, data):
        geom = data.get("geometry")
        if geom is not None:
            return [[round(x, 5), round(y, 5)] for x, y in geom.coords]
        return [
            [round(G.nodes[u]["x"], 5), round(G.nodes[u]["y"], 5)],
            [round(G.nodes[v]["x"], 5), round(G.nodes[v]["y"], 5)],
        ]

    # El grafo es dirigido: u->v y v->u comparten geometría. Se dibuja una vez.
    aristas = []
    vistos = set()
    for u, v, data in G.edges(data=True):
        par = (u, v) if u <= v else (v, u)
        if par in vistos:
            continue
        vistos.add(par)
        largo = data.get("length")
        aristas.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords_arista(u, v, data)},
            "properties": {
                "name": a_texto(data.get("name")),
                "highway": a_texto(data.get("highway")),
                "length": 0 if largo is None else int(round(float(largo))),
            },
        })

    nodos = []
    for n, data in G.nodes(data=True):
        nodos.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [round(data["x"], 5), round(data["y"], 5)],
            },
            "properties": {"id": str(n)},
        })

    aristas_json = json.dumps(
        {"type": "FeatureCollection", "features": aristas},
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("<", "\\u003c")
    nodos_json = json.dumps(
        {"type": "FeatureCollection", "features": nodos},
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("<", "\\u003c")

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Topografía del grafo</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body, #map {{ height: 100%; margin: 0; }}
  #info {{
    position: absolute; z-index: 1000; top: 12px; left: 56px;
    background: #fff; padding: 10px 14px; border-radius: 8px;
    font-family: Segoe UI, sans-serif; font-size: 13px; line-height: 1.45;
    box-shadow: 0 1px 6px rgba(0,0,0,.25);
  }}
</style>
</head>
<body>
<div id="info">
  <b>Topografía del grafo</b><br>
  Nodos: {G.number_of_nodes():,}<br>
  Aristas: {G.number_of_edges():,}
</div>
<div id="map"></div>
<script>
const aristas = {aristas_json};
const nodos = {nodos_json};
const colores = {{
  motorway: "#c0392b", motorway_link: "#e74c3c",
  trunk: "#d35400", trunk_link: "#e67e22",
  primary: "#b7950b", primary_link: "#f1c40f",
  secondary: "#1a5276", secondary_link: "#2980b9",
  tertiary: "#0e6655", tertiary_link: "#16a085",
  residential: "#7f8c8d", unclassified: "#95a5a6",
  living_street: "#85929e", service: "#aab7b8"
}};
const map = L.map("map");
L.tileLayer("https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png", {{
  attribution: "&copy; OpenStreetMap &copy; CARTO",
  subdomains: "abcd",
  maxZoom: 20
}}).addTo(map);
const canvas = L.canvas({{padding: 0.5}});
const capaAristas = L.geoJSON(aristas, {{
  renderer: canvas,
  style: function (f) {{
    const tipo = String(f.properties.highway || "").split(",")[0].trim();
    return {{color: colores[tipo] || "#2c3e50", weight: 2, opacity: 0.85}};
  }},
  onEachFeature: function (f, layer) {{
    const p = f.properties;
    layer.bindTooltip((p.name || "(sin nombre)") + "<br>" + (p.highway || "") + "<br>" + p.length + " m");
  }}
}}).addTo(map);
const capaNodos = L.geoJSON(nodos, {{
  renderer: canvas,
  pointToLayer: function (f, latlng) {{
    return L.circleMarker(latlng, {{
      renderer: canvas, radius: 3, color: "#1c2833", weight: 1,
      fillColor: "#1c2833", fillOpacity: 0.9
    }});
  }},
  onEachFeature: function (f, layer) {{
    layer.bindTooltip("Nodo " + f.properties.id);
  }}
}}).addTo(map);
map.fitBounds(capaAristas.getBounds());
L.control.layers(null, {{"Aristas": capaAristas, "Nodos": capaNodos}}, {{collapsed: false}}).addTo(map);
</script>
</body>
</html>
"""
    destino.write_text(html, encoding="utf-8")
    print(f"Topografía guardada en {destino}")
    webbrowser.open(destino.resolve().as_uri())
    return destino



# Orden de ejecucion de las funciones:

# Crear grafo para la ciudad de Montgomery County, Pennsylvania, USA
G = crear_grafo()
"""
# Leer puntos del archivo analisis.xlsx (Puntos: Coordenadas y Descripción previamente seleccionadas. 40 puntos en total incluyendo hospitales,depósitos y pacientes) 
df_puntos = leer_analisis()

# Asociar cada punto a su nodo más cercano en el grafo
df_puntos = puntos_cercanos_grafo(df_puntos, G)
"""
# Matriz de tiempos entre todos los puntos. La matriz se guarda en el archivo matriz_tiempos_nxn.csv
"""
df_matriz_tiempos = matriz_tiempos(df_puntos, G)
df_matriz_tiempos.to_csv("matriz_tiempos_nxn.csv")

# Calcular la matriz de distancias entre todos los puntos. La matriz se guarda en el archivo matriz_distancias_nxn.csv
df_matriz_distancias = matriz_distancias(df_puntos, G)
df_matriz_distancias.to_csv("matriz_distancias_nxn.csv")


# Dibujar las rutas en el mapa. La ruta se guarda en el archivo mapa_rutas.html. Se dibuja la ruta desde un origen (ej: P37, que es un hospital) hasta todos los otros puntos.
m = mapa_rutas(G, df_puntos, df_matriz_tiempos, origen="P37")
m.save("mapa_rutas.html")
webbrowser.open("mapa_rutas.html")

"""
"""
#Topografia del grafo
topografia_grafo(G, ruta="topografia_grafo.html")
"""