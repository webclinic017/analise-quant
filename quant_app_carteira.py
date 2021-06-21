import streamlit as st
from streamlit.hashing import _CodeHasher
import numpy as np
import pandas as pd
import yfinance as yf
import investpy as inv
import time
import matplotlib.pyplot as plt
import plotly.express as px
import seaborn as sns
import cufflinks as cf
import datetime
from datetime import date
import math

def carteira(state):

  st.header('Análise da Carteira')
  with st.form(key='Inserir_Ativos'):
    st.markdown('Insira os Ativos que compõem sua Carteira')
    col1, col2 = st.beta_columns(2)
    with col1:
      state.papel = st.selectbox('Insira o Ativo', state.stocks_df, help='Insira o ativo no caixa de seleção(Não é necessario apagar o ativo, apenas clique e digite as iniciais que a busca irá encontrar)')
    with col2:
      state.lote = st.text_input('Quantidade',value='100')

    col1, col2, col3, col4 = st.beta_columns([.4,.7,.9,1]) # Cria as colunas para disposição dos botões. Os numeros são os tamanhos para o alinhamento
    with col2:
      if st.form_submit_button(label='Inserir Ativo', help='Clique para inserir o Ativo e a Quantidade na Carteira'):
        botao_inserir(state)

    with col3:
      if st.form_submit_button(label='Apagar Último Ativo', help='Clique para apagar o último Ativo inserido'):
        botao_apagar_ultimo(state)

    with col4:
      if st.form_submit_button(label='Limpar Carteira', help='Clique para apagar todos os Ativos da Carteira'):
        botao_apagar_tudo(state)

  st.markdown("***")

  portifolio_style = state.portifolio.set_index('Ação') # Espelha o dataframe, com index na Ação, para fazer a formatação e mostrar
  portifolio_style = portifolio_style.style.format({"Últ. Preço": "R${:20,.2f}", "Valor na Carteira": "R${:20,.2f}", 
                                                          "Beta do Ativo": "{:.2}", "%": "{:.0%}", "Beta Ponderado": "{:.2}"})

  st.subheader('**Carteira**') 
  st.table(portifolio_style,) # Mostra o DataFrame
  if state.portifolio.shape[0] != 0:
    state.valor_carteira = state.portifolio['Valor na Carteira'].sum() # Obtem o valor total da Carteira
    st.write('**Valor Total da Carteira: **', 'R${:20,.2f}'.format(state.valor_carteira))
  
  st.markdown("***")

  st.subheader("**Cálculos e Análises**")

  # Chama as funções para os cálculos e ações

  calculo_hedge(state)
  calculo_correlacao(state)
  calculo_setorial(state)

  st.markdown("***")

  with st.beta_expander("Ajuda"):
    st.write(
        """
        - O que é BETA? - O Beta é uma medida da volatilidade dos preços de uma ação ou de uma Carteira em relação ao mercado. 
          Em outras palavras, como o preço daquela ação ou da sua Carteira se movimenta em relação ao mercado em geral.
        """
    )

##### Ações e Cálculos

def fix_col_names(df): # Função para tirar os .SA ou corrigir os simbolos
  return ['IBOV' if col =='^BVSP' else col.rstrip('.SA') for col in df.columns]

def botao_inserir(state):
  try:
    ticker = yf.Ticker(state.papel + '.SA')
    #ultimo_preco = yf.download(state.papel + '.SA',period='1d')['Adj Close'][0] #Pegar o ultimo preço de fechamento da lista
    precos = yf.download([state.papel + '.SA', '^BVSP'],period='1y', progress=False)['Adj Close']
    precos = precos.fillna(method='bfill')
    ultimo_preco = precos[state.papel + '.SA'].tail(1)[0] # Ultimo preço do Ativo
    retornos = precos.pct_change()
    retornos = retornos[1:]
    std_asset = retornos[state.papel + '.SA'].std()
    std_bench = retornos['^BVSP'].std()
    corr = retornos[state.papel + '.SA'].corr(retornos['^BVSP'])
    beta = corr * (std_asset / std_bench)
    valor_total = float(state.lote) * float(ultimo_preco)
    setor = ticker.info['sector']
    subsetor = ticker.info['industry']
    state.portifolio = state.portifolio.append({'Ação': state.papel, 'Qtde': state.lote, 'Últ. Preço': ultimo_preco, 'Valor na Carteira': valor_total,
                                                'Setor': setor, 'SubSetor': subsetor, 'Beta do Ativo': beta}, ignore_index=True)
    state.portifolio['%'] = (state.portifolio['Valor na Carteira'] / state.portifolio['Valor na Carteira'].sum()) 
    state.portifolio['Beta Ponderado'] = state.portifolio['%']  * state.portifolio['Beta do Ativo']

  except:
    st.error('Ops! Verifique as informações.')

def botao_apagar_ultimo(state):
  state.portifolio.drop(state.portifolio.tail(1).index,inplace=True) # Apaga o ultimo registro do DataFrame

def botao_apagar_tudo(state):
  state.portifolio = pd.DataFrame()
  state.portifolio['Ação'] = ''
  state.portifolio['Qtde'] = ''
  state.portifolio['Últ. Preço'] = ''
  state.portifolio['Valor na Carteira'] = ''
  #state.portifolio['%'] = ''
  state.portifolio['Setor'] = ''
  state.portifolio['SubSetor'] = ''
  state.portifolio['Beta do Ativo'] = ''
  #state.portifolio['Beta Ponderado'] = ''

def calculo_hedge(state):
  with st.beta_expander("Beta da Carteira e Informações sobre Hedge(Proteção)", expanded=True):
    if st.checkbox('Calcular o Beta da Carteira e Hedge de proteção', help='Selecione para calcular o Beta da Carteira e mostrar informações sobre Hedge'):
      if state.portifolio.shape[0] != 0:
        #try:
          # Cálculos
          beta_carteira = state.portifolio['Beta Ponderado'].sum().round(2)
          valor_carteira = state.portifolio['Valor na Carteira'].sum() # Obtem o valor total da Carteira
          preco_bova11 = yf.download('BOVA11.sa', period='1d', progress=False)['Adj Close'][0] # Pega último preço do BOVA11
          preco_winfut = yf.download('^BVSP', period='1d', progress=False)['Adj Close'][0] # Pega último preço do WINFUT(IBOV)
          #qtde_bova11 = (valor_carteira / preco_bova11) * beta_carteira # Qtde de lotes de BOVA11 para fazer Hedge
          #qtde_winfut = valor_carteira / (preco_winfut * 0.20) * beta_carteira # Qtde de contratos WINFUT para Hedge
          #qtde_bova11 = int(math.ceil(qtde_bova11)) #Arredondar para cima e tirar o "."
          #qtde_winfut = int(math.ceil(qtde_winfut)) #Arredondar para cima e tirar o "."
          # Mostrar Resultados
          col1, col2, col3 = st.beta_columns([0.6,0.1,1])
          with col1:
            #st.write('**Valor da Carteira: **', 'R${:20,.2f}'.format(valor_carteira))
            st.write('**Beta da Carteira: **', '{:.2}'.format(beta_carteira))
            #pct_hedge = st.slider('Escolha a % de Hedge', min_value=1, max_value=100 ,step = 1) / 100
            pct_hedge = st.selectbox('Escolha a % de Hedge', [25,50,75,100], index=3) / 100
            qtde_bova11 = ((valor_carteira * pct_hedge) / preco_bova11) * beta_carteira # Qtde de lotes de BOVA11 para fazer Hedge
            qtde_winfut = (valor_carteira * pct_hedge) / (preco_winfut * 0.20) * beta_carteira # Qtde de contratos WINFUT para Hedge
            qtde_bova11 = int(math.ceil(qtde_bova11)) #Arredondar para cima e tirar o "."
            qtde_winfut = int(math.ceil(qtde_winfut)) #Arredondar para cima e tirar o "."           

          with col3:
            st.write('**Preço BOVA11: **', 'R${:20,.2f}'.format(preco_bova11))
            st.write('**Preço WINFUT: **', 'R${:20,.2f}'.format(preco_winfut * 0.20), '(','{:.0f}'.format(preco_winfut), ' pontos)' )
            st.write('**Quantidade BOVA11 para Hedge: **', '{:.0f}'.format(qtde_bova11), '(','R${:20,.2f}'.format(qtde_bova11 * preco_bova11),')')
            st.write('**Quantidade WINFUT para Hedge: **', '{:.0f}'.format(qtde_winfut), '(','R${:20,.2f}'.format(qtde_winfut * (preco_winfut * 0.20)),')')
        #except:
          #st.write('Ops! Algo deu errado!')
      else:
        st.write("**Carteira Vazia!**")

def calculo_correlacao(state):
  with st.beta_expander("Correlação entre os Ativos e os Indices (IBOV e Dolar)", expanded=True):
    if st.checkbox('Análise de Correlação', help='Selecione para calcular a correlação entre os ativos da sua carteira e índices'):
      #try:
        tickers = state.portifolio['Ação'] + ".SA"
        tickers = tickers.to_list()
        tickers += ['^BVSP', 'USDBRL=X'] # Adicionar os indices na comparação

        retornos = yf.download(tickers, period='1y', progress=False)["Adj Close"].pct_change()
        retornos = retornos.rename(columns={'^BVSP': 'IBOV', 'USDBRL=X': 'Dolar'}) # Adicionar os indices na comparação
        retornos = retornos.fillna(method='bfill')
        #retornos = carteira.pct_change()
        retornos = retornos[1:] # Apagar primeira linha
        retornos.columns = fix_col_names(retornos) # Corrigir as colunas
        correlacao_full = retornos.corr() # Calcula a correlação entre todo mundo com indices
        correlacao = correlacao_full.drop('IBOV',1) # Cria tabela retirando os Indices (Separar duas comparacoes)
        correlacao = correlacao.drop('IBOV',0)
        correlacao = correlacao.drop('Dolar',1)
        correlacao = correlacao.drop('Dolar',0)
      
        col1, col2, col3 = st.beta_columns([1,0.1,1])
        with col1:
          st.write('***Correlação dos Ativos com IBOV e Dolar***')
          corr_table_indices = pd.DataFrame(correlacao_full['IBOV'])
          corr_table_indices['Dolar'] = correlacao_full['Dolar']
          corr_table_indices = corr_table_indices.drop('IBOV',0)
          corr_table_indices = corr_table_indices.drop('Dolar',0)

          ordenar = st.selectbox('Ordenar por', ['IBOV', 'Dolar'])
          if ordenar == 'IBOV':
            corr_table_indices = corr_table_indices.sort_values("IBOV",ascending = False)
            corr_table_indices = corr_table_indices.style.background_gradient(cmap="Oranges").format({"IBOV": "{:.0%}", "Dolar": "{:.0%}"})
            st.table(corr_table_indices)
          if ordenar == 'Dolar':
            corr_table_indices = corr_table_indices.sort_values("Dolar",ascending = False)
            corr_table_indices = corr_table_indices.style.background_gradient(cmap="Oranges").format({"IBOV": "{:.0%}", "Dolar": "{:.0%}"})
            st.table(corr_table_indices)

        with col3:
          st.write('***Correlações mais fortes e menos fortes***')
          correlacao['Ação 1'] = correlacao.index
          correlacao = correlacao.melt(id_vars = 'Ação 1', var_name = "Ação 2",value_name='Correlação').reset_index(drop = True)
          correlacao = correlacao[correlacao['Ação 1'] < correlacao['Ação 2']].dropna()
          highest_corr = correlacao.sort_values("Correlação",ascending = False)
          highest_corr.reset_index(drop=True, inplace=True) # Reseta o indice
          highest_corr.index += 1 # Iniciar o index em 1 ao invés de 0

          def _color_red_or_green(val): # Função para o mapa de cores da tabela
            color = 'red' if val < 0 else 'green'
            #return 'color: %s' % color
            return 'background-color: %s' % color
          
          #highest_corr = highest_corr.style.applymap(_color_red_or_green, subset=['Correlação']).format({"Correlação": "{:.0%}"}) # Aplicar Cores
          highest_corr = highest_corr.style.background_gradient(cmap="Oranges").format({"Correlação": "{:.0%}"})
          
          st.table(highest_corr)


      #except:
        #st.error('Algo errado aconteceu. Verifique as informações ou pode ser que algum ativo esteja apresentando problemas com seus dados.')

def calculo_setorial(state):
  with st.beta_expander("Análise Setorial da sua Carteira", expanded=True):
    if st.checkbox('Análise Setorial', help='Selecione para mostrar a distribuição setorial da sua Carteira'):
      #try:
        opcao_grafico = st.radio('Selecione o tipo de Gráfico', ['SunBurst', 'TreeMap'])
        if opcao_grafico == 'SunBurst':
          fig = px.sunburst(state.portifolio, path=['Setor', 'SubSetor', 'Ação'], values='%', height=700)
          fig.update_traces(textfont_color='white',
                            textfont_size=14,
                            hovertemplate='<b>%{label}:</b> %{value:.2f}%')
          st.plotly_chart(fig)

        if opcao_grafico == 'TreeMap':
          fig = px.treemap(state.portifolio, path=['Setor', 'SubSetor', 'Ação'], values='%', height=700)

          fig.update_traces(textfont_color='white',
                            textfont_size=14,
                            hovertemplate='<b>%{label}:</b> %{value:.2f}%')
          st.plotly_chart(fig)
      #except:
        #st.write('Ops! Isso é ruim.')
