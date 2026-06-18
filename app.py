import streamlit as st

st.set_page_config(
    page_title="Mesa de Clientes — Itaú",
    page_icon="🟠",
    layout="wide",
)

pg = st.navigation([
    st.Page("pages/01_mesa.py",   title="Mesa de Clientes", icon="📋"),
    st.Page("pages/02_cargue.py", title="Cargue de Datos",  icon="📤"),
])
pg.run()
