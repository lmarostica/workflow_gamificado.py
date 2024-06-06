import streamlit as st
import time
import pandas as pd
import os

# Função para carregar os dados do ranking
def load_data():
    if os.path.exists('ranking.csv'):
        return pd.read_csv('ranking.csv')
    else:
        return pd.DataFrame(columns=['User', 'Step', 'Task', 'Start Time', 'End Time', 'Duration'])

# Função para salvar os dados do ranking
def save_data(data):
    data.to_csv('ranking.csv', index=False)

# Interface de Login
st.title('Workflow Contábil Gamificado')
user = st.text_input("Digite seu nome para iniciar o workflow")

if user:
    # Carregar dados do ranking
    data = load_data()

    # Etapas e checklists
    steps = {
        "Verificar Período a Ser Lançado e Existência de Lançamentos na Conta Banco": [
            "Identificar o período contábil necessário.",
            "Verificar lançamentos contábeis existentes na conta bancária para o período.",
            "Comparar extrato bancário com lançamentos contábeis."
        ],
        "Usar Ferramenta Mister Contador / Visão Lógica de Acordo com Cliente": [
            "Selecionar a ferramenta contábil apropriada (Mister Contador ou Visão Lógica).",
            "Garantir uso eficaz das funcionalidades da ferramenta.",
            "Realizar treinamentos regulares para o uso das ferramentas.",
            "Utilizar guias de referência rápida e tutoriais.",
            "Acessar suporte técnico conforme necessário."
        ],
        "Verificar Necessidade de Ajuste no Histórico do Extrato Bancário": [
            "Revisar o extrato bancário.",
            "Identificar e corrigir inconsistências ou ajustes necessários nos históricos dos lançamentos.",
            "Confirmar ajustes corretos no sistema contábil."
        ],
        "Após Importação, Fazer Conciliação Bancária no Único": [
            "Realizar conciliação bancária no sistema Único.",
            "Comparar lançamentos contábeis com registros do extrato bancário.",
            "Garantir que todas as transações foram conciliadas corretamente.",
            "Gerar relatórios detalhados de conciliação."
        ],
        "Fazer Conciliação de Fornecedor pelo Processo de Conciliador": [
            "Realizar conciliação de registros de fornecedores.",
            "Assegurar que registros de pagamento e recebimento estão corretos.",
            "Conferir todas as transações e resolver discrepâncias.",
            "Utilizar portal de fornecedores para confirmação de registros."
        ],
        "Análise do Balanço": [
            "Impostos a pagar/recuperar, receita/deduções da receita.",
            "Distribuição de lucros/lucro disponível ou acumulado.",
            "Verificação das despesas e fornecedores.",
            "Parcelamentos de impostos; empréstimos."
        ]
    }

    # Função para calcular o progresso
    def calculate_progress(tasks):
        completed_tasks = sum(tasks.values())
        total_tasks = len(tasks)
        return completed_tasks / total_tasks

    # Função para registrar o tempo da tarefa
    def record_time(user, step, task, start_time):
        end_time = time.time()
        duration = end_time - start_time
        new_row = {
            'User': user,
            'Step': step,
            'Task': task,
            'Start Time': start_time,
            'End Time': end_time,
            'Duration': duration
        }
        global data
        data = data.append(new_row, ignore_index=True)
        save_data(data)

    # Dicionário para armazenar o estado das tarefas
    task_status = {}
    start_times = {}

    for step, tasks in steps.items():
        st.subheader(step)
        for task in tasks:
            if st.checkbox(task, key=f"{step}_{task}"):
                if f"{step}_{task}" not in start_times:
                    start_times[f"{step}_{task}"] = time.time()
                record_time(user, step, task, start_times[f"{step}_{task}"])
            task_status[step] = {task: st.checkbox(task, key=f"{step}_{task}_status") for task in tasks}

    # Cálculo do progresso por etapa
    progress_by_step = {step: calculate_progress(tasks) for step, tasks in task_status.items()}

    # Exibir barra de progresso por etapa
    for step, progress in progress_by_step.items():
        st.write(f"Progresso da etapa '{step}': {int(progress * 100)}% Completo")
        st.progress(progress)

    # Cálculo do progresso geral
    overall_progress = sum(progress_by_step.values()) / len(progress_by_step)
    st.write(f"Progresso geral: {int(overall_progress * 100)}% Completo")
    st.progress(overall_progress)

    # Mensagem de congratulação
    if overall_progress == 1:
        st.success("Parabéns! Você completou todas as etapas do workflow.")

    # Elementos de gamificação
    st.subheader("Gamificação")
    if overall_progress >= 0.5:
        st.balloons()
        st.write("Você atingiu 50% do progresso!")
    if overall_progress == 1:
        st.snow()
        st.write("Você completou 100% do workflow! 🏆")

    # Exibir ranking
    st.subheader("Ranking")
    ranking = data.groupby('User')['Duration'].sum().sort_values().reset_index()
    ranking['Rank'] = ranking['Duration'].rank(method='min')
    st.dataframe(ranking)

    # Mostrar posição do usuário
    user_rank = ranking[ranking['User'] == user]['Rank'].values[0]
    st.write(f"{user}, você está na posição {int(user_rank)} no ranking.")


