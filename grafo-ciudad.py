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


def _nombres_arista(data):
    """Normaliza el nombre OSM de una arista a una lista de strings.

    En el grafo de osmnx el atributo "name" no tiene un solo formato:
    puede ser un str ("Main Street"), una list (la arista pertenece a
    más de una calle) o puede no existir.

    Parametros:
        data (dict): atributos de una arista. Claves típicas: name, length, travel_time.

    Retorna:
        list[str]: nombres no vacíos de la arista.
        Lista vacía si la arista no tiene nombre; esas aristas no entran
        al ranking ni se pueden cerrar por nombre de calle.
    """
    nombre = data.get("name")
    # Un solo nombre: se envuelve en lista para tratar todos los casos igual.
    if isinstance(nombre, str) and nombre:
        return [nombre]
    # Varios nombres: se descartan valores que no sean texto o que vengan vacíos.
    if isinstance(nombre, list):
        return [n for n in nombre if isinstance(n, str) and n]
    return []


def _arista_minima(G, u, v, weight):
    """Elige la arista de menor peso entre dos nodos.

    El grafo es un MultiDiGraph: entre el mismo par u -> v puede haber
    varias aristas paralelas, cada una con su clave k. Dijkstra reconstruye
    el camino solo como lista de nodos, así que esta función recupera cuál
    de esas aristas paralelas se usó (la de menor weight).

    Parametros:
        G (networkx.MultiDiGraph): grafo de calles.
        u: nodo origen de la arista (id OSM).
        v: nodo destino de la arista (id OSM).
        weight (str): atributo a minimizar. En este script es "travel_time" (segundos).

    Retorna:
        tuple[clave, dict, float]:
            clave: key de la arista elegida dentro del MultiDiGraph. None si no hay arista.
            dict: atributos de esa arista (name, length, travel_time, ...). None si no hay arista.
            float: peso de esa arista. np.inf si no hay arista o el atributo no existe.
    """
    mejor_k, mejor_data, mejor_w = None, None, np.inf
    # G[u][v] es un dict {clave: atributos} con todas las aristas paralelas u -> v.
    for k, data in G[u][v].items():
        w = data.get(weight, np.inf)
        if w < mejor_w:
            mejor_k, mejor_data, mejor_w = k, data, w
    return mejor_k, mejor_data, mejor_w


def _componentes_calles(G):
    """Agrupa las aristas en calles.

    Una calle no es una sola arista: es la cadena de aristas que comparten
    nombre y se tocan por algún nodo. El mismo nombre puede existir en
    municipios distintos del condado; si esos tramos no se tocan, salen
    como calles distintas ("Main Street #1", "Main Street #2").
    Las aristas sin nombre se ignoran.

    Parametros:
        G (networkx.MultiDiGraph): grafo de calles, con coordenadas x/y en los nodos
        y atributos name y length en las aristas.

    Retorna:
        tuple[dict, dict]:
            catalogo (dict[str, dict]): calle_id -> ficha de la calle.
                calle_id (str): por ejemplo "Main Street #1".
                nombre (str): nombre OSM, sin el número.
                n_aristas (int): cuántas aristas forman la calle.
                km (float): suma de length de esas aristas, en kilómetros.
                lat (float), lng (float): promedio de las coordenadas de sus nodos.
                aristas (list[tuple]): cada item es (u, v, key), lo que se borra al cerrar la calle.
            edge_to_calles (dict[tuple, list[str]]): (u, v, key) -> calle_id que usan esa arista.
                Si la arista tiene dos nombres, aparece en las dos calles.
    """
    class UnionFind:
        """Libreta de grupos de nodos.

        Sirve para encadenar tramos de la misma calle. Si A-B, B-C y C-D
        se llaman igual, A y D quedan en el mismo grupo aunque no haya
        una arista directa entre ellos.
        """

        def __init__(self):
            # parent[nodo] = representante de su grupo. Vacío al inicio.
            self.parent = {}

        def find(self, x):
            """Devuelve el representante (jefe) del grupo de x.

            Retorna:
                el mismo tipo que x (id de nodo OSM). Si x entra por primera
                vez, queda como jefe de su propio grupo.
            """
            # Primera vez que se ve el nodo: se apunta a sí mismo.
            self.parent.setdefault(x, x)
            # Si apunta a otro nodo, se sigue la cadena hasta el jefe.
            if self.parent[x] != x:
                self.parent[x] = self.find(self.parent[x])
            return self.parent[x]

        def union(self, a, b):
            """Mete los grupos de a y de b en uno solo.

            No retorna nada. Si ya estaban en el mismo grupo, no cambia la libreta.
            """
            ra, rb = self.find(a), self.find(b)
            if ra != rb:
                # El grupo de b pasa a pertenecer al grupo de a.
                self.parent[rb] = ra

    # nombre -> lista de (u, v, key, atributos) de todas las aristas con ese nombre.
    edges_by_name = defaultdict(list)
    # nombre -> UnionFind propio. Una libreta por nombre evita mezclar calles distintas
    # que se cruzan en el mismo nodo.
    ufs = {}
    for u, v, k, data in G.edges(keys=True, data=True):
        for nombre in _nombres_arista(data):
            edges_by_name[nombre].append((u, v, k, data))
            # union ignora la dirección: u->v y v->u caen en la misma calle.
            ufs.setdefault(nombre, UnionFind()).union(u, v)

    catalogo = {}
    edge_to_calles = defaultdict(list)
    # Orden alfabético para que "Main Street #1" sea siempre el mismo grupo.
    for nombre in sorted(edges_by_name):
        uf = ufs[nombre]
        # jefe del grupo -> aristas de ese tramo conexo.
        grupos = defaultdict(list)
        for u, v, k, data in edges_by_name[nombre]:
            grupos[uf.find(u)].append((u, v, k, data))
        # Se numeran los grupos por el id de nodo más pequeño, para que el #1 no cambie entre ejecuciones.
        raices = sorted(grupos, key=lambda r: min(n for uv in grupos[r] for n in uv[:2]))
        for i, raiz in enumerate(raices, start=1):
            grupo = grupos[raiz]
            calle_id = f"{nombre} #{i}"
            nodos = set()
            km = 0.0
            aristas = []
            for u, v, k, data in grupo:
                nodos.add(u)
                nodos.add(v)
                # length de osmnx está en metros.
                km += data.get("length", 0) / 1000
                aristas.append((u, v, k))
                edge_to_calles[(u, v, k)].append(calle_id)
            catalogo[calle_id] = {
                "calle_id": calle_id,
                "nombre": nombre,
                "n_aristas": len(grupo),
                "km": km,
                "lat": float(np.mean([G.nodes[n]["y"] for n in nodos])),
                "lng": float(np.mean([G.nodes[n]["x"] for n in nodos])),
                "aristas": aristas,
            }
    return catalogo, edge_to_calles


def _reconstruir_camino(pred, origen, destino):
    """Arma la lista de nodos del camino más corto.

    dijkstra_predecessor_and_distance no devuelve el camino: devuelve, para
    cada nodo, cuál es el nodo anterior. Esta función camina esa cadena
    desde el destino hasta el origen y luego la invierte.

    Parametros:
        pred (dict): predecesores que devuelve NetworkX. pred[nodo] es una
            list de nodos anteriores. Se usa solo el primero, pred[nodo][0].
        origen: nodo de partida (id OSM).
        destino: nodo de llegada (id OSM).

    Retorna:
        list | None: nodos en orden de viaje, por ejemplo [origen, ..., destino].
        [origen] si origen y destino son el mismo nodo.
        None si no hay camino o si la cadena de predecesores se corta o hace un ciclo.
    """
    if destino == origen:
        return [origen]
    # Sin predecesor no hay forma de llegar al destino desde este origen.
    if destino not in pred or not pred[destino]:
        return None
    # Se construye al revés: primero el destino, luego quien va antes.
    camino = [destino]
    actual = destino
    vistos = set()
    while actual != origen:
        # Un nodo repetido sería un ciclo, no un camino válido.
        if actual in vistos or actual not in pred or not pred[actual]:
            return None
        vistos.add(actual)
        actual = pred[actual][0]
        camino.append(actual)
    camino.reverse()
    return camino


def uso_calles(G, df_puntos, weight="travel_time"):
    """Cuenta qué calles usan los caminos mínimos entre todos los puntos.

    Recorre cada par ordenado (P_i -> P_j, i distinto de j). Una calle suma
    1 por cada ruta que la toca al menos una vez, aunque la ruta use varios
    tramos de esa calle. En el mismo recorrido se llena la matriz de tiempos,
    para no repetir Dijkstra al comparar un cierre.

    Parametros:
        G (networkx.MultiDiGraph): grafo con travel_time (segundos) y length (metros).
        df_puntos (pandas.DataFrame): puntos del análisis. Debe traer las columnas
            "Punto" (P1, P2, ...) y "nodo_osm" (nodo del grafo más cercano).
        weight (str): atributo con el que Dijkstra elige el camino. Por defecto
            "travel_time".

    Retorna:
        tuple[pandas.DataFrame, pandas.DataFrame, dict]:
            df_uso: una fila por calle usada, ordenada de mayor a menor usos.
                Columnas: calle_id (str), nombre (str), usos (int), pct (float,
                porcentaje sobre n*(n-1) rutas), n_aristas (int), km (float),
                minutos (float, suma del tiempo de los tramos usados), lat (float),
                lng (float). Las calles con 0 usos no aparecen.
            df_tiempos: matriz de minutos entre puntos. Index y columnas son los
                id de "Punto". La diagonal es 0. Si no hay camino, la celda queda inf.
            catalogo (dict[str, dict]): el mismo catálogo de _componentes_calles,
                incluyendo las calles que nadie usó. Hace falta para saber qué
                aristas borrar en simular_cierre_calles.
    """
    # Catálogo de calles y el mapa arista -> calle_id.
    catalogo, edge_to_calles = _componentes_calles(G)
    ids = df_puntos["Punto"].tolist()
    nodos = df_puntos["nodo_osm"].tolist()
    n = len(nodos)
    # Pares ordenados: de cada punto hacia cada uno de los demás.
    total_rutas = n * (n - 1)
    # usos[calle_id] = cuántas rutas la tocan. minutos[calle_id] = tiempo acumulado sobre ella.
    usos = defaultdict(int)
    minutos = defaultdict(float)
    # inf marca los pares que todavía no tienen camino.
    matriz = np.full((n, n), np.inf)

    inicio = time()
    for i in range(n):
        # Un solo Dijkstra por origen. pred permite reconstruir el camino;
        # dist trae el tiempo en segundos hasta cada nodo alcanzable.
        pred, dist = nx.dijkstra_predecessor_and_distance(G, nodos[i], weight=weight)
        for j in range(n):
            if i == j:
                matriz[i, j] = 0
                continue
            if nodos[j] not in dist:
                continue
            matriz[i, j] = dist[nodos[j]] / 60
            camino = _reconstruir_camino(pred, nodos[i], nodos[j])
            # Un camino de un solo nodo no tiene aristas que contar.
            if not camino or len(camino) < 2:
                continue
            # calles_ruta evita sumar la misma calle más de una vez en esta ruta.
            calles_ruta = set()
            for u, v in zip(camino[:-1], camino[1:]):
                k, data, w = _arista_minima(G, u, v, weight)
                if k is None:
                    continue
                for calle_id in edge_to_calles.get((u, v, k), []):
                    calles_ruta.add(calle_id)
                    # w está en segundos; se acumula aunque la calle ya esté en el set,
                    # porque cada tramo suma tiempo.
                    minutos[calle_id] += w / 60
            for calle_id in calles_ruta:
                usos[calle_id] += 1

    print(f"Uso de calles: {time() - inicio:.1f} seg")
    filas = []
    for calle_id, info in catalogo.items():
        n_usos = usos.get(calle_id, 0)
        if n_usos == 0:
            continue
        filas.append({
            "calle_id": calle_id,
            "nombre": info["nombre"],
            "usos": n_usos,
            "pct": round(100 * n_usos / total_rutas, 2),
            "n_aristas": info["n_aristas"],
            "km": round(info["km"], 2),
            "minutos": round(minutos[calle_id], 2),
            "lat": round(info["lat"], 5),
            "lng": round(info["lng"], 5),
        })
    # Primero las más usadas. Si empatan en usos, queda arriba la de más minutos.
    df_uso = pd.DataFrame(filas).sort_values(
        ["usos", "minutos"], ascending=False
    ).reset_index(drop=True)
    df_tiempos = pd.DataFrame(matriz, index=ids, columns=ids).round(2)
    return df_uso, df_tiempos, catalogo


def _impacto_cierre(tiempos_antes, tiempos_despues):
    """Compara el tiempo de cada par antes y después de cerrar calles.

    Parametros:
        tiempos_antes (pandas.DataFrame): matriz de minutos con el grafo original.
            Index y columnas son los id de punto (P1, P2, ...).
        tiempos_despues (pandas.DataFrame): la misma matriz sobre el grafo sin las calles cerradas.

    Retorna:
        pandas.DataFrame: una fila por par ordenado, sin la diagonal.
            origen (str), destino (str): id de punto.
            min_antes (float): minutos en el grafo original. inf si ya no había ruta.
            min_despues (float): minutos tras el cierre. inf si el par quedó sin ruta.
            delta_min (float): min_despues - min_antes. NaN si alguno de los dos es inf.
            sin_ruta (bool): True si tras el cierre no hay camino.
        Además imprime cuántos pares se afectan, cuántos quedan sin ruta y el desvío medio y máximo.
    """
    ids = tiempos_antes.index.tolist()
    filas = []
    for origen in ids:
        for destino in ids:
            if origen == destino:
                continue
            antes = tiempos_antes.loc[origen, destino]
            despues = tiempos_despues.loc[origen, destino]
            sin_ruta = not np.isfinite(despues)
            # Sin los dos tiempos finitos no hay un desvío que restar.
            if sin_ruta or not np.isfinite(antes):
                delta = np.nan
            else:
                delta = despues - antes
            filas.append({
                "origen": origen,
                "destino": destino,
                "min_antes": antes,
                "min_despues": despues,
                "delta_min": round(delta, 2) if np.isfinite(delta) else np.nan,
                "sin_ruta": sin_ruta,
            })
    df = pd.DataFrame(filas)
    con_delta = df["delta_min"].dropna()
    # Afectado: se quedó sin ruta, o el nuevo camino tarda más de 0.01 min.
    afectados = df[(df["sin_ruta"]) | (df["delta_min"] > 0.01)]
    print(f"Pares afectados: {len(afectados)} de {len(df)}")
    print(f"Pares sin ruta tras el cierre: {int(df['sin_ruta'].sum())}")
    if len(con_delta):
        print(f"Desvío medio: {con_delta.mean():.2f} min")
        print(f"Desvío máximo: {con_delta.max():.2f} min")
    return df


def simular_cierre_calles(G, df_puntos, calles=None, n=3, df_uso=None, tiempos_antes=None, catalogo=None):
    """Quita calles del grafo y recalcula las rutas entre los puntos.

    No modifica G: trabaja sobre una copia. Cierra la calle completa, es decir
    todas las aristas de ese calle_id, en ambos sentidos si existen.

    Parametros:
        G (networkx.MultiDiGraph): grafo original.
        df_puntos (pandas.DataFrame): mismos puntos que usa uso_calles
            (columnas "Punto" y "nodo_osm").
        calles (list[str] | None): calle_id a cerrar, por ejemplo ["Main Street #1"].
            Si es None, se cierran las n primeras filas de df_uso.
        n (int): cuántas calles del ranking cerrar cuando calles es None. Por defecto 3.
        df_uso (pandas.DataFrame | None): ranking que ya devolvió uso_calles.
            Si falta, junto con tiempos_antes o catalogo, se calcula aquí.
        tiempos_antes (pandas.DataFrame | None): matriz de minutos del grafo original.
        catalogo (dict | None): catálogo de _componentes_calles. De aquí salen las
            aristas que se borran.

    Retorna:
        tuple[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]:
            df_impacto: comparación por par. Ver _impacto_cierre.
            df_tiempos: matriz de minutos con las calles ya cerradas.
                Mismo formato que matriz_tiempos: index y columnas = id de punto, valores en minutos.
            df_distancias: matriz de kilómetros con las calles ya cerradas.
                Mismo formato que matriz_distancias.
    """
    # Si el caller no trae el análisis previo, se calcula en este momento.
    if df_uso is None or tiempos_antes is None or catalogo is None:
        df_uso, tiempos_antes, catalogo = uso_calles(G, df_puntos)
    if calles is None:
        calles = df_uso["calle_id"].head(n).tolist()

    # La copia evita borrar aristas del grafo con el que se calculó el ranking.
    H = G.copy()
    print("Calles cerradas:")
    for calle_id in calles:
        info = catalogo.get(calle_id)
        if info is None:
            print(f"  {calle_id}: no está en el catálogo")
            continue
        H.remove_edges_from(info["aristas"])
        print(f"  {calle_id}: {info['n_aristas']} aristas, {info['km']:.2f} km")

    # Mismas funciones del grafo abierto, ahora sobre el grafo sin esas calles.
    df_tiempos = matriz_tiempos(df_puntos, H)
    df_distancias = matriz_distancias(df_puntos, H)
    df_impacto = _impacto_cierre(tiempos_antes, df_tiempos)
    return df_impacto, df_tiempos, df_distancias


# Orden de ejecucion de las funciones:

# Crear grafo para la ciudad de Montgomery County, Pennsylvania, USA
G = crear_grafo()

# Leer puntos del archivo analisis.xlsx (Puntos: Coordenadas y Descripción previamente seleccionadas. 40 puntos en total incluyendo hospitales,depósitos y pacientes) 
df_puntos = leer_analisis()

# Asociar cada punto a su nodo más cercano en el grafo
df_puntos = puntos_cercanos_grafo(df_puntos, G)
"""
# Matriz de tiempos entre todos los puntos. La matriz se guarda en el archivo matriz_tiempos_nxn.csv
df_matriz_tiempos = matriz_tiempos(df_puntos, G)
df_matriz_tiempos.to_csv("matriz_tiempos_nxn.csv")
"""
# Calcular la matriz de distancias entre todos los puntos. La matriz se guarda en el archivo matriz_distancias_nxn.csv
df_matriz_distancias = matriz_distancias(df_puntos, G)
df_matriz_distancias.to_csv("matriz_distancias_nxn.csv")

# Calles más usadas en los caminos mínimos entre los 40 puntos
df_uso, df_tiempos_antes, catalogo_calles = uso_calles(G, df_puntos)
df_uso.to_csv("uso_calles.csv", index=False)

# Cierre de las 3 calles con más usos y rutas alternativas
df_impacto, df_tiempos_cierre, df_distancias_cierre = simular_cierre_calles(
    G, df_puntos, n=3, df_uso=df_uso, tiempos_antes=df_tiempos_antes, catalogo=catalogo_calles
)
df_impacto.to_csv("impacto_cierre.csv", index=False)
df_tiempos_cierre.to_csv("matriz_tiempos_cierre.csv")
df_distancias_cierre.to_csv("matriz_distancias_cierre.csv")

"""
# Dibujar las rutas en el mapa. La ruta se guarda en el archivo mapa_rutas.html. Se dibuja la ruta desde un origen (ej: P37, que es un hospital) hasta todos los otros puntos.
m = mapa_rutas(G, df_puntos, df_matriz_tiempos, origen="P37")
m.save("mapa_rutas.html")
webbrowser.open("mapa_rutas.html")

"""