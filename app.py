import streamlit as st
from datetime import datetime

# Classe para gerenciar o checklist gamificado
class GamifiedChecklist:
    # ... (mantenha os métodos existentes da classe aqui)

# Função para salvar o estado da sessão
def save_state(state):
    for key, value in state.items():
        st.session_state[key] = value

# Inicialização da aplicação Streamlit
st.title('Checklist Gamificado')

# Inicialização do estado da sessão, se necessário
if 'checklist' not in st.session_state:
    st.session_state['checklist'] = GamifiedChecklist('Usuário', 'Empresa')

# Entrada de informações do usuário e da empresa
user = st.text_input('Usuário:', key='user_input')
company = st.text_input('Empresa:', key='company_input')

# Atualização do usuário e da empresa no objeto checklist
st.session_state['checklist'].user = user
st.session_state['checklist'].company = company

# Interface para completar tarefas
for i, task in enumerate(st.session_state['checklist'].tasks):
    if st.button(f"Completar: {task['name']}", key=f'task_{i}'):
        st.session_state['checklist'].complete_task(i)
        save_state({'checklist': st.session_state['checklist']})

# Exibição do status do usuário
status = st.session_state['checklist'].get_status()
st.write(f"Usuário: {status['user']}")
st.write(f"Empresa: {status['company']}")
st.write(f"Pontos Atuais: {status['current_points']}")
st.write(f"Nível Atual: {status['current_level']}")
st.write(f"Tempo Gasto: {status['time_spent']} minutos")

