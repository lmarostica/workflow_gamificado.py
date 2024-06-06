import streamlit as st

# Título do aplicativo
st.title('Workflow Contábil Gamificado')

# Lista de tarefas
tasks = [
    "Verificar Período",
    "Usar Ferramenta",
    "Verificar Ajuste Histórico",
    "Conciliação Bancária",
    "Conciliação Fornecedor",
    "Análise do Balanço"
]

# Dicionário para armazenar o estado das tarefas
task_status = {task: st.checkbox(task) for task in tasks}

# Cálculo do progresso
completed_tasks = sum(task_status.values())
total_tasks = len(tasks)
progress = completed_tasks / total_tasks * 100

# Exibir barra de progresso
st.progress(progress)
st.write(f"Progresso: {int(progress)}% Completo")

# Mensagem de congratulação
if progress == 100:
    st.success("Parabéns! Você completou todas as tarefas do workflow.")

# Elementos de gamificação
st.subheader("Gamificação")
if progress >= 50:
    st.balloons()
    st.write("Você atingiu 50% do progresso!")
if progress == 100:
    st.snow()
    st.write("Você completou 100% do workflow! 🏆")
