import os
import glob
import sys
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Importações originais do seu ecossistema
import config
from services.TissXmlService import TissXmlService
from comunication.SoapClient import TissSoapClient

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class TissMasterGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Gerenciador TISS ANS - Painel de Controle")
        self.geometry("760x680")
        self.resizable(False, False)

        # Mapeamento de Estados Iniciais vindo do seu config.py
        self.modo_execucao = ctk.StringVar(value="pasta") # "pasta" ou "arquivo"
        self.pasta_origem_var = ctk.StringVar(value=os.getcwd())
        self.arquivo_unico_var = ctk.StringVar(value=config.CAMINHO_XML_ENTRADA)
        
        self.planilha_var = ctk.StringVar(value=config.CAMINHO_PLANILHA_CARTEIRAS)
        self.coluna_var = ctk.StringVar(value=config.COLUNA_ALVO if config.COLUNA_ALVO else "")
        self.url_var = ctk.StringVar(value=config.URL_OPERADORA)
        self.action_var = ctk.StringVar(value=config.SOAP_ACTION_METODO)
        self.timeout_var = ctk.StringVar(value=str(config.TIMEOUT_REQUISICAO))

        # --- INTERFACE GRÁFICA ---
        
        # Abas de Separação (Execução vs Configurações Avançadas)
        self.tabview = ctk.CTkTabview(self, width=720, height=420)
        self.tabview.pack(pady=10, padx=20)
        
        self.tab_painel = self.tabview.add("Painel de Envio")
        self.tab_config = self.tabview.add("Configurações do Sistema (config.py)")

        # =====================================================================
        # CONTEÚDO DA ABA 1: PAINEL DE ENVIO
        # =====================================================================
        
        # Seletor de Modo: Pasta ou Arquivo Único
        self.frm_modo = ctk.CTkFrame(self.tab_painel)
        self.frm_modo.pack(pady=10, padx=10, fill="x")
        
        self.lbl_modo = ctk.CTkLabel(self.frm_modo, text="Selecione o escopo do envio:", font=ctk.CTkFont(weight="bold"))
        self.lbl_modo.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.rdb_pasta = ctk.CTkRadioButton(self.frm_modo, text="Processar pasta de XMLs", variable=self.modo_execucao, value="pasta", command=self.alternar_campos_modo)
        self.rdb_pasta.grid(row=1, column=0, padx=20, pady=5, sticky="w")
        
        self.rdb_arquivo = ctk.CTkRadioButton(self.frm_modo, text="Processar arquivo XML único", variable=self.modo_execucao, value="arquivo", command=self.alternar_campos_modo)
        self.rdb_arquivo.grid(row=1, column=1, padx=20, pady=5, sticky="w")

        # Container Dinâmico de Inputs de Origem
        self.frm_origem = ctk.CTkFrame(self.tab_painel)
        self.frm_origem.pack(pady=10, padx=10, fill="x")

        # Campo Dinâmico: Pasta
        self.lbl_pasta = ctk.CTkLabel(self.frm_origem, text="Pasta com os XMLs de Origem:", font=ctk.CTkFont(weight="bold"))
        self.lbl_pasta.grid(row=0, column=0, padx=10, pady=2, sticky="w")
        self.entry_pasta = ctk.CTkEntry(self.frm_origem, textvariable=self.pasta_origem_var, width=540)
        self.entry_pasta.grid(row=1, column=0, padx=10, pady=5)
        self.btn_pasta = ctk.CTkButton(self.frm_origem, text="Procurar...", width=100, command=self.buscar_pasta)
        self.btn_pasta.grid(row=1, column=1, padx=10, pady=5)

        # Campo Dinâmico: Arquivo Único (Inicia ocultado via layout managers)
        self.lbl_arq_unico = ctk.CTkLabel(self.frm_origem, text="Selecione o XML único de Entrada:", font=ctk.CTkFont(weight="bold"))
        self.entry_arq_unico = ctk.CTkEntry(self.frm_origem, textvariable=self.arquivo_unico_var, width=540)
        self.btn_arq_unico = ctk.CTkButton(self.frm_origem, text="Procurar...", width=100, command=self.buscar_arquivo_xml)

        # Input Comum: Planilha de Referência
        self.lbl_planilha = ctk.CTkLabel(self.tab_painel, text="Planilha Base de Carteiras (CSV/Excel):", font=ctk.CTkFont(weight="bold"))
        self.lbl_planilha.pack(padx=15, pady=2, anchor="w")
        self.frm_planilha = ctk.CTkFrame(self.tab_painel, fg_color="transparent")
        self.frm_planilha.pack(padx=10, fill="x")
        self.entry_planilha = ctk.CTkEntry(self.frm_planilha, textvariable=self.planilha_var, width=560)
        self.entry_planilha.pack(side="left", padx=10)
        self.btn_planilha = ctk.CTkButton(self.frm_planilha, text="Procurar...", width=100, command=self.buscar_planilha)
        self.btn_planilha.pack(side="right", padx=10)

        # =====================================================================
        # CONTEÚDO DA ABA 2: CONFIGURAÇÕES DO CONFIG.PY
        # =====================================================================
        
        # Flags Booleanas (Switches Mecânicos)
        self.switch_alterar_lote = ctk.CTkSwitch(self.tab_config, text="ALTERAR_LOTES (Mascarar Beneficiários/Carteiras)", font=ctk.CTkFont(weight="bold"))
        self.switch_alterar_lote.pack(pady=10, padx=20, anchor="w")
        if config.ALTERAR_LOTES: self.switch_alterar_lote.select()

        self.switch_enviar_ws = ctk.CTkSwitch(self.tab_config, text="ENVIAR_WS (Transmitir via protocolo SOAP para a operadora)", font=ctk.CTkFont(weight="bold"))
        self.switch_enviar_ws.pack(pady=10, padx=20, anchor="w")
        if config.ENVIAR_WS: self.switch_enviar_ws.select()

        self.switch_random_transacao = ctk.CTkSwitch(self.tab_config, text="UTILIZAR_RANDOM_TRANSACAO (Sorear IDs de lote aleatórios)", font=ctk.CTkFont(weight="bold"))
        self.switch_random_transacao.pack(pady=10, padx=20, anchor="w")
        if config.UTILIZAR_RANDOM_TRANSACAO: self.switch_random_transacao.select()

        # Inputs Textuais de Configuração de Endpoint e Rede
        self.frm_config_text = ctk.CTkFrame(self.tab_config)
        self.frm_config_text.pack(pady=10, padx=10, fill="both", expand=True)

        self.lbl_url = ctk.CTkLabel(self.frm_config_text, text="URL_OPERADORA (Endpoint):", font=ctk.CTkFont(weight="bold"))
        self.lbl_url.grid(row=0, column=0, padx=10, pady=2, sticky="w")
        self.entry_url = ctk.CTkEntry(self.frm_config_text, textvariable=self.url_var, width=660)
        self.entry_url.grid(row=1, column=0, padx=10, pady=5, columnspan=3)

        self.lbl_coluna = ctk.CTkLabel(self.frm_config_text, text="COLUNA_ALVO (Planilha):", font=ctk.CTkFont(weight="bold"))
        self.lbl_coluna.grid(row=2, column=0, padx=10, pady=2, sticky="w")
        self.entry_coluna = ctk.CTkEntry(self.frm_config_text, textvariable=self.coluna_var, width=180)
        self.entry_coluna.grid(row=3, column=0, padx=10, pady=5, sticky="w")

        self.lbl_action = ctk.CTkLabel(self.frm_config_text, text="TISS_SOAP_ACTION:", font=ctk.CTkFont(weight="bold"))
        self.lbl_action.grid(row=2, column=1, padx=10, pady=2, sticky="w")
        self.entry_action = ctk.CTkEntry(self.frm_config_text, textvariable=self.action_var, width=220)
        self.entry_action.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        self.lbl_timeout = ctk.CTkLabel(self.frm_config_text, text="TIMEOUT_REQUISICAO (ms):", font=ctk.CTkFont(weight="bold"))
        self.lbl_timeout.grid(row=2, column=2, padx=10, pady=2, sticky="w")
        self.entry_timeout = ctk.CTkEntry(self.frm_config_text, textvariable=self.timeout_var, width=180)
        self.entry_timeout.grid(row=3, column=2, padx=10, pady=5, sticky="w")

        # --- CONSOLE DE LOGS CENTRAL E BOTÃO DE DISPARO ---
        self.lbl_log = ctk.CTkLabel(self, text="Console de Execução / Logs do Sistema:", font=ctk.CTkFont(weight="bold"))
        self.lbl_log.pack(padx=20, anchor="w")
        self.txt_log = ctk.CTkTextbox(self, height=140, width=720)
        self.txt_log.pack(pady=5, padx=20)
        self.txt_log.configure(state="disabled")

        self.btn_executar = ctk.CTkButton(self, text="Iniciar Pipeline de Transmissão", font=ctk.CTkFont(size=15, weight="bold"), height=42, command=self.orquestrar_execucao)
        self.btn_executar.pack(pady=10)

    # --- MÉTODOS DE CONTROLE DE INTERFACE ---
    
    def alternar_campos_modo(self):
        """Alterna dinamicamente a exibição dos inputs dependendo da escolha do usuário."""
        if self.modo_execucao.get() == "pasta":
            self.lbl_arq_unico.grid_forget()
            self.entry_arq_unico.grid_forget()
            self.btn_arq_unico.grid_forget()
            
            self.lbl_pasta.grid(row=0, column=0, padx=10, pady=2, sticky="w")
            self.entry_pasta.grid(row=1, column=0, padx=10, pady=5)
            self.btn_pasta.grid(row=1, column=1, padx=10, pady=5)
        else:
            self.lbl_pasta.grid_forget()
            self.entry_pasta.grid_forget()
            self.btn_pasta.grid_forget()
            
            self.lbl_arq_unico.grid(row=0, column=0, padx=10, pady=2, sticky="w")
            self.entry_arq_unico.grid(row=1, column=0, padx=10, pady=5)
            self.btn_arq_unico.grid(row=1, column=1, padx=10, pady=5)

    def buscar_pasta(self):
        diretorio = filedialog.askdirectory()
        if diretorio: self.pasta_origem_var.set(diretorio)

    def buscar_arquivo_xml(self):
        arquivo = filedialog.askopenfilename(filetypes=[("Arquivos XML TISS", "*.xml")])
        if arquivo: self.arquivo_unico_var.set(arquivo)

    def buscar_planilha(self):
        arquivo = filedialog.askopenfilename(filetypes=[("Planilhas de Carteiras", "*.csv *.xlsx *.xls")])
        if arquivo: self.planilha_var.set(arquivo)

    def log(self, mensagem: str):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", mensagem + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")
        self.update_idletasks()

    # --- ENGINE DE SINCRONIZAÇÃO E OPERAÇÃO ---

    def orquestrar_execucao(self):
        # 1. SINCRONIZAÇÃO DINÂMICA: Despeja as configurações da tela direto no config.py global
        config.ALTERAR_LOTES = bool(self.switch_alterar_lote.get())
        config.ENVIAR_WS = bool(self.switch_enviar_ws.get())
        config.UTILIZAR_RANDOM_TRANSACAO = bool(self.switch_random_transacao.get())
        config.CAMINHO_PLANILHA_CARTEIRAS = self.planilha_var.get().strip()
        config.COLUNA_ALVO = self.coluna_var.get().strip() or None
        config.URL_OPERADORA = self.url_var.get().strip()
        config.SOAP_ACTION_METODO = self.action_var.get().strip()
        try:
            config.TIMEOUT_REQUISICAO = int(self.timeout_var.get().strip())
        except ValueError:
            config.TIMEOUT_REQUISICAO = 30  # Fallback seguro

        # Validação básica de caminhos
        if not os.path.exists(config.CAMINHO_PLANILHA_CARTEIRAS) and config.ALTERAR_LOTES:
            messagebox.showerror("Erro", "Planilha de carteiras não localizada.")
            return

        self.btn_executar.configure(state="disabled")
        self.log("[*] Console sincronizado. Aplicando variáveis do config.py...")

        # Redireciona saídas clássicas de print para a nossa janelaclass TerminalRedirection:
        def __init__(self, log_func):
            self.log_func = log_func

        def write(self, s):
            if s.strip():
                self.log_func(s.strip())

        def flush(self):
            pass

        sys.stdout = TerminalRedirection(self.log)

        # 2. DEFINIÇÃO DE ESCOPO: Pasta ou Arquivo Único (Requisito 1)
        lista_trabalho = []
        if self.modo_execucao.get() == "pasta":
            pasta_alvo = self.pasta_origem_var.get().strip()
            if not os.path.exists(pasta_alvo):
                messagebox.showerror("Erro", "Pasta de XMLs inválida.")
                sys.stdout = sys.stdout
                self.btn_executar.configure(state="normal")
                return

            # Filtra os arquivos ignorando retornos de execuções anteriores
            xmls = glob.glob(os.path.join(pasta_alvo, "*.xml"))
            lista_trabalho = [f for f in xmls if not os.path.basename(f).startswith("Resposta_")]
        else:
            arq_alvo = self.arquivo_unico_var.get().strip()
            if os.path.exists(arq_alvo):
                lista_trabalho.append(arq_alvo)

        if not lista_trabalho:
            self.log("[-] Nenhum arquivo XML válido foi localizado para execução.")
            sys.stdout = sys.stdout
            self.btn_executar.configure(state="normal")
            return

        # 3. PIPELINE DE EXECUÇÃO SEQUENCIAL
        for caminho_xml_origem in lista_trabalho:
            nome_arq = os.path.basename(caminho_xml_origem)
            diretorio_atual = os.path.dirname(caminho_xml_origem)
            self.log(f"\n========================================\n[→] Tracionando: {nome_arq}")

            # Define o arquivo de transição mascarado
            caminho_xml_saida = os.path.join(diretorio_atual, f"Modificado_{nome_arq}")

            # PASSO A: Alteração estrutural / Mascaramento (se ativo)
            if config.ALTERAR_LOTES:
                TissXmlService.processar_alteracao_tiss(
                    xml_origem=caminho_xml_origem,
                    xml_destino=caminho_xml_saida,
                    planilha_ref=config.CAMINHO_PLANILHA_CARTEIRAS,
                    coluna_nome=config.COLUNA_ALVO
                )
                xml_alvo_envio = caminho_xml_saida
            else:
                xml_alvo_envio = caminho_xml_origem

            # PASSO B: Envio via WebService SOAP Client (se ativo)
            if config.ENVIAR_WS:
                sucesso, resultado_ws = TissSoapClient.enviar_lote(
                    caminho_xml=xml_alvo_envio,
                    url_endpoint=config.URL_OPERADORA,
                    soap_action=config.SOAP_ACTION_METODO
                )

            # PASSO C: Gravação da Resposta individualizada (Requisito 2)
            nome_resposta = f"Resposta_{nome_arq}"
            caminho_salvamento_resposta = os.path.join(diretorio_atual, nome_resposta)
            with open(caminho_salvamento_resposta, "w", encoding="iso-8859-1") as f_res:
                f_res.write(resultado_ws)
            self.log(f"[+] Retorno da operadora gravado com sucesso em: {nome_resposta}")
        else:
            self.log("[*] Transmissão WebService (ENVIAR_WS) desmarcada nas configurações.")

        # Limpeza do lixo de transição gerado na pasta
        if os.path.exists(caminho_xml_saida):
            os.remove(caminho_xml_saida)

        # Restaura os canais de saída do sistema
        sys.stdout = sys.stdout
        self.btn_executar.configure(state="normal")
        self.log("\n[✔] Processamento concluído com sucesso!")
        messagebox.showinfo("Pipeline Concluído", "Operação executada com êxito para os arquivos selecionados!")
        
if __name__ == "__main__":
    app = TissMasterGUI()
    app.mainloop()