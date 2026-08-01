import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------------
# Persistência em arquivo JSON — substitui a planilha de controle
# ----------------------------------------------------------------------------
DATA_FILE = os.path.join(os.path.dirname(__file__), "workflows.json")

# Modelo padrão de tarefas do fechamento contábil mensal
DEFAULT_TASKS = [
    {"name": "Importar extratos bancários", "points": 10},
    {"name": "Conciliação bancária", "points": 20},
    {"name": "Lançamentos de notas fiscais (entradas/saídas)", "points": 20},
    {"name": "Integração da folha de pagamento", "points": 15},
    {"name": "Apuração de impostos (DAS/PIS/COFINS/ISS/ICMS)", "points": 25},
    {"name": "Conciliação de contas patrimoniais", "points": 20},
    {"name": "Revisão do balancete", "points": 25},
    {"name": "Geração de guias e envio ao cliente", "points": 15},
    {"name": "Entrega de obrigações acessórias", "points": 20},
    {"name": "Arquivamento dos documentos do mês", "points": 10},
]

LEVEL_THRESHOLDS = [0, 50, 100, 150, 200]

BADGES = {
    0.25: "🥉 Começou bem!",
    0.50: "🥈 Metade do caminho!",
    0.75: "🥇 Quase lá!",
    1.00: "🏆 Fechamento concluído!",
}


class GamifiedChecklist:
    """Checklist gamificado de fechamento contábil de uma empresa/competência."""

    def __init__(self, user, company, competencia, tasks=None, start_time=None):
        self.user = user
        self.company = company
        self.competencia = competencia
        self.tasks = tasks if tasks is not None else [
            {"name": t["name"], "completed": False, "points": t["points"]}
            for t in DEFAULT_TASKS
        ]
        self.start_time = start_time or datetime.now().isoformat(timespec="seconds")

    # -- Pontuação -----------------------------------------------------------
    @property
    def points(self):
        return sum(t["points"] for t in self.tasks if t["completed"])

    @property
    def total_points(self):
        return sum(t["points"] for t in self.tasks)

    @property
    def level(self):
        level = 1
        for i, threshold in enumerate(LEVEL_THRESHOLDS):
            if self.points >= threshold:
                level = i + 1
        return level

    @property
    def progress(self):
        return self.points / self.total_points if self.total_points else 0.0

    # -- Ações ---------------------------------------------------------------
    def add_task(self, task_name, points):
        self.tasks.append({"name": task_name, "completed": False, "points": points})

    def set_task(self, task_index, completed):
        if 0 <= task_index < len(self.tasks):
            self.tasks[task_index]["completed"] = completed

    def get_status(self):
        elapsed = datetime.now() - datetime.fromisoformat(self.start_time)
        return {
            "user": self.user,
            "company": self.company,
            "competencia": self.competencia,
            "current_points": self.points,
            "total_points": self.total_points,
            "current_level": self.level,
            "progress": self.progress,
            "time_spent_min": int(elapsed.total_seconds() // 60),
        }

    # -- Serialização --------------------------------------------------------
    def to_dict(self):
        return {
            "user": self.user,
            "company": self.company,
            "competencia": self.competencia,
            "tasks": self.tasks,
            "start_time": self.start_time,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            user=data["user"],
            company=data["company"],
            competencia=data["competencia"],
            tasks=data["tasks"],
            start_time=data.get("start_time"),
        )


# ----------------------------------------------------------------------------
# Camada de dados
# ----------------------------------------------------------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def workflow_key(company, competencia):
    return f"{company}|{competencia}"


# ----------------------------------------------------------------------------
# Interface Streamlit
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Workflow Contábil Gamificado", page_icon="📊", layout="wide")
st.title("📊 Workflow Contábil Gamificado")
st.caption("Checklist de fechamento mensal por empresa — substitui a planilha de controle.")

data = load_data()

with st.sidebar:
    st.header("⚙️ Fechamento")
    user = st.text_input("Responsável", value="Lucas")
    company = st.text_input("Empresa", placeholder="Nome do cliente")
    today = datetime.now()
    competencia = st.text_input("Competência (MM/AAAA)", value=f"{today.month:02d}/{today.year}")

    if st.button("Abrir / criar fechamento", type="primary", disabled=not company.strip()):
        key = workflow_key(company.strip(), competencia.strip())
        if key not in data:
            checklist = GamifiedChecklist(user.strip(), company.strip(), competencia.strip())
            data[key] = checklist.to_dict()
            save_data(data)
        st.session_state["active_key"] = key

    st.divider()
    st.header("➕ Tarefa extra")
    new_task = st.text_input("Descrição da tarefa")
    new_points = st.number_input("Pontos", min_value=5, max_value=50, value=10, step=5)

tab_checklist, tab_panel = st.tabs(["✅ Checklist", "📋 Painel geral"])

with tab_checklist:
    active_key = st.session_state.get("active_key")
    if not active_key or active_key not in data:
        st.info("Informe a empresa e a competência na barra lateral e clique em **Abrir / criar fechamento**.")
    else:
        checklist = GamifiedChecklist.from_dict(data[active_key])

        if st.sidebar.button("Adicionar tarefa", disabled=not new_task.strip()):
            checklist.add_task(new_task.strip(), int(new_points))
            data[active_key] = checklist.to_dict()
            save_data(data)
            st.rerun()

        status = checklist.get_status()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Empresa", status["company"])
        col2.metric("Pontos", f"{status['current_points']} / {status['total_points']}")
        col3.metric("Nível", status["current_level"])
        col4.metric("Tempo decorrido", f"{status['time_spent_min']} min")

        st.progress(status["progress"], text=f"Progresso do fechamento {status['competencia']}: {status['progress']:.0%}")

        for pct, badge in BADGES.items():
            if status["progress"] >= pct:
                earned = badge
        if status["progress"] >= 0.25:
            st.success(earned)
        if status["progress"] >= 1.0:
            st.balloons()

        st.subheader("Tarefas do fechamento")
        changed = False
        for i, task in enumerate(checklist.tasks):
            checked = st.checkbox(
                f"{task['name']}  —  {task['points']} pts",
                value=task["completed"],
                key=f"{active_key}::{i}",
            )
            if checked != task["completed"]:
                checklist.set_task(i, checked)
                changed = True
        if changed:
            data[active_key] = checklist.to_dict()
            save_data(data)
            st.rerun()

with tab_panel:
    st.subheader("Situação de todos os fechamentos")
    if not data:
        st.info("Nenhum fechamento cadastrado ainda.")
    else:
        rows = []
        for key, wf in data.items():
            status = GamifiedChecklist.from_dict(wf).get_status()
            rows.append(
                {
                    "Empresa": status["company"],
                    "Competência": status["competencia"],
                    "Responsável": status["user"],
                    "Pontos": f"{status['current_points']}/{status['total_points']}",
                    "Nível": status["current_level"],
                    "Progresso": f"{status['progress']:.0%}",
                    "Concluído": "✅" if status["progress"] >= 1.0 else "🔄",
                }
            )
        df = pd.DataFrame(rows).sort_values(["Competência", "Empresa"]).reset_index(drop=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Exportar painel (CSV)", csv, "painel_fechamentos.csv", "text/csv")
