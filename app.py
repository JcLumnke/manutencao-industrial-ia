import csv
import io
import sqlite3
import time
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
import google.generativeai as genai

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash-latest')

st.set_page_config(
    page_title="Diagnóstico de Manutenção Industrial",
    page_icon="🛠️",
    layout="wide",
)

DB_PATH = "diagnostics.db"

def gerar_diagnostico_ia(machine_name: str, problem_desc: str) -> str:
    prompt = f"""
    Você é um engenheiro sênior de manutenção industrial. 
    Analise o seguinte problema relatado na máquina '{machine_name}':
    {problem_desc}
    
    Forneça causas prováveis, riscos de segurança e recomendações técnicas detalhadas.
    """
    try:

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
    
        try:
            backup_model = genai.GenerativeModel('gemini-pro')
            response = backup_model.generate_content(prompt)
            return response.text
        except Exception as e2:
            return f"Erro Crítico de Conexão: {str(e2)}. Verifique sua cota no Google AI Studio."

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

def main():
    if "db_initialized" not in st.session_state:
        init_db()
        st.session_state.db_initialized = True
    
    st.session_state.history = load_history()
    
    tabs = st.tabs(["Dashboard", "Novo Diagnóstico", "Histórico"])
    
    with tabs[0]:
        st.title("Dashboard")
        if st.session_state.history:
            df = pd.DataFrame(st.session_state.history)
            fig = px.pie(df, names='urgency', color='urgency', 
                         color_discrete_map={"Alta": "#e74c3c", "Média": "#f1c40f", "Baixa": "#2ecc71"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum diagnóstico registrado.")

    with tabs[1]:
        st.title("Novo Diagnóstico (Gemini IA)")
        with st.form("diag_form"):
            machine = st.text_input("Máquina")
            problem = st.text_area("Descrição do Problema")
            urgency = st.selectbox("Urgência", ["Baixa", "Média", "Alta"])
            if st.form_submit_button("Gerar Análise Técnica"):
                if machine and problem:
                    with st.spinner("IA Analisando..."):
                        resultado = gerar_diagnostico_ia(machine, problem)
                        rec = {"machine": machine, "problem": problem, "diagnosis": resultado, "urgency": urgency, "timestamp": datetime.now()}
                        save_diagnosis(rec)
                        st.session_state.history = load_history()
                        st.success("Diagnóstico concluído!")
                        st.write(resultado)

    with tabs[2]:
        st.title("Histórico de Manutenção")
        for item in st.session_state.history:
            with st.expander(f"{item['machine']} - {item['timestamp'].strftime('%d/%m/%Y %H:%M')}"):
                st.write(f"**Problema:** {item['problem']}")
                st.info(item['diagnosis'])

if __name__ == "__main__":
    main()