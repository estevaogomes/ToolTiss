import os
import config
from services.TissXmlService import TissXmlService
from comunication.SoapClient import TissSoapClient

if __name__ == "__main__":
    # Definição dos caminhos dos arquivos de entrada e saída
    
    # Criando massa de teste automatizada caso os arquivos locais não existam
    if not os.path.exists(config.CAMINHO_XML_ENTRADA):
        with open(config.CAMINHO_XML_ENTRADA, "w", encoding="iso-8859-1") as f:
            f.write(
                """<?xml version="1.0" encoding="iso-8859-1"?>
<ans:faturamentoGuia xmlns:ans="http://ans.gov.br">
    <ans:guiasTISS>
        <ans:guiaFaturamento>
            <ans:numeroCarteira>444444444444444</ans:numeroCarteira>
            <ans:nomeBeneficiario>CARLOS ALBERTO</ans:nomeBeneficiario>
        </ans:guiaFaturamento>
    </ans:guiasTISS>
    <ans:epilogo>
        <ans:hash>hash_antigo_para_substituicao</ans:hash>
    </ans:epilogo>
</ans:faturamentoGuia>"""
            )

    if not os.path.exists(config.CAMINHO_PLANILHA_CARTEIRAS):
        with open(config.CAMINHO_PLANILHA_CARTEIRAS, "w", encoding="utf-8") as f:
            f.write("num_carteira\n777711112222333\n888899990000111\n")

    if config.ALTERAR_LOTES:
        # Execução do script
        TissXmlService.processar_alteracao_tiss(
            xml_origem=config.CAMINHO_XML_ENTRADA,
            xml_destino=config.CAMINHO_XML_SAIDA,
            planilha_ref=config.CAMINHO_PLANILHA_CARTEIRAS,
            coluna_nome=config.COLUNA_ALVO,
        )

    if config.ENVIAR_WS:
        sucesso, resultado = TissSoapClient.enviar_lote(
            caminho_xml=config.CAMINHO_XML_ENVIAR,
            url_endpoint=config.URL_OPERADORA,
            soap_action=""  # Remova essa linha se o webservice não exigir SOAPAction
        )

    if sucesso:
        print("[+] Envio realizado com sucesso!")
        print("[*] XML de resposta recebido da operadora:")

        caminho_txt_debug = "resposta.txt"
        with open(caminho_txt_debug, "w", encoding="iso-8859-1") as f:
            f.write(resultado)
        print(f"[+] Cópia do resultado SOAP salva em texto para auditoria: {caminho_txt_debug}")
        #print(resultado)  # Aqui estará o XML de retorno (ex: tissRetornoLoteGuias)
        
        # Aqui você poderá passar o 'resultado' para um serviço de parse se precisar tratar a resposta
    else:
        print(f"[-] Ocorreu uma falha no envio do lote:")
        print(resultado)  # Exibe os detalhes do erro HTTP ou falha de rede