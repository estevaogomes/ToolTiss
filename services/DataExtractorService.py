import csv
import os

class DataExtractorService:

    # Carrega números de carteirinhas de um arquivo CSV ou Excel (.xlsx/.xls).
    # Se for CSV, busca pelo nome da coluna ou usa a primeira por padrão.
    # Se for Excel, exige as bibliotecas pandas e openpyxl instaladas.

    @staticmethod
    def carregar_carteiras(caminho_planilha, nome_coluna=None):
        if not os.path.exists(caminho_planilha):
            raise FileNotFoundError(
                f"Arquivo de referência não encontrado: {caminho_planilha}"
            )

        extensao = os.path.splitext(caminho_planilha)[1].lower()
        carteiras = []

        if extensao == ".csv":
            try:
                with open(caminho_planilha, mode="r", encoding="utf-8") as f:
                    # Lendo como dicionário se houver nome de coluna especificado
                    if nome_coluna:
                        reader = csv.DictReader(f)
                        if nome_coluna not in reader.fieldnames:
                            # Fallback para leitura normal se a coluna não for encontrada pelo nome
                            f.seek(0)
                            reader = csv.reader(f)
                            next(reader, None)  # Pula cabeçalho
                            for linha in reader:
                                if linha:
                                    carteiras.append(linha[0].strip())
                        else:
                            for linha in reader:
                                if linha.get(nome_coluna):
                                    carteiras.append(linha[nome_coluna].strip())
                    else:
                        reader = csv.reader(f)
                        header = next(reader, None)  # Ignora ou avalia primeira linha
                        # Se o arquivo tiver apenas uma coluna e for dado puro, adiciona o header de volta
                        if header and len(header) == 1:
                            carteiras.append(header[0].strip())
                        for linha in reader:
                            if linha and linha[0].strip():
                                carteiras.append(linha[0].strip())
            except Exception as e:
                raise RuntimeError(f"Erro ao processar o arquivo CSV: {e}")

        elif extensao in [".xlsx", ".xls"]:
            try:
                import pandas as pd

                df = pd.read_excel(caminho_planilha)
                if df.empty:
                    raise ValueError("A planilha Excel está vazia.")

                if nome_coluna and nome_coluna in df.columns:
                    carteiras = (
                        df[nome_coluna].dropna().astype(str).str.strip().tolist()
                    )
                else:
                    # Usa a primeira coluna por padrão
                    carteiras = (
                        df.iloc[:, 0].dropna().astype(str).str.strip().tolist()
                    )
            except ImportError:
                raise ImportError(
                    "Para processar arquivos Excel, instale as dependências: pip install pandas openpyxl"
                )
            except Exception as e:
                raise RuntimeError(f"Erro ao processar o arquivo Excel: {e}")
        else:
            raise ValueError("Formato de planilha inválido. Use .csv, .xlsx ou .xls")

        # Remove valores vazios da lista
        carteiras = [c for c in carteiras if c]

        if not carteiras:
            raise ValueError(
                "Nenhuma carteirinha válida foi encontrada no arquivo de referência."
            )

        return carteiras

    