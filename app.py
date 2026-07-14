import streamlit as st
from datetime import datetime, date
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
            'time_spent': (datetime.now() - self.start_time).total_seconds() // 60
        }


def save_state(state):
    for key, value in state.items():
        st.session_state[key] = value


def init_session():
    if 'checklist' not in st.session_state:
        st.session_state['checklist'] = None
    if 'extrato_lancamentos' not in st.session_state:
        st.session_state['extrato_lancamentos'] = []
    if 'extrato_pontos_concedidos' not in st.session_state:
        st.session_state['extrato_pontos_concedidos'] = 0


def render_extrato_tab(checklist):
    st.header("📄 Contabilizar Extrato Bancário")
    st.markdown("Registre os lançamentos do extrato bancário e ganhe pontos por cada entrada contabilizada.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Novo Lançamento")
        data_lancamento = st.date_input("Data", value=date.today(), key="ext_data")
        descricao = st.text_input("Descrição", placeholder="Ex: Pagamento fornecedor XYZ", key="ext_desc")
        tipo = st.selectbox("Tipo", ["Débito", "Crédito"], key="ext_tipo")
        valor = st.number_input("Valor (R$)", min_value=0.01, step=0.01, format="%.2f", key="ext_valor")
        conta_contabil = st.text_input("Conta Contábil", placeholder="Ex: 1.1.1.01", key="ext_conta")
        historico = st.text_area("Histórico Contábil", placeholder="Descreva o lançamento contábil...", key="ext_hist")

        if st.button("✅ Registrar Lançamento", use_container_width=True):
            if descricao and conta_contabil and historico:
                lancamento = {
                    'data': str(data_lancamento),
                    'descricao': descricao,
                    'tipo': tipo,
                    'valor': valor,
                    'conta_contabil': conta_contabil,
                    'historico': historico,
                    'registrado_em': datetime.now().strftime("%H:%M:%S")
                }
                st.session_state['extrato_lancamentos'].append(lancamento)

                # Concede 10 pontos por lançamento registrado
                pontos = 10
                checklist.points += pontos
                checklist.check_level_up()
                st.session_state['extrato_pontos_concedidos'] += pontos
                st.session_state['checklist'] = checklist

                st.success(f"Lançamento registrado! +{pontos} pontos")
                st.rerun()
            else:
                st.error("Preencha todos os campos obrigatórios: Descrição, Conta Contábil e Histórico.")

    with col2:
        st.subheader("Resumo do Extrato")
        lancamentos = st.session_state['extrato_lancamentos']

        if lancamentos:
            df = pd.DataFrame(lancamentos)
            total_debitos = df[df['tipo'] == 'Débito']['valor'].sum()
            total_creditos = df[df['tipo'] == 'Crédito']['valor'].sum()
            saldo = total_creditos - total_debitos

            m1, m2, m3 = st.columns(3)
            m1.metric("Débitos", f"R$ {total_debitos:,.2f}")
            m2.metric("Créditos", f"R$ {total_creditos:,.2f}")
            m3.metric("Saldo", f"R$ {saldo:,.2f}", delta=f"{saldo:+.2f}")

            st.metric("Pontos ganhos no extrato", f"🏆 {st.session_state['extrato_pontos_concedidos']}")

            st.subheader("Lançamentos Registrados")
            display_df = df[['data', 'descricao', 'tipo', 'valor', 'conta_contabil']].copy()
            display_df['valor'] = display_df['valor'].apply(lambda x: f"R$ {x:,.2f}")
            display_df.columns = ['Data', 'Descrição', 'Tipo', 'Valor', 'Conta Contábil']
            st.dataframe(display_df, use_container_width=True)

            if st.button("🗑️ Limpar Lançamentos", type="secondary"):
                st.session_state['extrato_lancamentos'] = []
                st.session_state['extrato_pontos_concedidos'] = 0
                st.rerun()
        else:
            st.info("Nenhum lançamento registrado ainda. Adicione o primeiro lançamento ao lado.")


def main():
    st.set_page_config(page_title="Workflow Contábil Gamificado", page_icon="🏆", layout="wide")
    init_session()

    st.title("🏆 Workflow Contábil Gamificado")

    # Sidebar: identificação
    with st.sidebar:
        st.header("👤 Identificação")
        user = st.text_input("Usuário", value="Contador", key="sb_user")
        company = st.text_input("Empresa", value="Empresa SA", key="sb_company")

        if st.button("Iniciar / Reiniciar Workflow"):
            checklist = GamifiedChecklist(user, company)
            tasks = [
                ("Verificar Período", 20),
                ("Usar Ferramenta", 20),
                ("Verificar Ajuste Histórico", 30),
                ("Conciliação Bancária", 40),
                ("Conciliação Fornecedor", 40),
                ("Análise do Balanço", 50),
            ]
            for name, pts in tasks:
                checklist.add_task(name, pts)
            st.session_state['checklist'] = checklist
            st.session_state['extrato_lancamentos'] = []
            st.session_state['extrato_pontos_concedidos'] = 0
            st.rerun()

        checklist = st.session_state.get('checklist')
        if checklist:
            status = checklist.get_status()
            st.divider()
            st.subheader("📊 Status")
            st.metric("Pontos", status['current_points'])
            st.metric("Nível", status['current_level'])
            st.metric("Tempo (min)", int(status['time_spent']))

    checklist = st.session_state.get('checklist')

    if not checklist:
        st.info("👈 Preencha seus dados na barra lateral e clique em **Iniciar Workflow** para começar.")
        return

    tab1, tab2 = st.tabs(["✅ Checklist de Tarefas", "📄 Contabilizar Extrato"])

    with tab1:
        st.header("Checklist de Tarefas")
        completed = 0
        for i, task in enumerate(checklist.tasks):
            col1, col2 = st.columns([4, 1])
            with col1:
                checked = st.checkbox(
                    task['name'],
                    value=task['completed'],
                    key=f"task_{i}",
                    disabled=task['completed']
                )
            with col2:
                st.write(f"+{task['points']} pts")

            if checked and not task['completed']:
                checklist.complete_task(i)
                st.session_state['checklist'] = checklist
                st.rerun()

            if task['completed']:
                completed += 1

        progress = completed / len(checklist.tasks) if checklist.tasks else 0
        st.progress(progress)
        st.write(f"Progresso: {int(progress * 100)}% Completo ({completed}/{len(checklist.tasks)} tarefas)")

        if progress == 1.0:
            st.success("🎉 Parabéns! Você completou todas as tarefas do workflow!")
            st.balloons()

    with tab2:
        render_extrato_tab(checklist)


if __name__ == "__main__":
    main()
