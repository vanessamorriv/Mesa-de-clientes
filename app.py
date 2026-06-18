import streamlit as st
import pandas as pd
from data_loader import subir_operaciones, subir_clientes, subir_ciiu

COLOR_NARANJA = "#FF6900"
COLOR_GRIS    = "#8A8A8A"

st.markdown(f"""
<style>
.section-label {{
    font-size: 11px; font-weight: 600; color: {COLOR_GRIS};
    text-transform: uppercase; letter-spacing: .4px;
    padding: 8px 0 6px 0;
    border-bottom: 2px solid {COLOR_NARANJA};
    margin-bottom: 10px;
}}
.caja-ayuda {{
    background: #FFF6EE; border: 1px solid #FFD9B8;
    border-radius: 6px; padding: 7px 11px;
    font-size: 11px; color: #5A5A5A;
    margin: 6px 0 10px 0;
}}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="section-label">📤 Módulo de Cargue — Personal autorizado</div>', unsafe_allow_html=True)
st.markdown("""
<div class="caja-ayuda">
Suba aquí los archivos actualizados. Las operaciones se acumulan históricamente.
Clientes y CIIU reemplazan los registros existentes por NIT/código.
</div>
""", unsafe_allow_html=True)

# ── Operaciones ───────────────────────────────────────────────────
st.markdown("#### 📁 Operaciones")
archivo_ops = st.file_uploader(
    "Seleccione operaciones.xlsx",
    type=["xlsx"],
    key="upload_operaciones"
)
if archivo_ops:
    df_ops = pd.read_excel(archivo_ops)
    st.caption(f"{len(df_ops):,} registros encontrados")
    with st.expander("Vista previa"):
        st.dataframe(df_ops.head(10), use_container_width=True)
    if st.button("Subir operaciones", type="primary", key="btn_ops"):
        with st.spinner("Subiendo..."):
            try:
                res = subir_operaciones(df_ops)
                st.success(f"✅ {res['registros']:,} operaciones subidas correctamente en {res['lotes']} lotes.")
            except Exception as e:
                st.error(f"Error al subir operaciones: {e}")

st.markdown("<hr style='margin:16px 0; border:none; border-top:1px solid #F0F0F0'>", unsafe_allow_html=True)

# ── Clientes ──────────────────────────────────────────────────────
st.markdown("#### 👥 Clientes")
archivo_cli = st.file_uploader(
    "Seleccione clientes.xlsx",
    type=["xlsx"],
    key="upload_clientes"
)
if archivo_cli:
    df_cli = pd.read_excel(archivo_cli)
    st.caption(f"{len(df_cli):,} registros encontrados")
    with st.expander("Vista previa"):
        st.dataframe(df_cli.head(10), use_container_width=True)
    if st.button("Subir clientes", type="primary", key="btn_cli"):
        with st.spinner("Subiendo..."):
            try:
                res = subir_clientes(df_cli)
                st.success(f"✅ {res['registros']:,} clientes subidos correctamente.")
            except Exception as e:
                st.error(f"Error al subir clientes: {e}")

st.markdown("<hr style='margin:16px 0; border:none; border-top:1px solid #F0F0F0'>", unsafe_allow_html=True)

# ── CIIU ──────────────────────────────────────────────────────────
st.markdown("#### 🏭 Catálogo CIIU")
archivo_ciiu = st.file_uploader(
    "Seleccione ciiu.xlsx",
    type=["xlsx"],
    key="upload_ciiu"
)
if archivo_ciiu:
    df_ciiu = pd.read_excel(archivo_ciiu)
    st.caption(f"{len(df_ciiu):,} registros encontrados")
    with st.expander("Vista previa"):
        st.dataframe(df_ciiu.head(10), use_container_width=True)
    if st.button("Subir CIIU", type="primary", key="btn_ciiu"):
        with st.spinner("Subiendo..."):
            try:
                res = subir_ciiu(df_ciiu)
                st.success(f"✅ {res['registros']:,} códigos CIIU subidos correctamente.")
            except Exception as e:
                st.error(f"Error al subir CIIU: {e}")
