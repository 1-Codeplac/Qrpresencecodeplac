import streamlit as st
from supabase import create_client
import os
import re
import math
from streamlit_js_eval import get_geolocation

# --- CONFIGURAÇÕES DE SEGURANÇA ---
URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_KEY")
MODO_TESTE = os.getenv("MODO_TESTE", "DESLIGADO")

if URL and KEY:
    supabase = create_client(URL, KEY)
else:
    st.error("Erro: Chaves de API não configuradas no ambiente.")

# --- COORDENADAS UNICEPLAC (GAMA) ---
LAT_FACULDADE = -16.00122196328053
LON_FACULDADE = -48.05097423558202
RAIO_PERMITIDO_KM = 0.5


# --- FUNÇÕES AUXILIARES ---
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (
        math.sin(dLat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dLon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def formatar_cpf(cpf_bruto):
    numeros = re.sub(r"\D", "", cpf_bruto)
    if len(numeros) != 11:
        return None
    return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"


CURSOS = [
    "Análise e Desenvolvimento de Sistemas",
    "Ciência da Computação",
    "Engenharia de Software",
    "Gestão de Tecnologia da Informação",
]
SEMESTRES = [f"{i}º Semestre" for i in range(1, 9)]

# --- INTERFACE E ESTILIZAÇÃO CODEPLAC ---
st.set_page_config(page_title="Check-in Codeplac", page_icon="💻", layout="centered")

st.markdown(
    """
    <style>
    .stApp { background-color: #000b17; }
    #MainMenu, footer, header { visibility: hidden; }
    
    .formulario-card-box {
        background: rgba(13, 25, 33, 0.4);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(0, 234, 255, 0.3);
        border-radius: 20px;
        padding: 40px;
    }
    
    h1 { color: #00EAFF !important; text-align: center; letter-spacing: 2px; }
    
    /* Estilizando o formulário do Streamlit para combinar */
    [data-testid="stForm"] {
        background: transparent !important;
        border: none !important;
    }
    
    input, .stSelectbox div[data-baseweb="select"] {
        background: rgba(0, 20, 30, 0.6) !important;
        border: 1px solid #1a4a5a !important;
        color: #fff !important;
        border-radius: 8px !important;
    }
    
    button[kind="primaryFormSubmit"] {
        background: transparent !important;
        border: 1px solid #00EAFF !important;
        color: #00EAFF !important;
        border-radius: 50px !important;
        text-transform: uppercase;
        font-weight: bold;
        width: 100%;
    }
    
    button[kind="primaryFormSubmit"]:hover {
        background: #00EAFF !important;
        color: #000b17 !important;
        box-shadow: 0 0 20px rgba(0, 234, 255, 0.4);
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Wrapper Principal
st.markdown("<div class='formulario-card-box'>", unsafe_allow_html=True)
st.markdown("<h1>REGISTRO DE PRESENÇA</h1>", unsafe_allow_html=True)

# --- LÓGICA DE GEOLOCALIZAÇÃO ---
if MODO_TESTE == "DESLIGADO":
    loc = get_geolocation()
    if not loc:
        st.warning("Aguardando permissão de GPS...")
        if st.button("🔄 TENTAR NOVAMENTE"):
            st.rerun()
        st.stop()

    distancia = calcular_distancia(
        loc["coords"]["latitude"],
        loc["coords"]["longitude"],
        LAT_FACULDADE,
        LON_FACULDADE,
    )

    if distancia > RAIO_PERMITIDO_KM:
        st.error(
            f"❌ Você precisa ir até o local do evento para marcar sua presença :) (Distância: {distancia:.2f} km)"
        )
        st.stop()
    else:
        st.success("✅ Localização confirmada!")

# --- FORMULÁRIO ---
with st.form("form_registro", clear_on_submit=True):
    nome = st.text_input("NOME COMPLETO")
    cpf_input = st.text_input("CPF (APENAS OS 11 NÚMEROS)", max_chars=11)
    col1, col2 = st.columns(2)
    with col1:
        curso = st.selectbox("CURSO", CURSOS)
        periodo = st.selectbox("PERÍODO", ["Matutino", "Noturno"])
    with col2:
        semestre = st.selectbox("SEMESTRE", SEMESTRES)
        turma = st.text_input("TURMA (OPCIONAL)")

    if st.form_submit_button("REGISTRAR PRESENÇA"):
        cpf_limpo = formatar_cpf(cpf_input)
        if not nome or not cpf_input:
            st.warning("Por favor, preencha o Nome e o CPF!")
        elif not cpf_limpo:
            st.error("CPF Inválido!")
        else:
            try:
                dados = {
                    "nome_completo": nome.strip().upper(),
                    "cpf": cpf_limpo,
                    "curso": curso,
                    "semestre": semestre,
                    "turma": turma.strip().upper() if turma else "N/A",
                    "periodo": periodo,
                }
                supabase.table("presencas").insert(dados).execute()
                st.success(f"Tudo certo, {nome.split()[0]}!")
                st.balloons()
            except Exception as e:
                st.error("⚠️ Você já registrou presença hoje!")

st.markdown("</div>", unsafe_allow_html=True)  # Fecha card-box

