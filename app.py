import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime
import pytz
from zoneinfo import ZoneInfo

# Fuso Horário de Brasília
FUSO_SP = ZoneInfo("America/Sao_Paulo")

def get_connection():
    # Lê a URL de conexão configurada no arquivo .streamlit/secrets.toml
    return psycopg2.connect(st.secrets["SUPABASE_DB_URL"])


if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

if "chamado_para_editar" not in st.session_state:
    st.session_state["chamado_para_editar"] = None

def autenticar_usuario(email, senha):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Busca o usuário no banco pelo e-mail e senha
        cursor.execute(
            "SELECT nome, email, perfil FROM usuarios WHERE email = %s AND"
            " senha = %s;",
            (email, senha),
        )
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            # Retorna os dados do usuário se encontrado
            return {"nome": user[0], "email": user[1], "perfil": user[2]}
        return None

    except Exception as e:
        st.error(f"Erro ao conectar para autenticação: {e}")
        return None

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

    # 🛑 BLOQUEIO: Interrompe o script aqui para quem NÃO está logado.
    # Nada do código abaixo deste ponto será executado ou exibido.
    st.stop()




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
            (email, senha)
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
        # Lê a tabela de chamados ordenando pelos mais recentes
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
        # Busca apenas os nomes dos usuários ordenados alfabeticamente
        cursor.execute("SELECT nome FROM usuarios ORDER BY nome ASC;")
        usuarios = cursor.fetchall()
        cursor.close()
        conn.close()

        # Extrai os nomes da lista de tuplas [(nome1,), (nome2,)]
        lista_nomes = [u[0] for u in usuarios]
        return lista_nomes
    except Exception as e:
        st.error(f"Erro ao carregar lista de usuários: {e}")
        return []


TECNICOS = ["Não atribuído", "Carlos Silva", "Jacques Pinheiro"]

st.title("🎫 Sistema de Chamados de TI")

usuario = st.session_state["usuario_logado"]

with st.sidebar:
    st.write(f"👤 **{usuario['nome']}**")
    st.caption(f"Perfil: `{usuario['perfil'].upper()}`")
    if st.button("🚪 Sair / Logout"):
        st.session_state["usuario_logado"] = None
        st.session_state["chamado_para_editar"] = None
        st.rerun()



if usuario["perfil"] == "tecnico":
    aba1, aba2 = st.tabs(["➕ Abrir Chamado", "📋 Gerenciamento de Chamados"])
    with aba1:
            st.header("Novo Chamado")
            with st.form(key="form_novo_chamado"):
                # O nome do solicitante já vem preenchido com o usuário logado
                lista_usuarios = carregar_usuarios()
                solicitante = st.selectbox("Solicitante", options=lista_usuarios)
                departamento = st.selectbox("Setor / Departamento", ["TI", "RH", "Financeiro", "Operações", "Comercial"])
                categoria = st.selectbox("Categoria", ["Hardware", "Software", "Rede / Internet", "Acessos", "Outros"])
                prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Crítica"])
                descricao = st.text_area("Descrição do Problema")
    
                btn_submeter = st.form_submit_button("🚀 Abrir Chamado")
    
                if btn_submeter:
                    if descricao.strip() == "":
                        st.warning("Por favor, descreva o problema.")
                    else:
                        conn = get_connection()
                        cursor = conn.cursor()
                        
                        # Gerar ID do chamado (ex: INC-XXXX)
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
    aba1, = st.tabs(["➕ Abrir Chamado"])
    aba2 = None
    #--- ABA 1: ABRIR CHAMADO (Todos têm acesso) ---
    with aba1:
        st.header("Novo Chamado")
        with st.form(key="form_novo_chamado"):
            # O nome do solicitante já vem preenchido com o usuário logado
            solicitante = st.text_input("Solicitante", value=usuario["nome"], disabled=True)
            departamento = st.selectbox("Setor / Departamento", ["TI", "RH", "Financeiro", "Operações", "Comercial"])
            categoria = st.selectbox("Categoria", ["Hardware", "Software", "Rede / Internet", "Acessos", "Outros"])
            prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Crítica"])
            descricao = st.text_area("Descrição do Problema")

            btn_submeter = st.form_submit_button("🚀 Abrir Chamado")

            if btn_submeter:
                if descricao.strip() == "":
                    st.warning("Por favor, descreva o problema.")
                else:
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    # Gerar ID do chamado (ex: INC-XXXX)
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

    # --- ABA 2: GERENCIAMENTO (Apenas perfil 'tecnico') ---
    # --- ABA 2: GERENCIAMENTO (Visível apenas para perfil 'tecnico') ---
if aba2 is not None:
    with aba2:
        st.header("📋 Painel de Gerenciamento de Chamados")
        
        # 1. Carrega os dados atualizados do banco
        df_chamados = carregar_chamados()
        
        if df_chamados.empty:
            st.info("Nenhum chamado encontrado no banco de dados.")
        else:
            # 2. Métricas rápidas no topo do painel
            col_m1, col_m2, col_m3 = st.columns(3)
            total_chamados = len(df_chamados)
            chamados_abertos = len(df_chamados[df_chamados['status'] == 'Aberto'])
            chamados_concluidos = len(df_chamados[df_chamados['status'] == 'Concluído'])
            
            col_m1.metric("Total de Chamados", total_chamados)
            col_m2.metric("Abertos / Em Andamento", chamados_abertos)
            col_m3.metric("Concluídos", chamados_concluidos)
            
            st.divider()
            
            # 3. Exibição da Tabela de Chamados
            st.subheader("Fila de Atendimento")
            st.dataframe(
                df_chamados,
                use_container_width=True,
                hide_index=True
            )
            
            # 4. Área de Ações e Edição rápida (✏️ / ✅)
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
                            "UPDATE chamados SET status = %s, data_fim = NOW() WHERE id_chamado = %s;",
                            ("Concluído", id_selecionado)
                        )
                        conn.commit()
                        cursor.close()
                        conn.close()
                        st.success(f"Chamado {id_selecionado} marcado como Concluído!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar status: {e}")

            # 5. Formulário de Edição do Chamado Selecionado
            if st.session_state.get("chamado_para_editar") == id_selecionado:
                st.info(f"Editando o chamado: **{id_selecionado}**")
                
                # Obtém os dados atuais do chamado selecionado
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