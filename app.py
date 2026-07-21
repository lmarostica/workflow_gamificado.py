import streamlit as st
from datetime import datetime

# ─────────────────────────────────────────────
# Modelo de dados
# ─────────────────────────────────────────────

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
            'time_spent': (datetime.now() - self.start_time).total_seconds() // 60,
        }


def save_state(state):
    for key, value in state.items():
        st.session_state[key] = value


# ─────────────────────────────────────────────
# Dados do workflow – Grupo Cobogó
# Industrializar o serviço de montagem de móveis
# ─────────────────────────────────────────────

ETAPAS = [
    {
        "titulo": "📦 Diagnóstico Atual",
        "descricao": "Mapear como a montagem é feita hoje para identificar gargalos.",
        "tarefas": [
            {"nome": "Levantar volume mensal de montagens realizadas", "pts": 20},
            {"nome": "Mapear tempo médio por tipo de móvel (guarda-roupa, cozinha, etc.)", "pts": 20},
            {"nome": "Identificar principais reclamações de clientes sobre montagem", "pts": 15},
            {"nome": "Calcular custo atual por montagem (mão de obra + deslocamento)", "pts": 20},
            {"nome": "Documentar quais etapas dependem exclusivamente de habilidade individual do montador", "pts": 25},
        ],
    },
    {
        "titulo": "🏭 Definição do Modelo Industrial",
        "descricao": "Desenhar como o serviço seria padronizado e escalado.",
        "tarefas": [
            {"nome": "Criar fichas técnicas por tipo de móvel (sequência de montagem passo a passo)", "pts": 30},
            {"nome": "Definir kit de ferramentas padrão por equipe de montagem", "pts": 20},
            {"nome": "Estabelecer tempo-padrão (takt time) para cada tipo de montagem", "pts": 25},
            {"nome": "Projetar modelo de célula de trabalho (1 coordenador + N montadores)", "pts": 30},
            {"nome": "Definir indicadores de qualidade: retrabalho, NPS, tempo de atendimento", "pts": 20},
        ],
    },
    {
        "titulo": "👥 Formação e Capacitação",
        "descricao": "Estruturar a formação de montadores como processo repetível.",
        "tarefas": [
            {"nome": "Criar trilha de treinamento básico (onboarding de novo montador em ≤ 5 dias)", "pts": 35},
            {"nome": "Gravar vídeos de referência para cada tipo de montagem", "pts": 30},
            {"nome": "Definir avaliação prática de competência antes de liberar montador para clientes", "pts": 25},
            {"nome": "Criar plano de carreira: montador Jr → Sênior → Coordenador de equipe", "pts": 20},
            {"nome": "Estruturar remuneração variável atrelada a NPS e produtividade", "pts": 25},
        ],
    },
    {
        "titulo": "📱 Tecnologia e Rastreamento",
        "descricao": "Ferramentas para escalar sem perder controle de qualidade.",
        "tarefas": [
            {"nome": "Implantar sistema de agendamento online de montagem", "pts": 30},
            {"nome": "Criar checklist digital por montagem (app ou formulário Google)", "pts": 25},
            {"nome": "Registrar foto de antes/depois de cada montagem", "pts": 15},
            {"nome": "Monitorar deslocamento e tempo em campo via app", "pts": 20},
            {"nome": "Integrar avaliação pós-serviço automática para o cliente", "pts": 25},
        ],
    },
    {
        "titulo": "💰 Viabilidade Financeira",
        "descricao": "Validar se o modelo industrial é economicamente sustentável.",
        "tarefas": [
            {"nome": "Projetar ponto de equilíbrio: quantas montagens/mês para cobrir custos fixos", "pts": 35},
            {"nome": "Comparar margem por montagem: modelo atual vs. modelo industrializado", "pts": 30},
            {"nome": "Calcular investimento necessário (ferramentas, tecnologia, treinamento)", "pts": 25},
            {"nome": "Identificar nichos de maior margem (montagem express, grandes construtoras, e-commerce)", "pts": 30},
            {"nome": "Simular cenário de franquia ou licenciamento do modelo para outras cidades", "pts": 40},
        ],
    },
    {
        "titulo": "🚀 Piloto e Validação",
        "descricao": "Testar o modelo em pequena escala antes de escalar.",
        "tarefas": [
            {"nome": "Escolher 1 tipo de móvel e 1 equipe para o piloto", "pts": 20},
            {"nome": "Executar 20 montagens sob o modelo industrializado", "pts": 30},
            {"nome": "Medir desvio de tempo real vs. tempo-padrão", "pts": 25},
            {"nome": "Coletar NPS das 20 montagens piloto", "pts": 20},
            {"nome": "Documentar aprendizados e ajustar as fichas técnicas", "pts": 35},
            {"nome": "Decisão GO/NO-GO: escalar ou pivotar o modelo", "pts": 50},
        ],
    },
]

NIVEIS = {
    1:  (0,   100,  "🔩 Aprendiz de Montador"),
    2:  (100, 250,  "🪛 Montador Iniciante"),
    3:  (250, 450,  "🪚 Montador Experiente"),
    4:  (450, 700,  "⚙️  Técnico de Produção"),
    5:  (700, 1000, "🏭 Supervisor Industrial"),
    6:  (1000, 9999, "🏆 Diretor de Operações"),
}


def get_nivel(pts):
    for lvl, (lo, hi, nome) in NIVEIS.items():
        if lo <= pts < hi:
            return lvl, nome, lo, hi
    return 6, NIVEIS[6][2], NIVEIS[6][0], NIVEIS[6][1]


# ─────────────────────────────────────────────
# Inicialização da sessão
# ─────────────────────────────────────────────

def init_session():
    if "cobogo_pts" not in st.session_state:
        st.session_state.cobogo_pts = 0
    if "cobogo_tasks" not in st.session_state:
        tasks = {}
        for i, etapa in enumerate(ETAPAS):
            for j, t in enumerate(etapa["tarefas"]):
                tasks[f"{i}_{j}"] = False
        st.session_state.cobogo_tasks = tasks
    if "cobogo_inicio" not in st.session_state:
        st.session_state.cobogo_inicio = datetime.now().strftime("%d/%m/%Y %H:%M")


def toggle_task(key, pts):
    current = st.session_state.cobogo_tasks.get(key, False)
    if not current:
        st.session_state.cobogo_tasks[key] = True
        st.session_state.cobogo_pts += pts
    else:
        st.session_state.cobogo_tasks[key] = False
        st.session_state.cobogo_pts -= pts


# ─────────────────────────────────────────────
# Interface principal
# ─────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Grupo Cobogó – Industrializar Montagem",
        page_icon="🏭",
        layout="wide",
    )

    init_session()

    # Cabeçalho
    st.title("🏭 Grupo Cobogó")
    st.subheader("Workflow Gamificado: Industrializar o Serviço de Montagem de Móveis")
    st.markdown(
        """
        > **Por que não pivotar?**
        > A montagem de móveis é hoje um serviço artesanal, dependente de habilidade individual e difícil de escalar.
        > Industrializá-la significa transformar cada montagem em um processo repetível, previsível e lucrativo —
        > reduzindo o tempo de execução, eliminando retrabalho e abrindo caminho para crescimento sem perder qualidade.
        """
    )
    st.divider()

    # Painel de status
    pts = st.session_state.cobogo_pts
    lvl, nome_lvl, lo, hi = get_nivel(pts)
    total_tasks = sum(len(e["tarefas"]) for e in ETAPAS)
    done_tasks = sum(1 for v in st.session_state.cobogo_tasks.values() if v)
    pct_tasks = int(done_tasks / total_tasks * 100) if total_tasks else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🏅 Pontos", pts)
    col2.metric("🎯 Nível", f"{lvl} – {nome_lvl}")
    col3.metric("✅ Tarefas concluídas", f"{done_tasks}/{total_tasks}")
    col4.metric("📊 Progresso geral", f"{pct_tasks}%")

    # Barra de progresso até o próximo nível
    if hi < 9999:
        progresso_nivel = max(0, pts - lo) / (hi - lo)
        st.progress(min(progresso_nivel, 1.0), text=f"Progresso até o próximo nível ({hi} pts)")
    else:
        st.progress(1.0, text="Nível máximo atingido! 🏆")

    st.divider()

    # Etapas
    for i, etapa in enumerate(ETAPAS):
        tarefas_concluidas = sum(
            1 for j in range(len(etapa["tarefas"]))
            if st.session_state.cobogo_tasks.get(f"{i}_{j}", False)
        )
        total_etapa = len(etapa["tarefas"])
        pct_etapa = int(tarefas_concluidas / total_etapa * 100)

        with st.expander(
            f"{etapa['titulo']}  —  {tarefas_concluidas}/{total_etapa} tarefas  ({pct_etapa}%)",
            expanded=(tarefas_concluidas < total_etapa),
        ):
            st.caption(etapa["descricao"])
            st.progress(pct_etapa / 100)

            for j, tarefa in enumerate(etapa["tarefas"]):
                key = f"{i}_{j}"
                concluida = st.session_state.cobogo_tasks.get(key, False)
                label = f"{'~~' if concluida else ''}{tarefa['nome']}{'~~' if concluida else ''} &nbsp; `+{tarefa['pts']} pts`"
                if st.checkbox(
                    tarefa["nome"],
                    value=concluida,
                    key=f"cb_{key}",
                    help=f"+{tarefa['pts']} pontos",
                ):
                    if not concluida:
                        toggle_task(key, tarefa["pts"])
                        st.rerun()
                else:
                    if concluida:
                        toggle_task(key, tarefa["pts"])
                        st.rerun()

    st.divider()

    # Argumentos estratégicos (sidebar)
    with st.sidebar:
        st.header("💡 Por que industrializar?")
        st.markdown("""
**1. Escalabilidade**
Hoje o crescimento depende de encontrar montadores experientes. Com processos padronizados, qualquer pessoa treinada em 5 dias executa com a mesma qualidade.

**2. Redução de custos**
Fichas técnicas e tempo-padrão eliminam improvisos que geram retrabalho — principal vilão da margem.

**3. Previsibilidade para o cliente**
Prazo e resultado previsíveis aumentam NPS e geram indicações.

**4. Barreira competitiva**
Um sistema de montagem proprietário é difícil de copiar. Cria um ativo intangível valioso.

**5. Novas receitas**
Modelo industrializado abre portas para: contratos B2B com construtoras, parcerias com e-commerce de móveis e franqueamento do serviço.

**6. Valorização da equipe**
Plano de carreira claro e remuneração variável reduzem rotatividade e aumentam engajamento.
        """)

        st.divider()
        st.caption(f"Sessão iniciada em {st.session_state.cobogo_inicio}")

    # Conquistas
    st.subheader("🏆 Conquistas")
    badges = []
    if pts >= 100:
        badges.append("🔩 Diagnóstico iniciado")
    if pts >= 250:
        badges.append("🗺️ Modelo desenhado")
    if pts >= 450:
        badges.append("🎓 Time capacitado")
    if pts >= 700:
        badges.append("📱 Tecnologia implantada")
    if pts >= 1000:
        badges.append("✅ Piloto validado")
    if done_tasks == total_tasks:
        badges.append("🚀 INDUSTRIALIZAÇÃO COMPLETA!")

    if badges:
        st.write("  |  ".join(badges))
    else:
        st.info("Complete tarefas para desbloquear conquistas.")

    if done_tasks == total_tasks:
        st.balloons()
        st.success("🎉 Parabéns! O serviço de montagem do Grupo Cobogó está industrializado e pronto para escalar!")


if __name__ == "__main__":
    main()
