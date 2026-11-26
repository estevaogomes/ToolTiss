import sys
sys.path.insert(0, r'c:\Users\t2730\Documents\Airlines\dev\ToolTiss')
from services.TissXmlService import TissXmlService
import xml.etree.ElementTree as ET
import hashlib
import re

arquivos = {
    'A': r'Testando\0014449991_1161640A_1.xml',
    'C': r'Testando\0014449992_1161640C_1.xml',
}

for label, caminho in arquivos.items():
    with open(caminho, 'r', encoding='iso-8859-1') as f:
        conteudo = f.read()

    # Parse original
    tree = ET.fromstring(conteudo.encode('iso-8859-1'))

    # Extrai cadeia COM tail (como a ANS pode esperar)
    def extrair_com_tail(elemento):
        conteudo = ""
        if elemento.tag.endswith("epilogo") or elemento.tag.endswith("hash"):
            return ""
        if elemento.text and not list(elemento):
            conteudo += elemento.text
        for filho in elemento:
            conteudo += extrair_com_tail(filho)
            # Inclui tail do filho (texto apos a tag de fechamento do filho)
            if filho.tail:
                conteudo += filho.tail
        return conteudo

    # Extrai cadeia SEM tail (implementacao atual)
    cadeia_sem_tail = TissXmlService._extrair_valores_texto_tiss(tree)
    cadeia_com_tail = extrair_com_tail(tree)

    hash_sem_tail = hashlib.md5(cadeia_sem_tail.encode('iso-8859-1')).hexdigest()
    hash_com_tail = hashlib.md5(cadeia_com_tail.encode('iso-8859-1')).hexdigest()

    # Hash original do arquivo
    hash_orig_match = re.search(r'<ans:hash>([a-fA-F0-9]{32})</ans:hash>', conteudo, re.IGNORECASE)
    hash_original = hash_orig_match.group(1).lower() if hash_orig_match else 'NAO_ENCONTRADO'

    print(f'=== ARQUIVO {label} ===')
    print(f'Hash ORIGINAL no arquivo:  {hash_original}')
    print(f'Hash SEM tail (atual):     {hash_sem_tail}')
    print(f'Hash COM tail:             {hash_com_tail}')
    print(f'SEM tail == original:      {hash_sem_tail == hash_original}')
    print(f'COM tail == original:      {hash_com_tail == hash_original}')
    print(f'Tamanho cadeia SEM tail:   {len(cadeia_sem_tail)}')
    print(f'Tamanho cadeia COM tail:   {len(cadeia_com_tail)}')
    print(f'Diferenca de tamanho:      {len(cadeia_com_tail) - len(cadeia_sem_tail)} chars')

    # Mostra amostra das primeiras diferencas
    if cadeia_sem_tail != cadeia_com_tail:
        for i in range(min(len(cadeia_sem_tail), len(cadeia_com_tail))):
            if cadeia_sem_tail[i] != cadeia_com_tail[i]:
                print(f'Primeira diferenca na posicao {i}:')
                print(f'  SEM tail: ...{repr(cadeia_sem_tail[max(0,i-20):i+20])}...')
                print(f'  COM tail: ...{repr(cadeia_com_tail[max(0,i-20):i+20])}...')
                break
    print()