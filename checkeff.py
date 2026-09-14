import streamlit as st
import pandas as pd

st.title("📊 Dashboard SAH")

df = pd.DataFrame({
    'Item': ['', '', ''],
    'Số lượng': [0, 0, 0],
    'Routing': [0.0, 0.0, 0.0],
    'SAH': [0.0, 0.0, 0.0]
})

edited = st.data_editor(df, num_rows="dynamic")

if st.button("Tính"):
    st.success("Đã tính xong!")
