"""
Diagnóstico v3 — testa múltiplas estratégias de canonização C14N ANS.
Uso:
python diagnostico_hash_v3.py <arquivo.xml>

Testa diferentes abordagens de extração de texto para identificar qual
gera o hash MD5 que bate com o valor original no arquivo.
"""
import sys
import hashlib
import xml.etree.ElementTree as ET


def extrair_atual(elemento):
    """Estratégia atual: texto + filhos, SEM tail"""
    conteudo = ""
    if elemento.tag.endswith("epilogo") or elemento.tag.endswith("hash"):
        return ""
    if elemento.text and not list(elemento):
        texto_limpo = elemento.text.strip()
        if texto_limpo:
            conteudo += texto_limpo
    for filho in elemento:
        conteudo += extrair_atual(filho)
    return conteudo


def extrair_com_tail(elemento):
    """Estratégia com tail: texto + filhos + tail"""
    conteudo = ""
    if elemento.tag.endswith("epilogo") or elemento.tag.endswith("hash"):
        return ""
    if elemento.text and not list(elemento):
        texto_limpo = elemento.text.strip()
        if texto_limpo:
            conteudo += texto_limpo
    for filho in elemento:
        conteudo += extrair_com_tail(filho)
    # Incluir tail se existir
    if elemento.tail:
        tail_limpo = elemento.tail.strip()
        if tail_limpo:
            conteudo += tail_limpo
    return conteudo


def extrair_com_tail_raw(elemento):
    """Estratégia com tail bruto (sem strip)"""
    conteudo = ""
    if elemento.tag.endswith("epilogo") or elemento.tag.endswith("hash"):
        return ""
    if elemento.text:
        conteudo += elemento.text
    for filho in elemento:
        conteudo += extrair_com_tail_raw(filho)
    if elemento.tail:
        conteudo += elemento.tail
    return conteudo


def extrair_somente_folhas(elemento):
    """Estratégia: apenas nós folha (sem filhos)"""
    conteudo = ""
    if elemento.tag.endswith("epilogo") or elemento.tag.endswith("hash"):
        return ""
    if elemento.text and not list(elemento):
        conteudo += elemento.text.strip()
    for filho in elemento:
        conteudo += extrair_somente_folhas(filho)
    return conteudo


def extrair_com_tags(elemento):
    """Estratégia: inclui nomes das tags na cadeia"""
    conteudo = ""
    if elemento.tag.endswith("epilogo") or elemento.tag.endswith("hash"):
        return ""
    tag_nome = elemento.tag.split('}')[-1]
    if elemento.text and not list(elemento):
        texto_limpo = elemento.text.strip()
        if texto_limpo:
            conteudo += tag_nome + texto_limpo
    for filho in elemento:
        conteudo += extrair_com_tags(filho)
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

    estrategias = [
        ("Atual (texto+filhos, sem tail)", extrair_atual),
        ("Com tail (strip)", extrair_com_tail),
        ("Com tail (raw, sem strip)", extrair_com_tail_raw),
        ("Somente folhas", extrair_somente_folhas),
        ("Com nomes de tags", extrair_com_tags),
    ]

    print(f"Arquivo: {caminho}")
    print(f"Hash no arquivo (ANS): {hash_no_arquivo}")
    print(f"\n{'='*70}")
    print(f"{'Estratégia':<40} {'Hash Calculado':<35} {'Match'}")
    print(f"{'='*70}")

    for nome, func in estrategias:
        cadeia = func(root)
        try:
            hash_calc = hashlib.md5(cadeia.encode("iso-8859-1")).hexdigest()
            match = "✅ BATE" if hash_calc == hash_no_arquivo else "❌"
            print(f"{nome:<40} {hash_calc:<35} {match}")
        except Exception as e:
            print(f"{nome:<40} ERRO: {e}")

    # Mostrar preview das cadeias para as estratégias que não bateram
    print(f"\n{'='*70}")
    print("Preview das cadeias (primeiros 150 chars):")
    print(f"{'='*70}")
    for nome, func in estrategias[:3]:  # Só as 3 primeiras
        cadeia = func(root)
        print(f"\n{nome}:")
        print(f"  Len: {len(cadeia)}")
        print(f"  Preview: {repr(cadeia[:150])}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python diagnostico_hash_v3.py <arquivo.xml>")
        sys.exit(1)
    try:
        analisar(sys.argv[1])
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)