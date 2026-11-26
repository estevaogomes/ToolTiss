import ctypes
import os, glob, sys, json, shutil, threading, queue, concurrent.futures, customtkinter as ctk
from tkinter import filedialog, messagebox

# Mantém as pontes originais com as suas classes de negócio
import config
from services.TissXmlService import TissXmlService
from comunication.SoapClient import TissSoapClient
from services.TissResponseParser import TissResponseParser

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")
ARQUIVO_SETTINGS = "config_usuario.json"

class TissMasterGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ToolTiss")
        
        self.geometry("760x740")
        self.resizable(True, True) 

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1) 
        try:
            app_id = "mycompany.tooltiss.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except:
            pass

        nome_icone = "bateria.ico"
        if hasattr(sys, '_MEIPASS'):
            caminho_icone = os.path.join(sys._MEIPASS, nome_icone)
        else:
            caminho_icone = nome_icone

        # 3. Aplica o ícone na janela (Barra de título e Barra de tarefas)
        if os.path.exists(caminho_icone):
            self.wm_iconbitmap(caminho_icone)
        # Injeta dinamicamente as novas propriedades de controle de negócio
        #if not hasattr(config, 'ALTERAR_GUIAS'): config.ALTERAR_GUIAS = True
        #if not hasattr(config, 'ALTERAR_TRANSACAO_LOTE'): config.ALTERAR_TRANSACAO_LOTE = True
        #if not hasattr(config, 'SOBRESCREVER_ENTRADA'): config.SOBRESCREVER_ENTRADA = False
        #if not hasattr(config, 'PASTA_RESPOSTA'): config.PASTA_RESPOSTA = ""

        # Fila thread-safe para log assíncrono e flag de cancelamento cooperativo
        self._log_queue = queue.Queue()
        self._cancelar_envio = False
        self._worker_thread = None

        # Variáveis de Estado linkadas aos campos textuais e seletores
        self.modo_exec = ctk.StringVar(value="arquivo")
        self.p_origem = ctk.StringVar(value=os.getcwd())
        self.arq_unico = ctk.StringVar(value=config.CAMINHO_XML_ENTRADA)
        self.planilha = ctk.StringVar(value=config.CAMINHO_PLANILHA_CARTEIRAS)
        self.coluna = ctk.StringVar(value=config.COLUNA_ALVO if config.COLUNA_ALVO else "")
        self.url_ws = ctk.StringVar(value=config.URL_OPERADORA)
        self.action = ctk.StringVar(value=config.SOAP_ACTION_METODO)
        self.timeout = ctk.StringVar(value=str(config.TIMEOUT_REQUISICAO))
        self.p_resposta = ctk.StringVar(value=config.PASTA_RESPOSTA)

        # Cabeçalho Principal
        ctk.CTkLabel(self, text="Orquestrador TISS WebService", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        # Abas do Painel - fill="both" e expand=True para ocupar o espaço responsivo
        self.tabs = ctk.CTkTabview(self, width=720, height=410)
        self.tabs.pack(pady=5, padx=20, fill="both", expand=True)
        self.t_envio = self.tabs.add("Painel de Envio")
        self.t_config = self.tabs.add("Configurações Avançadas (config.py)")

        # Configura as abas internas para expanderem seus conteúdos
        self.t_envio.columnconfigure(0, weight=1)
        self.t_config.columnconfigure(0, weight=1)

        # --- CONTEÚDO DA ABA 1: OPERAÇÕES ---
        f_modo = ctk.CTkFrame(self.t_envio)
        f_modo.pack(pady=5, padx=10, fill="x")
        ctk.CTkLabel(f_modo, text="Escopo da execução:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, sticky="w")
        ctk.CTkRadioButton(f_modo, text="Processar pasta de XMLs", variable=self.modo_exec, value="pasta", command=self.mudar_modo).grid(row=1, column=0, padx=20, pady=5, sticky="w")
        ctk.CTkRadioButton(f_modo, text="Processar XML único", variable=self.modo_exec, value="arquivo", command=self.mudar_modo).grid(row=1, column=1, padx=20, pady=5, sticky="w")

        self.f_origem = ctk.CTkFrame(self.t_envio)
        self.f_origem.pack(pady=5, padx=10, fill="x")
        self.f_origem.columnconfigure(0, weight=1)

        self.lbl_p = ctk.CTkLabel(self.f_origem, text="Pasta de Origem dos XMLs:", font=ctk.CTkFont(weight="bold"))
        self.ent_p = ctk.CTkEntry(self.f_origem, textvariable=self.p_origem)
        self.btn_p = ctk.CTkButton(self.f_origem, text="Procurar...", width=110, command=lambda: self.p_origem.set(filedialog.askdirectory() or self.p_origem.get()))

        self.lbl_f = ctk.CTkLabel(self.f_origem, text="Arquivo XML Único de Entrada:", font=ctk.CTkFont(weight="bold"))
        self.ent_f = ctk.CTkEntry(self.f_origem, textvariable=self.arq_unico)
        self.btn_f = ctk.CTkButton(self.f_origem, text="Procurar...", width=110, command=lambda: self.arq_unico.set(filedialog.askopenfilename(filetypes=[("XML", "*.xml")]) or self.arq_unico.get()))

        # Pasta de Saída Customizada
        ctk.CTkLabel(self.t_envio, text="Pasta de Saída (Onde salvar os retornos - Deixe em branco para a mesma pasta):", font=ctk.CTkFont(weight="bold")).pack(padx=15, anchor="w", pady=(8,0))
        f_resp = ctk.CTkFrame(self.t_envio, fg_color="transparent")
        f_resp.pack(padx=10, fill="x", pady=2)
        ctk.CTkEntry(f_resp, textvariable=self.p_resposta).pack(side="left", padx=10, fill="x", expand=True)
        ctk.CTkButton(f_resp, text="Procurar...", width=110, command=lambda: self.p_resposta.set(filedialog.askdirectory() or self.p_resposta.get())).pack(side="right", padx=10)

        # Planilha Base
        ctk.CTkLabel(self.t_envio, text="Planilha de Carteiras de Referência (CSV/Excel):", font=ctk.CTkFont(weight="bold")).pack(padx=15, anchor="w", pady=(8,0))
        f_plan = ctk.CTkFrame(self.t_envio, fg_color="transparent")
        f_plan.pack(padx=10, fill="x", pady=2)
        ctk.CTkEntry(f_plan, textvariable=self.planilha).pack(side="left", padx=10, fill="x", expand=True)
        ctk.CTkButton(f_plan, text="Procurar...", width=110, command=lambda: self.planilha.set(filedialog.askopenfilename(filetypes=[("Dados", "*.csv *.xlsx *.xls")]) or self.planilha.get())).pack(side="right", padx=10)

        self.mudar_modo()

        # --- CONTEÚDO DA ABA 2: CHAVES INTERNAS DO CONFIG.PY ---
        f_switches = ctk.CTkFrame(self.t_config, fg_color="transparent")
        f_switches.pack(pady=5, padx=10, fill="x")
        
        self.sw_alterar = ctk.CTkSwitch(f_switches, text="ALTERAR_LOTES (Processar lote)", font=ctk.CTkFont(weight="bold"))
        self.sw_alterar.grid(row=0, column=0, padx=10, pady=4, sticky="w")
        if config.ALTERAR_LOTES: self.sw_alterar.select()

        self.sw_carteiras = ctk.CTkSwitch(f_switches, text="ALTERAR_CARTEIRAS (Mascarar beneficiários)", font=ctk.CTkFont(weight="bold"))
        self.sw_carteiras.grid(row=0, column=1, padx=10, pady=4, sticky="w")
        if getattr(config, 'ALTERAR_CARTEIRAS', True): self.sw_carteiras.select()

        self.sw_guias = ctk.CTkSwitch(f_switches, text="ALTERAR_GUIAS (Modificar números de guias)", font=ctk.CTkFont(weight="bold"))
        self.sw_guias.grid(row=1, column=0, padx=10, pady=4, sticky="w")
        if getattr(config, 'ALTERAR_GUIAS', True): self.sw_guias.select()

        self.sw_enviar = ctk.CTkSwitch(f_switches, text="ENVIAR_WS (Transmitir via SOAP)", font=ctk.CTkFont(weight="bold"))
        self.sw_enviar.grid(row=1, column=1, padx=10, pady=4, sticky="w")
        if config.ENVIAR_WS: self.sw_enviar.select()

        self.sw_rand = ctk.CTkSwitch(f_switches, text="UTILIZAR_RANDOM_TRANSACAO", font=ctk.CTkFont(weight="bold"))
        self.sw_rand.grid(row=2, column=0, padx=10, pady=4, sticky="w")
        if config.UTILIZAR_RANDOM_TRANSACAO: self.sw_rand.select()

        # NOVO SWITCH INDEPENDENTE: ALTERAR_TRANSACAO_LOTE solicitado
        self.sw_transacao = ctk.CTkSwitch(f_switches, text="ALTERAR_TRANSACAO_LOTE (Opção de transações)", font=ctk.CTkFont(weight="bold"))
        self.sw_transacao.grid(row=2, column=1, padx=10, pady=4, sticky="w")
        if getattr(config, 'ALTERAR_TRANSACAO_LOTE', True): self.sw_transacao.select()

        self.sw_sobrescrever = ctk.CTkSwitch(f_switches, text="SOBRESCREVER_ENTRADA (Gravar por cima do original)", font=ctk.CTkFont(weight="bold"))
        self.sw_sobrescrever.grid(row=3, column=0, padx=10, pady=4, sticky="w")
        if getattr(config, 'SOBRESCREVER_ENTRADA', False): self.sw_sobrescrever.select()

        self.sw_mover_enviados = ctk.CTkSwitch(f_switches, text="MOVER_ARQUIVOS_ENVIADOS (Mover para pasta Enviados após sucesso)", font=ctk.CTkFont(weight="bold"))
        self.sw_mover_enviados.grid(row=3, column=1, padx=10, pady=4, sticky="w")
        if getattr(config, 'MOVER_ARQUIVOS_ENVIADOS', True): self.sw_mover_enviados.select()

        f_txt = ctk.CTkFrame(self.t_config)
        f_txt.pack(pady=5, padx=10, fill="both", expand=True)
        f_txt.columnconfigure(0, weight=1)
        f_txt.columnconfigure(1, weight=1)
        f_txt.columnconfigure(2, weight=1)

        ctk.CTkLabel(f_txt, text="URL_OPERADORA (WebService Endpoint):", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, sticky="w")
        ctk.CTkEntry(f_txt, textvariable=self.url_ws).grid(row=1, column=0, padx=10, pady=2, columnspan=3, sticky="ew")
        
        ctk.CTkLabel(f_txt, text="COLUNA_ALVO:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=10, sticky="w")
        ctk.CTkEntry(f_txt, textvariable=self.coluna).grid(row=3, column=0, padx=10, pady=2, sticky="ew")
        ctk.CTkLabel(f_txt, text="TISS_SOAP_ACTION:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=1, padx=10, sticky="w")
        ctk.CTkEntry(f_txt, textvariable=self.action).grid(row=3, column=1, padx=10, pady=2, sticky="ew")
        ctk.CTkLabel(f_txt, text="TIMEOUT_REQUISICAO:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=2, padx=10, sticky="w")
        ctk.CTkEntry(f_txt, textvariable=self.timeout).grid(row=3, column=2, padx=10, pady=2, sticky="ew")

        # --- ENDPOINTS POR VERSÃO TISS ---
        f_versoes = ctk.CTkFrame(self.t_config)
        f_versoes.pack(pady=(10, 5), padx=10, fill="x")
        ctk.CTkLabel(f_versoes, text="Endpoints por Versão TISS (detectada automaticamente antes do envio):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=(5, 2))

        self._vars_urls_versao = {}
        urls_mapeadas = getattr(config, 'URLS_POR_VERSAO_TISS', {})
        for idx, (versao, url_padrao) in enumerate(sorted(urls_mapeadas.items())):
            var_url = ctk.StringVar(value=url_padrao)
            self._vars_urls_versao[versao] = var_url
            row_frame = ctk.CTkFrame(f_versoes, fg_color="transparent")
            row_frame.pack(fill="x", padx=5, pady=1)
            ctk.CTkLabel(row_frame, text=f"TISS {versao}:", width=90, anchor="e").pack(side="left", padx=(0, 5))
            ctk.CTkEntry(row_frame, textvariable=var_url).pack(side="left", fill="x", expand=True)

        # Console Geral de Logs
        ctk.CTkLabel(self, text="Console de Logs em Tempo Real:", font=ctk.CTkFont(weight="bold")).pack(padx=20, anchor="w", pady=(5,0))
        self.txt_log = ctk.CTkTextbox(self, height=150)
        self.txt_log.pack(pady=5, padx=20, fill="both", expand=True)
        self.txt_log.configure(state="disabled")

        # Container inferior para alinhar os botões
        f_botoes = ctk.CTkFrame(self, fg_color="transparent")
        f_botoes.pack(pady=10, padx=20, fill="x")
        
        self._cancelar_envio = False

        self.btn_go = ctk.CTkButton(f_botoes, text="Iniciar Pipeline TISS", font=ctk.CTkFont(size=14, weight="bold"), height=40, command=self.executar)
        self.btn_go.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_cancelar = ctk.CTkButton(f_botoes, text="Cancelar", font=ctk.CTkFont(size=14), width=100, height=40, fg_color="#d9534f", hover_color="#c9302c", command=self.cancelar_envio, state="disabled")
        self.btn_cancelar.pack(side="left", padx=(0, 10))

        self.btn_help = ctk.CTkButton(f_botoes, text="❓ Manual", font=ctk.CTkFont(size=14), width=100, height=40, fg_color="#555555", hover_color="#444444", command=self.abrir_manual)
        self.btn_help.pack(side="right")
        self.carregar_configuracoes_locais()
        # Vincula o evento de fechamento da janela para salvar os dados
        self.protocol("WM_DELETE_WINDOW", self.salvar_configuracoes_locais)

    # --- PERSISTÊNCIA DE DADOS (NOVO REQUIREMENTO) ---
    def salvar_configuracoes_locais(self):
        """Coleta o estado atual dos inputs da tela e salva em um arquivo JSON local."""
        urls_versao_salvar = {v: var.get() for v, var in self._vars_urls_versao.items()}
        dados_usuario = {"modo_exec": self.modo_exec.get(),"p_origem": self.p_origem.get(),"arq_unico": self.arq_unico.get(),"planilha": self.planilha.get(),"coluna": self.coluna.get(),"url_ws": self.url_ws.get(),"action": self.action.get(),"timeout": self.timeout.get(),"p_resposta": self.p_resposta.get(),"sw_alterar": self.sw_alterar.get(),"sw_carteiras": self.sw_carteiras.get(),"sw_guias": self.sw_guias.get(),"sw_enviar": self.sw_enviar.get(),"sw_rand": self.sw_rand.get(),"sw_transacao": self.sw_transacao.get(),"sw_sobrescrever": self.sw_sobrescrever.get(),"sw_mover_enviados": self.sw_mover_enviados.get(),"urls_por_versao_tiss": urls_versao_salvar}
        try:
            with open(ARQUIVO_SETTINGS, "w", encoding="utf-8") as f:
                json.dump(dados_usuario, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[-] Erro ao salvar arquivo de persistência: {e}")
        # Fecha a aplicação definitivamente
        self.destroy()

    def carregar_configuracoes_locais(self):
        """Busca se o arquivo JSON existe na pasta e popula os elementos da tela."""
        if not os.path.exists(ARQUIVO_SETTINGS):
            return
        try:
            with open(ARQUIVO_SETTINGS, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # Atualiza os inputs textuais
            if "modo_exec" in cfg:
                self.modo_exec.set(cfg["modo_exec"])
            if "p_origem" in cfg:
                self.p_origem.set(cfg["p_origem"])
            if "arq_unico" in cfg:
                self.arq_unico.set(cfg["arq_unico"])
            if "planilha" in cfg:
                self.planilha.set(cfg["planilha"])
            if "coluna" in cfg:
                self.coluna.set(cfg["coluna"])
            if "url_ws" in cfg:
                self.url_ws.set(cfg["url_ws"])
            if "action" in cfg:
                self.action.set(cfg["action"])
            if "timeout" in cfg:
                self.timeout.set(cfg["timeout"])
            if "p_resposta" in cfg:
                self.p_resposta.set(cfg["p_resposta"])
            # Atualiza os Switches (Liga/Desliga)
            def ajustar_switch(componente, chave):
                if cfg.get(chave) == 1:
                    componente.select()
                else:
                    componente.deselect()
            ajustar_switch(self.sw_alterar, "sw_alterar")
            ajustar_switch(self.sw_carteiras, "sw_carteiras")
            ajustar_switch(self.sw_guias, "sw_guias")
            ajustar_switch(self.sw_enviar, "sw_enviar")
            ajustar_switch(self.sw_rand, "sw_rand")
            ajustar_switch(self.sw_transacao, "sw_transacao")
            ajustar_switch(self.sw_sobrescrever, "sw_sobrescrever")
            ajustar_switch(self.sw_mover_enviados, "sw_mover_enviados")
            # Restaura endpoints por versão TISS salvos anteriormente
            urls_salvas = cfg.get("urls_por_versao_tiss", {})
            for versao, var_url in self._vars_urls_versao.items():
                if versao in urls_salvas:
                    var_url.set(urls_salvas[versao])
            # Redesenha a tela conforme o modo restaurado (pasta ou arquivo)
            self.mudar_modo()
        except Exception as e:
            print(f"[-] Erro ao ler arquivo de persistência: {e}")


    def abrir_manual(self):
        """Abre o manual embutido de forma compatível com o PyInstaller."""
        nome_pdf = "manual.pdf"
        
        # O PyInstaller descompacta os arquivos embutidos na pasta temporária sys._MEIPASS
        if hasattr(sys, '_MEIPASS'):
            caminho_pdf = os.path.join(sys._MEIPASS, nome_pdf)
        else:
            caminho_pdf = nome_pdf

        if os.path.exists(caminho_pdf):
            os.startfile(caminho_pdf) if hasattr(os, 'startfile') else os.system(f'xdg-open "{caminho_pdf}"')
            self.log("[*] Abrindo o manual do usuário embutido em formato PDF...")
        else:
            messagebox.showwarning("Arquivo Ausente", "O manual embutido não foi localizado.")


    def mudar_modo(self):
        if self.modo_exec.get() == "pasta":
            self.lbl_f.grid_forget(); self.ent_f.grid_forget(); self.btn_f.grid_forget()
            self.lbl_p.grid(row=0, column=0, padx=10, sticky="w")
            self.ent_p.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
            self.btn_p.grid(row=1, column=1, padx=10, pady=5)
        else:
            self.lbl_p.grid_forget(); self.ent_p.grid_forget(); self.btn_p.grid_forget()
            self.lbl_f.grid(row=0, column=0, padx=10, sticky="w")
            self.ent_f.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
            self.btn_f.grid(row=1, column=1, padx=10, pady=5)

    def log(self, text):
        """Enfileira mensagem de log para exibição assíncrona na main thread.
        Thread-safe: pode ser chamada de qualquer thread sem bloquear a GUI."""
        self._log_queue.put(text)

    def _drenar_fila_log(self):
        """Drena mensagens da fila e atualiza o widget de log na main thread.
        Reagenda automaticamente via after() para manter a GUI responsiva."""
        try:
            while True:
                text = self._log_queue.get_nowait()
                self.txt_log.configure(state="normal")
                self.txt_log.insert("end", text + "\n")
                self.txt_log.see("end")
                self.txt_log.configure(state="disabled")
        except queue.Empty:
            pass
        # Reagenda SEMPRE enquanto o worker orquestrador estiver vivo.
        # O pool de threads roda DENTRO do _worker_thread, então verificar
        # apenas _pool_active falha quando as threads internas produzem log
        # mas a fila está momentaneamente vazia entre mensagens.
        # A drenagem contínua (50ms) garante atualização em tempo real
        # mesmo com muitos arquivos e threads paralelas.
        if self._worker_thread is not None and self._worker_thread.is_alive():
            self.after(50, self._drenar_fila_log)
        elif not self._log_queue.empty():
            # Drena mensagens residuais após término do worker
            self.after(50, self._drenar_fila_log)

    def cancelar_envio(self):
        self._cancelar_envio = True
        self.log("[!] Cancelamento solicitado. Aguardando término da operação atual...")
        self.btn_cancelar.configure(state="disabled")

    def executar(self):
        """Valida inputs na main thread e delega o pipeline pesado a uma thread worker."""
        self._cancelar_envio = False
        self.btn_cancelar.configure(state="normal")
        # Sincroniza dinamicamente as escolhas do painel visual com a memória do config.py
        config.ALTERAR_LOTES = bool(self.sw_alterar.get())
        config.ALTERAR_CARTEIRAS = bool(self.sw_carteiras.get())
        config.ALTERAR_TRANSACAO_LOTE = bool(self.sw_transacao.get())
        config.ALTERAR_GUIAS = bool(self.sw_guias.get())
        config.ENVIAR_WS = bool(self.sw_enviar.get())
        config.UTILIZAR_RANDOM_TRANSACAO = bool(self.sw_rand.get())
        config.SOBRESCREVER_ENTRADA = bool(self.sw_sobrescrever.get())
        config.MOVER_ARQUIVOS_ENVIADOS = bool(self.sw_mover_enviados.get())
        config.CAMINHO_PLANILHA_CARTEIRAS = self.planilha.get().strip()
        config.COLUNA_ALVO = self.coluna.get().strip() or None
        config.URL_OPERADORA = self.url_ws.get().strip()
        # Sincroniza endpoints por versão TISS editados na GUI com o config em memória
        for versao, var_url in self._vars_urls_versao.items():
            config.URLS_POR_VERSAO_TISS[versao] = var_url.get().strip()
        config.SOAP_ACTION_METODO = self.action.get().strip()
        config.PASTA_RESPOSTA = self.p_resposta.get().strip()
        try:
            config.TIMEOUT_REQUISICAO = int(self.timeout.get().strip())
        except:
            config.TIMEOUT_REQUISICAO = 30

        if config.ALTERAR_CARTEIRAS and not os.path.exists(config.CAMINHO_PLANILHA_CARTEIRAS):
            messagebox.showerror("Erro de Dependência", "A planilha de carteiras especificada não foi encontrada.")
            return

        # Captura lista de arquivos ANTES de iniciar a thread (acesso seguro à GUI)
        modo = self.modo_exec.get()
        p_origem = self.p_origem.get().strip()
        arq_unico = self.arq_unico.get().strip()

        if modo == "pasta":
            if not os.path.exists(p_origem):
                messagebox.showerror("Erro", "Pasta de origem inválida.")
                return
            xmls = glob.glob(os.path.join(p_origem, "*.xml"))
            lista_arquivos = [f for f in xmls if not os.path.basename(f).startswith("Resposta_")]
        else:
            lista_arquivos = [arq_unico] if os.path.exists(arq_unico) else []

        if not lista_arquivos:
            messagebox.showwarning("Aviso", "Nenhum arquivo XML localizado.")
            return

        self.btn_go.configure(state="disabled")
        self.log("[*] Pipeline iniciado em segundo plano. GUI permanece responsiva.")

        # Inicia drenagem assíncrona do log
        self._drenar_fila_log()

        # Redireciona stdout para a fila de log (thread-safe)
        class QueueRedirection:
            def __init__(self, q):
                self.q = q
            def write(self, s):
                if s.strip():
                    self.q.put(s.strip())
            def flush(self):
                pass

        sys.stdout = QueueRedirection(self._log_queue)

        # Lança thread worker com todo o contexto necessário
        self._pool_active = True
        self._worker_thread = threading.Thread(
            target=self._pipeline_worker,
            args=(lista_arquivos,),
            daemon=True
        )
        self._worker_thread.start()

    def _processar_arquivo(self, orig):
        """Processa e envia um único arquivo. Thread-safe: usa apenas self.log() e config."""
        if self._cancelar_envio:
            return None

        name = os.path.basename(orig)
        dt = os.path.dirname(orig)
        self.log(f"\n[*] Processando arquivo: {name}")

        # Gerenciamento lógico do arquivo modificado conforme a decisão de sobrescrever
        if config.SOBRESCREVER_ENTRADA:
            out = orig
        else:
            out = os.path.join(dt, f"Modificado_{name}")

        try:
            if config.ALTERAR_LOTES:
                TissXmlService.processar_alteracao_tiss(orig, out, config.CAMINHO_PLANILHA_CARTEIRAS, config.COLUNA_ALVO)
                target_envio = out
            else:
                target_envio = orig

            if config.ENVIAR_WS:
                sucesso, resultado = TissSoapClient.enviar_lote(target_envio, config.URL_OPERADORA, config.SOAP_ACTION_METODO)

                pasta_final_resposta = config.PASTA_RESPOSTA if config.PASTA_RESPOSTA else dt
                nome_res = f"Resposta_{name}"
                caminho_resposta = os.path.join(pasta_final_resposta, nome_res)

                with open(caminho_resposta, "w", encoding="iso-8859-1") as fr:
                    fr.write(resultado)
                self.log(f"[+] Retorno da operadora gravado com sucesso em: {caminho_resposta}")

                # Parse da resposta e feedback de conteúdo.
                # IMPORTANTE: sempre tenta o parse, mesmo quando sucesso=False,
                # pois respostas de erro (texto puro ou XML com glosa) contêm
                # informações críticas que devem ser registradas no relatório CSV.
                parse_result = TissResponseParser.parse(resultado)

                if parse_result:
                    protocolo = parse_result.get("protocolo", "N/A")
                    situacao = parse_result.get("situacao_comunicacao", "N/A")
                    guias = parse_result.get("guias", [])
                    self.log(f"    Protocolo: {protocolo} | Situação: {situacao} | Guias: {len(guias)}")
                    for guia in guias:
                        status = guia.get("status", "desconhecido")
                        num_guia = guia.get("numero_guia_prestador", "?")
                        motivo = guia.get("motivo") or ""
                        icone = "✅" if status in ("aceito", "processado") else "❌"
                        linha = f"    {icone} Guia {num_guia}: {status}"
                        if motivo:
                            linha += f" — {motivo}"
                        self.log(linha)
                else:
                    self.log(f"    [!] Não foi possível extrair dados estruturados da resposta.")

                # Move arquivo enviado com sucesso para pasta "Enviados" (se habilitado)
                if config.MOVER_ARQUIVOS_ENVIADOS and sucesso:
                    try:
                        pasta_enviados = os.path.join(dt, config.NOME_PASTA_ENVIADOS)
                        os.makedirs(pasta_enviados, exist_ok=True)
                        arquivo_para_mover = target_envio
                        destino = os.path.join(pasta_enviados, os.path.basename(arquivo_para_mover))
                        if os.path.exists(destino):
                            base_nome, ext = os.path.splitext(os.path.basename(arquivo_para_mover))
                            contador = 1
                            while os.path.exists(destino):
                                destino = os.path.join(pasta_enviados, f"{base_nome}_{contador}{ext}")
                                contador += 1
                        shutil.move(arquivo_para_mover, destino)
                        self.log(f"[+] Arquivo movido para: {destino}")
                        target_envio = destino
                    except Exception as e_move:
                        self.log(f"[!] Falha ao mover arquivo para Enviados: {e_move}")

                # Remove o arquivo temporário apenas se a opção de sobrescrever estiver desativada
                # e o arquivo não tiver sido movido para a pasta Enviados
                if not config.SOBRESCREVER_ENTRADA and os.path.exists(out):
                    if out != target_envio or not config.MOVER_ARQUIVOS_ENVIADOS:
                        os.remove(out)

                self.log(f"[✓] Arquivo {name} concluído com sucesso.")
                return {"arquivo": name, "parse_result": parse_result}
            else:
                # Sem envio WS: apenas processa e limpa temporário
                if not config.SOBRESCREVER_ENTRADA and os.path.exists(out):
                    os.remove(out)
                self.log(f"[✓] Arquivo {name} processado (sem envio WS).")
                return None

        except Exception as e:
            self.log(f"[-] Erro ao processar {name}: {e}")
            return None

    def _pipeline_worker(self, lista_arquivos):
        """Orquestra múltiplas threads de processamento/envio paralelo via ThreadPoolExecutor."""
        max_threads = getattr(config, 'MAX_THREADS_ENVIO', 4)
        total = len(lista_arquivos)
        self.log(f"[*] Iniciando pool de {max_threads} threads para {total} arquivo(s).")

        resultados_relatorio = []
        lock_resultados = threading.Lock()

        def worker_wrapper(orig):
            result = self._processar_arquivo(orig)
            if result is not None:
                with lock_resultados:
                    resultados_relatorio.append(result)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = {executor.submit(worker_wrapper, arq): arq for arq in lista_arquivos}
                for future in concurrent.futures.as_completed(futures):
                    if self._cancelar_envio:
                        self.log("[!] Cancelamento solicitado. Aguardando threads ativas...")
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    try:
                        future.result()
                    except Exception as e:
                        arq = futures[future]
                        self.log(f"[-] Exceção não capturada em {os.path.basename(arq)}: {e}")

            # Gerar relatório CSV consolidado se houve envios
            if resultados_relatorio:
                pasta_rel = config.PASTA_RESPOSTA if config.PASTA_RESPOSTA else os.getcwd()
                caminho_csv = os.path.join(pasta_rel, "relatorio_envio_tiss.csv")
                try:
                    TissResponseParser.gerar_relatorio_csv(resultados_relatorio, caminho_csv)
                    self.log(f"\n[+] Relatório consolidado gerado: {caminho_csv}")
                except Exception as e:
                    self.log(f"\n[-] Erro ao gerar relatório CSV: {e}")

            if not self._cancelar_envio:
                self.log(f"\n[+] Pipeline concluído: {len(resultados_relatorio)} de {total} arquivo(s) processado(s).")
            else:
                self.log("\n[!] Pipeline interrompido por cancelamento do usuário.")

        except Exception as e:
            self.log(f"\n[-] Erro inesperado no pipeline: {e}")
        finally:
            sys.stdout = sys.__stdout__
            self.after(0, self._on_pipeline_finished)

    def _on_pipeline_finished(self):
        """Callback executado na main thread após término da thread worker."""
        self.btn_go.configure(state="normal")
        self.btn_cancelar.configure(state="disabled")
        self._worker_thread = None
        self._pool_active = False
        # Drena mensagens residuais da fila
        self._drenar_fila_log()


if __name__ == "__main__":
    app = TissMasterGUI()
    app.mainloop()