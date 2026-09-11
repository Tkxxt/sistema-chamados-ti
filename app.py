import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime
import pytz

# Configuração da página
st.set_page_config(page_title="Sistema de Chamados de TI", page_icon="🎫", layout="wide")

# Fuso Horário de Brasília
FUSO_SP = pytz.timezone("America/Sao_Paulo")

def get_hora_brasilia():
    return datetime.now(FUSO_SP)

def formatar_data(dt):
    if pd.notnull(dt):
        if isinstance(dt, str):
            dt = pd.to_datetime(dt)
        # Garante a conversão para o fuso de Brasília se houver informação de timezone
        if hasattr(dt, 'tz_convert') and dt.tzinfo is not None:
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

TECNICOS = ["Não atribuído", "Carlos Silva", "Jacques Pinheiro"]

st.title("🎫 Sistema de Chamados de TI")

aba1, aba2 = st.tabs(["📝 Novo Chamado", "📊 Painel & Gerenciamento"])

# --- ABA 1: ABRIR CHAMADO ---
with aba1:
    st.header("Novo Chamado")
    with st.form(key="form_chamado", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            solicitante = st.text_input("Solicitante *")
            departamento = st.selectbox("Departamento", ["TI", "RH", "Financeiro", "Vendas", "Operações", "Outro"])
            categoria = st.selectbox("Categoria", ["Hardware", "Software", "Rede / Internet", "Acessos", "Outros"])
        with col2:
            prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta", "Crítica"])
            tecnico = st.selectbox("Atribuir Técnico", TECNICOS)
        
        descricao = st.text_area("Descrição do Problema *")
        submit = st.form_submit_button("🚀 Registrar Chamado")

        if submit and solicitante and descricao:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM chamados;")
                qtd = cursor.fetchone()[0]
                id_chamado = f"INC-{1001 + qtd}"
                agora_bsb = get_hora_brasilia()

                cursor.execute("""
                    INSERT INTO chamados (id_chamado, solicitante, departamento, categoria, prioridade, status, tecnico, descricao, data_abertura)
                    VALUES (%s, %s, %s, %s, %s, 'Aberto', %s, %s, %s);
                """, (id_chamado, solicitante, departamento, categoria, prioridade, tecnico, descricao, agora_bsb))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                st.success(f"✅ Chamado **{id_chamado}** criado com sucesso às {agora_bsb.strftime('%H:%M - %d/%m/%Y')}!")
            except Exception as e:
                st.error(f"Erro ao cadastrar chamado: {e}")

# --- ABA 2: PAINEL DE CHAMADOS ---
with aba2:
    st.header("Gerenciamento de Chamados")
    try:
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM chamados ORDER BY id DESC;", conn)
        conn.close()

        if not df.empty:
            # Formatação visual das datas na tabela
            df_exibicao = df.copy()
            if 'data_abertura' in df_exibicao.columns:
                df_exibicao['data_abertura'] = df_exibicao['data_abertura'].apply(formatar_data)
            if 'data_fim' in df_exibicao.columns:
                df_exibicao['data_fim'] = df_exibicao['data_fim'].apply(formatar_data)

            st.dataframe(df_exibicao, use_container_width=True)
            st.markdown("---")
            
            st.subheader("✏️ Atualizar Status / Técnico")
            chamado_sel = st.selectbox("Selecione o chamado:", df['id_chamado'].tolist())
            dados = df[df['id_chamado'] == chamado_sel].iloc[0]

            with st.form(key="form_edicao"):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    novo_status = st.selectbox("Status", ["Aberto", "Em Andamento", "Concluído", "Cancelado"], 
                                               index=["Aberto", "Em Andamento", "Concluído", "Cancelado"].index(dados['status']))
                    novo_tecnico = st.selectbox("Técnico Responsável", TECNICOS, 
                                                index=TECNICOS.index(dados['tecnico']) if dados['tecnico'] in TECNICOS else 0)
                with col_e2:
                    st.info(f"🕒 **Abertura:** {formatar_data(dados['data_abertura'])}")
                    st.info(f"🏁 **Conclusão:** {formatar_data(dados['data_fim'])}")

                nova_descricao = st.text_area("Descrição / Notas de Solução", value=str(dados['descricao']))
                
                if st.form_submit_button("💾 Salvar Alterações"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    # Atualiza o encerramento com a hora atual de Brasília caso o status vire 'Concluído'
                    data_fim_update = get_hora_brasilia() if novo_status == "Concluído" and dados['status'] != "Concluído" else dados['data_fim']

                    cursor.execute("""
                        UPDATE chamados 
                        SET status = %s, tecnico = %s, descricao = %s, data_fim = %s 
                        WHERE id_chamado = %s;
                    """, (novo_status, novo_tecnico, nova_descricao, data_fim_update, chamado_sel))
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success(f"✅ Chamado **{chamado_sel}** atualizado com sucesso!")
                    st.rerun()
        else:
            st.info("Nenhum chamado cadastrado até o momento.")
    except Exception as e:
        st.error(f"Erro ao carregar o painel: {e}")