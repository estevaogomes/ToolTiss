"""
Diagnóstico v4 — testa encoding UTF-8 vs ISO-8859-1 no cálculo do hash MD5 TISS.

Uso:
    python diagnostico_hash_v4.py <arquivo.xml>

A biblioteca tiss-hash (referência canônica ANS) usa UTF-8 para gerar o MD5.
Nosso código atual usa ISO-8859-1. Este script compara ambos.
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

    if hash_no_arquivo is None:
        print("[-] Tag <hash> não encontrada no arquivo")
        return

    cadeia = extrair_valores_texto_tiss(root)

    # Hash com ISO-8859-1 (atual)
    hash_iso = hashlib.md5(cadeia.encode("iso-8859-1")).hexdigest()

    # Hash com UTF-8 (correto segundo tiss-hash / referência ANS)
    hash_utf8 = hashlib.md5(cadeia.encode("utf-8")).hexdigest()

    # Normalizar case para comparação (ANS pode usar upper ou lower)
    hash_arquivo_lower = hash_no_arquivo.lower()

    print(f"Arquivo: {caminho}")
    print(f"Hash no arquivo (ANS):  {hash_no_arquivo}")
    print(f"Hash ISO-8859-1 (atual): {hash_iso}  {'✅ BATE' if hash_iso == hash_arquivo_lower else '❌'}")
    print(f"Hash UTF-8 (correto):   {hash_utf8}  {'✅ BATE' if hash_utf8 == hash_arquivo_lower else '❌'}")

    if hash_utf8 == hash_arquivo_lower:
        print("\n🎯 CONFIRMADO: problema é encoding. Trocar iso-8859-1 por utf-8 no encode() resolve.")
    elif hash_iso == hash_arquivo_lower:
        print("\n⚠ ISO-8859-1 bateu mas UTF-8 não. Encoding atual está correto para este arquivo.")
    else:
        print("\n❓ Nenhum encoding bateu. Problema pode ser outro (ordem de elementos, tags extras, etc).")

    # Mostrar diferença de bytes nos caracteres acentuados
    print(f"\nCadeia (len): {len(cadeia)}")
    chars_acentuados = [c for c in cadeia if ord(c) > 127]
    if chars_acentuados:
        print(f"Caracteres acentuados na cadeia: {len(chars_acentuados)} ocorrências")
        print(f"Exemplo: '{chars_acentuados[0]}' → UTF-8: {chars_acentuados[0].encode('utf-8').hex()} | ISO-8859-1: {chars_acentuados[0].encode('iso-8859-1').hex()}")
    else:
        print("Nenhum caractere acentuado na cadeia (ASCII puro)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python diagnostico_hash_v4.py <arquivo.xml>")
        sys.exit(1)
    try:
        analisar(sys.argv[1])
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)