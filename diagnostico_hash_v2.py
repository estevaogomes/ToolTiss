"""
Diagnóstico v2 — valida hash MD5 TISS contra valor original esperado.

Uso:
  python diagnostico_hash_v2.py <arquivo_original_com_hash_valido.xml>

O script:
1. Lê o hash MD5 original já presente na tag <hash> (considerado válido pela ANS)
2. Extrai a cadeia de texto ANTES de qualquer alteração (cadeia_original)
3. Gera MD5 dessa cadeia (hash_calculado_original)
4. Compara hash_calculado_original vs hash_no_arquivo — se bater, nossa extração está ok
5. Se NÃO bater, mostra divergência: nossa extração C14N está errada para este arquivo

Isso isola se o bug é:
  (a) nossa extração de texto (cadeia) está errada — hash_calculado != hash_no_arquivo
  (b) nossa extração está ok mas algo acontece durante processamento posterior
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
    hash_calculado = hashlib.md5(cadeia.encode("iso-8859-1")).hexdigest()

    print(f"Arquivo: {caminho}")
    print(f"Hash no arquivo (ANS):    {hash_no_arquivo}")
    print(f"Hash que nós calculamos: {hash_calculado}")
    print(f"Cadeia (len):            {len(cadeia)}")

    if hash_calculado == hash_no_arquivo:
        print("✅ BATE — nossa extração C14N está correta para este arquivo")
        print("   Problema está em ALGUMA modificação feita no pipeline posterior.")
    else:
        print("❌ NÃO BATE — nossa extração C14N já gera hash errado ANTES de qualquer alteração!")
        print("   Este arquivo é um caso problemático. Precisamos investigar a cadeia.")

    print(f"\n--- Cadeia completa usada no hash ---")
    print(repr(cadeia))
    print(f"\n--- Cadeia em blocos de 80 chars ---")
    for i in range(0, len(cadeia), 80):
        print(f"[{i:04d}] {repr(cadeia[i:i+80])}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python diagnostico_hash_v2.py <arquivo.xml>")
        sys.exit(1)
    try:
        analisar(sys.argv[1])
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)