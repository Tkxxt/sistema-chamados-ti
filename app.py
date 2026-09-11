import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Sistema de Chamados de TI", page_icon="🎫", layout="wide")

# Conexão com o Supabase via PostgreSQL
def get_connection():
    return psycopg2.connect(st.secrets["SUPABASE_DB_URL"])

# Inicialização do banco de dados
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
            data_abertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_inicio TIMESTAMP
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()

try:
    init_db()
except Exception as e:
    st.error(f"Erro ao conectar com o banco de dados: {e}")

# Lista de técnicos cadastrados na equipe
TECNICOS = ["Não atribuído", "Carlos Silva", "Jacques Pinheiro"]

st.title("🎫 Sistema de Chamados de TI")

aba1, aba2 = st.tabs(["📝 Abrir Novo Chamado", "📊 Painel de Chamados"])

# --- ABA 1: ABRIR NOVO CHAMADO ---
with aba1:
    st.header("Novo Chamado")
    with st.form(key="form_chamado", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            solicitante = st.text_input("Solicitante *", placeholder="Ex: Maria Oliveira")
            departamento = st.selectbox("Departamento", ["TI", "RH", "Financeiro", "Vendas", "Operações", "Outro"])
            categoria = st.selectbox("Categoria", ["Hardware", "Software", "Rede / Internet", "Acessos / Senhas", "Outros"])
        
        with col2:
            prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Crítica"])
            tecnico = st.selectbox("Técnico Atribuído (Opcional)", TECNICOS)
        
        descricao = st.text_area("Descrição do Problema *", placeholder="Descreva os detalhes da solicitação...")
        
        submit = st.form_submit_button("🚀 Registrar Chamado")

        if submit:
            if not solicitante or not descricao:
                st.warning("Por favor, preencha todos os campos obrigatórios (*).")
            else:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    # Gerar ID único para o chamado
                    cursor.execute("SELECT COUNT(*) FROM chamados;")
                    qtd = cursor.fetchone()[0]
                    id_chamado = f"INC-{1001 + qtd}"
                    
                    agora = datetime.now()

                    cursor.execute("""
                        INSERT INTO chamados (id_chamado, solicitante, departamento, categoria, prioridade, status, tecnico, descricao, data_abertura)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (id_chamado, solicitante, departamento, categoria, prioridade, 'Aberto', tecnico, descricao, agora))
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    st.success(f"✅ Chamado **{id_chamado}** registrado com sucesso em {agora.strftime('%d/%m/%Y às %H:%M:%S')}!")
                except Exception as e:
                    st.error(f"Erro ao salvar chamado: {e}")

# --- ABA 2: PAINEL E EDIÇÃO DE CHAMADOS ---
with aba2:
    st.header("Gerenciamento de Chamados")
    
    try:
        conn = get_connection()
        query = "SELECT * FROM chamados ORDER BY id DESC;"
        df = pd.read_sql_query(query, conn)
        conn.close()

        if not df.empty:
            # Métricas
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Total de Chamados", len(df))
            col_m2.metric("Abertos", len(df[df['status'] == 'Aberto']))
            col_m3.metric("Em Andamento", len(df[df['status'] == 'Em Andamento']))
            col_m4.metric("Concluídos", len(df[df['status'] == 'Concluído']))

            st.markdown("---")
            
            # Exibição da Tabela
            st.subheader("📋 Lista de Chamados")
            st.dataframe(df, use_container_width=True)

            st.markdown("---")
            
            # --- SEÇÃO DE EDIÇÃO DO CHAMADO ---
            st.subheader("✏️ Editar / Atualizar Chamado")
            
            chamado_selecionado = st.selectbox(
                "Selecione um chamado para editar:",
                options=df['id_chamado'].tolist(),
                index=0
            )

            # Buscar dados do chamado selecionado
            dados_chamado = df[df['id_chamado'] == chamado_selecionado].iloc[0]

            with st.form(key="form_edicao"):
                col_e1, col_e2 = st.columns(2)

                with col_e1:
                    novo_status = st.selectbox(
                        "Status",
                        ["Aberto", "Em Andamento", "Concluído", "Cancelado"],
                        index=["Aberto", "Em Andamento", "Concluído", "Cancelado"].index(dados_chamado['status']) if dados_chamado['status'] in ["Aberto", "Em Andamento", "Concluído", "Cancelado"] else 0
                    )
                    
                    tecnico_atual = dados_chamado['tecnico'] if dados_chamado['tecnico'] in TECNICOS else TECNICOS[0]
                    novo_tecnico = st.selectbox("Técnico Responsável", TECNICOS, index=TECNICOS.index(tecnico_atual))
                    
                    nova_prioridade = st.selectbox(
                        "Prioridade", 
                        ["Baixa", "Média", "Alta", "Crítica"],
                        index=["Baixa", "Média", "Alta", "Crítica"].index(dados_chamado['prioridade'])
                    )

                with col_e2:
                    st.text_input("Data de Abertura (Registrado)", value=str(dados_chamado['data_abertura']), disabled=True)
                    
                    # Edição do horário de início do atendimento
                    data_inicio_val = dados_chamado['data_inicio']
                    data_def = datetime.now().date()
                    hora_def = datetime.now().time()
                    
                    if pd.notnull(data_inicio_val):
                        if isinstance(data_inicio_val, str):
                            dt_obj = datetime.strptime(data_inicio_val, '%Y-%m-%d %H:%M:%S')
                        else:
                            dt_obj = data_inicio_val
                        data_def = dt_obj.date()
                        hora_def = dt_obj.time()

                    dt_inicio = st.date_input("Data de Início do Atendimento", value=data_def)
                    hr_inicio = st.time_input("Hora de Início do Atendimento", value=hora_def)

                nova_descricao = st.text_area("Descrição / Notas de Resolução", value=str(dados_chamado['descricao']))
                
                btn_salvar = st.form_submit_button("💾 Salvar Alterações")

                if btn_salvar:
                    try:
                        data_inicio_combinada = datetime.combine(dt_inicio, hr_inicio)
                        
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE chamados
                            SET status = %s, tecnico = %s, prioridade = %s, descricao = %s, data_inicio = %s
                            WHERE id_chamado = %s;
                        """, (novo_status, novo_tecnico, nova_prioridade, nova_descricao, data_inicio_combinada, chamado_selecionado))
                        
                        conn.commit()
                        cursor.close()
                        conn.close()
                        
                        st.success(f"✅ Chamado **{chamado_selecionado}** atualizado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar chamado: {e}")

        else:
            st.info("Nenhum chamado encontrado no banco de dados.")
    except Exception as e:
        st.error(f"Erro ao carregar os chamados: {e}")