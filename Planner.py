import streamlit as st
import datetime
import json
import os
import hashlib
import io
import csv
import contextlib
import re

def gerar_hash(senha):
    return hashlib.sha256(senha.encode('utf-8')).hexdigest()

def validar_regras_senha(senha):
    if len(senha) < 8: return False, "A senha deve ter pelo menos 8 caracteres."
    if not re.search(r'[A-Z]', senha): return False, "A senha deve ter pelo menos 1 letra maiúscula."
    if not re.search(r'[a-z]', senha): return False, "A senha deve ter pelo menos 1 letra minúscula."
    if not re.search(r'\d', senha): return False, "A senha deve ter pelo menos 1 número."
    if re.search(r'(\d)\1', senha): return False, "O mesmo número não pode se repetir em sequência (ex: 11, 22)."
    return True, "Senha válida"

# ==========================================
# CAMADA DE DADOS E REGRA DE NEGÓCIO
# ==========================================
class Usuario:
    def __init__(self, nome, email, funcao, senha_hash, nivel_acesso="Membro"):
        self._nome = nome
        self._email = email
        self._funcao = funcao
        self._senha_hash = senha_hash
        self._nivel_acesso = nivel_acesso

    def get_nome(self): return self._nome
    def get_email(self): return self._email
    def get_funcao(self): return self._funcao
    def get_nivel(self): return self._nivel_acesso
    
    def verificar_senha(self, senha_texto): return self._senha_hash == gerar_hash(senha_texto)
    def set_senha(self, nova_senha_hash): self._senha_hash = nova_senha_hash
    def set_nivel(self, novo_nivel): self._nivel_acesso = novo_nivel

class Tarefa:
    def __init__(self, titulo, descricao, prioridade, prazo, criador, responsavel=None, status="A Fazer", data_conclusao=None, data_criacao=None, tempo_focado=0.0):
        self._titulo = titulo
        self._descricao = descricao
        self._prioridade = prioridade
        self._prazo = prazo if isinstance(prazo, datetime.date) else datetime.date.fromisoformat(str(prazo))
        self._criador = criador
        self._responsavel = responsavel
        self._status = status
        self._data_conclusao = data_conclusao
        self._data_criacao = data_criacao if data_criacao else datetime.date.today().isoformat()
        self._tempo_focado = float(tempo_focado)

    def atribuir_responsavel(self, usuario): self._responsavel = usuario
    def get_status(self): return self._status
    def get_responsavel(self): return self._responsavel
    def get_titulo(self): return self._titulo
    def get_criador(self): return self._criador
    def get_data_conclusao(self): return self._data_conclusao
    def get_data_criacao(self): return self._data_criacao
    def get_tempo_focado(self): return self._tempo_focado

    def set_criador(self, novo_criador): self._criador = novo_criador
    def set_prazo(self, novo_prazo): self._prazo = novo_prazo if isinstance(novo_prazo, datetime.date) else datetime.date.fromisoformat(str(novo_prazo))
    def set_tempo_focado(self, novo_tempo): self._tempo_focado = float(novo_tempo)

    def set_status(self, novo_status): 
        self._status = novo_status
        if novo_status == "Concluído":
            self._data_conclusao = datetime.date.today().isoformat()
        else:
            self._data_conclusao = None

class GestorTaskFlow:
    def __init__(self):
        self._usuarios = []
        self._tarefas = []
        self._config = {"tipo": "Imagem", "valor": "https://images.unsplash.com/photo-1557683316-973673baf926?q=80&w=2000&auto=format&fit=crop"}
        self.arq_usuarios = 'usuarios.json'
        self.arq_tarefas = 'tarefas.json'
        self.arq_config = 'config.json'
        self._carregar_dados()

    def _carregar_dados(self):
        self._usuarios = []
        self._tarefas = []
        # Carrega Configurações de UI
        if os.path.exists(self.arq_config):
            with open(self.arq_config, 'r', encoding='utf-8') as f:
                self._config = json.load(f)

        # Carrega Usuários
        if os.path.exists(self.arq_usuarios):
            with open(self.arq_usuarios, 'r', encoding='utf-8') as f:
                for d in json.load(f):
                    self._usuarios.append(Usuario(d['nome'], d['email'], d['funcao'], d['senha'], d.get('nivel', 'Membro')))
        else:
            self.cadastrar_usuario("José Nita", "jose@email.com", "Desenvolvedor", "Administrador")

        # Carrega Tarefas
        if os.path.exists(self.arq_tarefas):
            with open(self.arq_tarefas, 'r', encoding='utf-8') as f:
                for d in json.load(f):
                    resp = next((u for u in self._usuarios if u.get_nome() == d['responsavel']), None)
                    t = Tarefa(d['titulo'], d['descricao'], d['prioridade'], d['prazo'], d.get('criador', 'Sistema'), resp, d['status'], d.get('data_conclusao'), d.get('data_criacao'), d.get('tempo_focado', 0.0))
                    self._tarefas.append(t)

    def _salvar_usuarios(self):
        dados = [{"nome": u.get_nome(), "email": u.get_email(), "funcao": u.get_funcao(), "senha": u._senha_hash, "nivel": u.get_nivel()} for u in self._usuarios]
        with open(self.arq_usuarios, 'w', encoding='utf-8') as f: json.dump(dados, f, ensure_ascii=False, indent=4)

    def _salvar_tarefas(self):
        dados = []
        for t in self._tarefas:
            resp_nome = t.get_responsavel().get_nome() if t.get_responsavel() else None
            dados.append({"titulo": t.get_titulo(), "descricao": t._descricao, "prioridade": t._prioridade, "prazo": str(t._prazo), "criador": t.get_criador(), "data_criacao": t.get_data_criacao(), "tempo_focado": t.get_tempo_focado(), "responsavel": resp_nome, "status": t.get_status(), "data_conclusao": t.get_data_conclusao()})
        with open(self.arq_tarefas, 'w', encoding='utf-8') as f: json.dump(dados, f, ensure_ascii=False, indent=4)

    def salvar_config(self, tipo, valor):
        self._config = {"tipo": tipo, "valor": valor}
        with open(self.arq_config, 'w', encoding='utf-8') as f: json.dump(self._config, f, ensure_ascii=False, indent=4)

    def get_config(self): return self._config

    def cadastrar_usuario(self, nome, email, funcao, nivel_acesso, senha_texto=None):
        senha_hash = gerar_hash(senha_texto) if senha_texto else "PENDENTE"
        u = Usuario(nome, email, funcao, senha_hash, nivel_acesso)
        self._usuarios.append(u)
        self._salvar_usuarios()
        return u

    def definir_senha_usuario(self, email, nova_senha):
        for u in self._usuarios:
            if u.get_email() == email:
                u.set_senha(gerar_hash(nova_senha))
                self._salvar_usuarios()
                return u
        return None

    def remover_usuario(self, nome_usuario):
        self._usuarios = [u for u in self._usuarios if u.get_nome() != nome_usuario]
        self._salvar_usuarios()
        for t in self._tarefas:
            if t.get_responsavel() and t.get_responsavel().get_nome() == nome_usuario:
                t.atribuir_responsavel(None)
        self._salvar_tarefas()

    def alterar_nivel_usuario(self, nome_usuario, novo_nivel):
        for u in self._usuarios:
            if u.get_nome() == nome_usuario:
                u.set_nivel(novo_nivel)
                self._salvar_usuarios()
                return True
        return False

    def validar_login(self, email, senha):
        email_limpo = email.strip().lower()
        for u in self._usuarios:
            if u.get_email() == email_limpo:
                if u._senha_hash == "PENDENTE": return "PENDENTE"
                if u.verificar_senha(senha.strip()): return u
        return None

    def cadastrar_tarefa(self, titulo, descricao, prioridade, prazo, criador, responsavel=None):
        t = Tarefa(titulo, descricao, prioridade, prazo, criador, responsavel)
        self._tarefas.append(t)
        self._salvar_tarefas()
        return t

    def atualizar_status_tarefa(self, titulo, novo_status):
        for t in self._tarefas:
            if t.get_titulo() == titulo:
                t.set_status(novo_status)
                self._salvar_tarefas()
                break

    def alterar_detalhes_tarefa(self, titulo, novo_criador, novo_prazo, novo_responsavel, novo_tempo):
        for t in self._tarefas:
            if t.get_titulo() == titulo:
                t.set_criador(novo_criador)
                t.set_prazo(novo_prazo)
                t.set_tempo_focado(novo_tempo)
                t.atribuir_responsavel(novo_responsavel)
                self._salvar_tarefas()
                break

    def remover_tarefa(self, titulo_tarefa):
        self._tarefas = [t for t in self._tarefas if t.get_titulo() != titulo_tarefa]
        self._salvar_tarefas()

    def get_todos_usuarios(self): return self._usuarios
    def get_todas_tarefas(self): return self._tarefas

# ==========================================
# CAMADA DE APRESENTAÇÃO WEB (Streamlit)
# ==========================================
st.set_page_config(page_title="TaskFlow - Gestão", layout="wide")

if 'gestor' not in st.session_state: st.session_state['gestor'] = GestorTaskFlow()
g = st.session_state['gestor']

# --- APLICAÇÃO DINÂMICA DO BACKGROUND (CSS) ---
config_atual = g.get_config()
if config_atual['tipo'] == 'Cor':
    fundo_css = f"background-color: {config_atual['valor']};"
else:
    fundo_css = f"background-image: url('{config_atual['valor']}'); background-size: cover; background-attachment: fixed;"

css_customizado = f"""
<style>
[data-testid="stAppViewContainer"] {{
    {fundo_css}
}}
[data-testid="stAppViewBlockContainer"] {{
    background-color: rgba(14, 17, 23, 0.85); 
    padding-top: 2rem;
    padding-bottom: 2rem;
    border-radius: 10px;
    margin-top: 2rem;
}}
[data-testid="stSidebar"] {{
    background-color: rgba(14, 17, 23, 0.95);
}}
</style>
"""
st.markdown(css_customizado, unsafe_allow_html=True)

MAPA_PRIORIDADE = {"Alta": "❗ Alta", "Média": "⚠️ Média", "Baixa": "⬇️ Baixa"}

def cor_borda_prioridade(prioridade):
    if prioridade == "Alta": return "#ff4b4b"
    elif prioridade == "Média": return "#ffa500"
    return "#4b8bff"

if 'usuario_logado' not in st.session_state: st.session_state['usuario_logado'] = None
if 'nivel_logado' not in st.session_state: st.session_state['nivel_logado'] = None

# ------------------------------------------
# TELA DE LOGIN
# ------------------------------------------
if st.session_state['usuario_logado'] is None:
    st.title("🔒 Acesso ao TaskFlow")
    
    aba_login, aba_primeiro_acesso = st.tabs(["Fazer Login", "Primeiro Acesso (Novo Usuário)"])
    
    with aba_login:
        st.write("Insira suas credenciais para acessar o sistema.")
        with st.form("form_login"):
            email_digitado = st.text_input("E-mail", key="login_email_input")
            senha_digitada = st.text_input("Senha", type="password", key="login_senha_input") 
            if st.form_submit_button("Entrar", type="primary"):
                resultado = g.validar_login(email_digitado, senha_digitada)
                
                if resultado == "PENDENTE":
                    st.warning("⚠️ Este é o seu primeiro acesso! Vá para a aba 'Primeiro Acesso (Novo Usuário)' para criar sua senha.")
                elif resultado and resultado != "PENDENTE":
                    st.session_state['usuario_logado'] = resultado.get_nome()
                    st.session_state['nivel_logado'] = resultado.get_nivel()
                    st.rerun()
                else:
                    st.error(f"Incorreto! O Sistema leu E-MAIL: '{email_digitado}' | Senha: '{senha_digitada}'")

    with aba_primeiro_acesso:
        st.write("Se o seu Administrador já cadastrou o seu E-mail, crie sua senha de acesso abaixo:")
        with st.form("form_primeiro_acesso"):
            email_pa = st.text_input("E-mail cadastrado")
            st.markdown("*A senha deve ter pelo menos 8 dígitos, contendo 1 maiúscula, 1 minúscula e 1 número (sem ser repetido na sequência).*")
            senha_pa = st.text_input("Crie sua Senha", type="password")
            senha_pa2 = st.text_input("Confirme sua Senha", type="password")
            
            if st.form_submit_button("Criar Senha e Entrar", type="primary"):
                u_encontrado = next((u for u in g.get_todos_usuarios() if u.get_email() == email_pa), None)
                if not u_encontrado:
                    st.error("E-mail não encontrado no sistema.")
                elif u_encontrado._senha_hash != "PENDENTE":
                    st.error("Este usuário já possui uma senha. Vá para a aba 'Fazer Login'.")
                elif senha_pa != senha_pa2:
                    st.error("As senhas não coincidem!")
                else:
                    valido, msg_erro = validar_regras_senha(senha_pa)
                    if not valido:
                        st.error(msg_erro)
                    else:
                        u_atualizado = g.definir_senha_usuario(email_pa, senha_pa)
                        if u_atualizado:
                            st.success("Senha criada! Entrando...")
                            st.session_state['usuario_logado'] = u_atualizado.get_nome()
                            st.session_state['nivel_logado'] = u_atualizado.get_nivel()
                            st.rerun()
                        else:
                            st.error("Erro ao definir senha.")
                            
# ------------------------------------------
# TELA PRINCIPAL
# ------------------------------------------
else:
    st.title("TaskFlow - Sistema de Gestão de Tarefas")

    if st.session_state.get('toast_msg'):
        st.toast(st.session_state.pop('toast_msg'), icon="✅")

    st.sidebar.success(f"Logado como: **{st.session_state['usuario_logado']}**")
    
    if st.sidebar.button("Sair (Logout)"):
        st.session_state['usuario_logado'] = None
        st.session_state['nivel_logado'] = None
        st.rerun()
        
    st.sidebar.markdown("---")
    
    if st.session_state['nivel_logado'] == "Administrador":
        st.sidebar.header("Novo Usuário (Acesso Restrito)")
        with st.sidebar.form("form_usuario", clear_on_submit=True):
            nome_u = st.text_input("Nome")
            email_u = st.text_input("Email")
            funcao_u = st.text_input("Função")
            nivel_u = st.selectbox("Nível de Acesso", ["Membro", "Administrador"])
            
            if st.form_submit_button("Criar Acesso"):
                if nome_u and email_u and funcao_u:
                    g.cadastrar_usuario(nome_u, email_u, funcao_u, nivel_u)
                    st.toast(f"Acesso criado! Peça para {nome_u} definir a senha no Primeiro Acesso.", icon="✅")
                else:
                    st.sidebar.error("Preencha todos os campos!")
        st.sidebar.markdown("---")

    st.sidebar.header("Nova Tarefa")
    with st.sidebar.form("form_tarefa", clear_on_submit=True):
        titulo_t = st.text_input("Título")
        desc_t = st.text_area("Descrição")
        prioridade_t = st.selectbox("Prioridade", ["Alta", "Média", "Baixa"])
        prazo_t = st.date_input("Prazo", value=datetime.date.today())
        usuarios_dict = {u.get_nome(): u for u in g.get_todos_usuarios()}
        resp_nome_t = st.selectbox("Atribuir Responsável", ["Sem responsável"] + list(usuarios_dict.keys()))
        
        if st.form_submit_button("Criar Tarefa") and titulo_t:
            resp_obj = usuarios_dict.get(resp_nome_t) if resp_nome_t != "Sem responsável" else None
            g.cadastrar_tarefa(titulo_t, desc_t, prioridade_t, prazo_t, st.session_state['usuario_logado'], resp_obj)
            st.toast("Tarefa adicionada ao quadro!", icon="📌")
            st.rerun()

    nomes_abas = ["📋 Tarefas", "👥 Equipe"]
    if st.session_state['nivel_logado'] == "Administrador":
        nomes_abas.append("📊 Relatório Executivo")
        nomes_abas.append("⚙️ Configurações") # NOVA ABA DE CONFIGURAÇÕES
        
    abas_renderizadas = st.tabs(nomes_abas)

    # ABA 1: Tarefas
    with abas_renderizadas[0]:
        with st.expander("🔍 Filtros de Busca", expanded=True):
            f_col1, f_col2, f_col3 = st.columns(3)
            opcoes_resp = ["Todos", "Sem responsável"] + [u.get_nome() for u in g.get_todos_usuarios()]
            filtro_resp = f_col1.selectbox("Filtrar por Responsável", opcoes_resp)
            filtro_prio = f_col2.selectbox("Filtrar por Prioridade", ["Todas", "Alta", "Média", "Baixa"])
            filtro_prazo = f_col3.date_input("Filtrar por Prazo (Período)", value=(), help="Selecione data inicial e final")

        st.subheader("Quadro de Atividades")
        tarefas_filtradas = g.get_todas_tarefas()
        if filtro_resp != "Todos": tarefas_filtradas = [t for t in tarefas_filtradas if (t.get_responsavel().get_nome() if t.get_responsavel() else "Sem responsável") == filtro_resp]
        if filtro_prio != "Todas": tarefas_filtradas = [t for t in tarefas_filtradas if t._prioridade == filtro_prio]
        if isinstance(filtro_prazo, tuple) and len(filtro_prazo) == 2: tarefas_filtradas = [t for t in tarefas_filtradas if filtro_prazo[0] <= t._prazo <= filtro_prazo[1]]
        
        if not tarefas_filtradas: st.info("Nenhuma tarefa encontrada.")
                        
        for t in tarefas_filtradas:
            resp_nome = t.get_responsavel().get_nome() if t.get_responsavel() else "Sem responsável"
            prio_formatada = MAPA_PRIORIDADE.get(t._prioridade, t._prioridade)
            cor = cor_borda_prioridade(t._prioridade)

            st.markdown(f"""
                <div style="border-left: 5px solid {cor}; border-radius: 8px; 
                            background-color: rgba(30,33,40,0.85); 
                            padding: 4px 12px; margin-bottom: 4px;">
                </div>
            """, unsafe_allow_html=True)

            with st.container(border=True):
                col1, col2, col3, col4, col5 = st.columns([2.5, 1.5, 1.2, 1.5, 1])
                col1.markdown(f"**{t.get_titulo()}**")
                col2.write(f"👤 {resp_nome}")
                col3.write(f"**{prio_formatada}**")

                if t.get_status() == "Concluído":
                    data_conc_br = datetime.date.fromisoformat(t.get_data_conclusao()).strftime('%d/%m/%Y') if t.get_data_conclusao() else ""
                    col4.write(f"✅ em **{data_conc_br}**")
                else:
                    col4.write(f"⏳ {t.get_status()}")

                botoes = col5.columns(2)
                if t.get_status() != "Concluído":
                    if botoes[0].button("✅", key=f"concluir_{t.get_titulo()}", help="Concluir"):
                        g.atualizar_status_tarefa(t.get_titulo(), "Concluído")
                        st.toast(f"Tarefa '{t.get_titulo()}' finalizada!", icon="🏆")
                        st.rerun()
                else:
                    botoes[0].write("✅")
                if botoes[1].button("🗑️", key=f"del_t_{t.get_titulo()}", help="Remover"):
                    g.remover_tarefa(t.get_titulo())
                    st.rerun()

                with st.expander("Detalhes e Edição da Demanda"):
                    data_criacao_br = datetime.date.fromisoformat(t.get_data_criacao()).strftime('%d/%m/%Y')
                    st.write(f"**Data de Criação:** {data_criacao_br}")
                    st.write(f"**Descrição:** {t._descricao}")

                    if t.get_status() != "Concluído":
                        st.markdown("---")
                        st.write("✏️ **Editar Informações e Apontar Horas:**")
                        with st.form(key=f"edit_form_{t.get_titulo()}"):
                            e_col1, e_col2, e_col3 = st.columns([2, 2, 2])
                            novo_criador = e_col1.text_input("Solicitante", value=t.get_criador())
                            novo_prazo = e_col2.date_input("Prazo Limite", value=t._prazo)
                            novo_tempo = e_col3.number_input("Tempo Focado (h)", value=int(t.get_tempo_focado()), min_value=0, step=1)

                            usuarios_dict = {u.get_nome(): u for u in g.get_todos_usuarios()}
                            lista_nomes = ["Sem responsável"] + list(usuarios_dict.keys())
                            index_atual = lista_nomes.index(resp_nome)
                            novo_resp_nome = st.selectbox("Responsável Atual", lista_nomes, index=index_atual)

                            lista_status = ["A Fazer", "Em Andamento"]
                            index_status = lista_status.index(t.get_status()) if t.get_status() in lista_status else 0
                            novo_status = st.selectbox("Status", lista_status, index=index_status)

                            if st.form_submit_button("💾 Salvar Alterações"):
                                novo_resp_obj = usuarios_dict.get(novo_resp_nome) if novo_resp_nome != "Sem responsável" else None
                                g.alterar_detalhes_tarefa(t.get_titulo(), novo_criador, novo_prazo, novo_resp_obj, novo_tempo)
                                g.atualizar_status_tarefa(t.get_titulo(), novo_status)
                                st.session_state['toast_msg'] = "Informações atualizadas!"  
                                st.rerun()
                    else:
                        st.write(f"**Solicitante:** {t.get_criador()}")
                        st.write(f"**Prazo Limite Original:** {t._prazo.strftime('%d/%m/%Y')}")
                        st.write(f"**Tempo Gasto:** {int(t.get_tempo_focado())} horas")
                        st.write(f"**Concluído em:** {datetime.date.fromisoformat(t.get_data_conclusao()).strftime('%d/%m/%Y')}")
    # ABA 2: Equipe
    with abas_renderizadas[1]:
        st.subheader("Membros do Projeto")
        for u in g.get_todos_usuarios():
            with st.container(border=True):
                if st.session_state['nivel_logado'] == "Administrador":
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                    col1.markdown(f"**{u.get_nome()}**")
                    col2.write(f"Função: {u.get_funcao()}")
                    
                    niveis = ["Membro", "Administrador"]
                    index_atual = niveis.index(u.get_nivel())
                    novo_nivel = col3.selectbox("Nível de Acesso", niveis, index=index_atual, key=f"sel_niv_{u.get_nome()}")
                    
                    if novo_nivel != u.get_nivel():
                        if u.get_nome() == st.session_state['usuario_logado'] and novo_nivel == "Membro":
                            st.error("⚠️ Você não pode remover seu próprio acesso de Administrador!")
                        else:
                            g.alterar_nivel_usuario(u.get_nome(), novo_nivel)
                            st.toast(f"Nível de {u.get_nome()} atualizado para {novo_nivel}!", icon="🔄")
                            st.rerun()

                    if col4.button("Remover", key=f"del_u_{u.get_nome()}", type="primary"):
                        if u.get_nome() == st.session_state['usuario_logado']:
                            st.error("Não pode apagar a si mesmo!")
                        else:
                            g.remover_usuario(u.get_nome())
                            st.rerun()
                else:
                    col1, col2, col3 = st.columns([2, 2, 2])
                    col1.markdown(f"**{u.get_nome()}**")
                    col2.write(f"Função: {u.get_funcao()}")
                    col3.write(f"Nível: *{u.get_nivel()}*")

    # ABA 3: Relatório (Só Admin)
    if st.session_state['nivel_logado'] == "Administrador":
        with abas_renderizadas[2]:
            st.subheader("Métricas e Extração por Período")
            col_d1, col_d2 = st.columns(2)
            hoje = datetime.date.today()
            
            data_inicio = col_d1.date_input("Data Inicial da Conclusão", value=hoje.replace(day=1))
            data_fim = col_d2.date_input("Data Final da Conclusão", value=hoje)
            st.markdown("---")
            
            tarefas_concluidas = [t for t in g.get_todas_tarefas() if t.get_status() == "Concluído"]
            dados_extracao = []
            fechadas_no_periodo = 0
            horas_totais_periodo = 0.0
            
            for t in tarefas_concluidas:
                data_conc = datetime.date.fromisoformat(t.get_data_conclusao())
                if data_inicio <= data_conc <= data_fim:
                    fechadas_no_periodo += 1
                    horas_totais_periodo += t.get_tempo_focado()
                    resp_n = t.get_responsavel().get_nome() if t.get_responsavel() else "Sem responsável"
                    
                    dados_extracao.append([
                        t.get_titulo(), t._descricao, t._prioridade, t.get_criador(), 
                        datetime.date.fromisoformat(t.get_data_criacao()).strftime('%d/%m/%Y'),
                        t.get_tempo_focado(), resp_n, data_conc.strftime('%d/%m/%Y')
                    ])

            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Tarefas Abertas", len([t for t in g.get_todas_tarefas() if t.get_status() != "Concluído"]))
            col_m2.metric("Concluídas (Geral)", len(tarefas_concluidas))
            col_m3.metric("Fechadas no Período", fechadas_no_periodo)
            col_m4.metric("Horas Trabalhadas", f"{horas_totais_periodo} h")
            
            st.markdown("---")
            if dados_extracao:
                output = io.StringIO()
                writer = csv.writer(output, delimiter=';')
                writer.writerow(['Titulo da Tarefa', 'Descricao', 'Prioridade', 'Solicitante', 'Data de Criacao', 'Tempo Focado (h)', 'Responsavel pela Conclusao', 'Data de Conclusao'])
                writer.writerows(dados_extracao)
                
                st.download_button(
                    label="📥 Baixar Extração Completa (Excel/CSV)",
                    data=output.getvalue().encode('utf-8-sig'),
                    file_name=f"extracao_tarefas_{data_inicio.strftime('%d%m%Y')}_a_{data_fim.strftime('%d%m%Y')}.csv",
                    mime="text/csv",
                    type="primary"
                )
            else:
                st.warning("Nenhuma tarefa foi concluída no período selecionado.")

    # ABA 4: CONFIGURAÇÕES (NOVA! Só Admin)
    if st.session_state['nivel_logado'] == "Administrador":
        with abas_renderizadas[3]:
            st.subheader("🎨 Personalização Visual do Sistema")
            st.write("Escolha como o fundo de tela de todos os usuários deve ser exibido.")
            
            config_atual = g.get_config()
            index_radio = 0 if config_atual['tipo'] == 'Imagem' else 1
            
            tipo_fundo = st.radio("Tipo de Fundo:", ["Imagem (URL)", "Cor Sólida"], index=index_radio, horizontal=True)
            
            if tipo_fundo == "Cor Sólida":
                valor_padrao_cor = config_atual['valor'] if config_atual['tipo'] == 'Cor' else '#0E1117'
                novo_valor_fundo = st.color_picker("Escolha a cor:", value=valor_padrao_cor)
            else:
                valor_padrao_img = config_atual['valor'] if config_atual['tipo'] == 'Imagem' else ''
                novo_valor_fundo = st.text_input("Cole o Link (URL) da imagem desejada:", value=valor_padrao_img)
                st.caption("Dica: Use imagens em alta resolução do Unsplash ou do Google Images. Exemplo: https://images.unsplash.com/photo-1557683316-973673baf926")

            if st.button("💾 Salvar Tema do Sistema", type="primary"):
                tipo_salvar = "Cor" if tipo_fundo == "Cor Sólida" else "Imagem"
                g.salvar_config(tipo_salvar, novo_valor_fundo)
                st.toast("Tema atualizado para toda a equipe!", icon="🎨")
                st.rerun()