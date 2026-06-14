import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from data_loader import (
    cargar_operaciones,
    cargar_clientes,
    cargar_ciiu,
    cruzar_bases,
    obtener_lista_traders,
    filtrar_por_trader,
)

# -----------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# -----------------------------------------------------------------
st.set_page_config(
    page_title="Mesa de Clientes – Itaú",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------
# ESTILOS GLOBALES — Paleta Itaú (blanco + naranja)
# -----------------------------------------------------------------
st.markdown("""
<style>
    /* Fuentes y fondo */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', sans-serif;
        background-color: #FFFFFF;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #F0F0F0;
    }
    section[data-testid="stSidebar"] * {
        color: #1A1A1A !important;
    }
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #FF6900 !important;
    }

    /* Tarjetas de métricas */
    div[data-testid="metric-container"] {
        background-color: #FFFFFF;
        border: 1px solid #FFD9B8;
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 1px 4px rgba(255,105,0,0.06);
    }

    /* Tarjetas de priorización */
    .cliente-card {
        background: #FFFFFF;
        border: 1px solid #F0F0F0;
        border-left: 5px solid #FF6900;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 10px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .cliente-card.media {
        border-left-color: #FFA94D;
    }
    .cliente-card.baja {
        border-left-color: #BDBDBD;
    }
    .cliente-nombre {
        font-size: 16px;
        font-weight: 700;
        color: #1A1A1A;
    }
    .cliente-puntaje {
        font-size: 13px;
        color: #8A8A8A;
        margin-top: 2px;
    }
    .cliente-motivo {
        font-size: 13px;
        color: #5A5A5A;
        margin-top: 6px;
    }
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        margin-right: 6px;
        margin-top: 6px;
    }
    .badge-rojo { background: #FFE3D1; color: #D2480C; }
    .badge-naranja { background: #FFF1E0; color: #FF6900; }
    .badge-verde { background: #F0F0F0; color: #5A5A5A; }
    .badge-azul { background: #FFEDD9; color: #B85400; }

    /* Títulos de sección */
    .seccion-titulo {
        font-size: 18px;
        font-weight: 700;
        color: #1A1A1A;
        margin: 24px 0 12px 0;
        padding-bottom: 6px;
        border-bottom: 2px solid #FF6900;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------
# CARGA DE DATOS
# -----------------------------------------------------------------
@st.cache_data(ttl=3600)
def cargar_todo():
    df_ops = cargar_operaciones()
    df_clientes = cargar_clientes()
    df_ciiu = cargar_ciiu()

    # Convertir fecha de formato numérico Excel a fecha real
    if "Fecha" in df_ops.columns:
        df_ops["Fecha"] = pd.to_datetime(
            df_ops["Fecha"], origin="1899-12-30", unit="D", errors="coerce"
        )

    return cruzar_bases(df_ops, df_clientes, df_ciiu)

try:
    df = cargar_todo()
except Exception as e:
    st.error(f"Error al cargar los datos: {e}")
    st.stop()

COLUMNA_TRADER = "Cod_Cartera"

if COLUMNA_TRADER not in df.columns:
    st.error(f"No se encontró la columna '{COLUMNA_TRADER}' en los datos.")
    st.stop()

traders = obtener_lista_traders(df, COLUMNA_TRADER)

# -----------------------------------------------------------------
# FUNCIÓN DE PRIORIZACIÓN
# -----------------------------------------------------------------
def calcular_prioridad(df_trader: pd.DataFrame) -> pd.DataFrame:
    """
    Genera un puntaje 0–100 por cliente basado en:
    - 40% días sin operar (más días = más urgente)
    - 40% % operaciones en Mercado (más % = más oportunidad)
    - 20% volumen histórico (más monto = más impacto)
    """
    hoy = pd.Timestamp.now()
    resumen = []

    for nit, grupo in df_trader.groupby("NIT"):
        # Nombre del cliente (si existe)
        nombre = nit

        # Factor 1: días sin operar
        if "Fecha" in grupo.columns and grupo["Fecha"].notna().any():
            ultima_op = grupo["Fecha"].max()
            dias_sin_operar = (hoy - ultima_op).days
        else:
            dias_sin_operar = 999

        # Factor 2: % en Mercado
        if "Entidad" in grupo.columns:
            total_ops = len(grupo)
            ops_mercado = grupo["Entidad"].str.upper().eq("MERCADO").sum()
            pct_mercado = (ops_mercado / total_ops * 100) if total_ops > 0 else 0
        else:
            pct_mercado = 0

        # Factor 3: Volumen total
        if "Monto_Total_" in grupo.columns:
            monto_total = grupo["Monto_Total_"].sum()
        else:
            monto_total = 0

        resumen.append({
            "NIT": nit,
            "Nombre": nombre,
            "Dias_Sin_Operar": dias_sin_operar,
            "Pct_Mercado": round(pct_mercado, 1),
            "Monto_Total": monto_total,
            "N_Operaciones": len(grupo),
        })

    df_res = pd.DataFrame(resumen)
    if df_res.empty:
        return df_res

    # Normalizar cada factor entre 0 y 1
    def norm(serie):
        mn, mx = serie.min(), serie.max()
        return (serie - mn) / (mx - mn) if mx > mn else pd.Series([0.5] * len(serie), index=serie.index)

    df_res["score_dias"]   = norm(df_res["Dias_Sin_Operar"]) * 40
    df_res["score_mercado"] = norm(df_res["Pct_Mercado"])    * 40
    df_res["score_monto"]   = norm(df_res["Monto_Total"])    * 20
    df_res["Puntaje"] = (df_res["score_dias"] + df_res["score_mercado"] + df_res["score_monto"]).round(1)

    return df_res.sort_values("Puntaje", ascending=False).reset_index(drop=True)


def inferir_necesidades(row) -> list:
    """Infiere posibles necesidades del cliente basadas en sus métricas."""
    necesidades = []
    if row["Dias_Sin_Operar"] > 30:
        necesidades.append(("🔁 Reactivación", "badge-rojo"))
    if row["Pct_Mercado"] > 50:
        necesidades.append(("🏦 Retención – opera con competencia", "badge-naranja"))
    if row["Pct_Mercado"] < 30 and row["N_Operaciones"] > 3:
        necesidades.append(("⭐ Cliente fiel – ofrecer nuevos productos", "badge-verde"))
    if row["N_Operaciones"] == 1:
        necesidades.append(("🆕 Cliente nuevo – seguimiento inicial", "badge-azul"))
    if not necesidades:
        necesidades.append(("✅ Sin alertas urgentes", "badge-verde"))
    return necesidades


def prioridad_clase(puntaje: float) -> str:
    if puntaje >= 66:
        return "alta"
    elif puntaje >= 33:
        return " media"
    else:
        return " baja"


# -----------------------------------------------------------------
# SIDEBAR – SELECCIÓN DE TRADER
# -----------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🟠 Itaú Colombia")
    st.markdown("### Mesa de Clientes")
    st.markdown("---")
    st.markdown("**Busca tu cartera:**")

    busqueda = st.text_input("Buscar trader", placeholder="Ej: 4042", label_visibility="collapsed")

    if busqueda:
        traders_filtrados = [t for t in traders if busqueda.strip().lower() in str(t).lower()]
        if not traders_filtrados:
            st.warning("No se encontró ningún trader con ese texto.")
            traders_filtrados = traders
    else:
        traders_filtrados = traders

    trader_sel = st.radio(
        label="Selecciona tu cartera:",
        options=traders_filtrados,
        format_func=lambda t: f"Trader {t}",
    )
    st.markdown("---")
    st.caption("Los datos se actualizan automáticamente cuando cambian las fuentes.")

# -----------------------------------------------------------------
# CONTENIDO PRINCIPAL — contenido centrado, no a todo lo ancho
# -----------------------------------------------------------------
df_trader = filtrar_por_trader(df, trader_sel, COLUMNA_TRADER)
df_prio = calcular_prioridad(df_trader)

col_margen_izq, col_central, col_margen_der = st.columns([1, 6, 1])

with col_central:
    st.markdown(f"## Cartera del Trader {trader_sel}")
    st.caption(f"{df_trader['NIT'].nunique()} clientes · {len(df_trader)} operaciones registradas")

    # ── MÉTRICAS RÁPIDAS ──────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    monto_total = df_trader["Monto_Total_"].sum() if "Monto_Total_" in df_trader.columns else 0
    pct_mercado_global = (
        df_trader["Entidad"].str.upper().eq("MERCADO").sum() / len(df_trader) * 100
        if "Entidad" in df_trader.columns and len(df_trader) > 0 else 0
    )
    dias_prom = df_prio["Dias_Sin_Operar"].replace(999, pd.NA).mean() if not df_prio.empty else 0
    clientes_urgentes = (df_prio["Puntaje"] >= 66).sum() if not df_prio.empty else 0

    col1.metric("Clientes en cartera", df_trader["NIT"].nunique())
    col2.metric("Clientes urgentes hoy", int(clientes_urgentes), delta="🔴 requieren llamada")
    col3.metric("% operaciones en Mercado", f"{pct_mercado_global:.1f}%")
    col4.metric("Monto total histórico", f"{monto_total:,.0f}")

    st.markdown("---")

    # ── LISTA DE PRIORIZACIÓN ────────────────────────────────────────
    st.markdown('<div class="seccion-titulo">📋 Lista de priorización de hoy</div>', unsafe_allow_html=True)
    st.caption("Ordenada de mayor a menor urgencia. Naranja fuerte = llamada inmediata · Naranja claro = pronto · Gris = sin urgencia.")

    if df_prio.empty:
        st.info("No hay clientes en esta cartera.")
    else:
        for i, row in df_prio.iterrows():
            clase = prioridad_clase(row["Puntaje"])
            necesidades = inferir_necesidades(row)
            badges_html = " ".join([f'<span class="badge {b[1]}">{b[0]}</span>' for b in necesidades])

            motivos = []
            if row["Dias_Sin_Operar"] < 999:
                motivos.append(f"{int(row['Dias_Sin_Operar'])} días sin operar")
            if row["Pct_Mercado"] > 0:
                motivos.append(f"{row['Pct_Mercado']}% operaciones en Mercado")
            motivo_txt = " · ".join(motivos) if motivos else "Sin datos de fecha"

            st.markdown(f"""
            <div class="cliente-card{clase}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="cliente-nombre">#{i+1} · NIT {row['NIT']}</span>
                    <span style="font-size:20px; font-weight:800; color:#FF6900;">
                        {row['Puntaje']}<span style="font-size:12px; color:#8A8A8A;">/100</span>
                    </span>
                </div>
                <div class="cliente-puntaje">{motivo_txt}</div>
                <div>{badges_html}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ── TASAS DE PROBABILIDAD ────────────────────────────────────────
    st.markdown('<div class="seccion-titulo">📊 Tasas de probabilidad por cliente</div>', unsafe_allow_html=True)
    st.caption("Probabilidad estimada basada en el historial de operaciones de cada cliente.")

    if not df_prio.empty:
        df_tasas = df_prio[["NIT", "Pct_Mercado"]].copy()
        df_tasas["Pct_Entidad"] = 100 - df_tasas["Pct_Mercado"]
        df_tasas = df_tasas.rename(columns={
            "Pct_Mercado": "% Prob. compra en Mercado (otros bancos)",
            "Pct_Entidad": "% Prob. compra en Itaú",
        })

        fig_tasas = px.bar(
            df_tasas.melt(id_vars="NIT", var_name="Canal", value_name="Probabilidad (%)"),
            x="NIT",
            y="Probabilidad (%)",
            color="Canal",
            barmode="stack",
            color_discrete_map={
                "% Prob. compra en Mercado (otros bancos)": "#FFB266",
                "% Prob. compra en Itaú": "#FF6900",
            },
            labels={"NIT": "Cliente (NIT)"},
        )
        fig_tasas.update_layout(
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            height=320,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(fig_tasas, use_container_width=True, key=f"tasas_{trader_sel}")

    st.markdown("---")

    # ── POSIBLES NECESIDADES ─────────────────────────────────────────
    st.markdown('<div class="seccion-titulo">📌 Posibles necesidades por cliente</div>', unsafe_allow_html=True)

    if not df_prio.empty:
        for _, row in df_prio.iterrows():
            necesidades = inferir_necesidades(row)
            badges_html = " ".join([f'<span class="badge {b[1]}">{b[0]}</span>' for b in necesidades])
            st.markdown(
                f'<div style="margin-bottom:8px;"><strong>NIT {row["NIT"]}</strong>: {badges_html}</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── DETALLE DE OPERACIONES ───────────────────────────────────────
    with st.expander("📂 Ver detalle completo de operaciones"):
        st.dataframe(df_trader, use_container_width=True)
