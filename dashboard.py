import streamlit as st
import pandas as pd
import time
import os

st.set_page_config(page_title="AI Pump Radar", layout="wide")

st.title("🚀 Solana AI Pump Radar")
st.caption("Scanner de pré-pumps em tempo real")

placeholder = st.empty()

while True:
    if os.path.exists("dashboard.csv"):
        df = pd.read_csv("dashboard.csv")

        df = df.sort_values("Score IA", ascending=False)

        # métricas
        col1, col2, col3 = st.columns(3)

        col1.metric("Tokens rastreados", len(df))
        col2.metric("Maior pump 5m", f"{df['Pump 5m %'].max():.2f}%")
        col3.metric("Maior score IA", f"{df['Score IA'].max():.2f}")

        st.dataframe(
            df,
            use_container_width=True,
            height=500
        )

        # gráfico simples
        st.subheader("📈 Score IA")
        st.bar_chart(df.set_index("Token")["Score IA"])

    else:
        st.warning("Aguardando dados do scanner...")

    time.sleep(5)
    st.rerun()
