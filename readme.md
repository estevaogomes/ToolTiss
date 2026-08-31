# 🥁 ToolTiss (Ba-dum-tss! 🥁)

O **ToolTiss** é um orquestrador e transmissor de lotes XML no padrão **TISS (Agência Nacional de Saúde Suplementar)**. Ele foi desenvolvido para automatizar o processo de edição, mascaramento de dados sensíveis de beneficiários (em conformidade com as boas práticas de segurança de dados), recálculo de assinaturas digitais (Hash MD5) e transmissão via protocolo SOAP diretamente para o WebService de operadoras de saúde.

A aplicação conta com uma interface gráfica moderna e fluida desenvolvida em **CustomTkinter** e pode ser compilada como um executável autônomo para o usuário final.

---

## 🛠️ Funcionalidades

- **Duplo Escopo de Execução:** Permite processar e enviar um único arquivo XML TISS de teste ou realizar a varredura e transmissão sequencial de uma pasta inteira de arquivos.
- **Mascaramento Automatizado (`ALTERAR_LOTES`):** Substituição aleatória e segura de números de carteirinhas de beneficiários com base em uma planilha de referência (CSV/Excel).
- **Gerenciador de Identificadores (`ALTERAR_GUIAS`):** Sorteio de novos números de guias do prestador, guias principais e senhas para evitar rejeições por duplicidade no servidor.
- **Recálculo de Hash ANS:** Algoritmo integrado que limpa o Hash antigo, extrai os valores textuais puros das guias modificadas conforme a regra de canonização (C14N) e embutirá a nova assinatura MD5 válida.
- **Higienização Estrutural TISS:** Edita o arquivo XML em tempo real para iniciar estritamente a partir da tag `<cabecalho>`, eliminando wrappers intermediários como `<prestadorParaOperadora>` e `<epilogo>`, mantendo apenas o conteúdo útil exigido pelo envelope SOAP.
- **Controle Total de Ambiente:** Interface gráfica com aba dedicada para gerenciar em tempo real todas as chaves do arquivo `config.py` (URLs, Actions, Timeouts e chaves liga/desliga de fluxo).
- **Manual Integrado:** Botão nativo na tela que extrai e abre o manual do usuário em PDF diretamente do executável.

---

## 📂 Estrutura do Projeto

```text
ToolTiss/
├── comunication/
│   └── SoapClient.py          # Cliente HTTP SOAP (envelopamento e transmissão)
├── services/
│   ├── DataExtractorService.py# Leitura e extração de dados das planilhas
│   └── TissXmlService.py      # Tratamento estrutural do XML e recálculo de Hash
├── config.py                  # Arquivo de propriedades e variáveis globais
├── tooltiss.py                # Arquivo principal (Interface Gráfica CustomTkinter)
├── manual_usuario.pdf         # Manual do usuário para o operador leigo
├── bateria.ico                # Ícone visual do executável (Trocadilho ToolTiss 🔋)
└── .gitignore                 # Filtro de rastreamento do Git
```

---

## 🚀 Como Rodar o Projeto

### Pré-requisitos

Certifique-se de ter o Python instalado (recomendado 3.10 ou superior) e instale as dependências do projeto:

```bash
pip install customtkinter requests
```

### Execução via Código Fonte

Para iniciar a interface gráfica pelo terminal, execute:

```bash
python tooltiss.py
```

---

## 📦 Como Gerar o Executável (`.exe`)

Para compilar a aplicação em um arquivo único e independente para o Windows, garantindo que a biblioteca visual e o manual em PDF fiquem embutidos, execute o PyInstaller através do módulo do Python:

```bash
python -m PyInstaller --clean --noconsole --onefile --collect-all customtkinter --add-data "manual.pdf;." -n "ToolTiss" -i "bateria.ico" tooltiss.py
```

O arquivo finalizado **`ToolTiss.exe`** será gerado dentro da pasta **`dist/`** e estará pronto para distribuição, sem necessidade de instalação de dependências na máquina do usuário.

---

## 🚨 Configuração do `.gitignore`

Este repositório está configurado para **nunca** rastrear ou expor dados reais de produção ou arquivos gerados durante a compilação. Certifique-se de que seu arquivo `.gitignore` contenha:

```text
__pycache__/
*.pyc
build/
dist/
*.spec
*.csv
*.txt
*.xml
!tooltiss.py
```
