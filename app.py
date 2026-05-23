import streamlit as st
from supabase import create_client
import os
import re
import math
import json
import unicodedata
from streamlit_js_eval import get_geolocation

# --- CONFIGURAÇÕES ---
URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_KEY")
MODO_TESTE = os.getenv("MODO_TESTE", "DESLIGADO")

if URL and KEY:
    supabase = create_client(URL, KEY)
else:
    st.error("Erro: Chaves de API não configuradas.")

LAT_FACULDADE = -16.00122196328053
LON_FACULDADE = -48.05097423558202
RAIO_PERMITIDO_KM = 0.5


# --- FUNÇÕES ---
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
    return (
        f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"
        if len(numeros) == 11
        else None
    )


def buscar_e_organizar_dados():
    response = supabase.table("presencas").select("*").execute()
    dados = response.data or []
    relatorio = {}
    for item in dados:
        chave = f"{item.get('curso', 'N/A')} - {item.get('periodo', 'N/A')} {item.get('semestre', 'N/A')}"  # type: ignore
        if chave not in relatorio:
            relatorio[chave] = []
        relatorio[chave].append(item.get("nome_completo", "Sem Nome"))  # type: ignore

    for chave in relatorio:
        # Ordenação que ignora acentos
        relatorio[chave].sort(
            key=lambda x: unicodedata.normalize("NFKD", x)
            .encode("ASCII", "ignore")
            .decode("utf-8")
            .lower()
        )
    return relatorio


# --- INTERFACE ---
st.set_page_config(page_title="Check-in Codeplac", page_icon="💻", layout="centered")

st.markdown(
    """
    <style>
    .stApp { background-color: #000b17; }
    .formulario-card-box { background: rgba(13, 25, 33, 0.4); backdrop-filter: blur(15px); border: 1px solid rgba(0, 234, 255, 0.3); border-radius: 20px; padding: 40px; }
    h1 { color: #00EAFF !important; text-align: center; letter-spacing: 2px; }
    button[kind="primaryFormSubmit"] { background: transparent !important; border: 1px solid #00EAFF !important; color: #00EAFF !important; border-radius: 50px !important; width: 100%; font-weight: bold; }
    </style>
""",
    unsafe_allow_html=True,
)

st.markdown("<div class='formulario-card-box'>", unsafe_allow_html=True)

# --- LÓGICA DE ROTA ADMIN ---
query_params = st.query_params
if query_params.get("admin") == "akyparfaitcoisas":
    st.title("🔒 Painel Administrativo")
    if st.text_input("Senha", type="password") == "logoeuqueamavameucavalo":
        if st.button("Gerar Relatório JSON"):
            dados = buscar_e_organizar_dados()
            st.download_button(
                "Baixar JSON",
                json.dumps(dados, indent=4, ensure_ascii=False),
                "presencas.json",
                "application/json",
            )
            st.json(dados)
    else:
        st.warning("Acesso restrito.")
else:
    # --- PÁGINA DO ALUNO ---
    st.markdown("<h1>REGISTRO DE PRESENÇA</h1>", unsafe_allow_html=True)
    if MODO_TESTE == "DESLIGADO":
        loc = get_geolocation()
        if not loc or "coords" not in loc:
            st.warning(
                "Não foi possível conseguir sua localização, ative e tente novamente."
            )
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
                f"❌ Você precisa estar no local do evento. (Distância: {distancia:.2f} km)"
            )
            st.stop()
        else:
            st.success("✅ Localização confirmada!")

    with st.form("form_registro", clear_on_submit=True):
        nome = st.text_input("NOME COMPLETO")
        cpf_input = st.text_input("CPF (APENAS OS 11 NÚMEROS)", max_chars=11)
        col1, col2 = st.columns(2)
        with col1:
            curso = st.selectbox(
                "CURSO",
                [
                    "Análise e Desenvolvimento de Sistemas",
                    "Ciência da Computação",
                    "Engenharia de Software",
                    "Gestão de Tecnologia da Informação",
                ],
            )
            periodo = st.selectbox("PERÍODO", ["Matutino", "Noturno"])
        with col2:
            semestre = st.selectbox("SEMESTRE", [f"{i}º Semestre" for i in range(1, 9)])
            turma = st.text_input("TURMA (OPCIONAL)")

        if st.form_submit_button("REGISTRAR PRESENÇA"):
            cpf_limpo = formatar_cpf(cpf_input)
            if not nome or not cpf_limpo:
                st.warning("Preencha todos os campos corretamente!")
            else:
                try:
                    supabase.table("presencas").insert(
                        {
                            "nome_completo": nome.strip().upper(),
                            "cpf": cpf_limpo,
                            "curso": curso,
                            "semestre": semestre,
                            "turma": turma.strip().upper() if turma else "N/A",
                            "periodo": periodo,
                        }
                    ).execute()
                    st.success("Tudo certo!")
                    st.balloons()
                except Exception:
                    st.error("⚠️ Você já registrou presença hoje!")

st.markdown("</div>", unsafe_allow_html=True)
