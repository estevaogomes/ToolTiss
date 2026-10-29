"""
Parser de resposta SOAP TISS (tissRetornoLoteGuias).
Extrai dados estruturados de protocolo, situação e glosas por guia.
"""
import xml.etree.ElementTree as ET


class TissResponseParser:
    """Parseia XML de resposta TISS e extrai resultados por guia."""

    @staticmethod
    def parse(xml_text):
        """
        Recebe texto XML da resposta SOAP e retorna dict estruturado:
        {
            "protocolo": str,
            "situacao_comunicacao": str,
            "guias": [
                {
                    "numero_guia_prestador": str,
                    "numero_protocolo": str,
                    "status": str,  # "aceito", "glosado", "rejeitado"
                    "motivo": str | None,
                }
            ]
        }
        Retorna None se parsing falhar.
        """
        try:
            root = ET.fromstring(xml_text.encode("iso-8859-1"))
        except Exception:
            return None

        ns = {"ans": "http://www.ans.gov.br/padroes/tiss/schemas"}

        resultado = {
            "protocolo": "",
            "situacao_comunicacao": "",
            "guias": [],
        }

        # Extrair número do protocolo
        protocolo_elem = root.find(".//ans:protocolo", ns)
        if protocolo_elem is not None and protocolo_elem.text:
            resultado["protocolo"] = protocolo_elem.text.strip()

        # Extrair situação da comunicação
        situacao_elem = root.find(".//ans:situacaoComunicacao", ns)
        if situacao_elem is not None and situacao_elem.text:
            resultado["situacao_comunicacao"] = situacao_elem.text.strip()

        # Extrair guias com status individual
        for guia_proto in root.findall(".//ans:guiaProtocolo", ns):
            guia_info = {
                "numero_guia_prestador": "",
                "numero_protocolo": "",
                "status": "desconhecido",
                "motivo": None,
            }

            num_guia = guia_proto.find("ans:numeroGuiaPrestador", ns)
            if num_guia is not None and num_guia.text:
                guia_info["numero_guia_prestador"] = num_guia.text.strip()

            num_proto = guia_proto.find("ans:numeroProtocolo", ns)
            if num_proto is not None and num_proto.text:
                guia_info["numero_protocolo"] = num_proto.text.strip()

            # Verificar status: pode estar em diferentes tags dependendo da operadora
            status_elem = guia_proto.find("ans:situacaoGuia", ns)
            if status_elem is None:
                status_elem = guia_proto.find("ans:statusProcessamento", ns)
            if status_elem is not None and status_elem.text:
                guia_info["status"] = status_elem.text.strip().lower()

            # Motivo de glosa/rejeição
            motivo_elem = guia_proto.find("ans:motivoGlosa", ns)
            if motivo_elem is None:
                motivo_elem = guia_proto.find("ans:descricaoMotivo", ns)
            if motivo_elem is not None and motivo_elem.text:
                guia_info["motivo"] = motivo_elem.text.strip()

            resultado["guias"].append(guia_info)

        return resultado

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