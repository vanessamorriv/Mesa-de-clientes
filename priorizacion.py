import pandas as pd
import numpy as np

# ===================================================================
# 1. CONFIGURACIÓN DE PESOS Y UMBRALES
# ===================================================================

PESO_OPORTUNIDAD_MERCADO = 30
PESO_VALOR_ACTUAL_ITAU   = 30
PESO_DIAS_SIN_OPERAR     = 20
PESO_FIDELIZACION        = 20

UMBRAL_DIAS_REACTIVACION = 30
UMBRAL_OPERACIONES_FIEL  = 3


# ===================================================================
# 2. MÉTRICAS POR CLIENTE
# ===================================================================

def calcular_metricas_por_cliente(df_trader: pd.DataFrame) -> pd.DataFrame:
    hoy   = pd.Timestamp.now()
    filas = []

    for nit, grupo in df_trader.groupby('nit'):
        monto_entidad = grupo['monto_entidad'].sum() if 'monto_entidad' in grupo.columns else 0
        monto_total   = grupo['monto_total'].sum()   if 'monto_total'   in grupo.columns else 0
        monto_mercado = max(monto_total - monto_entidad, 0)

        if 'fecha' in grupo.columns and grupo['fecha'].notna().any():
            dias_sin_operar = (hoy - grupo['fecha'].max()).days
        else:
            dias_sin_operar = 999

        pct_mercado = (monto_mercado / monto_total * 100) if monto_total > 0 else 0

        # Datos estáticos del cliente
        segmento    = grupo['segmento'].iloc[0]    if 'segmento'    in grupo.columns else None
        subsegmento = grupo['subsegmento'].iloc[0] if 'subsegmento' in grupo.columns else None
        des_ciiu    = grupo['des_ciiu'].iloc[0]    if 'des_ciiu'    in grupo.columns else 'No disponible'

        filas.append({
            'nit':              nit,
            'monto_itau':       monto_entidad,
            'monto_mercado':    monto_mercado,
            'monto_total':      monto_total,
            'dias_sin_operar':  dias_sin_operar,
            'n_operaciones':    len(grupo),
            'pct_mercado':      round(pct_mercado, 1),
            'segmento':         segmento,
            'subsegmento':      subsegmento,
            'sector_economico': des_ciiu,
        })

    return pd.DataFrame(filas)


# ===================================================================
# 3. PUNTAJE DE PRIORIDAD HISTÓRICO
# ===================================================================

def _normalizar(serie: pd.Series) -> pd.Series:
    minimo, maximo = serie.min(), serie.max()
    if maximo == minimo:
        return pd.Series([0.5] * len(serie), index=serie.index)
    return (serie - minimo) / (maximo - minimo)


def calcular_puntaje_prioridad(df_metricas: pd.DataFrame) -> pd.DataFrame:
    if df_metricas.empty:
        return df_metricas

    df = df_metricas.copy()

    df['score_oportunidad']  = _normalizar(df['monto_mercado'])   * PESO_OPORTUNIDAD_MERCADO
    df['score_valor_actual'] = _normalizar(df['monto_itau'])      * PESO_VALOR_ACTUAL_ITAU
    df['score_dias']         = _normalizar(df['dias_sin_operar']) * PESO_DIAS_SIN_OPERAR
    df['score_fidelizacion'] = _normalizar(df['n_operaciones'])   * PESO_FIDELIZACION

    df['puntaje_historico'] = (
        df['score_oportunidad']
        + df['score_valor_actual']
        + df['score_dias']
        + df['score_fidelizacion']
    ).round(1)

    return df.sort_values('puntaje_historico', ascending=False).reset_index(drop=True)


# ===================================================================
# 4. SCORE COMBINADO (ML + HISTÓRICO)
# ===================================================================

def calcular_score_combinado(
    df_metricas: pd.DataFrame,
    df_predicciones: pd.DataFrame,
    peso_ml: float = 0.6,
    peso_historico: float = 0.4,
) -> pd.DataFrame:
    """
    Combina el score del modelo ML con el puntaje histórico.
    peso_ml + peso_historico debe sumar 1.0
    """
    if df_metricas.empty:
        return df_metricas

    df = df_metricas.copy()

    # Normalizar puntaje histórico a 0-1
    df['puntaje_historico_norm'] = _normalizar(df['puntaje_historico'])

    # Cruzar con predicciones ML
    if not df_predicciones.empty:
        pred_cols = df_predicciones[['nit', 'prob_opera_7d', 'producto_predicho', 'score_prioridad']].copy()
        pred_cols['nit'] = pred_cols['nit'].astype(str)
        df['nit'] = df['nit'].astype(str)
        df = df.merge(pred_cols, on='nit', how='left')
        df['prob_opera_7d']   = df['prob_opera_7d'].fillna(0)
        df['score_prioridad'] = df['score_prioridad'].fillna(0)
    else:
        df['prob_opera_7d']    = 0
        df['producto_predicho'] = None
        df['score_prioridad']  = 0

    # Score combinado
    df['score_combinado'] = (
        peso_ml * _normalizar(df['score_prioridad']) +
        peso_historico * df['puntaje_historico_norm']
    ).round(4)

    return df.sort_values('score_combinado', ascending=False).reset_index(drop=True)


# ===================================================================
# 5. RECOMENDACIÓN DE OFERTA
# ===================================================================

def calcular_recomendacion_oferta(df_trader: pd.DataFrame, nit) -> dict:
    ops_cliente = df_trader[df_trader['nit'] == str(nit)]

    resultado = {
        'producto_frecuente': None, 'pct_producto': 0,
        'lado_frecuente':     None, 'pct_lado':     0,
        'moneda_frecuente':   None, 'pct_moneda':   0,
    }

    if ops_cliente.empty:
        return resultado

    if 'producto' in ops_cliente.columns:
        conteo = ops_cliente['producto'].value_counts()
        if not conteo.empty:
            resultado['producto_frecuente'] = conteo.index[0]
            resultado['pct_producto']       = round(conteo.iloc[0] / len(ops_cliente) * 100, 0)

    if 'lado' in ops_cliente.columns:
        conteo = ops_cliente['lado'].value_counts()
        if not conteo.empty:
            resultado['lado_frecuente'] = conteo.index[0]
            resultado['pct_lado']       = round(conteo.iloc[0] / len(ops_cliente) * 100, 0)

    if 'moneda' in ops_cliente.columns:
        conteo = ops_cliente['moneda'].value_counts()
        if not conteo.empty:
            resultado['moneda_frecuente'] = conteo.index[0]
            resultado['pct_moneda']       = round(conteo.iloc[0] / len(ops_cliente) * 100, 0)

    return resultado


def texto_sugerencia_oferta(recomendacion: dict) -> str:
    producto    = recomendacion.get('producto_frecuente')
    lado        = recomendacion.get('lado_frecuente')
    moneda      = recomendacion.get('moneda_frecuente')
    pct_producto = recomendacion.get('pct_producto', 0)
    pct_lado     = recomendacion.get('pct_lado', 0)
    pct_moneda   = recomendacion.get('pct_moneda', 0)

    if not producto and not lado and not moneda:
        return 'Sin historial suficiente para sugerir una oferta.'

    partes = []
    if producto:
        partes.append(f"{producto} ({pct_producto:.0f}% de sus operaciones)")
    if lado:
        partes.append(f"{lado.title()} ({pct_lado:.0f}%)")
    if moneda:
        partes.append(f"Moneda: {moneda} ({pct_moneda:.0f}%)")

    return ' · '.join(partes)


# ===================================================================
# 6. NECESIDADES / ALERTAS
# ===================================================================

def inferir_necesidades(fila: pd.Series) -> list:
    necesidades = []

    if fila['dias_sin_operar'] > UMBRAL_DIAS_REACTIVACION:
        necesidades.append(('Reactivación – cliente inactivo', 'alerta'))

    if fila['pct_mercado'] > 50:
        necesidades.append(('Oportunidad – opera más con la competencia', 'oportunidad'))

    if fila['n_operaciones'] >= UMBRAL_OPERACIONES_FIEL and fila['pct_mercado'] < 30:
        necesidades.append(('Cliente fiel – posible cross-sell', 'fidelidad'))

    if fila['n_operaciones'] == 1:
        necesidades.append(('Cliente nuevo – seguimiento inicial', 'nuevo'))

    if not necesidades:
        necesidades.append(('Sin alertas urgentes', 'neutral'))

    return necesidades


# ===================================================================
# 7. RANKINGS
# ===================================================================

def ranking_clientes_por_moneda(df_trader: pd.DataFrame, monedas: list, top_n: int = 5) -> pd.DataFrame:
    cols_vacias = ['nit', 'moneda', 'n_operaciones']
    if df_trader.empty or 'moneda' not in df_trader.columns:
        return pd.DataFrame(columns=cols_vacias)

    filtrado = df_trader[df_trader['moneda'].isin(monedas)]
    if filtrado.empty:
        return pd.DataFrame(columns=cols_vacias)

    return (
        filtrado.groupby(['nit', 'moneda'])
        .size()
        .reset_index(name='n_operaciones')
        .sort_values('n_operaciones', ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


def ranking_clientes_por_producto(df_trader: pd.DataFrame, productos: list, top_n: int = 5) -> pd.DataFrame:
    cols_vacias = ['nit', 'producto', 'n_operaciones']
    if df_trader.empty or 'producto' not in df_trader.columns:
        return pd.DataFrame(columns=cols_vacias)

    filtrado = df_trader[df_trader['producto'].isin(productos)]
    if filtrado.empty:
        return pd.DataFrame(columns=cols_vacias)

    return (
        filtrado.groupby(['nit', 'producto'])
        .size()
        .reset_index(name='n_operaciones')
        .sort_values('n_operaciones', ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


# ===================================================================
# 8. FUNCIÓN PRINCIPAL
# ===================================================================

def generar_priorizacion(
    df_trader: pd.DataFrame,
    df_predicciones: pd.DataFrame = None,
    modo: str = 'historico',  # 'historico', 'ml', 'combinado'
) -> pd.DataFrame:
    """
    modo='historico'  → ordena por puntaje histórico (montos, días, frecuencia)
    modo='ml'         → ordena por score_prioridad del modelo
    modo='combinado'  → combina ambos (60% ML + 40% histórico)
    """
    if df_trader.empty:
        return pd.DataFrame()

    df_metricas = calcular_metricas_por_cliente(df_trader)
    df_puntaje  = calcular_puntaje_prioridad(df_metricas)

    if modo == 'ml' and df_predicciones is not None and not df_predicciones.empty:
        pred_cols = df_predicciones[['nit', 'prob_opera_7d', 'producto_predicho', 'score_prioridad']].copy()
        pred_cols['nit'] = pred_cols['nit'].astype(str)
        df_puntaje['nit'] = df_puntaje['nit'].astype(str)
        df_puntaje = df_puntaje.merge(pred_cols, on='nit', how='left')
        df_puntaje = df_puntaje.sort_values('score_prioridad', ascending=False).reset_index(drop=True)

    elif modo == 'combinado' and df_predicciones is not None:
        df_puntaje = calcular_score_combinado(df_puntaje, df_predicciones)

    else:
        # modo historico — agregar columnas ML vacías para consistencia
        df_puntaje['prob_opera_7d']    = None
        df_puntaje['producto_predicho'] = None
        df_puntaje['score_prioridad']  = None

    # Agregar recomendación, necesidades para cada cliente
    sugerencias      = []
    necesidades_list = []

    for _, fila in df_puntaje.iterrows():
        rec = calcular_recomendacion_oferta(df_trader, fila['nit'])
        sugerencias.append(texto_sugerencia_oferta(rec))
        necesidades_list.append(inferir_necesidades(fila))

    df_puntaje['sugerencia_oferta'] = sugerencias
    df_puntaje['necesidades']       = necesidades_list

    return df_puntaje
