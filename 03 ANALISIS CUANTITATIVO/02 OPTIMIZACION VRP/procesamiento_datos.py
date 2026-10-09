"""Arma la base VRP a partir de NO-SUBIR/911.csv.

Replica el Power Query: EMS, cuatro enfermedades, Lower Merion, exclusión
de tres latitudes, recorte al cuadrado de Lower Merion, muestra
aleatoria de 96 clientes y anexo de 3 hospitales y 1 depósito.
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
CSV_911 = RAIZ / "NO-SUBIR" / "911.csv"
SALIDA = Path(__file__).resolve().parent / "puntos_vrp.xlsx"

N_CLIENTES = 96
SEMILLA = 42
COLUMNAS = ["lat", "lng", "desc", "zip", "title", "timeStamp", "twp", "addr", "e"]
ENFERMEDADES = [
    "DIZZINESS",
    "NAUSEA/VOMITING",
    "GENERAL WEAKNESS",
    "HEAT EXHAUSTION",
]
LATITUDES_EXCLUIDAS = {"40.0429364", "40.0581359", "40.0627596"}


def dms_a_decimal(grados: float, minutos: float, segundos: float, hemisferio: str) -> float:
    decimal = grados + minutos / 60 + segundos / 3600
    if hemisferio in {"S", "W"}:
        return -decimal
    return decimal


# Esquinas en orden: suroeste, sureste, noreste, noroeste.
CUADRADO = [
    (dms_a_decimal(39, 58, 44.56, "N"), dms_a_decimal(75, 20, 18.84, "W")),
    (dms_a_decimal(39, 58, 34.85, "N"), dms_a_decimal(75, 11, 42.98, "W")),
    (dms_a_decimal(40, 2, 23.25, "N"), dms_a_decimal(75, 11, 26.23, "W")),
    (dms_a_decimal(40, 2, 30.49, "N"), dms_a_decimal(75, 20, 10.83, "W")),
]
# Misma marca de tiempo que en la tabla de hospitales (serial de Excel).
MARCA_INSTALACION = pd.to_datetime(43588.89354, unit="D", origin="1899-12-30")

INSTALACIONES = pd.DataFrame(
    [
        {
            "lat": 39.98811,
            "lng": -75.26282,
            "desc": "HOSPITAL 1",
            "zip": 19096,
            "title": "HOSPITAL",
            "timeStamp": MARCA_INSTALACION,
            "twp": "LOWER MERION",
            "addr": "100 East Lancaster Avenue, Wynnewood",
            "e": 1,
        },
        {
            "lat": 40.01934,
            "lng": -75.32085,
            "desc": "HOSPITAL 2",
            "zip": 19010,
            "title": "HOSPITAL",
            "timeStamp": MARCA_INSTALACION,
            "twp": "LOWER MERION",
            "addr": "130 South Bryn Mawr Avenue, Bryn Mawr",
            "e": 1,
        },
        {
            "lat": 40.02894703263187,
            "lng": -75.20955726527649,
            "desc": "HOSPITAL 3",
            "zip": 19301,
            "title": "HOSPITAL",
            "timeStamp": MARCA_INSTALACION,
            "twp": "LOWER MERION",
            "addr": "255 West Lancaster Avenue",
            "e": 1,
        },
        {
            "lat": 40.00480682964976,
            "lng": -75.264368626472,
            "desc": "DEPOSITO",
            "zip": 19301,
            "title": "NARBERTH HEALT DEPARMENT",
            "timeStamp": MARCA_INSTALACION,
            "twp": "LOWER MERION",
            "addr": "100 Conway Ave, Narberth, PA 19072, Estados Unidos",
            "e": 1,
        },
    ]
)


def cargar_llamadas(ruta: Path) -> pd.DataFrame:
    """Lee el CSV con el mismo criterio del Power Query (Windows-1252, 9 columnas)."""
    return pd.read_csv(
        ruta,
        encoding="cp1252",
        dtype=str,
        usecols=COLUMNAS,
        low_memory=False,
    )


def filtrar_clientes(llamadas: pd.DataFrame) -> pd.DataFrame:
    """Aplica los pasos del Power Query hasta antes de anexar hospitales."""
    titulo = llamadas["title"].fillna("")
    partes = titulo.str.split(": ", n=1, expand=True)
    clientes = llamadas.copy()
    clientes["TIPO"] = partes[0]
    clientes["ENFERMEDAD"] = partes[1]

    clientes = clientes.loc[clientes["TIPO"].eq("EMS")]
    clientes = clientes.loc[clientes["ENFERMEDAD"].isin(ENFERMEDADES)]
    clientes = clientes.sort_values("ENFERMEDAD", kind="mergesort")
    clientes = clientes.loc[clientes["twp"].eq("LOWER MERION")]
    clientes = clientes.loc[~clientes["lat"].isin(LATITUDES_EXCLUIDAS)]

    clientes = clientes.drop(columns=["TIPO", "ENFERMEDAD"])
    clientes["lat"] = clientes["lat"].astype(float)
    clientes["lng"] = clientes["lng"].astype(float)
    clientes["zip"] = pd.to_numeric(clientes["zip"], errors="coerce").astype("Int64")
    clientes["timeStamp"] = pd.to_datetime(clientes["timeStamp"])
    clientes["e"] = pd.to_numeric(clientes["e"], errors="coerce").astype("Int64")
    return clientes.reset_index(drop=True)


def dentro_del_cuadrado(
    lat: pd.Series,
    lng: pd.Series,
    vertices: list[tuple[float, float]],
) -> pd.Series:
    """True si el punto cae dentro del cuadrilátero (lat, lng), borde incluido."""
    x = lng.to_numpy(dtype=float)
    y = lat.to_numpy(dtype=float)
    dentro = np.zeros(len(x), dtype=bool)
    vertice_anterior = len(vertices) - 1
    for indice in range(len(vertices)):
        lat_i, lng_i = vertices[indice]
        lat_j, lng_j = vertices[vertice_anterior]
        cruza = (lat_i > y) != (lat_j > y)
        denominador = lat_j - lat_i
        lng_cruce = np.divide(
            lng_j - lng_i,
            denominador,
            out=np.zeros_like(y),
            where=denominador != 0,
        ) * (y - lat_i) + lng_i
        dentro ^= cruza & (x <= lng_cruce)
        vertice_anterior = indice
    return pd.Series(dentro, index=lat.index)


def armar_base(clientes: pd.DataFrame) -> pd.DataFrame:
    instalaciones = INSTALACIONES.copy()
    instalaciones["zip"] = instalaciones["zip"].astype("Int64")
    instalaciones["e"] = instalaciones["e"].astype("Int64")
    return pd.concat([clientes[COLUMNAS], instalaciones[COLUMNAS]], ignore_index=True)


def main() -> None:
    llamadas = cargar_llamadas(CSV_911)
    clientes = filtrar_clientes(llamadas)
    dentro = dentro_del_cuadrado(clientes["lat"], clientes["lng"], CUADRADO)
    print(f"Clientes antes del cuadrado: {len(clientes):,}")
    print(f"Clientes dentro del cuadrado: {int(dentro.sum()):,}")
    clientes = clientes.loc[dentro].reset_index(drop=True)
    # Una llamada por coordenada: el mismo cruce no cuenta como dos puntos.
    clientes = (
        clientes.sample(frac=1, random_state=SEMILLA)
        .drop_duplicates(["lat", "lng"], keep="first")
        .sample(n=N_CLIENTES, random_state=SEMILLA)
        .reset_index(drop=True)
    )
    base = armar_base(clientes)
    destino = SALIDA
    try:
        base.to_excel(destino, sheet_name="MUESTRA", index=False)
    except PermissionError:
        destino = SALIDA.with_name("puntos_vrp_cuadrado.xlsx")
        base.to_excel(destino, sheet_name="MUESTRA", index=False)
        print(f"No se pudo sobrescribir {SALIDA.name} porque esta abierto.")

    n_hospitales = int(base["desc"].isin(["HOSPITAL 1", "HOSPITAL 2", "HOSPITAL 3"]).sum())
    n_deposito = int(base["desc"].eq("DEPOSITO").sum())
    print(f"Llamadas en el CSV: {len(llamadas):,}")
    print(f"Filas exportadas: {len(base):,} ({len(clientes):,} clientes, {n_hospitales} hospitales, {n_deposito} deposito)")
    print(base["title"].value_counts().to_string())
    print(f"Archivo: {destino}")
    if (len(clientes), n_hospitales, n_deposito, len(base)) != (N_CLIENTES, 3, 1, 100):
        raise SystemExit("La base no tiene 96 clientes, 3 hospitales y 1 deposito.")


if __name__ == "__main__":
    main()
