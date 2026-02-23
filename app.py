import csv
import io
import sqlite3
import time
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
import google.generativeai as genai

# --- CONFIGURAÇÃO DA IA (CORREÇÃO DE VERSÃO) ---
# Forçamos o uso do modelo via string simples que a biblioteca v1 gerencia melhor
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(
    page_title="Diagnóstico de Manutenção Industrial",
    page_icon="🛠️",
    layout="wide",
)

DB_PATH = "diagnostics.db"

# --- FUNÇÃO DE INTELIGÊNCIA REAL (ETAPA 2) ---
def gerar_diagnostico_ia(machine_name: str, problem_desc: str) -> str:
    # Prompt estruturado para agir como Engenheiro Sênior
    prompt = f"Aja como um engenheiro sênior de manutenção industrial. Analise o problema na máquina '{machine_name}': {problem_desc}. Forneça causas prováveis, riscos e recomendações técnicas."
    
    try:
        # Chamada ao modelo
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # Se falhar, tentamos uma rota secundária de nome de modelo
        try:
            model_alt = genai.GenerativeModel('gemini-pro')
            response = model_alt.generate_content(prompt)
            return response.text
        except:
            return f"Erro de Conexão: {str(e)}. Verifique se a chave API está ativa no Google AI Studio."

# --- FUNÇÕES DE BANCO DE DADOS (IGUAIS AO ORIGINAL) ---
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

# --- INTERFACE ---
def main():
    if "db_initialized" not in st.session_state:
        init_db()
        st.session_state.db_initialized = True
    
    st.session_state.history = load_history()
    
    tab1, tab2, tab3 = st.tabs(["Dashboard", "Novo Diagnóstico", "Histórico"])
    
    with tab1:
        st.title("Dashboard")
        if st.session_state.history:
            df = pd.DataFrame(st.session_state.history)
            st.plotly_chart(px.pie(df, names='urgency', title="Distribuição de Urgência"), use_container_width=True)
        else:
            st.info("Aguardando primeiro diagnóstico...")

    with tab2:
        st.title("Novo Diagnóstico (IA)")
        with st.form("diag_form"):
            m_name = st.text_input("Máquina")
            p_desc = st.text_area("Problema")
            urg = st.selectbox("Urgência", ["Baixa", "Média", "Alta"])
            if st.form_submit_button("Gerar Análise"):
                with st.spinner("Consultando Engenheiro IA..."):
                    diag = gerar_diagnostico_ia(m_name, p_desc)
                    res = {"machine": m_name, "problem": p_desc, "diagnosis": diag, "urgency": urg, "timestamp": datetime.now()}
                    save_diagnosis(res)
                    st.session_state.history = load_history()
                    st.success("Análise Concluída!")
                    st.write(diag)

    with tab3:
        st.title("Histórico")
        for item in st.session_state.history:
            with st.expander(f"{item['machine']} - {item['timestamp'].strftime('%d/%m/%Y')}"):
                st.write(item['diagnosis'])

if __name__ == "__main__":
    main()