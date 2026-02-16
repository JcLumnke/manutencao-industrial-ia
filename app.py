import csv
import io
import sqlite3
import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Diagnóstico de Manutenção Industrial",
    page_icon="🛠️",
    layout="wide",
)


DB_PATH = "diagnostics.db"


def init_state():
    if "history" not in st.session_state:
        st.session_state.history = []
    if "last_diagnosis" not in st.session_state:
        st.session_state.last_diagnosis = None
    if "db_initialized" not in st.session_state:
        init_db()
        seed_test_data()
        st.session_state.db_initialized = True


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
        ensure_column(conn, "diagnoses", "urgency", "TEXT NOT NULL DEFAULT 'Média'")


def ensure_column(conn, table_name, column_name, column_def):
    cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing = {col[1] for col in cols}
    if column_name not in existing:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")


def seed_test_data():
    with sqlite3.connect(DB_PATH) as conn:
        count = conn.execute("SELECT COUNT(*) FROM diagnoses").fetchone()[0]
        if count > 0:
            return

        samples = [
            ("Bobinadeira 01", "Ruído intermitente no motor principal", "Alta"),
            ("Bobinadeira 02", "Oscilação na tensão da bobina", "Média"),
            ("Prensa Hidráulica A", "Vazamento leve no circuito", "Média"),
            ("Prensa Hidráulica B", "Queda súbita de pressão", "Alta"),
            ("Esteira 3", "Desalinhamento lateral recorrente", "Baixa"),
            ("Esteira 4", "Paradas curtas sem motivo aparente", "Média"),
            ("Forno Térmico 1", "Aquecimento abaixo do setpoint", "Alta"),
            ("Compressor Z9", "Vibração excessiva na base", "Média"),
            ("Misturador M5", "Aumento de temperatura no rolamento", "Alta"),
            ("Bobinadeira 01", "Desgaste anormal da correia", "Baixa"),
        ]

        now = datetime.now()
        for idx, (machine, problem, urgency) in enumerate(samples):
            diagnosis = mock_diagnosis(machine, problem)
            created_at = now.replace(microsecond=0)
            conn.execute(
                """
                INSERT INTO diagnoses (machine, problem, diagnosis, urgency, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    machine,
                    problem,
                    diagnosis,
                    urgency,
                    created_at.isoformat(),
                ),
            )


def load_history():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT machine, problem, diagnosis, urgency, created_at
            FROM diagnoses
            ORDER BY id DESC
            """
        ).fetchall()

    history = []
    for machine, problem, diagnosis, urgency, created_at in rows:
        history.append(
            {
                "machine": machine,
                "problem": problem or "",
                "diagnosis": diagnosis,
                "urgency": urgency or "Média",
                "timestamp": datetime.fromisoformat(created_at),
            }
        )
    return history


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


def mock_diagnosis(machine_name: str, problem_desc: str) -> str:
    return (
        f"Diagnóstico simulado para '{machine_name}': o conjunto de rolamentos do "
        "eixo principal apresenta fadiga por vibração excessiva, possivelmente causada "
        "por desalinhamento no acoplamento e falta de lubrificação adequada. Recomenda-se "
        "parada programada para inspeção, substituição preventiva dos rolamentos e "
        "recalibração do alinhamento. Observação registrada: "
        f"{problem_desc.strip() or 'Sem observações adicionais.'}"
    )


def render_dashboard():
    st.title("Dashboard")
    st.caption("Visão geral rápida do status da manutenção e diagnósticos recentes.")

    total_diagnoses = len(st.session_state.history)
    last_diag = st.session_state.last_diagnosis

    col1, col2, col3 = st.columns(3)
    col1.metric("Diagnósticos na sessão", total_diagnoses)
    col2.metric("Máquina mais recente", last_diag["machine"] if last_diag else "—")
    col3.metric(
        "Última atualização",
        last_diag["timestamp"].strftime("%d/%m/%Y %H:%M") if last_diag else "—",
    )

    st.divider()

    st.subheader("Resumo do último diagnóstico")
    if not last_diag:
        st.info("Nenhum diagnóstico registrado ainda. Use a aba 'Novo Diagnóstico'.")
        return

    st.write(f"**Máquina:** {last_diag['machine']}")
    st.write(f"**Problema relatado:** {last_diag['problem']}")
    st.write(f"**Diagnóstico (mock):** {last_diag['diagnosis']}")

    st.subheader("Diagnósticos por máquina")
    bar_col, pie_col = st.columns(2)

    machine_counts = {}
    labels = {}
    for item in st.session_state.history:
        normalized = item["machine"].strip().lower()
        machine_counts[normalized] = machine_counts.get(normalized, 0) + 1
        labels.setdefault(normalized, item["machine"].strip())

    urgency_counts = {"Baixa": 0, "Média": 0, "Alta": 0}
    for item in st.session_state.history:
        urgency = item.get("urgency") or "Média"
        urgency_counts[urgency] = urgency_counts.get(urgency, 0) + 1

    if machine_counts:
        chart_df = pd.DataFrame(
            [
                {"machine": labels[name], "count": count}
                for name, count in machine_counts.items()
            ]
        ).sort_values("count", ascending=False)

        with bar_col:
            bar_fig = px.bar(
                chart_df,
                x="machine",
                y="count",
                color="machine",
                color_discrete_sequence=px.colors.qualitative.Vivid,
                labels={"machine": "Máquina", "count": "Diagnósticos"},
            )
            bar_fig.update_layout(showlegend=False, height=360, margin=dict(t=10, b=10))
            st.plotly_chart(bar_fig, use_container_width=True)

    with pie_col:
        pie_df = pd.DataFrame(
            [
                {"urgency": urgency, "count": count}
                for urgency, count in urgency_counts.items()
            ]
        )
        pie_fig = px.pie(
            pie_df,
            names="urgency",
            values="count",
            color="urgency",
            color_discrete_map={
                "Baixa": "#2ecc71",
                "Média": "#f1c40f",
                "Alta": "#e74c3c",
            },
        )
        pie_fig.update_layout(height=360, margin=dict(t=10, b=10))
        st.plotly_chart(pie_fig, use_container_width=True)


def render_new_diagnosis():
    st.title("Novo Diagnóstico")
    st.caption("Preencha os dados básicos para gerar um diagnóstico simulado.")

    with st.form("diagnosis_form", clear_on_submit=False):
        machine_name = st.text_input("Nome da máquina")
        problem_desc = st.text_area("Descrição do problema", height=140)
        urgency = st.selectbox("Nível de urgência", ["Baixa", "Média", "Alta"])
        submitted = st.form_submit_button("Processar diagnóstico")

    if submitted:
        if not machine_name.strip():
            st.error("Informe o nome da máquina para continuar.")
            return

        with st.spinner("Processando diagnóstico..."):
            time.sleep(0.8)

        diagnosis_text = mock_diagnosis(machine_name, problem_desc)
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

        st.success("Diagnóstico gerado com sucesso (mock).")
        st.write(diagnosis_text)


def render_history():
    st.title("Histórico")
    st.caption("Lista dos diagnósticos realizados nesta sessão.")

    if not st.session_state.history:
        st.info("Histórico vazio. Registre um novo diagnóstico.")
        return

    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["machine", "problem", "diagnosis", "timestamp"])
    for item in st.session_state.history:
        writer.writerow(
            [
                item["machine"],
                item["problem"],
                item["diagnosis"],
                item["timestamp"].isoformat(),
            ]
        )
    st.download_button(
        "Exportar CSV",
        data=csv_buffer.getvalue(),
        file_name="diagnosticos.csv",
        mime="text/csv",
    )

    for idx, item in enumerate(reversed(st.session_state.history), start=1):
        with st.expander(
            f"{idx}. {item['machine']} — {item['timestamp'].strftime('%d/%m/%Y %H:%M')}"
        ):
            st.write(f"**Problema relatado:** {item['problem'] or '—'}")
            st.write(f"**Diagnóstico (mock):** {item['diagnosis']}")


def main():
    init_state()
    if not st.session_state.history:
        st.session_state.history = load_history()
        if st.session_state.history:
            st.session_state.last_diagnosis = st.session_state.history[0]

    tabs = st.tabs(["Dashboard", "Novo Diagnóstico", "Histórico"])
    with tabs[0]:
        render_dashboard()
    with tabs[1]:
        render_new_diagnosis()
    with tabs[2]:
        render_history()


if __name__ == "__main__":
    main()
