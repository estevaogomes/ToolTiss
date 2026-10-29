import hashlib
import nt
import random
import re
import sys
from services.DataExtractorService import DataExtractorService
import config
import xml.etree.ElementTree as ET


class TissXmlService:

    # Gera recursivamente a cadeia de caracteres coletando o texto limpo de cada nó.
    # Esta abordagem ignora a formatação física (tails/indentações) e foca estritamente 
    # no conteúdo dos dados, que é exatamente o que a regra C14N da ANS exige.
    @classmethod
    def _extrair_valores_texto_tiss(cls, elemento):
        conteudo = ""

        # Regra ANS TISS: Ignora completamente o bloco do epílogo/hash no cálculo de assinatura
        if elemento.tag.endswith("epilogo") or elemento.tag.endswith("hash"):
            return ""

        # Se o elemento possui texto direto, adiciona sem strip (apenas se não for nó com filhos).
        # Regra ANS TISS: whitespace literal é preservado na cadeia de hash; .strip() quebra
        # o cálculo em arquivos com formatação específica (ex: outrasDespesas, indicacaoClinica).
        if elemento.text and not list(elemento):
            conteudo += elemento.text

        # Percorre os nós filhos em ordem estrita de profundidade
        for filho in elemento:
            conteudo += cls._extrair_valores_texto_tiss(filho)

        return conteudo


    # Calcula o Hash MD5 baseado na cadeia de texto gerada no formato ISO-8859-1.
    # Localiza a tag de hash e atualiza seu respectivo valor interno.
    @classmethod
    def atualizar_hash_tiss(cls, root):
        # 1. Localiza a tag hash alvo na árvore e limpa seu valor pré-existente
        tag_hash_alvo = None
        for elem in root.iter():
            if elem.tag.endswith("hash"):
                elem.text = ""
                tag_hash_alvo = elem

        # 2. Extrai a string linear exata dos dados purificados
        cadeia_valores = cls._extrair_valores_texto_tiss(root)

        # 3. Codifica em ISO-8859-1 (Latin-1) e gera a assinatura MD5 de 32 dígitos hexadecimais
        novo_hash = hashlib.md5(cadeia_valores.encode("iso-8859-1")).hexdigest()

        # 4. Insere o hash atualizado na tag se ela existir no arquivo
        if tag_hash_alvo is not None:
            tag_hash_alvo.text = novo_hash
            return novo_hash
        return None


    # Orquestra a leitura, substituição aleatória de dados sensíveis dos beneficiários,
    # preservação de namespaces estruturais e gravação do XML com hash recalculado.
    @classmethod
    def processar_alteracao_tiss(
        cls, xml_origem, xml_destino, planilha_ref, coluna_nome=None
    ):
        """Orquestra a leitura, substituição aleatória de dados sensíveis dos beneficiários,

        preservação de namespaces estruturais e gravação do XML com hash recalculado.
        """
        try:
            # Carrega dados externos de substituição
            banco_carteiras = DataExtractorService.carregar_carteiras(planilha_ref, coluna_nome)

            # Mapeia e registra namespaces para evitar que o ElementTree renomeie tags para 'ns0:tag'
            namespaces = dict(
                [node for _, node in ET.iterparse(xml_origem, events=["start-ns"])]
            )
            for prefix, uri in namespaces.items():
                ET.register_namespace(prefix, uri)

            # Realiza o Parse do arquivo XML estruturado
            parser = ET.XMLParser(encoding="iso-8859-1")
            tree = ET.parse(xml_origem, parser)
            root = tree.getroot()

            # Substitui os valores de todas as ocorrências da tag numeroCarteira, sequencialTransacao e numeroLote
            contador_alteracoes = 0
            
            # Inicializa a variável da guia fora do loop
            guia_atual = None

            for elem in root.iter():
                # Limpa o namespace uma única vez para evitar múltiplos .endswith()
                tag_nome = elem.tag.split('}')[-1]

                if tag_nome == "numeroCarteira":
                    elem.text = str(random.choice(banco_carteiras))
                    contador_alteracoes += 1

                elif tag_nome in ("numeroLote", "sequencialTransacao") and config.ALTERAR_TRANSACAO_LOTE:
                    if(config.UTILIZAR_RANDOM_TRANSACAO):
                        elem.text = str(random.randint(0,1000000))
                    else:
                        valor_atual = int(elem.text.strip())
                        print(valor_atual)
                        elem.text = str(valor_atual + 1)

                elif tag_nome == "numeroGuiaPrestador":
                    if(config.ALTERAR_GUIAS):
                        guia_atual = random.randint(1000, 9999999)  # Sorteia apenas aqui!
                        elem.text = str(guia_atual)

                elif tag_nome in ("numeroGuiaOperadora", "senha", "guiaPrincipal", "guiaSolicInternacao") and guia_atual is not None:
                    if(config.ALTERAR_GUIAS):
                        elem.text = str(guia_atual)  # Reutiliza a guia sorteada no prestador
                

            if contador_alteracoes == 0:
                print(
                    "[!] Alerta: Nenhuma tag <numeroCarteira> foi localizada para alteração."
                )
            else:
                print(
                    f"[+] Sucesso: {contador_alteracoes} carteira(s) de beneficiário(s) modificada(s)."
                )

            # Recalcula e atualiza o hash digital TISS ANS
            hash_gerado = cls.atualizar_hash_tiss(root)
            if hash_gerado:
                print(f"[+] Novo Hash MD5 gravado com sucesso: {hash_gerado}")
            else:
                print(
                    "[!] Alerta: Tag <hash> não encontrada. O arquivo foi alterado mas o hash não foi embutido."
                )

            # Exporta o novo documento mantendo a codificação e cabeçalho originais obrigatórios
            tree.write(
                xml_destino,
                encoding="iso-8859-1",
                xml_declaration=True,
                method="xml",
            )
            print(f"[+] Arquivo salvo com sucesso em: {xml_destino}")

        except ET.ParseError as e:
            print(f"[-] Erro crítico: XML de origem corrompido ou inválido. ({e})")
            sys.exit(1)
        except FileNotFoundError as e:
            print(f"[-] Erro crítico: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"[-] Erro inesperado durante a execução do pipeline: {e}")
            sys.exit(1)


    @classmethod
    def preparar_conteudo_xml(cls, texto_xml: str) -> str:
        """
        Carrega o XML bruto completo para evitar tags órfãs, extrai cirurgicamente
        as informações do cabeçalho, lote de guias e hash, gerando o retorno estruturado.
        """
        # 1. Identifica dinamicamente todos os namespaces do arquivo bruto
        padrao_namespace = r'(xmlns(?::\w+)?\s*=\s*"[^"]*")'
        namespaces_encontrados = re.findall(padrao_namespace, texto_xml)
        
        # 2. Parse seguro do XML BRUTO COMPLETO
        texto_limpo_para_parse = re.sub(r'<\?xml[^>]*\?>', '', texto_xml).strip()
        texto_limpo_para_parse = f"<?xml version='1.0' encoding='iso-8859-1'?>\n{texto_limpo_para_parse}"
        
        raiz_bruta = ET.fromstring(texto_limpo_para_parse.encode('iso-8859-1'))
        
        # 3. Localiza os elementos reais que precisamos de forma imune aos namespaces
        cabecalho_no = None
        lote_guias_no = None
        hash_no = None
        
        for elemento in raiz_bruta.iter():
            tag_limpa = elemento.tag.split('}')[-1]
            if tag_limpa in ('cabecalho', 'cabeçalho'):
                cabecalho_no = elemento
            elif tag_limpa == 'loteGuias':
                lote_guias_no = elemento
            elif tag_limpa == 'hash':
                hash_no = elemento

        if not cabecalho_no or not lote_guias_no:
            raise ValueError("As tags obrigatórias <cabecalho> ou <loteGuias> não foram localizadas na estrutura do arquivo.")

        # 4. EXECUTA O SEU RECALCULO DE HASH NA ÁRVORE INTEGRAL
        # Passamos a raiz_bruta completa para que a sua função extraia os valores texto purificados das guias modificadas
        # Se a sua classe possuir outro nome ou o método não for estático, ajuste a chamada abaixo (ex: SeuObjeto.atualizar_hash_tiss(raiz_bruta))
        
        hash_gerado = cls.atualizar_hash_tiss(raiz_bruta)
        if hash_gerado:
            print(f"[+] Novo Hash MD5 gravado com sucesso para envio: {hash_gerado}")
        else:
            print(
                "[!] Alerta: Tag <hash> não encontrada. O arquivo foi alterado mas o hash não foi embutido."
            )

        # 5. Registra os prefixos originais no gerador para manter a formatação da ANS (evita 'ns0')
        for ns_string in namespaces_encontrados:
            match_ns = re.search(r'xmlns:(\w+)\s*=\s*"([^"]*)"', ns_string)
            if match_ns:
                prefixo, uri = match_ns.groups()
                ET.register_namespace(prefixo, uri)

        # 6. RECONSTRUÇÃO: Função recursiva para limpar prestadorParaOperadora e epilogo
        tags_para_remover = {'prestadorParaOperadora', 'epilogo'}

        def filtrar_elemento(elemento_atual):
            nome_limpo = elemento_atual.tag.split('}')[-1]
            
            if nome_limpo in tags_para_remover:
                filhos_convertidos = []
                for filho in elemento_atual:
                    filhos_convertidos.extend(filtrar_elemento(filho))
                return filhos_convertidos
            else:
                novo_elemento = ET.Element(elemento_atual.tag, elemento_atual.attrib)
                novo_elemento.text = elemento_atual.text
                novo_elemento.tail = elemento_atual.tail
                
                for filho in elemento_atual:
                    for novo_filho in filtrar_elemento(filho):
                        novo_elemento.append(novo_filho)
                
                return [novo_elemento]

        # 7. Serializa o cabeçalho e o lote de guias limpos de forma independente
        cabecalho_filtrado = filtrar_elemento(cabecalho_no)[0]
        lote_filtrado = filtrar_elemento(lote_guias_no)[0]
        
        xml_cabecalho = ET.tostring(cabecalho_filtrado, encoding='iso-8859-1').decode('iso-8859-1')
        xml_lote = ET.tostring(lote_filtrado, encoding='iso-8859-1').decode('iso-8859-1')
        
        # Se a tag hash foi localizada no arquivo bruto, nós filtramos/limpamos ela e serializamos também
        xml_hash = ""
        if hash_no is not None:
            hash_filtrado = filtrar_elemento(hash_no)[0]
            xml_hash = "\n" + ET.tostring(hash_filtrado, encoding='iso-8859-1').decode('iso-8859-1')
        
        # Consolida o retorno combinando as três estruturas legítimas tratadas (Cabecalho + Lote + Novo Hash calculado)
        xml_final = xml_cabecalho + xml_lote + xml_hash
        
        # Garante a remoção de quaisquer tags '<?xml...?>' fantasmas geradas nas conversões secundárias
        xml_final = re.sub(r'<\?xml[^>]*\?>', '', xml_final).strip()
        
        return xml_final