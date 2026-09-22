# %% [markdown]
# # Ruteo de Ambulancias — Red Vial con OSMnx
# 
# Este notebook resuelve el problema de calcular distancias y rutas reales
# por la red vial de una ciudad, usando únicamente Python.
# 
# **Requisitos:** `pip install osmnx networkx pandas matplotlib folium`

# %% [markdown]
# ## 1. Instalación de dependencias

# %%
# Descomentar y ejecutar solo la primera vez
# !pip install osmnx networkx pandas matplotlib folium

# %% [markdown]
# ## 2. Descargar la red vial

# %%
import osmnx as ox
import networkx as nx
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

# Configuración de osmnx
ox.settings.use_cache = True      # Cachea descargas para no repetir
ox.settings.log_console = False

# --- OPCIÓN A: Por nombre de ciudad ---
# G = ox.graph_from_place("Bogotá, Colombia", network_type="drive")

# --- OPCIÓN B: Por bounding box (más rápido, zona específica) ---
# Norte, Sur, Este, Oeste de la zona de interés
G = ox.graph_from_bbox(
    bbox=(4.75, 4.55, -73.98, -74.15),  # (north, south, east, west)
    network_type="drive"
)

# --- OPCIÓN C: Desde un punto + radio en metros ---
# G = ox.graph_from_point((4.6508, -74.0721), dist=5000, network_type="drive")

print(f"Nodos: {G.number_of_nodes():,}")
print(f"Aristas: {G.number_of_edges():,}")

# %% [markdown]
# ## 3. Agregar velocidades y tiempos de viaje

# %%
# osmnx asigna velocidades según el tipo de vía (highway tag de OSM)
# y calcula travel_time en segundos para cada arista
G = ox.add_edge_speeds(G)
G = ox.add_edge_travel_times(G)

# Verificar que se asignaron
ejemplo = list(G.edges(data=True))[0]
print(f"Ejemplo de arista:")
print(f"  Longitud: {ejemplo[2].get('length', '?'):.0f} m")
print(f"  Velocidad: {ejemplo[2].get('speed_kph', '?')} km/h")
print(f"  Tiempo: {ejemplo[2].get('travel_time', '?'):.1f} seg")

# %% [markdown]
# ## 4. Definir puntos (estaciones y emergencias)

# %%
# Ejemplo: una estación y varias emergencias
# Reemplaza con tus datos reales del CSV de 911

estaciones = pd.DataFrame({
    "id": ["E1", "E2"],
    "nombre": ["Estación Norte", "Estación Centro"],
    "lat": [4.6850, 4.6250],
    "lon": [-74.0550, -74.0700],
})

emergencias = pd.DataFrame({
    "id": ["P1", "P2", "P3", "P4", "P5"],
    "lat": [4.6689, 4.6352, 4.6750, 4.6100, 4.6500],
    "lon": [-74.0836, -74.0612, -74.0400, -74.0850, -74.0650],
})

# Punto de retorno al final del turno
punto_retorno = {"id": "R1", "lat": 4.6508, "lon": -74.0721}

# Combinar todos los puntos para la matriz
todos = pd.concat([
    estaciones[["id", "lat", "lon"]],
    emergencias[["id", "lat", "lon"]],
    pd.DataFrame([punto_retorno])
], ignore_index=True)

print(todos)

# %% [markdown]
# ## 5. Snap de coordenadas a la red vial

# %%
# Cada coordenada se "snapea" al nodo más cercano del grafo
todos["nodo_osm"] = todos.apply(
    lambda row: ox.nearest_nodes(G, X=row["lon"], Y=row["lat"]),
    axis=1
)

# Verificar qué tan lejos quedó el snap (si es >200m, la coordenada
# puede estar fuera de la red — zona peatonal, parque, etc.)
for _, row in todos.iterrows():
    nodo = row["nodo_osm"]
    lat_nodo = G.nodes[nodo]["y"]
    lon_nodo = G.nodes[nodo]["x"]
    dist_snap = ox.distance.great_circle(row["lat"], row["lon"], lat_nodo, lon_nodo)
    print(f"{row['id']}: snap a {dist_snap:.0f} m del punto original")

# %% [markdown]
# ## 6. Calcular la matriz de tiempos de viaje

# %%
def calcular_matriz_tiempos(G, puntos_df, peso="travel_time"):
    """
    Calcula la matriz NxN de tiempos de viaje (en minutos).
    Retorna inf si no hay ruta posible.
    """
    nodos = puntos_df["nodo_osm"].tolist()
    ids = puntos_df["id"].tolist()
    n = len(nodos)
    
    matriz = np.full((n, n), np.inf)
    np.fill_diagonal(matriz, 0)
    
    rutas_fallidas = []
    
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            try:
                t = nx.shortest_path_length(G, nodos[i], nodos[j], weight=peso)
                matriz[i][j] = t / 60  # convertir segundos a minutos
            except nx.NetworkXNoPath:
                rutas_fallidas.append((ids[i], ids[j]))
    
    df_matriz = pd.DataFrame(matriz, index=ids, columns=ids).round(2)
    
    if rutas_fallidas:
        print(f"⚠️ {len(rutas_fallidas)} pares sin ruta posible:")
        for o, d in rutas_fallidas[:5]:
            print(f"   {o} → {d}")
    
    return df_matriz


matriz_base = calcular_matriz_tiempos(G, todos)
print("\nMatriz de tiempos (minutos):")
print(matriz_base)

# %% [markdown]
# ## 7. Calcular y visualizar una ruta específica

# %%
def obtener_ruta(G, df, id_origen, id_destino, peso="travel_time"):
    """Calcula la ruta más corta entre dos puntos por ID."""
    nodo_o = df.loc[df["id"] == id_origen, "nodo_osm"].values[0]
    nodo_d = df.loc[df["id"] == id_destino, "nodo_osm"].values[0]
    
    ruta = nx.shortest_path(G, nodo_o, nodo_d, weight=peso)
    tiempo = nx.shortest_path_length(G, nodo_o, nodo_d, weight=peso)
    distancia = nx.shortest_path_length(G, nodo_o, nodo_d, weight="length")
    
    print(f"Ruta {id_origen} → {id_destino}:")
    print(f"  Tiempo:    {tiempo/60:.1f} min")
    print(f"  Distancia: {distancia/1000:.2f} km")
    print(f"  Nodos:     {len(ruta)}")
    
    return ruta


# Ejemplo: de la estación E1 a la emergencia P1
ruta_ejemplo = obtener_ruta(G, todos, "E1", "P1")

# Visualización estática con matplotlib
fig, ax = ox.plot_graph_route(G, ruta_ejemplo, route_linewidth=3,
                               node_size=0, figsize=(12, 12))

# %% [markdown]
# ## 8. Visualización interactiva con Folium

# %%
def mapa_ruta_interactivo(G, ruta, puntos_df, nombre="Ruta"):
    """Genera un mapa interactivo con la ruta y los puntos."""
    import folium
    
    # Coordenadas de la ruta
    coords_ruta = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in ruta]
    centro = [np.mean([c[0] for c in coords_ruta]),
              np.mean([c[1] for c in coords_ruta])]
    
    m = folium.Map(location=centro, zoom_start=13, tiles="CartoDB positron")
    
    # Dibujar la ruta
    folium.PolyLine(coords_ruta, weight=4, color="blue", opacity=0.8).add_to(m)
    
    # Marcar puntos
    colores = {"E": "green", "P": "red", "R": "purple"}
    for _, row in puntos_df.iterrows():
        color = colores.get(row["id"][0], "gray")
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=8, color=color, fill=True,
            popup=row["id"], tooltip=row["id"]
        ).add_to(m)
    
    return m


mapa = mapa_ruta_interactivo(G, ruta_ejemplo, todos)
mapa  # En Jupyter se renderiza automáticamente

# %% [markdown]
# ---
# # Simulación de Cierres Viales
# ---

# %% [markdown]
# ## 9. Framework de escenarios

# %%
def cerrar_calles(G, cierres):
    """
    Modifica el grafo según las reglas de cierre.
    
    Cada cierre es un dict:
      {"tipo": "eliminar", "nombre": "Avenida Caracas"}
      {"tipo": "tramo",    "nombre": "Caracas", "lat_min": 4.62, "lat_max": 4.66}
      {"tipo": "penalizar","nombre": "Calle 80", "factor": 5}
    
    Retorna un nuevo grafo (no modifica el original).
    """
    G_mod = G.copy()
    resumen = []
    
    for cierre in cierres:
        aristas_afectadas = []
        
        for u, v, k, data in G_mod.edges(keys=True, data=True):
            nombre_via = str(data.get("name", ""))
            
            if cierre["nombre"].lower() not in nombre_via.lower():
                continue
            
            if cierre["tipo"] == "tramo":
                lat = G_mod.nodes[u]["y"]
                if not (cierre["lat_min"] <= lat <= cierre["lat_max"]):
                    continue
            
            aristas_afectadas.append((u, v, k, data))
        
        if cierre["tipo"] == "penalizar":
            factor = cierre.get("factor", 5)
            for u, v, k, data in aristas_afectadas:
                data["travel_time"] *= factor
            resumen.append(f"  Penalizadas {len(aristas_afectadas)} aristas "
                          f"de '{cierre['nombre']}' x{factor}")
        else:
            G_mod.remove_edges_from([(u, v, k) for u, v, k, _ in aristas_afectadas])
            resumen.append(f"  Eliminadas {len(aristas_afectadas)} aristas "
                          f"de '{cierre['nombre']}'")
    
    print("Modificaciones aplicadas:")
    for r in resumen:
        print(r)
    
    return G_mod

# %% [markdown]
# ## 10. Definir y correr escenarios

# %%
escenarios = {
    "base": [],
    
    "cierre_caracas": [
        {"tipo": "eliminar", "nombre": "Avenida Caracas"}
    ],
    
    "cierre_tramo_caracas": [
        {"tipo": "tramo", "nombre": "Caracas",
         "lat_min": 4.62, "lat_max": 4.66}
    ],
    
    "congestion_calle80": [
        {"tipo": "penalizar", "nombre": "Calle 80", "factor": 5}
    ],
    
    "crisis": [
        {"tipo": "eliminar", "nombre": "Avenida Caracas"},
        {"tipo": "penalizar", "nombre": "Calle 80", "factor": 10},
        {"tipo": "eliminar", "nombre": "Autopista Norte"},
    ],
}


resultados = {}

for nombre, cierres in escenarios.items():
    print(f"\n{'='*50}")
    print(f"Escenario: {nombre}")
    print(f"{'='*50}")
    
    if cierres:
        G_esc = cerrar_calles(G, cierres)
    else:
        G_esc = G
    
    matriz = calcular_matriz_tiempos(G_esc, todos)
    resultados[nombre] = matriz
    print(f"\nMatriz de tiempos (min):")
    print(matriz)

# %% [markdown]
# ## 11. Comparar escenarios

# %%
def comparar_escenarios(resultados, escenario_base="base"):
    """Muestra el incremento porcentual respecto al escenario base."""
    base = resultados[escenario_base]
    
    comparaciones = {}
    for nombre, matriz in resultados.items():
        if nombre == escenario_base:
            continue
        
        # Calcular incremento porcentual (ignorando inf y diagonal)
        mask = (base > 0) & (base < np.inf) & (matriz < np.inf)
        if mask.any().any():
            incremento = ((matriz[mask] - base[mask]) / base[mask] * 100)
            comparaciones[nombre] = {
                "incremento_promedio_%": round(incremento.mean(), 1),
                "incremento_maximo_%": round(incremento.max(), 1),
                "pares_sin_ruta": (matriz == np.inf).sum().sum(),
            }
    
    return pd.DataFrame(comparaciones).T


print("Impacto de cada escenario vs. base:")
print(comparar_escenarios(resultados))

# %% [markdown]
# ## 12. Visualizar ruta base vs. escenario de cierre

# %%
def comparar_rutas_visual(G_base, G_mod, df, id_o, id_d):
    """Dibuja ambas rutas superpuestas."""
    import folium
    
    nodo_o = df.loc[df["id"] == id_o, "nodo_osm"].values[0]
    nodo_d = df.loc[df["id"] == id_d, "nodo_osm"].values[0]
    
    ruta_base = nx.shortest_path(G_base, nodo_o, nodo_d, weight="travel_time")
    t_base = nx.shortest_path_length(G_base, nodo_o, nodo_d, weight="travel_time")
    
    try:
        ruta_mod = nx.shortest_path(G_mod, nodo_o, nodo_d, weight="travel_time")
        t_mod = nx.shortest_path_length(G_mod, nodo_o, nodo_d, weight="travel_time")
    except nx.NetworkXNoPath:
        print(f"❌ No hay ruta {id_o} → {id_d} en el escenario modificado")
        return None
    
    coords_base = [(G_base.nodes[n]["y"], G_base.nodes[n]["x"]) for n in ruta_base]
    coords_mod = [(G_mod.nodes[n]["y"], G_mod.nodes[n]["x"]) for n in ruta_mod]
    
    centro = coords_base[len(coords_base)//2]
    m = folium.Map(location=centro, zoom_start=13, tiles="CartoDB positron")
    
    folium.PolyLine(coords_base, weight=4, color="blue", opacity=0.7,
                    tooltip=f"Base: {t_base/60:.1f} min").add_to(m)
    folium.PolyLine(coords_mod, weight=4, color="red", opacity=0.7,
                    tooltip=f"Modificado: {t_mod/60:.1f} min").add_to(m)
    
    # Marcadores origen/destino
    folium.Marker(coords_base[0], popup=id_o,
                  icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(coords_base[-1], popup=id_d,
                  icon=folium.Icon(color="red")).add_to(m)
    
    print(f"Ruta {id_o} → {id_d}:")
    print(f"  Base:       {t_base/60:.1f} min")
    print(f"  Modificado: {t_mod/60:.1f} min")
    print(f"  Incremento: +{(t_mod-t_base)/60:.1f} min ({(t_mod/t_base-1)*100:.0f}%)")
    
    return m


# Comparar E1 → P1 en base vs cierre de Caracas
G_cierre = cerrar_calles(G, escenarios["cierre_caracas"])
mapa_comparacion = comparar_rutas_visual(G, G_cierre, todos, "E1", "P1")
mapa_comparacion

# %% [markdown]
# ## 13. Exportar matriz para el modelo de optimización

# %%
# Guardar la matriz de cada escenario como CSV
for nombre, matriz in resultados.items():
    archivo = f"matriz_tiempos_{nombre}.csv"
    matriz.to_csv(archivo)
    print(f"Exportada: {archivo}")

# La matriz también se puede exportar como numpy array
# para alimentar directamente a OR-Tools, PuLP, etc.
matriz_np = resultados["base"].to_numpy()
print(f"\nForma de la matriz: {matriz_np.shape}")
print(f"Tipo: {matriz_np.dtype}")