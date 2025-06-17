import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import folium
from streamlit_folium import st_folium
from datetime import datetime
from PIL import Image
import io
import os

# === Título ===
st.set_page_config(layout="wide")

# === Logotipo ===
logo = Image.open("logo_painel.png")
st.image(logo, width=350)

st.title("Dashboard de Tarefas Judiciais")

# === Leitura automática da planilha ===
nome_arquivo = "tarefas_sapiens_simuladas.xlsx"
caminho_arquivo = os.path.join(os.path.dirname(__file__), nome_arquivo)

try:
    df = pd.read_excel(caminho_arquivo)
    df.columns = df.columns.str.strip().str.lower()
except Exception as e:
    st.error(f"Erro ao carregar o arquivo automaticamente: {e}")
    st.stop()

# === Processamento ===
hoje = datetime(2025, 4, 30)
df['final prazo'] = pd.to_datetime(df['final prazo'], errors='coerce')
df['status'] = df['final prazo'].apply(lambda x: 'Em atraso' if pd.notnull(x) and x < hoje else 'Dentro do prazo')
df['dias_em_atraso'] = (hoje - df['final prazo']).dt.days
df['dias_para_vencer'] = (df['final prazo'] - hoje).dt.days

# === Filtros ===
st.sidebar.header("Filtros")
status_filtro = st.sidebar.selectbox("Status", options=["Todos"] + sorted(df['status'].dropna().unique().tolist()))
usuarios = sorted(df['usuário responsável'].dropna().unique().tolist())
usuario_filtro = st.sidebar.multiselect("Usuário Responsável", options=usuarios, default=usuarios)

setor_filtro = st.sidebar.multiselect("Setor de Origem", options=sorted(df['setor de origem'].dropna().unique()),
                                      default=sorted(df['setor de origem'].dropna().unique()))

df_filtrado = df.copy()
if status_filtro != "Todos":
    df_filtrado = df_filtrado[df_filtrado['status'] == status_filtro]
df_filtrado = df_filtrado[df_filtrado['usuário responsável'].isin(usuario_filtro)]
df_filtrado = df_filtrado[df_filtrado['setor de origem'].isin(setor_filtro)]

# === Menu Lateral: Botão de Download do Relatório ===
with st.sidebar:
    st.markdown("---")
    st.subheader("📥 Top 20 - Maior Atraso")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_filtrado.to_excel(writer, index=False, sheet_name='Tarefas Filtradas')
        df_top20 = df[df['status'] == 'Em atraso'].sort_values(by='dias_em_atraso', ascending=False).head(20)
        df_top20.to_excel(writer, index=False, sheet_name='Top 20 Atrasos')
    st.download_button(
        label="📄 Baixar Excel com dados",
        data=output.getvalue(),
        file_name="relatorio_tarefas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.markdown("---")

# === Gráfico Pizza: Status ===
st.subheader("Distribuição de Status")
status_counts = df_filtrado['status'].value_counts()
fig1, ax1 = plt.subplots(figsize=(5, 5))
status_counts.plot.pie(autopct='%1.1f%%', ax=ax1)
ax1.set_ylabel('')
st.pyplot(fig1)

# === Barras: Tarefas por Usuário ===
st.subheader("Tarefas por Usuário")
tarefas_por_usuario = df_filtrado['usuário responsável'].value_counts()
fig2, ax2 = plt.subplots(figsize=(8, 4))
tarefas_por_usuario.plot(kind='bar', ax=ax2, color='#6699cc')
ax2.set_title("Distribuição de Tarefas por Usuário")
st.pyplot(fig2)

# === Percentual de Atraso por Usuário ===
st.subheader("Percentual de Atraso por Usuário")
total_por_usuario = df['usuário responsável'].value_counts()
atrasadas = df[df['status'] == 'Em atraso']
atrasadas_por_usuario = atrasadas['usuário responsável'].value_counts()
percentual_atraso = (atrasadas_por_usuario / total_por_usuario * 100).sort_values(ascending=False)
fig3, ax3 = plt.subplots(figsize=(8, 4))
percentual_atraso.plot(kind='bar', ax=ax3, color='#ffcc00')
ax3.set_ylabel('% de Atraso')
st.pyplot(fig3)

# === Previsão de Vencimento ===
st.subheader("Previsão de Vencimento")
df_futuro = df[df['status'] == 'Dentro do prazo'].copy()
def faixa_vencimento(d):
    if d <= 7:
        return '0-7 dias'
    elif d <= 15:
        return '8-15 dias'
    elif d <= 30:
        return '16-30 dias'
    else:
        return '+30 dias'
df_futuro['faixa'] = df_futuro['dias_para_vencer'].apply(faixa_vencimento)
contagem_faixa = df_futuro['faixa'].value_counts().reindex(['0-7 dias', '8-15 dias', '16-30 dias', '+30 dias'], fill_value=0)
fig4, ax4 = plt.subplots(figsize=(6, 4))
contagem_faixa.plot(kind='bar', ax=ax4, color='#66c2a5')
ax4.set_ylabel('Qtd de Processos')
st.pyplot(fig4)

# === Mapa Interativo ===
st.subheader("Mapa de Tarefas por Setor")
coordenadas = {
    'TJSE': [-10.9472, -37.0731],
    'TJPE': [-8.0543, -34.8813],
    'TJPB': [-7.1151, -34.8641],
    'TJRN': [-5.7945, -35.2110],
    'TRF5': [-7.5, -38.5]
}
contagem_setor = df_filtrado['setor de origem'].value_counts()
mapa = folium.Map(location=[-8.5, -35.0], zoom_start=6)
for setor, count in contagem_setor.items():
    if setor in coordenadas:
        lat, lon = coordenadas[setor]
        folium.CircleMarker(
            location=[lat, lon],
            radius=min(10, count**0.5 + 2),
            popup=f"{setor}: {count} tarefas",
            tooltip=f"{setor}: {count} tarefas",
            color='blue',
            fill=True,
            fill_opacity=0.6
        ).add_to(mapa)
st_folium(mapa, width=700, height=500)

# === Tabela: Top 20 Processos com Maior Atraso ===
st.subheader("Top 20 Processos com Maior Atraso")
df_top20 = df[df['status'] == 'Em atraso'].sort_values(by='dias_em_atraso', ascending=False).head(20)
st.dataframe(df_top20[['processo', 'usuário responsável', 'setor de origem', 'dias_em_atraso']])
