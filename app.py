import streamlit as st
import google.generativeai as genai
import sqlite3
import time
import io
import csv
from datetime import datetime
import pandas as pd
import plotly.express as px

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(
    page_title="Diagnóstico Industrial IA",
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
    prompt = f"""
    Você é um engenheiro sênior de manutenção industrial especialista em Indústria 4.0.
    Analise o seguinte problema na máquina '{machine}':
    Descrição do problema: {problem}
    
    Forneça:
    1. Uma análise técnica detalhada.
    2. Possíveis causas raiz.
    3. Recomendações de segurança e manutenção imediata.
    Seja profissional e direto.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro ao conectar com a IA: {e}"


def render_dashboard():
    st.title("📊 Dashboard Industrial")
    history = st.session_state.get("history", [])
    
    if not history:
        st.info("Nenhum dado disponível.")
        return

    last_diag = history[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Diagnósticos", len(history))
    c2.metric("Última Máquina", last_diag["machine"])
    c3.metric("Urgência Atual", last_diag["urgency"])

    st.subheader("Análise Urgência vs Máquina")
    df = pd.DataFrame(history)
    fig = px.pie(df, names='urgency', color='urgency',
                 color_discrete_map={"Alta": "#e74c3c", "Média": "#f1c40f", "Baixa": "#2ecc71"})
    st.plotly_chart(fig, use_container_width=True)

def render_new_diagnosis():
    st.title("🛠️ Novo Diagnóstico Real")
    with st.form("ia_form"):
        machine = st.text_input("Nome da Máquina")
        problem = st.text_area("Descrição do Problema")
        urgency = st.selectbox("Urgência", ["Baixa", "Média", "Alta"])
        submit = st.form_submit_button("Gerar Análise com Gemini IA")

    if submit and machine and problem:
        with st.spinner("O Gemini está analisando os dados industriais..."):
            resultado_ia = gerar_diagnostico_ia(machine, problem)
            
            record = {
                "machine": machine,
                "problem": problem,
                "diagnosis": resultado_ia,
                "urgency": urgency,
                "timestamp": datetime.now()
            }
            save_diagnosis(record)
            st.session_state.history = load_history()
            st.success("Análise Concluída!")
            st.markdown(f"### Diagnóstico Especialista:\n{resultado_ia}")

def main():
    if "db_initialized" not in st.session_state:
        init_db()
        st.session_state.db_initialized = True
    
    st.session_state.history = load_history()
    
    tab1, tab2 = st.tabs(["Dashboard", "Novo Diagnóstico"])
    with tab1: render_dashboard()
    with tab2: render_new_diagnosis()

if __name__ == "__main__":
    main()