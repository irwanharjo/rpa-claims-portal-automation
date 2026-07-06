import os
import time
import re
import tkinter as tk
from tkinter import messagebox
import pandas as pd
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

load_dotenv()

PORTAL_URL = os.environ.get("PORTAL_BASE_URL", "https://your-claims-portal.example.com")
PORTAL_USERNAME = os.environ.get("PORTAL_USERNAME")
PORTAL_PASSWORD = os.environ.get("PORTAL_PASSWORD")

# Illustrative client/entity map — replace with your own portal's structure.
# Keys are short internal codes extracted from the source spreadsheet; values
# are the display name the web portal expects when filtering/creating a claim.
ENTITY_CODE_MAP = {
    'CLIENT_A': ['E01AAA', 'E01AAB', 'E01AAC', 'E01AAD', 'E01AAE'],
    'CLIENT_B': ['E01BBB', 'E01BBC', 'E01BBD', 'E01BBE', 'E01BBF'],
    'CLIENT_C': ['E01CCC', 'E01CCD'],
    'CLIENT_D': ['E01DDD'],
    'CLIENT_E': ['E01EEE'],
    'CLIENT_F': ['E01FFF'],
    'CLIENT_G': ['E01GGG'],
    'CLIENT_H': ['E01HHH'],
}
DEFAULT_ENTITY = 'CLIENT_A'
PISA_CATEGORY_CODES = ['E01AAA', 'E01DDD', 'E01CCC', 'E01EEE', 'E01FFF', 'E0CCCC', 'E0CAAA', 'E01GGG', 'E01BBB', 'E01HHH']


class RobotClaimsPortalAutomation:
    def __init__(self, root):
        self.root = root
        self.root.title("Claims Portal Automation [V4.1 STABLE]")

        # --- HUD STYLING ---
        window_width = 420
        window_height = 280
        screen_width = self.root.winfo_screenwidth()
        x_coordinate = screen_width - window_width - 20
        y_coordinate = 20
        self.root.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")

        self.root.attributes('-topmost', True)

        self.bg_color = "#0B0C10"
        self.fg_neon = "#66FCF1"
        self.fg_accent = "#45A29E"
        self.fg_text = "#C5C6C7"
        self.fg_alert = "#FF4C4C"
        self.fg_warn = "#F2A900"

        self.root.configure(bg=self.bg_color)

        self.folder_siap = "Siap_Input"
        self.folder_selesai = "Selesai_Input"
        self.setup_folders()
        self.current_file = None
        self.driver = None

        self.font_header = ("Consolas", 11, "bold")
        self.font_title = ("Consolas", 10, "bold")
        self.font_text = ("Consolas", 9)

        self.lbl_greeting = tk.Label(root, text="WELCOME BACK, OPERATOR.\nALL SYSTEMS ONLINE.",
                                     font=self.font_header, bg=self.bg_color, fg=self.fg_neon)
        self.lbl_greeting.pack(pady=(15, 5))

        self.lbl_status = tk.Label(root, text="SYSTEM STANDBY: Awaiting command.",
                                   font=self.font_title, bg=self.bg_color, fg=self.fg_text)
        self.lbl_status.pack(pady=10)

        self.lbl_file = tk.Label(root, text="TARGET DATA: None",
                                 font=self.font_text, bg=self.bg_color, fg=self.fg_accent)
        self.lbl_file.pack(pady=5)

        self.btn_mulai = tk.Button(root, text="[ INITIALIZE AUTOMATION ]", font=self.font_title,
                                   bg="#1F2833", fg=self.fg_neon, activebackground=self.fg_neon, activeforeground="#1F2833",
                                   relief="ridge", bd=2, cursor="hand2", command=self.mulai_proses)
        self.btn_mulai.pack(pady=8, fill='x', padx=40, ipady=3)

        self.btn_lanjut = tk.Button(root, text="[ PROCEED TO NEXT TARGET ]", font=self.font_title,
                                    bg="#1F2833", fg=self.fg_warn, activebackground=self.fg_warn, activeforeground="#1F2833",
                                    state="disabled", relief="ridge", bd=2, cursor="hand2", command=self.lanjut_file)
        self.btn_lanjut.pack(pady=5, fill='x', padx=40, ipady=3)

    def setup_folders(self):
        if not os.path.exists(self.folder_siap): os.makedirs(self.folder_siap)
        if not os.path.exists(self.folder_selesai): os.makedirs(self.folder_selesai)

    def get_next_excel(self):
        files = [f for f in os.listdir(self.folder_siap) if f.endswith(('.xlsx', '.csv'))]
        return files[0] if files else None

    def force_click(self, element):
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.1)
        self.driver.execute_script("arguments[0].click();", element)

    def ekstrak_tanggal_dari_pdf(self, path_pdf):
        try:
            import pdfplumber
            with pdfplumber.open(path_pdf) as pdf:
                teks_halaman = pdf.pages[0].extract_text()
                match = re.search(r'Jakarta[,\.\s]*(\d{2})\s*[-/]\s*(\d{2})\s*[-/]\s*(\d{4})', teks_halaman, re.IGNORECASE)
                if match:
                    return f"{match.group(1)}{match.group(2)}{match.group(3)}"

                kumpulan_tanggal = re.findall(r'(\d{2})\s*[-/]\s*(\d{2})\s*[-/]\s*(\d{4})', teks_halaman)
                if kumpulan_tanggal:
                    tgl, bln, thn = kumpulan_tanggal[0]
                    return f"{tgl}{bln}{thn}"
        except ImportError:
            print("WARNING: pdfplumber missing.")
            return ""
        except Exception as e:
            print(f"PDF Extraction Failed: {e}")
            return ""
        return ""

    def minta_tanggal_manual(self, tebakan_tanggal=""):
        dialog = tk.Toplevel(self.root)
        dialog.title("MANUAL OVERRIDE")

        w = 380
        h = 170
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        dialog.geometry('%dx%d+%d+%d' % (w, h, x, y))

        dialog.configure(bg=self.bg_color)
        dialog.attributes('-topmost', True)
        dialog.grab_set()

        lbl_info = tk.Label(dialog, text="REQUIRE HUMAN INTERVENTION\nPlease insert the invoice date here:",
                            font=self.font_text, bg=self.bg_color, fg=self.fg_warn)
        lbl_info.pack(pady=(15, 10))

        tebakan_bersih = re.sub(r'\D', '', tebakan_tanggal)

        entry_var = tk.StringVar(value=tebakan_bersih)
        entry = tk.Entry(dialog, textvariable=entry_var, font=("Consolas", 14, "bold"),
                         bg="#1F2833", fg=self.fg_neon, justify='center', bd=1, relief="ridge")
        entry.pack(pady=5, ipadx=10, ipady=3)
        entry.focus()

        hasil = {"tanggal": None}

        def submit(event=None):
            val = entry_var.get().strip()
            angka_saja = re.sub(r'\D', '', val)

            if len(angka_saja) == 8:
                val_final = f"{angka_saja[:2]}-{angka_saja[2:4]}-{angka_saja[4:]}"
            else:
                val_final = val

            if val_final:
                hasil["tanggal"] = val_final
                dialog.destroy()
            else:
                messagebox.showwarning("WARNING", "Input cannot be empty.", parent=dialog)

        dialog.bind('<Return>', submit)

        btn_submit = tk.Button(dialog, text="[ CONFIRM & RESUME ]", font=self.font_title,
                               bg="#1F2833", fg=self.fg_neon, activebackground=self.fg_neon, activeforeground="#1F2833",
                               relief="ridge", bd=2, cursor="hand2", command=submit)
        btn_submit.pack(pady=10, fill='x', padx=50)

        self.root.wait_window(dialog)
        return hasil["tanggal"]

    def ketik_ninja(self, teks):
        self.driver.switch_to.active_element.send_keys(teks)
        time.sleep(0.05)

    def aksi_ninja(self, tombol):
        self.driver.switch_to.active_element.send_keys(tombol)
        time.sleep(0.05)

    def format_uang_web(self, val):
        val = round(val, 2)
        if val.is_integer():
            return "{:,}".format(int(val)).replace(',', '.')
        else:
            s = str(val)
            if '.' in s:
                int_p, dec_p = s.split('.')
                int_f = "{:,}".format(int(int_p)).replace(',', '.')
                return f"{int_f},{dec_p}"
            return "{:,}".format(int(val)).replace(',', '.')

    def bersihkan_nama(self, nama):
        if pd.isna(nama):
            return ""
        nama_str = str(nama).upper().strip()
        nama_str = re.sub(r'^FX[\.\s]*', '', nama_str)
        nama_str = re.sub(r'[\s,\.]+(TN|NY|NN|AN|BY)\b', '', nama_str)
        nama_str = re.sub(r'^[^A-Z0-9]+|[^A-Z0-9]+$', '', nama_str)
        return nama_str.strip()

    def mulai_proses(self):
        self.btn_mulai.config(state="disabled")
        if not PORTAL_USERNAME or not PORTAL_PASSWORD:
            messagebox.showerror("SYSTEM ERROR", "PORTAL_USERNAME / PORTAL_PASSWORD not set in .env")
            self.btn_mulai.config(state="normal")
            return

        self.lbl_status.config(text="STATUS: Booting WebDriver Protocol...", fg=self.fg_neon)
        self.root.update()

        if not self.driver:
            chrome_options = Options()
            chrome_options.add_argument("--disable-popup-blocking")
            prefs = {
                "profile.default_content_setting_values.notifications": 1,
                "profile.default_content_setting_values.geolocation": 1,
                "profile.default_content_setting_values.media_stream_mic": 1,
                "profile.default_content_setting_values.media_stream_camera": 1,
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False
            }
            chrome_options.add_experimental_option("prefs", prefs)
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.maximize_window()

        self.jalankan_login_otomatis(PORTAL_USERNAME, PORTAL_PASSWORD)

    def jalankan_login_otomatis(self, username, password):
        self.lbl_status.config(text="STATUS: Bypassing Security (Login)...", fg=self.fg_neon)
        self.root.update()
        self.driver.get(f"{PORTAL_URL}/auth/sign-in")
        try:
            wait = WebDriverWait(self.driver, 15)
            user_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text' or contains(@placeholder, 'Username')]")))
            user_field.clear()
            user_field.send_keys(username)

            pass_field = self.driver.find_element(By.XPATH, "//input[@type='password' or contains(@placeholder, 'Sandi')]")
            pass_field.clear()
            pass_field.send_keys(password)

            btn_login = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            self.force_click(btn_login)
            time.sleep(3)
        except Exception as e:
            messagebox.showerror("LOGIN FAILED", f"Authentication Error:\n{e}")
            self.lbl_status.config(text="STATUS: Access Denied!", fg=self.fg_alert)
            self.btn_mulai.config(state="normal")
            return

        self.eksekusi_file()

    def ekstrak_kode_pelanggan(self, df_raw):
        try:
            df_top = df_raw.head(20)
            teks_gabungan = " ".join([str(val).upper().replace('\n', ' ').replace('\r', ' ') for val in df_top.values.flatten() if pd.notna(val)])

            match_kode = re.search(r'\b(E01[A-Z0-9]{3}|E0C[A-Z0-9]{3}|E00[A-Z0-9]{3})\b', teks_gabungan)
            if match_kode: return match_kode.group(1).strip()

            # Fallback: infer entity from free-text keywords when no explicit code is present.
            if "CLIENT C KEYWORD" in teks_gabungan: return "E01CCC"
            if "CLIENT B KEYWORD" in teks_gabungan: return "E01BBB"
            if "CLIENT E KEYWORD" in teks_gabungan: return "E01EEE"
            if "CLIENT D KEYWORD" in teks_gabungan: return "E01DDD"
            if "CLIENT G KEYWORD" in teks_gabungan: return "E01GGG"
            if "CLIENT F KEYWORD" in teks_gabungan: return "E01FFF"
            if "CLIENT H KEYWORD" in teks_gabungan: return "E01HHH"
            if "CLIENT A KEYWORD" in teks_gabungan: return "E01AAA"

            return "E01AAA"
        except Exception:
            return "E01AAA"

    def tentukan_kategori(self, kode):
        return "PISA" if kode in PISA_CATEGORY_CODES else "Pensiunan"

    def tentukan_entitas(self, kode):
        for entitas, list_kode in ENTITY_CODE_MAP.items():
            if kode in list_kode: return entitas
        return DEFAULT_ENTITY

    def eksekusi_file(self):
        file_excel = self.get_next_excel()
        if not file_excel:
            self.lbl_status.config(text="STATUS: Mission Accomplished. Queue Empty.", fg=self.fg_text)
            self.lbl_file.config(text="TARGET DATA: None")
            self.btn_lanjut.config(state="disabled")
            messagebox.showinfo("PROTOCOL COMPLETE", "All files have been successfully processed.")
            return

        self.current_file = file_excel
        self.lbl_status.config(text="STATUS: Parsing Target Matrix (Excel)...", fg=self.fg_neon)
        self.lbl_file.config(text=f"TARGET DATA: {self.current_file}")
        self.root.update()

        file_path = os.path.join(self.folder_siap, self.current_file)
        nomor_inv_murni = self.current_file.replace('.xlsx', '').replace('.csv', '')
        path_pdf = os.path.join(self.folder_siap, f"{nomor_inv_murni}.pdf")

        with open(file_path, 'rb') as f:
            dict_df = pd.read_excel(f, sheet_name=None, header=None)

        df_mentah_pertama = list(dict_df.values())[0]

        kode_pelanggan = self.ekstrak_kode_pelanggan(df_mentah_pertama)
        jenis_pisa = self.tentukan_kategori(kode_pelanggan)
        nama_entitas = self.tentukan_entitas(kode_pelanggan)

        teks_mcu = " ".join([str(val).upper().replace('\n', ' ').replace('\r', ' ') for val in df_mentah_pertama.head(20).values.flatten() if pd.notna(val)])
        is_mcu = "MEDICAL CHECK UP" in teks_mcu or "MCU" in teks_mcu
        jenis_layanan = "Medical Check Up" if is_mcu else "Rawat Jalan Tingkat Pertama"

        df_list = []
        for sheet_name, df_sheet in dict_df.items():
            header_idx = 0
            for i in range(min(25, len(df_sheet))):
                row_str = " ".join([str(val).lower() for val in df_sheet.iloc[i].values if pd.notna(val)])
                if "nama pasien" in row_str or "pegawai" in row_str or "jaminan" in row_str:
                    header_idx = i
                    break

            df_sheet.columns = df_sheet.iloc[header_idx]
            df_sheet = df_sheet.iloc[header_idx+1:].reset_index(drop=True)
            df_list.append(df_sheet)

        df_gabungan = pd.concat(df_list, ignore_index=True)

        kolom_target = None
        kolom_tgl = None
        kolom_nama = None
        kolom_no = None
        kolom_total = None

        for col in df_gabungan.columns:
            col_lower = str(col).lower().strip()
            if "peg" in col_lower or "jaminan" in col_lower:
                kolom_target = col
            if "tgl" in col_lower or "tanggal" in col_lower:
                kolom_tgl = col
            if "nama" in col_lower and ("pasien" in col_lower or "peserta" in col_lower):
                kolom_nama = col
            if col_lower == "no" or col_lower == "no.":
                kolom_no = col
            if col_lower == "total" or col_lower == "tagihan":
                kolom_total = col

        if not kolom_target or not kolom_tgl or not kolom_nama or not kolom_total:
            messagebox.showerror("SYSTEM ERROR", "Required fields missing in data matrix.")
            self.lbl_status.config(text="STATUS: Matrix Extraction Failed!", fg=self.fg_alert)
            self.btn_lanjut.config(state="normal")
            return

        try:
            self.lbl_status.config(text=f"STATUS: Injecting Entity [{nama_entitas}]...", fg=self.fg_neon)
            self.root.update()
            self.driver.get(f"{PORTAL_URL}/claim-submissions")

            wait = WebDriverWait(self.driver, 20)
            search_box_awal = wait.until(EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'Search') or contains(@placeholder, 'search')]")))

            baris_utama = search_box_awal.find_element(By.XPATH, "./../..")

            def ketik_ke_dropdown(urutan_kotak, teks_tujuan):
                try:
                    input_asli = baris_utama.find_element(By.XPATH, f"./div[{urutan_kotak}]//input")
                    self.driver.execute_script("arguments[0].focus();", input_asli)
                    input_asli.send_keys(Keys.CONTROL + "a", Keys.BACKSPACE)
                    time.sleep(0.1)
                    input_asli.send_keys(str(teks_tujuan))
                    time.sleep(1.0)
                    input_asli.send_keys(Keys.ARROW_DOWN)
                    input_asli.send_keys(Keys.ENTER)
                except Exception:
                    pass

            ketik_ke_dropdown(1, jenis_pisa)
            ketik_ke_dropdown(2, nama_entitas)
            ketik_ke_dropdown(4, jenis_layanan)

            try:
                search_box_limit = self.driver.find_element(By.XPATH, "//input[contains(@placeholder, 'Search') or contains(@placeholder, 'search')]")
                self.driver.execute_script("arguments[0].focus();", search_box_limit)
                search_box_limit.send_keys(Keys.TAB)
                self.driver.switch_to.active_element.send_keys("25")
                self.driver.switch_to.active_element.send_keys(Keys.ENTER)
                time.sleep(0.5)
            except Exception:
                pass

            pasien_diproses = 0
            total_target_baris = 0
            failed_rows_info = []

            self.lbl_status.config(text="STATUS: Scanning for Subject Matrix...", fg=self.fg_neon)
            self.root.update()

            for index, row in df_gabungan.iterrows():
                if pd.notna(row[kolom_target]) and pd.notna(row[kolom_tgl]):
                    val_no_peg = str(row[kolom_target])
                    if "total" in val_no_peg.lower() or len(val_no_peg) < 3: continue

                    try:
                        raw_val = row[kolom_total]
                        if isinstance(raw_val, (int, float)):
                            excel_total = float(raw_val)
                        else:
                            clean_str = str(raw_val).replace('Rp', '').replace(' ', '').strip()
                            if clean_str == '' or clean_str == '-': excel_total = 0.0
                            elif ',' in clean_str and '.' in clean_str: excel_total = float(clean_str.replace('.', '').replace(',', '.'))
                            elif ',' in clean_str: excel_total = float(clean_str.replace(',', '.'))
                            else: excel_total = float(clean_str.replace('.', ''))
                    except Exception:
                        excel_total = 0.0

                    if excel_total <= 0: continue

                    str_tagihan_web = self.format_uang_web(excel_total)
                    total_target_baris += 1

                    parts = [p.strip() for p in val_no_peg.replace('\n', '/').replace('\\', '/').split('/') if len(p.strip()) > 0]
                    valid_ids = []
                    if len(parts) == 1:
                        valid_ids = [parts[0]]
                    elif len(parts) > 1:
                        valid_ids = [parts[1]] if len(parts[0]) <= 7 else [parts[0], parts[1]]

                    raw_tgl = str(row[kolom_tgl]).split(' ')[0].replace('-', '/')
                    parts_tgl = raw_tgl.split('/')
                    if len(parts_tgl) == 3:
                        if len(parts_tgl[0]) == 4: y, m, d = parts_tgl[0], parts_tgl[1], parts_tgl[2]
                        else: d, m, y = parts_tgl[0], parts_tgl[1], parts_tgl[2]
                        tgl_web_1, tgl_web_2 = f"{d.zfill(2)}/{m.zfill(2)}/{y}", f"{m.zfill(2)}/{d.zfill(2)}/{y}"
                    else:
                        tgl_web_1 = tgl_web_2 = raw_tgl

                    cleaned_name = self.bersihkan_nama(row[kolom_nama])
                    first_word = cleaned_name.split()[0] if cleaned_name else ""

                    search_input_aktif = self.driver.find_element(By.XPATH, "//input[contains(@placeholder, 'Search') or contains(@placeholder, 'search')]")
                    berhasil_centang = False

                    if not is_mcu:
                        for current_id in valid_ids:
                            self.driver.execute_script("arguments[0].focus();", search_input_aktif)
                            search_input_aktif.send_keys(Keys.CONTROL + "a", Keys.BACKSPACE)
                            search_input_aktif.send_keys(current_id)
                            time.sleep(0.1)
                            try:
                                xpath_row = f"//table/tbody/tr[contains(., '{current_id}') and (contains(., '{tgl_web_1}') or contains(., '{tgl_web_2}'))]"
                                baris_ditemukan = WebDriverWait(self.driver, 2).until(EC.presence_of_all_elements_located((By.XPATH, xpath_row)))
                                for baris in baris_ditemukan:
                                    teks_baris = baris.text
                                    tagihan_matches = re.findall(r'Rp\.?\s*([\d\.,]+)', teks_baris, re.IGNORECASE)
                                    web_total = -1.0
                                    for t in tagihan_matches: web_total = float(t.replace('.', '').replace(',', '.'))
                                    if web_total >= 0 and abs(web_total - excel_total) <= 2.0:
                                        cb = baris.find_element(By.XPATH, ".//input[@type='checkbox']")
                                        if not cb.is_selected():
                                            self.force_click(cb)
                                            berhasil_centang = True
                                            break
                                if berhasil_centang: break
                            except Exception: pass
                    else:
                        self.driver.execute_script("arguments[0].focus();", search_input_aktif)
                        search_input_aktif.send_keys(Keys.CONTROL + "a", Keys.BACKSPACE)
                        search_input_aktif.send_keys(cleaned_name)
                        time.sleep(0.3)

                        xpath_row_mcu = f"//table/tbody/tr[contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{first_word}') and (contains(., '{tgl_web_1}') or contains(., '{tgl_web_2}'))]"
                        try:
                            baris_mcu = WebDriverWait(self.driver, 2).until(EC.presence_of_all_elements_located((By.XPATH, xpath_row_mcu)))
                            for baris in baris_mcu:
                                teks_baris = baris.text
                                tagihan_matches = re.findall(r'Rp\.?\s*([\d\.,]+)', teks_baris, re.IGNORECASE)
                                web_total = -1.0
                                for t in tagihan_matches: web_total = float(t.replace('.', '').replace(',', '.'))
                                if web_total >= 0 and abs(web_total - excel_total) <= 2.0:
                                    cb = baris.find_element(By.XPATH, ".//input[@type='checkbox']")
                                    if not cb.is_selected():
                                        self.force_click(cb)
                                        berhasil_centang = True
                                        break
                        except Exception:
                            words = cleaned_name.split()
                            two_words = " ".join(words[:2]) if len(words) >= 2 else cleaned_name
                            self.driver.execute_script("arguments[0].focus();", search_input_aktif)
                            search_input_aktif.send_keys(Keys.CONTROL + "a", Keys.BACKSPACE)
                            search_input_aktif.send_keys(two_words)
                            time.sleep(0.3)
                            try:
                                baris_mcu = WebDriverWait(self.driver, 2).until(EC.presence_of_all_elements_located((By.XPATH, xpath_row_mcu)))
                                for baris in baris_mcu:
                                    teks_baris = baris.text
                                    tagihan_matches = re.findall(r'Rp\.?\s*([\d\.,]+)', teks_baris, re.IGNORECASE)
                                    web_total = -1.0
                                    for t in tagihan_matches: web_total = float(t.replace('.', '').replace(',', '.'))
                                    if web_total >= 0 and abs(web_total - excel_total) <= 2.0:
                                        cb = baris.find_element(By.XPATH, ".//input[@type='checkbox']")
                                        if not cb.is_selected():
                                            self.force_click(cb)
                                            berhasil_centang = True
                                            break
                            except Exception: pass

                    if berhasil_centang: pasien_diproses += 1
                    else:
                        nama_pasien_log = str(row[kolom_nama]).strip() if kolom_nama and pd.notna(row[kolom_nama]) else "Tanpa Nama"
                        no_baris_log = str(row[kolom_no]).split('.')[0] if kolom_no and pd.notna(row[kolom_no]) else str(index + 1)
                        failed_rows_info.append(f"Baris No. {no_baris_log} | {nama_pasien_log} (Total: {str_tagihan_web})")

            if pasien_diproses == 0: raise Exception("All subject identification tracks returned empty results.")

            self.lbl_status.config(text="STATUS: Compiling Final Payload...", fg=self.fg_neon)
            self.root.update()

            self.lbl_status.config(text="PHASE 1 & 2: Invoice Injection...", fg=self.fg_accent)
            self.root.update()

            input_invoice = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@placeholder, 'Invoice') or contains(@placeholder, 'invoice')]")))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", input_invoice)
            time.sleep(0.5)

            try: input_invoice.click()
            except Exception: self.driver.execute_script("arguments[0].click();", input_invoice)

            active_el = self.driver.switch_to.active_element
            active_el.send_keys(Keys.CONTROL + 'a', Keys.BACKSPACE)
            active_el.send_keys(nomor_inv_murni, Keys.TAB)

            self.lbl_status.config(text="PHASE 3: Syncing Timestamps...", fg=self.fg_accent)
            self.root.update()
            tgl_pdf_tebakan = self.ekstrak_tanggal_dari_pdf(path_pdf) if os.path.exists(path_pdf) else ""
            tgl_final = self.minta_tanggal_manual(tebakan_tanggal=tgl_pdf_tebakan)
            if not tgl_final: raise Exception("MANUAL OVERRIDE ABORTED: Missing Invoice Date.")

            active_el = self.driver.switch_to.active_element
            active_el.send_keys(Keys.CONTROL + "a", Keys.BACKSPACE)
            active_el.send_keys(tgl_final, Keys.ESCAPE, Keys.TAB)

            self.lbl_status.config(text="PHASE 4 & 5: Document Parameters...", fg=self.fg_accent)
            self.root.update()
            active_el = self.driver.switch_to.active_element
            active_el.send_keys(nomor_inv_murni, Keys.TAB, Keys.TAB, Keys.TAB)

            self.ketik_ninja("kwitansi")
            self.aksi_ninja(Keys.TAB)
            self.ketik_ninja("surat pengantar")
            self.aksi_ninja(Keys.TAB)
            self.ketik_ninja("debet nota")
            self.aksi_ninja(Keys.TAB)

            if is_mcu:
                self.ketik_ninja("Rekap Pasien MCU")
                self.aksi_ninja(Keys.TAB)
                self.ketik_ninja("Bukti Kehadiran MCU")
                self.aksi_ninja(Keys.TAB)
            self.aksi_ninja(Keys.TAB)

            self.lbl_status.config(text="PHASE 6: Uploading PDF...", fg=self.fg_accent)
            self.root.update()
            active_el = self.driver.switch_to.active_element
            active_el.send_keys(nomor_inv_murni)

            if os.path.exists(path_pdf):
                file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
                for fi in file_inputs:
                    try:
                        self.driver.execute_script("arguments[0].style.display = 'block';", fi)
                        self.driver.execute_script("arguments[0].style.visibility = 'visible';", fi)
                        fi.send_keys(os.path.abspath(path_pdf))
                        time.sleep(0.5)
                        self.driver.execute_script("arguments[0].style.display = 'none';", fi)
                        break
                    except Exception: pass

            self.lbl_status.config(text="PHASE 7 & 8: Locking Target Account...", fg=self.fg_accent)
            self.root.update()

            input_no_dok = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@placeholder, 'Dokumen') or contains(@placeholder, 'dokumen')]")))
            try: input_no_dok.click()
            except Exception: self.driver.execute_script("arguments[0].click();", input_no_dok)

            active_el = self.driver.switch_to.active_element
            active_el.send_keys(Keys.TAB, Keys.TAB, Keys.TAB, Keys.ARROW_DOWN, Keys.TAB)

        except Exception as e:
            messagebox.showerror("DIAGNOSTIC FEEDBACK", f"Payload execution failed:\n{e}")
            self.lbl_status.config(text="STATUS: SYSTEM HALTED. ERROR DETECTED.", fg=self.fg_alert)
            self.btn_mulai.config(state="normal")
            return

        if failed_rows_info:
            msg_report = f"Target Input: {total_target_baris} baris\nBerhasil Dicentang: {pasien_diproses} baris\n\n[ GAGAL DITEMUKAN ]\n" + "\n".join(failed_rows_info) + "\n\nSilakan verifikasi manual sebelum menekan tombol Ajukan Klaim."
            messagebox.showwarning("DIAGNOSTIC REPORT (PARTIAL SUCCESS)", msg_report)
            self.lbl_status.config(text=f"STATUS: PARTIAL SUCCESS ({pasien_diproses}/{total_target_baris})", fg=self.fg_warn)
        else:
            self.lbl_status.config(text=f"STATUS: SUCCESS. All {pasien_diproses} Subjects Processed.", fg=self.fg_neon)

        self.btn_lanjut.config(state="normal")

    def lanjut_file(self):
        self.btn_lanjut.config(state="disabled")
        self.lbl_status.config(text="STATUS: Archiving Processed Data...", fg=self.fg_text)
        self.root.update()

        path_awal_excel = os.path.join(self.folder_siap, self.current_file)
        path_akhir_excel = os.path.join(self.folder_selesai, self.current_file)
        nama_pdf = self.current_file.replace('.xlsx', '.pdf').replace('.csv', '.pdf')
        path_awal_pdf = os.path.join(self.folder_siap, nama_pdf)
        path_akhir_pdf = os.path.join(self.folder_selesai, nama_pdf)

        while True:
            try:
                if os.path.exists(path_awal_excel): os.rename(path_awal_excel, path_akhir_excel)
                break
            except Exception:
                retry = messagebox.askretrycancel("FILE LOCK ALERT", f"Excel target '{self.current_file}' masih terbuka atau terkunci.\n\nTolong tutup file tersebut, lalu klik 'Retry'.")
                if not retry:
                    self.lbl_status.config(text="STATUS: Archiving Failed.", fg=self.fg_alert)
                    self.btn_lanjut.config(state="normal")
                    return

        while True:
            try:
                if os.path.exists(path_awal_pdf): os.rename(path_awal_pdf, path_akhir_pdf)
                break
            except Exception:
                retry = messagebox.askretrycancel("FILE LOCK ALERT", f"PDF target '{nama_pdf}' masih terbuka atau terkunci.\n\nTolong tutup file tersebut, lalu klik 'Retry'.")
                if not retry:
                    self.lbl_status.config(text="STATUS: Archiving Failed.", fg=self.fg_alert)
                    self.btn_lanjut.config(state="normal")
                    return

        self.eksekusi_file()


if __name__ == "__main__":
    root = tk.Tk()
    app = RobotClaimsPortalAutomation(root)
    root.mainloop()
