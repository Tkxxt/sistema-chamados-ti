import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime

# Configuração da página do Streamlit
st.set_page_config(
    page_title="Sistema de Helpdesk - TI",
    page_icon="🎫",
    layout="wide"
)

# Função para conectar ao Supabase via variável de ambiente/secrets
def get_connection():
    return psycopg2.connect(st.secrets["SUPABASE_DB_URL"])

# Inicialização e criação automática da tabela no banco PostgreSQL
def init_db():
    try:
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
                descricao TEXT,
                data_abertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"Aguardando configuração das credenciais do banco: {e}")

# Função para cadastrar novo chamado
def criar_chamado(solicitante, departamento, categoria, prioridade, descricao):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Gera um ID sequencial para o ticket (ex: INC-1001)
    cursor.execute("SELECT COUNT(*) FROM chamados")
    total = cursor.fetchone()[0]
    id_chamado = f"INC-{1001 + total}"

    query = """
        INSERT INTO chamados (id_chamado, solicitante, departamento, categoria, prioridade, status, descricao)
        VALUES (%s, %s, %s, %s, %s, 'Aberto', %s)
    """
    cursor.execute(query, (id_chamado, solicitante, departamento, categoria, prioridade, descricao))
    conn.commit()
    cursor.close()
    conn.close()
    return id_chamado

# Função para listar os chamados cadastrados
def listar_chamados():
    try:
        conn = get_connection()
        query = '''
            SELECT 
                id_chamado AS "ID", 
                solicitante AS "Solicitante", 
                departamento AS "Departamento", 
                categoria AS "Categoria", 
                prioridade AS "Prioridade", 
                status AS "Status", 
                data_abertura AS "Data de Abertura", 
                descricao AS "Descrição" 
            FROM chamados 
            ORDER BY id DESC
        '''
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

# Tenta inicializar o banco de dados
init_db()

# --- INTERFACE VISUAL ---
st.title("🎫 Sistema de Helpdesk & Suporte de TI")
st.markdown("Gerenciamento centralizado de incidentes e solicitações de TI.")

# Abas de navegação
tab1, tab2 = st.tabs(["📝 Abrir Novo Chamado", "📊 Painel de Chamados"])

with tab1:
    st.subheader("Formulário de Solicitação")
    with st.form("form_novo_chamado", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            solicitante = st.text_input("Nome do Solicitante*", placeholder="Ex: Jacques Oliveira")
            departamento = st.selectbox("Departamento*", ["TI", "RH", "Financeiro", "Operações", "Comercial", "Diretoria"])
            categoria = st.selectbox("Categoria do Incidente*", ["Hardware", "Software", "Rede / Internet", "Acesso & Senhas", "Impressoras", "Outros"])
            
        with col2:
            prioridade = st.selectbox("Prioridade*", ["Baixa", "Média", "Alta", "Crítica"])
            descricao = st.text_area("Descrição Detalhada do Problema*", placeholder="Descreva o problema com o máximo de detalhes...", height=125)
            
        submit = st.form_submit_button("🚀 Registrar Chamado", use_container_width=True)

        if submit:
            if not solicitante or not descricao:
                st.warning("Por favor, preencha todos os campos obrigatórios (*).")
            else:
                try:
                    novo_id = criar_chamado(solicitante, departamento, categoria, prioridade, descricao)
                    st.success(f"✅ Chamado **{novo_id}** registrado com sucesso!")
                except Exception as err:
                    st.error(f"Erro ao salvar chamado: {err}")

with tab2:
    st.subheader("Acompanhamento de Incidentes")
    df_chamados = listar_chamados()
    
    if not df_chamados.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Chamados", len(df_chamados))
        col2.metric("Chamados Abertos", len(df_chamados[df_chamados["Status"] == "Aberto"]))
        col3.metric("Prioridade Crítica", len(df_chamados[df_chamados["Prioridade"] == "Crítica"]))
        
        st.divider()
        st.dataframe(df_chamados, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum chamado encontrado no banco de dados.")
