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

            # 1.5. Detecta versão TISS e seleciona endpoint correto automaticamente
            versao_tiss = TissXmlService.detectar_versao_tiss(conteudo_bruto)
            if versao_tiss:
                urls_mapeadas = getattr(config, 'URLS_POR_VERSAO_TISS', {})
                if versao_tiss in urls_mapeadas:
                    url_endpoint = urls_mapeadas[versao_tiss]
                    print(f"[*] Versão TISS detectada: {versao_tiss} → Endpoint: {url_endpoint}")
                else:
                    print(f"[!] Versão TISS {versao_tiss} não mapeada em URLS_POR_VERSAO_TISS. Usando fallback: {url_endpoint}")
            else:
                print(f"[!] Não foi possível detectar versão TISS no arquivo. Usando endpoint padrão: {url_endpoint}")

            # 2. CHAMADA DA NOVA CLASSE UTILITÁRIA
            conteudo_xml = TissXmlService.preparar_conteudo_xml(conteudo_bruto)

            # 2.5. VALIDAÇÃO E CORREÇÃO DE HASH PRÉ-ENVIO
            # Recalcula o hash sobre o conteúdo exato do payload (já filtrado)
            # para garantir que o valor na tag <ans:hash> corresponda à cadeia
            # de texto que será efetivamente transmitida. Corrige automaticamente
            # divergências causadas por arquivos com hash incorreto na origem,
            # sem bloquear o envio.
            import re as _re
            import hashlib as _hashlib
            import xml.etree.ElementTree as _ET

            try:
                # Extrai hash declarado no payload preparado
                _hash_match = _re.search(r'<ans:hash>([a-fA-F0-9]{32})</ans:hash>', conteudo_xml, _re.IGNORECASE)
                if _hash_match:
                    _hash_declarado = _hash_match.group(1).lower()

                    # Recalcula sobre o conteúdo exato que irá para o envelope
                    # (sem a tag hash, pois ela não entra no cálculo C14N ANS)
                    _conteudo_sem_hash = _re.sub(r'<ans:hash>[^<]*</ans:hash>', '', conteudo_xml)
                    _wrapper = f"<?xml version='1.0' encoding='iso-8859-1'?><ans:mensagemTISS xmlns:ans=\"http://www.ans.gov.br/padroes/tiss/schemas\">{_conteudo_sem_hash}</ans:mensagemTISS>"
                    _tree_validacao = _ET.fromstring(_wrapper.encode('iso-8859-1'))
                    _cadeia_validacao = TissXmlService._extrair_valores_texto_tiss(_tree_validacao)
                    _hash_recalculado = _hashlib.md5(_cadeia_validacao.encode('iso-8859-1')).hexdigest()

                    if _hash_declarado != _hash_recalculado:
                        print(f"[!] ALERTA: Hash divergente detectado antes do envio!")
                        print(f"    Declarado:   {_hash_declarado}")
                        print(f"    Recalculado: {_hash_recalculado}")
                        print(f"[+] Corrigindo hash automaticamente no payload...")
                        conteudo_xml = _re.sub(
                            r'<ans:hash>[a-fA-F0-9]{32}</ans:hash>',
                            f'<ans:hash>{_hash_recalculado}</ans:hash>',
                            conteudo_xml,
                            flags=_re.IGNORECASE
                        )
                    else:
                        print(f"[+] Validação de hash pré-envio: OK ({_hash_declarado})")
                else:
                    print("[!] ALERTA: Tag <ans:hash> não encontrada no payload. Enviando sem validação.")
            except Exception as _e_validacao:
                print(f"[!] Erro na validação de hash pré-envio (envio prossegue): {_e_validacao}")

            # 3. Montagem estrutural do envelope SOAP
            # IMPORTANTE: Sem whitespace significativo dentro de <ans:loteGuiasWS>.
            # Espaços em branco antes/depois do payload alteram o conteúdo assinado
            # e causam erro 5014 (hash inválido) no servidor da operadora.
            soap_envelope = (
                '<?xml version="1.0" encoding="ISO-8859-1"?>'
                '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
                'xmlns:ans="http://www.ans.gov.br/padroes/tiss/schemas" '
                'xmlns:xd="http://www.w3.org/2000/09/xmldsig#">'
                '<soapenv:Header/>'
                '<soapenv:Body>'
                '<ans:loteGuiasWS>'
                + conteudo_xml +
                '</ans:loteGuiasWS>'
                '</soapenv:Body>'
                '</soapenv:Envelope>'
            )

            headers = {
                "Content-Type": "text/xml; charset=iso-8859-1",
                "Accept": "text/xml",
            }
            if soap_action:
                headers["SOAPAction"] = f'"{soap_action}"'

            print(f"[*] Transmitindo envelope SOAP para: {url_endpoint}")
            dados_bytes = soap_envelope.encode("iso-8859-1")

            # Salva cópia exata do que foi transmitido (byte-a-byte idêntica)
            caminho_txt_debug = "ultimo_envio_soap.txt"
            with open(caminho_txt_debug, "wb") as f:
                f.write(dados_bytes)

            # Salva versão XML indentada para inspeção visual em editores.
            # A indentação NÃO altera o hash nem o conteúdo transmitido;
            # é apenas uma cópia formatada para debugging.
            import xml.etree.ElementTree as _ET_fmt
            try:
                # Registra namespaces ANTES do parse para evitar ns0: na re-serialização
                _ET_fmt.register_namespace("soapenv", "http://schemas.xmlsoap.org/soap/envelope/")
                _ET_fmt.register_namespace("ans", "http://www.ans.gov.br/padroes/tiss/schemas")
                _ET_fmt.register_namespace("xd", "http://www.w3.org/2000/09/xmldsig#")
                _tree_env = _ET_fmt.fromstring(dados_bytes)
                _ET_fmt.indent(_tree_env, space="  ")
                _xml_indentado = _ET_fmt.tostring(_tree_env, encoding="iso-8859-1", xml_declaration=True)
                caminho_xml_debug = "ultimo_envio_soap.xml"
                with open(caminho_xml_debug, "wb") as f_xml:
                    f_xml.write(_xml_indentado)
                print(f"[+] Envelope SOAP salvo: {caminho_txt_debug} (raw) e {caminho_xml_debug} (formatado)")
            except Exception as _e_fmt:
                print(f"[!] Não foi possível gerar XML formatado: {_e_fmt}")
                print(f"[+] Cópia raw salva em: {caminho_txt_debug}")

            response = requests.post(
                url_endpoint,
                data=dados_bytes,
                headers=headers,
                timeout=config.TIMEOUT_REQUISICAO,
            )

            print(f"[+] Resposta HTTP recebida. Status: {response.status_code}")
            response.raise_for_status()

            # Parse da resposta SOAP para extrair protocolo, erros e logs do servidor
            resposta_texto = response.text
            import re

            # Extrai número do protocolo (sucesso)
            protocolo_match = re.search(r'<[^>]*numeroProtocolo[^>]*>([^<]*)</', resposta_texto)
            if protocolo_match:
                print(f"[+] Protocolo recebido: {protocolo_match.group(1)}")

            # Extrai erro de hash (5014) ou outros erros de glosa
            erro_match = re.search(r'<[^>]*mensagemErro[^>]*>.*?<[^>]*codigoGlosa[^>]*>([^<]*)</.*?<[^>]*descricaoGlosa[^>]*>([^<]*)</', resposta_texto, re.DOTALL)
            if erro_match:
                codigo_glosa = erro_match.group(1)
                descricao_glosa = erro_match.group(2)
                print(f"[!] ERRO DO SERVIDOR - Código: {codigo_glosa}")
                print(f"[!] Descrição: {descricao_glosa}")
                return False, f"Erro {codigo_glosa}: {descricao_glosa}"

            # Extrai fault SOAP genérico
            fault_match = re.search(r'<[^>]*tissFault[^>]*>([^<]*)</', resposta_texto)
            if fault_match:
                print(f"[!] FAULT SOAP: {fault_match.group(1)}")
                return False, f"SOAP Fault: {fault_match.group(1)}"

            # Se não há protocolo nem erro explícito, loga aviso
            if not protocolo_match and not erro_match and not fault_match:
                print("[!] Resposta não contém protocolo nem erro identificável. Verifique o XML de resposta.")

            return True, resposta_texto

        except requests.exceptions.HTTPError as e:
            msg_erro = response.text if "response" in locals() and response.text else str(e)
            # Tenta extrair erro estruturado mesmo em respostas HTTP de erro
            import re
            erro_match = re.search(r'<[^>]*codigoGlosa[^>]*>([^<]*)</.*?<[^>]*descricaoGlosa[^>]*>([^<]*)</', msg_erro, re.DOTALL)
            if erro_match:
                print(f"[!] ERRO HTTP + GLOSA - Código: {erro_match.group(1)}")
                print(f"[!] Descrição: {erro_match.group(2)}")
                return False, f"Erro HTTP {erro_match.group(1)}: {erro_match.group(2)}"
            return False, f"Erro HTTP do servidor:\n{msg_erro}"
        except Exception as e:
            return False, f"Falha de comunicação/rede: {e}"
