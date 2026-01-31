import sys
import os
import re
from datetime import datetime

# --- FUNZIONI DI UTILITA' ---
def resource_path(relative_path):
    """Trova il percorso assoluto delle risorse (utile per PyInstaller)"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def data_ita_to_db(data_ita): 
    """Converte gg/mm/aaaa in YYYY-MM-DD"""
    return None if not data_ita else datetime.strptime(data_ita, "%d/%m/%Y").strftime("%Y-%m-%d")

def data_db_to_ita(data_db): 
    """Converte YYYY-MM-DD in gg/mm/aaaa"""
    if not data_db or data_db == 'None': return ""
    try: return datetime.strptime(data_db.split(" ")[0], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError: return data_db

def valida_email(email): 
    return True if not email else re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email) is not None

def valida_telefono(telefono): 
    return True if not telefono else re.match(r"^\+?[0-9\s]+$", telefono) is not None

# --- GESTIONE CARTELLE ---
def get_external_folder(folder_name):
    """
    Crea una cartella un livello sopra la cartella dello script.
    Serve per tenere PDF e BACKUP fuori dalla cartella dell'eseguibile.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    folder = os.path.join(parent_dir, folder_name)
    
    if not os.path.exists(folder):
        try:
            os.makedirs(folder)
        except OSError:
            # Fallback nella cartella corrente se non ci sono permessi
            folder = os.path.join(script_dir, folder_name)
            if not os.path.exists(folder):
                os.makedirs(folder)
    return folder

# --- COSTANTI ---
NOME_DB = "liu_basedati.db"
NOME_IMMAGINE_SPLASH = resource_path("liu-logo.png")

# Percorsi calcolati dinamicamente
PDF_DIR = get_external_folder("LIU_PDF") 
BACKUP_DIR = get_external_folder("LIU_BACKUP")

VERSIONE = "LIU' v34.0 (Admin Tuning)"
COPYRIGHT = "Liberata (Giorgia) De Novellis 2025-2026"

DISCLAIMER_DEFAULT = """Guida, Note Legali e Contatti

1. Scopo del Software
LIU' (Letture In Uscita) è stato progettato per semplificare la gestione bibliotecaria.

2. Esclusione di Responsabilità (Disclaimer)
Questo software è fornito "così com'è" (as is), senza garanzie esplicite o implicite.

3. Sicurezza dei Dati
I dati sono salvati localmente. Si raccomanda il backup periodico.

Contatti: giorgia.denovellis@gmail.com
© 2025-2026 Liberata (Giorgia) De Novellis"""

COMUNI_SALERNO = [
    "Acerno", "Agropoli", "Albanella", "Alfano", "Altavilla Silentina", "Amalfi", "Angri", "Aquara", "Ascea", "Atena Lucana", "Atrani", "Auletta",
    "Baronissi", "Battipaglia", "Bellizzi", "Bellosguardo", "Bracigliano", "Buccino", "Buonabitacolo", "Caggiano", "Calvanico", "Camerota", "Campagna", 
    "Campora", "Cannalonga", "Capaccio Paestum", "Casal Velino", "Casalbuono", "Casaletto Spartano", "Caselle in Pittari", "Castel San Giorgio", 
    "Castel San Lorenzo", "Castelcivita", "Castellabate", "Castelnuovo Cilento", "Castelnuovo di Conza", "Castiglione del Genovesi", "Cava de' Tirreni",
    "Celle di Bulgheria", "Centola", "Ceraso", "Cetara", "Cicerale", "Colliano", "Conca dei Marini", "Controne", "Contursi Terme", "Corbara", 
    "Corleto Monforte", "Cuccaro Vetere", "Eboli", "Felitto", "Fisciano", "Furore", "Futani", "Giffoni Sei Casali", "Giffoni Valle Piana", "Gioi", 
    "Giungano", "Ispani", "Laureana Cilento", "Laurino", "Laurito", "Laviano", "Lustra", "Magliano Vetere", "Maiori", "Mercato San Severino", "Minori", 
    "Moio della Civitella", "Montano Antilia", "Monte San Giacomo", "Montecorice", "Montecorvino Pugliano", "Montecorvino Rovella", "Monteforte Cilento", 
    "Montesano sulla Marcellana", "Morigerati", "Nocera Inferiore", "Nocera Superiore", "Novi Velia", "Ogliastro Cilento", "Olevano sul Tusciano", 
    "Oliveto Citra", "Omignano", "Orria", "Ottati", "Padula", "Pagani", "Palomonte", "Pellezzano", "Perdifumo", "Perito", "Pertosa", "Petina", 
    "Piaggine", "Pisciotta", "Polla", "Pollica", "Pontecagnano Faiano", "Positano", "Postiglione", "Praiano", "Prignano Cilento", "Ravello", "Ricigliano", 
    "Roccadaspide", "Roccagloriosa", "Roccapiemonte", "Rofrano", "Romagnano al Monte", "Roscigno", "Rutino", "Sacco", "Sala Consilina", "Salento", 
    "Salerno", "Salvitelle", "San Cipriano Picentino", "San Giovanni a Piro", "San Gregorio Magno", "San Mango Piemonte", "San Marzano sul Sarno", 
    "San Mauro Cilento", "San Mauro la Bruca", "San Pietro al Tanagro", "San Rufo", "San Valentino Torio", "Santa Marina", "Sant'Angelo a Fasanella", 
    "Sant'Arsenio", "Sant'Egidio del Monte Albino", "Santomenna", "Sanza", "Sapri", "Sarno", "Sassano", "Scafati", "Scala", "Serramezzana", "Serre", 
    "Sessa Cilento", "Siano", "Sicignano degli Alburni", "Stella Cilento", "Stio", "Teggiano", "Torchiara", "Torraca", "Torre Orsaia", "Tortorella", 
    "Tramonti", "Trentinara", "Valle dell'Angelo", "Vallo della Lucania", "Valva", "Vibonati", "Vietri sul Mare"
]