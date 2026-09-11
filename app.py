import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime

st.set_page_config(page_title="Sistema de Chamados de TI", page_icon="🎫", layout="wide")

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
            data_abertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_fim TIMESTAMP
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()

try:
    init_db()
except Exception as e:
    st.error(f"Erro no banco: {e}")

TECNICOS = ["Não atribuído", "Carlos Silva", "Ana Souza", "Roberto Lima", "Mariana Costa", "Jacques Pinheiro"]

st.title("🎫 Sistema de Chamados de TI")

aba1, aba2, aba3 = st.tabs(["📝 Novo Chamado", "📊 Painel & Edição", "📈 Métricas & Gráficos"])

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
                agora = datetime.now()

                cursor.execute("""
                    INSERT INTO chamados (id_chamado, solicitante, departamento, categoria, prioridade, status, tecnico, descricao, data_abertura)
                    VALUES (%s, %s, %s, %s, %s, 'Aberto', %s, %s, %s);
                """, (id_chamado, solicitante, departamento, categoria, prioridade, tecnico, descricao, agora))
                
                conn.commit()
                cursor.close()
                conn.close()
                st.success(f"✅ Chamado **{id_chamado}** criado com sucesso às {agora.strftime('%H:%M:%S')}!")
            except Exception as e:
                st.error(f"Erro: {e}")

# --- ABA 2: PAINEL & EDIÇÃO ---
with aba2:
    st.header("Gerenciamento de Chamados")
    try:
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM chamados ORDER BY id DESC;", conn)
        conn.close()

        if not df.empty:
            st.dataframe(df, use_container_width=True)
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
                    st.info(f"🕒 **Início (Abertura):** {dados['data_abertura']}")
                    st.info(f"🏁 **Fim (Conclusão):** {dados['data_fim'] if pd.notnull(dados['data_fim']) else 'Em aberto'}")

                nova_descricao = st.text_area("Descrição / Notas de Solução", value=str(dados['descricao']))
                if st.form_submit_button("💾 Salvar Alterações"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    # Se o status mudou para Concluído, grava a data/hora de fim atual
                    data_fim_update = datetime.now() if novo_status == "Concluído" and dados['status'] != "Concluído" else dados['data_fim']

                    cursor.execute("""
                        UPDATE chamados 
                        SET status = %s, tecnico = %s, descricao = %s, data_fim = %s 
                        WHERE id_chamado = %s;
                    """, (novo_status, novo_tecnico, nova_descricao, data_fim_update, chamado_sel))
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success(f"✅ Chamado {chamado_sel} atualizado!")
                    st.rerun()
    except Exception as e:
        st.error(f"Erro ao carregar painel: {e}")

# --- ABA 3: MÉTRICAS & GRÁFICOS ---
with aba3:
    st.header("📈 Indicadores e Métricas de Atendimento")
    try:
        conn = get_connection()
        df_metrics = pd.read_sql_query("SELECT * FROM chamados;", conn)
        conn.close()

        if not df_metrics.empty:
            df_concluidos = df_metrics[df_metrics['status'] == 'Concluído'].copy()
            
            # Cálculo de tempo de resolução em horas
            if not df_concluidos.empty and 'data_fim' in df_concluidos.columns:
                df_concluidos['data_abertura'] = pd.to_datetime(df_concluidos['data_abertura'])
                df_concluidos['data_fim'] = pd.to_datetime(df_concluidos['data_fim'])
                df_concluidos['tempo_horas'] = (df_concluidos['data_fim'] - df_concluidos['data_abertura']).dt.total_seconds() / 3600
                
                tma = df_concluidos['tempo_horas'].mean()
            else:
                tma = 0

            m1, m2, m3 = st.columns(3)
            m1.metric("Total de Chamados", len(df_metrics))
            m2.metric("Chamados Concluídos", len(df_concluidos))
            m3.metric("Tempo Médio de Atendimento (TMA)", f"{tma:.2f} h" if tma > 0 else "N/A")

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Chamados por Categoria")
                st.bar_chart(df_metrics['categoria'].value_counts())
            with c2:
                st.subheader("Atendimentos por Técnico")
                st.bar_chart(df_metrics['tecnico'].value_counts())
        else:
            st.info("Sem dados suficientes para gerar métricas.")
    except Exception as e:
        st.error(f"Erro ao gerar gráficos: {e}")