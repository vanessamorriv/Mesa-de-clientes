import streamlit as st

st.set_page_config(
    page_title="Mesa de Clientes — Itaú",
    page_icon="🟠",
    layout="wide",
)

# CSS global que aplica a todas las páginas
st.markdown("""
<style>
  .card { background:#fff; border:1px solid #E5E7EB; border-radius:12px; 
          padding:18px 20px; margin-bottom:14px; box-shadow:0 1px 4px rgba(0,0,0,.06); }
  .card-head { display:flex; justify-content:space-between; align-items:center;
               margin-bottom:12px; padding-bottom:10px; border-bottom:1px solid #F3F4F6; }
  .card-nit { font-size:16px; font-weight:700; color:#111827; }
  .card-rank { font-size:13px; font-weight:500; color:#6B7280; margin-right:6px; }
  .card-score { background:#FF6900; color:#fff; font-size:15px; font-weight:700;
                border-radius:20px; padding:3px 14px; }
  .card-score span { font-size:11px; font-weight:400; opacity:.85; margin-left:2px; }
  .card-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px 20px; margin-bottom:12px; }
  .card-item { display:flex; flex-direction:column; gap:1px; }
  .card-item-label { font-size:11px; color:#6B7280; text-transform:uppercase; letter-spacing:.4px; }
  .card-item-value { font-size:14px; font-weight:600; color:#111827; }
  .card-sector { font-size:12px; color:#6B7280; margin-bottom:10px; 
                 white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .card-offer { background:#FFF3EA; border-radius:8px; padding:9px 13px;
                font-size:13px; color:#4B3A2A; margin-bottom:10px; line-height:1.5; }
  .badges { display:flex; flex-wrap:wrap; gap:6px; }
  .badge { font-size:11px; font-weight:600; border-radius:20px; padding:3px 11px; }
  .badge-alerta      { background:#FEE2E2; color:#991B1B; }
  .badge-oportunidad { background:#FEF3C7; color:#92400E; }
  .badge-fidelidad   { background:#D1FAE5; color:#065F46; }
  .badge-nuevo       { background:#DBEAFE; color:#1E40AF; }
  .badge-neutral     { background:#F3F4F6; color:#6B7280; }
  .prio-scroll { max-height:72vh; overflow-y:auto; padding-right:4px; }
  .section-label { font-size:13px; font-weight:700; color:#6B7280; text-transform:uppercase;
                   letter-spacing:.6px; padding:10px 0 8px; border-bottom:3px solid #FF6900; margin-bottom:16px; }
  .caja-ayuda { background:#FFF3EA; border:1px solid #FFCFA0; border-radius:8px;
                padding:10px 14px; font-size:13px; color:#4B3A2A; margin:6px 0 16px; line-height:1.5; }
</style>
""", unsafe_allow_html=True)

pg = st.navigation([
    st.Page("pages/01_mesa.py",   title="Mesa de Clientes", icon="📋"),
    st.Page("pages/02_cargue.py", title="Cargue de Datos",  icon="📤"),
])
pg.run()

pg.run()
