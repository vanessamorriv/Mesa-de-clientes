import pandas as pd

# -----------------------------------------------------------------
# CONFIGURACIÓN DE FUENTES DE DATOS
# -----------------------------------------------------------------
# Por ahora, lee de la carpeta local /data
# Cuando tengas el enlace público de OneDrive, reemplaza estas rutas
# por las URLs de descarga directa (ej: "https://onedrive.live.com/download?...")

RUTA_OPERACIONES = "data/operaciones.xlsx"
RUTA_CLIENTES = "data/clientes.xlsx"
RUTA_CIIU = "data/ciiu.xlsx"


def _normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Quita espacios extra en los nombres de columnas."""
    df.columns = [c.strip() for c in df.columns]
    return df


def cargar_operaciones(ruta: str = RUTA_OPERACIONES) -> pd.DataFrame:
    """Carga la base de operaciones (Fecha, NIT, Producto, Lado, Entidad, Moneda, Montos)."""
    df = pd.read_excel(ruta)
    return _normalizar_columnas(df)


def cargar_clientes(ruta: str = RUTA_CLIENTES) -> pd.DataFrame:
    """Carga la base de perfiles de clientes/BUC (ID, Segmento, Cod_Cartera, CIIU_BUC, etc.)."""
    df = pd.read_excel(ruta)
    return _normalizar_columnas(df)


def cargar_ciiu(ruta: str = RUTA_CIIU) -> pd.DataFrame:
    """Carga el catálogo CIIU (código -> nombre del sector económico)."""
    df = pd.read_excel(ruta)
    return _normalizar_columnas(df)


def cruzar_bases(
    df_operaciones: pd.DataFrame,
    df_clientes: pd.DataFrame,
    df_ciiu: pd.DataFrame,
) -> pd.DataFrame:
    """
    Cruza las 3 bases en cadena:

    1) Operaciones <-> Clientes/BUC   por NIT (operaciones) = ID (clientes)
    2) Resultado    <-> CIIU          por CIIU_BUC (clientes) = COD_ACT_CIIU_NOCLI (ciiu)

    Devuelve la base consolidada final, lista para usar en la app.
    """
    # 1) Operaciones + Clientes
    df = df_operaciones.merge(
        df_clientes,
        left_on="NIT",
        right_on="ID",
        how="left",
        suffixes=("", "_cliente"),
    )

    # 2) + CIIU (agrega nombre del sector económico)
    df = df.merge(
        df_ciiu,
        left_on="CIIU_BUC",
        right_on="COD_ACT_CIIU_NOCLI",
        how="left",
        suffixes=("", "_ciiu"),
    )

    return df


def obtener_lista_traders(df: pd.DataFrame, columna_trader: str = "Cod_Cartera") -> list:
    """Devuelve la lista de traders únicos (valores de Cod_Cartera) presentes en los datos."""
    return sorted(df[columna_trader].dropna().unique().tolist())


def filtrar_por_trader(df: pd.DataFrame, trader_id, columna_trader: str = "Cod_Cartera") -> pd.DataFrame:
    """Filtra el dataframe consolidado para mostrar solo los registros de un trader específico."""
    return df[df[columna_trader] == trader_id]


def cargar_datos_completos():
    """
    Función de conveniencia: carga las 3 bases, las cruza en cadena,
    y devuelve el dataframe consolidado listo para usar en la app.
    """
    df_ops = cargar_operaciones()
    df_clientes = cargar_clientes()
    df_ciiu = cargar_ciiu()
    df_consolidado = cruzar_bases(df_ops, df_clientes, df_ciiu)
    return df_consolidado
