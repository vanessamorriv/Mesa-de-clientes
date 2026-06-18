import streamlit as st
import pandas as pd
import plotly.express as px

from data_loader import (
    cargar_operaciones,
    cargar_clientes,
    cargar_ciiu,
    cargar_predicciones,
    cruzar_bases,
    asignar_traders,
    obtener_lista_traders,
    filtrar_por_trader,
)
from priorizacion import (
    generar_priorizacion,
    calcular_metricas_por_cliente,
    calcular_recomendacion_oferta,
    texto_sugerencia_oferta,
    ranking_clientes_por_moneda,
    ranking_clientes_por_producto,
)

# ── Paleta ────────────────────────────────────────────────────────
COLOR_NARANJA       = "#FF6900"
COLOR_NARANJA_CLARO = "#FFB266"
COLOR_NARANJA_PALE  = "#FFF3EA"
COLOR_GRIS          = "#6B7280"
COLOR_GRIS_CLARO    = "#F3F4F6"
COLOR_BORDE         = "#E5E7EB"

BADGE_CLASES = {
    "alerta":      "badge-alerta",
    "oportunidad": "badge-oportunidad",
    "fidelidad":   "badge-fidelidad",
    "nuevo":       "badge-nuevo",
    "neutral":     "badge-neutral",
}

# ── CSS Global ────────────────────────────────────────────────────
st.markdown(f"""
<style>
  /* ── Base ── */
  html, body, [class*="css"] {{ font-size: 15px; }}

  /* ── Topbar ── */
  .topbar-logo {{ font-size: 18px; font-weight: 800; color: {COLOR_NARANJA}; }}
  .topbar-sep  {{ color: {COLOR_BORDE}; font-size: 22px; }}
  .topbar-app  {{ font-size: 16px; font-weight: 600; color: #111827; }}

  /* ── Section label ── */
  .section-label {{
    font-size: 13px; font-weight: 700; color: {COLOR_GRIS};
    text-transform: uppercase; letter-spacing: .6px;
    padding: 10px 0 8px 0;
    border-bottom: 3px solid {COLOR_NARANJA};
    margin-bottom: 16px;
  }}

  /* ── Info box ── */
  .caja-ayuda {{
    background: {COLOR_NARANJA_PALE}; border: 1px solid #FFCFA0;
    border-radius: 8px; padding: 10px 14px;
    font-size: 13px; color: #4B3A2A;
    margin: 6px 0 16px 0; line-height: 1.5;
  }}

  /* ── TARJETA ── */
  .card {{
    background: #FFFFFF;
    border: 1px solid {COLOR_BORDE};
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 14px;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
    transition: box-shadow .15s;
  }}
  .card:hover {{ box-shadow: 0 4px 14px rgba(255,105,0,.12); }}

  /* Cabecera tarjeta */
  .card-head {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 12px;
    padding-bottom: 10px;
    border-bottom: 1px solid {COLOR_GRIS_CLARO};
  }}
  .card-nit {{
    font-size: 16px; font-weight: 700; color: #111827;
  }}
  .card-rank {{
    font-size: 13px; font-weight: 500; color: {COLOR_GRIS};
    margin-right: 6px;
  }}
  .card-score {{
    background: {COLOR_NARANJA};
    color: #fff;
    font-size: 15px; font-weight: 700;
    border-radius: 20px;
    padding: 3px 14px;
    white-space: nowrap;
  }}
  .card-score span {{ font-size: 11px; font-weight: 400; opacity: .85; margin-left: 2px; }}

  /* Filas de datos dentro de tarjeta */
  .card-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px 20px;
    margin-bottom: 12px;
  }}
  .card-item {{
    display: flex; flex-direction: column; gap: 1px;
  }}
  .card-item-label {{
    font-size: 11px; color: {COLOR_GRIS}; text-transform: uppercase; letter-spacing: .4px;
  }}
  .card-item-value {{
    font-size: 14px; font-weight: 600; color: #111827;
  }}

  /* Sector (ancho completo) */
  .card-sector {{
    font-size: 12px; color: {COLOR_GRIS};
    margin-bottom: 10px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}

  /* Oferta */
  .card-offer {{
    background: {COLOR_NARANJA_PALE};
    border-radius: 8px;
    padding: 9px 13px;
    font-size: 13px; color: #4B3A2A;
    margin-bottom: 10px;
    line-height: 1.5;
  }}

  /* Badges */
  .badges {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .badge {{
    font-size: 11px; font-weight: 600;
    border-radius: 20px; padding: 3px 11px;
    white-space: nowrap;
  }}
  .badge-alerta      {{ background:#FEE2E2; color:#991B1B; }}
  .badge-oportunidad {{ background:#FEF3C7; color:#92400E; }}
  .badge-fidelidad   {{ background:#D1FAE5; color:#065F46; }}
  .badge-nuevo       {{ background:#DBEAFE; color:#1E40AF; }}
  .badge-neutral     {{ background:{COLOR_GRIS_CLARO}; color:{COLOR_GRIS}; }}

  /* Scroll lista */
  .prio-scroll {{ max-height: 72vh; overflow-y: auto; padding-right: 4px; }}

  /* ── FICHA CLIENTE ── */
  .ficha-wrap {{
    background: #FFFFFF;
    border: 1px solid {COLOR_BORDE};
    border-radius: 14px;
    padding: 24px 28px;
    box-shadow: 0 2px 8px rgba(0,0,0,.07);
    margin-bottom: 20px;
  }}
  .ficha-header {{
    display: flex; justify-content: space-between; align-items: flex-start;
    margin-bottom: 20px; padding-bottom: 16px;
    border-bottom: 2px solid {COLOR_NARANJA};
  }}
  .ficha-nit {{
    font-size: 22px; font-weight: 800; color: #111827;
  }}
  .ficha-sub {{
    font-size: 13px; color: {COLOR_GRIS}; margin-top: 2px;
  }}
  .ficha-ml-pill {{
    background: {COLOR_NARANJA};
    color: #fff;
    border-radius: 24px;
    padding: 6px 18px;
    text-align: center;
  }}
  .ficha-ml-prob {{
    font-size: 22px; font-weight: 800; line-height: 1;
  }}
  .ficha-ml-label {{
    font-size: 11px; opacity: .85;
  }}
  .ficha-stats {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 18px;
  }}
  .ficha-stat {{
    background: {COLOR_GRIS_CLARO};
    border-radius: 10px;
    padding: 14px 16px;
    text-align: center;
  }}
  .ficha-stat-val {{
    font-size: 20px; font-weight: 800; color: {COLOR_NARANJA};
  }}
  .ficha-stat-lbl {{
    font-size: 11px; color: {COLOR_GRIS}; margin-top: 3px;
    text-transform: uppercase; letter-spacing: .4px;
  }}
  .ficha-offer {{
    background: {COLOR_NARANJA_PALE};
    border-radius: 10px; padding: 12px 16px;
    font-size: 13px; color: #4B3A2A; line-height: 1.6;
  }}
</style>
""", unsafe_allow_html=True)


# ── Carga de datos ────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def cargar_todo():
    df_ops      = cargar_operaciones()
    df_clientes = cargar_clientes()
    df_ciiu     = cargar_ciiu()
    df          = cruzar_bases(df_ops, df_clientes, df_ciiu)
    df          = asignar_traders(df)
    return df

@st.cache_data(ttl=3600)
def cargar_pred():
    return cargar_predicciones()

try:
    df   = cargar_todo()
    pred = cargar_pred()
except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.stop()

lista_traders = obtener_lista_traders(df)


# ── Topbar ────────────────────────────────────────────────────────
col_logo, col_sep, col_app, col_spacer, col_sel = st.columns([1.2, 0.1, 1.8, 4, 1.8])
with col_logo:
    st.markdown('<div class="topbar-logo" style="padding-top:6px">🟠 Itaú Colombia</div>', unsafe_allow_html=True)
with col_sep:
    st.markdown('<div class="topbar-sep" style="padding-top:6px">|</div>', unsafe_allow_html=True)
with col_app:
    st.markdown('<div class="topbar-app" style="padding-top:9px">Mesa de Clientes</div>', unsafe_allow_html=True)
with col_sel:
    trader_seleccionado = st.selectbox(
        label="Cartera",
        options=lista_traders,
        label_visibility="collapsed",
        key="trader_selector",
    )

st.markdown("<hr style='margin:4px 0 16px 0; border:none; border-top:1px solid #E5E7EB'>", unsafe_allow_html=True)


# ── Datos del trader ──────────────────────────────────────────────
df_trader   = filtrar_por_trader(df, trader_seleccionado)
nits_trader = df_trader['nit'].unique().tolist()
pred_trader = pred[pred['nit'].astype(str).isin([str(n) for n in nits_trader])] if not pred.empty else pd.DataFrame()


# ── KPIs ─────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("Clientes en cartera",     df_trader['nit'].nunique())
m2.metric("Predicciones ML",         len(pred_trader))
m3.metric("Monto Itaú",  f"${df_trader['monto_entidad'].sum():,.0f}" if 'monto_entidad' in df_trader.columns else "—")
m4.metric("Oportunidad mercado", f"${df_trader['monto_mercado'].sum():,.0f}"  if 'monto_mercado' in df_trader.columns else "—")

st.markdown("<div class='caja-ayuda'>ℹ️ <b>Monto Itaú</b>: operaciones cerradas con Itaú. &nbsp;|&nbsp; <b>Oportunidad mercado</b>: monto operado con la competencia — negocio capturable.</div>", unsafe_allow_html=True)


# ── Helper: construir tarjeta ─────────────────────────────────────
def _tarjeta(pos, fila, modo="hist"):
    """Devuelve el HTML de una tarjeta de cliente."""
    texto_dias = "Sin registro" if fila['dias_sin_operar'] >= 999 else f"{int(fila['dias_sin_operar'])} días sin operar"
    sector     = str(fila.get('sector_economico') or 'Sector no disponible')[:55]
    badges_html = "".join(
        f'<span class="badge {BADGE_CLASES.get(tipo, "badge-neutral")}">{texto}</span>'
        for texto, tipo in fila['necesidades']
    )

    # Score / prob según modo
    if modo == "ml":
        prob  = fila.get('prob_opera_7d', 0) or 0
        score_html = f'<span class="card-score">{prob:.0%}<span> prob.</span></span>'
    elif modo == "comb":
        sc    = fila.get('score_combinado', 0) or 0
        score_html = f'<span class="card-score">{sc:.2f}<span> score</span></span>'
    else:
        score_html = f'<span class="card-score">{fila["puntaje_historico"]}<span>/100</span></span>'

    # Fila de datos central (varía por modo)
    if modo == "ml":
        prod = str(fila.get('producto_predicho') or '—')
        if prod.lower() in ('nan', 'none', ''):
            prod = '—'
        datos_html = f"""
        <div class="card-grid">
          <div class="card-item">
            <span class="card-item-label">Producto predicho</span>
            <span class="card-item-value">🎯 {prod}</span>
          </div>
          <div class="card-item">
            <span class="card-item-label">Última operación</span>
            <span class="card-item-value">⏱️ {texto_dias}</span>
          </div>
          <div class="card-item">
            <span class="card-item-label">N° operaciones</span>
            <span class="card-item-value">🔄 {int(fila['n_operaciones'])}</span>
          </div>
        </div>"""
    elif modo == "comb":
        prob = fila.get('prob_opera_7d', 0) or 0
        prod = str(fila.get('producto_predicho') or '—')
        if prod.lower() in ('nan', 'none', ''):
            prod = '—'
        datos_html = f"""
        <div class="card-grid">
          <div class="card-item">
            <span class="card-item-label">Prob. ML</span>
            <span class="card-item-value">🤖 {prob:.0%}</span>
          </div>
          <div class="card-item">
            <span class="card-item-label">Producto predicho</span>
            <span class="card-item-value">🎯 {prod}</span>
          </div>
          <div class="card-item">
            <span class="card-item-label">Monto Itaú</span>
            <span class="card-item-value">💰 {fila['monto_itau']:,.0f}</span>
          </div>
          <div class="card-item">
            <span class="card-item-label">Oportunidad mercado</span>
            <span class="card-item-value">📈 {fila['monto_mercado']:,.0f}</span>
          </div>
        </div>"""
    else:
        datos_html = f"""
        <div class="card-grid">
          <div class="card-item">
            <span class="card-item-label">Monto Itaú</span>
            <span class="card-item-value">💰 {fila['monto_itau']:,.0f}</span>
          </div>
          <div class="card-item">
            <span class="card-item-label">Oportunidad mercado</span>
            <span class="card-item-value">📈 {fila['monto_mercado']:,.0f}</span>
          </div>
          <div class="card-item">
            <span class="card-item-label">Última operación</span>
            <span class="card-item-value">⏱️ {texto_dias}</span>
          </div>
          <div class="card-item">
            <span class="card-item-label">N° operaciones</span>
            <span class="card-item-value">🔄 {int(fila['n_operaciones'])}</span>
          </div>
        </div>"""

    return f"""
    <div class="card">
      <div class="card-head">
        <div>
          <span class="card-rank">#{pos+1}</span>
          <span class="card-nit">NIT {fila['nit']}</span>
        </div>
        {score_html}
      </div>
      <div class="card-sector">🏢 {sector}</div>
      {datos_html}
      <div class="card-offer">
        📞 <b>Patrones históricos:</b> {fila['sugerencia_oferta']}
      </div>
      <div class="badges">{badges_html}</div>
    </div>"""


# ── Tabs ──────────────────────────────────────────────────────────
tab_ml, tab_hist, tab_comb, tab_dash, tab_buscar = st.tabs([
    "🤖 ML",
    "📋 Histórico",
    "⚡ Combinado",
    "📊 Dashboard",
    "🔍 Buscar Cliente",
])


# ══════════════════════════════════════════════════════════════════
# TAB 1 · Predicciones ML
# ══════════════════════════════════════════════════════════════════
with tab_ml:
    st.markdown('<div class="section-label">🤖 Clientes con mayor probabilidad de operar (próximos 7 días)</div>', unsafe_allow_html=True)
    st.markdown('<div class="caja-ayuda">Ordenado por el <b>modelo ML</b>. Predice quién va a operar y qué producto. No considera historial de montos — mira hacia adelante.</div>', unsafe_allow_html=True)

    if pred_trader.empty:
        st.info("No hay predicciones disponibles para este trader.")
    else:
        df_ml = generar_priorizacion(df_trader, pred_trader, modo='ml')
        col_lista, col_panel = st.columns([3, 2], gap="large")

        with col_lista:
            html = "".join(_tarjeta(pos, fila, modo="ml") for pos, fila in df_ml.iterrows())
            st.markdown(f'<div class="prio-scroll">{html}</div>', unsafe_allow_html=True)

        with col_panel:
            st.markdown("##### Distribución de productos predichos")
            prod_counts = pred_trader['producto_predicho'].dropna().value_counts().reset_index()
            prod_counts.columns = ['Producto', 'Conteo']
            if not prod_counts.empty:
                fig = px.pie(prod_counts, names='Producto', values='Conteo', hole=0.5,
                             color_discrete_sequence=[COLOR_NARANJA, COLOR_NARANJA_CLARO, COLOR_GRIS])
                fig.update_layout(height=260, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='#FFFFFF')
                st.plotly_chart(fig, use_container_width=True, key=f"pie_ml_{trader_seleccionado}")

            st.markdown("##### Top 10 por probabilidad")
            if not df_ml.empty:
                top10 = df_ml[['nit','prob_opera_7d','producto_predicho']].head(10).copy()
                top10['producto_predicho'] = top10['producto_predicho'].apply(
                    lambda x: '—' if pd.isna(x) or str(x).lower() in ('nan','none','') else x
                )
                top10.columns = ['NIT', 'Prob.', 'Producto']
                top10['Prob.'] = top10['Prob.'].apply(lambda x: f"{x:.1%}" if x else "—")
                st.dataframe(top10, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════
# TAB 2 · Priorización Histórica
# ══════════════════════════════════════════════════════════════════
with tab_hist:
    st.markdown('<div class="section-label">📋 A quién llamar hoy — basado en historial</div>', unsafe_allow_html=True)
    st.markdown('<div class="caja-ayuda">Ordenado por <b>puntaje histórico</b>: combina monto con Itaú, oportunidad en mercado, días sin operar y frecuencia.</div>', unsafe_allow_html=True)

    df_hist = generar_priorizacion(df_trader, modo='historico')
    col_lista, col_panel = st.columns([3, 2], gap="large")

    with col_lista:
        if df_hist.empty:
            st.info("Esta cartera no tiene clientes registrados.")
        else:
            html = "".join(_tarjeta(pos, fila, modo="hist") for pos, fila in df_hist.iterrows())
            st.markdown(f'<div class="prio-scroll">{html}</div>', unsafe_allow_html=True)

    with col_panel:
        top_n = st.slider("Top N a mostrar", 3, 15, 5, key=f"slider_hist_{trader_seleccionado}")

        st.markdown("##### 💱 Top clientes por moneda")
        monedas_disp = sorted(df_trader['moneda'].dropna().unique().tolist()) if 'moneda' in df_trader.columns else []
        monedas_obj  = [m for m in monedas_disp if m in ('USD/COP', 'EUR/COP')] or monedas_disp
        rank_moneda  = ranking_clientes_por_moneda(df_trader, monedas_obj, top_n)
        if not rank_moneda.empty:
            st.dataframe(rank_moneda, use_container_width=True, hide_index=True)

        st.markdown("##### 📦 Top clientes por producto")
        prods_disp = sorted(df_trader['producto'].dropna().unique().tolist()) if 'producto' in df_trader.columns else []
        prods_obj  = [p for p in prods_disp if p.strip().upper() in ('SPOT', 'FORWARD')] or prods_disp
        rank_prod  = ranking_clientes_por_producto(df_trader, prods_obj, top_n)
        if not rank_prod.empty:
            st.dataframe(rank_prod, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════
# TAB 3 · Combinado
# ══════════════════════════════════════════════════════════════════
with tab_comb:
    st.markdown('<div class="section-label">⚡ Priorización combinada — ML + Histórico</div>', unsafe_allow_html=True)
    st.markdown('<div class="caja-ayuda">Ajusta los pesos para combinar el score ML (quién va a operar) con el puntaje histórico (valor del cliente).</div>', unsafe_allow_html=True)

    col_w1, col_w2, _ = st.columns([1, 1, 2])
    with col_w1:
        peso_ml = st.slider("Peso ML (%)", 0, 100, 60, step=10, key=f"peso_ml_{trader_seleccionado}") / 100
    with col_w2:
        st.metric("Peso Histórico", f"{(1-peso_ml):.0%}")

    df_comb = generar_priorizacion(df_trader, pred_trader, modo='combinado')
    col_lista, col_panel = st.columns([3, 2], gap="large")

    with col_lista:
        if df_comb.empty:
            st.info("No hay datos suficientes.")
        else:
            html = "".join(_tarjeta(pos, fila, modo="comb") for pos, fila in df_comb.iterrows())
            st.markdown(f'<div class="prio-scroll">{html}</div>', unsafe_allow_html=True)

    with col_panel:
        if not df_comb.empty:
            st.markdown("##### Score combinado vs Probabilidad ML")
            fig = px.scatter(
                df_comb.head(50),
                x='prob_opera_7d', y='puntaje_historico',
                size='score_combinado', hover_data=['nit'],
                color_discrete_sequence=[COLOR_NARANJA],
                labels={'prob_opera_7d': 'Prob. ML', 'puntaje_historico': 'Puntaje Histórico'},
            )
            fig.update_layout(height=320, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='#FFFFFF')
            st.plotly_chart(fig, use_container_width=True, key=f"scatter_comb_{trader_seleccionado}")


# ══════════════════════════════════════════════════════════════════
# TAB 4 · Dashboard con filtros de fecha
# ══════════════════════════════════════════════════════════════════
with tab_dash:
    st.markdown('<div class="section-label">📊 Dashboard de la cartera</div>', unsafe_allow_html=True)

    # ── Filtros ──
    if 'fecha' in df_trader.columns and df_trader['fecha'].notna().any():
        fecha_min = df_trader['fecha'].min().date()
        fecha_max = df_trader['fecha'].max().date()

        fc1, fc2, fc3 = st.columns([1, 1, 2])
        with fc1:
            desde = st.date_input("Desde", value=fecha_min, min_value=fecha_min, max_value=fecha_max, key="dash_desde")
        with fc2:
            hasta = st.date_input("Hasta", value=fecha_max, min_value=fecha_min, max_value=fecha_max, key="dash_hasta")
        with fc3:
            prods_filtro = df_trader['producto'].dropna().unique().tolist() if 'producto' in df_trader.columns else []
            prod_sel = st.multiselect("Producto", options=sorted(prods_filtro), default=[], key="dash_prod",
                                      placeholder="Todos los productos")

        # Aplicar filtros
        mask = (df_trader['fecha'].dt.date >= desde) & (df_trader['fecha'].dt.date <= hasta)
        df_dash = df_trader[mask].copy()
        if prod_sel:
            df_dash = df_dash[df_dash['producto'].isin(prod_sel)]

        st.markdown(f"<div class='caja-ayuda'>📅 Mostrando <b>{len(df_dash):,}</b> operaciones entre <b>{desde}</b> y <b>{hasta}</b>.</div>", unsafe_allow_html=True)
    else:
        df_dash = df_trader.copy()

    st.markdown("---")

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("##### Operaciones por producto (por cliente)")
        if 'producto' in df_dash.columns and not df_dash.empty:
            prod_top = (
                df_dash.groupby(['nit', 'producto']).size().reset_index(name='conteo')
                .sort_values(['nit','conteo'], ascending=[True, False])
                .groupby('nit').first().reset_index()
            )
            fig = px.bar(prod_top, x='nit', y='conteo', color='producto',
                         color_discrete_sequence=[COLOR_NARANJA, COLOR_NARANJA_CLARO, COLOR_GRIS])
            fig.update_layout(height=280, margin=dict(l=4,r=4,t=10,b=4),
                               paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF',
                               legend_title_text='Producto')
            fig.update_xaxes(type='category', tickfont=dict(size=8), title='NIT')
            st.plotly_chart(fig, use_container_width=True, key=f"bar_prod_{trader_seleccionado}")

    with col_g2:
        st.markdown("##### Distribución por moneda")
        if 'moneda' in df_dash.columns and not df_dash.empty:
            mc = df_dash['moneda'].value_counts().reset_index()
            mc.columns = ['Moneda', 'Conteo']
            fig = px.pie(mc, names='Moneda', values='Conteo', hole=0.5,
                         color_discrete_sequence=[COLOR_NARANJA, COLOR_NARANJA_CLARO, COLOR_GRIS])
            fig.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='#FFFFFF')
            st.plotly_chart(fig, use_container_width=True, key=f"pie_moneda_{trader_seleccionado}")

    col_g3, col_g4 = st.columns(2)

    with col_g3:
        st.markdown("##### Operaciones por mes")
        if 'fecha' in df_dash.columns and not df_dash.empty:
            df_mes = df_dash.copy()
            df_mes['mes'] = df_mes['fecha'].dt.to_period('M').astype(str)
            ops_mes = df_mes.groupby('mes').size().reset_index(name='Operaciones')
            fig = px.line(ops_mes, x='mes', y='Operaciones',
                          markers=True, color_discrete_sequence=[COLOR_NARANJA])
            fig.update_layout(height=240, margin=dict(l=4,r=4,t=10,b=4),
                               paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF')
            fig.update_xaxes(tickfont=dict(size=9), title='Mes')
            st.plotly_chart(fig, use_container_width=True, key=f"line_mes_{trader_seleccionado}")

    with col_g4:
        st.markdown("##### Monto total por producto")
        if 'producto' in df_dash.columns and 'monto_total' in df_dash.columns and not df_dash.empty:
            mp = df_dash.groupby('producto')['monto_total'].sum().reset_index()
            mp.columns = ['Producto', 'Monto']
            fig = px.bar(mp, x='Producto', y='Monto',
                         color_discrete_sequence=[COLOR_NARANJA],
                         text_auto='.2s')
            fig.update_layout(height=240, margin=dict(l=4,r=4,t=10,b=4),
                               paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF')
            st.plotly_chart(fig, use_container_width=True, key=f"bar_monto_{trader_seleccionado}")


# ══════════════════════════════════════════════════════════════════
# TAB 5 · Buscar Cliente
# ══════════════════════════════════════════════════════════════════
with tab_buscar:
    st.markdown('<div class="section-label">🔍 Ficha de cliente</div>', unsafe_allow_html=True)

    lista_nits  = sorted(df_trader['nit'].dropna().unique().tolist())
    nit_buscado = st.selectbox(
        "Selecciona un NIT",
        options=["— Selecciona un cliente —"] + [str(n) for n in lista_nits],
        label_visibility="collapsed",
        key=f"nit_{trader_seleccionado}",
    )

    if nit_buscado != "— Selecciona un cliente —":
        ops_cliente  = df_trader[df_trader['nit'].astype(str) == nit_buscado]
        pred_cliente = pred[pred['nit'].astype(str) == nit_buscado] if not pred.empty else pd.DataFrame()
        metricas     = calcular_metricas_por_cliente(ops_cliente)
        rec          = calcular_recomendacion_oferta(df_trader, nit_buscado)
        sugerencia   = texto_sugerencia_oferta(rec)

        if metricas.empty:
            st.warning("No se encontraron datos para este cliente.")
        else:
            datos      = metricas.iloc[0]
            texto_dias = "Sin registro" if datos['dias_sin_operar'] >= 999 else f"{int(datos['dias_sin_operar'])} días"

            # Predicción ML
            prob_ml, prod_ml = None, None
            if not pred_cliente.empty:
                prob_ml = pred_cliente.iloc[0].get('prob_opera_7d', None)
                prod_ml = pred_cliente.iloc[0].get('producto_predicho', None)
                if pd.isna(prod_ml) or str(prod_ml).lower() in ('nan', 'none', ''):
                    prod_ml = '—'

            # ── Ficha header ──
            pill_html = ""
            if prob_ml is not None:
                pill_html = f"""
                <div class="ficha-ml-pill">
                  <div class="ficha-ml-prob">{prob_ml:.0%}</div>
                  <div class="ficha-ml-label">prob. operar 7d</div>
                  <div style="font-size:12px;margin-top:4px;opacity:.9">🎯 {prod_ml}</div>
                </div>"""

            sector = str(datos.get('sector_economico') or 'Sector no disponible')
            segmento = str(datos.get('segmento') or '')

            st.markdown(f"""
            <div class="ficha-wrap">
              <div class="ficha-header">
                <div>
                  <div class="ficha-nit">👤 NIT {nit_buscado}</div>
                  <div class="ficha-sub">{segmento} &nbsp;·&nbsp; {sector[:60]}</div>
                </div>
                {pill_html}
              </div>

              <div class="ficha-stats">
                <div class="ficha-stat">
                  <div class="ficha-stat-val">${datos['monto_itau']:,.0f}</div>
                  <div class="ficha-stat-lbl">Monto Itaú</div>
                </div>
                <div class="ficha-stat">
                  <div class="ficha-stat-val">${datos['monto_mercado']:,.0f}</div>
                  <div class="ficha-stat-lbl">Oportunidad mercado</div>
                </div>
                <div class="ficha-stat">
                  <div class="ficha-stat-val">{texto_dias}</div>
                  <div class="ficha-stat-lbl">Sin operar</div>
                </div>
                <div class="ficha-stat">
                  <div class="ficha-stat-val">{int(datos['n_operaciones'])}</div>
                  <div class="ficha-stat-lbl">Operaciones</div>
                </div>
              </div>

              <div class="ficha-offer">
                📞 <b>Patrones históricos:</b> {sugerencia}
              </div>
            </div>
            """, unsafe_allow_html=True)

            # ── Gráficas ──
            g1, g2, g3 = st.columns(3)

            with g1:
                st.markdown("##### Producto")
                if 'producto' in ops_cliente.columns:
                    cp = ops_cliente['producto'].value_counts().reset_index()
                    cp.columns = ['Producto', 'N']
                    fig = px.pie(cp, names='Producto', values='N', hole=0.55,
                                 color_discrete_sequence=[COLOR_NARANJA, COLOR_NARANJA_CLARO, COLOR_GRIS])
                    fig.update_layout(height=200, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='#FFFFFF')
                    fig.update_traces(textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True, key=f"prod_pie_{nit_buscado}")

            with g2:
                st.markdown("##### Moneda")
                if 'moneda' in ops_cliente.columns:
                    cm = ops_cliente['moneda'].value_counts().reset_index()
                    cm.columns = ['Moneda', 'N']
                    fig = px.pie(cm, names='Moneda', values='N', hole=0.55,
                                 color_discrete_sequence=[COLOR_NARANJA, COLOR_NARANJA_CLARO, COLOR_GRIS])
                    fig.update_layout(height=200, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='#FFFFFF')
                    fig.update_traces(textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True, key=f"moneda_pie_{nit_buscado}")

            with g3:
                st.markdown("##### Itaú vs Mercado")
                df_canal = pd.DataFrame({
                    'Canal': ['Itaú', 'Mercado'],
                    'Monto': [float(datos['monto_itau']), float(datos['monto_mercado'])]
                })
                if df_canal['Monto'].sum() > 0:
                    fig = px.pie(df_canal, names='Canal', values='Monto', hole=0.55,
                                 color='Canal',
                                 color_discrete_map={'Itaú': COLOR_NARANJA, 'Mercado': COLOR_GRIS})
                    fig.update_layout(height=200, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='#FFFFFF')
                    fig.update_traces(textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True, key=f"canal_pie_{nit_buscado}")

            with st.expander("📋 Ver todas las operaciones"):
                st.dataframe(ops_cliente, use_container_width=True, hide_index=True)
