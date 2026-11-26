import hashlib
import nt
import random
import re
import sys
from services.DataExtractorService import DataExtractorService
import config
import xml.etree.ElementTree as ET


class TissXmlService:

    @classmethod
    def detectar_versao_tiss(cls, conteudo_xml):
        """Extrai a versão TISS da tag <Padrao> no cabecalho do XML.

        Retorna a string de versão (ex: '4.03.00', '4.02.00') ou None se não encontrada.
        Usa regex para evitar parse completo do XML, já que esta função é chamada
        antes do processamento para selecionar o endpoint correto.
        """
        match = re.search(r'<[^>]*:?Padrao>([^<]+)</[^>]*:?Padrao>', conteudo_xml)
        if match:
            return match.group(1).strip()
        return None

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
        # 0. Indenta a árvore ANTES de calcular o hash para garantir que
        # a serialização posterior produza XML formatado. A indentação
        # não altera o hash porque _extrair_valores_texto_tiss ignora
        # tails/whitespace entre tags (regra C14N ANS).
        try:
            ET.indent(root, space="    ")
        except AttributeError:
            pass  # Python < 3.9 não tem ET.indent

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

                if tag_nome == "numeroCarteira" and config.ALTERAR_CARTEIRAS:
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
            # Nota: a indentação já foi aplicada em atualizar_hash_tiss() antes do
            # recálculo do hash, garantindo XML formatado sem alterar a assinatura.
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

        # 4. Registra os prefixos originais no gerador para manter a formatação da ANS (evita 'ns0')
        for ns_string in namespaces_encontrados:
            match_ns = re.search(r'xmlns:(\w+)\s*=\s*"([^"]*)"', ns_string)
            if match_ns:
                prefixo, uri = match_ns.groups()
                ET.register_namespace(prefixo, uri)

        # 5. RECONSTRUÇÃO: Função recursiva para remover apenas <epilogo>.
        # IMPORTANTE: <prestadorParaOperadora> NÃO deve ser removido nem ter seus
        # filhos elevados. Conforme XSD tissV4_03_00.xsd linha 16, ele é um elemento
        # legítimo da estrutura <mensagemTISS> e contém dados como codigoPrestadorNaOperadora
        # que são exigidos pelo servidor da operadora para identificação do prestador.
        # Removê-lo causa erro "prestador não localizado" mesmo com hash correto.
        tags_para_remover = {'epilogo'}

        def filtrar_elemento(elemento_atual):
            nome_limpo = elemento_atual.tag.split('}')[-1]

            if nome_limpo in tags_para_remover:
                filhos_convertidos = []
                for filho in elemento_atual:
                    filhos_convertidos.extend(filtrar_elemento(filho))
                return filhos_convertidos
            else:
                # Filtra atributos de namespace redundantes (xmlns, xmlns:*) para evitar
                # que o ElementTree reinsira declarações duplicadas na serialização.
                # O namespace já está registrado globalmente via ET.register_namespace.
                atributos_filtrados = {
                    k: v for k, v in elemento_atual.attrib.items()
                    if not k.startswith('xmlns') and k != 'xmlns'
                }
                novo_elemento = ET.Element(elemento_atual.tag, atributos_filtrados)
                novo_elemento.text = elemento_atual.text
                # Limpa tail para evitar whitespace artefato na serialização.
                # O tail é formatação física entre irmãos e não faz parte do
                # conteúdo assinado pela regra ANS C14N. Sua preservação causa
                # \n inicial no payload que invalida hash byte-a-byte (erro 5014).
                novo_elemento.tail = None

                for filho in elemento_atual:
                    for novo_filho in filtrar_elemento(filho):
                        novo_elemento.append(novo_filho)

                return [novo_elemento]

        # 6. Serializa o cabeçalho e o lote de guias limpos de forma independente
        cabecalho_filtrado = filtrar_elemento(cabecalho_no)[0]
        lote_filtrado = filtrar_elemento(lote_guias_no)[0]

        xml_cabecalho = ET.tostring(cabecalho_filtrado, encoding='iso-8859-1').decode('iso-8859-1')
        xml_lote = ET.tostring(lote_filtrado, encoding='iso-8859-1').decode('iso-8859-1')

        # Remove declarações XML residuais E namespaces redundantes que o ElementTree
        # reinsere automaticamente ao serializar elementos com tags namespaced.
        # O namespace já está declarado no wrapper <mensagemTISS> ou no envelope SOAP.
        # IMPORTANTE: não aplicar .strip() para preservar whitespace literal interno
        # conforme regra ANS item 148, mas os namespaces redundantes DEVEM ser removidos
        # pois não existiam no XML original e sua presença altera a cadeia de hash.
        # Remove declaração XML E o newline que o ET.tostring() insere logo após ela.
        # O \n pós-declaração é artefato de serialização, não conteúdo assinado.
        xml_cabecalho_limpo = re.sub(r'<\?xml[^>]*\?>\s*', '', xml_cabecalho)
        xml_cabecalho_limpo = re.sub(r'\s+xmlns(?::\w+)?\s*=\s*"[^"]*"', '', xml_cabecalho_limpo)
        xml_lote_limpo = re.sub(r'<\?xml[^>]*\?>\s*', '', xml_lote)
        xml_lote_limpo = re.sub(r'\s+xmlns(?::\w+)?\s*=\s*"[^"]*"', '', xml_lote_limpo)

        # 7. CALCULA O HASH APÓS FILTRAR - sobre o conteúdo exato que será enviado
        # Cria uma árvore temporária com apenas cabecalho + loteGuias (sem prestadorParaOperadora/epilogo)
        # para garantir que o hash seja calculado sobre exatamente o mesmo conteúdo do envelope SOAP
        conteudo_para_hash = xml_cabecalho_limpo + xml_lote_limpo
        conteudo_para_hash = f"<?xml version='1.0' encoding='iso-8859-1'?><ans:mensagemTISS xmlns:ans=\"http://www.ans.gov.br/padroes/tiss/schemas\">{conteudo_para_hash}</ans:mensagemTISS>"

        try:
            raiz_filtrada = ET.fromstring(conteudo_para_hash.encode('iso-8859-1'))
            # Calcula o hash diretamente sobre a árvore filtrada (sem depender da tag <hash>)
            # A função _extrair_valores_texto_tiss já ignora <epilogo> e <hash>, então podemos usá-la diretamente
            cadeia_valores = cls._extrair_valores_texto_tiss(raiz_filtrada)
            hash_gerado = hashlib.md5(cadeia_valores.encode("iso-8859-1")).hexdigest()
            print(f"[+] Novo Hash MD5 calculado após filtragem para envio: {hash_gerado}")
        except Exception as e:
            print(f"[!] Erro ao recalcular hash após filtragem: {e}")
            hash_gerado = None

        # 8. Constrói a tag hash com o valor recalculado.
        # IMPORTANTE: Não remover namespaces via regex nem aplicar .strip().
        # A regra ANS exige conteúdo literal; a tag <ans:hash> é filha direta
        # de <loteGuiasWS> conforme XSD tissWebServicesV4_03_00.xsd linha 72.
        xml_hash = ""
        if hash_gerado:
            xml_hash = f"<ans:hash>{hash_gerado}</ans:hash>"
        elif hash_no is not None:
            # Fallback: usa o hash original se o recálculo falhar
            hash_filtrado = filtrar_elemento(hash_no)[0]
            xml_hash_raw = ET.tostring(hash_filtrado, encoding='iso-8859-1').decode('iso-8859-1')
            xml_hash = re.sub(r'<\?xml[^>]*\?>', '', xml_hash_raw)

        # Consolida o retorno concatenando cabecalho + loteGuias + hash
        xml_final = xml_cabecalho_limpo + xml_lote_limpo + xml_hash

        # Remove APENAS declarações XML residuais. NÃO aplicar .strip():
        # whitespace no início/fim do payload faz parte do conteúdo assinado
        # conforme regra ANS item 148 ("sem qualquer supressão").
        xml_final = re.sub(r'<\?xml[^>]*\?>', '', xml_final)

        return xml_final