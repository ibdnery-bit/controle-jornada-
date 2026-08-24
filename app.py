import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import json
import os
import io

st.set_page_config(page_title="Controle Operacional de Jornada - MRS", layout="wide", page_icon="🚆")

# --- ESTILIZAÇÃO CSS CORPORATIVA (CARDS E TIPOGRAFIA) ---
st.markdown("""
    <style>
    /* Estilização dos Cards KPI */
    .kpi-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 12px 16px;
        border-left: 5px solid #6c757d;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }
    .kpi-normal { border-left-color: #28a745 !important; }
    .kpi-atencao { border-left-color: #ffc107 !important; }
    .kpi-critico { border-left-color: #dc3545 !important; }
    
    .kpi-title {
        font-size: 0.85rem;
        color: #6c757d;
        font-weight: 600;
        margin-bottom: 2px;
    }
    .kpi-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #212529;
    }
    </style>
""", unsafe_allow_html=True)

ARQUIVO_BANCO = "dados_jornada.json"

DURACAO_ATIVIDADE = {
    "Viagem": 10,
    "Manobra": 6,
    "Auxílio": 8,
    "Manutenção": 8,
    "Outra Atividade": 8
}

HORAS_DESCANSO_REGULAMENTAR = 11

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

def gerar_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Jornadas')
    return output.getvalue()

def verificar_descanso(matricula, dt_inicio_pretendida):
    for enc in reversed(st.session_state.get("encerrados", [])):
        if str(enc.get("Matrícula")) == str(matricula):
            dt_apto_str = enc.get("Apto em", "")
            if dt_apto_str:
                try:
                    dt_apto = datetime.strptime(dt_apto_str, "%d/%m %H:%M")
                    dt_apto = dt_apto.replace(year=dt_inicio_pretendida.year)
                    if dt_inicio_pretendida < dt_apto:
                        return False, dt_apto_str
                except ValueError:
                    pass
            break
    return True, ""

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

# --- IMPORTAÇÃO ---
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

# --- LANÇAMENTO MANUAL ---
st.sidebar.subheader("✍️ Lançamento Manual")

with st.sidebar.expander("➕ Inserir Manualmente"):
    with st.form("form_manual", clear_on_submit=True):
        m_nome = st.text_input("Nome do Maquinista")
        m_mat = st.text_input("Matrícula")
        m_ativ = st.selectbox("Atividade", list(DURACAO_ATIVIDADE.keys()))
        m_trem = st.text_input("Trem / Prefixo")
        m_loco = st.text_input("Locomotiva")
        m_orig = st.text_input("Origem")
        m_dest = st.text_input("Destino")
        
        btn_manual = st.form_submit_button("Confirmar Lançamento")
        
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

# --- ABAS ---
aba1, aba2, aba3 = st.tabs(["⏱️ Jornadas em Andamento", "📋 Programação (Aguardando Start)", "📊 Histórico e Performance"])

# --- ABA 1: OPERAÇÃO ---
with aba1:
    st.subheader("🟢 Maquinistas em Operação")
    
    if len(st.session_state.em_jornada) > 0:
        agora = datetime.now()
        dados_tabela = []
        texto_whatsapp_op = f"*📋 RESUMO DE JORNADAS EM OPERAÇÃO - {agora.strftime('%d/%m/%Y %H:%M')}*\n\n"
        
        c_normal, c_atencao, c_critico, c_total = 0, 0, 0, len(st.session_state.em_jornada)
        
        for idx, m in enumerate(st.session_state.em_jornada):
            dt_fim = m.get("DataFim", agora)
            tempo_restante_min = int((dt_fim - agora).total_seconds() / 60)
            
            if tempo_restante_min <= 0:
                status = "🔴 EXCEDIDO"
                restante_fmt = "00h 00m"
                c_critico += 1
            elif tempo_restante_min <= 45:
                status = "🔴 RISCO ALTO (<45m)"
                horas = tempo_restante_min // 60
                minutos = tempo_restante_min % 60
                restante_fmt = f"{horas:02d}h {minutos:02d}m"
                c_atencao += 1
            elif tempo_restante_min <= 90:
                status = "⚠️ ATENÇÃO (<90m)"
                horas = tempo_restante_min // 60
                minutos = tempo_restante_min % 60
                restante_fmt = f"{horas:02d}h {minutos:02d}m"
                c_atencao += 1
            else:
                status = "🟢 NORMAL"
                horas = tempo_restante_min // 60
                minutos = tempo_restante_min % 60
                restante_fmt = f"{horas:02d}h {minutos:02d}m"
                c_normal += 1
                
            dados_tabela.append({
                "Status": status,
                "Maquinista": m.get("Maquinista", "-"),
                "Matrícula": m.get("Matrícula", "-"),
                "Atividade": m.get("Atividade", "-"),
                "Trem / Loco": f"{m.get('Trem', '-')} / {m.get('Locomotiva', '-')}",
                "Abertura": m.get("Início", "-"),
                "Restante": restante_fmt,
                "Encerrar Caderno?": False
            })
            
            texto_whatsapp_op += f"👤 *{m.get('Maquinista')}* (Mat: {m.get('Matrícula')})\n"
            texto_whatsapp_op += f"🔹 Atividade: {m.get('Atividade')} | Trem/Loco: {m.get('Trem')}/{m.get('Locomotiva')}\n"
            texto_whatsapp_op += f"⏱️ Abertura: {m.get('Início')} | Restante: {restante_fmt} [{status}]\n\n"

        # --- NOVO PAINEL COMPACTO DE CARDS KPI (VISUAL PROFISSIONAL) ---
        k1, k2, k3, k4 = st.columns(4)
        
        with k1:
            st.markdown(f'''
                <div class="kpi-card">
                    <div class="kpi-title">Total em Operação</div>
                    <div class="kpi-value">{c_total}</div>
                </div>
            ''', unsafe_allow_html=True)
            
        with k2:
            st.markdown(f'''
                <div class="kpi-card kpi-normal">
                    <div class="kpi-title">🟢 Em Ritmo Normal</div>
                    <div class="kpi-value">{c_normal}</div>
                </div>
            ''', unsafe_allow_html=True)
            
        with k3:
            st.markdown(f'''
                <div class="kpi-card kpi-atencao">
                    <div class="kpi-title">⚠️ Em Atenção / Risco</div>
                    <div class="kpi-value">{c_atencao}</div>
                </div>
            ''', unsafe_allow_html=True)
            
        with k4:
            st.markdown(f'''
                <div class="kpi-card kpi-critico">
                    <div class="kpi-title">🔴 Excedidos</div>
                    <div class="kpi-value">{c_critico}</div>
                </div>
            ''', unsafe_allow_html=True)
            
        df_operacao = pd.DataFrame(dados_tabela)

        busca_op = st.text_input("🔍 Filtrar Operação (Nome, Matrícula ou Trem):", "", placeholder="Digite para buscar...")
        if busca_op:
            df_operacao = df_operacao[
                df_operacao['Maquinista'].str.contains(busca_op, case=False, na=False) |
                df_operacao['Matrícula'].str.contains(busca_op, case=False, na=False) |
                df_operacao['Trem / Loco'].str.contains(busca_op, case=False, na=False)
            ]

        edited_df = st.data_editor(
            df_operacao,
            use_container_width=True,
            hide_index=True,
            disabled=["Status", "Maquinista", "Matrícula", "Atividade", "Trem / Loco", "Abertura", "Restante"],
            key="editor_operacao"
        )

        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        
        with col_btn1:
            if st.button("🔄 Atualizar Tempos", use_container_width=True):
                st.rerun()
                
        with col_btn2:
            df_export = df_operacao.drop(columns=["Encerrar Caderno?"])
            excel_bytes = gerar_excel(df_export)
            st.download_button(
                label="📥 Exportar Excel",
                data=excel_bytes,
                file_name=f"jornadas_em_andamento_{agora.strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
        with col_btn3:
            with st.popover("📱 Resumo WhatsApp", use_container_width=True):
                st.markdown("**Copie o texto abaixo para enviar:**")
                st.code(texto_whatsapp_op, language="text")

        linhas_encerradas = edited_df[edited_df["Encerrar Caderno?"] == True]
        
        if not linhas_encerradas.empty:
            idx_selecionado = linhas_encerradas.index[0]
            m_target = st.session_state.em_jornada[idx_selecionado]
            
            st.markdown("---")
            st.warning(f"🛑 **Ajuste de Encerramento do Caderno:** {m_target.get('Maquinista')}")
            
            col_d, col_h, col_btn = st.columns([1.5, 1.5, 1.5])
            with col_d:
                data_fechamento = st.date_input("Data de Fechamento", value=datetime.now().date(), key="dt_fechar")
            with col_h:
                hora_fechamento = st.time_input("Hora de Fechamento", value=time(0, 0), key="hr_fechar")
                
            with col_btn:
                st.write("")
                st.write("")
                if st.button("Confirmar Fechamento Manual", type="primary"):
                    fim_real_dt = datetime.combine(data_fechamento, hora_fechamento)
                    inicio_real_dt = m_target.get("DataInicioDT", datetime.now())
                    
                    duracao_min = int((fim_real_dt - inicio_real_dt).total_seconds() / 60)
                    if duracao_min < 0:
                        duracao_min = 0
                    dur_horas = duracao_min // 60
                    dur_mins = duracao_min % 60
                    duracao_formatada = f"{dur_horas:02d}h {dur_mins:02d}m"
                    
                    dt_apto_proxima = fim_real_dt + timedelta(hours=HORAS_DESCANSO_REGULAMENTAR)
                    
                    st.session_state.encerrados.append({
                        "Maquinista": m_target.get("Maquinista", "-"),
                        "Matrícula": m_target.get("Matrícula", "-"),
                        "Atividade": m_target.get("Atividade", "-"),
                        "Trem/Loco": f"{m_target.get('Trem', '-')} / {m_target.get('Locomotiva', '-')}",
                        "Abertura": m_target.get("Início", "-"),
                        "Fechamento": fim_real_dt.strftime("%d/%m %H:%M"),
                        "Tempo Aberto": duracao_formatada,
                        "Apto em": dt_apto_proxima.strftime("%d/%m %H:%M")
                    })
                    
                    st.session_state.em_jornada.pop(idx_selecionado)
                    salvar_dados()
                    st.success(f"Caderno de {m_target.get('Maquinista')} encerrado! Apto em: {dt_apto_proxima.strftime('%d/%m %H:%M')}")
                    st.rerun()

    else:
        st.info("Nenhum caderno aberto no momento. Dê o START na aba de 'Programação'.")

# --- ABA 2: PROGRAMAÇÃO ---
with aba2:
    st.subheader("📋 Escala Agendada")
    
    if len(st.session_state.programados) > 0:
        dados_prog = []
        texto_whatsapp_prog = f"*📋 PROGRAMAÇÃO DE ESCALA - {datetime.now().strftime('%d/%m/%Y')}*\n\n"
        
        for item in st.session_state.programados:
            dados_prog.append({
                "Maquinista": item.get("Maquinista", "-"),
                "Matrícula": item.get("Matrícula", "-"),
                "Atividade": item.get("Atividade", "-"),
                "Trem": item.get("Trem", "-"),
                "Loco": item.get("Locomotiva", "-"),
                "Trecho": item.get("Trecho", "-"),
                "Dar Start?": False
            })
            
            texto_whatsapp_prog += f"👤 *{item.get('Maquinista')}* (Mat: {item.get('Matrícula')})\n"
            texto_whatsapp_prog += f"🔹 Atividade: {item.get('Atividade')} | Trem/Loco: {item.get('Trem')}/{item.get('Locomotiva')}\n"
            texto_whatsapp_prog += f"📍 Trecho: {item.get('Trecho')}\n\n"
            
        df_prog = pd.DataFrame(dados_prog)
        
        edited_prog = st.data_editor(
            df_prog,
            use_container_width=True,
            hide_index=True,
            disabled=["Maquinista", "Matrícula", "Atividade", "Trem", "Loco", "Trecho"],
            key="editor_programados"
        )
        
        col_p1, col_p2, col_p3 = st.columns([1, 1, 1])
        
        with col_p1:
            df_prog_export = df_prog.drop(columns=["Dar Start?"])
            st.download_button(
                label="📥 Exportar Excel",
                data=gerar_excel(df_prog_export),
                file_name=f"programacao_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
        with col_p2:
            with st.popover("📱 Resumo WhatsApp", use_container_width=True):
                st.markdown("**Copie o texto abaixo para enviar:**")
                st.code(texto_whatsapp_prog, language="text")
                
        with col_p3:
            if st.button("🗑️ Limpar Escala", use_container_width=True):
                st.session_state.programados = []
                salvar_dados()
                st.rerun()

        linhas_start = edited_prog[edited_prog["Dar Start?"] == True]
        
        if not linhas_start.empty:
            idx_start_sel = linhas_start.index[0]
            item_start = st.session_state.programados[idx_start_sel]
            
            st.markdown("---")
            st.info(f"🚀 **Ajuste de Abertura do Caderno:** {item_start.get('Maquinista')}")
            
            col_sd, col_sh, col_sbtn = st.columns([1.5, 1.5, 1.5])
            with col_sd:
                data_inicio = st.date_input("Data de Início", value=datetime.now().date(), key="dt_start")
            with col_sh:
                hora_inicio = st.time_input("Hora de Início", value=time(0, 0), key="hr_start")
                
            with col_sbtn:
                st.write("")
                st.write("")
                if st.button("Confirmar Start Manual", type="primary"):
                    inicio_dt = datetime.combine(data_inicio, hora_inicio)
                    apto, dt_apto_str = verificar_descanso(item_start.get("Matrícula"), inicio_dt)
                    
                    if not apto:
                        st.error(f"🛑 **BLOQUEIO DE SEGURANÇA:** O maquinista {item_start.get('Maquinista')} está em período de descanso regulamentar! Estará apto apenas em: **{dt_apto_str}**.")
                    else:
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
                        
                        st.session_state.programados.pop(idx_start_sel)
                        salvar_dados()
                        st.success(f"Caderno de {item_start.get('Maquinista')} aberto com sucesso!")
                        st.rerun()
    else:
        st.info("Nenhuma programação carregada. Faça o upload da planilha ou lance manualmente no menu lateral.")

# --- ABA 3: HISTÓRICO ---
with aba3:
    st.subheader("📊 Histórico e Gestão de Interjornada")
    
    if len(st.session_state.encerrados) > 0:
        df_enc = pd.DataFrame(st.session_state.encerrados)
        
        st.dataframe(df_enc, use_container_width=True, hide_index=True)
        
        col_h1, col_h2 = st.columns([1, 1])
        with col_h1:
            st.download_button(
                label="📥 Exportar Histórico para Excel (.xlsx)",
                data=gerar_excel(df_enc),
                file_name=f"historico_jornadas_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with col_h2:
            if st.button("🗑️ Limpar Histórico", use_container_width=True):
                st.session_state.encerrados = []
                salvar_dados()
                st.rerun()
    else:
        st.info("Nenhum caderno foi encerrado até o momento.")
