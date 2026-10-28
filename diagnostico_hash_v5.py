"""
Diagnóstico v5 — compara extração de cadeia entre arquivo que passa e arquivo que falha.
Uso:
python diagnostico_hash_v5.py <arquivo_que_passa.xml> <arquivo_que_falha.xml>

Objetivo: identificar divergências na extração que causam hash inválido em alguns arquivos.
"""
import sys
import hashlib
import xml.etree.ElementTree as ET

def extrair_valores_texto_tiss(elemento):
    """Mesma lógica de TissXmlService._extrair_valores_texto_tiss"""
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

    cadeia = extrair_valores_texto_tiss(root)
    hash_calc = hashlib.md5(cadeia.encode("iso-8859-1")).hexdigest()

    return {
        "caminho": caminho,
        "hash_arquivo": hash_no_arquivo,
        "hash_calc": hash_calc,
        "cadeia": cadeia,
        "match": hash_calc.lower() == (hash_no_arquivo or "").lower()
    }

def comparar(a, b):
    print(f"{'='*80}")
    print(f"PASSA: {a['caminho']}")
    print(f"  Hash arquivo: {a['hash_arquivo']}")
    print(f"  Hash calculado: {a['hash_calc']} {'✅' if a['match'] else '❌'}")
    print(f"  Cadeia len: {len(a['cadeia'])}")
    print()
    print(f"FALHA: {b['caminho']}")
    print(f"  Hash arquivo: {b['hash_arquivo']}")
    print(f"  Hash calculado: {b['hash_calc']} {'✅' if b['match'] else '❌'}")
    print(f"  Cadeia len: {len(b['cadeia'])}")
    print(f"{'='*80}")

    # Encontrar primeira divergência
    cadeias_a = a['cadeia']
    cadeias_b = b['cadeia']

    divergencia_pos = None
    for i in range(min(len(cadeias_a), len(cadeias_b))):
        if cadeias_a[i] != cadeias_b[i]:
            divergencia_pos = i
            break

    if divergencia_pos is not None:
        print(f"\n⚠ Primeira divergência na posição: {divergencia_pos}")
        print(f"\nContexto PASSA (pos {max(0,divergencia_pos-30)} a {divergencia_pos+30}):")
        print(repr(cadeias_a[max(0,divergencia_pos-30):divergencia_pos+30]))
        print(f"\nContexto FALHA (pos {max(0,divergencia_pos-30)} a {divergencia_pos+30}):")
        print(repr(cadeias_b[max(0,divergencia_pos-30):divergencia_pos+30]))
    else:
        print(f"\n✅ Cadeias idênticas até posição {min(len(cadeias_a), len(cadeias_b))}")
        if len(cadeias_a) != len(cadeias_b):
            print(f"⚠ Mas comprimentos diferentes: PASSA={len(cadeias_a)}, FALHA={len(cadeias_b)}")

    # Comparar primeiros 300 chars
    print(f"\n{'='*80}")
    print("Primeiros 300 chars:")
    print(f"{'='*80}")
    print(f"PASSA: {repr(cadeias_a[:300])}")
    print(f"FALHA: {repr(cadeias_b[:300])}")

    # Verificar caracteres não-ASCII
    print(f"\n{'='*80}")
    print("Caracteres não-ASCII:")
    print(f"{'='*80}")
    nao_ascii_a = [c for c in cadeias_a if ord(c) > 127]
    nao_ascii_b = [c for c in cadeias_b if ord(c) > 127]
    print(f"PASSA: {len(nao_ascii_a)} ocorrências")
    print(f"FALHA: {len(nao_ascii_b)} ocorrências")

    if nao_ascii_a:
        print(f"\nExemplos PASSA: {set(nao_ascii_a[:20])}")
    if nao_ascii_b:
        print(f"\nExemplos FALHA: {set(nao_ascii_b[:20])}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python diagnostico_hash_v5.py <arquivo_que_passa.xml> <arquivo_que_falha.xml>")
        sys.exit(1)

    try:
        a = analisar(sys.argv[1])
        b = analisar(sys.argv[2])
        comparar(a, b)
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)