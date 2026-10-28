"""
Diagnóstico v6 — testa exclusão de tags específicas para identificar quais a ANS ignora no hash.

Uso:
  python diagnostico_hash_v6.py <arquivo_que_falha.xml>

Baseado no diagnóstico v1, arquivo FALHA tem tags com contagem diferente.
Este script testa se excluir certas tags faz o hash bater com o valor original.
"""
import sys
import hashlib
import xml.etree.ElementTree as ET

# Tags candidatas a exclusão (baseado no diagnóstico v1 - tags com contagem diferente)
TAGS_CANDIDATAS_EXCLUSAO = [
    'procedimentoExecutado',
    'procedimentosExecutados',
    'contratadoExecutante',
    'dadosExecutante',
    'dadosSolicitante',
    'contratadoSolicitante',
    'profissionalSolicitante',
    'dadosSolicitacao',
    'horaInicial',
    'horaFinal',
    'dataExecucao',
    'sequencialItem',
    'codigoProcedimento',
    'codigoTabela',
    'descricaoProcedimento',
    'quantidadeExecutada',
    'valorUnitario',
    'reducaoAcrescimo',
    'viaAcesso',
    'tecnicaUtilizada',
    'valorTotal',
]

def extrair_valores_excluindo_tags(elemento, tags_excluir):
    """Extrai texto excluindo tags específicas e seus descendentes"""
    conteudo = ""

    # Pula epilogo e hash (igual ao original)
    if elemento.tag.endswith("epilogo") or elemento.tag.endswith("hash"):
        return ""

    # Verifica se esta tag deve ser excluída
    tag_nome = elemento.tag.split('}')[-1]
    if tag_nome in tags_excluir:
        return ""  # Exclui esta tag e todos os descendentes

    if elemento.text and not list(elemento):
        texto_limpo = elemento.text.strip()
        if texto_limpo:
            conteudo += texto_limpo

    for filho in elemento:
        conteudo += extrair_valores_excluindo_tags(filho, tags_excluir)

    return conteudo

def extrair_valores_texto_tiss(elemento):
    """Lógica atual sem exclusões extras"""
    conteudo = ""
    if elemento.tag.endswith("epilogo") or elemento.tag.endswith("hash"):
        return ""
    if elemento.text and not list(elemento):
        texto_limpo = elemento.text.strip()
        if texto_limpo:
            conteudo += texto_limpo
    for filho in elemento:
        conteudo += extrair_valores_texto_tiss(filho)
    return conteudo

def analisar(caminho):
    parser = ET.XMLParser(encoding="iso-8859-1")
    tree = ET.parse(caminho, parser)
    root = tree.getroot()

    hash_no_arquivo = None
    for elem in root.iter():
        if elem.tag.endswith("hash"):
            hash_no_arquivo = (elem.text or "").strip()
            break

    if hash_no_arquivo is None:
        print("[-] Tag <hash> não encontrada no arquivo")
        return

    hash_arquivo_lower = hash_no_arquivo.lower()

    print(f"Arquivo: {caminho}")
    print(f"Hash no arquivo (ANS): {hash_no_arquivo}")
    print(f"\n{'='*80}")
    print(f"{'Tags excluídas':<50} {'Hash Calculado':<35} {'Match'}")
    print(f"{'='*80}")

    # Teste baseline (sem exclusões extras)
    cadeia = extrair_valores_texto_tiss(root)
    hash_calc = hashlib.md5(cadeia.encode("iso-8859-1")).hexdigest()
    match = "✅ BATE" if hash_calc == hash_arquivo_lower else "❌"
    print(f"{'(nenhuma)':<50} {hash_calc:<35} {match}")
    print(f" Cadeia len: {len(cadeia)}")

    # Testar exclusão de cada tag individualmente
    print(f"\n{'='*80}")
    print("Testando exclusão de tags individuais:")
    print(f"{'='*80}")

    for tag in TAGS_CANDIDATAS_EXCLUSAO:
        cadeia = extrair_valores_excluindo_tags(root, [tag])
        hash_calc = hashlib.md5(cadeia.encode("iso-8859-1")).hexdigest()
        match = "✅ BATE" if hash_calc == hash_arquivo_lower else "❌"
        print(f"{tag:<50} {hash_calc:<35} {match}")
        print(f" Cadeia len: {len(cadeia)}")

    # Testar combinações de tags mais prováveis
    print(f"\n{'='*80}")
    print("Testando combinações de tags:")
    print(f"{'='*80}")

    combinacoes = [
        (['procedimentoExecutado'], "procedimentoExecutado (tag wrapper)"),
        (['procedimentoExecutado', 'contratadoExecutante', 'dadosExecutante'], "procedimentoExecutado + dados executante"),
        (['procedimentoExecutado', 'contratadoExecutante', 'dadosExecutante', 'horaInicial', 'horaFinal', 'dataExecucao'], "procedimentoExecutado + dados executante + tempo"),
    ]

    for tags, descricao in combinacoes:
        cadeia = extrair_valores_excluindo_tags(root, tags)
        hash_calc = hashlib.md5(cadeia.encode("iso-8859-1")).hexdigest()
        match = "✅ BATE" if hash_calc == hash_arquivo_lower else "❌"
        print(f"{descricao:<50} {hash_calc:<35} {match}")
        print(f" Cadeia len: {len(cadeia)}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python diagnostico_hash_v6.py <arquivo.xml>")
        sys.exit(1)
    try:
        analisar(sys.argv[1])
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)