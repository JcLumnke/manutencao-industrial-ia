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

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.set_page_config(
    page_title="Diagnóstico de Manutenção Industrial",
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

def load_history():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT machine, problem, diagnosis, urgency, created_at FROM diagnoses ORDER BY id DESC").fetchall()
    return [{"machine": r[0].strip().upper(), "problem": r[1], "diagnosis": r[2], "urgency": r[3], "timestamp": datetime.fromisoformat(r[4])} for r in rows]

def save_diagnosis(record):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO diagnoses (machine, problem, diagnosis, urgency, created_at) VALUES (?, ?, ?, ?, ?)",
                     (record["machine"], record["problem"], record["diagnosis"], record["urgency"], record["timestamp"].isoformat()))

def gerar_diagnostico_ia(machine, problem):
    prompt = f"Aja como engenheiro de manutenção industrial. Analise a máquina {machine}. Problema: {problem}."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro Técnico: {str(e)}"

def render_dashboard():
    st.title("Dashboard")
    history = load_history()
    if not history:
        st.warning("O banco de dados está vazio. Realize um 'Novo Diagnóstico' para gerar os gráficos.")
        return
    
    df = pd.DataFrame(history)
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Volume por Equipamento")
        m_counts = df['machine'].value_counts().reset_index()
        m_counts.columns = ['Máquina', 'Total']
        st.plotly_chart(px.bar(m_counts, x='Máquina', y='Total', color='Máquina'), use_container_width=True)
        
    with col2:
        st.subheader("Distribuição de Urgência")
        st.plotly_chart(px.pie(df, names='urgency', color='urgency', 
                               color_discrete_map={"Alta": "#e74c3c", "Média": "#f1c40f", "Baixa": "#2ecc71"}), use_container_width=True)

    if st.button("Limpar Histórico"):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM diagnoses")
        st.rerun()

def render_new_diagnosis():
    st.title("Novo Diagnóstico")
    with st.form("main_form"):
        m = st.text_input("Máquina")
        p = st.text_area("Descrição do Problema")
        u = st.selectbox("Urgência", ["Baixa", "Média", "Alta"])
        if st.form_submit_button("Gerar Análise Técnica"):
            if m and p:
                with st.spinner("IA Processando..."):
                    diag = gerar_diagnostico_ia(m, p)
                    save_diagnosis({"machine": m.strip().upper(), "problem": p, "diagnosis": diag, "urgency": u, "timestamp": datetime.now()})
                    st.success("Diagnóstico concluído.")
                    st.write(diag)

def render_history():
    st.title("Histórico")
    history = load_history()
    if history:
        csv_buf = io.StringIO()
        pd.DataFrame(history).to_csv(csv_buf)
        st.download_button("Exportar CSV", csv_buf.getvalue(), "diagnosticos.csv")
        
    for item in history:
        with st.expander(f"{item['machine']} - {item['timestamp'].strftime('%d/%m/%Y %H:%M')}"):
            st.info(item['diagnosis'])

def main():
    init_db()
    tabs = st.tabs(["Dashboard", "Novo Diagnóstico", "Histórico"])
    with tabs[0]: render_dashboard()
    with tabs[1]: render_new_diagnosis()
    with tabs[2]: render_history()

if __name__ == "__main__":
    main()