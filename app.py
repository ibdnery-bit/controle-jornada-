import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os

st.set_page_config(page_title="Controle Operacional de Jornada - MRS", layout="wide", page_icon="🚆")

ARQUIVO_BANCO = "dados_jornada.json"

# Mapeamento padrão de horas por atividade
DURACAO_ATIVIDADE = {
    "Viagem": 10,
    "Manobra": 6,
    "Auxílio": 8,
    "Manutenção": 8,
    "Outra Atividade": 8
}

# --- FUNÇÕES PARA SALVAR E CARREGAR DADOS ---
def salvar_dados():
    em_jornada_serializavel = []
    if isinstance(st.session_state.get("em_jornada"), list):
        for item in st.session_state.em_jornada:
            if isinstance(item, dict):
                copia = item.copy()
                if isinstance(copia.get("DataFim"), datetime):
                    copia["DataFim"] = copia["DataFim"].strftime("%Y-%m-%d %H:%M:%S")
                if isinstance(copia.get("DataInicioDT"), datetime):
                    copia["DataInicioDT"] = copia["DataInicioDT"].strftime("%Y-%m-%d %H:%M:%S")
                em_jornada_serializavel.append(copia)
        
    dados = {
        "programados": st.session_state.get("programados", []),
        "em_jornada": em_jornada_serializavel,
        "encerrados": st.session_state.get("encerrados", [])
    }
    with open(ARQUIVO_BANCO, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

def carregar_dados():
    st.session_state.programados = []
    st.session_state.em_jornada = []
    st.session_state.encerrados = []
    
    if os.path.exists(ARQUIVO_BANCO):
        try:
            with open(ARQUIVO_BANCO, "r", encoding="utf-8") as f:
                dados = json.load(f)
                
                if isinstance(dados, dict):
                    st.session_state.programados = dados.get("programados", []) if isinstance(dados.get("programados"), list) else []
                    st.session_state.encerrados = dados.get("encerrados", []) if isinstance(dados.get("encerrados"), list) else []
                    
                    raw_em_jornada = dados.get("em_jornada", [])
                    if isinstance(raw_em_jornada, list):
                        for item in raw_em_jornada:
                            if isinstance(item, dict):
                                if "DataFim" in item and isinstance(item["DataFim"], str):
                                    try:
                                        item["DataFim"] = datetime.strptime(item["DataFim"], "%Y-%m-%d %H:%M:%S")
                                    except ValueError:
                                        pass
                                if "DataInicioDT" in item and isinstance(item["DataInicioDT"], str):
                                    try:
                                        item["DataInicioDT"] = datetime.strptime(item["DataInicioDT"], "%Y-%m-%d %H:%M:%S")
                                    except ValueError:
                                        pass
                                st.session_state.em_jornada.append(item)
        except Exception:
            st.session_state.programados = []
            st.session_state.em_jornada = []
            st.session_state.encerrados = []

if 'programados' not in st.session_state or 'em_jornada' not in st.session_state:
    carregar_dados()

if not isinstance(st.session_state.em_jornada, list):
    st.session_state.em_jornada = []

if not isinstance(st.session_state.programados, list):
    st.session_state.programados = []

if 'encerrados' not in st.session_state or not isinstance(st.session_state.encerrados, list):
    st.session_state.encerrados = []

st.title("🚆 Controle Operacional de Jornada")

st.sidebar.header("⚙️ Opções e Carga")

# --- 1. IMPORTAÇÃO DA PLANILHA ---
st.sidebar.subheader("📂 Programação Diária (.xlsx / .csv)")
arquivo_enviado = st.sidebar.file_uploader("Carregar Escala do Dia", type=["xlsx", "csv"])

if arquivo_enviado is not None:
    if 'ultimo_arquivo' not in st.session_state or st.session_state.ultimo_arquivo != arquivo_enviado.name:
        try:
            if arquivo_enviado.name.endswith('.csv'):
                df_importado = pd.read_csv(arquivo_enviado)
            else:
                df_importado = pd.read_excel(arquivo_enviado)
                
            novos_programados = []
            for _, linha in df_importado.iterrows():
                nome = str(linha.get("Maquinista", linha.get("Nome", "Não informado")))
                matricula = str(linha.get("Matrícula", linha.get("Matricula", "-")))
                atividade = str(linha.get("Atividade", "Viagem"))
                trem = str(linha.get("Trem / Prefixo", linha.get("Trem", linha.get("Prefixo", "-"))))
                loco = str(linha.get("Locomotiva", linha.get("Loco", "-")))
                origem = str(linha.get("Origem", "-"))
                destino = str(linha.get("Destino", "-"))
                
                novos_programados.append({
                    "Matrícula": matricula,
                    "Maquinista": nome,
                    "Atividade": atividade,
                    "Trem": trem,
                    "Locomotiva": loco,
                    "Trecho": f"{origem} ➔ {destino}"
                })
                
            st.session_state.programados.extend(novos_programados)
            st.session_state.ultimo_arquivo = arquivo_enviado.name
            salvar_dados()
            st.sidebar.success(f"✅ {len(novos_programados)} maquinistas adicionados!")
        except Exception as e:
            st.sidebar.error(f"Erro ao ler arquivo: {e}")

st.sidebar.markdown("---")

# --- 2. LANÇAMENTO MANUAL ---
st.sidebar.subheader("✍️ Lançamento Manual")
with st.sidebar.form("form_manual", clear_on_submit=True):
    m_nome = st.text_input("Nome do Maquinista")
    m_mat = st.text_input("Matrícula")
    m_ativ = st.selectbox("Atividade", list(DURACAO_ATIVIDADE.keys()))
    m_trem = st.text_input("Trem / Prefixo")
    m_loco = st.text_input("Locomotiva")
    m_orig = st.text_input("Origem")
    m_dest = st.text_input("Destino")
    
    btn_manual = st.form_submit_button("➕ Adicionar à Escala")
    
    if btn_manual:
        if m_nome.strip() != "":
            st.session_state.programados.append({
                "Matrícula": m_mat if m_mat else "-",
                "Maquinista": m_nome,
                "Atividade": m_ativ,
                "Trem": m_trem if m_trem else "-",
                "Locomotiva": m_loco if m_loco else "-",
                "Trecho": f"{m_orig if m_orig else '-'} ➔ {m_dest if m_dest else '-'}"
            })
            salvar_dados()
            st.sidebar.success(f"✅ {m_nome} adicionado com sucesso!")
            st.rerun()
        else:
            st.sidebar.warning("Por favor, digite o nome do maquinista.")

st.sidebar.markdown("---")

# --- NAVEGAÇÃO POR ABAS ---
aba1, aba2, aba3 = st.tabs(["⏱️ Jornadas em Andamento", "📋 Programação (Aguardando Start)", "📊 Histórico e Performance"])

# --- ABA 1: EM OPERAÇÃO (LINHAS COM BOTÃO DE ENCERRAR NA PRÓPRIA LINHA) ---
with aba1:
    st.subheader("🟢 Maquinistas em Operação")
    
    if len(st.session_state.em_jornada) > 0:
        if st.button("🔄 Atualizar Tempos"):
            st.rerun()
            
        # Cabeçalho da Planilha
        col_st, col_maq, col_mat, col_ativ, col_trem, col_ab, col_rest, col_acao = st.columns([1.5, 1.8, 1.1, 1.1, 1.3, 1.2, 1.2, 1.2])
        col_st.markdown("**Status**")
        col_maq.markdown("**Maquinista**")
        col_mat.markdown("**Matrícula**")
        col_ativ.markdown("**Atividade**")
        col_trem.markdown("**Trem / Loco**")
        col_ab.markdown("**Abertura**")
        col_rest.markdown("**Restante**")
        col_acao.markdown("**Ação**")
        st.divider()
        
        agora = datetime.now()
        item_para_remover = None
        
        for idx, m in enumerate(st.session_state.em_jornada):
            dt_fim = m.get("DataFim", agora)
            tempo_restante_min = int((dt_fim - agora).total_seconds() / 60)
            
            if tempo_restante_min <= 0:
                status = "🔴 EXCEDIDO"
                restante_fmt = "00h 00m"
            elif tempo_restante_min <= 60:
                status = "⚠️ ATENÇÃO"
                horas = tempo_restante_min // 60
                minutos = tempo_restante_min % 60
                restante_fmt = f"{horas:02d}h {minutos:02d}m"
            else:
                status = "🟢 NORMAL"
                horas = tempo_restante_min // 60
                minutos = tempo_restante_min % 60
                restante_fmt = f"{horas:02d}h {minutos:02d}m"
                
            c_st, c_maq, c_mat, c_ativ, c_trem, c_ab, c_rest, c_acao = st.columns([1.5, 1.8, 1.1, 1.1, 1.3, 1.2, 1.2, 1.2])
            
            c_st.write(status)
            c_maq.write(m.get("Maquinista", "-"))
            c_mat.write(m.get("Matrícula", "-"))
            c_ativ.write(m.get("Atividade", "-"))
            c_trem.write(f"{m.get('Trem', '-')} / {m.get('Locomotiva', '-')}")
            c_ab.write(m.get("Início", "-"))
            c_rest.write(restante_fmt)
            
            # Botão individual na linha
            if c_acao.button("🛑 Encerrar", key=f"btn_close_line_{idx}"):
                item_para_remover = idx
                
        # Processamento do encerramento
        if item_para_remover is not None:
            m_target = st.session_state.em_jornada[item_para_remover]
            fim_real_dt = datetime.now()
            inicio_real_dt = m_target.get("DataInicioDT", datetime.now())
            
            duracao_min = int((fim_real_dt - inicio_real_dt).total_seconds() / 60)
            if duracao_min < 0:
                duracao_min = 0
            dur_horas = duracao_min // 60
            dur_mins = duracao_min % 60
            duracao_formatada = f"{dur_horas:02d}h {dur_mins:02d}m"
            
            st.session_state.encerrados.append({
                "Maquinista": m_target.get("Maquinista", "-"),
                "Matrícula": m_target.get("Matrícula", "-"),
                "Atividade": m_target.get("Atividade", "-"),
                "Trem/Loco": f"{m_target.get('Trem', '-')} / {m_target.get('Locomotiva', '-')}",
                "Abertura": m_target.get("Início", "-"),
                "Fechamento": fim_real_dt.strftime("%d/%m %H:%M"),
                "Tempo de Caderno Aberto": duracao_formatada
            })
            
            st.session_state.em_jornada.pop(item_para_remover)
            salvar_dados()
            st.success(f"Caderno de {m_target.get('Maquinista')} encerrado!")
            st.rerun()
            
    else:
        st.info("Nenhum caderno aberto no momento. Dê o START na aba de 'Programação'.")

# --- ABA 2: LISTA DE ESPERA (LINHAS COM BOTÃO START NA PRÓPRIA LINHA) ---
with aba2:
    col_titulo, col_limpar = st.columns([3, 1])
    with col_titulo:
        st.subheader("📋 Escala Agendada")
    with col_limpar:
        if len(st.session_state.programados) > 0:
            if st.button("🗑️ Limpar Escala"):
                st.session_state.programados = []
                salvar_dados()
                st.rerun()
    
    if len(st.session_state.programados) > 0:
        # Cabeçalho da Lista Agendada
        col_maq, col_mat, col_ativ, col_trem, col_loco, col_trecho, col_act = st.columns([2, 1.2, 1.2, 1.2, 1.2, 2, 1.2])
        col_maq.markdown("**Maquinista**")
        col_mat.markdown("**Matrícula**")
        col_ativ.markdown("**Atividade**")
        col_trem.markdown("**Trem**")
        col_loco.markdown("**Locomotiva**")
        col_trecho.markdown("**Trecho**")
        col_act.markdown("**Ação**")
        st.divider()
        
        idx_start_target = None
        
        for idx, item in enumerate(st.session_state.programados):
            c_maq, c_mat, c_ativ, c_trem, c_loco, c_trecho, c_act = st.columns([2, 1.2, 1.2, 1.2, 1.2, 2, 1.2])
            
            c_maq.write(item.get("Maquinista", "-"))
            c_mat.write(item.get("Matrícula", "-"))
            c_ativ.write(item.get("Atividade", "-"))
            c_trem.write(item.get("Trem", "-"))
            c_loco.write(item.get("Locomotiva", "-"))
            c_trecho.write(item.get("Trecho", "-"))
            
            if c_act.button("▶️ Start", key=f"btn_start_line_{idx}"):
                idx_start_target = idx
                
        if idx_start_target is not None:
            item_start = st.session_state.programados[idx_start_target]
            inicio_dt = datetime.now()
            duracao_horas = DURACAO_ATIVIDADE.get(item_start.get('Atividade'), 8)
            fim_dt = inicio_dt + timedelta(hours=duracao_horas)
            
            st.session_state.em_jornada.append({
                "Maquinista": item_start.get("Maquinista", "-"),
                "Matrícula": item_start.get("Matrícula", "-"),
                "Atividade": item_start.get("Atividade", "Viagem"),
                "Trem": item_start.get("Trem", "-"),
                "Locomotiva": item_start.get("Locomotiva", "-"),
                "Início": inicio_dt.strftime("%d/%m %H:%M"),
                "Fim Previsto": fim_dt.strftime("%d/%m %H:%M"),
                "DataFim": fim_dt,
                "DataInicioDT": inicio_dt
            })
            
            st.session_state.programados.pop(idx_start_target)
            salvar_dados()
            st.success(f"Caderno de {item_start.get('Maquinista')} aberto!")
            st.rerun()
    else:
        st.info("Nenhuma programação carregada. Faça o upload da planilha ou lance manualmente no menu lateral.")

# --- ABA 3: HISTÓRICO ---
with aba3:
    st.subheader("📊 Histórico de Jornadas Concluídas")
    
    if len(st.session_state.encerrados) > 0:
        df_enc = pd.DataFrame(st.session_state.encerrados)
        st.dataframe(df_enc, use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Limpar Histórico"):
            st.session_state.encerrados = []
            salvar_dados()
            st.rerun()
    else:
        st.info("Nenhum caderno foi encerrado até o momento.")



