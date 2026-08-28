import requests
# Importa o processador que criamos acima
from services.TissXmlService import TissXmlService
import config

class TissSoapClient:
    # ... outros métodos da sua classe ...
    @staticmethod
    def enviar_lote(caminho_xml, url_endpoint, soap_action=None):
        try:
            # 1. Lê o arquivo original
            with open(caminho_xml, "r", encoding="iso-8859-1") as f:
                conteudo_bruto = f.read()

            # 2. CHAMADA DA NOVA CLASSE UTILITÁRIA
            conteudo_xml = TissXmlService.preparar_conteudo_xml(conteudo_bruto)

            # 3. Montagem estrutural do envelope SOAP
            soap_envelope = f"""<?xml version="1.0" encoding="ISO-8859-1"?>
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ans="http://www.ans.gov.br/padroes/tiss/schemas" xmlns:xd="http://www.w3.org/2000/09/xmldsig#">
                <soapenv:Header/>
                <soapenv:Body>
                    <ans:loteGuiasWS>
                        {conteudo_xml}
                    </ans:loteGuiasWS>
                </soapenv:Body>
            </soapenv:Envelope>"""

            headers = {
                "Content-Type": "text/xml; charset=iso-8859-1",
                "Accept": "text/xml",
            }
            if soap_action:
                headers["SOAPAction"] = f'"{soap_action}"'

            print(f"[*] Transmitindo envelope SOAP para: {url_endpoint}")
            dados_bytes = soap_envelope.encode("iso-8859-1")

            caminho_txt_debug = "ultimo_envio_soap.txt"
            with open(caminho_txt_debug, "w", encoding="iso-8859-1") as f:
                f.write(soap_envelope)
            print(f"[+] Cópia do envelope SOAP salva em texto para auditoria: {caminho_txt_debug}")

            response = requests.post(
                url_endpoint,
                data=dados_bytes,
                headers=headers,
                timeout=config.TIMEOUT_REQUISICAO,
            )

            print(f"[+] Resposta HTTP recebida. Status: {response.status_code}")
            response.raise_for_status()

            return True, response.text

        except requests.exceptions.HTTPError as e:
            msg_erro = response.text if "response" in locals() and response.text else str(e)
            return False, f"Erro HTTP do servidor:\n{msg_erro}"
        except Exception as e:
            return False, f"Falha de comunicação/rede: {e}"
