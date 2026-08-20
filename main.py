import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os, sys, json, subprocess, threading

DEFAULT_DIR = r"C:\Users\brice\Documents\03_Programmes\python"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "launcher_config.json")

BG_PAGE    = "#F5F4F1"
BG_SURFACE = "#FFFFFF"
BG_MUTED   = "#F0EFE9"
BG_ENTRY   = "#F8F7F4"
BORDER     = "#D3D1C7"
BORDER_MED = "#B4B2A9"
ACCENT_V   = "#534AB7"
ACCENT_V_L = "#EEEDFE"
ACCENT_V_D = "#3C3489"
ACCENT_G   = "#0F6E56"
ACCENT_G_L = "#E1F5EE"
ACCENT_G_D = "#085041"
ACCENT_C   = "#993C1D"
ACCENT_C_L = "#FAECE7"
TEXT_PRI   = "#2C2C2A"
TEXT_SEC   = "#5F5E5A"
TEXT_HINT  = "#888780"
CARD_ACCENTS = ["#534AB7", "#0F6E56", "#D85A30", "#185FA5", "#BA7517", "#993556"]

FONT_TITLE = ("Segoe UI", 14, "bold")
FONT_HEAD  = ("Segoe UI", 11, "bold")
FONT_BODY  = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_MONO  = ("Consolas", 9)

PARAMS_EXAMPLE = {
    "description": "Description courte du script",
    "params": [
        {"name": "input_file", "type": "file",   "label": "Fichier entree",   "description": "Fichier a traiter",         "required": True,  "default": ""},
        {"name": "output_dir", "type": "dir",    "label": "Dossier sortie",   "description": "Ou enregistrer les result", "required": False, "default": ""},
        {"name": "mode",       "type": "choice", "label": "Mode",             "description": "Algorithme a utiliser",      "required": True,  "default": "rapide", "choices": ["rapide", "precis", "complet"]},
        {"name": "verbose",    "type": "bool",   "label": "Mode verbeux",     "description": "Afficher les details",       "required": False, "default": False},
        {"name": "iterations", "type": "int",    "label": "Iterations",       "description": "Entre 1 et 1000",           "required": False, "default": 10},
        {"name": "threshold",  "type": "float",  "label": "Seuil",            "description": "Valeur entre 0.0 et 1.0",   "required": False, "default": 0.5},
        {"name": "label",      "type": "str",    "label": "Etiquette",        "description": "Texte libre",               "required": False, "default": ""}
    ]
}


def _btn(parent, text, cmd, bg, fg=BG_SURFACE, hover=None,
         width=None, font=None, padx=12, pady=7):
    kw = dict(text=text, command=cmd, bg=bg, fg=fg,
              font=font or FONT_BODY, bd=0, padx=padx, pady=pady,
              relief="flat", cursor="hand2",
              activeforeground=fg, activebackground=hover or bg)
    if width:
        kw["width"] = width
    btn = tk.Button(parent, **kw)
    h = hover or bg
    btn.bind("<Enter>", lambda e: btn.config(bg=h))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


def _sep(parent, color=BORDER, height=1):
    tk.Frame(parent, bg=color, height=height).pack(fill="x")


def load_params_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return None, "JSON invalide : " + str(e)
    except Exception as e:
        return None, "Erreur lecture : " + str(e)

    if "params" not in data or not isinstance(data["params"], list):
        return None, 'Le JSON doit contenir une cle "params" (liste).'

    valid_types = {"str", "int", "float", "bool", "file", "dir", "choice"}
    for i, p in enumerate(data["params"]):
        if "name" not in p:
            return None, 'Parametre #' + str(i+1) + ' : cle "name" manquante.'
        if "type" not in p:
            return None, 'Parametre #' + str(i+1) + ' : cle "type" manquante.'
        if p["type"] not in valid_types:
            return None, 'Parametre #' + str(i+1) + ' : type "' + p["type"] + '" inconnu.'
        if p["type"] == "choice" and "choices" not in p:
            return None, 'Parametre #' + str(i+1) + ' (choice) : cle "choices" manquante.'
    return data, None


class ParamDialog(tk.Toplevel):

    def __init__(self, parent, app_name, params):
        super().__init__(parent)
        self.title("Parametres - " + app_name)
        self.configure(bg=BG_SURFACE)
        self.resizable(True, False)
        self.result = None
        self.grab_set()
        self.transient(parent)
        pw = 520
        ph = max(240, 130 + len(params) * 82)
        sx = (self.winfo_screenwidth()  - pw) // 2
        sy = (self.winfo_screenheight() - ph) // 2
        self.geometry(str(pw) + "x" + str(ph) + "+" + str(sx) + "+" + str(sy))

        hdr = tk.Frame(self, bg=BG_SURFACE)
        hdr.pack(fill="x", padx=20, pady=(16, 6))
        tk.Label(hdr, text="Parametres - " + app_name,
                 bg=BG_SURFACE, fg=TEXT_PRI, font=FONT_HEAD).pack(anchor="w")
        tk.Label(hdr, text="Renseignez les valeurs avant de lancer le script.",
                 bg=BG_SURFACE, fg=TEXT_HINT, font=FONT_SMALL).pack(anchor="w")
        _sep(self)

        self._vars = {}
        body = tk.Frame(self, bg=BG_SURFACE)
        body.pack(fill="both", expand=True, padx=20, pady=10)
        for p in params:
            self._build_row(body, p)

        _sep(self)
        btn_row = tk.Frame(self, bg=BG_SURFACE)
        btn_row.pack(pady=12)
        _btn(btn_row, "> Lancer", self._on_ok,
             ACCENT_G, hover=ACCENT_G_D, width=14).pack(side="left", padx=6)
        _btn(btn_row, "Annuler", self.destroy,
             BG_MUTED, fg=TEXT_SEC, hover=BORDER, width=10).pack(side="left", padx=6)

    def _build_row(self, parent, p):
        name    = p.get("name",    "param")
        ptype   = p.get("type",    "str")
        label   = p.get("label",   name)
        desc    = p.get("description", "")
        req     = p.get("required", True)
        dflt    = p.get("default",  "")
        choices = p.get("choices",  [])

        frame = tk.Frame(parent, bg=BG_MUTED,
                         highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="x", pady=4, ipady=6, ipadx=10)

        top = tk.Frame(frame, bg=BG_MUTED)
        top.pack(fill="x")
        lbl_text = label + ("  *" if req else "")
        tk.Label(top, text=lbl_text, bg=BG_MUTED, fg=ACCENT_V,
                 font=("Segoe UI", 10, "bold")).pack(side="left", anchor="w")
        tk.Label(top, text=ptype, bg=BG_MUTED, fg=TEXT_HINT,
                 font=FONT_SMALL).pack(side="right", anchor="e")
        if desc:
            tk.Label(frame, text=desc, bg=BG_MUTED, fg=TEXT_SEC,
                     font=FONT_SMALL).pack(anchor="w")

        row = tk.Frame(frame, bg=BG_MUTED)
        row.pack(fill="x", pady=(4, 0))

        if ptype == "bool":
            var = tk.BooleanVar(value=bool(dflt))
            self._vars[name] = (var, ptype)
            tk.Checkbutton(row, variable=var, bg=BG_MUTED,
                           activebackground=BG_MUTED, cursor="hand2").pack(side="left")

        elif ptype == "choice":
            if dflt not in choices and choices:
                dflt = choices[0]
            var = tk.StringVar(value=str(dflt))
            self._vars[name] = (var, ptype)
            om = tk.OptionMenu(row, var, *choices)
            om.config(bg=BG_ENTRY, fg=TEXT_PRI, font=FONT_BODY, bd=0,
                      relief="flat", activebackground=ACCENT_V_L,
                      highlightbackground=BORDER, highlightthickness=1, cursor="hand2")
            om["menu"].config(bg=BG_SURFACE, fg=TEXT_PRI, font=FONT_BODY)
            om.pack(side="left", fill="x", expand=True)

        else:
            var = tk.StringVar(value=str(dflt) if dflt is not None else "")
            self._vars[name] = (var, ptype)
            entry = tk.Entry(row, textvariable=var, bg=BG_ENTRY,
                             fg=TEXT_PRI, font=FONT_MONO, bd=0, relief="flat",
                             insertbackground=ACCENT_V,
                             highlightbackground=BORDER_MED, highlightthickness=1)
            entry.pack(side="left", fill="x", expand=True, ipady=5)
            if ptype in ("file", "dir"):
                def browse(v=var, t=ptype):
                    p_ = (filedialog.askopenfilename() if t == "file"
                          else filedialog.askdirectory())
                    if p_:
                        v.set(p_)
                _btn(row, "...", browse, BG_MUTED, fg=TEXT_PRI,
                     hover=BORDER, width=3, padx=6, pady=5).pack(side="left", padx=(6, 0))

    def _on_ok(self):
        self.result = {}
        for name, (var, ptype) in self._vars.items():
            if ptype == "bool":
                self.result[name] = var.get()
                continue
            val = var.get().strip()
            if ptype == "int":
                try:
                    val = int(val)
                except ValueError:
                    messagebox.showwarning("Valeur invalide",
                                           '"' + name + '" doit etre un entier.')
                    return
            elif ptype == "float":
                try:
                    val = float(val.replace(",", "."))
                except ValueError:
                    messagebox.showwarning("Valeur invalide",
                                           '"' + name + '" doit etre un nombre decimal.')
                    return
            self.result[name] = val
        self.destroy()


class AppCard(tk.Frame):

    def __init__(self, parent, app_info, on_remove, on_save, accent_color, **kw):
        super().__init__(parent, bg=BG_SURFACE,
                         highlightbackground=BORDER, highlightthickness=1, **kw)
        self.app_info     = app_info
        self.on_remove    = on_remove
        self.on_save      = on_save
        self.accent_color = accent_color
        self._build()

    def _build(self):
        name      = self.app_info.get("name",        "Script")
        path      = self.app_info.get("path",        "")
        params    = self.app_info.get("params",       [])
        desc      = self.app_info.get("description", "")
        json_path = self.app_info.get("params_json", "")
        ac        = self.accent_color
        n         = len(params)

        tk.Frame(self, bg=ac, height=3).pack(fill="x")

        body = tk.Frame(self, bg=BG_SURFACE)
        body.pack(fill="both", expand=True, padx=12, pady=8)

        tk.Label(body, text=name, bg=BG_SURFACE, fg=TEXT_PRI,
                 font=FONT_HEAD, anchor="w").pack(fill="x")
        tk.Label(body, text=os.path.basename(path), bg=BG_SURFACE,
                 fg=TEXT_HINT, font=FONT_SMALL, anchor="w").pack(fill="x")
        if desc:
            tk.Label(body, text=desc[:90], bg=BG_SURFACE, fg=TEXT_SEC,
                     font=FONT_SMALL, wraplength=260, justify="left").pack(anchor="w", pady=(3, 0))

        badge_row = tk.Frame(body, bg=BG_SURFACE)
        badge_row.pack(anchor="w", pady=(6, 2))
        if n == 0:
            b_bg, b_fg, b_txt = BG_MUTED, TEXT_HINT, "Aucun parametre"
        else:
            b_bg  = ACCENT_V_L
            b_fg  = ACCENT_V
            b_txt = str(n) + " parametre" + ("s" if n > 1 else "")
        tk.Label(badge_row, text=b_txt, bg=b_bg, fg=b_fg,
                 font=FONT_SMALL, padx=8, pady=2).pack(side="left")

        json_lbl   = os.path.basename(json_path) if json_path else "Pas de fichier JSON"
        json_color = ACCENT_G if json_path else TEXT_HINT
        tk.Label(badge_row, text="  " + json_lbl, bg=BG_SURFACE,
                 fg=json_color, font=FONT_SMALL).pack(side="left", padx=(8, 0))

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        btn_row = tk.Frame(self, bg=BG_SURFACE)
        btn_row.pack(fill="x", padx=10, pady=8)
        _btn(btn_row, "> Executer", self._launch,
             ACCENT_G, hover=ACCENT_G_D, padx=10, pady=6).pack(side="left", padx=(0, 6))
        _btn(btn_row, "Changer JSON", self._change_json,
             ACCENT_V_L, fg=ACCENT_V, hover="#CECBF6",
             padx=8, pady=6, font=FONT_SMALL).pack(side="left", padx=(0, 6))
        _btn(btn_row, "x", self._remove,
             ACCENT_C_L, fg=ACCENT_C, hover="#F5C4B3",
             width=3, padx=6, pady=6).pack(side="left")

    def _launch(self):
        path   = self.app_info.get("path",   "")
        params = self.app_info.get("params", [])
        if not os.path.isfile(path):
            messagebox.showerror("Introuvable", "Script introuvable :\n" + path)
            return
        if params:
            dlg = ParamDialog(self.winfo_toplevel(),
                              self.app_info.get("name", "Script"), params)
            self.wait_window(dlg)
            if dlg.result is None:
                return
            param_values = dlg.result
        else:
            param_values = {}
        cmd  = [sys.executable, path] + [str(v) for v in param_values.values()]
        name = self.app_info.get("name", "Script")
        top  = self.winfo_toplevel()

        # Fenetre de progression
        win = tk.Toplevel(top)
        win.title("Execution - " + name)
        win.configure(bg=BG_SURFACE)
        win.resizable(True, True)
        win.grab_set()
        win.transient(top)
        pw, ph = 520, 300
        sx = (win.winfo_screenwidth()  - pw) // 2
        sy = (win.winfo_screenheight() - ph) // 2
        win.geometry(str(pw) + "x" + str(ph) + "+" + str(sx) + "+" + str(sy))

        # En-tete
        hdr = tk.Frame(win, bg=BG_SURFACE)
        hdr.pack(fill="x", padx=20, pady=(16, 6))
        tk.Label(hdr, text=name, bg=BG_SURFACE, fg=TEXT_PRI,
                 font=FONT_HEAD).pack(anchor="w")
        _sep(win)

        # Zone statut (sablier + message)
        status_frame = tk.Frame(win, bg=BG_SURFACE)
        status_frame.pack(fill="x", padx=20, pady=(10, 4))
        spinner_lbl = tk.Label(status_frame, text="( )", bg=BG_SURFACE,
                               fg=ACCENT_V, font=("Segoe UI", 13, "bold"))
        spinner_lbl.pack(side="left")
        status_lbl = tk.Label(status_frame, text="  Execution en cours...",
                              bg=BG_SURFACE, fg=TEXT_SEC, font=FONT_BODY)
        status_lbl.pack(side="left")

        # Zone de sortie
        txt = scrolledtext.ScrolledText(win, bg=BG_ENTRY, fg=TEXT_PRI,
                                         font=FONT_MONO, bd=0, relief="flat",
                                         padx=10, pady=8, state="disabled")
        txt.pack(fill="both", expand=True, padx=14, pady=(4, 10))

        btn_close = _btn(win, "Fermer", win.destroy,
                         BG_MUTED, fg=TEXT_SEC, hover=BORDER,
                         padx=12, font=FONT_SMALL)
        btn_close.pack(pady=(0, 12))
        btn_close.config(state="disabled")

        # Animation sablier
        frames = ["( )", "(o)", "(O)", "(o)"]
        anim_running = [True]
        frame_idx    = [0]

        def animate():
            if anim_running[0]:
                spinner_lbl.config(text=frames[frame_idx[0] % len(frames)])
                frame_idx[0] += 1
                win.after(200, animate)

        animate()

        def append_text(text):
            txt.config(state="normal")
            txt.insert("end", text)
            txt.see("end")
            txt.config(state="disabled")

        def run():
            try:
                r = subprocess.run(cmd, capture_output=True, text=True,
                                   cwd=os.path.dirname(path))
                def done():
                    anim_running[0] = False
                    spinner_lbl.config(
                        text="OK" if r.returncode == 0 else "!!",
                        fg=ACCENT_G if r.returncode == 0 else ACCENT_C)
                    status_lbl.config(
                        text="  Termine (code " + str(r.returncode) + ")",
                        fg=ACCENT_G if r.returncode == 0 else ACCENT_C)
                    output = ""
                    if r.stdout:
                        output += r.stdout
                    if r.stderr:
                        output += "\n--- Erreurs ---\n" + r.stderr
                    if output:
                        append_text(output)
                    else:
                        append_text("(aucune sortie)")
                    btn_close.config(state="normal")
                win.after(0, done)
            except Exception as e:
                def err():
                    anim_running[0] = False
                    spinner_lbl.config(text="!!", fg=ACCENT_C)
                    status_lbl.config(text="  Erreur lors du lancement", fg=ACCENT_C)
                    append_text(str(e))
                    btn_close.config(state="normal")
                win.after(0, err)

        threading.Thread(target=run, daemon=True).start()

    def _change_json(self):
        path = filedialog.askopenfilename(
            title="Selectionner le fichier JSON de parametres",
            filetypes=[("Fichiers JSON", "*.json"), ("Tous", "*.*")])
        if not path:
            return
        data, err = load_params_json(path)
        if err:
            messagebox.showerror("JSON invalide", err)
            return
        self.app_info["params_json"]  = path
        self.app_info["params"]       = data.get("params", [])
        self.app_info["description"]  = data.get("description", self.app_info.get("description", ""))
        self.on_save()
        for w in self.winfo_children():
            w.destroy()
        self._build()

    def _remove(self):
        if messagebox.askyesno("Retirer",
                               "Retirer \"" + self.app_info.get("name", "") + "\" du lanceur ?"):
            self.on_remove(self.app_info)


class PythonLauncher(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Python Launcher")
        self.configure(bg=BG_PAGE)
        self.resizable(True, True)
        self.minsize(740, 520)
        self.apps   = []
        self._cards = []
        self._load_config()
        self._build_ui()
        self._center(960, 660)
        self._refresh_cards()

    def _center(self, w, h):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(str(w) + "x" + str(h) + "+" + str((sw-w)//2) + "+" + str((sh-h)//2))

    def _load_config(self):
        if os.path.isfile(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.apps = data.get("apps", [])
            except Exception:
                pass

    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"apps": self.apps}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showwarning("Sauvegarde", "Impossible de sauvegarder : " + str(e))

    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG_SURFACE, pady=10)
        hdr.pack(fill="x")
        left = tk.Frame(hdr, bg=BG_SURFACE)
        left.pack(side="left", padx=18)
        icon = tk.Frame(left, bg=ACCENT_V, width=30, height=30)
        icon.pack(side="left")
        icon.pack_propagate(False)
        tk.Label(icon, text="^", bg=ACCENT_V, fg=BG_SURFACE,
                 font=("Segoe UI", 13, "bold")).place(relx=.5, rely=.5, anchor="center")
        tf = tk.Frame(left, bg=BG_SURFACE)
        tf.pack(side="left", padx=(10, 0))
        tk.Label(tf, text="Python Launcher",
                 bg=BG_SURFACE, fg=TEXT_PRI, font=FONT_TITLE).pack(anchor="w")
        tk.Label(tf, text="Lanceur de scripts - parametres via fichier JSON",
                 bg=BG_SURFACE, fg=TEXT_HINT, font=FONT_SMALL).pack(anchor="w")
        _btn(hdr, "Voir structure JSON", self._show_example,
             BG_MUTED, fg=TEXT_SEC, hover=BORDER,
             padx=10, pady=6, font=FONT_SMALL).pack(side="right", padx=18)
        _sep(self)

        toolbar = tk.Frame(self, bg=BG_MUTED, pady=8)
        toolbar.pack(fill="x")
        tk.Label(toolbar, text="   Programmes",
                 bg=BG_MUTED, fg=TEXT_SEC, font=FONT_SMALL).pack(side="left")
        _btn(toolbar, "+ Ajouter un script...", self._add_app,
             ACCENT_V_L, fg=ACCENT_V, hover="#CECBF6",
             padx=10, pady=5, font=FONT_SMALL).pack(side="left", padx=12)
        _sep(self)

        outer = tk.Frame(self, bg=BG_PAGE)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=BG_PAGE, bd=0, highlightthickness=0)
        vsb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        self._cards_frame = tk.Frame(canvas, bg=BG_PAGE)
        self._canvas_win  = canvas.create_window((0, 0), window=self._cards_frame, anchor="nw")
        self._cards_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(self._canvas_win, width=e.width))
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))

        sb = tk.Frame(self, bg=BG_MUTED)
        sb.pack(fill="x", side="bottom")
        _sep(sb)
        self._status = tk.StringVar(value="Pret.")
        tk.Label(sb, textvariable=self._status, bg=BG_MUTED, fg=TEXT_HINT,
                 font=FONT_SMALL, anchor="w", padx=14, pady=5).pack(fill="x")

    def _add_app(self):
        py_path = filedialog.askopenfilename(
            title="Selectionner un script Python",
            initialdir=DEFAULT_DIR,
            filetypes=[("Scripts Python", "*.py"), ("Tous", "*.*")])
        if not py_path:
            return
        if any(a["path"] == py_path for a in self.apps):
            messagebox.showinfo("Deja present", "Ce script est deja dans le lanceur.")
            return
        name = os.path.splitext(os.path.basename(py_path))[0]
        params    = []
        json_path = ""
        desc      = ""
        if messagebox.askyesno(
                "Fichier de parametres",
                "Voulez-vous associer un fichier JSON de parametres a \"" + name + "\" ?\n\n"
                "Cliquez Non si le script ne prend pas de parametres."):
            json_path = filedialog.askopenfilename(
                title="Selectionner le fichier JSON de parametres",
                initialdir=os.path.dirname(py_path),
                filetypes=[("Fichiers JSON", "*.json"), ("Tous", "*.*")])
            if json_path:
                data, err = load_params_json(json_path)
                if err:
                    messagebox.showerror("JSON invalide", err)
                    json_path = ""
                else:
                    params = data.get("params", [])
                    desc   = data.get("description", "")
        self.apps.append({
            "name":        name,
            "path":        py_path,
            "params_json": json_path,
            "params":      params,
            "description": desc,
        })
        self._save_config()
        self._refresh_cards()
        self._status.set("\"" + name + "\" ajoute - " + str(len(params)) + " parametre(s) charge(s).")

    def _show_example(self):
        win = tk.Toplevel(self)
        win.title("Structure du fichier JSON de parametres")
        win.configure(bg=BG_SURFACE)
        win.geometry("660x600")
        win.grab_set()

        tk.Label(win, text="Structure du fichier JSON de parametres",
                 bg=BG_SURFACE, fg=TEXT_PRI, font=FONT_HEAD,
                 anchor="w").pack(anchor="w", padx=16, pady=(14, 4))

        info = [
            "Champs obligatoires par parametre : name, type",
            "Champs optionnels : label, description, required (bool), default",
            "",
            "Types disponibles :",
            "  str    -> texte libre",
            "  int    -> nombre entier",
            "  float  -> nombre decimal",
            "  bool   -> case a cocher  (default: true ou false)",
            '  file   -> chemin fichier  (bouton "..." pour parcourir)',
            '  dir    -> chemin dossier  (bouton "..." pour parcourir)',
            '  choice -> liste deroulante (obligatoire: "choices": ["val1", "val2", ...])',
        ]
        for line in info:
            tk.Label(win, text=line, bg=BG_SURFACE,
                     fg=TEXT_SEC if line else BG_SURFACE,
                     font=FONT_SMALL, anchor="w").pack(anchor="w", padx=16)

        _sep(win)
        txt = scrolledtext.ScrolledText(win, bg=BG_ENTRY, fg=TEXT_PRI,
                                         font=FONT_MONO, bd=0, relief="flat",
                                         padx=12, pady=8)
        txt.pack(fill="both", expand=True, padx=14, pady=10)
        txt.insert("1.0", json.dumps(PARAMS_EXAMPLE, indent=2, ensure_ascii=True))
        txt.config(state="disabled")
        _sep(win)

        def _copy():
            win.clipboard_clear()
            win.clipboard_append(json.dumps(PARAMS_EXAMPLE, indent=2, ensure_ascii=True))
            cb.config(text="Copie !")
            win.after(1500, lambda: cb.config(text="Copier dans le presse-papier"))

        br = tk.Frame(win, bg=BG_SURFACE)
        br.pack(pady=10)
        cb = _btn(br, "Copier dans le presse-papier", _copy,
                  ACCENT_V_L, fg=ACCENT_V, hover="#CECBF6", padx=10, font=FONT_SMALL)
        cb.pack(side="left", padx=6)
        _btn(br, "Fermer", win.destroy,
             BG_MUTED, fg=TEXT_SEC, hover=BORDER, padx=10, font=FONT_SMALL).pack(side="left", padx=6)

    def _remove_app(self, app_info):
        self.apps = [a for a in self.apps if a["path"] != app_info["path"]]
        self._save_config()
        self._refresh_cards()
        self._status.set("\"" + app_info["name"] + "\" retire.")

    def _refresh_cards(self):
        for w in self._cards_frame.winfo_children():
            w.destroy()
        self._cards = []
        if not self.apps:
            tk.Label(self._cards_frame,
                     text="Aucun script ajoute.\nCliquez sur \"+ Ajouter un script...\"",
                     bg=BG_PAGE, fg=TEXT_HINT, font=FONT_BODY,
                     justify="center").pack(pady=80)
            self._status.set("Pret.")
            return
        for i, app_info in enumerate(self.apps):
            row, col = divmod(i, 3)
            ac   = CARD_ACCENTS[i % len(CARD_ACCENTS)]
            card = AppCard(self._cards_frame, app_info,
                           on_remove=self._remove_app,
                           on_save=self._save_config,
                           accent_color=ac, width=280)
            card.grid(row=row, column=col, padx=14, pady=12, sticky="nsew")
            self._cards.append(card)
        for c in range(3):
            self._cards_frame.columnconfigure(c, weight=1)
        self._status.set("Pret - " + str(len(self.apps)) + " programme(s) charge(s).")


if __name__ == "__main__":
    PythonLauncher().mainloop()