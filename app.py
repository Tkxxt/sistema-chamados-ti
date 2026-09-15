import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime
from zoneinfo import ZoneInfo

# ==========================================
# CONFIGURAÇÕES E FUSO HORÁRIO
# ==========================================
FUSO_SP = ZoneInfo("America/Sao_Paulo")

def get_hora_brasilia():
    return datetime.now(FUSO_SP)

def formatar_data(dt):
    if pd.notnull(dt) and dt != "":
        if isinstance(dt, str):
            dt = pd.to_datetime(dt)
        
        if dt.tzinfo is None:
            dt = dt.tz_localize("UTC").tz_convert(FUSO_SP)
        else:
            dt = dt.tz_convert(FUSO_SP)
            
        return dt.strftime("%H:%M - %d/%m/%Y")
    return "Em aberto"

# ==========================================
# BANCO DE DADOS & BANCO DE DADOS HELPERS
# ==========================================
def get_connection():
    return psycopg2.connect(st.secrets["SUPABASE_DB_URL"])

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chamados (
            id SERIAL PRIMARY KEY,
            id_chamado VARCHAR(20) UNIQUE,
            solicitante VARCHAR(100),
            departamento VARCHAR(50),
            categoria VARCHAR(50),
            prioridade VARCHAR(20),
            status VARCHAR(20) DEFAULT 'Aberto',
            tecnico VARCHAR(100),
            descricao TEXT,
            data_abertura TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            data_fim TIMESTAMP WITH TIME ZONE
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()

try:
    init_db()
except Exception as e:
    st.error(f"Erro no banco de dados: {e}")

def autenticar_usuario(email, senha):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT nome, email, perfil FROM usuarios WHERE email = %s AND senha = %s;",
            (email, senha),
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            return {"nome": user[0], "email": user[1], "perfil": user[2]}
        return None
    except Exception as e:
        st.error(f"Erro ao autenticar: {e}")
        return None

def carregar_chamados():
    try:
        conn = get_connection()
        query = "SELECT * FROM chamados ORDER BY data_abertura DESC;"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar chamados: {e}")
        return pd.DataFrame()

def carregar_usuarios():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nome FROM usuarios ORDER BY nome ASC;")
        usuarios = cursor.fetchall()
        cursor.close()
        conn.close()
        return [u[0] for u in usuarios]
    except Exception as e:
        st.error(f"Erro ao carregar lista de usuários: {e}")
        return []

# ==========================================
# CONTROLE DE SESSÃO & AUTENTICAÇÃO
# ==========================================
if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

if "chamado_para_editar" not in st.session_state:
    st.session_state["chamado_para_editar"] = None

# TELA DE LOGIN
if st.session_state["usuario_logado"] is None:
    st.title("🔑 Login - Sistema de TI")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form(key="form_login"):
            email_input = st.text_input("E-mail")
            senha_input = st.text_input("Senha", type="password")
            btn_entrar = st.form_submit_button("Entrar")

            if btn_entrar:
                user = autenticar_usuario(email_input, senha_input)
                if user:
                    st.session_state["usuario_logado"] = user
                    st.success(f"Bem-vindo(a), {user['nome']}!")
                    st.rerun()
                else:
                    st.error("E-mail ou senha incorretos.")

    st.stop()  # Bloqueia a execução para quem não está logado

# ==========================================
# APLICAÇÃO PRINCIPAL (USUÁRIO AUTENTICADO)
# ==========================================
usuario = st.session_state["usuario_logado"]
perfil_usuario = str(usuario["perfil"]).strip().lower()

st.title("🎫 Sistema de Chamados de TI")

with st.sidebar:
    st.write(f"👤 **{usuario['nome']}**")
    st.caption(f"Perfil: `{usuario['perfil'].upper()}`")
    if st.button("🚪 Sair / Logout"):
        st.session_state["usuario_logado"] = None
        st.session_state["chamado_para_editar"] = None
        st.rerun()

# ROTEAMENTO DAS ABAS
if perfil_usuario == "tecnico":
    aba1, aba2 = st.tabs(["➕ Abrir Chamado", "📋 Gerenciamento de Chamados"])
else:
    aba1, aba2 = st.tabs(["➕ Abrir Chamado", "📋 Meus Chamados"])

# ==========================================
# ABA 1: FORMULÁRIO DE ABERTURA DE CHAMADO
# ==========================================
with aba1:
    if perfil_usuario != "tecnico":
        st.header("Novo Chamado (Solicitante)")
        st.caption("Preencha os dados abaixo para relatar um problema à equipe de TI.")
        
        with st.form(key="form_solicitante"):
            st.text_input("Solicitante", value=usuario["nome"], disabled=True)
            departamento = st.selectbox("Seu Setor / Departamento", ["TI", "RH", "Financeiro", "Operações", "Comercial"])
            categoria = st.selectbox("Categoria", ["Hardware", "Software", "Rede / Internet", "Acessos", "Outros"])
            prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta"])
            descricao = st.text_area("Descreva o seu problema detalhadamente")

            btn_submeter = st.form_submit_button("🚀 Enviar Chamado")

            if btn_submeter:
                if not descricao.strip():
                    st.warning("Por favor, informe a descrição do problema.")
                else:
                    conn = get_connection()
                    cursor = conn.cursor()
                    id_chamado = f"INC-{int(datetime.now().timestamp())}"
                    data_abertura = get_hora_brasilia()

                    cursor.execute("""
                        INSERT INTO chamados (id_chamado, solicitante, departamento, categoria, prioridade, status, tecnico, descricao, data_abertura)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (id_chamado, usuario["nome"], departamento, categoria, prioridade, "Aberto", "Não Atribuído", descricao, data_abertura))

                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success(f"Chamado **{id_chamado}** aberto com sucesso!")

    else:
        st.header("Abertura Direta / Registro Interno (Técnico)")
        st.caption("Use esta tela para registrar um chamado presencial, por telefone ou para atribuição direta.")
        
        with st.form(key="form_tecnico"):
            lista_usuarios = carregar_usuarios()
            solicitante = st.selectbox("Selecione o Solicitante", options=lista_usuarios)
            departamento = st.selectbox("Setor", ["TI", "RH", "Financeiro", "Operações", "Comercial"])
            categoria = st.selectbox("Categoria", ["Hardware", "Software", "Rede / Internet", "Acessos", "Outros"])
            
            col_prio, col_stat = st.columns(2)
            with col_prio:
                prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Crítica"])
            with col_stat:
                status_inicial = st.selectbox("Status Inicial", ["Aberto", "Em Atendimento"])
            
            atribuir_mim = st.checkbox("Atribuir este chamado a mim imediatamente", value=True)
            tecnico_resp = usuario["nome"] if atribuir_mim else "Não Atribuído"

            descricao = st.text_area("Observações / Descrição do Chamado")

            btn_submeter_tec = st.form_submit_button("💾 Registrar Chamado")

            if btn_submeter_tec:
                if not descricao.strip():
                    st.warning("Por favor, insira a descrição.")
                else:
                    conn = get_connection()
                    cursor = conn.cursor()
                    id_chamado = f"INC-{int(datetime.now().timestamp())}"
                    data_abertura = get_hora_brasilia()

                    cursor.execute("""
                        INSERT INTO chamados (id_chamado, solicitante, departamento, categoria, prioridade, status, tecnico, descricao, data_abertura)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (id_chamado, solicitante, departamento, categoria, prioridade, status_inicial, tecnico_resp, descricao, data_abertura))

                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success(f"Chamado **{id_chamado}** cadastrado com sucesso!")

# ==========================================
# ABA 2: CONSULTA E GERENCIAMENTO DE CHAMADOS
# ==========================================
with aba2:
    df_chamados = carregar_chamados()

    # Formatação de datas para exibição adequada
    if not df_chamados.empty:
        df_chamados["data_abertura"] = df_chamados["data_abertura"].apply(formatar_data)
        if "data_fim" in df_chamados.columns:
            df_chamados["data_fim"] = df_chamados["data_fim"].apply(formatar_data)

    # --- VISÃO DO SOLICITANTE ---
    if perfil_usuario != "tecnico":
        st.header("📋 Meus Chamados")
        
        if df_chamados.empty:
            st.info("Você não possui chamados registrados.")
        else:
            # Filtra apenas os chamados do usuário logado
            df_meus_chamados = df_chamados[df_chamados["solicitante"] == usuario["nome"]].copy()
            
            if df_meus_chamados.empty:
                st.info("Você não possui chamados registrados.")
            else:
                # 1. Mapeia o Status para adicionar badges visuais com emojis
                mapa_status = {
                    "Aberto": "🔴 Aberto",
                    "Em Atendimento": "🟡 Em Atendimento",
                    "Aguardando Usuário": "🟠 Aguardando",
                    "Concluído": "🟢 Concluído"
                }
                df_meus_chamados["status_visual"] = df_meus_chamados["status"].map(lambda x: mapa_status.get(x, f"⚪ {x}"))

                # 2. Seleciona e Reordena as colunas para exibição
                colunas_exibir = {
                    "id_chamado": "Código",
                    "categoria": "Categoria",
                    "prioridade": "Prioridade",
                    "status_visual": "Status",
                    "tecnico": "Técnico Responsável",
                    "data_abertura": "Aberto em",
                    "descricao": "Descrição"
                }
                
                # Filtra apenas as colunas que existem no DataFrame
                cols_disponiveis = [c for c in colunas_exibir.keys() if c in df_meus_chamados.columns]
                df_exibicao = df_meus_chamados[cols_disponiveis].rename(columns=colunas_exibir)

                # 3. Exibe com configurações customizadas de colunas
                st.dataframe(
                    df_exibicao,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Código": st.column_config.TextColumn("Código", help="Identificador do chamado", width="small"),
                        "Status": st.column_config.TextColumn("Status", width="medium"),
                        "Prioridade": st.column_config.TextColumn("Prioridade", width="small"),
                        "Aberto em": st.column_config.TextColumn("Aberto em", width="medium"),
                        "Descrição": st.column_config.TextColumn("Descrição do Problema", width="large"),
                    }
                )
    # --- VISÃO DO TÉCNICO ---
    else:
        st.header("📋 Painel de Gerenciamento de Chamados")
        
        if df_chamados.empty:
            st.info("Nenhum chamado encontrado no banco de dados.")
        else:
            # 1. MÉTRICAS EXPANDIDAS
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total", len(df_chamados))
            c2.metric("🔴 Abertos", len(df_chamados[df_chamados['status'] == 'Aberto']))
            c3.metric("🟡 Em Atendimento", len(df_chamados[df_chamados['status'] == 'Em Atendimento']))
            c4.metric("🟢 Concluídos", len(df_chamados[df_chamados['status'] == 'Concluído']))
            
            st.divider()

            # 2. FILTROS RÁPIDOS DA FILA
            with st.expander("🔍 **Filtros da Fila de Atendimento**", expanded=False):
                col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
                with col_f1:
                    busca_texto = st.text_input("Buscar por ID, Solicitante ou Descrição:", value="", placeholder="Ex: INC-1234 ou Ana")
                with col_f2:
                    filtro_status = st.multiselect(
                        "Status",
                        options=list(df_chamados["status"].unique()),
                        default=[]
                    )
                with col_f3:
                    filtro_prioridade = st.multiselect(
                        "Prioridade",
                        options=list(df_chamados["prioridade"].unique()),
                        default=[]
                    )

            # Aplicação dos Filtros no DataFrame
            df_filtrado = df_chamados.copy()

            if busca_texto.strip():
                termo = busca_texto.strip().lower()
                df_filtrado = df_filtrado[
                    df_filtrado["id_chamado"].astype(str).str.lower().str.contains(termo) |
                    df_filtrado["solicitante"].astype(str).str.lower().str.contains(termo) |
                    df_filtrado["descricao"].astype(str).str.lower().str.contains(termo)
                ]

            if filtro_status:
                df_filtrado = df_filtrado[df_filtrado["status"].isin(filtro_status)]

            if filtro_prioridade:
                df_filtrado = df_filtrado[df_filtrado["prioridade"].isin(filtro_prioridade)]

            # 3. MAPEAMENTO DE BADGES VISUAIS (STATUS E PRIORIDADE)
            mapa_status = {
                "Aberto": "🔴 Aberto",
                "Em Atendimento": "🟡 Em Atendimento",
                "Aguardando Usuário": "🟠 Aguardando",
                "Concluído": "🟢 Concluído"
            }
            mapa_prioridade = {
                "Crítica": "🔥 Crítica",
                "Alta": "⚡ Alta",
                "Média": "🟡 Média",
                "Baixa": "🟢 Baixa"
            }

            df_filtrado["status_fmt"] = df_filtrado["status"].map(lambda x: mapa_status.get(x, f"⚪ {x}"))
            df_filtrado["prioridade_fmt"] = df_filtrado["prioridade"].map(lambda x: mapa_prioridade.get(x, x))

            # 4. REORDENAÇÃO E SELEÇÃO DE COLUNAS
            colunas_tecnico = {
                "id_chamado": "Código",
                "solicitante": "Solicitante",
                "departamento": "Setor",
                "categoria": "Categoria",
                "prioridade_fmt": "Prioridade",
                "status_fmt": "Status",
                "tecnico": "Técnico",
                "data_abertura": "Aberto em",
                "data_fim": "Encerrado em",
                "descricao": "Descrição"
            }

            cols_existentes = [c for c in colunas_tecnico.keys() if c in df_filtrado.columns]
            df_painel_exibir = df_filtrado[cols_existentes].rename(columns=colunas_tecnico)

            st.subheader(f"Fila de Atendimento ({len(df_filtrado)})")

            # 5. EXIBIÇÃO DA TABELA FORMATADA
            st.dataframe(
                df_painel_exibir,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Código": st.column_config.TextColumn("Código", width="small"),
                    "Prioridade": st.column_config.TextColumn("Prioridade", width="small"),
                    "Status": st.column_config.TextColumn("Status", width="medium"),
                    "Solicitante": st.column_config.TextColumn("Solicitante", width="medium"),
                    "Setor": st.column_config.TextColumn("Setor", width="small"),
                    "Aberto em": st.column_config.TextColumn("Aberto em", width="medium"),
                    "Encerrado em": st.column_config.TextColumn("Encerrado em", width="medium"),
                    "Descrição": st.column_config.TextColumn("Descrição do Problema", width="large"),
                }
            )
            
            st.subheader("⚙️ Ações no Chamado")
            lista_ids = df_chamados["id_chamado"].tolist()
            id_selecionado = st.selectbox("Selecione o chamado para gerenciar:", lista_ids)
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("✏️ Editar Chamado", use_container_width=True):
                    st.session_state["chamado_para_editar"] = id_selecionado
                    
            with col_btn2:
                if st.button("✅ Concluir Chamado", use_container_width=True):
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE chamados SET status = %s, data_fim = %s, tecnico = %s WHERE id_chamado = %s;",
                            ("Concluído", get_hora_brasilia(), usuario["nome"], id_selecionado)
                        )
                        conn.commit()
                        cursor.close()
                        conn.close()
                        st.success(f"Chamado {id_selecionado} marcado como Concluído!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar status: {e}")

            # FORMULÁRIO DE EDIÇÃO
            if st.session_state.get("chamado_para_editar") == id_selecionado:
                st.info(f"Editando o chamado: **{id_selecionado}**")
                dados_chamado = df_chamados[df_chamados["id_chamado"] == id_selecionado].iloc[0]
                
                with st.form(key="form_edicao_chamado"):
                    novo_status = st.selectbox(
                        "Status", 
                        ["Aberto", "Em Atendimento", "Aguardando Usuário", "Concluído"],
                        index=["Aberto", "Em Atendimento", "Aguardando Usuário", "Concluído"].index(dados_chamado["status"]) if dados_chamado["status"] in ["Aberto", "Em Atendimento", "Aguardando Usuário", "Concluído"] else 0
                    )
                    novo_tecnico = st.text_input("Técnico Responsável", value=usuario["nome"])
                    
                    btn_salvar_edicao = st.form_submit_button("💾 Salvar Alterações")
                    
                    if btn_salvar_edicao:
                        try:
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE chamados SET status = %s, tecnico = %s WHERE id_chamado = %s;",
                                (novo_status, novo_tecnico, id_selecionado)
                            )
                            conn.commit()
                            cursor.close()
                            conn.close()
                            st.session_state["chamado_para_editar"] = None
                            st.success("Chamado atualizado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar edição: {e}")