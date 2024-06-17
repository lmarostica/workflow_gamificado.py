import streamlit as st
from datetime import datetime

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

# Função para salvar o estado da sessão
def save_state(state):
    for key, value in state.items():
        st.session_state[key] = value

# Restante do código Streamlit...
