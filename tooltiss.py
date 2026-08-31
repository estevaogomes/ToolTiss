import ctypes
import os, glob, sys, json, customtkinter as ctk
from tkinter import filedialog, messagebox

# Mantém as pontes originais com as suas classes de negócio
import config
from services.TissXmlService import TissXmlService
from comunication.SoapClient import TissSoapClient

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
        
        self.sw_alterar = ctk.CTkSwitch(f_switches, text="ALTERAR_LOTES (Mascarar carteiras)", font=ctk.CTkFont(weight="bold"))
        self.sw_alterar.grid(row=0, column=0, padx=10, pady=4, sticky="w")
        if config.ALTERAR_LOTES: self.sw_alterar.select()

        self.sw_guias = ctk.CTkSwitch(f_switches, text="ALTERAR_GUIAS (Modificar números de guias)", font=ctk.CTkFont(weight="bold"))
        self.sw_guias.grid(row=0, column=1, padx=10, pady=4, sticky="w")
        if getattr(config, 'ALTERAR_GUIAS', True): self.sw_guias.select()

        self.sw_enviar = ctk.CTkSwitch(f_switches, text="ENVIAR_WS (Transmitir via SOAP)", font=ctk.CTkFont(weight="bold"))
        self.sw_enviar.grid(row=1, column=0, padx=10, pady=4, sticky="w")
        if config.ENVIAR_WS: self.sw_enviar.select()

        self.sw_rand = ctk.CTkSwitch(f_switches, text="UTILIZAR_RANDOM_TRANSACAO", font=ctk.CTkFont(weight="bold"))
        self.sw_rand.grid(row=1, column=1, padx=10, pady=4, sticky="w")
        if config.UTILIZAR_RANDOM_TRANSACAO: self.sw_rand.select()

        # NOVO SWITCH INDEPENDENTE: ALTERAR_TRANSACAO_LOTE solicitado
        self.sw_transacao = ctk.CTkSwitch(f_switches, text="ALTERAR_TRANSACAO_LOTE (Opção de transações)", font=ctk.CTkFont(weight="bold"))
        self.sw_transacao.grid(row=2, column=0, padx=10, pady=4, sticky="w")
        if getattr(config, 'ALTERAR_TRANSACAO_LOTE', True): self.sw_transacao.select()

        self.sw_sobrescrever = ctk.CTkSwitch(f_switches, text="SOBRESCREVER_ENTRADA (Gravar por cima do original)", font=ctk.CTkFont(weight="bold"))
        self.sw_sobrescrever.grid(row=2, column=1, padx=10, pady=4, sticky="w")
        if getattr(config, 'SOBRESCREVER_ENTRADA', False): self.sw_sobrescrever.select()

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

        # Console Geral de Logs
        ctk.CTkLabel(self, text="Console de Logs em Tempo Real:", font=ctk.CTkFont(weight="bold")).pack(padx=20, anchor="w", pady=(5,0))
        self.txt_log = ctk.CTkTextbox(self, height=150)
        self.txt_log.pack(pady=5, padx=20, fill="both", expand=True)
        self.txt_log.configure(state="disabled")

        # Container inferior para alinhar os botões
        f_botoes = ctk.CTkFrame(self, fg_color="transparent")
        f_botoes.pack(pady=10, padx=20, fill="x")
        
        self.btn_go = ctk.CTkButton(f_botoes, text="Iniciar Pipeline TISS", font=ctk.CTkFont(size=14, weight="bold"), height=40, command=self.executar)
        self.btn_go.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_help = ctk.CTkButton(f_botoes, text="❓ Manual", font=ctk.CTkFont(size=14), width=100, height=40, fg_color="#555555", hover_color="#444444", command=self.abrir_manual)
        self.btn_help.pack(side="right")
        self.carregar_configuracoes_locais()
        # Vincula o evento de fechamento da janela para salvar os dados
        self.protocol("WM_DELETE_WINDOW", self.salvar_configuracoes_locais)

    # --- PERSISTÊNCIA DE DADOS (NOVO REQUIREMENTO) ---
    def salvar_configuracoes_locais(self):
        """Coleta o estado atual dos inputs da tela e salva em um arquivo JSON local."""
        dados_usuario = {"modo_exec": self.modo_exec.get(),"p_origem": self.p_origem.get(),"arq_unico": self.arq_unico.get(),"planilha": self.planilha.get(),"coluna": self.coluna.get(),"url_ws": self.url_ws.get(),"action": self.action.get(),"timeout": self.timeout.get(),"p_resposta": self.p_resposta.get(),"sw_alterar": self.sw_alterar.get(),"sw_guias": self.sw_guias.get(),"sw_enviar": self.sw_enviar.get(),"sw_rand": self.sw_rand.get(),"sw_transacao": self.sw_transacao.get(),"sw_sobrescrever": self.sw_sobrescrever.get()}
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
            ajustar_switch(self.sw_guias, "sw_guias")
            ajustar_switch(self.sw_enviar, "sw_enviar")
            ajustar_switch(self.sw_rand, "sw_rand")
            ajustar_switch(self.sw_transacao, "sw_transacao")
            ajustar_switch(self.sw_sobrescrever, "sw_sobrescrever")
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
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", text + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")
        self.update_idletasks()

    def executar(self):
        # Sincroniza dinamicamente as escolhas do painel visual com a memória do config.py
        config.ALTERAR_LOTES = bool(self.sw_alterar.get())
        config.ALTERAR_TRANSACAO_LOTE = bool(self.sw_transacao.get())
        config.ALTERAR_GUIAS = bool(self.sw_guias.get())
        config.ENVIAR_WS = bool(self.sw_enviar.get())
        config.UTILIZAR_RANDOM_TRANSACAO = bool(self.sw_rand.get())
        config.SOBRESCREVER_ENTRADA = bool(self.sw_sobrescrever.get())
        config.CAMINHO_PLANILHA_CARTEIRAS = self.planilha.get().strip()
        config.COLUNA_ALVO = self.coluna.get().strip() or None
        config.URL_OPERADORA = self.url_ws.get().strip()
        config.SOAP_ACTION_METODO = self.action.get().strip()
        config.PASTA_RESPOSTA = self.p_resposta.get().strip()
        try:
            config.TIMEOUT_REQUISICAO = int(self.timeout.get().strip())
        except:
            config.TIMEOUT_REQUISICAO = 30

        if config.ALTERAR_LOTES and not os.path.exists(config.CAMINHO_PLANILHA_CARTEIRAS):
            messagebox.showerror("Erro de Dependência", "A planilha de carteiras especificada não foi encontrada.")
            return

        self.btn_go.configure(state="disabled")
        self.log("[*] Console visual ativo. Vinculando variáveis ao config.py...")

        class Redirection:
            def __init__(self, lf):
                self.lf = lf

            def write(self, s):
                if s.strip():
                    self.lf(s.strip())

            def flush(self):
                pass

        sys.stdout = Redirection(self.log)
        lt = []

        if self.modo_exec.get() == "pasta":
            pa = self.p_origem.get().strip()
            if not os.path.exists(pa):
                messagebox.showerror("Erro", "Pasta de origem inválida.")
                sys.stdout = sys.stdout
                self.btn_go.configure(state="normal")
                return
            xmls = glob.glob(os.path.join(pa, "*.xml"))
            lt = [f for f in xmls if not os.path.basename(f).startswith("Resposta_")]
        else:
            f_target = self.arq_unico.get().strip()
            if os.path.exists(f_target):
                lt.append(f_target)

        if not lt:
            self.log("[-] Nenhum arquivo XML localizado.")
            sys.stdout = sys.stdout
            self.btn_go.configure(state="normal")
            return

        for orig in lt:
            name = os.path.basename(orig)
            dt = os.path.dirname(orig)
            self.log(f"\n[*] Processando arquivo: {name}")

            # Gerenciamento lógico do arquivo modificado conforme a decisão de sobrescrever
            if config.SOBRESCREVER_ENTRADA:
                out = orig
            else:
                out = os.path.join(dt, f"Modificado_{name}")

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

            # Remove o arquivo temporário apenas se a opção de sobrescrever estiver desativada
            if not config.SOBRESCREVER_ENTRADA and os.path.exists(out):
                os.remove(out)

        sys.stdout = sys.stdout
        self.btn_go.configure(state="normal")
        messagebox.showinfo("Sucesso", "Pipeline concluído com sucesso!")


if __name__ == "__main__":
    app = TissMasterGUI()
    app.mainloop()