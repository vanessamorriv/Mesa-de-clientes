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

COLOR_NARANJA       = "#FF6900"
COLOR_NARANJA_CLARO = "#FFB266"
COLOR_GRIS          = "#8A8A8A"
COLOR_GRIS_CLARO    = "#F0F0F0"

BADGE_CLASES = {
    "alerta":      "badge-alerta",
    "oportunidad": "badge-oportunidad",
    "fidelidad":   "badge-fidelidad",
    "nuevo":       "badge-nuevo",
    "neutral":     "badge-neutral",
}


# ── Carga de datos con cache ──────────────────────────────────────
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
col_logo, col_sep, col_app, col_spacer, col_sel = st.columns([1.2, 0.15, 1.5, 4, 1.5])
with col_logo:
    st.markdown('<div class="topbar-logo" style="padding-top:6px">🟠 Itaú Colombia</div>', unsafe_allow_html=True)
with col_sep:
    st.markdown('<div class="topbar-sep" style="padding-top:8px">|</div>', unsafe_allow_html=True)
with col_app:
    st.markdown('<div class="topbar-app" style="padding-top:9px">Mesa de Clientes</div>', unsafe_allow_html=True)
with col_sel:
    trader_seleccionado = st.selectbox(
        label="Cartera",
        options=lista_traders,
        format_func=lambda t: t,
        label_visibility="collapsed",
        key="trader_selector",
    )

st.markdown("<hr style='margin:0 0 10px 0; border:none; border-top:1px solid #F0F0F0'>", unsafe_allow_html=True)


# ── Datos del trader ──────────────────────────────────────────────
df_trader = filtrar_por_trader(df, trader_seleccionado)
nits_trader = df_trader['nit'].unique().tolist()
pred_trader = pred[pred['nit'].astype(str).isin([str(n) for n in nits_trader])] if not pred.empty else pd.DataFrame()


# ── Métricas ──────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("Clientes en cartera", df_trader['nit'].nunique())
m2.metric("Predicciones disponibles", len(pred_trader))
m3.metric("Monto generado Itaú", f"{df_trader['monto_entidad'].sum():,.0f}" if 'monto_entidad' in df_trader.columns else "—")
m4.metric("Oportunidad Mercado",  f"{df_trader['monto_mercado'].sum():,.0f}"  if 'monto_mercado'  in df_trader.columns else "—")

st.markdown("<div class='caja-ayuda'>ℹ️ <b>Monto Itaú</b>: operado con Itaú. <b>Oportunidad</b>: operado con la competencia — negocio capturable.</div>", unsafe_allow_html=True)


# ── Tabs principales ──────────────────────────────────────────────
tab_ml, tab_hist, tab_comb, tab_dash, tab_buscar = st.tabs([
    "🤖 Predicciones ML",
    "📋 Priorización Histórica",
    "⚡ Combinado",
    "📊 Dashboard",
    "🔍 Buscar Cliente",
])


# ── TAB 1: Predicciones ML ────────────────────────────────────────
with tab_ml:
    st.markdown('<div class="section-label">🤖 Clientes con mayor probabilidad de operar mañana</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="caja-ayuda">
    Ordenado por <b>score del modelo ML</b>: predice quién va a operar en los próximos 7 días y qué producto.
    No considera historial de montos — mira hacia adelante.
    </div>
    """, unsafe_allow_html=True)

    if pred_trader.empty:
        st.info("No hay predicciones disponibles para este trader.")
    else:
        df_ml = generar_priorizacion(df_trader, pred_trader, modo='ml')
        col_lista, col_panel = st.columns([3, 2], gap="medium")

        with col_lista:
            tarjetas_html = ""
            for pos, fila in df_ml.iterrows():
                prob   = fila.get('prob_opera_7d', 0) or 0
                prod   = fila.get('producto_predicho') or '—'
                badges = "".join(
                    f'<span class="badge {BADGE_CLASES.get(tipo, "badge-neutral")}">{texto}</span>'
                    for texto, tipo in fila['necesidades']
                )
                texto_dias = "Sin registro" if fila['dias_sin_operar'] >= 999 else f"{int(fila['dias_sin_operar'])} días sin operar"
                tarjetas_html += (
                    '<div class="card">'
                      '<div class="card-head">'
                        f'<span class="card-name">#{pos+1} · NIT {fila["nit"]}</span>'
                        f'<span class="card-score">{prob:.0%}<span> prob.</span></span>'
                      '</div>'
                      '<div class="card-row">'
                        f'<span>🎯 Producto predicho: <b>{prod}</b></span>'
                        f'<span>⏱️ {texto_dias}</span>'
                      '</div>'
                      '<div class="card-row">'
                        f'<span>🏢 {fila["sector_economico"]}</span>'
                        f'<span>🔄 <b>{int(fila["n_operaciones"])}</b> ops.</span>'
                      '</div>'
                      '<div class="card-offer">'
                        f'📞 <b>Historial:</b> {fila["sugerencia_oferta"]}'
                      '</div>'
                      f'<div>{badges}</div>'
                    '</div>'
                )
            st.markdown(f'<div class="prio-scroll">{tarjetas_html}</div>', unsafe_allow_html=True)

        with col_panel:
            st.markdown("**Distribución de productos predichos**")
            prod_counts = pred_trader['producto_predicho'].dropna().value_counts().reset_index()
            prod_counts.columns = ['Producto', 'Conteo']
            if not prod_counts.empty:
                fig = px.pie(prod_counts, names='Producto', values='Conteo', hole=0.5,
                             color_discrete_sequence=[COLOR_NARANJA, COLOR_NARANJA_CLARO, COLOR_GRIS])
                fig.update_layout(height=250, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='#FFFFFF')
                st.plotly_chart(fig, use_container_width=True, key=f"pie_ml_{trader_seleccionado}")

            st.markdown("**Top 10 por probabilidad**")
            if not df_ml.empty:
                top10 = df_ml[['nit','prob_opera_7d','producto_predicho']].head(10).copy()
                top10.columns = ['NIT', 'Prob. Opera 7d', 'Producto Predicho']
                top10['Prob. Opera 7d'] = top10['Prob. Opera 7d'].apply(lambda x: f"{x:.1%}" if x else "—")
                st.dataframe(top10, use_container_width=True, hide_index=True)


# ── TAB 2: Priorización Histórica ────────────────────────────────
with tab_hist:
    st.markdown('<div class="section-label">📋 A quién llamar hoy — basado en historial</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="caja-ayuda">
    Ordenado por <b>puntaje histórico</b>: combina monto con Itaú, oportunidad en mercado,
    días sin operar y frecuencia. Mira hacia atrás.
    </div>
    """, unsafe_allow_html=True)

    df_hist = generar_priorizacion(df_trader, modo='historico')
    col_lista, col_panel = st.columns([3, 2], gap="medium")

    with col_lista:
        if df_hist.empty:
            st.info("Esta cartera no tiene clientes registrados.")
        else:
            tarjetas_html = ""
            for pos, fila in df_hist.iterrows():
                badges = "".join(
                    f'<span class="badge {BADGE_CLASES.get(tipo, "badge-neutral")}">{texto}</span>'
                    for texto, tipo in fila['necesidades']
                )
                texto_dias = "Sin registro" if fila['dias_sin_operar'] >= 999 else f"{int(fila['dias_sin_operar'])} días sin operar"
                tarjetas_html += (
                    '<div class="card">'
                      '<div class="card-head">'
                        f'<span class="card-name">#{pos+1} · NIT {fila["nit"]}</span>'
                        f'<span class="card-score">{fila["puntaje_historico"]}<span>/100</span></span>'
                      '</div>'
                      '<div class="card-row">'
                        f'<span>💰 Itaú: <b>{fila["monto_itau"]:,.0f}</b></span>'
                        f'<span>🎯 Mercado: <b>{fila["monto_mercado"]:,.0f}</b></span>'
                        f'<span>⏱️ {texto_dias}</span>'
                      '</div>'
                      '<div class="card-row">'
                        f'<span>🏢 {fila["sector_economico"]}</span>'
                        f'<span>🔄 <b>{int(fila["n_operaciones"])}</b> ops.</span>'
                      '</div>'
                      '<div class="card-offer">'
                        f'📞 <b>Qué ofrecer:</b> {fila["sugerencia_oferta"]}'
                      '</div>'
                      f'<div>{badges}</div>'
                    '</div>'
                )
            st.markdown(f'<div class="prio-scroll">{tarjetas_html}</div>', unsafe_allow_html=True)

    with col_panel:
        top_n = st.slider("Clientes a mostrar", 3, 10, 5, key=f"slider_hist_{trader_seleccionado}")

        st.markdown("**💱 Top por moneda**")
        monedas_disp = sorted(df_trader['moneda'].dropna().unique().tolist()) if 'moneda' in df_trader.columns else []
        monedas_obj  = [m for m in monedas_disp if m in ('USD/COP', 'EUR/COP')] or monedas_disp
        rank_moneda  = ranking_clientes_por_moneda(df_trader, monedas_obj, top_n)
        if not rank_moneda.empty:
            st.dataframe(rank_moneda, use_container_width=True, hide_index=True)

        st.markdown("**📦 Top por producto**")
        prods_disp = sorted(df_trader['producto'].dropna().unique().tolist()) if 'producto' in df_trader.columns else []
        prods_obj  = [p for p in prods_disp if p.strip().upper() in ('SPOT', 'FORWARD')] or prods_disp
        rank_prod  = ranking_clientes_por_producto(df_trader, prods_obj, top_n)
        if not rank_prod.empty:
            st.dataframe(rank_prod, use_container_width=True, hide_index=True)


# ── TAB 3: Combinado ─────────────────────────────────────────────
with tab_comb:
    st.markdown('<div class="section-label">⚡ Priorización combinada — ML + Histórico</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="caja-ayuda">
    Combina el <b>score del modelo ML</b> (quién va a operar) con el <b>puntaje histórico</b>
    (valor del cliente). Ajusta los pesos según lo que más le importe al equipo.
    </div>
    """, unsafe_allow_html=True)

    col_w1, col_w2, _ = st.columns([1, 1, 2])
    with col_w1:
        peso_ml   = st.slider("Peso ML (%)", 0, 100, 60, step=10, key=f"peso_ml_{trader_seleccionado}") / 100
    with col_w2:
        peso_hist = round(1 - peso_ml, 2)
        st.metric("Peso Histórico (%)", f"{peso_hist:.0%}")

    df_comb = generar_priorizacion(df_trader, pred_trader, modo='combinado')

    col_lista, col_panel = st.columns([3, 2], gap="medium")

    with col_lista:
        if df_comb.empty:
            st.info("No hay datos para mostrar.")
        else:
            tarjetas_html = ""
            for pos, fila in df_comb.iterrows():
                prob  = fila.get('prob_opera_7d', 0) or 0
                prod  = fila.get('producto_predicho') or '—'
                score = fila.get('score_combinado', 0) or 0
                badges = "".join(
                    f'<span class="badge {BADGE_CLASES.get(tipo, "badge-neutral")}">{texto}</span>'
                    for texto, tipo in fila['necesidades']
                )
                texto_dias = "Sin registro" if fila['dias_sin_operar'] >= 999 else f"{int(fila['dias_sin_operar'])} días sin operar"
                tarjetas_html += (
                    '<div class="card">'
                      '<div class="card-head">'
                        f'<span class="card-name">#{pos+1} · NIT {fila["nit"]}</span>'
                        f'<span class="card-score">{score:.2f}<span> score</span></span>'
                      '</div>'
                      '<div class="card-row">'
                        f'<span>🤖 Prob: <b>{prob:.0%}</b></span>'
                        f'<span>🎯 Producto: <b>{prod}</b></span>'
                        f'<span>⏱️ {texto_dias}</span>'
                      '</div>'
                      '<div class="card-row">'
                        f'<span>💰 Itaú: <b>{fila["monto_itau"]:,.0f}</b></span>'
                        f'<span>🎯 Mercado: <b>{fila["monto_mercado"]:,.0f}</b></span>'
                      '</div>'
                      '<div class="card-offer">'
                        f'📞 <b>Historial:</b> {fila["sugerencia_oferta"]}'
                      '</div>'
                      f'<div>{badges}</div>'
                    '</div>'
                )
            st.markdown(f'<div class="prio-scroll">{tarjetas_html}</div>', unsafe_allow_html=True)

    with col_panel:
        if not df_comb.empty:
            st.markdown("**Score combinado vs Probabilidad ML**")
            fig = px.scatter(
                df_comb.head(50),
                x='prob_opera_7d',
                y='puntaje_historico',
                size='score_combinado',
                hover_data=['nit'],
                color_discrete_sequence=[COLOR_NARANJA],
                labels={'prob_opera_7d': 'Prob. ML', 'puntaje_historico': 'Puntaje Histórico'},
            )
            fig.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='#FFFFFF')
            st.plotly_chart(fig, use_container_width=True, key=f"scatter_comb_{trader_seleccionado}")


# ── TAB 4: Dashboard ─────────────────────────────────────────────
with tab_dash:
    st.markdown('<div class="section-label">📊 Dashboard de la cartera</div>', unsafe_allow_html=True)

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("**Producto más usado por cliente**")
        if 'producto' in df_trader.columns and not df_trader.empty:
            prod_top = (
                df_trader.groupby(['nit', 'producto'])
                .size().reset_index(name='conteo')
                .sort_values(['nit', 'conteo'], ascending=[True, False])
                .groupby('nit').first().reset_index()
            )
            fig = px.bar(prod_top, x='nit', y='conteo', color='producto',
                         color_discrete_sequence=[COLOR_NARANJA, COLOR_NARANJA_CLARO, COLOR_GRIS])
            fig.update_layout(height=260, margin=dict(l=4,r=4,t=10,b=4),
                               paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF')
            fig.update_xaxes(type='category', tickfont=dict(size=8))
            st.plotly_chart(fig, use_container_width=True, key=f"bar_prod_{trader_seleccionado}")

    with col_g2:
        st.markdown("**Distribución por moneda**")
        if 'moneda' in df_trader.columns:
            moneda_counts = df_trader['moneda'].value_counts().reset_index()
            moneda_counts.columns = ['Moneda', 'Conteo']
            fig = px.pie(moneda_counts, names='Moneda', values='Conteo', hole=0.5,
                         color_discrete_sequence=[COLOR_NARANJA, COLOR_NARANJA_CLARO, COLOR_GRIS])
            fig.update_layout(height=260, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='#FFFFFF')
            st.plotly_chart(fig, use_container_width=True, key=f"pie_moneda_{trader_seleccionado}")

    col_g3, col_g4 = st.columns(2)

    with col_g3:
        st.markdown("**Operaciones por mes**")
        if 'fecha' in df_trader.columns:
            df_mes = df_trader.copy()
            df_mes['mes'] = df_mes['fecha'].dt.to_period('M').astype(str)
            ops_mes = df_mes.groupby('mes').size().reset_index(name='operaciones')
            fig = px.line(ops_mes, x='mes', y='operaciones',
                          color_discrete_sequence=[COLOR_NARANJA])
            fig.update_layout(height=220, margin=dict(l=4,r=4,t=10,b=4),
                               paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF')
            fig.update_xaxes(tickfont=dict(size=8))
            st.plotly_chart(fig, use_container_width=True, key=f"line_mes_{trader_seleccionado}")

    with col_g4:
        st.markdown("**Monto total por producto**")
        if 'producto' in df_trader.columns and 'monto_total' in df_trader.columns:
            monto_prod = df_trader.groupby('producto')['monto_total'].sum().reset_index()
            monto_prod.columns = ['Producto', 'Monto']
            fig = px.bar(monto_prod, x='Producto', y='Monto',
                         color_discrete_sequence=[COLOR_NARANJA])
            fig.update_layout(height=220, margin=dict(l=4,r=4,t=10,b=4),
                               paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF')
            st.plotly_chart(fig, use_container_width=True, key=f"bar_monto_{trader_seleccionado}")


# ── TAB 5: Buscar Cliente ─────────────────────────────────────────
with tab_buscar:
    st.markdown('<div class="section-label">🔍 Detalle por cliente</div>', unsafe_allow_html=True)

    lista_nits  = sorted(df_trader['nit'].dropna().unique().tolist())
    nit_buscado = st.selectbox(
        "Selecciona un NIT",
        options=["-- Selecciona --"] + [str(n) for n in lista_nits],
        label_visibility="collapsed",
        key=f"nit_{trader_seleccionado}",
    )

    if nit_buscado != "-- Selecciona --":
        ops_cliente  = df_trader[df_trader['nit'].astype(str) == nit_buscado]
        pred_cliente = pred[pred['nit'].astype(str) == nit_buscado] if not pred.empty else pd.DataFrame()
        metricas     = calcular_metricas_por_cliente(ops_cliente)
        rec          = calcular_recomendacion_oferta(df_trader, nit_buscado)
        sugerencia   = texto_sugerencia_oferta(rec)

        if not metricas.empty:
            datos      = metricas.iloc[0]
            texto_dias = "Sin registro" if datos['dias_sin_operar'] >= 999 else f"{int(datos['dias_sin_operar'])} días sin operar"

            # Predicción ML si existe
            if not pred_cliente.empty:
                prob_ml = pred_cliente.iloc[0].get('prob_opera_7d', 0)
                prod_ml = pred_cliente.iloc[0].get('producto_predicho') or '—'
                st.markdown(f"""
                <div class="caja-ayuda">
                🤖 <b>Predicción ML:</b> {prob_ml:.0%} de probabilidad de operar en los próximos 7 días
                · Producto esperado: <b>{prod_ml}</b>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(
                '<div class="ficha-cliente">'
                f'<div class="ficha-titulo">👤 NIT {nit_buscado}</div>'
                '<div class="ficha-grid">'
                  '<div class="ficha-dato">'
                    '<div class="ficha-dato-etiqueta">Valor para Itaú</div>'
                    f'<div class="ficha-dato-valor">{datos["monto_itau"]:,.0f}</div>'
                  '</div>'
                  '<div class="ficha-dato">'
                    '<div class="ficha-dato-etiqueta">Monto en Mercado</div>'
                    f'<div class="ficha-dato-valor">{datos["monto_mercado"]:,.0f}</div>'
                  '</div>'
                  '<div class="ficha-dato">'
                    '<div class="ficha-dato-etiqueta">Última actividad</div>'
                    f'<div class="ficha-dato-valor">{texto_dias}</div>'
                  '</div>'
                  '<div class="ficha-dato">'
                    '<div class="ficha-dato-etiqueta">Operaciones</div>'
                    f'<div class="ficha-dato-valor">{int(datos["n_operaciones"])}</div>'
                  '</div>'
                '</div>'
                '<div class="card-offer">'
                  f'📞 <b>Patrones históricos:</b> {sugerencia}'
                '</div>'
                '</div>',
                unsafe_allow_html=True,
            )

            g1, g2, g3 = st.columns(3)

            with g1:
                st.markdown('<div class="mini-chart-label">Producto</div>', unsafe_allow_html=True)
                if 'producto' in ops_cliente.columns:
                    cp = ops_cliente['producto'].value_counts().reset_index()
                    cp.columns = ['Producto', 'Conteo']
                    fig = px.pie(cp, names='Producto', values='Conteo', hole=0.55,
                                 color_discrete_sequence=[COLOR_NARANJA, COLOR_NARANJA_CLARO, COLOR_GRIS])
                    fig.update_layout(height=180, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='#FFFFFF')
                    st.plotly_chart(fig, use_container_width=True, key=f"prod_pie_{nit_buscado}")

            with g2:
                st.markdown('<div class="mini-chart-label">Moneda</div>', unsafe_allow_html=True)
                if 'moneda' in ops_cliente.columns:
                    cm = ops_cliente['moneda'].value_counts().reset_index()
                    cm.columns = ['Moneda', 'Conteo']
                    fig = px.pie(cm, names='Moneda', values='Conteo', hole=0.55,
                                 color_discrete_sequence=[COLOR_NARANJA, COLOR_NARANJA_CLARO, COLOR_GRIS])
                    fig.update_layout(height=180, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='#FFFFFF')
                    st.plotly_chart(fig, use_container_width=True, key=f"moneda_pie_{nit_buscado}")

            with g3:
                st.markdown('<div class="mini-chart-label">Itaú vs Mercado</div>', unsafe_allow_html=True)
                df_canal = pd.DataFrame({
                    'Canal': ['Itaú', 'Mercado'],
                    'Monto': [float(datos['monto_itau']), float(datos['monto_mercado'])]
                })
                if df_canal['Monto'].sum() > 0:
                    fig = px.pie(df_canal, names='Canal', values='Monto', hole=0.55,
                                 color='Canal',
                                 color_discrete_map={'Itaú': COLOR_NARANJA, 'Mercado': COLOR_GRIS})
                    fig.update_layout(height=180, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='#FFFFFF')
                    st.plotly_chart(fig, use_container_width=True, key=f"canal_pie_{nit_buscado}")

            with st.expander("Ver todas las operaciones de este cliente"):
                st.dataframe(ops_cliente, use_container_width=True)
