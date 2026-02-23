import csv
import io
import sqlite3
import time
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
import google.generativeai as genai

# --- CONFIGURAÇÃO DA IA (CORREÇÃO DO ERRO 404) ---
# Usando a configuração recomendada para evitar conflitos de versão da API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

st.set_page_config(
    page_title="Diagnóstico de Manutenção Industrial",
    page_icon="🛠️",
    layout="wide",
)

DB_PATH = "diagnostics.db"

# --- FUNÇÃO DE INTELIGÊNCIA REAL (AJUSTADA) ---
def gerar_diagnostico_ia(machine_name: str, problem_desc: str) -> str:
    prompt = f"""
    Você é um engenheiro sênior de manutenção industrial. 
    Analise o seguinte problema relatado na máquina '{machine_name}':
    {problem_desc}
    
    Forneça:
    1. Causas prováveis.
    2. Riscos de segurança.
    3. Recomendações técnicas detalhadas.
    """
    try:
        # Chamada direta ao modelo configurado
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro na conexão com Gemini: {str(e)}. Verifique se a cota da API ou a região estão disponíveis."

# --- FUNÇÕES DE BANCO DE DADOS (IGUAIS AO SEU ORIGINAL) ---
def init_state():
    if "history" not in st.session_state:
        st.session_state.history = []
    if "last_diagnosis" not in st.session_state:
        st.session_state.last_diagnosis = None
    if "db_initialized" not in st.session_state:
        init_db()
        st.session_state.db_initialized = True

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
    history = []
    for machine, problem, diagnosis, urgency, created_at in rows:
        history.append({
            "machine": machine,
            "problem": problem or "",
            "diagnosis": diagnosis,
            "urgency": urgency,
            "timestamp": datetime.fromisoformat(created_at),
        })
    return history

def save_diagnosis(record):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO diagnoses (machine, problem, diagnosis, urgency, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (record["machine"], record["problem"], record["diagnosis"], 
              record["urgency"], record["timestamp"].isoformat()))

# --- INTERFACES DE RENDERIZAÇÃO ---
def render_dashboard():
    st.title("Dashboard")
    history = st.session_state.history
    if not history:
        st.info("Nenhum diagnóstico registrado.")
        return
    
    last_diag = st.session_state.last_diagnosis or (history[0] if history else None)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Diagnósticos", len(history))
    col2.metric("Última Máquina", last_diag["machine"] if last_diag else "—")
    col3.metric("Urgência", last_diag["urgency"] if last_diag else "—")

    st.divider()
    st.subheader("Análise de Urgências")
    df = pd.DataFrame(history)
    fig = px.pie(df, names='urgency', color='urgency', 
                 color_discrete_map={"Alta": "#e74c3c", "Média": "#f1c40f", "Baixa": "#2ecc71"})
    st.plotly_chart(fig, use_container_width=True)

def render_new_diagnosis():
    st.title("Novo Diagnóstico (IA Ativa)")
    with st.form("diagnosis_form"):
        machine_name = st.text_input("Nome da máquina")
        problem_desc = st.text_area("Descrição do problema", height=140)
        urgency = st.selectbox("Nível de urgência", ["Baixa", "Média", "Alta"])
        submitted = st.form_submit_button("Processar com Gemini IA")

    if submitted and machine_name:
        with st.spinner("IA Analisando falha..."):
            diagnosis_text = gerar_diagnostico_ia(machine_name, problem_desc)
            
            record = {
                "machine": machine_name.strip(),
                "problem": problem_desc.strip(),
                "diagnosis": diagnosis_text,
                "urgency": urgency,
                "timestamp": datetime.now(),
            }
            save_diagnosis(record)
            st.session_state.history = load_history()
            st.session_state.last_diagnosis = record
            st.success("Diagnóstico Gerado!")
            st.markdown(f"### Análise Técnica:\n{diagnosis_text}")

def render_history():
    st.title("Histórico")
    if not st.session_state.history:
        st.info("Histórico vazio.")
        return

    csv_buffer = io.StringIO()
    pd.DataFrame(st.session_state.history).to_csv(csv_buffer)
    st.download_button("Exportar CSV", data=csv_buffer.getvalue(), file_name="diagnosticos.csv")

    for idx, item in enumerate(st.session_state.history, start=1):
        with st.expander(f"{idx}. {item['machine']} — {item['timestamp'].strftime('%d/%m/%Y %H:%M')}"):
            st.write(f"**Problema:** {item['problem']}")
            st.info(f"**Análise da IA:** {item['diagnosis']}")

def main():
    init_state()
    st.session_state.history = load_history()
    
    tabs = st.tabs(["Dashboard", "Novo Diagnóstico", "Histórico"])
    with tabs[0]: render_dashboard()
    with tabs[1]: render_new_diagnosis()
    with tabs[2]: render_history()

if __name__ == "__main__":
    main()