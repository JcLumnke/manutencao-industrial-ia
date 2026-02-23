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
model = genai.GenerativeModel("gemini-1.5-flash")

st.set_page_config(
    page_title="Diagnóstico de Manutenção Industrial",
    page_icon="🛠️",
    layout="wide",
)

DB_PATH = "diagnostics.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS diagnoses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine TEXT NOT NULL,
                problem TEXT,
                diagnosis TEXT NOT NULL,
                urgency TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

def load_history():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT machine, problem, diagnosis, urgency, created_at FROM diagnoses ORDER BY id DESC"
        ).fetchall()
    return [
        {
            "machine": r[0],
            "problem": r[1],
            "diagnosis": r[2],
            "urgency": r[3],
            "timestamp": datetime.fromisoformat(r[4]),
        }
        for r in rows
    ]

def save_diagnosis(record):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO diagnoses (machine, problem, diagnosis, urgency, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record["machine"],
                record["problem"],
                record["diagnosis"],
                record["urgency"],
                record["timestamp"].isoformat(),
            ),
        )

def gerar_diagnostico_ia(machine, problem):
    prompt = f"Aja como engenheiro de manutenção industrial. Analise a máquina {machine}. Problema: {problem}."
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "Erro de conexão com o servidor de IA. Verifique as configurações."

def render_dashboard():
    st.title("Dashboard")
    history = st.session_state.get("history", [])
    if not history:
        st.info("Aguardando dados para exibição.")
        return

    df = pd.DataFrame(history)
    df["machine"] = df["machine"].str.strip().str.upper()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Diagnósticos", len(df))
    c2.metric("Máquina Recente", df.iloc[0]["machine"])
    c3.metric("Status Recente", df.iloc[0]["urgency"])

    st.divider()
    col_bar, col_pie = st.columns(2)

    with col_bar:
        m_counts = df["machine"].value_counts().reset_index()
        m_counts.columns = ["Máquina", "Quantidade"]
        fig = px.bar(m_counts, x="Máquina", y="Quantidade", color="Máquina",
                     title="Volume por Equipamento")
        st.plotly_chart(fig, use_container_width=True)

    with col_pie:
        fig = px.pie(df, names="urgency", color="urgency",
                     color_discrete_map={"Alta": "#e74c3c", "Média": "#f1c40f", "Baixa": "#2ecc71"},
                     title="Distribuição de Urgência")
        st.plotly_chart(fig, use_container_width=True)

def render_new_diagnosis():
    st.title("Novo Diagnóstico")
    with st.form("main_form"):
        m = st.text_input("Nome da Máquina")
        p = st.text_area("Problema")
        u = st.selectbox("Urgência", ["Baixa", "Média", "Alta"])
        if st.form_submit_button("Analisar com Gemini IA"):
            if m and p:
                with st.spinner("Processando..."):
                    diag = gerar_diagnostico_ia(m, p)
                    rec = {
                        "machine": m.strip().upper(),
                        "problem": p.strip(),
                        "diagnosis": diag,
                        "urgency": u,
                        "timestamp": datetime.now(),
                    }
                    save_diagnosis(rec)
                    st.session_state.history = load_history()
                    st.success("Análise Finalizada.")
                    st.write(diag)

def render_history():
    st.title("Histórico")
    history = st.session_state.get("history", [])
    if not history:
        st.info("Histórico disponível após o primeiro registro.")
        return

    csv_buf = io.StringIO()
    pd.DataFrame(history).to_csv(csv_buf)
    st.download_button("Baixar Dados (CSV)", csv_buf.getvalue(), "diagnosticos.csv")

    for item in history:
        with st.expander(f"{item['machine']} - {item['timestamp'].strftime('%d/%m/%Y %H:%M')}"):
            st.write(f"**Problema:** {item['problem']}")
            st.info(item["diagnosis"])

def main():
    if "db_initialized" not in st.session_state:
        init_db()
        st.session_state.db_initialized = True
    st.session_state.history = load_history()
    t1, t2, t3 = st.tabs(["Dashboard", "Novo Diagnóstico", "Histórico"])
    with t1: render_dashboard()
    with t2: render_new_diagnosis()
    with t3: render_history()

if __name__ == "__main__":
    main()