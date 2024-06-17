import streamlit as st
from datetime import datetime
import pandas as pd

# Classe para gerenciar o checklist gamificado
class GamifiedChecklist:
    def __init__(self, user, company):
        self.user = user
        self.company = company
        self.tasks = []
        self.points = 0
        self.level = 1
        self.start_time = datetime.now()

    def add_task(self, task_name, points):
        self.tasks.append({'name': task_name, 'completed': False, 'points': points})

    def complete_task(self, task_index):
        if not self.tasks[task_index]['completed']:
            self.tasks[task_index]['completed'] = True
            self.points += self.tasks[task_index]['points']
            self.check_level_up()

    def check_level_up(self):
        level_thresholds = {1: 100, 2: 200, 3: 300, 4: 400}
        for level, threshold in level_thresholds.items():
            if self.points >= threshold:
                self.level = level + 1

    def get_status(self):
        return {
            'user': self.user,
            'company': self.company,
            'current_points': self.points,
            'current_level': self.level,
            'time_spent': (datetime.now() - self.start_time).total_seconds() // 60  # Em minutos
        }

# Inicialização da aplicação Streamlit
st.title('Checklist Gamificado')

# Entrada de informações do usuário e da empresa
user = st.text_input('Usuário:')
company = st.text_input('Empresa:')

# Criação do objeto checklist
checklist = GamifiedChecklist(user, company)

# Adição de tarefas ao checklist
checklist.add_task('Coletor de Insumos', 20)
checklist.add_task('Mestre da Importação', 30)
checklist.add_task('Detetive Financeiro', 40)
# Adicione mais tarefas conforme necessário

# Interface para completar tarefas
for i, task in enumerate(checklist.tasks):
    if st.button(f"Completar: {task['name']}", key=i):
        checklist.complete_task(i)

# Exibição do status do usuário
status = checklist.get_status()
st.write(f"Usuário: {status['user']}")
st.write(f"Empresa: {status['company']}")
st.write(f"Pontos Atuais: {status['current_points']}")
st.write(f"Nível Atual: {status['current_level']}")
st.write(f"Tempo Gasto: {status['time_spent']} minutos")

# Rodar a aplicação com o comando abaixo no terminal
# streamlit run seu_arquivo.py
