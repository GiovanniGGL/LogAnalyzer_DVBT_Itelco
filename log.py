import tkinter as tk
from tkinter import ttk, messagebox
from io import StringIO
import requests
from requests.auth import HTTPBasicAuth
import pandas as pd

class LogAnalyzerApp:
    def __init__(self, root, ip_list, delta_in_secondi, event_types):
        self.root = root
        self.root.title("Analizzatore di Log Itelco DVB-T")
        icon_path = "logo.ico" 
        self.root.iconbitmap(icon_path)
        self.ip_list = ip_list
        self.delta_in_secondi = delta_in_secondi
        self.event_types = event_types
        self.ip_combinations = self.create_ip_combinations()
        self.username = "admin" 
        self.password = "system"
        self.setup_ui()

    def create_ip_combinations(self):
        ip_combinations = []
        for location, devices in self.ip_list.items():
            for device, ip in devices.items():
                ip_combinations.append(f"{location} {device}: {ip}")
        return ip_combinations

    def setup_ui(self):
        label = tk.Label(self.root, text="Seleziona un IP e il tipo di evento", padx=10, pady=10)
        label.pack()

        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=10)

        # Label e entry per la ricerca dell'IP
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.update_ip_list)  # Aggiorna la lista al cambiamento del testo
        search_label = tk.Label(input_frame, text="Cerca MUX e Location :")
        search_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        search_entry = tk.Entry(input_frame, textvariable=self.search_var, width=40)
        search_entry.grid(row=0, column=1, padx=5)

        # Menu a tendina per la selezione dell'IP 
        self.ip_combobox = ttk.Combobox(input_frame, values=self.ip_combinations, width=60)  # Usa ttk.Combobox
        self.ip_combobox.grid(row=1, column=0, columnspan=10, pady=5)
        if self.ip_combinations: #se la lista non è vuota
           self.ip_combobox.set(self.ip_combinations[0])  # Imposta un valore iniziale

        # Combobox per la selezione del delta temporale
        delta_label = tk.Label(input_frame, text="Durata minima (secondi):")
        delta_label.grid(row=2, column=0, sticky=tk.W, pady=5)
        self.delta_in_secondi_combobox = ttk.Combobox(input_frame, values=self.delta_in_secondi, width=15)
        self.delta_in_secondi_combobox.grid(row=2, column=1, sticky=tk.W, pady=5)
        self.delta_in_secondi_combobox.set(self.delta_in_secondi[0])

        # Combobox per la selezione del tipo di evento
        event_label = tk.Label(input_frame, text="Tipo di evento:")
        event_label.grid(row=3, column=0, sticky=tk.W, pady=5)
        self.event_type_combobox = ttk.Combobox(input_frame, values=list(self.event_types.keys()), width=40)
        self.event_type_combobox.grid(row=3, column=1, pady=5)
        self.event_type_combobox.set(list(self.event_types.keys())[0])

        # Pulsante per eseguire l'analisi
        request_button = tk.Button(self.root, text="Esegui richiesta", command=self.process_log_data)
        request_button.pack(pady=10)

        # Creazione della tabella Treeview 
        self.create_results_table()

    def update_ip_list(self, *args):
        #Filtra e aggiorna la lista degli IP nel Combobox in base alla ricerca
        search_term = self.search_var.get().lower()
        filtered_ips = [
          ip for ip in self.create_ip_combinations() if search_term in ip.lower()
        ]
        self.ip_combobox["values"] = filtered_ips  # Aggiorna i valori del Combobox
        if filtered_ips: # se la lista non è vuota
          self.ip_combobox.set(filtered_ips[0])
        else: #se la lista è vuota          
          self.ip_combobox.set('') #imposta il valore su una stringa vuota

    def create_results_table(self):
        #Crea la tabella Treeview per i risultati, con scrollbar e colori alternati
        # Frame per la tabella 
        self.table_frame = tk.Frame(self.root)
        self.table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Definizione delle colonne
        self.columns = ("id", "ID","Evento", "Inizio", "Durata")
        self.tree = ttk.Treeview(self.table_frame, columns=self.columns, show="headings")

        # Configurazione delle intestazioni
        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=100)

       # Definizione dei tag per i colori alternati
        self.tree.tag_configure('oddrow', background='#f0f0f0')  
        self.tree.tag_configure('evenrow', background='white')  

        # Scrollbar verticale 
        self.scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set) 

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)  
        self.tree.pack(fill=tk.BOTH, expand=True)   

    #Restituisce l'IP selezionato dal combobox
    def get_selected_ip(self):
        selected_text = self.ip_combobox.get()
        return selected_text.split(": ")[1].strip() 

    # Chiamata http
    def process_log_data(self):
        ip_address = self.ip_combobox.get()
        ip = ip_address.split(":")[1].strip()
        url = f"http://{ip}/cgi-bin/getfile.cgi?type=eventlog"
        username = "username"
        password = "password"
        try:
            response = requests.get(url, auth=HTTPBasicAuth(username, password), timeout=10) # timeout 
            if response.status_code == 200:
                raw_data = response.text
                df = self.handle_log_data(raw_data)
                self.display_results(df)
            else:
                self.show_error(f"Errore nella richiesta: {response.status_code}")
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            self.show_error(f"Errore durante la richiesta: {e}")  
        except Exception as e:
            self.show_error(f"Errore imprevisto: {e}")

    #Funzione"ponte" che esegue due operazioni principali sui dati grezzi dei log
    def handle_log_data(self, raw_data):
        df = self.razionalizza_log(raw_data)
        df_filtered = self.filtra_log(df)
        df_analysis = self.analizza(df_filtered)
        return df_analysis

    # razionalizza
    def razionalizza_log(self, response_text):
        column_names = ['ID', 'Timestamp', 'Event']
        df = pd.read_csv(StringIO(response_text), sep=',', quotechar='"', names=column_names, header=None)

        df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%Y-%m-%d, %H:%M:%S', errors='coerce')
        df.dropna(subset=['Timestamp'], inplace=True)  
        df[['EventType', 'EventStatus']] = df['Event'].str.split(', ', n=1, expand=True)
        df["EventStatus"] = df["EventStatus"].str.strip()
        return df
    
    
    # filtra
    def filtra_log(self, df):
        selected_event_type = self.event_type_combobox.get()
        if selected_event_type == "All":
             df_filtered = df
        elif selected_event_type in self.event_types:
             df_filtered =  df[df['EventType'] == selected_event_type]
        else:
           df_filtered = df
           df_filtered = df_filtered.sort_values(by=df_filtered.columns[0])  # ordino per id crescente
        return df_filtered

    # analizza
    def analizza(self, df_filtered):
        
        required_cols = ["ID", "EventType", "EventStatus", "Timestamp"]
        
        delta_seconds_threshold = int(self.delta_in_secondi_combobox.get())
        
        valid_transitions = {
            ("Fail", "Ok"),
            ("Present", "All Ok"),
            ("Missing", "Present") 
        }
        
        risultati = []  # Lista per memorizzare le transizioni valide trovate
        last_states = {}  # Dizionario per tracciare l'ultimo stato di ogni tipo di evento
        
        for row in df_filtered.itertuples():
            event_type = row.EventType
            event_status = row.EventStatus
            
            if event_type in last_states:
                last_timestamp, last_status = last_states[event_type]
                time_diff_seconds = (row.Timestamp - last_timestamp).total_seconds()
                
                if (time_diff_seconds >= delta_seconds_threshold and 
                    (last_status, event_status) in valid_transitions):
                    
                    risultati.append({
                        "ID": row.ID,
                        "Evento": event_type,
                        "Inizio": last_timestamp.strftime("%d/%m/%Y %H:%M:%S"),
                        "Durata": self._format_duration(time_diff_seconds)
                    })
            
            last_states[event_type] = (row.Timestamp, event_status)
            
        risultati.append({      # Per prevenire pd vuoti aggiungo a prescindere una riga vuota
                        "ID": "END",
                        "Evento": "END",
                        "Inizio": "END",
                        "Durata": "END"
                    })
        
        return pd.DataFrame(risultati)

    def _format_duration(self, seconds):
        # Formatta una durata in secondi in un formato leggibile
        
        seconds = max(0, int(seconds))  # Previene valori negativi
        
        if seconds < 86400:  # < 24 ore
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d {hours:02d}h"


    def display_results(self, results_df):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for index, entry in results_df.iterrows():
            self.tree.insert("", tk.END, values=(index + 1, entry['ID'], entry['Evento'], entry['Inizio'], entry['Durata']),
                             tags=('evenrow',) if (index +1) % 2 == 0 else ('oddrow',))

    def clear_results(self):
        #Pulisce la tabella dei risultati.
        for item in self.tree.get_children():
            self.tree.delete(item)

    def show_error(self, message):
        messagebox.showerror("Errore", message)
        
if __name__ == "__main__":
    
    # Lista degli eventi
    event_types = {
    "All": {},
    "TS Secondary Sync Loss": {"Fail", "Ok"},
    "TS Primary MIP Data": {"Missing", "Present"},
    "TS Secondary MIP Data": {"Missing", "Present"},
    "TS Primary Sync Loss":  {"Fail", "Ok"},
    "TS Primary Transport Stream ID":  {"Fail", "Ok"},
    "TS Secondary Transport Stream ID":  {"Fail", "Ok"},
    "ASI Alarms": {"Present", "All Ok"},
    "subMute Off":  {"Modulator Resync", "No TS Lock"}, 
    "subMute On":  {"Modulator Resync", "No TS Lock"}, 
    "TS Primary Network ID": {"Fail", "Ok"},
    "TS Secondary Network ID": {"Fail", "Ok"},
    "SFN Resync Error": {"Fail", "Ok"},
    "SFN Alarms": {"Present", "All Ok"},
    "RF Alarms":  {"Present", "All Ok"},
    "HPA Warning": {"Fail", "Ok"},
    "HPA Reflected": {"Fail", "Ok"},
    "HPA RF Absent": {"Fail", "Ok"},
    "HPA Fault": {"Fail", "Ok"},
    "TSoIP Alarms": {"Present", "All Ok"},
    "TSoIP RX1 Package Error Ratio": {"Fail", "Ok"},
    "TSoIP RX2 Package Error Ratio": {"Fail", "Ok"},
    "TSoIP RX1 Signal": {"Fail", "Ok"},
    "TSoIP RX2 Signal": {"Fail", "Ok"}
}

    delta_in_secondi = [1, 15, 30, 60]

    ip_list= {
            "site1": {},
            "site2": {},
            "site3": {},
    }
    
# APP INDEX  
root = tk.Tk()
app = LogAnalyzerApp(root, ip_list, delta_in_secondi, event_types)
root.geometry("900x500")
root.mainloop()


