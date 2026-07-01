import streamlit as st

st.set_page_config(
    page_title="Nutrition Label Analyzer",
    layout="wide",
    initial_sidebar_state="expanded",
)

pg = st.navigation([
    st.Page("pages/1_Label_Analyzer.py", title="Label Analyzer"),
    st.Page("pages/2_Label_Checker.py", title="Label Checker"),
    st.Page("pages/3_DMT.py", title="DMT")
])

pg.run()
