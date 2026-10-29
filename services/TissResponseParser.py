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
        Recebe texto XML da resposta SOAP e retorna dict estruturado:
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
        try:
            root = ET.fromstring(xml_text.encode("iso-8859-1"))
        except Exception:
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

    @classmethod
    def _parse_protocolo_recebimento(cls, root):
        """Parseia formato protocoloRecebimentoWS."""
        ns = cls.NS

        # Buscar protocoloRecebimento (com ou sem namespace)
        pr = root.find(".//ans:protocoloRecebimento", ns)
        if pr is None:
            pr = root.find(".//protocoloRecebimento")
        if pr is None:
            return None

        resultado = {
            "protocolo": "",
            "situacao_comunicacao": "recebido",
            "guias": [],
        }

        # Número do protocolo
        det = pr.find("ans:detalheProtocolo", ns) or pr.find("detalheProtocolo")
        if det is not None:
            num_proto = cls._find_text(det, "numeroProtocolo", ns)
            resultado["protocolo"] = num_proto

        # Extrair guias de dadosGuiasProtocolo/dadosGuias
        for guia_elem in root.findall(".//ans:dadosGuias", ns):
            guia_info = {
                "numero_guia_prestador": cls._find_text(guia_elem, "numeroGuiaPrestador", ns),
                "numero_protocolo": resultado["protocolo"],
                "status": "recebido",
                "motivo": None,
            }

            # Verificar glosas
            glosa_guia = guia_elem.find("ans:glosaGuia", ns) or guia_elem.find("glosaGuia")
            if glosa_guia is not None:
                motivos = []
                for motivo in glosa_guia.findall("ans:motivoGlosa", ns):
                    codigo = cls._find_text(motivo, "codigoGlosa", ns)
                    descricao = cls._find_text(motivo, "descricaoGlosa", ns)
                    if codigo or descricao:
                        motivos.append(f"{codigo} - {descricao}" if codigo else descricao)
                # Tentar também sem namespace
                if not motivos:
                    for motivo in glosa_guia.findall("motivoGlosa"):
                        codigo = cls._find_text(motivo, "codigoGlosa")
                        descricao = cls._find_text(motivo, "descricaoGlosa")
                        if codigo or descricao:
                            motivos.append(f"{codigo} - {descricao}" if codigo else descricao)

                if motivos:
                    guia_info["status"] = "glosado"
                    guia_info["motivo"] = "; ".join(motivos)

            # Verificar valores para determinar status mais preciso
            vl_informado = guia_elem.find("ans:vlInformadoGuia", ns) or guia_elem.find("vlInformadoGuia")
            if vl_informado is not None:
                valor_glosa = cls._find_text(vl_informado, "valorGlosa", ns)
                valor_liberado = cls._find_text(vl_informado, "valorLiberado", ns)
                if valor_glosa and float(valor_glosa.replace(",", ".")) > 0:
                    guia_info["status"] = "glosado"
                elif valor_liberado and float(valor_liberado.replace(",", ".")) > 0:
                    guia_info["status"] = "aceito"

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