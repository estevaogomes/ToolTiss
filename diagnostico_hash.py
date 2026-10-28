"""
Diagnóstico comparativo de estrutura XML TISS.
Uso: python diagnostico_hash.py <arquivo_que_passa.xml> <arquivo_que_falha.xml>

Gera relatório lado-a-lado de:
- Tags presentes/ausentes
- Profundidade máxima
- Contagem de elementos por tag
- Cadeia de texto usada no hash (C14N simplificada)
- Hash MD5 resultante em iso-8859-1
"""
import sys
import hashlib
import xml.etree.ElementTree as ET
from collections import Counter


def extrair_valores_texto_tiss(elemento):
    """Mesma lógica do TissXmlService._extrair_valores_texto_tiss"""
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


def analisar_xml(caminho):
    parser = ET.XMLParser(encoding="iso-8859-1")
    tree = ET.parse(caminho, parser)
    root = tree.getroot()

    tags = Counter()
    profundidades = []

    def percorrer(elem, profundidade):
        tag_limpa = elem.tag.split('}')[-1]
        tags[tag_limpa] += 1
        profundidades.append(profundidade)
        for filho in elem:
            percorrer(filho, profundidade + 1)

    percorrer(root, 0)

    cadeia = extrair_valores_texto_tiss(root)
    hash_md5 = hashlib.md5(cadeia.encode("iso-8859-1")).hexdigest()

    return {
        "caminho": caminho,
        "tags": tags,
        "profundidade_max": max(profundidades) if profundidades else 0,
        "total_elementos": sum(tags.values()),
        "cadeia_len": len(cadeia),
        "cadeia_preview": cadeia[:200],
        "hash": hash_md5,
        "encoding_decl": tree.getroot().tag,
    }


def comparar(a, b):
    print(f"\n{'='*70}")
    print(f"PASSA: {a['caminho']}")
    print(f"FALHA: {b['caminho']}")
    print(f"{'='*70}")

    print(f"\n--- Métricas ---")
    print(f"{'Métrica':<25} {'Passa':>10} {'Falha':>10}")
    print(f"{'Total elementos':<25} {a['total_elementos']:>10} {b['total_elementos']:>10}")
    print(f"{'Profundidade máx':<25} {a['profundidade_max']:>10} {b['profundidade_max']:>10}")
    print(f"{'Cadeia hash (len)':<25} {a['cadeia_len']:>10} {b['cadeia_len']:>10}")
    print(f"{'Hash MD5':<25} {a['hash']:>10} {b['hash']:>10}")

    todas_tags = sorted(set(list(a['tags'].keys()) + list(b['tags'].keys())))
    print(f"\n--- Tags (diferenças marcadas com *) ---")
    print(f"{'Tag':<35} {'Passa':>8} {'Falha':>8}")
    for tag in todas_tags:
        ca = a['tags'].get(tag, 0)
        cb = b['tags'].get(tag, 0)
        marca = " *" if ca != cb else ""
        print(f"{tag:<35} {ca:>8} {cb:>8}{marca}")

    tags_so_a = set(a['tags'].keys()) - set(b['tags'].keys())
    tags_so_b = set(b['tags'].keys()) - set(a['tags'].keys())
    if tags_so_a:
        print(f"\n⚠ Tags SÓ no arquivo que PASSA: {sorted(tags_so_a)}")
    if tags_so_b:
        print(f"\n⚠ Tags SÓ no arquivo que FALHA: {sorted(tags_so_b)}")

    print(f"\n--- Preview cadeia hash (primeiros 200 chars) ---")
    print(f"PASSA: {a['cadeia_preview']!r}")
    print(f"FALHA: {b['cadeia_preview']!r}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python diagnostico_hash.py <arquivo_passa.xml> <arquivo_falha.xml>")
        sys.exit(1)

    try:
        a = analisar_xml(sys.argv[1])
        b = analisar_xml(sys.argv[2])
        comparar(a, b)
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)