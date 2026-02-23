import csv
import io
import sqlite3
import time
import os
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
import google.generativeai as genai

os.environ["GOOGLE_API_USE_MTLS"] = "never" 
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(
    page_title="Diagnóstico Industrial - Julio",
    page_icon="🛠️",
    layout="wide",
)

DB_PATH = "diagnostics.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS diagnoses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine TEXT NOT NULL,
                problem TEXT,
                diagnosis TEXT NOT NULL,
                urgency TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

def save_diagnosis(record):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO diagnoses (machine, problem, diagnosis, urgency, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (record["machine"], record["problem"], record["diagnosis"], 
              record["urgency"], record["timestamp"].isoformat()))

def load_history():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT machine, problem, diagnosis, urgency, created_at FROM diagnoses ORDER BY id DESC").fetchall()
    return [{"machine": r[0], "problem": r[1], "diagnosis": r[2], "urgency": r[3], "timestamp": datetime.fromisoformat(r[4])} for r in rows]

def gerar_diagnostico_ia(machine, problem):
    prompt = f"Aja como engenheiro de manutenção industrial. Analise a máquina {machine}. Problema: {problem}."
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro técnico na IA: {str(e)}. Verifique a cota no AI Studio."

def render_dashboard():
    st.title("📊 Dashboard Industrial")
    history = st.session_state.history
    
    if not history:
        st.info("Aguardando registros para gerar os gráficos...")
        return

    df = pd.DataFrame(history)
    

    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Diagnósticos", len(df))
    c2.metric("Última Máquina", df.iloc[0]['machine'])
    c3.metric("Urgência Recente", df.iloc[0]['urgency'])

    st.divider()
    
    col_bar, col_pie = st.columns(2)


    with col_bar:
        st.subheader("Diagnósticos por Máquina")

        machine_counts = df['machine'].value_counts().reset_index()
        machine_counts.columns = ['Máquina', 'Quantidade']
        fig_bar = px.bar(machine_counts, x='Máquina', y='Quantidade', color='Máquina',
                         color_discrete_sequence=px.colors.qualitative.Vivid)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_pie:
        st.subheader("Distribuição de Urgência")
        fig_pie = px.pie(df, names='urgency', color='urgency',
                         color_discrete_map={"Alta": "#e74c3c", "Média": "#f1c40f", "Baixa": "#2ecc71"})
        st.plotly_chart(fig_pie, use_container_width=True)

def main():
    if "db_initialized" not in st.session_state:
        init_db()
        st.session_state.db_initialized = True
    
    st.session_state.history = load_history()
    
    tabs = st.tabs(["Dashboard", "Novo Diagnóstico", "Histórico"])
    
    with tabs[0]: render_dashboard()
    
    with tabs[1]:
        st.title("🛠️ Novo Diagnóstico IA")
        with st.form("form_ia"):
            m = st.text_input("Nome da Máquina")
            p = st.text_area("Descrição do Problema")
            u = st.selectbox("Urgência", ["Baixa", "Média", "Alta"])
            if st.form_submit_button("Consultar Gemini"):
                if m and p:
                    with st.spinner("IA Analisando..."):
                        res = gerar_diagnostico_ia(m, p)
                        save_diagnosis({"machine": m, "problem": p, "diagnosis": res, "urgency": u, "timestamp": datetime.now()})
                        st.session_state.history = load_history()
                        st.success("Análise Concluída!")
                        st.write(res)

    with tabs[2]:
        st.title("📜 Histórico SQLite")
        for item in st.session_state.history:
            with st.expander(f"{item['machine']} - {item['timestamp'].strftime('%d/%m/%Y %H:%M')}"):
                st.write(f"**Problema:** {item['problem']}")
                st.info(item['diagnosis'])

if __name__ == "__main__":
    main()