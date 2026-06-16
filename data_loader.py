import pandas as pd
import gdown
import os
import tempfile


# -----------------------------------------------------------------
# CONFIGURACIÓN DE FUENTES DE DATOS
# -----------------------------------------------------------------

ID_OPERACIONES = "1w_SMaC88aWgV0ZMG6kI17qu8I6ToCvgV"
ID_CLIENTES = "1-BoqjiefDtqQ0ILX-JFx1yZ30nHLmHQF"
ID_CIIU = "10n3IllrQRzMWzOcAL1tZ_cmvjXIzAze4"


# -----------------------------------------------------------------
# CONFIGURACIÓN DE BASE HISTÓRICA LOCAL
# -----------------------------------------------------------------

CARPETA_DATA = "data"
RUTA_OPERACIONES_HISTORICA = os.path.join(CARPETA_DATA, "operaciones_historica.xlsx")


# -----------------------------------------------------------------
# FUNCIONES GENERALES
# -----------------------------------------------------------------

def _normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Quita espacios extra en los nombres de columnas."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _normalizar_texto_series(serie: pd.Series) -> pd.Series:
    """Normaliza una serie para construir llaves consistentes."""
    return (
        serie.astype(str)
        .str.strip()
        .str.upper()
        .str.replace(r"\s+", " ", regex=True)
    )


def _descargar_y_leer(file_id: str, nombre: str = "archivo") -> pd.DataFrame:
    """
    Descarga un archivo de Google Drive por su ID usando gdown
    y lo carga como DataFrame.
    """
    carpeta_temp = tempfile.gettempdir()
    ruta_destino = os.path.join(carpeta_temp, f"{file_id}.xlsx")

    url = f"https://drive.google.com/uc?id={file_id}"

    resultado = gdown.download(url, ruta_destino, quiet=False)

    if resultado is None:
        raise RuntimeError(
            f"No se pudo descargar el archivo '{nombre}' (ID: {file_id}). "
            f"Verifica que esté compartido como 'Cualquier usuario con el enlace - Lector'."
        )

    if not os.path.exists(ruta_destino) or os.path.getsize(ruta_destino) == 0:
        raise RuntimeError(
            f"El archivo '{nombre}' (ID: {file_id}) se descargó vacío o no se guardó correctamente."
        )

    df = pd.read_excel(ruta_destino)
    return _normalizar_columnas(df)


def _convertir_fecha_si_existe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte la columna Fecha si existe.
    Sirve tanto para fechas tipo Excel numérico como fechas normales.
    """
    df = df.copy()

    if "Fecha" in df.columns:
        if pd.api.types.is_numeric_dtype(df["Fecha"]):
            df["Fecha"] = pd.to_datetime(
                df["Fecha"],
                origin="1899-12-30",
                unit="D",
                errors="coerce"
            )
        else:
            df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

    return df


# -----------------------------------------------------------------
# CARGA DESDE GOOGLE DRIVE
# -----------------------------------------------------------------

def cargar_operaciones() -> pd.DataFrame:
    """Carga la base de operaciones desde Google Drive."""
    df = _descargar_y_leer(ID_OPERACIONES, nombre="Operaciones")
    df = _convertir_fecha_si_existe(df)
    return df


def cargar_clientes() -> pd.DataFrame:
    """Carga la base de clientes/BUC desde Google Drive."""
    return _descargar_y_leer(ID_CLIENTES, nombre="Clientes/BUC")


def cargar_ciiu() -> pd.DataFrame:
    """Carga el catálogo CIIU desde Google Drive."""
    return _descargar_y_leer(ID_CIIU, nombre="CIIU")


# -----------------------------------------------------------------
# BASE HISTÓRICA LOCAL
# -----------------------------------------------------------------

def existe_base_operaciones_historica() -> bool:
    """Valida si ya existe una base histórica local de operaciones."""
    return (
        os.path.exists(RUTA_OPERACIONES_HISTORICA)
        and os.path.getsize(RUTA_OPERACIONES_HISTORICA) > 0
    )


def cargar_base_operaciones_historica() -> pd.DataFrame:
    """
    Carga la base histórica local de operaciones.
    Si no existe, devuelve un DataFrame vacío.
    """
    if not existe_base_operaciones_historica():
        return pd.DataFrame()

    df = pd.read_excel(RUTA_OPERACIONES_HISTORICA)
    df = _normalizar_columnas(df)
    df = _convertir_fecha_si_existe(df)

    return df


def guardar_base_operaciones_historica(df: pd.DataFrame) -> None:
    """Guarda la base histórica local de operaciones."""
    os.makedirs(CARPETA_DATA, exist_ok=True)

    df_guardar = df.copy()

    if "LLAVE_OPERACION" in df_guardar.columns:
        df_guardar = df_guardar.drop(columns=["LLAVE_OPERACION"])

    df_guardar.to_excel(RUTA_OPERACIONES_HISTORICA, index=False)


# -----------------------------------------------------------------
# LLAVE ÚNICA PARA EVITAR DUPLICADOS
# -----------------------------------------------------------------

def crear_llave_operacion(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crea una llave única para identificar operaciones.

    Prioridad:
    1. Si existe ID_OPERACION, usa esa columna.
    2. Si no existe, construye una llave con columnas de negocio.

    Nota:
    Lo ideal es que en la base exista una columna ID_OPERACION.
    """
    df = _normalizar_columnas(df)
    df = df.copy()

    if "ID_OPERACION" in df.columns:
        df["LLAVE_OPERACION"] = _normalizar_texto_series(df["ID_OPERACION"])
        return df

    posibles_columnas_llave = [
        "Fecha",
        "NIT",
        "Producto",
        "Lado",
        "Entidad",
        "Moneda",
        "Monto",
    ]

    columnas_disponibles = [
        col for col in posibles_columnas_llave
        if col in df.columns
    ]

    columnas_faltantes = [
        col for col in posibles_columnas_llave
        if col not in df.columns
    ]

    if len(columnas_disponibles) < 4:
        raise ValueError(
            "No se puede crear una llave única confiable para las operaciones. "
            f"Columnas disponibles para llave: {columnas_disponibles}. "
            f"Columnas faltantes esperadas: {columnas_faltantes}. "
            "Se recomienda agregar una columna ID_OPERACION."
        )

    partes_llave = []

    for col in columnas_disponibles:
        if col == "Fecha":
            fecha_normalizada = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
            partes_llave.append(fecha_normalizada.fillna("SIN_FECHA"))
        else:
            partes_llave.append(_normalizar_texto_series(df[col]).fillna("SIN_DATO"))

    df["LLAVE_OPERACION"] = partes_llave[0]

    for parte in partes_llave[1:]:
        df["LLAVE_OPERACION"] = df["LLAVE_OPERACION"] + "|" + parte

    return df


# -----------------------------------------------------------------
# LÓGICA DE CARGA DESDE STREAMLIT
# -----------------------------------------------------------------

def procesar_carga_streamlit(
    df_nuevo: pd.DataFrame,
    modo_carga: str,
) -> pd.DataFrame:
    """
    Procesa el archivo cargado desde Streamlit.

    modo_carga puede ser:
    - "Cargar toda la base"
    - "Cargar solo nuevos casos"

    Retorna la base histórica final.
    """
    if df_nuevo is None or df_nuevo.empty:
        raise ValueError("El archivo cargado no contiene registros.")

    df_nuevo = _normalizar_columnas(df_nuevo)
    df_nuevo = _convertir_fecha_si_existe(df_nuevo)
    df_nuevo = crear_llave_operacion(df_nuevo)

    if modo_carga == "Cargar toda la base":
        df_final = df_nuevo.copy()

    elif modo_carga == "Cargar solo nuevos casos":
        df_historico = cargar_base_operaciones_historica()

        if df_historico.empty:
            df_final = df_nuevo.copy()
        else:
            df_historico = _normalizar_columnas(df_historico)
            df_historico = _convertir_fecha_si_existe(df_historico)
            df_historico = crear_llave_operacion(df_historico)

            registros_antes = len(df_historico)

            df_final = pd.concat(
                [df_historico, df_nuevo],
                ignore_index=True
            )

            df_final = df_final.drop_duplicates(
                subset=["LLAVE_OPERACION"],
                keep="last"
            )

            registros_despues = len(df_final)
            registros_nuevos = registros_despues - registros_antes

            print(f"Registros históricos antes: {registros_antes}")
            print(f"Registros finales después: {registros_despues}")
            print(f"Registros nuevos agregados: {registros_nuevos}")

    else:
        raise ValueError(
            "Modo de carga no válido. Use 'Cargar toda la base' o 'Cargar solo nuevos casos'."
        )

    guardar_base_operaciones_historica(df_final)

    return df_final


# -----------------------------------------------------------------
# CRUCE DE BASES
# -----------------------------------------------------------------

def cruzar_bases(
    df_operaciones: pd.DataFrame,
    df_clientes: pd.DataFrame,
    df_ciiu: pd.DataFrame,
) -> pd.DataFrame:
    """
    Cruza las 3 bases en cadena:

    1) Operaciones <-> Clientes/BUC
       NIT = ID

    2) Resultado <-> CIIU
       CIIU_BUC = COD_ACT_CIIU_NOCLI
    """
    df_operaciones = _normalizar_columnas(df_operaciones)
    df_clientes = _normalizar_columnas(df_clientes)
    df_ciiu = _normalizar_columnas(df_ciiu)

    columnas_requeridas_ops = ["NIT"]
    columnas_requeridas_clientes = ["ID", "CIIU_BUC"]
    columnas_requeridas_ciiu = ["COD_ACT_CIIU_NOCLI"]

    for col in columnas_requeridas_ops:
        if col not in df_operaciones.columns:
            raise ValueError(f"No se encontró la columna requerida '{col}' en operaciones.")

    for col in columnas_requeridas_clientes:
        if col not in df_clientes.columns:
            raise ValueError(f"No se encontró la columna requerida '{col}' en clientes.")

    for col in columnas_requeridas_ciiu:
        if col not in df_ciiu.columns:
            raise ValueError(f"No se encontró la columna requerida '{col}' en CIIU.")

    df = df_operaciones.merge(
        df_clientes,
        left_on="NIT",
        right_on="ID",
        how="left",
        suffixes=("", "_cliente"),
    )

    df = df.merge(
        df_ciiu,
        left_on="CIIU_BUC",
        right_on="COD_ACT_CIIU_NOCLI",
        how="left",
        suffixes=("", "_ciiu"),
    )

    return df


# -----------------------------------------------------------------
# FUNCIONES DE APOYO PARA EL DASHBOARD
# -----------------------------------------------------------------

def obtener_lista_traders(
    df: pd.DataFrame,
    columna_trader: str = "Cod_Cartera",
) -> list:
    """Devuelve la lista de traders únicos presentes en los datos."""
    if columna_trader not in df.columns:
        raise ValueError(f"No existe la columna '{columna_trader}' en la base consolidada.")

    return sorted(df[columna_trader].dropna().unique().tolist())


def filtrar_por_trader(
    df: pd.DataFrame,
    trader_id,
    columna_trader: str = "Cod_Cartera",
) -> pd.DataFrame:
    """Filtra el DataFrame consolidado por trader."""
    if columna_trader not in df.columns:
        raise ValueError(f"No existe la columna '{columna_trader}' en la base consolidada.")

    return df[df[columna_trader] == trader_id]


def cargar_datos_completos() -> pd.DataFrame:
    """
    Carga las bases completas.

    Prioridad:
    1. Si existe base histórica local cargada por Streamlit, usa esa.
    2. Si no existe, carga operaciones desde Google Drive.
    """
    df_ops = cargar_base_operaciones_historica()

    if df_ops.empty:
        df_ops = cargar_operaciones()

    df_clientes = cargar_clientes()
    df_ciiu = cargar_ciiu()

    df_consolidado = cruzar_bases(df_ops, df_clientes, df_ciiu)

    return df_consolidado
