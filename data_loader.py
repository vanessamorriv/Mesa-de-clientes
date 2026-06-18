import pandas as pd
import os
from supabase import create_client

# ── Conexión Supabase ─────────────────────────────────────────────
SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_SERVICE_KEY']
supabase     = create_client(SUPABASE_URL, SUPABASE_KEY)


# ── Conexión ──────────────────────────────────────────────────────
def get_supabase():
    return supabase


# ── Cargar tablas base ────────────────────────────────────────────
def cargar_operaciones() -> pd.DataFrame:
    rows = []
    chunk = 1000
    offset = 0
    while True:
        res = supabase.table('operaciones').select('*').range(offset, offset + chunk - 1).execute()
        if not res.data:
            break
        rows.extend(res.data)
        offset += chunk
    df = pd.DataFrame(rows)
    if not df.empty and 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    return df


def cargar_clientes() -> pd.DataFrame:
    rows = []
    chunk = 1000
    offset = 0
    while True:
        res = supabase.table('clientes').select('*').range(offset, offset + chunk - 1).execute()
        if not res.data:
            break
        rows.extend(res.data)
        offset += chunk
    return pd.DataFrame(rows)


def cargar_ciiu() -> pd.DataFrame:
    res = supabase.table('ciiu').select('*').execute()
    return pd.DataFrame(res.data)


def cargar_predicciones(fecha: str = None) -> pd.DataFrame:
    """
    Carga predicciones desde Supabase.
    Si se pasa fecha (formato 'YYYY-MM-DD'), filtra por esa fecha.
    Si no, trae la fecha más reciente disponible.
    """
    if fecha:
        res = supabase.table('predicciones').select('*').eq('fecha_prediccion', fecha).execute()
        df  = pd.DataFrame(res.data)
    else:
        # Obtener fecha más reciente
        res_fecha = (
            supabase.table('predicciones')
            .select('fecha_prediccion')
            .order('fecha_prediccion', desc=True)
            .limit(1)
            .execute()
        )
        if not res_fecha.data:
            return pd.DataFrame()
        fecha_max = res_fecha.data[0]['fecha_prediccion']

        rows  = []
        chunk = 1000
        offset = 0
        while True:
            res = (
                supabase.table('predicciones')
                .select('*')
                .eq('fecha_prediccion', fecha_max)
                .range(offset, offset + chunk - 1)
                .execute()
            )
            if not res.data:
                break
            rows.extend(res.data)
            offset += chunk
        df = pd.DataFrame(rows)

    if not df.empty and 'fecha_prediccion' in df.columns:
        df['fecha_prediccion'] = pd.to_datetime(df['fecha_prediccion'], errors='coerce')
    return df


def cargar_vista_completa() -> pd.DataFrame:
    rows = []
    chunk = 1000
    offset = 0
    while True:
        res = supabase.table('vista_operaciones_completa') \
                      .select('*') \
                      .range(offset, offset + chunk - 1) \
                      .execute()
        if not res.data:
            break
        rows.extend(res.data)
        offset += chunk
    df = pd.DataFrame(rows)
    if not df.empty and 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    return df


# ── Asignación temporal de traders ───────────────────────────────
def asignar_traders(df: pd.DataFrame, n_traders: int = 20, seed: int = 42) -> pd.DataFrame:
    """
    Asigna un trader a cada NIT de forma aleatoria y reproducible.
    Cuando llegue la data real de asignación, reemplazar esta función.
    """
    import numpy as np
    np.random.seed(seed)
    nits_unicos = df['nit'].dropna().unique()
    asignacion  = {
        nit: f"Trader_{str(i+1).zfill(2)}"
        for i, (nit, _) in enumerate(
            zip(nits_unicos, np.random.randint(1, n_traders + 1, size=len(nits_unicos)))
        )
    }
    # Asignación real aleatoria
    traders_asignados = [f"Trader_{str(x).zfill(2)}" for x in np.random.randint(1, n_traders + 1, size=len(nits_unicos))]
    asignacion = dict(zip(nits_unicos, traders_asignados))
    df['trader'] = df['nit'].map(asignacion)
    return df


def obtener_lista_traders(df: pd.DataFrame) -> list:
    if 'trader' not in df.columns:
        return []
    return sorted(df['trader'].dropna().unique().tolist())


def filtrar_por_trader(df: pd.DataFrame, trader_id: str) -> pd.DataFrame:
    if 'trader' not in df.columns:
        return df
    return df[df['trader'] == trader_id]


# ── Subir archivos desde la app (módulo de cargue) ───────────────
def subir_operaciones(df_nuevo: pd.DataFrame) -> dict:
    """
    Recibe un DataFrame de operaciones nuevas y hace upsert a Supabase.
    Devuelve un dict con el resultado.
    """
    df = df_nuevo.copy()
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={
        'Fecha':         'fecha',
        'TipoIDC':       'tipo_idc',
        'NIT':           'nit',
        'Producto':      'producto',
        'Lado':          'lado',
        'Entidad':       'entidad',
        'Moneda':        'moneda',
        'Monto_Total_':  'monto_total',
        'Monto_Entidad': 'monto_entidad',
        'Monto_Mercado': 'monto_mercado',
    })

    if pd.api.types.is_numeric_dtype(df['fecha']):
        df['fecha'] = pd.to_datetime(df['fecha'], origin='1899-12-30', unit='D', errors='coerce')
    else:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')

    df['fecha'] = df['fecha'].dt.strftime('%Y-%m-%d')
    df['nit']   = df['nit'].astype(str).str.strip()
    df = df.dropna(subset=['fecha', 'nit'])
    df = df.where(pd.notna(df), None)

    data = df.to_dict('records')
    lotes = 0
    for i in range(0, len(data), 500):
        supabase.table('operaciones').upsert(
            data[i:i+500],
            on_conflict='fecha,nit,producto,lado,entidad,moneda,monto_total'
        ).execute()
        lotes += 1

    return {'registros': len(data), 'lotes': lotes}


def subir_clientes(df_nuevo: pd.DataFrame) -> dict:
    df = df_nuevo.copy()
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={
        'ID':          'id',
        'TipoID':      'tipo_id',
        'TipoIDC':     'tipo_idc',
        'Segmento':    'segmento',
        'Subsegmento': 'subsegmento',
        'Cod_Cartera': 'cod_cartera',
        'CIIU_BUC':    'ciiu_buc',
        'IDE':         'ide',
    })
    df['id'] = df['id'].astype(str).str.strip()
    df = df.dropna(subset=['id'])
    df = df.where(pd.notna(df), None)

    data = df.to_dict('records')
    for i in range(0, len(data), 500):
        supabase.table('clientes').upsert(data[i:i+500], on_conflict='id').execute()

    return {'registros': len(data)}


def subir_ciiu(df_nuevo: pd.DataFrame) -> dict:
    df = df_nuevo.copy()
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={
        'COD_ACT_CIIU_NOCLI': 'cod_act_ciiu_nocli',
        'DES_CIIU':           'des_ciiu',
    })
    df['cod_act_ciiu_nocli'] = df['cod_act_ciiu_nocli'].astype(str).str.strip()
    df = df.dropna(subset=['cod_act_ciiu_nocli'])
    df = df.where(pd.notna(df), None)

    data = df.to_dict('records')
    for i in range(0, len(data), 500):
        supabase.table('ciiu').upsert(
            data[i:i+500], on_conflict='cod_act_ciiu_nocli'
        ).execute()

    return {'registros': len(data)}
