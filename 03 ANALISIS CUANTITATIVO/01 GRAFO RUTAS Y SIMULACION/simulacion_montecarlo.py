import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import copy
from pathlib import Path

# rutas desde este archivo, no desde donde lo corra
RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ.parent / "02 OPTIMIZACION VRP" / "DATOS.xlsx"

# datos
insta = 5
np.random.seed(126)


depcentral = pd.read_excel(DATOS, sheet_name='hospitales')
pacientes  = pd.read_excel(DATOS, sheet_name='Pacientes', index_col=2)
eco        = pd.read_excel(DATOS, sheet_name='eco capital')

durserv = pd.read_excel(DATOS, sheet_name='Tiempo de servicio', index_col=0)
durserv.columns = ['t']

tiempos = pd.read_csv(RAIZ / "matriz_tiempos_cierre.csv", index_col=0)

distancias_km = pd.read_csv(RAIZ / "matriz_distancias_cierre.csv", index_col=0)

 
limtiemp = 6 * 60
limkits  = 36
 
N_SIM = 30
CV    = 0.05
 
# 30 matrices de distancia
mu = distancias_km.values.astype(float)
n  = mu.shape[0]
iu = np.triu_indices(n, k=1)
rng = np.random.default_rng(126)
 
distancias_sim = []
for s in range(N_SIM):
    sim = np.zeros_like(mu)
    vals = rng.normal(loc=mu[iu], scale=CV * mu[iu])
    sim[iu]             = vals
    sim[(iu[1], iu[0])] = vals
    distancias_sim.append(pd.DataFrame(sim, index=distancias_km.index, columns=distancias_km.columns))
 
 
# funciones del notebook
def rta_asig(rutas_optmizadas_2, rta_rutas_optmizadas_2):
    filas = []
    for i in range(len(rutas_optmizadas_2)):
        rut   = rutas_optmizadas_2[i][1]
        costo = rutas_optmizadas_2[i][0]
        for j in range(rut.shape[0]):
            cliente = rut.iat[j, 0]
            ruta    = rut.iat[j, 1]
            filas.append({
                'cliente': cliente,
                'costo':   costo,
                'ruta':    ruta
            })
    nuevo_df = pd.DataFrame(filas, columns=['cliente', 'costo', 'ruta'])
    return pd.concat([rta_rutas_optmizadas_2, nuevo_df], ignore_index=True)
 
 
def rta_asig_costos(rutas_optmizadas, rta_rutas_optmizadas_costos):
    filas = []
    for i in range(len(rutas_optmizadas)):
        rut   = rutas_optmizadas[i][1]
        costo = rutas_optmizadas[i][0]
        cliente = rut.iat[0, 0]
        ruta    = rut.iat[0, 1]
        filas.append({
            'cliente': cliente,
            'costo':   costo,
            'ruta':    ruta
        })
    nuevo_df = pd.DataFrame(filas, columns=['cliente', 'costo', 'ruta'])
    return pd.concat([rta_rutas_optmizadas_costos, nuevo_df], ignore_index=True)
 
 
def suma_costo(R_optmizadas):
    costo_total = 0
    for i in range(len(R_optmizadas)):
        costo_total += R_optmizadas[i][0]
    return costo_total
 
 
def conteo_split(I, J, newRoute):
    dif = J - I
    costo_split = 0
    for i in range(dif):
        d = distancias[num_HOSPITAL][0].loc[newRoute.iat[I + i, 0], newRoute.iat[I + i + 1, 0]]
        costo_split += d
    return costo_split
 
 
def conteo_quieto(I, J, newRoute):
    dif = J - I
    costo_split = 0
    for i in range(dif):
        d = distancias[num_HOSPITAL][0].loc[newRoute.iat[I + i, 0], newRoute.iat[I + i + 1, 0]]
        costo_split += d
    return costo_split
 
 
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
 
 
# 30 simulaciones: cambia la distancia y a que hospital queda cada cliente
resultados = []
 
for s in range(N_SIM):
    print(f"\n{'='*60}")
    print(f"  SIMULACION {s+1}/{N_SIM}")
    print(f"{'='*60}")
 
    distancias_km_actual = distancias_sim[s]
 
    # asigno cada cliente al hospital mas cercano en terminos de tiempo. Se le suma la desviacion estandar de 10% en cada iteracion 
    tiempos_sim = tiempos.loc[:, ['H1', 'H2', 'H3']] * (1 + rng.normal(0, 0.10, (len(tiempos), 3)))
 
    tabdistan = tiempos_sim.loc[:, ['H1', 'H2', 'H3']].copy()
    lista = []
    for cliente in tabdistan.index:
        a = tabdistan.loc[cliente, :].idxmin()
        lista.append(a)
    tabdistan['hospital asignado'] = lista
    tabdistan.loc['Eco', 'hospital asignado'] = 'H1'
 
    # separo por hospital
    tabdistan.iloc[-1, -1] = 'H1'
    b1clie = tabdistan[tabdistan['hospital asignado'] == 'H1']
    tabdistan.iloc[-1, -1] = 'H2'
    b2clie = tabdistan[tabdistan['hospital asignado'].isna() | (tabdistan['hospital asignado'] == 'H2')]
    tabdistan.iloc[-1, -1] = 'H3'
    b3clie = tabdistan[tabdistan['hospital asignado'].isna() | (tabdistan['hospital asignado'] == 'H3')]
    globa = [b1clie, b2clie, b3clie]
 
    # distancias en km por hospital
    distancias = []
    for hospital in globa:
        matrix = []
        for cust in hospital.index:
            parcial = []
            for othercust in hospital.index:
                if cust == othercust:
                    distan = np.nan
                else:
                    distan = distancias_km_actual.loc[cust, othercust]
                parcial.append(distan)
            matrix.append(parcial)
        matrix = pd.DataFrame(matrix)
        matrix.index = hospital.index
        matrix.columns = hospital.index
        distancias.append([matrix])
 
    # tiempos en min por hospital
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
 
    # vecino mas cercano, una ruta grande por hospital
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
 
    # parto cada ruta grande en ambulancias (tiempo y kits)
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
 
            tiempo = (distancias_t[rutas][0].loc[subrutas[rutas][0][i], cliente_sig]
                      + tiempo_serv + tiempo)
 
            if (tiempo + (distancias_t[rutas][0].loc[cliente_sig, 'Eco']) > limtiemp) \
                    or len(temporal) * 3 > limkits - 1:
                tiempo = 0
                temporal.append(['Eco', j])
                j += 1
                rutaamb.append(temporal)
                temporal = []
                temporal.append([subrutas[rutas][0][0], j])
                temporal.append([cliente_sig, j])
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
 
    # heuristica constructiva
    costList = []
    numero = 1
    rutas_optmizadas = []
    names = ['cliente', 'ruta']
    temp = pd.DataFrame(columns=names)
 
    for i in range(asig_ambulancias.shape[0]):
        if numero != asig_ambulancias.iloc[i, 1] and 0 != i:
            numero = asig_ambulancias.iloc[i, 1]
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
    costo_constructivo = costList[-1]
 
    # swap
    new_rutas_optmizadas = copy.deepcopy(rutas_optmizadas)
    rutas_optmizadas_2 = []
    costo_total_inicial = costList[-1]
    iter_swap = 0
 
    for i in range(len(new_rutas_optmizadas)):
        mySol = new_rutas_optmizadas[i]
        costo = mySol[0]
        temp  = copy.deepcopy(mySol[1])
 
        if temp.iat[0, 0] == 'H1':
            num_HOSPITAL = 0
        elif temp.iat[0, 0] == 'H2':
            num_HOSPITAL = 1
        else:
            num_HOSPITAL = 2
 
        bandera = True
        while bandera == True:
            myNewSol = swap(costo, temp)
            if myNewSol[2] == False:
                bandera = False
            else:
                iter_swap += 1
                costo_anterior = costo
                costo = myNewSol[0]
                temp  = copy.deepcopy(myNewSol[1])
                diferencia_costo = costo - costo_anterior
                costo_total_inicial += diferencia_costo
                costList.append(costo_total_inicial)
 
        rutas_optmizadas_2.append([costo, temp])
 
    costo_despues_swap = suma_costo(rutas_optmizadas_2)
 
    # 2-opt
    rutas_optmizadas_3 = []
    costo_total_inicial = costList[-1]
    iter_twoopt = 0
 
    for i in range(len(rutas_optmizadas_2)):
        mySol = rutas_optmizadas_2[i]
        Bestcost = mySol[0]
        temp_rut = copy.deepcopy(mySol[1])
 
        if mySol[1].iat[0, 0] == 'H1':
            num_HOSPITAL = 0
        elif mySol[1].iat[0, 0] == 'H2':
            num_HOSPITAL = 1
        else:
            num_HOSPITAL = 2
 
        bandera = True
        while bandera == True:
            myNewSol = twoOptimal_1(Bestcost, temp_rut)
            if myNewSol[2] == False:
                bandera = False
            else:
                iter_twoopt += 1
                costo_anterior = Bestcost
                Bestcost = myNewSol[0]
                temp_rut = copy.deepcopy(myNewSol[1])
                diferencia_costo = Bestcost - costo_anterior
                costo_total_inicial += diferencia_costo
                costList.append(costo_total_inicial)
 
        rutas_optmizadas_3.append([Bestcost, temp_rut])
 
    # metricas de esta simulacion
    dist_total = 0.0
    tiempo_total = 0.0
    kits = 0
    viajes_H1 = 0; viajes_H2 = 0; viajes_H3 = 0
    pacientes_H1 = 0; pacientes_H2 = 0; pacientes_H3 = 0
 
    for costo, df_ruta in rutas_optmizadas_3:
        dist_total += float(costo)
        nodos = df_ruta['cliente'].tolist()
        hosp_ini = nodos[0]
        if hosp_ini == 'H1':
            num_HOSPITAL = 0
        elif hosp_ini == 'H2':
            num_HOSPITAL = 1
        else:
            num_HOSPITAL = 2
        D_t = distancias_t[num_HOSPITAL][0]
        for j in range(len(nodos) - 1):
            tiempo_total += D_t.loc[nodos[j], nodos[j + 1]]
        for nodo in nodos:
            if nodo not in ('H1', 'H2', 'H3', 'Eco'):
                tiempo_total += durserv.loc[pacientes.loc[nodo, 'Servicio'], 't']
                kits += 3
                if hosp_ini == 'H1':
                    pacientes_H1 += 1
                elif hosp_ini == 'H2':
                    pacientes_H2 += 1
                else:
                    pacientes_H3 += 1
        v = sum(1 for nodo in nodos if nodo == 'Eco')
        if hosp_ini == 'H1':
            viajes_H1 += v
        elif hosp_ini == 'H2':
            viajes_H2 += v
        else:
            viajes_H3 += v
 
    costo_despues_twoopt = dist_total
 
    pct_mejora_swap = ((costo_constructivo - costo_despues_swap) / costo_constructivo * 100) if costo_constructivo != 0 else 0.0
    pct_mejora_twoopt = ((costo_despues_swap - costo_despues_twoopt) / costo_despues_swap * 100) if costo_despues_swap != 0 else 0.0
 
    resultados.append({
        'simulacion': s + 1,
        'tiempo_total': tiempo_total,
        'costo_constructivo': costo_constructivo,
        'costo_despues_swap': costo_despues_swap,
        'costo_despues_twoopt': costo_despues_twoopt,
        'pct_mejora_swap': pct_mejora_swap,
        'pct_mejora_twoopt': pct_mejora_twoopt,
        'iter_swap': iter_swap,
        'iter_twoopt': iter_twoopt,
        'viajes_H1': viajes_H1,
        'viajes_H2': viajes_H2,
        'viajes_H3': viajes_H3,
        'pacientes_H1': pacientes_H1,
        'pacientes_H2': pacientes_H2,
        'pacientes_H3': pacientes_H3,
    })
 
    print(f"  Tiempo total              : {tiempo_total:.2f} min")
    print(f"  Costo constructivo        : {costo_constructivo:.4f} km")
    print(f"  Costo despues de swap     : {costo_despues_swap:.4f} km")
    print(f"  Costo despues de two-opt  : {costo_despues_twoopt:.4f} km")
    print(f"  % mejora por swap         : {pct_mejora_swap:.2f} %")
    print(f"  % mejora por two-opt      : {pct_mejora_twoopt:.2f} %")
    print(f"  Iteraciones swap          : {iter_swap}")
    print(f"  Iteraciones two-opt       : {iter_twoopt}")
    print(f"  Viajes H1 / H2 / H3       : {viajes_H1} / {viajes_H2} / {viajes_H3}")
    print(f"  Pacientes H1 / H2 / H3    : {pacientes_H1} / {pacientes_H2} / {pacientes_H3}")
    print("=" * 60)
 
 
# lo guardo en excel
df_resultados = pd.DataFrame(resultados)
df_resultados.columns = [
    'Simulacion',
    'Tiempo total (min)',
    'Costo constructivo (km)',
    'Costo despues de swap (km)',
    'Costo despues de two-opt (km)',
    '% mejora por swap',
    '% mejora por two-opt',
    'Iteraciones swap',
    'Iteraciones two-opt',
    'Viajes H1',
    'Viajes H2',
    'Viajes H3',
    'Pacientes H1',
    'Pacientes H2',
    'Pacientes H3',
]
 
with pd.ExcelWriter(RAIZ / "resultados_simulaciones.xlsx") as writer:
    df_resultados.to_excel(writer, sheet_name='Resultados', index=False)
 
    resumen = (
        df_resultados.drop(columns=['Simulacion'])
        .agg(['mean', 'std', 'min', 'max'])
    )
 
    # viajes, pacientes e iteraciones los dejo enteros, redondeando para arriba
    cols_ceil = [
        'Iteraciones swap',
        'Iteraciones two-opt',
        'Viajes H1',
        'Viajes H2',
        'Viajes H3',
        'Pacientes H1',
        'Pacientes H2',
        'Pacientes H3',
    ]
 
    resumen[cols_ceil] = np.ceil(resumen[cols_ceil]).astype(int)
 
    resumen = resumen.round(4)
 
    resumen.to_excel(writer, sheet_name='Resumen')
 
print("\nResultados exportados a 'resultados_simulaciones.xlsx'")
