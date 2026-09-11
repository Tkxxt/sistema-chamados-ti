import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime
import pytz
from zoneinfo import ZoneInfo

# Fuso Horário de Brasília
FUSO_SP = ZoneInfo("America/Sao_Paulo")

if "chamado_para_editar" not in st.session_state:
    st.session_state["chamado_para_editar"] = None

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
            # 1. Métricas no Topo
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Total de Chamados", len(df))
            col_m2.metric("Em Aberto", len(df[df['status'] == 'Aberto']))
            col_m3.metric("Em Andamento", len(df[df['status'] == 'Em Andamento']))
            col_m4.metric("Concluídos", len(df[df['status'] == 'Concluído']))

            st.markdown("---")

            # 2. Tabela formatada para visualização
            st.subheader("📋 Lista de Chamados")
            
            df_exibicao = df.copy()
            if 'data_abertura' in df_exibicao.columns:
                df_exibicao['data_abertura'] = df_exibicao['data_abertura'].apply(formatar_data)
            if 'data_fim' in df_exibicao.columns:
                df_exibicao['data_fim'] = df_exibicao['data_fim'].apply(formatar_data)

            # Seleção e renomeação de colunas
            colunas_ver = ['id_chamado', 'solicitante', 'departamento', 'categoria', 'prioridade', 'status', 'tecnico', 'data_abertura', 'data_fim']
            cols = [c for c in colunas_ver if c in df_exibicao.columns]
            
            df_exibicao = df_exibicao[cols].rename(columns={
                'id_chamado': 'ID',
                'solicitante': 'Solicitante',
                'departamento': 'Setor',
                'categoria': 'Categoria',
                'prioridade': 'Prioridade',
                'status': 'Status',
                'tecnico': 'Técnico',
                'data_abertura': 'Abertura',
                'data_fim': 'Conclusão'
            })

            st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

            st.markdown("---")

            # 3. Ações Rápidas por Chamado (Lista interativa de botões)
            st.subheader("⚡ Ações Rápidas por Chamado")

            for _, row in df.iterrows():
                id_c = row['id_chamado']
                status_c = row['status']
                solic_c = row['solicitante']

                # Linha de ação para cada chamado
                col_info, col_btn_concluir, col_btn_editar = st.columns([4, 2, 1])

                with col_info:
                    st.write(f"**{id_c}** — {solic_c} | Status: `{status_c}`")

                with col_btn_concluir:
                    # Se o chamado não estiver concluído, mostra o botão para concluir
                    if status_c != "Concluído":
                        if st.button(f"✅ Concluir", key=f"btn_concluir_{id_c}"):
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE chamados 
                                SET status = 'Concluído', data_fim = %s 
                                WHERE id_chamado = %s;
                            """, (get_hora_brasilia(), id_c))
                            conn.commit()
                            cursor.close()
                            conn.close()
                            st.success(f"Chamado {id_c} marcado como Concluído!")
                            st.rerun()
                    else:
                        st.caption("✔ Já Concluído")

                with col_btn_editar:
                    # Botão Lápis para selecionar e abrir formulário de edição
                    if st.button(f"✏️ Editar", key=f"btn_editar_{id_c}"):
                        st.session_state["chamado_para_editar"] = id_c
                        st.rerun()

            # 4. Formulário de Edição Separado (Exibido se um chamado for selecionado)
            if st.session_state["chamado_para_editar"]:
                id_sel = st.session_state["chamado_para_editar"]
                dados_sel = df[df['id_chamado'] == id_sel].iloc[0]

                st.markdown("---")
                st.subheader(f"✏️ Editando Chamado: {id_sel}")

                with st.form(key="form_edicao_separado"):
                    c1, c2 = st.columns(2)
                    with c1:
                        novo_status = st.selectbox(
                            "Status", 
                            ["Aberto", "Em Andamento", "Concluído", "Cancelado"],
                            index=["Aberto", "Em Andamento", "Concluído", "Cancelado"].index(dados_sel['status'])
                        )
                        novo_tecnico = st.selectbox(
                            "Técnico Responsável", 
                            TECNICOS,
                            index=TECNICOS.index(dados_sel['tecnico']) if dados_sel['tecnico'] in TECNICOS else 0
                        )
                        nova_prioridade = st.selectbox(
                            "Prioridade",
                            ["Baixa", "Média", "Alta", "Crítica"],
                            index=["Baixa", "Média", "Alta", "Crítica"].index(dados_sel['prioridade'])
                        )

                    with c2:
                        st.info(f"🕒 **Abertura:** {formatar_data(dados_sel['data_abertura'])}")
                        st.info(f"🏁 **Conclusão:** {formatar_data(dados_sel['data_fim'])}")
                        nova_categoria = st.selectbox(
                            "Categoria",
                            ["Hardware", "Software", "Rede / Internet", "Acessos", "Outros"],
                            index=["Hardware", "Software", "Rede / Internet", "Acessos", "Outros"].index(dados_sel['categoria']) if dados_sel['categoria'] in ["Hardware", "Software", "Rede / Internet", "Acessos", "Outros"] else 0
                        )

                    nova_descricao = st.text_area("Descrição / Notas de Solução", value=str(dados_sel['descricao']))

                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        btn_salvar = st.form_submit_button("💾 Salvar Alterações")
                    with col_f2:
                        btn_cancelar = st.form_submit_button("❌ Fechar Edição")

                    if btn_salvar:
                        conn = get_connection()
                        cursor = conn.cursor()

                        # Atualiza data_fim para horário BSB caso o status mude para Concluído
                        data_fim_upd = get_hora_brasilia() if novo_status == "Concluído" and dados_sel['status'] != "Concluído" else dados_sel['data_fim']

                        cursor.execute("""
                            UPDATE chamados 
                            SET status = %s, tecnico = %s, prioridade = %s, categoria = %s, descricao = %s, data_fim = %s 
                            WHERE id_chamado = %s;
                        """, (novo_status, novo_tecnico, nova_prioridade, nova_categoria, nova_descricao, data_fim_upd, id_sel))

                        conn.commit()
                        cursor.close()
                        conn.close()

                        st.session_state["chamado_para_editar"] = None
                        st.success(f"✅ Chamado {id_sel} atualizado!")
                        st.rerun()

                    if btn_cancelar:
                        st.session_state["chamado_para_editar"] = None
                        st.rerun()

        else:
            st.info("Nenhum chamado encontrado no banco de dados.")
    except Exception as e:
        st.error(f"Erro ao carregar o painel: {e}")