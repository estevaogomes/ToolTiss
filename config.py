import os

CAMINHO_XML_ENTRADA = "contas.xml"
CAMINHO_XML_SAIDA = "saida.xml"
CAMINHO_PLANILHA_CARTEIRAS = "dados.csv"
UTILIZAR_RANDOM_TRANSACAO = True
CAMINHO_XML_ENVIAR = "saida.xml"
URL_OPERADORA = "http://or2tasyhtmlpj01:8082/TISS40200OPS/tissLoteGuias"
ENVIAR_WS = True
ALTERAR_LOTES = True
    
    # Nome da coluna a ser lida na planilha (Opcional, mude para None se quiser ler a 1ª coluna)
COLUNA_ALVO = "num_carteira"


# Caminhos de Arquivos Padrão
XML_ENTRADA = os.getenv("TISS_XML_ENTRADA", "contas.xml")
XML_MASCARADO = os.getenv("TISS_XML_SAIDA", "saida.xml")
PLANILHA_CARTEIRAS = os.getenv("TISS_PLANILHA", "dados.csv")
COLUNA_PLANILHA = os.getenv("TISS_COLUNA_CARTEIRA", None)

# Endereços do WebService da Operadora de Saúde
URL_SISOAP = os.getenv(
    "TISS_URL_SOAP",
    "http://or2tasyhtmlpj01:8082/TISS40300OPS/tissLoteGuias",
)
SOAP_ACTION_METODO = os.getenv(
    "TISS_SOAP_ACTION",
    "",
)

# Timeout de Rede
TIMEOUT_REQUISICAO = 100000
