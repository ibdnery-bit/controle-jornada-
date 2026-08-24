import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Controle Operacional de Jornada - MRS", layout="wide", page_icon="🚆")

st.title("🚆 Controle Operacional de Jornada")

# Mapeamento padrao de horas por atividade
DURACAO_ATIVIDADE = {
    "Viagem": 10,
    "Manobra": 6,
    "Auxílio": 8,
    "Manutenção": 8,
    "Outra Atividade": 8
}

# Inicializacao da memoria do app
if 'programados' not in st.session_state:
    st.session_state.programados = []

if 'em_jornada' not in st.session_state:
    st.session_state.em_jornada = []

st.sidebar.header("⚙️ Opções e Carga")

# --- IMPORTACAO DA PLANILHA ---
st.sidebar.subheader("📂 Programação Diária (.xlsx / .csv)")
arquivo_enviado = st.sidebar.file_uploader("Carregar Escala do Dia", type=["xlsx", "csv"])

if arquivo_enviado is not None:
    try:
        if arquivo_enviado.name.endswith('.csv'):
            df_importado = pd.read_csv(arquivo_enviado)
        else:
            df_importado = pd.read_excel(arquivo_enviado)
            
        if st.sidebar.button("Carregar Programação"):
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
                
            st.session_state.programados = novos_programados
            st.sidebar.success(f"{len(novos_programados)} maquinistas carregados na programação!")
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"Erro ao ler arquivo: {e}")

st.sidebar.markdown("---")

# --- NAVEGACAO POR ABAS ---
aba1, aba2 = st.tabs(["⏱️ Jornadas em Andamento", "📋 Programação (Aguardando Start)"])

# --- ABA 1: EM OPERACAO ---
with aba1:
    st.subheader("🟢 Maquinistas com Caderno Aberto / Em Operação")
    
    if st.session_state.em_jornada:
        agora = datetime.now()
        lista_exibicao = []
        
        for idx, m in enumerate(st.session_state.em_jornada):
            tempo_restante_min = int((m["DataFim"] - agora).total_seconds() / 60)
            
            if tempo_restante_min <= 0:
                status = "🔴 JORNADA EXCEDIDA / ENCERRAR"
                restante_fmt = "00h 00m"
            elif tempo_restante_min <= 60:
                status = "⚠️ ATENÇÃO: Menos de 1h"
                horas = tempo_restante_min // 60
                minutos = tempo_restante_min % 60
                restante_fmt = f"{horas:02d}h {minutos:02d}m"
            else:
                status = "🟢 Operação Normal"
                horas = tempo_restante_min // 60
                minutos = tempo_restante_min % 60
                restante_fmt = f"{horas:02d}h {minutos:02d}m"
                
            lista_exibicao.append({
                "Maquinista": m["Maquinista"],
                "Matrícula": m["Matrícula"],
                "Atividade": m["Atividade"],
                "Trem/Loco": f"{m['Trem']} / {m['Locomotiva']}",
                "Abertura Caderno": m["Início"],
                "Fim Previsto": m["Fim Previsto"],
                "Tempo Restante": restante_fmt,
                "Status": status
            })
            
        st.dataframe(pd.DataFrame(lista_exibicao), use_container_width=True)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔄 Atualizar Tempos"):
                st.rerun()
        with col_btn2:
            if st.button("🗑️ Encerrar / Limpar Todos"):
                st.session_state.em_jornada = []
                st.rerun()
    else:
        st.info("Nenhum caderno aberto no momento. Dê o START na aba de 'Programação'.")

# --- ABA 2: LISTA DE ESPERA E START ---
with aba2:
    st.subheader("📋 Lista da Escala do Dia")
    
    if st.session_state.programados:
        for idx, item in enumerate(st.session_state.programados):
            col_info, col_acao = st.columns([4, 1])
            
            with col_info:
                st.write(f"**{item['Maquinista']}** (Matrícula: {item['Matrícula']}) | **Atividade:** {item['Atividade']} | **Trem/Loco:** {item['Trem']} / {item['Locomotiva']} | **Trecho:** {item['Trecho']}")
                
            with col_acao:
                if st.button(f"▶️ Abrir Caderno", key=f"start_{idx}"):
                    agora = datetime.now()
                    duracao_horas = DURACAO_ATIVIDADE.get(item['Atividade'], 8)
                    fim = agora + timedelta(hours=duracao_horas)
                    
                    st.session_state.em_jornada.append({
                        "Maquinista": item["Maquinista"],
                        "Matrícula": item["Matrícula"],
                        "Atividade": item["Atividade"],
                        "Trem": item["Trem"],
                        "Locomotiva": item["Locomotiva"],
                        "Início": agora.strftime("%H:%M"),
                        "Fim Previsto": fim.strftime("%H:%M"),
                        "DataFim": fim
                    })
                    
                    st.session_state.programados.pop(idx)
                    st.success(f"Caderno de {item['Maquinista']} aberto às {agora.strftime('%H:%M')}!")
                    st.rerun()
            st.divider()
    else:
        st.info("Nenhuma programação carregada. Faça o upload da planilha no menu lateral.")
