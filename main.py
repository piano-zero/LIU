import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext, filedialog
import sqlite3
from datetime import datetime, timedelta
from PIL import Image, ImageTk 
import os
import shutil 

# --- IMPORT MODULI PROPRIETARI ---
import liu_config as cfg
import liu_reports as rep

# --- SPLASH SCREEN ---
def show_splash_screen():
    splash = tk.Tk()
    splash.overrideredirect(True)
    width, height = 500, 350
    screen_width, screen_height = splash.winfo_screenwidth(), splash.winfo_screenheight()
    splash.geometry(f'{width}x{height}+{int((screen_width/2)-(width/2))}+{int((screen_height/2)-(height/2))}')
    bg_color = "#4a4a4a" 
    splash.configure(bg=bg_color)
    try:
        if os.path.exists(cfg.NOME_IMMAGINE_SPLASH):
            pil_img = Image.open(cfg.NOME_IMMAGINE_SPLASH)
            pil_img.thumbnail((300, 200)) 
            img = ImageTk.PhotoImage(pil_img)
            lbl_img = tk.Label(splash, image=img, bg=bg_color)
            lbl_img.image = img
            lbl_img.pack(pady=(40, 10))
        else:
            tk.Label(splash, text="LIU'", font=("Georgia", 40, "bold"), fg="orange", bg=bg_color).pack(pady=(50,10))
    except Exception: pass
    
    tk.Label(splash, text=f"{cfg.VERSIONE}", font=("Arial", 9, "bold"), fg="#cccccc", bg=bg_color).pack(pady=(20, 5))
    tk.Label(splash, text=f"{cfg.COPYRIGHT}", font=("Arial", 9, "bold"), fg="#cccccc", bg=bg_color).pack(pady=(5, 5))
    
    progress = ttk.Progressbar(splash, orient="horizontal", length=400, mode="determinate")
    progress.pack(pady=20)
    progress.start(30)
    splash.after(3000, splash.destroy)
    splash.mainloop()

# --- FINESTRA GESTIONE COMUNI ---
class GestioneComuniDialog:
    def __init__(self, parent, conn):
        self.win = tk.Toplevel(parent)
        self.win.title("Gestione e Bonifica Comuni")
        self.win.geometry("500x500")
        self.conn = conn
        self.cursor = self.conn.cursor()
        
        ttk.Label(self.win, text="Lista Comuni registrati", font=("Arial", 12, "bold")).pack(pady=10)
        frame_list = ttk.Frame(self.win)
        frame_list.pack(expand=True, fill="both", padx=10)
        self.scrollbar = ttk.Scrollbar(frame_list)
        self.scrollbar.pack(side="right", fill="y")
        self.listbox = tk.Listbox(frame_list, yscrollcommand=self.scrollbar.set, font=("Arial", 11))
        self.listbox.pack(side="left", expand=True, fill="both")
        self.scrollbar.config(command=self.listbox.yview)
        
        frame_edit = ttk.LabelFrame(self.win, text="Strumenti di Bonifica")
        frame_edit.pack(fill="x", padx=10, pady=10)
        ttk.Label(frame_edit, text="Seleziona un comune errato e scrivi quello corretto:").pack(pady=5)
        self.entry_fix = ttk.Entry(frame_edit, width=30); self.entry_fix.pack(pady=5)
        btn_frame = ttk.Frame(frame_edit); btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="✏️ Rinomina/Unisci", command=self.rinomina_comune).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🗑️ Elimina (Solo se non usato)", command=self.elimina_comune).pack(side="left", padx=5)
        self.listbox.bind('<<ListboxSelect>>', self.on_select); self.aggiorna_lista()

    def aggiorna_lista(self):
        self.listbox.delete(0, tk.END)
        self.cursor.execute("SELECT nome FROM comuni ORDER BY nome")
        for row in self.cursor.fetchall(): self.listbox.insert(tk.END, row[0])

    def on_select(self, event):
        sel = self.listbox.curselection()
        if sel: self.entry_fix.delete(0, tk.END); self.entry_fix.insert(0, self.listbox.get(sel[0]))

    def rinomina_comune(self):
        sel = self.listbox.curselection()
        if not sel: return
        vecchio, nuovo = self.listbox.get(sel[0]), self.entry_fix.get().strip().title()
        if not nuovo or nuovo == vecchio: return
        if messagebox.askyesno("Conferma", f"Spostare tutti da '{vecchio}' a '{nuovo}'?"):
            try:
                self.cursor.execute("UPDATE utenti SET comune = ? WHERE comune = ?", (nuovo, vecchio))
                self.cursor.execute("SELECT nome FROM comuni WHERE nome = ?", (nuovo,))
                if self.cursor.fetchone(): self.cursor.execute("DELETE FROM comuni WHERE nome = ?", (vecchio,))
                else: self.cursor.execute("UPDATE comuni SET nome = ? WHERE nome = ?", (nuovo, vecchio))
                self.conn.commit(); messagebox.showinfo("OK", "Bonifica completata!"); self.aggiorna_lista()
            except Exception as e: messagebox.showerror("Errore", str(e))

    def elimina_comune(self):
        sel = self.listbox.curselection()
        if not sel: return
        nome = self.listbox.get(sel[0])
        self.cursor.execute("SELECT count(*) FROM utenti WHERE comune = ?", (nome,))
        if self.cursor.fetchone()[0] > 0: messagebox.showwarning("Stop", "Comune in uso da utenti. Usa Rinomina."); return
        if messagebox.askyesno("Elimina", f"Eliminare '{nome}'?"):
            self.cursor.execute("DELETE FROM comuni WHERE nome = ?", (nome,)); self.conn.commit(); self.aggiorna_lista()

# --- APP ---
class BibliotecaApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1200x800") 
        
        self.id_utente_in_modifica = None
        self.id_operatore_in_modifica = None 
        self.mostra_storico_prestiti = tk.BooleanVar(value=False)
        self.filtro_solo_ritardi = tk.BooleanVar(value=False)
        self.mostra_storico_utenti = tk.BooleanVar(value=False)
        self.mostra_storico_operatori = tk.BooleanVar(value=False)
        self.config_unlocked = False 
        self.config_data = {} 
        self.lista_comuni_cache = [] 
        self.lista_libri_cache = []
        self.mappa_operatori = {} 
        self.lista_utenti_cache = [] 
        
        self.init_db()
        self.carica_configurazione()
        self.pdf_manager = rep.PDFManager(self.config_data)
        
        self.root.title(f"LIU' - Gestionale: {self.config_data.get('nome_biblio', 'Biblioteca')}")
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", rowheight=25)
        
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=10, expand=True, fill="both")
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        
        self.frame_utenti = ttk.Frame(self.notebook); self.notebook.add(self.frame_utenti, text="👤 Anagrafica Utenti"); self.setup_utenti_tab()
        self.frame_prestiti = ttk.Frame(self.notebook); self.notebook.add(self.frame_prestiti, text="📚 Gestione Prestiti"); self.setup_prestiti_tab()
        self.frame_statistiche = ttk.Frame(self.notebook); self.notebook.add(self.frame_statistiche, text="📊 Statistiche"); self.setup_statistiche_tab()
        self.frame_stampe = ttk.Frame(self.notebook); self.notebook.add(self.frame_stampe, text="🖨️ Centro Stampe"); self.setup_stampe_tab()
        self.frame_info = ttk.Frame(self.notebook); self.notebook.add(self.frame_info, text="ℹ️ Info"); self.setup_info_tab() 
        self.frame_config = ttk.Frame(self.notebook); self.notebook.add(self.frame_config, text="⚙️ Amministrazione"); self.setup_config_tab()

    def init_db(self):
        self.conn = sqlite3.connect(cfg.NOME_DB)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS utenti (id INTEGER PRIMARY KEY AUTOINCREMENT, data_registrazione DATE, nome TEXT NOT NULL, cognome TEXT NOT NULL, data_nascita DATE, comune TEXT, documento TEXT, email TEXT, telefono TEXT, attivo INTEGER DEFAULT 1)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS prestiti (id INTEGER PRIMARY KEY AUTOINCREMENT, utente_id INTEGER, titolo_libro TEXT NOT NULL, data_inizio DATE, data_scadenza DATE, data_restituzione DATE, FOREIGN KEY(utente_id) REFERENCES utenti(id))''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY CHECK (id = 1), nome_biblio TEXT, indirizzo TEXT, telefono TEXT, email TEXT, giorni_prestito INTEGER DEFAULT 30, password_admin TEXT DEFAULT 'admin', testo_regolamento TEXT, disclaimer_copyright TEXT)''') 
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS operatori (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, cognome TEXT NOT NULL, attivo INTEGER DEFAULT 1)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS comuni (nome TEXT PRIMARY KEY)''')
        
        try: self.cursor.execute("SELECT operatore_id FROM utenti"); 
        except: self.cursor.execute("ALTER TABLE utenti ADD COLUMN operatore_id INTEGER"); self.conn.commit()
        try: self.cursor.execute("SELECT op_prestito_id FROM prestiti"); 
        except: self.cursor.execute("ALTER TABLE prestiti ADD COLUMN op_prestito_id INTEGER"); self.conn.commit()
        try: self.cursor.execute("SELECT op_rientro_id FROM prestiti"); 
        except: self.cursor.execute("ALTER TABLE prestiti ADD COLUMN op_rientro_id INTEGER"); self.conn.commit()
        try: self.cursor.execute("SELECT testo_regolamento FROM config")
        except sqlite3.OperationalError: self.cursor.execute("ALTER TABLE config ADD COLUMN testo_regolamento TEXT"); self.conn.commit()
        try: self.cursor.execute("SELECT disclaimer_copyright FROM config")
        except sqlite3.OperationalError: self.cursor.execute("ALTER TABLE config ADD COLUMN disclaimer_copyright TEXT"); self.conn.commit()
        
        self.cursor.execute("SELECT count(*) FROM config")
        if self.cursor.fetchone()[0] == 0:
            regolamento_default = "Il prestito ha durata di 30 giorni..."
            self.cursor.execute('''INSERT INTO config (id, nome_biblio, indirizzo, telefono, email, giorni_prestito, password_admin, testo_regolamento, disclaimer_copyright) VALUES (1, 'Biblioteca Comunale', 'Via Roma 1', '000-000000', 'info@biblioteca.it', 30, 'admin', ?, ?)''', (regolamento_default, ""))
        self.cursor.execute("SELECT count(*) FROM comuni")
        if self.cursor.fetchone()[0] == 0:
            for c in cfg.COMUNI_SALERNO: self.cursor.execute("INSERT OR IGNORE INTO comuni (nome) VALUES (?)", (c,))
        self.conn.commit()
        
        self.cursor.execute("UPDATE operatori SET attivo = 1 WHERE attivo IS NULL OR attivo = 0")
        self.conn.commit()

    def carica_configurazione(self):
        self.cursor.execute("SELECT nome_biblio, indirizzo, telefono, email, giorni_prestito, password_admin, testo_regolamento, disclaimer_copyright FROM config WHERE id=1")
        row = self.cursor.fetchone()
        self.config_data = {'nome_biblio': row[0], 'indirizzo': row[1], 'telefono': row[2], 'email': row[3], 'giorni_prestito': row[4], 'password_admin': row[5], 'testo_regolamento': row[6] if row[6] else "", 'disclaimer_copyright': row[7] if row[7] else ""}

    # --- HELPER UTILS ---
    def get_lista_comuni(self):
        self.cursor.execute("SELECT nome FROM comuni ORDER BY nome")
        self.lista_comuni_cache = [row[0] for row in self.cursor.fetchall()]
        return self.lista_comuni_cache
    
    def get_lista_operatori_nomi(self):
        self.cursor.execute("SELECT id, nome, cognome FROM operatori WHERE attivo=1 ORDER BY nome")
        rows = self.cursor.fetchall()
        self.mappa_operatori = {}
        nomi_puliti = []
        for r in rows:
            nome_completo = f"{r[1]} {r[2]}"
            self.mappa_operatori[nome_completo] = r[0] 
            nomi_puliti.append(nome_completo)
        return nomi_puliti
    
    def get_lista_libri_cache(self):
        self.cursor.execute("SELECT DISTINCT titolo_libro FROM prestiti ORDER BY titolo_libro")
        self.lista_libri_cache = [row[0] for row in self.cursor.fetchall()]
        return self.lista_libri_cache
    
    def refresh_all_dropdowns(self):
        ops = self.get_lista_operatori_nomi()
        try: self.combo_operatore_reg['values'] = ops
        except: pass
        try: self.combo_operatore_prestiti['values'] = ops
        except: pass

    def ordina_colonna_treeview(self, tree, col, reverse):
        l = [(tree.set(k, col), k) for k in tree.get_children('')]
        try: l.sort(key=lambda t: int(t[0]), reverse=reverse)
        except ValueError:
            try: l.sort(key=lambda t: datetime.strptime(t[0], "%d/%m/%Y"), reverse=reverse)
            except ValueError: l.sort(key=lambda t: t[0].lower(), reverse=reverse)
        for index, (val, k) in enumerate(l): tree.move(k, '', index)
        tree.heading(col, command=lambda: self.ordina_colonna_treeview(tree, col, not reverse))
    def abilita_ordinamento(self, tree, columns):
        for col in columns: tree.heading(col, text=col, command=lambda c=col: self.ordina_colonna_treeview(tree, c, False))

    # --- TAB UTENTI ---
    def setup_utenti_tab(self):
        self.input_frame_utenti = ttk.LabelFrame(self.frame_utenti, text="Dati Anagrafici")
        self.input_frame_utenti.pack(side="top", fill="x", padx=10, pady=5)

        ttk.Label(self.input_frame_utenti, text="Operatore:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.combo_operatore_reg = ttk.Combobox(self.input_frame_utenti, width=20, state="readonly")
        self.combo_operatore_reg.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.combo_operatore_reg['values'] = self.get_lista_operatori_nomi()

        ttk.Label(self.input_frame_utenti, text="Nome:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.entry_nome = ttk.Entry(self.input_frame_utenti, width=25)
        self.entry_nome.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        ttk.Label(self.input_frame_utenti, text="Cognome:").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.entry_cognome = ttk.Entry(self.input_frame_utenti, width=25)
        self.entry_cognome.grid(row=0, column=5, padx=5, pady=5, sticky="w")

        ttk.Label(self.input_frame_utenti, text="Nascita (gg/mm/aaaa):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.entry_nascita = ttk.Entry(self.input_frame_utenti, width=20)
        self.entry_nascita.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        ttk.Label(self.input_frame_utenti, text="Documento (CIE):").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        self.entry_documento = ttk.Entry(self.input_frame_utenti, width=25)
        self.entry_documento.grid(row=1, column=3, padx=5, pady=5, sticky="w")
        ttk.Label(self.input_frame_utenti, text="Comune:").grid(row=1, column=4, padx=5, pady=5, sticky="e")
        self.entry_comune = ttk.Combobox(self.input_frame_utenti, width=23)
        self.entry_comune.grid(row=1, column=5, padx=5, pady=5, sticky="w")
        self.entry_comune['values'] = self.get_lista_comuni()
        self.entry_comune.bind('<KeyRelease>', self.filtra_comuni)

        ttk.Label(self.input_frame_utenti, text="Email:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.entry_email = ttk.Entry(self.input_frame_utenti, width=40)
        self.entry_email.grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky="w") 
        ttk.Label(self.input_frame_utenti, text="Telefono:").grid(row=2, column=4, padx=5, pady=5, sticky="e")
        self.entry_telefono = ttk.Entry(self.input_frame_utenti, width=20)
        self.entry_telefono.grid(row=2, column=5, padx=5, pady=5, sticky="w")

        bottom_frame = ttk.Frame(self.frame_utenti)
        bottom_frame.pack(side="bottom", fill="both", expand=True, padx=10, pady=5)

        list_frame = ttk.Frame(bottom_frame)
        list_frame.pack(side="left", fill="both", expand=True)
        ttk.Checkbutton(list_frame, text="Mostra ARCHIVIATI", variable=self.mostra_storico_utenti, command=self.aggiorna_lista_utenti).pack(anchor='w')
        
        cols = ("ID", "Data Reg.", "Nome", "Cognome", "Nascita", "Comune", "Doc", "Email", "Tel")
        self.tree_utenti = ttk.Treeview(list_frame, columns=cols, show="headings")
        self.abilita_ordinamento(self.tree_utenti, cols)
        for col in cols: 
            self.tree_utenti.heading(col, text=col); self.tree_utenti.column(col, width=80)
        self.tree_utenti.column("ID", width=40)
        scr = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree_utenti.yview)
        self.tree_utenti.configure(yscroll=scr.set)
        scr.pack(side="right", fill="y"); self.tree_utenti.pack(side="left", expand=True, fill="both")
        self.tree_utenti.bind("<<TreeviewSelect>>", self.on_user_select)

        btn_frame_right = ttk.Frame(bottom_frame)
        btn_frame_right.pack(side="right", fill="y", padx=(10, 0)) 
        self.btn_cerca = ttk.Button(btn_frame_right, text="🔍 Cerca Utente", command=self.cerca_utenti)
        self.btn_cerca.pack(side="top", fill="x", pady=5)
        self.btn_pulisci = ttk.Button(btn_frame_right, text="🧹 Pulisci Campi", command=self.reset_form_utenti)
        self.btn_pulisci.pack(side="top", fill="x", pady=5)
        ttk.Separator(btn_frame_right, orient="horizontal").pack(fill="x", pady=10)
        self.btn_salva_utente = ttk.Button(btn_frame_right, text="Salva Nuovo Utente", command=self.salva_utente)
        self.btn_salva_utente.pack(side="top", fill="x", pady=5)
        self.btn_annulla = ttk.Button(btn_frame_right, text="Annulla Modifica", command=self.reset_form_utenti, state="disabled")
        self.btn_annulla.pack(side="top", fill="x", pady=5)
        ttk.Separator(btn_frame_right, orient="horizontal").pack(fill="x", pady=10)
        ttk.Button(btn_frame_right, text="✏️ Modifica Utente", command=self.carica_utente_per_modifica).pack(side="top", fill="x", pady=5)
        self.btn_archivia = ttk.Button(btn_frame_right, text="📦 Archivia Utente", command=self.toggle_stato_utente)
        self.btn_archivia.pack(side="top", fill="x", pady=5)
        ttk.Separator(btn_frame_right, orient="horizontal").pack(fill="x", pady=10)
        ttk.Button(btn_frame_right, text="🖨️ Stampa Scheda", command=self.stampa_scheda_utente).pack(side="top", fill="x", pady=5)
        self.aggiorna_lista_utenti()

    def filtra_comuni(self, event):
        dig = self.entry_comune.get()
        self.entry_comune['values'] = self.lista_comuni_cache if not dig else [i for i in self.lista_comuni_cache if dig.lower() in i.lower()]

    def on_user_select(self, event):
        if self.tree_utenti.selection():
            tags = self.tree_utenti.item(self.tree_utenti.selection())['tags']
            self.btn_archivia.config(text="♻️ Ripristina Utente" if 'archiviato' in tags else "📦 Archivia Utente")

    def stampa_scheda_utente(self):
        if not self.tree_utenti.selection(): messagebox.showwarning("!", "Seleziona utente"); return
        try: self.pdf_manager.crea_scheda_iscrizione(self.tree_utenti.item(self.tree_utenti.selection())['values'], self.config_data.get('testo_regolamento', ""))
        except Exception as e: messagebox.showerror("Errore Stampa", str(e))

    def cerca_utenti(self):
        for r in self.tree_utenti.get_children(): self.tree_utenti.delete(r)
        nome = self.entry_nome.get().strip(); cognome = self.entry_cognome.get().strip(); comune = self.entry_comune.get().strip()
        email = self.entry_email.get().strip(); tel = self.entry_telefono.get().strip(); doc = self.entry_documento.get().strip()
        query = "SELECT id, data_registrazione, nome, cognome, data_nascita, comune, documento, email, telefono, attivo FROM utenti WHERE 1=1"
        params = []
        if not self.mostra_storico_utenti.get(): query += " AND attivo=1"
        if nome: query += " AND nome LIKE ?"; params.append(f"%{nome}%")
        if cognome: query += " AND cognome LIKE ?"; params.append(f"%{cognome}%")
        if comune: query += " AND comune LIKE ?"; params.append(f"%{comune}%")
        if email: query += " AND email LIKE ?"; params.append(f"%{email}%")
        if tel: query += " AND telefono LIKE ?"; params.append(f"%{tel}%")
        if doc: query += " AND documento LIKE ?"; params.append(f"%{doc}%")
        query += " ORDER BY cognome"
        try:
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            if not rows: messagebox.showinfo("Ricerca", "Nessun utente trovato con questi criteri."); return
            for r in rows:
                l = list(r[:9]); l[1] = cfg.data_db_to_ita(l[1]); l[4] = cfg.data_db_to_ita(l[4]) 
                self.tree_utenti.insert("", "end", values=l, tags=("attivo" if r[9] else "archiviato",))
            self.tree_utenti.tag_configure("archiviato", foreground="gray")
        except Exception as e: messagebox.showerror("Errore Ricerca", str(e))

    def salva_utente(self):
        op_str = self.combo_operatore_reg.get(); op_id = self.mappa_operatori.get(op_str)
        if not self.id_utente_in_modifica and not op_id:
            messagebox.showerror("Errore Bloccante", "Devi selezionare un Operatore per registrare un nuovo utente!"); return
        nome, cognome = self.entry_nome.get().strip(), self.entry_cognome.get().strip()
        if not nome or not cognome: messagebox.showerror("Errore", "Nome e Cognome sono obbligatori"); return
        try: nascita = cfg.data_ita_to_db(self.entry_nascita.get().strip())
        except: messagebox.showerror("Errore", "Data errata"); return
        comune = self.entry_comune.get().strip().title()
        if comune: 
            self.cursor.execute("INSERT OR IGNORE INTO comuni (nome) VALUES (?)", (comune,)); self.conn.commit()
            self.get_lista_comuni(); self.entry_comune['values'] = self.lista_comuni_cache
        dati = [nome, cognome, nascita, comune, self.entry_documento.get(), self.entry_email.get(), self.entry_telefono.get()]
        if self.id_utente_in_modifica: 
            self.cursor.execute("UPDATE utenti SET nome=?, cognome=?, data_nascita=?, comune=?, documento=?, email=?, telefono=? WHERE id=?", dati + [self.id_utente_in_modifica])
        else: 
            self.cursor.execute("INSERT INTO utenti (data_registrazione, nome, cognome, data_nascita, comune, documento, email, telefono, attivo, operatore_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)", [datetime.now().strftime("%Y-%m-%d")] + dati + [op_id])
        self.conn.commit(); self.reset_form_utenti(); self.aggiorna_lista_utenti(); self.aggiorna_dropdown_utenti()

    def carica_utente_per_modifica(self):
        if not self.tree_utenti.selection(): return
        val = self.tree_utenti.item(self.tree_utenti.selection())['values']; self.id_utente_in_modifica = val[0]
        self.cursor.execute("SELECT * FROM utenti WHERE id=?", (self.id_utente_in_modifica,)); u = self.cursor.fetchone()
        self.entry_nome.delete(0, tk.END); self.entry_nome.insert(0, u[2])
        self.entry_cognome.delete(0, tk.END); self.entry_cognome.insert(0, u[3])
        self.entry_nascita.delete(0, tk.END); self.entry_nascita.insert(0, cfg.data_db_to_ita(u[4]) if u[4] else "")
        self.entry_comune.set(u[5] or ""); self.entry_documento.delete(0, tk.END); self.entry_documento.insert(0, u[6] or "")
        self.entry_email.delete(0, tk.END); self.entry_email.insert(0, u[7] or ""); self.entry_telefono.delete(0, tk.END); self.entry_telefono.insert(0, u[8] or "")
        self.btn_salva_utente.config(text="Aggiorna Utente"); self.btn_annulla.config(state="normal")

    def reset_form_utenti(self):
        self.id_utente_in_modifica = None; self.btn_salva_utente.config(text="Salva Nuovo Utente"); self.btn_annulla.config(state="disabled")
        for e in [self.entry_nome, self.entry_cognome, self.entry_nascita, self.entry_comune, self.entry_documento, self.entry_email, self.entry_telefono]: e.delete(0, tk.END)
        self.combo_operatore_reg.set(''); self.aggiorna_lista_utenti()

    def toggle_stato_utente(self):
        if not self.tree_utenti.selection(): return
        uid = self.tree_utenti.item(self.tree_utenti.selection())['values'][0]
        st = 1 if 'archiviato' in self.tree_utenti.item(self.tree_utenti.selection())['tags'] else 0
        self.cursor.execute("UPDATE utenti SET attivo=? WHERE id=?", (st, uid)); self.conn.commit(); self.aggiorna_lista_utenti()

    def aggiorna_lista_utenti(self):
        for r in self.tree_utenti.get_children(): self.tree_utenti.delete(r)
        q = "SELECT id, data_registrazione, nome, cognome, data_nascita, comune, documento, email, telefono, attivo FROM utenti" + ("" if self.mostra_storico_utenti.get() else " WHERE attivo=1") + " ORDER BY cognome"
        self.cursor.execute(q)
        for r in self.cursor.fetchall():
            l = list(r[:9]); l[1] = cfg.data_db_to_ita(l[1]); l[4] = cfg.data_db_to_ita(l[4])
            self.tree_utenti.insert("", "end", values=l, tags=("attivo" if r[9] else "archiviato",))
        self.tree_utenti.tag_configure("archiviato", foreground="gray")

    # --- TAB PRESTITI ---
    def setup_prestiti_tab(self):
        input_frame = ttk.LabelFrame(self.frame_prestiti, text="Gestione Movimenti"); input_frame.pack(side="top", fill="x", padx=10, pady=5)
        ttk.Label(input_frame, text="Operatore di Turno:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.combo_operatore_prestiti = ttk.Combobox(input_frame, width=25, state="readonly"); self.combo_operatore_prestiti.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.combo_operatore_prestiti['values'] = self.get_lista_operatori_nomi()
        ttk.Label(input_frame, text="Utente:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.combo_utenti = ttk.Combobox(input_frame, width=30); self.combo_utenti.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.aggiorna_dropdown_utenti(); self.combo_utenti.bind('<KeyRelease>', self.filtra_utenti_prestito)
        ttk.Label(input_frame, text="Libro:").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        self.entry_libro = ttk.Combobox(input_frame, width=30); self.entry_libro.grid(row=1, column=3, padx=5, pady=5, sticky="w")
        self.entry_libro.bind('<KeyRelease>', self.filtra_libri); self.entry_libro['values'] = self.get_lista_libri_cache()

        bottom_frame = ttk.Frame(self.frame_prestiti); bottom_frame.pack(side="bottom", fill="both", expand=True, padx=10, pady=5)
        list_frame = ttk.Frame(bottom_frame); list_frame.pack(side="left", fill="both", expand=True)
        chk_frame = ttk.Frame(list_frame); chk_frame.pack(fill="x", pady=2)
        ttk.Checkbutton(chk_frame, text="Mostra Storico (Restituiti)", variable=self.mostra_storico_prestiti, command=self.aggiorna_lista_prestiti).pack(side="left")
        ttk.Checkbutton(chk_frame, text="⚠️ Solo Ritardi", variable=self.filtro_solo_ritardi, command=self.aggiorna_lista_prestiti).pack(side="left", padx=15)

        cols = ("ID", "Tessera", "Utente", "Libro", "Data Preso", "Scadenza", "Restituito il")
        self.tree_prestiti = ttk.Treeview(list_frame, columns=cols, show="headings"); self.abilita_ordinamento(self.tree_prestiti, cols)
        self.tree_prestiti.heading("ID", text="ID"); self.tree_prestiti.column("ID", width=30)
        self.tree_prestiti.heading("Tessera", text="Tessera"); self.tree_prestiti.column("Tessera", width=50) 
        self.tree_prestiti.heading("Utente", text="Utente"); self.tree_prestiti.column("Utente", width=150)
        self.tree_prestiti.heading("Libro", text="Libro"); self.tree_prestiti.column("Libro", width=200)
        self.tree_prestiti.heading("Data Preso", text="Data Preso"); self.tree_prestiti.column("Data Preso", width=80)
        self.tree_prestiti.heading("Scadenza", text="Scadenza"); self.tree_prestiti.column("Scadenza", width=80)
        self.tree_prestiti.heading("Restituito il", text="Restituito"); self.tree_prestiti.column("Restituito il", width=80)
        scr = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree_prestiti.yview); self.tree_prestiti.configure(yscroll=scr.set); scr.pack(side="right", fill="y"); self.tree_prestiti.pack(side="left", expand=True, fill="both")

        btn_frame = ttk.Frame(bottom_frame); btn_frame.pack(side="right", fill="y", padx=(10, 0))
        ttk.Button(btn_frame, text="🔍 Cerca Prestito", command=self.cerca_prestiti).pack(side="top", fill="x", pady=5)
        ttk.Button(btn_frame, text="🧹 Pulisci", command=self.reset_input_prestiti).pack(side="top", fill="x", pady=5)
        ttk.Separator(btn_frame, orient="horizontal").pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="➕ Registra Prestito", command=self.registra_prestito).pack(side="top", fill="x", pady=5)
        ttk.Button(btn_frame, text="↩️ Restituisci", command=self.restituisci_libro).pack(side="top", fill="x", pady=5)
        ttk.Separator(btn_frame, orient="horizontal").pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="🖨️ Sollecito", command=self.stampa_sollecito).pack(side="top", fill="x", pady=5)
        self.aggiorna_lista_prestiti()

    def aggiorna_dropdown_utenti(self):
        self.cursor.execute("SELECT id, cognome, nome FROM utenti WHERE attivo=1 ORDER BY cognome")
        self.lista_utenti_cache = [f"{u[0]} - {u[1]} {u[2]}" for u in self.cursor.fetchall()]; self.combo_utenti['values'] = self.lista_utenti_cache
    
    def filtra_utenti_prestito(self, e): 
        v = self.combo_utenti.get(); self.combo_utenti['values'] = [u for u in self.lista_utenti_cache if v.lower() in u.lower()] if v else self.lista_utenti_cache

    def filtra_libri(self, event):
        digitato = self.entry_libro.get()
        if not digitato: self.entry_libro['values'] = self.lista_libri_cache
        else: self.entry_libro['values'] = [l for l in self.lista_libri_cache if digitato.lower() in l.lower()]

    def reset_input_prestiti(self):
        self.combo_utenti.set(''); self.entry_libro.set(''); self.aggiorna_lista_prestiti()

    def cerca_prestiti(self):
        filtro_utente = self.combo_utenti.get().strip().lower()
        filtro_libro = self.entry_libro.get().strip().lower()
        for r in self.tree_prestiti.get_children(): self.tree_prestiti.delete(r)
        q = "SELECT p.id, u.id, u.cognome || ' ' || u.nome, p.titolo_libro, p.data_inizio, p.data_scadenza, p.data_restituzione FROM prestiti p JOIN utenti u ON p.utente_id = u.id WHERE 1=1"
        if not self.mostra_storico_prestiti.get(): q += " AND p.data_restituzione IS NULL"
        params = []
        if filtro_utente:
            if " - " in filtro_utente and filtro_utente.split(" - ")[0].isdigit():
                q += " AND u.id = ?"; params.append(filtro_utente.split(" - ")[0])
            else:
                q += " AND (u.cognome LIKE ? OR u.nome LIKE ?)"; params.append(f"%{filtro_utente}%"); params.append(f"%{filtro_utente}%")
        if filtro_libro: q += " AND p.titolo_libro LIKE ?"; params.append(f"%{filtro_libro}%")
        q += " ORDER BY p.data_scadenza ASC"
        self.cursor.execute(q, params); today = datetime.now().date()
        for row in self.cursor.fetchall():
            l = list(row); l[4] = cfg.data_db_to_ita(l[4]); l[5] = cfg.data_db_to_ita(l[5]); tag = "in_corso"; rit = False
            if l[6]: l[6] = cfg.data_db_to_ita(l[6]); tag = "restituito"
            else:
                l[6] = "---"; 
                if row[5] and datetime.strptime(row[5], "%Y-%m-%d").date() < today: tag = "ritardo"; rit = True
            if self.filtro_solo_ritardi.get() and not rit: continue
            self.tree_prestiti.insert("", "end", values=l, tags=(tag,))
        self.tree_prestiti.tag_configure("restituito", foreground="gray"); self.tree_prestiti.tag_configure("ritardo", foreground="red", font=("Arial", 10, "bold"))

    def registra_prestito(self):
        op_str = self.combo_operatore_prestiti.get(); op_id = self.mappa_operatori.get(op_str)
        if not op_id: messagebox.showerror("Errore Bloccante", "Devi selezionare un Operatore di Turno per proseguire!"); return
        usr, libro = self.combo_utenti.get(), self.entry_libro.get().strip() 
        if not usr or not libro: messagebox.showerror("Error", "Dati mancanti (Utente o Libro)"); return
        try:
            uid = int(usr.split(" - ")[0]); today = datetime.now().strftime("%Y-%m-%d"); scad = (datetime.now() + timedelta(days=self.config_data.get('giorni_prestito', 30))).strftime("%Y-%m-%d")
            self.cursor.execute("INSERT INTO prestiti (utente_id, titolo_libro, data_inizio, data_scadenza, op_prestito_id) VALUES (?,?,?,?,?)", (uid, libro, today, scad, op_id)); self.conn.commit()
            self.entry_libro.set(''); self.get_lista_libri_cache(); self.entry_libro['values'] = self.lista_libri_cache
            self.aggiorna_lista_prestiti()
        except Exception as e: messagebox.showerror("Errore", str(e))

    def aggiorna_lista_prestiti(self):
        if not self.combo_utenti.get() and not self.entry_libro.get(): self.cerca_prestiti()
        else: self.cerca_prestiti()

    def restituisci_libro(self):
        if not self.tree_prestiti.selection(): return
        item = self.tree_prestiti.item(self.tree_prestiti.selection())
        if item['values'][6] != "---": messagebox.showinfo("Info", "Già restituito"); return
        op_str = self.combo_operatore_prestiti.get(); op_id = self.mappa_operatori.get(op_str)
        if not op_id: messagebox.showerror("Errore Bloccante", "Devi selezionare un Operatore di Turno per registrare la restituzione!"); return
        if messagebox.askyesno("Conferma", "Segnare come restituito?"): 
            self.cursor.execute("UPDATE prestiti SET data_restituzione=?, op_rientro_id=? WHERE id=?", (datetime.now().strftime("%Y-%m-%d"), op_id, item['values'][0])); self.conn.commit(); self.aggiorna_lista_prestiti()

    def stampa_sollecito(self):
        if not self.tree_prestiti.selection(): return
        if self.tree_prestiti.item(self.tree_prestiti.selection())['tags'][0] == "restituito": return
        pid = self.tree_prestiti.item(self.tree_prestiti.selection())['values'][0]
        self.cursor.execute("SELECT u.nome, u.cognome, u.comune, u.email, u.telefono, p.titolo_libro, p.data_scadenza FROM prestiti p JOIN utenti u ON p.utente_id = u.id WHERE p.id=?", (pid,))
        r = self.cursor.fetchone()
        if r: self.pdf_manager.crea_sollecito({'nome': r[0], 'cognome': r[1], 'comune': r[2], 'email': r[3], 'telefono': r[4], 'titolo': r[5], 'scadenza': cfg.data_db_to_ita(r[6])})

    # --- TAB STATISTICHE ---
    def setup_statistiche_tab(self):
        mf = ttk.Frame(self.frame_statistiche); mf.pack(fill="both", expand=True, padx=10, pady=10)
        hf = ttk.Frame(mf); hf.pack(fill="x", pady=(0, 15))
        ttk.Label(hf, text="Cruscotto Statistiche (Business Intelligence)", font=("Arial", 16, "bold")).pack(side="left")
        ttk.Button(hf, text="🔄 Aggiorna", command=self.aggiorna_vista_statistiche).pack(side="right", padx=5)
        ttk.Button(hf, text="🖨️ Stampa Report Completo", command=self.stampa_report_stats).pack(side="right")
        
        cf = ttk.Frame(mf); cf.pack(fill="x", pady=5)
        self.card_u = self.crea_card(cf, "Utenti Attivi", "#3498db"); self.card_u.pack(side="left", fill="x", expand=True, padx=5)
        self.card_p = self.crea_card(cf, "Totale Prestiti", "#27ae60"); self.card_p.pack(side="left", fill="x", expand=True, padx=5)
        self.card_l = self.crea_card(cf, "In Lettura", "#f39c12"); self.card_l.pack(side="left", fill="x", expand=True, padx=5)
        self.card_r = self.crea_card(cf, "In Ritardo", "#e74c3c"); self.card_r.pack(side="left", fill="x", expand=True, padx=5)

        row2 = ttk.Frame(mf); row2.pack(fill="both", expand=True, pady=15)
        f_age = ttk.LabelFrame(row2, text="👥 Demografia (Fasce d'Età)"); f_age.pack(side="left", fill="both", expand=True, padx=5)
        self.frame_age_content = ttk.Frame(f_age); self.frame_age_content.pack(fill="both", expand=True, padx=10, pady=10)
        f_trend = ttk.LabelFrame(row2, text="📈 Trend Prestiti (Ultimi 12 Mesi)"); f_trend.pack(side="right", fill="both", expand=True, padx=5)
        self.tr_trend = ttk.Treeview(f_trend, columns=("Mese", "N"), show="headings", height=5)
        self.tr_trend.heading("Mese", text="Mese"); self.tr_trend.column("Mese", width=100)
        self.tr_trend.heading("N", text="N. Prestiti"); self.tr_trend.column("N", width=80)
        self.tr_trend.pack(fill="both", expand=True)

        row3 = ttk.Frame(mf); row3.pack(fill="both", expand=True, pady=5)
        f_c = ttk.LabelFrame(row3, text="🏙️ Top Città"); f_c.pack(side="left", fill="both", expand=True, padx=5)
        self.tr_c = ttk.Treeview(f_c, columns=("Città", "N", "Pct"), show="headings", height=6)
        self.tr_c.heading("Città", text="Città"); self.tr_c.column("Città", width=120)
        self.tr_c.heading("N", text="N"); self.tr_c.column("N", width=40)
        self.tr_c.heading("Pct", text="%"); self.tr_c.column("Pct", width=50)
        self.tr_c.pack(fill="both", expand=True)
        f_l = ttk.LabelFrame(row3, text="🏆 Top Libri"); f_l.pack(side="right", fill="both", expand=True, padx=5)
        self.tr_l = ttk.Treeview(f_l, columns=("Libro", "N", "Pct"), show="headings", height=6)
        self.tr_l.heading("Libro", text="Titolo"); self.tr_l.column("Libro", width=200)
        self.tr_l.heading("N", text="N"); self.tr_l.column("N", width=40)
        self.tr_l.heading("Pct", text="%"); self.tr_l.column("Pct", width=50)
        self.tr_l.pack(fill="both", expand=True)
        self.lbl_info_extra = ttk.Label(mf, text="", font=("Arial", 9, "italic"), foreground="gray")
        self.lbl_info_extra.pack(pady=5)
        self.root.after(500, self.aggiorna_vista_statistiche)

    def crea_card(self, p, t, c):
        f = tk.Frame(p, bg=c, padx=10, pady=10)
        tk.Label(f, text=t, font=("Arial", 10, "bold"), fg="white", bg=c).pack(anchor="w")
        l = tk.Label(f, text="0", font=("Arial", 24, "bold"), fg="white", bg=c); l.pack(anchor="e")
        f.vl = l; return f

    def calcola_statistiche(self):
        stats = {}
        self.cursor.execute("SELECT COUNT(*) FROM utenti WHERE attivo=1"); stats['utenti_attivi'] = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT MIN(data_registrazione) FROM utenti WHERE attivo=1"); rd = self.cursor.fetchone()[0]
        stats['data_piu_vecchia'] = cfg.data_db_to_ita(rd) if rd else "---"
        self.cursor.execute("SELECT COUNT(*) FROM prestiti"); stats['tot_prestiti'] = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM prestiti WHERE data_restituzione IS NULL"); stats['in_lettura'] = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM prestiti WHERE data_restituzione IS NULL AND data_scadenza < ?", (datetime.now().strftime("%Y-%m-%d"),)); stats['in_ritardo'] = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT comune, COUNT(*) as c FROM utenti WHERE attivo=1 GROUP BY comune HAVING c >= 2 ORDER BY c DESC LIMIT 10")
        raw_c = self.cursor.fetchall(); tot_u = stats['utenti_attivi']; top_c_processed = []
        for c, n in raw_c: pct = (n / tot_u * 100) if tot_u > 0 else 0; top_c_processed.append((c, n, f"{pct:.1f}%"))
        stats['top_citta'] = top_c_processed

        self.cursor.execute("SELECT titolo_libro, COUNT(*) as c FROM prestiti GROUP BY titolo_libro HAVING c >= 2 ORDER BY c DESC LIMIT 10")
        raw_l = self.cursor.fetchall(); tot_p = stats['tot_prestiti']; top_l_processed = []
        for l, n in raw_l: pct = (n / tot_p * 100) if tot_p > 0 else 0; top_l_processed.append((l, n, f"{pct:.1f}%"))
        stats['top_libri'] = top_l_processed

        self.cursor.execute("SELECT strftime('%Y-%m', data_inizio) as mese, COUNT(*) FROM prestiti GROUP BY mese ORDER BY mese DESC LIMIT 12")
        stats['trend_mensile'] = self.cursor.fetchall()

        # --- FASCE D'ETA' RIVISTE ---
        self.cursor.execute("SELECT data_nascita FROM utenti WHERE attivo=1 AND data_nascita IS NOT NULL")
        raw_dates = self.cursor.fetchall()
        
        age_bins = {
            'Prima Infanzia (0-4)': 0,
            'Età Scolare (5-14)': 0,
            'Giovani e Formazione (15-24)': 0,
            'Adulti Giovani (25-44)': 0,
            'Adulti Maturi (45-64)': 0,
            'Anziani Giovani (65-79)': 0,
            'Grandi Anziani (80 anni e oltre)': 0,
            'N/D': 0
        }
        today = datetime.now()
        for row in raw_dates:
            d_str = row[0]
            if not d_str: age_bins['N/D'] += 1; continue
            try:
                born = datetime.strptime(d_str, "%Y-%m-%d")
                age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
                if age <= 4: age_bins['Prima Infanzia (0-4)'] += 1
                elif age <= 14: age_bins['Età Scolare (5-14)'] += 1
                elif age <= 24: age_bins['Giovani e Formazione (15-24)'] += 1
                elif age <= 44: age_bins['Adulti Giovani (25-44)'] += 1
                elif age <= 64: age_bins['Adulti Maturi (45-64)'] += 1
                elif age <= 79: age_bins['Anziani Giovani (65-79)'] += 1
                else: age_bins['Grandi Anziani (80 anni e oltre)'] += 1
            except: age_bins['N/D'] += 1
                
        stats['fasce_eta'] = []
        for label, count in age_bins.items():
            pct = (count / tot_u * 100) if tot_u > 0 else 0
            stats['fasce_eta'].append((label, count, pct))

        return stats

    def aggiorna_vista_statistiche(self):
        if not hasattr(self, 'lbl_info_extra') or not hasattr(self, 'card_u'): return
        stats = self.calcola_statistiche()
        
        self.card_u.vl.config(text=str(stats['utenti_attivi']))
        self.card_p.vl.config(text=str(stats['tot_prestiti']))
        self.card_l.vl.config(text=str(stats['in_lettura']))
        self.card_r.vl.config(text=str(stats['in_ritardo']))

        for r in self.tr_c.get_children(): self.tr_c.delete(r)
        for row in stats['top_citta']: self.tr_c.insert("", "end", values=row)
        for r in self.tr_l.get_children(): self.tr_l.delete(r)
        for row in stats['top_libri']: self.tr_l.insert("", "end", values=row)
        
        for r in self.tr_trend.get_children(): self.tr_trend.delete(r)
        for row in stats['trend_mensile']: self.tr_trend.insert("", "end", values=row)

        for widget in self.frame_age_content.winfo_children(): widget.destroy()
        
        for label, count, pct in stats['fasce_eta']:
            if count == 0: continue 
            row_f = ttk.Frame(self.frame_age_content)
            row_f.pack(fill="x", pady=2)
            ttk.Label(row_f, text=f"{label}: {count}", width=35, anchor="w").pack(side="left") # width aumentato a 35
            pb = ttk.Progressbar(row_f, length=100, mode='determinate', value=pct)
            pb.pack(side="left", fill="x", expand=True, padx=5)
            ttk.Label(row_f, text=f"{pct:.1f}%", width=6).pack(side="left")

        self.lbl_info_extra.config(text=f"Dati storici a partire dal: {stats['data_piu_vecchia']}")
        self.ultime_stats = stats

    def stampa_report_stats(self):
        if hasattr(self, 'ultime_stats'):
            try: self.pdf_manager.crea_report_statistico(self.ultime_stats)
            except Exception as e: messagebox.showerror("Errore Stampa", str(e))
        else: self.aggiorna_vista_statistiche(); self.stampa_report_stats()

    def setup_stampe_tab(self):
        main_frame = ttk.Frame(self.frame_stampe)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        grp_utenti = ttk.LabelFrame(main_frame, text="Report Anagrafiche")
        grp_utenti.pack(fill="x", pady=10)
        btn_attivi = ttk.Button(grp_utenti, text="👥 Stampa Utenti ATTIVI", command=lambda: self.stampa_elenco_custom("utenti_attivi"))
        btn_attivi.pack(side="left", padx=20, pady=20)
        btn_cancellati = ttk.Button(grp_utenti, text="🗑️ Stampa Utenti CANCELLATI", command=lambda: self.stampa_elenco_custom("utenti_cancellati"))
        btn_cancellati.pack(side="left", padx=20, pady=20)
        
        grp_prestiti = ttk.LabelFrame(main_frame, text="Report Movimenti")
        grp_prestiti.pack(fill="x", pady=10)
        btn_incorso = ttk.Button(grp_prestiti, text="📚 Stampa Prestiti IN CORSO", command=lambda: self.stampa_elenco_custom("prestiti_incorso"))
        btn_incorso.pack(side="left", padx=20, pady=20)
        btn_scaduti = ttk.Button(grp_prestiti, text="⚠️ Stampa Prestiti SCADUTI", command=lambda: self.stampa_elenco_custom("prestiti_scaduti"))
        btn_scaduti.pack(side="left", padx=20, pady=20)

    def stampa_elenco_custom(self, tipo):
        try:
            if tipo == "utenti_attivi":
                self.cursor.execute("SELECT id, cognome, nome, data_nascita, comune, telefono, email FROM utenti WHERE attivo=1 ORDER BY cognome")
                data = self.cursor.fetchall()
                data_fmt = []
                for row in data:
                    r = list(row); r[3] = cfg.data_db_to_ita(r[3]); data_fmt.append(r)
                headers = ["Tessera", "Cognome", "Nome", "Nascita", "Comune", "Telefono", "Email"]
                widths = [20, 40, 40, 25, 40, 35, 60]
                self.pdf_manager.crea_elenco_tabellare("ELENCO UTENTI ATTIVI", headers, data_fmt, widths)

            elif tipo == "utenti_cancellati":
                self.cursor.execute("SELECT id, cognome, nome, data_nascita, comune, telefono, email FROM utenti WHERE attivo=0 ORDER BY cognome")
                data = self.cursor.fetchall()
                data_fmt = []
                for row in data:
                    r = list(row); r[3] = cfg.data_db_to_ita(r[3]); data_fmt.append(r)
                headers = ["Tessera", "Cognome", "Nome", "Nascita", "Comune", "Telefono", "Email"]
                widths = [20, 40, 40, 25, 40, 35, 60]
                self.pdf_manager.crea_elenco_tabellare("ELENCO UTENTI ARCHIVIATI", headers, data_fmt, widths)

            elif tipo == "prestiti_incorso":
                self.cursor.execute("""SELECT p.id, u.id, u.cognome || ' ' || u.nome, p.titolo_libro, p.data_inizio, p.data_scadenza 
                                    FROM prestiti p JOIN utenti u ON p.utente_id = u.id 
                                    WHERE p.data_restituzione IS NULL ORDER BY p.data_scadenza""")
                data = self.cursor.fetchall()
                data_fmt = []
                for row in data:
                    r = list(row); r[4] = cfg.data_db_to_ita(r[4]); r[5] = cfg.data_db_to_ita(r[5]); data_fmt.append(r)
                headers = ["ID", "Tessera", "Utente", "Libro", "Data Inizio", "Scadenza"]
                widths = [10, 20, 50, 130, 25, 25] 
                self.pdf_manager.crea_elenco_tabellare("ELENCO PRESTITI IN CORSO", headers, data_fmt, widths)

            elif tipo == "prestiti_scaduti":
                oggi = datetime.now().strftime("%Y-%m-%d")
                self.cursor.execute("""SELECT p.id, u.id, u.cognome || ' ' || u.nome, p.titolo_libro, u.telefono, u.email, p.data_inizio, p.data_scadenza 
                                    FROM prestiti p JOIN utenti u ON p.utente_id = u.id 
                                    WHERE p.data_restituzione IS NULL AND p.data_scadenza < ? ORDER BY p.data_scadenza""", (oggi,))
                data = self.cursor.fetchall()
                data_fmt = []
                for row in data:
                    r = list(row)
                    r[6] = cfg.data_db_to_ita(r[6])
                    r[7] = cfg.data_db_to_ita(r[7])
                    data_fmt.append(r)
                headers = ["ID", "Tessera", "Utente", "Libro", "Tel", "Email", "Inizio", "Scadenza"]
                widths = [10, 15, 45, 60, 30, 60, 25, 25] 
                self.pdf_manager.crea_elenco_tabellare("ELENCO PRESTITI SCADUTI (Con Contatti)", headers, data_fmt, widths)

        except Exception as e:
            messagebox.showerror("Errore Generazione PDF", str(e))

    def setup_info_tab(self):
        frame = ttk.Frame(self.frame_info)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        try:
            img_path = cfg.NOME_IMMAGINE_SPLASH
            if os.path.exists(img_path):
                pil_img = Image.open(img_path)
                pil_img.thumbnail((200, 200)) 
                img = ImageTk.PhotoImage(pil_img)
                lbl_img = ttk.Label(frame, image=img)
                lbl_img.image = img 
                lbl_img.pack(pady=20)
        except Exception:
            pass

        ttk.Label(frame, text="LIU' - Letture In Uscita", font=("Arial", 16, "bold")).pack()
        ttk.Label(frame, text=f"{cfg.VERSIONE}", font=("Arial", 10)).pack()
        ttk.Label(frame, text=f"{cfg.COPYRIGHT}", font=("Arial", 10)).pack(pady=5)
        
        ttk.Label(frame, text="Note Legali / Disclaimer:", font=("Arial", 12, "bold")).pack(pady=(30, 5))
        
        text_area = scrolledtext.ScrolledText(frame, width=75, height=20, font=("Arial", 10))
        text_area.pack(pady=5)
        
        disclaimer_text = self.config_data.get('disclaimer_copyright', '')
        if not disclaimer_text or len(disclaimer_text) < 10:
            disclaimer_text = cfg.DISCLAIMER_DEFAULT
            
        text_area.insert(tk.END, disclaimer_text)
        text_area.configure(state='disabled') 

    def setup_config_tab(self): self.mostra_login_config()
    def on_tab_change(self, event):
        try: 
            idx = self.notebook.index(self.notebook.select())
            if idx == 5: self.mostra_login_config()
            else: self.config_unlocked = False
        except: pass
    def mostra_login_config(self):
        for w in self.frame_config.winfo_children(): w.destroy()
        if not self.config_unlocked:
            f = ttk.Frame(self.frame_config); f.place(relx=0.5, rely=0.5, anchor="center")
            ttk.Label(f, text="Password Admin:").pack(); self.entry_pwd = ttk.Entry(f, show="*"); self.entry_pwd.pack(pady=5); self.entry_pwd.bind("<Return>", self.verifica_password)
            ttk.Button(f, text="Login", command=self.verifica_password).pack()
        else: self.costruisci_interfaccia_config()
    def verifica_password(self, e=None):
        if self.entry_pwd.get() == self.config_data['password_admin']: self.config_unlocked = True; self.mostra_login_config()
        else: messagebox.showerror("Errore", "Password errata")
    
    def costruisci_interfaccia_config(self):
        main_frame = ttk.Frame(self.frame_config)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        left_frame = ttk.LabelFrame(main_frame, text="Parametri LIU' (Generali)")
        left_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        ttk.Label(left_frame, text="Nome Biblioteca:").pack(anchor="w", padx=5)
        self.conf_nome = ttk.Entry(left_frame, width=40)
        self.conf_nome.pack(anchor="w", padx=5, pady=2)
        ttk.Label(left_frame, text="Indirizzo:").pack(anchor="w", padx=5)
        self.conf_indirizzo = ttk.Entry(left_frame, width=40)
        self.conf_indirizzo.pack(anchor="w", padx=5, pady=2)
        ttk.Label(left_frame, text="Telefono:").pack(anchor="w", padx=5)
        self.conf_tel = ttk.Entry(left_frame, width=40)
        self.conf_tel.pack(anchor="w", padx=5, pady=2)
        ttk.Label(left_frame, text="Email:").pack(anchor="w", padx=5)
        self.conf_email = ttk.Entry(left_frame, width=40)
        self.conf_email.pack(anchor="w", padx=5, pady=2)
        ttk.Label(left_frame, text="Durata Prestito (gg):").pack(anchor="w", padx=5, pady=(10,0))
        self.conf_giorni = ttk.Entry(left_frame, width=10)
        self.conf_giorni.pack(anchor="w", padx=5, pady=2)
        ttk.Label(left_frame, text="Nuova Password Admin:").pack(anchor="w", padx=5, pady=(10,0))
        self.conf_pwd = ttk.Entry(left_frame, width=20, show="*")
        self.conf_pwd.pack(anchor="w", padx=5, pady=2)
        
        ttk.Label(left_frame, text="Testo Regolamento (per scheda iscrizione):").pack(anchor="w", padx=5, pady=(15,0))
        self.conf_regolamento = scrolledtext.ScrolledText(left_frame, width=40, height=6, font=("Arial", 9))
        self.conf_regolamento.pack(anchor="w", padx=5, pady=2)
        
        ttk.Label(left_frame, text="Disclaimer Copyright (per stampe):").pack(anchor="w", padx=5, pady=(10,0))
        self.conf_disclaimer = scrolledtext.ScrolledText(left_frame, width=40, height=4, font=("Arial", 9))
        self.conf_disclaimer.pack(anchor="w", padx=5, pady=2)
        
        ttk.Button(left_frame, text="💾 Salva Configurazione", command=self.salva_configurazione).pack(anchor="w", padx=5, pady=10)
        ttk.Button(left_frame, text="🛠️ Gestione/Bonifica Comuni", command=self.apri_gestione_comuni).pack(anchor="w", padx=5, pady=5)
        
        self.conf_nome.insert(0, self.config_data['nome_biblio'])
        self.conf_indirizzo.insert(0, self.config_data['indirizzo'])
        self.conf_tel.insert(0, self.config_data['telefono'])
        self.conf_email.insert(0, self.config_data['email'])
        self.conf_giorni.insert(0, str(self.config_data['giorni_prestito']))
        self.conf_regolamento.insert(tk.END, self.config_data['testo_regolamento'])
        
        disc_val = self.config_data.get('disclaimer_copyright', '')
        if not disc_val: disc_val = cfg.DISCLAIMER_DEFAULT
        self.conf_disclaimer.insert(tk.END, disc_val)

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=10)

        op_frame = ttk.LabelFrame(right_frame, text="Gestione Operatori")
        op_frame.pack(fill="x", pady=5)
        
        op_input_frame = ttk.Frame(op_frame)
        op_input_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(op_input_frame, text="Nome:").pack(side="left")
        self.entry_op_nome = ttk.Entry(op_input_frame, width=15)
        self.entry_op_nome.pack(side="left", padx=5)
        ttk.Label(op_input_frame, text="Cognome:").pack(side="left")
        self.entry_op_cognome = ttk.Entry(op_input_frame, width=15)
        self.entry_op_cognome.pack(side="left", padx=5)
        
        self.btn_salva_op = ttk.Button(op_input_frame, text="Aggiungi", command=self.salva_operatore)
        self.btn_salva_op.pack(side="left", padx=5)
        self.btn_annulla_op = ttk.Button(op_input_frame, text="Annulla", command=self.reset_form_operatori, state="disabled")
        self.btn_annulla_op.pack(side="left", padx=2)
        
        ttk.Checkbutton(op_frame, text="Mostra storici", variable=self.mostra_storico_operatori, command=self.aggiorna_lista_operatori).pack(anchor="w", padx=5)
        
        cols_op = ("ID", "Nome", "Cognome")
        self.tree_operatori = ttk.Treeview(op_frame, columns=cols_op, show="headings", height=10)
        for c in cols_op:
            self.tree_operatori.heading(c, text=c)
            self.tree_operatori.column(c, width=80)
        self.tree_operatori.column("ID", width=30)
        self.abilita_ordinamento(self.tree_operatori, cols_op)
        self.tree_operatori.pack(expand=True, fill="both", padx=5, pady=5)
        
        btn_box_op = ttk.Frame(op_frame)
        btn_box_op.pack(pady=5)
        ttk.Button(btn_box_op, text="✏️ Modifica", command=self.carica_operatore_per_modifica).pack(side="left", padx=5)
        self.btn_archivia_op = ttk.Button(btn_box_op, text="📦 Archivia Operatore", command=self.toggle_stato_operatore)
        self.btn_archivia_op.pack(side="left", padx=5)
        
        self.tree_operatori.bind("<<TreeviewSelect>>", self.on_operator_select)

        sec_frame = ttk.LabelFrame(right_frame, text="Area di Sicurezza (Backup)")
        sec_frame.pack(fill="x", pady=20)

        lbl_info = ttk.Label(sec_frame, text="Salva una copia di sicurezza o ripristina un vecchio database.", font=("Arial", 9, "italic"), foreground="gray")
        lbl_info.pack(pady=5)

        btn_sec_box = ttk.Frame(sec_frame)
        btn_sec_box.pack(pady=10)

        ttk.Button(btn_sec_box, text="💾 Esegui BACKUP Ora", command=self.esegui_backup).pack(side="left", padx=10)
        ttk.Button(btn_sec_box, text="⚠️ RIPRISTINA da File", command=self.esegui_ripristino).pack(side="left", padx=10)

        self.root.after(10, self.aggiorna_lista_operatori) 

    def esegui_backup(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_backup = f"{timestamp}_backup_{cfg.NOME_DB}"
            path_destinazione = os.path.join(cfg.BACKUP_DIR, nome_backup)
            
            # Copia il file del database
            shutil.copy2(cfg.NOME_DB, path_destinazione)
            
            messagebox.showinfo("Backup Riuscito", f"Backup salvato correttamente in:\n{path_destinazione}")
        except Exception as e:
            messagebox.showerror("Errore Backup", f"Impossibile eseguire il backup:\n{str(e)}")

    def esegui_ripristino(self):
        if not messagebox.askyesno("ATTENZIONE - RIPRISTINO", 
                                   "SEI SICURO?\n\nIl ripristino SOVRASCRIVERÀ i dati attuali con quelli del file selezionato.\n\nTutti i dati inseriti dopo quel backup andranno PERSI.\n\nVuoi procedere?"):
            return

        file_path = filedialog.askopenfilename(
            initialdir=cfg.BACKUP_DIR,
            title="Seleziona il file di Backup da ripristinare",
            filetypes=[("Database SQLite", "*.db"), ("Tutti i file", "*.*")]
        )

        if not file_path: return

        try:
            self.conn.close() 
            shutil.copy2(file_path, cfg.NOME_DB) 
            self.conn = sqlite3.connect(cfg.NOME_DB)
            self.cursor = self.conn.cursor()
            
            self.carica_configurazione()
            self.aggiorna_lista_operatori()
            self.aggiorna_lista_utenti()
            
            messagebox.showinfo("Ripristino Completato", "Il database è stato ripristinato con successo.\nIl programma è ora aggiornato ai dati del backup.")
            
        except Exception as e:
            try:
                self.conn = sqlite3.connect(cfg.NOME_DB)
                self.cursor = self.conn.cursor()
            except: pass
            messagebox.showerror("Errore Fatale Ripristino", f"Errore durante la copia del file:\n{str(e)}\n\nRiavviare l'applicazione.")

    def add_conf(self, p, t, v, show=None):
        ttk.Label(p, text=t).pack(anchor="w"); e = ttk.Entry(p, show=show, width=40); e.pack(anchor="w"); e.insert(0, v); return e

    def apri_gestione_comuni(self):
        GestioneComuniDialog(self.root, self.conn)

    def salva_configurazione(self):
        try:
            days = int(self.conf_giorni.get())
            pwd = self.conf_pwd.get() or self.config_data['password_admin']
            self.cursor.execute("UPDATE config SET nome_biblio=?, indirizzo=?, telefono=?, email=?, giorni_prestito=?, password_admin=?, testo_regolamento=?, disclaimer_copyright=? WHERE id=1", (self.conf_nome.get(), self.conf_indirizzo.get(), self.conf_tel.get(), self.conf_email.get(), days, pwd, self.conf_regolamento.get("1.0", tk.END).strip(), self.conf_disclaimer.get("1.0", tk.END).strip()))
            self.conn.commit(); self.carica_configurazione(); self.pdf_manager = rep.PDFManager(self.config_data); messagebox.showinfo("OK", "Salvato")
        except: messagebox.showerror("Err", "Giorni prestito deve essere numero")

    def salva_operatore(self):
        n, c = self.entry_op_nome.get(), self.entry_op_cognome.get()
        if n and c:
            if self.id_operatore_in_modifica: self.cursor.execute("UPDATE operatori SET nome=?, cognome=? WHERE id=?", (n, c, self.id_operatore_in_modifica))
            else: self.cursor.execute("INSERT INTO operatori (nome, cognome, attivo) VALUES (?, ?, 1)", (n, c))
            self.conn.commit(); self.reset_form_operatori(); self.aggiorna_lista_operatori()
            self.refresh_all_dropdowns() 
            
    def carica_operatore_per_modifica(self):
        if not self.tree_operatori.selection(): return
        v = self.tree_operatori.item(self.tree_operatori.selection())['values']; self.id_operatore_in_modifica = v[0]
        self.entry_op_nome.delete(0, tk.END); self.entry_op_nome.insert(0, v[1]); self.entry_op_cognome.delete(0, tk.END); self.entry_op_cognome.insert(0, v[2])
        self.btn_salva_op.config(text="Aggiorna"); self.btn_annulla_op.config(state="normal")
        
    def reset_form_operatori(self):
        self.id_operatore_in_modifica = None; self.entry_op_nome.delete(0, tk.END); self.entry_op_cognome.delete(0, tk.END); self.btn_salva_op.config(text="Aggiungi"); self.btn_annulla_op.config(state="disabled")
        
    def toggle_stato_operatore(self):
        if self.tree_operatori.selection():
            uid = self.tree_operatori.item(self.tree_operatori.selection())['values'][0]; s = 1 if 'archiviato' in self.tree_operatori.item(self.tree_operatori.selection())['tags'] else 0
            self.cursor.execute("UPDATE operatori SET attivo=? WHERE id=?", (s, uid)); self.conn.commit(); self.aggiorna_lista_operatori()
            self.refresh_all_dropdowns() 
            
    def aggiorna_lista_operatori(self):
        for r in self.tree_operatori.get_children(): self.tree_operatori.delete(r)
        q = "SELECT id, nome, cognome, attivo FROM operatori" + ("" if self.mostra_storico_operatori.get() else " WHERE attivo=1") + " ORDER BY cognome"
        self.cursor.execute(q)
        for r in self.cursor.fetchall(): self.tree_operatori.insert("", "end", values=r[:3], tags=("attivo" if r[3] else "archiviato",))
        self.tree_operatori.tag_configure("archiviato", foreground="gray")
        
    def on_operator_select(self, event):
        if self.tree_operatori.selection():
            tags = self.tree_operatori.item(self.tree_operatori.selection())['tags']
            self.btn_archivia_op.config(text="♻️ Ripristina" if 'archiviato' in tags else "📦 Archivia")

if __name__ == "__main__":
    show_splash_screen()
    root = tk.Tk()
    app = BibliotecaApp(root)
    root.mainloop()