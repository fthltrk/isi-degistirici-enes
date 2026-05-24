import customtkinter as ctk
import math
import os
from tkinter import filedialog, messagebox

# PDF Raporlama için gerekli standart kütüphane araçları
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("blue") 

class EGRGelis_mis_Laboratuvar(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("EGR Cooler Ar-Ge ve Termal Analiz Laboratuvarı v4.0")
        self.geometry("1280x880")
        self.resizable(True, True)

        # Akışkan Özgül Isı Veritabanı (J/kgK)
        self.egzoz_veritabanı = {
            "Dizel Egzoz Gazı": 1150,
            "Benzin Egzoz Gazı": 1250,
            "LPG Egzoz Gazı": 1180,
            "Hidrojen Egzoz Gazı": 1420
        }
        self.sogutucu_veritabanı = {
            "Saf Su": 4184,
            "%50 Etilen Glikol (Antifriz)": 3300,
            "%30 Propilen Glikol": 3700
        }

        # Geçmiş Hafızası
        self.gecmis_hafiza = []
        self.suanki_indeks = -1

        # Üst Başlık ve İmza
        self.lbl_imza = ctk.CTkLabel(self, text="Bu program Enes Çelik tarafından geliştirilmiştir.", font=("Arial", 13, "italic"), text_color="#aaaaaa")
        self.lbl_imza.pack(side="top", pady=5)

        # Sekmeli Ana Yapı
        self.tabview = ctk.CTkTabview(self, width=1220, height=780)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)
        
        self.tab_ana = self.tabview.add("Giriş & Termal Simülasyon")
        self.tab_sihirbaz = self.tabview.add("🛠️ Geometri & Alan Sihirbazı")
        self.tab_grafik = self.tabview.add("📊 Gelişmiş Grafik Paneli")

        self.setup_sekme_ana()
        self.setup_sekme_sihirbaz()
        self.setup_sekme_grafik()

        # İlk Çizim Tetiklemeleri
        self.update()
        self.hesapla(hafizaya_yaz=True)

    # ----------------------------------------------------------------
    # SEKME 1: ANA SİMÜLASYON EKRANI TASARIMI
    # ----------------------------------------------------------------
    def setup_sekme_ana(self):
        # Sol Panel (Girdiler ve Kontroller)
        self.sol_frame = ctk.CTkScrollableFrame(self.tab_ana, width=460)
        self.sol_frame.pack(side="left", fill="y", padx=10, pady=10)

        # Sağ Panel (Şema ve Rapor)
        self.sag_frame = ctk.CTkFrame(self.tab_ana)
        self.sag_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # --- AÇILIR MENÜLER VE SEÇİMLER ---
        # 1. Akış Tipi Seçimi
        ctk.CTkLabel(self.sol_frame, text="Isı Değiştirici Akış Yönü:", font=("Arial", 12, "bold")).pack(pady=(10,2), padx=15, anchor="w")
        self.combo_akis_tipi = ctk.CTkOptionMenu(self.sol_frame, values=["Zıt Akış (Counter-Flow)", "Paralel Akış (Parallel-Flow)"], command=lambda x: self.hesapla())
        self.combo_akis_tipi.pack(pady=2, padx=15, fill="x")

        # 2. Egzoz Gazı Tipi
        ctk.CTkLabel(self.sol_frame, text="Egzoz Gazı / Yakıt Tipi:", font=("Arial", 12, "bold")).pack(pady=(10,2), padx=15, anchor="w")
        self.combo_egzoz = ctk.CTkOptionMenu(self.sol_frame, values=list(self.egzoz_veritabanı.keys()), command=lambda x: self.hesapla())
        self.combo_egzoz.pack(pady=2, padx=15, fill="x")

        # 3. Soğutucu Akışkan Tipi
        ctk.CTkLabel(self.sol_frame, text="Soğutucu Akışkan Tipi:", font=("Arial", 12, "bold")).pack(pady=(10,2), padx=15, anchor="w")
        self.combo_sogutucu = ctk.CTkOptionMenu(self.sol_frame, values=list(self.sogutucu_veritabanı.keys()), command=lambda x: self.hesapla())
        self.combo_sogutucu.pack(pady=2, padx=15, fill="x")

        # Geçmiş Butonları
        nav_frame = ctk.CTkFrame(self.sol_frame, fg_color="transparent")
        nav_frame.pack(pady=10, padx=15, fill="x")
        self.btn_geri = ctk.CTkButton(nav_frame, text="⬅ Geri", width=90, command=self.gecmis_geri, state="disabled")
        self.btn_geri.pack(side="left", padx=2)
        self.btn_ileri = ctk.CTkButton(nav_frame, text="İleri ➡", width=90, command=self.gecmis_ileri, state="disabled")
        self.btn_ileri.pack(side="right", padx=2)

        # NUMERİK GİRDİLER
        self.ent_motor_gucu = self.create_num_input(self.sol_frame, "Motor Gücü [kW]:", "120")
        self.ent_deb_e = self.create_num_input(self.sol_frame, "Egzoz Debisi (ṁ_e) [kg/s]:", "0.15")
        self.ent_temp_ei = self.create_num_input(self.sol_frame, "Egzoz Giriş Sıcaklığı [°C]:", "450")
        self.ent_deb_s = self.create_num_input(self.sol_frame, "Sıvı Debisi (ṁ_s) [kg/s]:", "0.5")
        self.ent_temp_si = self.create_num_input(self.sol_frame, "Sıvı Giriş Sıcaklığı [°C]:", "80")
        self.ent_u_katsayi = self.create_num_input(self.sol_frame, "Isı Transfer Katsayısı (U) [W/m²K]:", "280")

        # CANLI DEĞİŞİM SLIDER'I (Alan Kontrolü)
        ctk.CTkLabel(self.sol_frame, text="Canlı Alan Ayarı (A) [m²]:", font=("Arial", 12, "bold")).pack(pady=(15,0), padx=15, anchor="w")
        self.slider_alan = ctk.CTkSlider(self.sol_frame, from_=0.1, to=3.5, number_of_steps=68, command=self.slider_tetiklendi)
        self.slider_alan.set(1.2)
        self.slider_alan.pack(pady=2, padx=15, fill="x")
        self.lbl_slider_deger = ctk.CTkLabel(self.sol_frame, text="Mevcut Alan: 1.20 m²", font=("Arial", 11, "italic"), text_color="cyan")
        self.lbl_slider_deger.pack(pady=0, padx=15, anchor="e")

        # AKSİYON BUTONLARI
        self.btn_hesapla = ctk.CTkButton(self.sol_frame, text="SİMÜLASYONU ÇALIŞTIR", font=("Arial", 14, "bold"), command=self.hesapla, fg_color="#1f538d")
        self.btn_hesapla.pack(pady=15, padx=15, fill="x")

        self.btn_pdf = ctk.CTkButton(self.sol_frame, text="📄 PDF RAPORU OLUŞTUR", font=("Arial", 13, "bold"), command=self.rapor_pdf_uret, fg_color="#22aa55", hover_color="#1a8844")
        self.btn_pdf.pack(pady=5, padx=15, fill="x")

        # SAĞ PANEL BİLEŞENLERİ (Gelişmiş Mühendislik Şeması)
        self.canvas_sema = ctk.CTkCanvas(self.sag_frame, width=600, height=230, bg="#1c1c1c", highlightthickness=0)
        self.canvas_sema.pack(pady=10, padx=10, fill="x")
        
        self.txt_sonuc = ctk.CTkTextbox(self.sag_frame, font=("Courier New", 12))
        self.txt_sonuc.pack(pady=10, padx=10, fill="both", expand=True)

        self.renk_bar = ctk.CTkLabel(self.sag_frame, text="Sistem Hazır", font=("Arial", 13, "bold"), fg_color="#555555", height=45, text_color="white")
        self.renk_bar.pack(pady=5, padx=10, fill="x")

    def create_num_input(self, parent, label_text, default_val):
        fr = ctk.CTkFrame(parent, fg_color="transparent")
        fr.pack(pady=3, fill="x", padx=15)
        lbl = ctk.CTkLabel(fr, text=label_text, font=("Arial", 11, "bold"), width=240, anchor="w")
        lbl.pack(side="left")
        ent = ctk.CTkEntry(fr, width=100)
        ent.pack(side="right")
        ent.insert(0, default_val)
        return ent

    def slider_tetiklendi(self, val):
        self.lbl_slider_deger.configure(text=f"Mevcut Alan: {val:.2f} m²")
        self.hesapla(hafizaya_yaz=False)

    # ----------------------------------------------------------------
    # SEKME 2: GEOMETRİ VE TASARIM SİHİRBAZI
    # ----------------------------------------------------------------
    def setup_sekme_sihirbaz(self):
        box = ctk.CTkFrame(self.tab_sihirbaz)
        box.pack(pady=30, padx=30, fill="both", expand=True)

        ctk.CTkLabel(box, text="🛠️ Gövde-Boru Tipi EGR Alan Hesaplama Sihirbazı", font=("Arial", 16, "bold")).pack(pady=15)
        ctk.CTkLabel(box, text="Bu panelde gireceğiniz boru geometrisi verileri, ana simülasyondaki Isı Transfer Alanını (A) dinamik belirler.", font=("Arial", 11, "italic")).pack(pady=5)

        self.ent_sihirbaz_d = self.create_num_input(box, "Tek Bir Borunun Dış Çapı (d) [mm]:", "12")
        self.ent_sihirbaz_l = self.create_num_input(box, "Boruların Etkin Uzunluğu (L) [mm]:", "350")
        self.ent_sihirbaz_n = self.create_num_input(box, "Toplam İç Boru Sayısı (N) [Adet]:", "90")

        self.lbl_sihirbaz_sonuc = ctk.CTkLabel(box, text="Hesaplanan Toplam Alan: -- m²", font=("Arial", 14, "bold"), text_color="cyan")
        self.lbl_sihirbaz_sonuc.pack(pady=25)

        btn_aktar = ctk.CTkButton(box, text="Hesapla ve Alana Aktar 💾", font=("Arial", 13, "bold"), command=self.sihirbazdan_aktar, fg_color="#e67e22", hover_color="#d35400")
        btn_aktar.pack(pady=10, width=250)

    def sihirbazdan_aktar(self):
        try:
            d = float(self.ent_sihirbaz_d.get()) / 1000.0 # mm -> m
            L = float(self.ent_sihirbaz_l.get()) / 1000.0 # mm -> m
            N = float(self.ent_sihirbaz_n.get())
            
            hesaplanan_alan = math.pi * d * L * N
            self.lbl_sihirbaz_sonuc.configure(text=f"Hesaplanan Toplam Alan: {hesaplanan_alan:.4f} m²")
            
            # Ana ekrandaki slider'ı ve simülasyonu güncelle
            self.slider_alan.set(min(max(hesaplanan_alan, 0.1), 3.5))
            self.lbl_slider_deger.configure(text=f"Mevcut Alan: {hesaplanan_alan:.2f} m²")
            
            messagebox.showinfo("Başarılı", f"Geometrik alan ({hesaplanan_alan:.4f} m²) başarıyla simülasyon motoruna aktarıldı!")
            self.tabview.set("Giriş & Termal Simülasyon")
            self.hesapla()
        except Exception as e:
            messagebox.showerror("Geometri Hatası", "Lütfen girilen boyut değerlerini kontrol edin.")

    # ----------------------------------------------------------------
    # SEKME 3: YERLİ GRAFİK MOTORU EKRANI
    # ----------------------------------------------------------------
    def setup_sekme_grafik(self):
        self.canvas_grafik = ctk.CTkCanvas(self.tab_grafik, bg="#1a1a1a", highlightthickness=0)
        self.canvas_grafik.pack(fill="both", expand=True, padx=15, pady=15)

    # ----------------------------------------------------------------
    # DİNAMİK ISI DEĞİŞTİRİCİ ŞEMATİK GÖSTERİM MOTORU
    # ----------------------------------------------------------------
    def sema_ciz(self, T_ei, T_si, T_eo, T_so, akis_tipi):
        self.canvas_sema.delete("all")
        
        # Gövde Tasarımı (Mühendislik Sembolü)
        self.canvas_sema.create_oval(110, 60, 160, 160, fill="#2c3e50", outline="#7f8c8d", width=2) 
        self.canvas_sema.create_oval(430, 60, 480, 160, fill="#2c3e50", outline="#7f8c8d", width=2) 
        self.canvas_sema.create_rectangle(135, 70, 455, 150, fill="#2b2b2b", outline="#7f8c8d", width=2) 

        # Boru demetleri gösterimi
        for i in range(4):
            self.canvas_sema.create_line(140, 85 + i*18, 450, 85 + i*18, fill="#555555", width=2)

        self.canvas_sema.create_text(295, 110, text="EGR BUNDLE COOLER GÖVDE", fill="#ecf0f1", font=("Arial", 11, "bold"))

        # EGZOZ AKIŞI (Her zaman soldan sağa)
        self.canvas_sema.create_rectangle(75, 95, 112, 125, fill="#3a3a3a", outline="#7f8c8d", width=1)
        self.canvas_sema.create_line(30, 110, 85, 110, fill="#e74c3c", width=6, arrow="last")
        self.canvas_sema.create_text(65, 80, text=f"Egzoz Giriş\n{T_ei:.1f}°C", fill="#ff7675", font=("Arial", 10, "bold"))

        self.canvas_sema.create_rectangle(478, 95, 515, 125, fill="#3a3a3a", outline="#7f8c8d", width=1)
        self.canvas_sema.create_line(510, 110, 565, 110, fill="#e67e22", width=6, arrow="last")
        self.canvas_sema.create_text(535, 80, text=f"Egzoz Çıkış\n{T_eo:.1f}°C", fill="#f39c12", font=("Arial", 10, "bold"))

        # SOĞUTUCU SIVI AKIŞI (Seçime Göre Yön Değiştirir!)
        if "Zıt" in akis_tipi:
            # Sağ üstten girer, sol alttan çıkar
            self.canvas_sema.create_rectangle(435, 35, 465, 72, fill="#2c3e50", outline="#7f8c8d", width=1)
            self.canvas_sema.create_line(450, 8, 450, 45, fill="#3498db", width=5, arrow="last")
            self.canvas_sema.create_text(450, -3, text=f"Sıvı Giriş: {T_si:.1f}°C", fill="#74b9ff", font=("Arial", 9, "bold"), anchor="s")

            self.canvas_sema.create_rectangle(125, 148, 155, 185, fill="#2c3e50", outline="#7f8c8d", width=1)
            self.canvas_sema.create_line(140, 180, 140, 218, fill="#1abc9c", width=5, arrow="last")
            self.canvas_sema.create_text(140, 226, text=f"Sıvı Çıkış: {T_so:.1f}°C", fill="#55efc4", font=("Arial", 9, "bold"), anchor="n")
            
            self.canvas_sema.create_text(295, 165, text="⬅ AKIŞ YÖNÜ: ZIT AKIŞ (COUNTER)", fill="#74b9ff", font=("Arial", 9, "bold"))
        else:
            # Paralel Akış: Sol üstten girer, sağ alttan çıkar
            self.canvas_sema.create_rectangle(125, 35, 155, 72, fill="#2c3e50", outline="#7f8c8d", width=1)
            self.canvas_sema.create_line(140, 8, 140, 45, fill="#3498db", width=5, arrow="last")
            self.canvas_sema.create_text(140, -3, text=f"Sıvı Giriş: {T_si:.1f}°C", fill="#74b9ff", font=("Arial", 9, "bold"), anchor="s")

            self.canvas_sema.create_rectangle(435, 148, 465, 185, fill="#2c3e50", outline="#7f8c8d", width=1)
            self.canvas_sema.create_line(450, 180, 450, 218, fill="#1abc9c", width=5, arrow="last")
            self.canvas_sema.create_text(450, 226, text=f"Sıvı Çıkış: {T_so:.1f}°C", fill="#55efc4", font=("Arial", 9, "bold"), anchor="n")
            
            self.canvas_sema.create_text(295, 165, text="➡ AKIŞ YÖNÜ: PARALEL AKIŞ (CO-CURRENT)", fill="#e74c3c", font=("Arial", 9, "bold"))

    # ----------------------------------------------------------------
    # GELİŞMİŞ YERLİ ÜÇLÜ GRAFİK MOTORU
    # ----------------------------------------------------------------
    def yerli_grafik_ciz(self, T_ei, T_eo, T_si, T_so, NTU, A, C_r, q_max, C_e, U, C_min, akis_tipi):
        self.canvas_grafik.delete("all")
        w = self.canvas_grafik.winfo_width()
        h = self.canvas_grafik.winfo_height()
        if w < 200 or h < 200: w, h = 1150, 650 

        g_w = (w - 160) // 3
        g_h = h - 120
        y_bot = 60 + g_h - 40

        def eksen_ciz(ox, baslik, xl, yl):
            cx = ox + g_w - 30
            self.canvas_grafik.create_text(ox + g_w//2, 30, text=baslik, fill="white", font=("Arial", 12, "bold"))
            self.canvas_grafik.create_line(ox, y_bot, ox, 60, fill="white", width=2)
            self.canvas_grafik.create_line(ox, y_bot, cx, y_bot, fill="white", width=2)
            self.canvas_grafik.create_text(ox, y_bot+20, text=xl, fill="#b2bec3", font=("Arial", 9), anchor="n")
            self.canvas_grafik.create_text(ox-10, (60+y_bot)//2, text=yl, fill="#b2bec3", font=("Arial", 9), anchor="e", angle=90)
            return cx

        # --- GRAFİK 1: SICAKLIK PROFİLİ ---
        ox1 = 60
        ex1 = eksen_ciz(ox1, "Sıcaklık Değişim Profili", "Konum (EGR Boyu)", "Sıcaklık [°C]")
        max_t = max(T_ei, T_so, T_eo, T_si) + 40
        min_t = min(T_ei, T_so, T_eo, T_si) - 15
        def t_s(t): return y_bot - (((t - min_t) / (max_t - min_t)) * (y_bot - 60))

        # Egzoz Çizgisi (Her zaman soldan sağa düşer)
        self.canvas_grafik.create_line(ox1, t_s(T_ei), ex1, t_s(T_eo), fill="#ff7675", width=3)
        self.canvas_grafik.create_text(ox1-8, t_s(T_ei), text=f"{int(T_ei)}°C", fill="#ff7675", font=("Arial", 9), anchor="e")
        self.canvas_grafik.create_text(ex1+8, t_s(T_eo), text=f"{int(T_eo)}°C", fill="#f39c12", font=("Arial", 9), anchor="w")

        # Soğutucu Sıvı Çizgisi (Akış tipine göre yönü değişir!)
        if "Zıt" in akis_tipi:
            self.canvas_grafik.create_line(ox1, t_s(T_so), ex1, t_s(T_si), fill="#74b9ff", width=3)
            self.canvas_grafik.create_text(ox1-8, t_s(T_so), text=f"{int(T_so)}°C", fill="#55efc4", font=("Arial", 9), anchor="e")
            self.canvas_grafik.create_text(ex1+8, t_s(T_si), text=f"{int(T_si)}°C", fill="#74b9ff", font=("Arial", 9), anchor="w")
        else:
            self.canvas_grafik.create_line(ox1, t_s(T_si), ex1, t_s(T_so), fill="#74b9ff", width=3)
            self.canvas_grafik.create_text(ox1-8, t_s(T_si), text=f"{int(T_si)}°C", fill="#74b9ff", font=("Arial", 9), anchor="e")
            self.canvas_grafik.create_text(ex1+8, t_s(T_so), text=f"{int(T_so)}°C", fill="#55efc4", font=("Arial", 9), anchor="w")

        # --- GRAFİK 2: NTU - ÇIKIŞ ANALİZİ ---
        ox2 = ex1 + 80
        ex2 = eksen_ciz(ox2, "NTU - Çıkış Sıcaklığı Analizi", "NTU Sayısı", "Egzoz Çıkış [°C]")
        pts_n = []
        for i in range(35):
            n_t = 0.05 + (i / 34) * 5.0
            if "Zıt" in akis_tipi:
                eps_t = (1 - math.exp(-n_t*(1-C_r))) / (1 - C_r*math.exp(-n_t*(1-C_r))) if C_r != 1 else n_t/(1+n_t)
            else:
                eps_t = (1 - math.exp(-n_t*(1+C_r))) / (1 + C_r)
            
            te_out_t = T_ei - ((eps_t * q_max) / C_e)
            px = ox2 + (n_t / 5.0) * (ex2 - ox2)
            py = y_bot - (((te_out_t - min_t) / (max_t - min_t)) * (y_bot - 60))
            pts_n.append((px, py))

        for i in range(len(pts_n)-1):
            self.canvas_grafik.create_line(pts_n[i][0], pts_n[i][1], pts_n[i+1][0], pts_n[i+1][1], fill="#2ecc71", width=2.5)

        cur_ntu_x = ox2 + (min(NTU, 5.0) / 5.0) * (ex2 - ox2)
        self.canvas_grafik.create_line(cur_ntu_x, y_bot, cur_ntu_x, 60, fill="yellow", dash=(5,5))
        self.canvas_grafik.create_text(cur_ntu_x, 50, text=f"NTU:{NTU:.2f}", fill="yellow", font=("Arial", 9, "bold"))

        # --- GRAFİK 3: ALAN - ISI GÜCÜ GRAFİĞİ (DÜZELTİLDİ: "magenta" hatasız çizim) ---
        ox3 = ex2 + 80
        ex3 = eksen_ciz(ox3, "Yüzey Alanı - Isı Gücü Etkisi", "Alan [m²]", "Isı Gücü [kW]")
        pts_q = []
        m_a_plot = A * 2.5 if A > 0 else 3.0
        q_lim_kw = q_max / 1000.0 * 1.15

        for i in range(35):
            a_t = 0.05 + (i / 34) * m_a_plot
            ntu_t = (U * a_t) / C_min
            if "Zıt" in akis_tipi:
                eps_t = (1 - math.exp(-ntu_t*(1-C_r))) / (1 - C_r*math.exp(-ntu_t*(1-C_r))) if C_r != 1 else ntu_t/(1+ntu_t)
            else:
                eps_t = (1 - math.exp(-ntu_t*(1+C_r))) / (1 + C_r)
            
            qk_t = (eps_t * q_max) / 1000.0
            px = ox3 + (a_t / m_a_plot) * (ex3 - ox3)
            py = y_bot - ((qk_t / q_lim_kw) * (y_bot - 60))
            pts_q.append((px, py))

        for i in range(len(pts_q)-1):
            # Standart 'magenta' rengi sorunsuz çalışır
            self.canvas_grafik.create_line(pts_q[i][0], pts_q[i][1], pts_q[i+1][0], pts_q[i+1][1], fill="magenta", width=2.5)

        cur_a_x = ox3 + (A / m_a_plot) * (ex3 - ox3)
        self.canvas_grafik.create_line(cur_a_x, y_bot, cur_a_x, 60, fill="cyan", dash=(5,5))
        self.canvas_grafik.create_text(cur_a_x, 50, text=f"A:{A:.2f}m²", fill="cyan", font=("Arial", 9, "bold"))

    # ----------------------------------------------------------------
    # ANA MATEMATİKSEL SİMÜLASYON MOTORU (e-NTU)
    # ----------------------------------------------------------------
    def hesapla(self, hafizaya_yaz=True):
        try:
            # Girdileri oku
            akis_tipi = self.combo_akis_tipi.get()
            egzoz_adi = self.combo_egzoz.get()
            sogutucu_adi = self.combo_sogutucu.get()

            cp_e = self.egzoz_veritabanı[egzoz_adi]
            cp_s = self.sogutucu_veritabanı[sogutucu_adi]

            P_motor = float(self.ent_motor_gucu.get())
            m_dot_e = float(self.ent_deb_e.get())
            T_e_in = float(self.ent_temp_ei.get())
            m_dot_s = float(self.ent_deb_s.get())
            T_s_in = float(self.ent_temp_si.get())
            U = float(self.ent_u_katsayi.get())
            A = self.slider_alan.get()

            if hafizaya_yaz:
                self.gecmis_hafizaya_ekle([akis_tipi, egzoz_adi, sogutucu_adi, P_motor, m_dot_e, T_e_in, m_dot_s, T_s_in, U, A])

            # Termal denklemler
            C_e = m_dot_e * cp_e
            C_s = m_dot_s * cp_s
            C_min = min(C_e, C_s)
            C_max = max(C_e, C_s)
            C_r = C_min / C_max
            
            NTU = (U * A) / C_min

            # Seçilen akış yönüne göre formül değişimi
            if "Zıt" in akis_tipi:
                epsilon = (1 - math.exp(-NTU * (1 - C_r))) / (1 - C_r * math.exp(-NTU * (1 - C_r))) if C_r != 1 else NTU / (1 + NTU)
            else:
                epsilon = (1 - math.exp(-NTU * (1 + C_r))) / (1 + C_r)

            epsilon = min(max(epsilon, 0.0), 1.0)
            q_max = C_min * (T_e_in - T_s_in)
            q = epsilon * q_max
            
            T_e_out = T_e_in - (q / C_e)
            T_s_out = T_s_in + (q / C_s)

            # LMTD Hesabı
            if "Zıt" in akis_tipi:
                dt1 = T_e_in - T_s_out
                dt2 = T_e_out - T_s_in
            else:
                dt1 = T_e_in - T_s_in
                dt2 = T_e_out - T_s_out

            if dt1 > 0 and dt2 > 0 and dt1 != dt2:
                LMTD = (dt1 - dt2) / math.log(dt1 / dt2)
            else:
                LMTD = (dt1 + dt2) / 2.0

            # Grafik ve şemayı güncelle
            self.sema_ciz(T_e_in, T_s_in, T_e_out, T_s_out, akis_tipi)
            self.yerli_grafik_ciz(T_e_in, T_e_out, T_s_in, T_s_out, NTU, A, C_r, q_max, C_e, U, C_min, akis_tipi)

            # Ekrana rapor yazdır
            self.son_analiz_raporu = {
                "akis_tipi": akis_tipi, "egzoz_adi": egzoz_adi, "sogutucu_adi": sogutucu_adi,
                "P_motor": P_motor, "m_dot_e": m_dot_e, "T_e_in": T_e_in, "m_dot_s": m_dot_s,
                "T_s_in": T_s_in, "U": U, "A": A, "T_e_out": T_e_out, "T_s_out": T_s_out,
                "q_kw": q/1000.0, "verim": epsilon*100.0, "LMTD": LMTD, "NTU": NTU
            }

            sonuc_txt = (
                f"====================================================================\n"
                f"       EGR COOLER İLERİ SEVİYE SİMÜLASYON RAPORU\n"
                f"====================================================================\n"
                f" Akış Modeli / Yönü           : {akis_tipi}\n"
                f" Seçilen Gaz / Sıvı Bileşimi  : {egzoz_adi} / {sogutucu_adi}\n"
                f" Aktif Isı Transfer Alanı (A) : {A:.4f} m²\n"
                f"--------------------------------------------------------------------\n"
                f" Egzoz Gazı Çıkış Sıcaklığı   : {T_e_out:.2f} °C\n"
                f" Soğutma Sıvısı Çıkış Sıcaklığı: {T_s_out:.2f} °C\n"
                f" Geri Kazanılan Isı Gücü      : {q/1000.0:.2f} kW\n"
                f" Cihaz Termal Etkinliği (Verim): % {epsilon*100.0:.2f}\n"
                f" Logaritmik Ortalama Sıc. Farkı: {LMTD:.2f} °C\n"
                f" Hesaplanan NTU Değeri        : {NTU:.4f}\n"
                f"===================================================================="
            )
            self.txt_sonuc.delete("0.0", "end")
            self.txt_sonuc.insert("0.0", sonuc_txt)

            # Sistem Durum Uyarı Çubuğu
            if T_e_out > 190:
                self.renk_bar.configure(fg_color="#c0392b", text="⚠️ KRİTİK SEVİYE: Egzoz gazı yeterince soğutulamıyor, alanı büyütün.")
            elif 110 <= T_e_out <= 190:
                self.renk_bar.configure(fg_color="#27ae60", text="✅ İDEAL TASARIM: Optimum emisyon ve soğutma dengesi yakalandı.")
            else:
                self.renk_bar.configure(fg_color="#d35400", text="⚠️ YOĞUŞMA ALARMI: Çıkış çok soğuk, borularda kurum ve asit birikebilir.")

        except Exception as e:
            self.txt_sonuc.delete("0.0", "end")
            self.txt_sonuc.insert("0.0", f"Hata Oluştu: {str(e)}")

    # ----------------------------------------------------------------
    # PDF RAPORLAMA SİSTEMİ
    # ----------------------------------------------------------------
    def rapor_pdf_uret(self):
        try:
            dosya_yolu = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Dosyası", "*.pdf")], title="Raporu Kaydet")
            if not dosya_yolu: return

            doc = SimpleDocTemplate(dosya_yolu, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Özel başlık stili
            baslik_stili = ParagraphStyle('Baslik', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#1f538d'), spaceAfter=15, alignment=1)
            normal_stil = ParagraphStyle('Normal_Rapor', parent=styles['Normal'], fontSize=11, spaceAfter=8)

            hikaye = []
            r = self.son_analiz_raporu

            hikaye.append(Paragraph("EGR Cooler Termal Mühendislik Analiz Raporu", baslik_stili))
            hikaye.append(Paragraph("Bu teknik rapor Enes Çelik simülasyon motoru tarafından üretilmiştir.", ParagraphStyle('ItalicSub', parent=normal_stil, fontName='Helvetica-Oblique', textColor=colors.gray)))
            hikaye.append(Spacer(1, 15))

            data = [
                ["Parametre Adı", "Girdi Değeri", "Analiz Sonucu", "Birim"],
                ["Akış Tipi", r["akis_tipi"], "-", "-"],
                ["Yakıt / Gaz Türü", r["egzoz_adi"], "-", "-"],
                ["Soğutucu Akışkan", r["sogutucu_adi"], "-", "-"],
                ["Isı Transfer Alanı (A)", f"{r['A']:.4f}", "-", "m²"],
                ["Egzoz Giriş / Çıkış Sıcaklığı", f"{r['T_e_in']:.1f}", f"{r['T_e_out']:.2f}", "°C"],
                ["Sıvı Giriş / Çıkış Sıcaklığı", f"{r['T_s_in']:.1f}", f"{r['T_s_out']:.2f}", "°C"],
                ["Transfer Edilen Isı Gücü", "-", f"{r['q_kw']:.2f}", "kW"],
                ["Isı Değiştirici Verimi", "-", f"% {r['verim']:.2f}", "-"],
                ["LMTD / NTU Sayıları", "-", f"{r['LMTD']:.2f} / {r['NTU']:.2f}", "-"]
            ]

            t = Table(data, colWidths=[200, 110, 110, 70])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f538d')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f5f6fa')),
                ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#dcdde1')),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
            ]))

            hikaye.append(t)
            doc.build(hikaye)
            messagebox.showinfo("Başarılı", f"Mühendislik PDF raporu başarıyla oluşturuldu:\n{dosya_yolu}")
        except Exception as e:
            messagebox.showerror("PDF Hatası", f"PDF raporu yazılırken hata çıktı: {str(e)}")

    # ----------------------------------------------------------------
    # GEÇMİŞ YÖNETİMİ HAFİZA SİSTEMİ
    # ----------------------------------------------------------------
    def gecmis_hafizaya_ekle(self, veri):
        if self.suanki_indeks == -1 or self.gecmis_hafiza[self.suanki_indeks] != veri:
            self.gecmis_hafiza = self.gecmis_hafiza[:self.suanki_indeks + 1]
            self.gecmis_hafiza.append(veri)
            self.suanki_indeks = len(self.gecmis_hafiza) - 1
            self.buton_durumlarini_guncelle()

    def buton_durumlarini_guncelle(self):
        if self.suanki_indeks > 0: self.btn_geri.configure(state="normal")
        else: self.btn_geri.configure(state="disabled")
        if self.suanki_indeks < len(self.gecmis_hafiza) - 1: self.btn_ileri.configure(state="normal")
        else: self.btn_ileri.configure(state="disabled")

    def gecmis_veri_yukle(self, idx):
        v = self.gecmis_hafiza[idx]
        self.combo_akis_tipi.set(v[0])
        self.combo_egzoz.set(v[1])
        self.combo_sogutucu.set(v[2])
        self.ent_motor_gucu.delete(0, "end"); self.ent_motor_gucu.insert(0, str(v[3]))
        self.ent_deb_e.delete(0, "end"); self.ent_deb_e.insert(0, str(v[4]))
        self.ent_temp_ei.delete(0, "end"); self.ent_temp_ei.insert(0, str(v[5]))
        self.ent_deb_s.delete(0, "end"); self.ent_deb_s.insert(0, str(v[6]))
        self.ent_temp_si.delete(0, "end"); self.ent_temp_si.insert(0, str(v[7]))
        self.ent_u_katsayi.delete(0, "end"); self.ent_u_katsayi.insert(0, str(v[8]))
        self.slider_alan.set(v[9])
        self.lbl_slider_deger.configure(text=f"Mevcut Alan: {v[9]:.2f} m²")
        self.hesapla(hafizaya_yaz=False)

    def gecmis_geri(self):
        if self.suanki_indeks > 0:
            self.suanki_indeks -= 1
            self.gecmis_veri_yukle(self.suanki_indeks)
            self.buton_durumlarini_guncelle()

    def gecmis_ileri(self):
        if self.suanki_indeks < len(self.gecmis_hafiza) - 1:
            self.suanki_indeks += 1
            self.gecmis_veri_yukle(self.suanki_indeks)
            self.buton_durumlarini_guncelle()

if __name__ == "__main__":
    app = EGRGelis_mis_Laboratuvar()
    app.mainloop()
