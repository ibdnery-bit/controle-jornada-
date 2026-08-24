import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Controle de Jornada - Maquinistas", layout="wide", page_icon="🚆")

st.title("🚆 Controle Operacional de Jornada")

# Banco de dados temporário na memória
if 'maquinistas' not in st.session_state:
    st.session_state.maquinistas = []

# --- MENU LATERAL: CADASTRO ---
st.sidebar.header("📋 Cadastrar Apresentação")

nome = st.sidebar.text_input("Nome / Matrícula do Maquinista")

opcoes_atividade = {
    "Auxílio (8h)": 8,
    "Manobra (6h)": 6,
    "Viagem (10h)": 10,
    "Outra Atividade": 8
}

atividade = st.sidebar.selectbox("Tipo de Atividade", list(opcoes_atividade.keys()))
horas_jornada = opcoes_atividade[atividade]

duracao = st.sidebar.number_input("Horas de Jornada", value=horas_jornada, min_value=1, max_value=12)

horario_apres = st.sidebar.time_input("Horário de Apresentação", value=datetime.now().time())

if st.sidebar.button("Registrar Maquinista"):
    if nome:
        hoje = datetime.now().date()
        inicio = datetime.combine(hoje, horario_apres)
        fim = inicio + timedelta(hours=duracao)
        
        st.session_state.maquinistas.append({
            "Nome": nome,
            "Atividade": atividade,
            "Início": inicio.strftime("%H:%M"),
            "Fim Previsto": fim.strftime("%H:%M"),
            "DataFim": fim
        })
        st.sidebar.success(f"{nome} registrado com sucesso!")
    else:
        st.sidebar.error("Informe o nome ou matrícula do maquinista.")

# --- PAINEL PRINCIPAL DE MONITORAMENTO ---
st.subheader("⏱️ Status em Tempo Real")

if st.session_state.maquinistas:
    agora = datetime.now()
    lista_exibicao = []
    
    for m in st.session_state.maquinistas:
        tempo_restante_min = int((m["DataFim"] - agora).total_seconds() / 60)
        
        if tempo_restante_min <= 0:
            status = "🔴 JORNADA ENCERRADA / EXCEDIDA"
            restante_fmt = "00h 00m"
        elif tempo_restante_min <= 60:
            status = "⚠️ ATENÇÃO: Menos de 1h restante"
            horas = tempo_restante_min // 60
            minutos = tempo_restante_min % 60
            restante_fmt = f"{horas:02d}h {minutos:02d}m"
        else:
            status = "🟢 Em Operação Normal"
            horas = tempo_restante_min // 60
            minutos = tempo_restante_min % 60
            restante_fmt = f"{horas:02d}h {minutos:02d}m"
            
        lista_exibicao.append({
            "Maquinista": m["Nome"],
            "Atividade": m["Atividade"],
            "Apresentação": m["Início"],
            "Fim Previsto": m["Fim Previsto"],
            "Tempo Restante": restante_fmt,
            "Status": status
        })
        
    df = pd.DataFrame(lista_exibicao)
    st.dataframe(df, use_container_width=True)
    
    if st.button("🔄 Atualizar Painel"):
        st.rerun()
else:
    st.info("Nenhum maquinista registrado no momento.")
