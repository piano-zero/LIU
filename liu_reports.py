import os
import platform
import subprocess
from fpdf import FPDF
from datetime import datetime
import liu_config as cfg

class PDFManager:
    def __init__(self, config_data):
        self.conf = config_data

    def salva_e_apri(self, pdf_obj, nome_file_base):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_finale = f"{timestamp}_{nome_file_base}"
        full_path = os.path.join(cfg.PDF_DIR, nome_finale)
        try:
            pdf_obj.output(full_path)
            self.apri_file(full_path)
        except PermissionError:
            alt_name = f"COPY_{nome_finale}"
            full_path = os.path.join(cfg.PDF_DIR, alt_name)
            pdf_obj.output(full_path)
            self.apri_file(full_path)
        except Exception as e:
            print(f"Errore nel salvataggio PDF: {e}")

    def apri_file(self, percorso_file):
        if platform.system() == 'Darwin': subprocess.call(('open', percorso_file))
        elif platform.system() == 'Windows': os.startfile(percorso_file)
        else: subprocess.call(('xdg-open', percorso_file))

    def pulisci_testo(self, testo):
        if not testo: return ""
        if not isinstance(testo, str): testo = str(testo)
        mappa = {"’": "'", "“": '"', "”": '"', "–": "-", "€": "EUR"}
        for k, v in mappa.items(): testo = testo.replace(k, v)
        return testo.encode('latin-1', 'replace').decode('latin-1')

    # REPORT 1: SCHEDA UTENTE
    def crea_scheda_iscrizione(self, utente, regolamento):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, self.pulisci_testo(f"{self.conf.get('nome_biblio', 'Biblioteca')}"), ln=True, align='C')
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 5, self.pulisci_testo(f"{self.conf.get('indirizzo', '')} - {self.conf.get('email', '')}"), ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "SCHEDA DI ISCRIZIONE E ACCETTAZIONE REGOLAMENTO", ln=True, align='C')
        pdf.ln(5)
        pdf.set_font("Arial", '', 11)
        campi = [f"Tessera N.: {utente[0]}", f"Cognome e Nome: {utente[3]} {utente[2]}", f"Nato il: {utente[4]}",
            f"Residente a: {utente[5]}", f"Documento: {utente[6]}", f"Email: {utente[7]}", f"Telefono: {utente[8]}"]
        for riga in campi: pdf.cell(0, 8, self.pulisci_testo(riga), ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 10, "DICHIARAZIONE DI ACCETTAZIONE", ln=True)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 5, self.pulisci_testo(regolamento))
        pdf.ln(10)
        pdf.set_font("Arial", '', 10)
        pdf.cell(90, 10, "Data: " + datetime.now().strftime("%d/%m/%Y"), ln=0)
        pdf.cell(0, 10, "Firma dell'Utente", ln=1, align='R')
        pdf.ln(10)
        pdf.cell(0, 10, "."*50, ln=1, align='R')
        self.salva_e_apri(pdf, f"Scheda_{utente[0]}_{utente[3]}.pdf")

    # REPORT 2: SOLLECITO
    def crea_sollecito(self, dati):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, self.pulisci_testo(f"{self.conf.get('nome_biblio', 'Biblioteca')}"), ln=True, align='C')
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 5, self.pulisci_testo(f"{self.conf.get('indirizzo', '')}"), ln=True, align='C')
        pdf.ln(15)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "Spett.le Utente:", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 6, self.pulisci_testo(f"{dati['nome']} {dati['cognome']}"), ln=True)
        pdf.cell(0, 6, self.pulisci_testo(f"Residente a: {dati['comune']}"), ln=True)
        pdf.ln(5)
        pdf.set_fill_color(240, 240, 240)
        pdf.rect(10, pdf.get_y(), 190, 20, 'F')
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 6, "DATI DI CONTATTO UTENTE (Uso interno):", ln=True)
        pdf.set_font("Arial", '', 10)
        contatti = f"Tel: {dati['telefono']}  -  Email: {dati['email']}"
        pdf.cell(0, 6, self.pulisci_testo(contatti), ln=True)
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"OGGETTO: Sollecito restituzione prestito scaduto", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", '', 11)
        testo = f"""Gentile utente,\n\ndai nostri registri risulta che il prestito del libro:\n\n"{dati['titolo']}"\n\nera in scadenza il {dati['scadenza']} e non risulta ancora restituito.\n\nLa preghiamo di provvedere alla restituzione quanto prima o di contattarci per un eventuale rinnovo.\n\nCordiali saluti,\nLa Direzione"""
        pdf.multi_cell(0, 7, self.pulisci_testo(testo))
        self.salva_e_apri(pdf, f"Sollecito_{dati['cognome']}_{dati['nome']}.pdf")

    # REPORT 3: STATISTICHE COMPLETO
    def crea_report_statistico(self, stats):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "REPORT STATISTICO LIU'", ln=True, align='C')
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 10, f"Generato il: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
        pdf.ln(10)
        
        # 1. RIEPILOGO
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "1. RIEPILOGO GENERALE", ln=True, fill=True)
        pdf.ln(2)
        pdf.set_font("Arial", '', 11)
        pdf.cell(90, 10, f"Utenti Attivi: {stats['utenti_attivi']}", ln=0)
        pdf.cell(0, 10, f"Iscrizioni dal: {stats['data_piu_vecchia']}", ln=1)
        pdf.cell(90, 10, f"Totale Prestiti (Storico): {stats['tot_prestiti']}", ln=0)
        pdf.cell(0, 10, f"Libri attualmente in lettura: {stats['in_lettura']}", ln=1)
        pdf.set_text_color(200, 0, 0)
        pdf.cell(0, 10, f"Prestiti SCADUTI (Ritardi): {stats['in_ritardo']}", ln=1)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)

        # 2. DEMOGRAFIA
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "2. ANALISI DEMOGRAFICA", ln=True, fill=True)
        pdf.ln(2)
        pdf.set_font("Arial", '', 10)
        for label, count, pct in stats['fasce_eta']:
            if count > 0:
                # Disegno una barra "finta" con pipe |
                bar_len = int(pct / 2)
                bar_str = "|" * bar_len
                pdf.cell(0, 6, f"{label}: {count} ({pct:.1f}%) {bar_str}", ln=True)
        pdf.ln(5)

        # 3. TREND MENSILE
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "3. TREND MENSILE (Ultimi 12 mesi)", ln=True, fill=True)
        pdf.ln(2)
        pdf.set_font("Arial", '', 10)
        # Tabella semplice
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(40, 7, "Mese", 1, 0, 'C', True)
        pdf.cell(30, 7, "Prestiti", 1, 1, 'C', True)
        for mese, count in stats['trend_mensile']:
            pdf.cell(40, 6, mese, 1)
            pdf.cell(30, 6, str(count), 1, 1, 'C')
        pdf.ln(5)

        # 4. TOP CITTA E LIBRI
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(90, 10, "4. CLASSIFICA CITTA'", ln=0, fill=True)
        pdf.cell(5)
        pdf.cell(0, 10, "5. CLASSIFICA LIBRI", ln=1, fill=True)
        
        pdf.set_font("Arial", '', 9)
        max_rows = max(len(stats['top_citta']), len(stats['top_libri']))
        for i in range(max_rows):
            # Colonna Città
            if i < len(stats['top_citta']):
                c = stats['top_citta'][i]
                txt_citta = self.pulisci_testo(f"{i+1}. {c[0]} ({c[1]} - {c[2]})")
            else: txt_citta = ""
            
            # Colonna Libri
            if i < len(stats['top_libri']):
                l = stats['top_libri'][i]
                libro_tit = l[0]
                if len(libro_tit) > 30: libro_tit = libro_tit[:27] + "..."
                txt_libro = self.pulisci_testo(f"{i+1}. {libro_tit} ({l[1]} - {l[2]})")
            else: txt_libro = ""
            
            pdf.cell(90, 6, txt_citta, ln=0)
            pdf.cell(5)
            pdf.cell(0, 6, txt_libro, ln=1)
            
        self.salva_e_apri(pdf, "Report_Statistiche.pdf")

    # REPORT 4: ELENCHI TABELLARI
    def crea_elenco_tabellare(self, titolo, headers, data, col_widths):
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, self.pulisci_testo(f"{self.conf.get('nome_biblio', 'Biblioteca')}"), ln=True)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, self.pulisci_testo(titolo), ln=True)
        pdf.set_font("Arial", '', 9)
        pdf.cell(0, 5, f"Data stampa: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
        pdf.ln(5)
        
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(200, 200, 200)
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 8, self.pulisci_testo(header), border=1, fill=True)
        pdf.ln()
        
        pdf.set_font("Arial", '', 9)
        for idx, row in enumerate(data):
            if idx % 2 == 0:
                pdf.set_fill_color(245, 245, 245)
                fill_row = True
            else:
                fill_row = False

            for i, item in enumerate(row):
                txt = self.pulisci_testo(str(item))
                max_w = col_widths[i] - 2 
                if pdf.get_string_width(txt) > max_w:
                    while pdf.get_string_width(txt + "..") > max_w and len(txt) > 0:
                        txt = txt[:-1]
                    txt += ".."
                pdf.cell(col_widths[i], 7, txt, border=1, fill=fill_row)
            pdf.ln()
            
        self.salva_e_apri(pdf, f"Elenco_{titolo.replace(' ', '_')}.pdf")