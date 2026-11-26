"""
Parser de resposta SOAP TISS.
Suporta dois formatos de retorno:
1. tissRetornoLoteGuias (resposta síncrona com status por guia)
2. protocoloRecebimentoWS (confirmação de recebimento com glosas)
"""
import xml.etree.ElementTree as ET


class TissResponseParser:
    """Parseia XML de resposta TISS e extrai resultados por guia."""

    NS = {"ans": "http://www.ans.gov.br/padroes/tiss/schemas"}

    @staticmethod
    def _find_text(parent, tag, ns=None):
        """Busca texto de uma tag filha, tentando com e sem namespace."""
        if ns:
            elem = parent.find(f"ans:{tag}", ns)
            if elem is not None and elem.text:
                return elem.text.strip()
        # Tenta sem namespace (respostas podem omitir prefixo)
        elem = parent.find(tag)
        if elem is not None and elem.text:
            return elem.text.strip()
        return ""

    @classmethod
    def parse(cls, xml_text):
        """
        Recebe texto da resposta SOAP e retorna dict estruturado:
        {
            "protocolo": str,
            "situacao_comunicacao": str,
            "guias": [
                {
                    "numero_guia_prestador": str,
                    "numero_protocolo": str,
                    "status": str,
                    "motivo": str | None,
                }
            ]
        }
        Retorna None se parsing falhar completamente.
        """
        # Decodifica bytes para string se necessário
        if isinstance(xml_text, bytes):
            xml_text = xml_text.decode("iso-8859-1")

        try:
            # Parse XML por tags conforme schema TISS (caminho padrão).
            # Respostas SOAP TISS chegam em ISO-8859-1; xml_text já foi decodificado acima.
            root = ET.fromstring(xml_text)
        except Exception:
            # Fallback: algumas operadoras retornam mensagens de erro em texto puro
            # (não-XML) como "Erro 5012: ... Erro: 5014 - CODIGO HASH INVALIDO".
            # Extrai todos os códigos de erro via regex apenas quando o parse XML falha.
            import re
            erros_simples = re.findall(r'(\d{4})\s*-\s*([^.]*)', xml_text, re.IGNORECASE)
            erros_dois_pontos = re.findall(r'[Ee]rro\s+(\d{4}):\s*([^.]*)', xml_text, re.IGNORECASE)

            codigos_vistos = set()
            motivos = []
            for codigo, descricao in erros_simples + erros_dois_pontos:
                if codigo not in codigos_vistos:
                    codigos_vistos.add(codigo)
                    desc_limpa = descricao.strip().rstrip(".;:,")
                    motivos.append(f"{codigo} - {desc_limpa}" if desc_limpa else codigo)

            if motivos:
                return {
                    "protocolo": "",
                    "situacao_comunicacao": "erro",
                    "guias": [{
                        "numero_guia_prestador": "",
                        "numero_protocolo": "",
                        "status": "rejeitado",
                        "motivo": "; ".join(motivos),
                    }],
                }
            # Fallback final: se o conteúdo não é XML e nenhum código de erro foi
            # identificado via regex, registra o texto bruto como motivo para que
            # o relatório CSV nunca perca a informação de rejeição.
            texto_limpo = xml_text.strip()[:500]
            if texto_limpo:
                return {
                    "protocolo": "",
                    "situacao_comunicacao": "erro",
                    "guias": [{
                        "numero_guia_prestador": "",
                        "numero_protocolo": "",
                        "status": "rejeitado",
                        "motivo": texto_limpo,
                    }],
                }
            return None

        resultado = {
            "protocolo": "",
            "situacao_comunicacao": "",
            "guias": [],
        }

        # Tentar formato 1: protocoloRecebimentoWS
        protocolo_recebimento = cls._parse_protocolo_recebimento(root)
        if protocolo_recebimento:
            return protocolo_recebimento

        # Tentar formato 2: tissRetornoLoteGuias
        retorno_lote = cls._parse_retorno_lote(root)
        if retorno_lote:
            return retorno_lote

        # Nenhum formato reconhecido
        return None

    # Namespace TISS em notação Clark (usado quando o XML declara xmlns= sem prefixo)
    NS_CLARK = "{http://www.ans.gov.br/padroes/tiss/schemas}"

    @classmethod
    def _find_element(cls, parent, tag):
        """Busca elemento filho tentando três formas: prefixo ans:, Clark notation e sem namespace."""
        # 1. Com prefixo ans: (quando XML declara xmlns:ans=...)
        elem = parent.find(f"ans:{tag}", cls.NS)
        if elem is not None:
            return elem
        # 2. Com namespace Clark (quando XML declara xmlns= sem prefixo)
        elem = parent.find(f"{cls.NS_CLARK}{tag}")
        if elem is not None:
            return elem
        # 3. Sem namespace
        elem = parent.find(tag)
        return elem

    @classmethod
    def _find_all_elements(cls, parent, tag):
        """Busca todos os elementos correspondentes (recursivo .//), tentando três formas de namespace.
        Usa .// pois as tags TISS na resposta SOAP estão aninhadas dentro de S:Envelope/S:Body
        e não são filhas diretas do elemento pai passado."""
        resultados = parent.findall(f".//ans:{tag}", cls.NS)
        if not resultados:
            resultados = parent.findall(f".//{cls.NS_CLARK}{tag}")
        if not resultados:
            resultados = parent.findall(f".//{tag}")
        return resultados

    @classmethod
    def _find_text(cls, parent, tag, ns=None):
        """Busca texto de uma tag filha, tentando com e sem namespace."""
        elem = cls._find_element(parent, tag)
        if elem is not None and elem.text:
            return elem.text.strip()
        return ""

    @classmethod
    def _parse_protocolo_recebimento(cls, root):
        """Parseia formato protocoloRecebimentoWS."""
        # Buscar protocoloRecebimento usando busca recursiva profunda (.//).
        # O elemento está aninhado dentro de S:Envelope/S:Body/protocoloRecebimentoWS/recebimentoLote,
        # então busca por filho direto na raiz sempre falha. Usamos .// com notação Clark
        # pois o XML de resposta usa namespace padrão (xmlns= sem prefixo ans:).
        ns_clark = cls.NS_CLARK
        pr = root.find(f".//{ns_clark}protocoloRecebimento")
        if pr is None:
            # Fallback adicional: busca por local name via iter() caso o namespace seja diferente
            for candidate in root.iter():
                local_name = candidate.tag.split("}")[-1] if "}" in candidate.tag else candidate.tag
                if local_name == "protocoloRecebimento":
                    pr = candidate
                    break
        if pr is None:
            return None

        resultado = {
            "protocolo": "",
            "situacao_comunicacao": "recebido",
            "guias": [],
        }

        # Número do protocolo
        det = cls._find_element(pr, "detalheProtocolo")
        if det is not None:
            num_proto = cls._find_text(det, "numeroProtocolo")
            resultado["protocolo"] = num_proto

        # Extrair guias de dadosGuiasProtocolo/dadosGuias
        for guia_elem in cls._find_all_elements(root, "dadosGuias"):
            guia_info = {
                "numero_guia_prestador": cls._find_text(guia_elem, "numeroGuiaPrestador"),
                "numero_protocolo": resultado["protocolo"],
                "status": "recebido",
                "motivo": None,
            }

            # Verificar glosas
            glosa_guia = cls._find_element(guia_elem, "glosaGuia")
            if glosa_guia is not None:
                motivos = []
                for motivo in cls._find_all_elements(glosa_guia, "motivoGlosa"):
                    codigo = cls._find_text(motivo, "codigoGlosa")
                    descricao = cls._find_text(motivo, "descricaoGlosa")
                    if codigo or descricao:
                        motivos.append(f"{codigo} - {descricao}" if codigo else descricao)

                if motivos:
                    guia_info["status"] = "glosado"
                    guia_info["motivo"] = "; ".join(motivos)

            # Verificar valores para determinar status mais preciso
            vl_informado = cls._find_element(guia_elem, "vlInformadoGuia")
            if vl_informado is not None:
                valor_glosa = cls._find_text(vl_informado, "valorGlosa")
                valor_liberado = cls._find_text(vl_informado, "valorLiberado")
                try:
                    if valor_glosa and float(valor_glosa.replace(",", ".")) > 0:
                        guia_info["status"] = "glosado"
                    elif valor_liberado and float(valor_liberado.replace(",", ".")) > 0:
                        guia_info["status"] = "aceito"
                except ValueError:
                    pass

            resultado["guias"].append(guia_info)

        return resultado if resultado["guias"] else None

    @classmethod
    def _parse_retorno_lote(cls, root):
        """Parseia formato tissRetornoLoteGuias (resposta síncrona)."""
        ns = cls.NS

        # Buscar situacaoComunicacao
        situacao = root.find(".//ans:situacaoComunicacao", ns)
        if situacao is None:
            situacao = root.find(".//situacaoComunicacao")
        if situacao is None:
            return None

        resultado = {
            "protocolo": "",
            "situacao_comunicacao": situacao.text.strip() if situacao.text else "",
            "guias": [],
        }

        # Protocolo
        protocolo = root.find(".//ans:protocolo", ns) or root.find(".//protocolo")
        if protocolo is not None and protocolo.text:
            resultado["protocolo"] = protocolo.text.strip()

        # Guias com status individual
        for guia_proto in root.findall(".//ans:guiaProtocolo", ns):
            guia_info = {
                "numero_guia_prestador": cls._find_text(guia_proto, "numeroGuiaPrestador", ns),
                "numero_protocolo": cls._find_text(guia_proto, "numeroProtocolo", ns) or resultado["protocolo"],
                "status": "desconhecido",
                "motivo": None,
            }

            # Status
            status_elem = guia_proto.find("ans:situacaoGuia", ns) or guia_proto.find("situacaoGuia")
            if status_elem is None:
                status_elem = guia_proto.find("ans:statusProcessamento", ns) or guia_proto.find("statusProcessamento")
            if status_elem is not None and status_elem.text:
                guia_info["status"] = status_elem.text.strip().lower()

            # Motivo
            motivo_elem = guia_proto.find("ans:motivoGlosa", ns) or guia_proto.find("motivoGlosa")
            if motivo_elem is None:
                motivo_elem = guia_proto.find("ans:descricaoMotivo", ns) or guia_proto.find("descricaoMotivo")
            if motivo_elem is not None and motivo_elem.text:
                guia_info["motivo"] = motivo_elem.text.strip()

            resultado["guias"].append(guia_info)

        return resultado if resultado["guias"] else None

    @staticmethod
    def gerar_relatorio_csv(resultados_por_arquivo, caminho_saida):
        """
        Gera CSV consolidado a partir de lista de dicts:
        [{"arquivo": str, "parse_result": dict}, ...]
        """
        import csv

        with open(caminho_saida, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow([
                "Arquivo",
                "Protocolo",
                "Situação Comunicação",
                "Nº Guia Prestador",
                "Nº Protocolo Guia",
                "Status",
                "Motivo Glosa/Rejeição",
            ])

            for item in resultados_por_arquivo:
                arquivo = item["arquivo"]
                parse = item.get("parse_result")

                if parse is None:
                    writer.writerow([arquivo, "", "", "", "", "ERRO_PARSING", ""])
                    continue

                protocolo = parse.get("protocolo", "")
                situacao = parse.get("situacao_comunicacao", "")
                guias = parse.get("guias", [])

                if not guias:
                    writer.writerow([arquivo, protocolo, situacao, "", "", "SEM_GUIAS", ""])
                else:
                    for guia in guias:
                        writer.writerow([
                            arquivo,
                            protocolo,
                            situacao,
                            guia.get("numero_guia_prestador", ""),
                            guia.get("numero_protocolo", ""),
                            guia.get("status", ""),
                            guia.get("motivo", "") or "",
                        ])