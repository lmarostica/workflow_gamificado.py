import streamlit as st

# Título do aplicativo
st.title('Workflow Contábil Gamificado')

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

# Dicionário para armazenar o estado das tarefas
task_status = {}
for step, tasks in steps.items():
    st.subheader(step)
    task_status[step] = {task: st.checkbox(task) for task in tasks}

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
