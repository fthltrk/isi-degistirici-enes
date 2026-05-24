import customtkinter as ctk
import math
import os

ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("dark-blue") 

AYAR_DOSYASI = "parametreler.txt"

if not os.path.exists(AYAR_DOSYASI):
    with open(AYAR_DOSYASI, "w", encoding="utf-8") as f:
        f.write("# EGR Cooler Gelis_mis_ Ayar Dosyası\n")
        f.write("Motor Gücü (P_m) [kW] | 100\n")
        f.write("Egzoz Gazı Debisi (ṁ_e) [kg/s] | 0.15\n")
        f.write("Egzoz Özgül Isısı (C_pe) [J/kgK] | 1150\n")
        f.write("Egzoz Giriş Sıcaklığı (T_ei) [°C] | 400\n")
        f.write("Soğutucu Sıvı Debisi (ṁ_s) [kg/s] | 0.6\n")
        f.write("Soğutucu Özgül Isı (C_ps) [J/kgK] | 3800\n")
        f.write("Soğutucu Giriş Sıcaklığı (T_si) [°C] | 85\n")
        f.write("Isı Transfer Katsayısı (U) [W/m²K] | 250\n")
        f.write("Isı Transfer Alanı (A) [m²] | 1.1025\n")

def ayarlari_oku():
    parametreler = []
    with open(AYAR_DOSYASI, "r", encoding="utf-8") as f:
        for line in f:
            if "|" in line and not line.startswith("#"):
                isim, deger = line.split("|")
                parametreler.append({"isim": isim.strip(), "deger": deger.strip()})
    return parametreler

class EGRCoolerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("EGR Cooler Termal Analiz Laboratuvarı v3.0")
        self.geometry("1150x850")
        self.resizable(True, True)

        self.gecmis_hafiza = []
        self.suanki_indeks = -1

        # Telif / İmza Bölümü
        self.lbl_imza = ctk.CTkLabel(self, text="Bu program Enes Çelik tarafından yapılmıştır.", font=("Arial", 12, "italic"), text_color="#aaaaaa")
        self.lbl_imza.pack(side="top", pady=5)

        # Sekmeli Yapı
        self.tabview = ctk.CTkTabview(self, width=1100, height=760)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)
        
        self.tab_ana = self.tabview.add("Giriş & Hesaplama & Şema")
        self.tab_grafik = self.tabview.add("Grafiksel Analiz Paneli")

        # --- SEKME 1 DÜZENİ ---
        self.sol_frame = ctk.CTkFrame(self.tab_ana, width=450)
        self.sol_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.sag_frame = ctk.CTkFrame(self.tab_ana)
        self.sag_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Motor Tipi
        self.lbl_motor = ctk.CTkLabel(self.sol_frame, text="Motor ve Yakıt Tipi Seçimi:", font=("Arial", 12, "bold"))
        self.lbl_motor.pack(pady=(15,2), padx=20, anchor="w")
        
        self.combo_motor = ctk.CTkOptionMenu(self.sol_frame, values=["Dizel Motor Analizi", "Benzinli Motor Analizi"], command=self.motor_tipi_degisti)
        self.combo_motor.pack(pady=5, padx=20, fill="x")

        # Geçmiş Yönetimi
        self.nav_frame = ctk.CTkFrame(self.sol_frame, fg_color="transparent")
        self.nav_frame.pack(pady=10, padx=20, fill="x")
        
        self.btn_geri = ctk.CTkButton(self.nav_frame, text="⬅ Geri", width=120, command=self.gecmis_geri, state="disabled")
        self.btn_geri.pack(side="left", padx=5)
        
        self.btn_ileri = ctk.CTkButton(self.nav_frame, text="İleri ➡", width=120, command=self.gecmis_ileri, state="disabled")
        self.btn_ileri.pack(side="right", padx=5)

        try: self.veriler = ayarlari_oku()
        except: self.veriler = []
        
        self.kutular = []
        for veri in self.veriler:
            entry = self.create_input(self.sol_frame, veri["isim"], veri["deger"])
            self.kutular.append(entry)

        self.btn_hesapla = ctk.CTkButton(self.sol_frame, text="HESAPLA (Enter)", font=("Arial", 14, "bold"), command=self.hesapla, fg_color="#1f538d", hover_color="#14375e")
        self.btn_hesapla.pack(pady=20, padx=20, fill="x")

        self.bind("<Return>", lambda event: self.hesapla())

        # Şema Alanı (Güncellendi: Isı Değiştirici Sembolü)
        self.lbl_sema_title = ctk.CTkLabel(self.sag_frame, text="EGR Cooler Gelişmiş Şematik Gösterimi", font=("Arial", 14, "bold"))
        self.lbl_sema_title.pack(pady=10)
        
        # Daha gerçekçi bir ısı değiştirici şeması için özel bir çizim kanvası
        self.canvas_sema = ctk.CTkCanvas(self.sag_frame, width=580, height=220, bg="#212121", highlightthickness=0)
        self.canvas_sema.pack(pady=5, padx=10, fill="x")
        
        self.txt_sonuc = ctk.CTkTextbox(self.sag_frame, height=250, font=("Courier New", 12))
        self.txt_sonuc.pack(pady=15, padx=10, fill="both", expand=True)
        self.txt_sonuc.insert("0.0", "Değerleri girip HESAPLA butonuna basın veya ENTER'a tıklayın.")

        self.renk_bar = ctk.CTkLabel(self.sag_frame, text="Sistem Durumu: Bekleniyor", font=("Arial", 13, "bold"), fg_color="#555555", height=45, text_color="white")
        self.renk_bar.pack(pady=5, padx=10, fill="x")

        # --- SEKME 2 DÜZENİ (Yerli Grafik Motoru v2.0) ---
        self.lbl_grafik_info = ctk.CTkLabel(self.tab_grafik, text="📊 Gelişmiş Termal Analiz Grafikleri (Sıcaklık Profili - NTU - Yüzey Alanı Etkisi)", font=("Arial", 16, "bold"))
        self.lbl_grafik_info.pack(pady=15)

        self.canvas_grafik = ctk.CTkCanvas(self.tab_grafik, bg="#1e1e1e", highlightthickness=0)
        self.canvas_grafik.pack(fill="both", expand=True, padx=20, pady=10)

        # Başlangıç şemasını çiz
        self.update() # Kanvas boyutlarının doğru hesaplanması için
        self.sema_ciz(400, 85, 250, 95)

    def create_input(self, parent, label_text, default_val):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(pady=3, fill="x", padx=15)
        lbl = ctk.CTkLabel(frame, text=label_text, width=280, anchor="w", font=("Arial", 12, "bold"))
        lbl.pack(side="left")
        entry = ctk.CTkEntry(frame, width=120)
        entry.pack(side="right")
        entry.insert(0, default_val)
        return entry

    def motor_tipi_degisti(self, secim):
        if "Benzinli" in secim:
            self.kutular[3].delete(0, "end")
            self.kutular[3].insert(0, "750")
        else:
            self.kutular[3].delete(0, "end")
            self.kutular[3].insert(0, "400")

    def sema_ciz(self, T_ei, T_si, T_eo, T_so):
        self.canvas_sema.delete("all")
        # Gerçekçi ısı değiştirici gövdesi sembolü (Yuvarlatılmış tanklar ve boru demeti)
        g_color = "#333333"
        l_color = "#555555"
        self.canvas_sema.create_oval(100, 60, 160, 160, fill=g_color, outline=l_color, width=2) # Sol tank
        self.canvas_sema.create_oval(420, 60, 480, 160, fill=g_color, outline=l_color, width=2) # Sağ tank
        self.canvas_sema.create_rectangle(130, 70, 450, 150, fill=g_color, outline=l_color, width=2) # Orta gövde
        
        # İç boru demetlerini temsil eden çizgiler
        for i in range(5):
            self.canvas_sema.create_line(135, 80 + i*15, 445, 80 + i*15, fill="#444444", width=1)

        self.canvas_sema.create_text(290, 110, text="EGR GOVDE / ISI DEGISTIRICI", fill="#aaaaaa", font=("Arial", 11, "bold"))

        # EGZOZ GAZI AKIŞI (Soldan Sağa - Kırmızı/Turuncu)
        # Giriş nozulu
        self.canvas_sema.create_rectangle(70, 95, 105, 125, fill=g_color, outline=l_color, width=2)
        self.canvas_sema.create_line(30, 110, 80, 110, fill="#ff3333", width=6, arrow="last")
        self.canvas_sema.create_text(65, 80, text=f"Egzoz Giriş\n{T_ei:.1f}°C", fill="#ff5555", font=("Arial", 10, "bold"))
        
        # Çıkış nozulu
        self.canvas_sema.create_rectangle(475, 95, 510, 125, fill=g_color, outline=l_color, width=2)
        self.canvas_sema.create_line(505, 110, 560, 110, fill="#ff7700", width=6, arrow="last")
        self.canvas_sema.create_text(525, 80, text=f"Egzoz Çıkış\n{T_eo:.1f}°C", fill="#ffaa33", font=("Arial", 10, "bold"))

        # SOĞUTUCU SIVI AKIŞI (Zıt Akış - Mavi/Yeşil)
        # Giriş nozulu (Sağ üstten içeri)
        self.canvas_sema.create_rectangle(430, 40, 460, 75, fill=g_color, outline=l_color, width=2)
        self.canvas_sema.create_line(445, 10, 445, 50, fill="#0077ff", width=5, arrow="last")
        self.canvas_sema.create_text(450, -5, text=f"Sıvı Giriş: {T_si:.1f}°C", fill="#55bbff", font=("Arial", 9, "bold"), anchor="s")

        # Çıkış nozulu (Sol alttan dışarı)
        self.canvas_sema.create_rectangle(120, 145, 150, 180, fill=g_color, outline=l_color, width=2)
        self.canvas_sema.create_line(135, 175, 135, 215, fill="#009977", width=5, arrow="last")
        self.canvas_sema.create_text(135, 225, text=f"Sıvı Çıkış: {T_so:.1f}°C", fill="#33ffee", font=("Arial", 9, "bold"), anchor="n")

    def yerli_grafik_ciz(self, T_ei, T_eo, T_si, T_so, NTU, A, C_r, q_max, C_e, U, C_min):
        self.canvas_grafik.delete("all")
        w = self.canvas_grafik.winfo_width()
        h = self.canvas_grafik.winfo_height()
        if w < 100 or h < 100: w, h = 1050, 600 # Fallback

        g_width = (w - 150) // 3
        g_height = h - 100

        def plot_axes(ox, title, x_label, y_label):
            x2 = ox + g_width - 30
            y_bot = 60 + g_height - 40
            self.canvas_grafik.create_text(ox + g_width//2, 30, text=title, fill="white", font=("Arial", 12, "bold"))
            self.canvas_grafik.create_line(ox, y_bot, ox, 60, fill="white", width=2) # Y axis
            self.canvas_grafik.create_line(ox, y_bot, x2, y_bot, fill="white", width=2) # X axis
            self.canvas_grafik.create_text(ox, y_bot+20, text=x_label, fill="#cccccc", font=("Arial", 9), anchor="n")
            self.canvas_grafik.create_text(ox-10, (60+y_bot)//2, text=y_label, fill="#cccccc", font=("Arial", 9), anchor="e", angle=90)
            return x2, y_bot

        # --- GRAFİK 1: SICAKLIK PROFİLİ ---
        ox1 = 60
        ex1, y_bot = plot_axes(ox1, "Sıcaklık Değişim Profili", "Konum (Zıt Akış)", "Sıcaklık [°C]")
        
        max_t = max(T_ei, T_so, T_eo, T_si) + 30
        min_t = min(T_ei, T_so, T_eo, T_si) - 10
        if max_t == min_t: max_t += 10 # Prevent div by 0
        def t_scale(t): return y_bot - (((t - min_t) / (max_t - min_t)) * (y_bot - 60))

        self.canvas_grafik.create_line(ox1, t_scale(T_ei), ex1, t_scale(T_eo), fill="#ff3333", width=3) # Egzoz
        self.canvas_grafik.create_oval(ox1-4, t_scale(T_ei)-4, ox1+4, t_scale(T_ei)+4, fill="#ff3333", outline="")
        self.canvas_grafik.create_oval(ex1-4, t_scale(T_eo)-4, ex1+4, t_scale(T_eo)+4, fill="#ff3333", outline="")
        self.canvas_grafik.create_text(ox1-5, t_scale(T_ei), text=f"{int(T_ei)}°C", fill="#ff6666", font=("Arial", 9), anchor="e")
        self.canvas_grafik.create_text(ex1+5, t_scale(T_eo), text=f"{int(T_eo)}°C", fill="#ffaa44", font=("Arial", 9), anchor="w")

        self.canvas_grafik.create_line(ox1, t_scale(T_so), ex1, t_scale(T_si), fill="#0077ff", width=3) # Sıvı (Zıt)
        self.canvas_grafik.create_oval(ox1-4, t_scale(T_so)-4, ox1+4, t_scale(T_so)+4, fill="#0077ff", outline="")
        self.canvas_grafik.create_oval(ex1-4, t_scale(T_si)-4, ex1+4, t_scale(T_si)+4, fill="#0077ff", outline="")
        self.canvas_grafik.create_text(ox1-5, t_scale(T_so), text=f"{int(T_so)}°C", fill="#33ffee", font=("Arial", 9), anchor="e")
        self.canvas_grafik.create_text(ex1+5, t_scale(T_si), text=f"{int(T_si)}°C", fill="#55bbff", font=("Arial", 9), anchor="w")

        self.canvas_grafik.create_text(ox1, y_bot+10, text="Egzoz Giriş /\nSıvı Çıkış", fill="#aaaaaa", font=("Arial", 8), anchor="n")
        self.canvas_grafik.create_text(ex1, y_bot+10, text="Egzoz Çıkış /\nSıvı Giriş", fill="#aaaaaa", font=("Arial", 8), anchor="n")

        # --- GRAFİK 2: NTU ANALİZİ ---
        ox2 = ex1 + 90
        ex2, y_bot = plot_axes(ox2, "NTU - Çıkış Sıcaklığı Analizi", "NTU Sayısı", "Egzoz Çıkış [°C]")
        
        points_n = []
        max_ntu_plot = 5.0
        for i in range(30):
            n_t = 0.05 + (i / 29) * max_ntu_plot
            eps_t = (1 - math.exp(-n_t * (1 - C_r))) / (1 - C_r * math.exp(-n_t * (1 - C_r))) if C_r != 1 else n_t / (1 + n_t)
            t_out_t = T_ei - ((eps_t * q_max) / C_e)
            
            px = ox2 + (n_t / max_ntu_plot) * (ex2 - ox2)
            py = y_bot - (((t_out_t - min_t) / (max_t - min_t)) * (y_bot - 60))
            points_n.append((px, py))

        for i in range(len(points_n)-1):
            self.canvas_grafik.create_line(points_n[i][0], points_n[i][1], points_n[i+1][0], points_n[i+1][1], fill="#11cc66", width=2.5)

        cur_ntu_x = ox2 + (min(NTU, max_ntu_plot) / max_ntu_plot) * (ex2 - ox2)
        self.canvas_grafik.create_line(cur_ntu_x, y_bot, cur_ntu_x, 60, fill="yellow", dash=(6,6))
        self.canvas_grafik.create_text(cur_ntu_x, 60-15, text=f"NTU:{NTU:.2f}", fill="yellow", font=("Arial", 9, "bold"))
        self.canvas_grafik.create_text(ox2, y_bot+10, text="0", fill="#aaaaaa", font=("Arial", 8), anchor="n")
        self.canvas_grafik.create_text(ex2, y_bot+10, text=str(max_ntu_plot), fill="#aaaaaa", font=("Arial", 8), anchor="n")

        # --- GRAFİK 3: YÜZEY ALANI - ISI GÜCÜ (DÜZELTİLDİ: "#magenta" hatası giderildi, renk adı "magenta" yapıldı) ---
        ox3 = ex2 + 90
        ex3, y_bot = plot_axes(ox3, "Yüzey Alanı - Isı Transferi", "Yüzey Alanı [m²]", "Transfer Isı [kW]")
        
        points_q = []
        max_area_plot = A * 2.5 if A > 0 else 3.0
        q_limit_kw = q_max / 1000.0 * 1.1 # Max theoretical kW + 10%

        for i in range(30):
            a_t = 0.05 + (i / 29) * max_area_plot
            ntu_t = (U * a_t) / C_min
            eps_t = (1 - math.exp(-ntu_t * (1 - C_r))) / (1 - C_r * math.exp(-ntu_t * (1 - C_r))) if C_r != 1 else ntu_t / (1 + ntu_t)
            q_kw_t = (eps_t * q_max) / 1000.0

            px = ox3 + (a_t / max_area_plot) * (ex3 - ox3)
            py = y_bot - ((q_kw_t / q_limit_kw) * (y_bot - 60))
            points_q.append((px, py))

        for i in range(len(points_q)-1):
            # HATA BURADA DÜZELTİLDİ: "#magenta" yerine "magenta"
            self.canvas_grafik.create_line(points_q[i][0], points_q[i][1], points_q[i+1][0], points_q[i+1][1], fill="magenta", width=2.5)

        cur_a_x = ox3 + (A / max_area_plot) * (ex3 - ox3)
        self.canvas_grafik.create_line(cur_a_x, y_bot, cur_a_x, 60, fill="cyan", dash=(6,6))
        self.canvas_grafik.create_text(cur_a_x, 60-15, text=f"A:{A:.2f}m²", fill="cyan", font=("Arial", 9, "bold"))
        self.canvas_grafik.create_text(ox3, y_bot+10, text="0", fill="#aaaaaa", font=("Arial", 8), anchor="n")
        self.canvas_grafik.create_text(ex3, y_bot+10, text=f"{max_area_plot:.1f}", fill="#aaaaaa", font=("Arial", 8), anchor="n")

    def hafizaya_kaydet(self, mevcut_girdiler):
        if self.suanki_indeks == -1 or self.gecmis_hafiza[self.suanki_indeks] != mevcut_girdiler:
            self.gecmis_hafiza = self.gecmis_hafiza[:self.suanki_indeks + 1]
            self.gecmis_hafiza.append(mevcut_girdiler)
            self.suanki_indeks = len(self.gecmis_hafiza) - 1
            self.buton_durumlarini_guncelle()

    def buton_durumlarini_guncelle(self):
        if self.suanki_indeks > 0: self.btn_geri.configure(state="normal")
        else: self.btn_geri.configure(state="disabled")
        if self.suanki_indeks < len(self.gecmis_hafiza) - 1: self.btn_ileri.configure(state="normal")
        else: self.btn_ileri.configure(state="disabled")

    def gecmis_veri_yukle(self, indeks):
        girdiler = self.gecmis_hafiza[indeks]
        for i, val in enumerate(girdiler):
            self.kutular[i].delete(0, "end")
            self.kutular[i].insert(0, str(val))
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

    def hesapla(self, hafizaya_yaz=True):
        try:
            girdiler = [float(k.get()) for k in self.kutular]
            if hafizaya_yaz: self.hafizaya_kaydet(girdiler)

            P_motor, m_dot_e, cp_e, T_e_in, m_dot_s, cp_s, T_s_in, U, A = girdiler
            motor_tipi = self.combo_motor.get()

            # Isı Değiştirici Termal Hesaplamaları
            C_e = m_dot_e * cp_e
            C_s = m_dot_s * cp_s
            if C_e == 0 or C_s == 0: raise ValueError("Debi ve Özgül Isı çarpımı 0 olamaz.")
            
            C_min = min(C_e, C_s)
            C_max = max(C_e, C_s)
            C_r = C_min / C_max
            
            if C_min == 0: raise ValueError("Minimum Isı Kapasitesi 0 olamaz.")
            
            NTU = (U * A) / C_min
            
            # e-NTU Verim Denklemi (Zıt Akış / Counter-Flow için)
            if C_r == 1.0: # Özel durum
                epsilon = NTU / (1 + NTU)
            else:
                epsilon = (1 - math.exp(-NTU * (1 - C_r))) / (1 - C_r * math.exp(-NTU * (1 - C_r)))
            
            if epsilon > 1.0: epsilon = 1.0 # Termodinamik limit
            
            q_max = C_min * (T_e_in - T_s_in)
            q = epsilon * q_max
            
            T_e_out = T_e_in - (q / C_e)
            T_s_out = T_s_in + (q / C_s)

            delta_T1 = T_e_in - T_s_out
            delta_T2 = T_e_out - T_s_in
            if delta_T1 != delta_T2 and delta_T1/delta_T2 > 0:
                LMTD = (delta_T1 - delta_T2) / math.log(delta_T1 / delta_T2)
            else:
                LMTD = 0 # Sıcaklık farkı çok küçük veya negatif

            # Şemayı ve Grafikleri Dinamik Güncelle
            self.sema_ciz(T_e_in, T_s_in, T_e_out, T_s_out)
            self.yerli_grafik_ciz(T_e_in, T_e_out, T_s_in, T_s_out, NTU, A, C_r, q_max, C_e, U, C_min)

            # RENK KODLARI VE DURUM UYARILARI (Düzeltildi: Hata mesajı yerine sonuçlar gösteriliyor)
            if T_e_out > 200:
                durum_renk = "#aa2222" # Kırmızı
                durum_mesaj = f"⚠️ KRİTİK UYARI: Egzoz Çıkış Sıcaklığı Çok Yüksek! Soğutma yetersizliği."
            elif 120 <= T_e_out <= 200:
                durum_renk = "#22aa55" # Yeşil
                durum_mesaj = f"✅ OPTİMUM TASARIM: Isı değiştirici ideal mühendislik rejiminde çalışıyor."
            else:
                durum_renk = "#aaaa22" # Sarı
                durum_mesaj = f"⚠️ YOĞUŞMA RİSKİ: Çıkış çok düşük. Egzoz yoğuşabilir ve kurumlanma yapabilir."

            self.renk_bar.configure(fg_color=durum_renk, text=durum_mesaj)

            # Sonuç Metnini Güncelle
            sonuc_metni = (
                f"====================================================================\n"
                f" ANALİZ RAPORU TİPİ : {motor_tipi.upper()}\n"
                f"====================================================================\n"
                f" Motor Gücü Başlangıç Değeri  : {P_motor:.2f} kW\n"
                f"--------------------------------------------------------------------\n"
                f" Egzoz Gazı Çıkış Sıcaklığı   : {T_e_out:.2f} °C\n"
                f" Soğutma Sıvısı Çıkış Sıcaklığı: {T_s_out:.2f} °C\n"
                f" Transfer Edilen Isı Enerjisi : {q/1000:.2f} kW (Verim: %{epsilon*100:.1f})\n"
                f"--------------------------------------------------------------------\n"
                f" LMTD (Log. Sıcaklık Farkı)   : {LMTD:.2f} °C\n"
                f" Boyutsuz Sayı NTU (v_Alan)   : {NTU:.4f}\n"
                f"===================================================================="
            )
            self.txt_sonuc.delete("0.0", "end")
            self.txt_sonuc.insert("0.0", sonuc_metni)

        except Exception as e:
            self.renk_bar.configure(fg_color="#555555", text="Hata Oluştu!")
            self.txt_sonuc.delete("0.0", "end")
            self.txt_sonuc.insert("0.0", f"Hesaplama veya Çizim Hatası!\nGirdileri kontrol edin (Örn: Debi=0 olamaz).\n\nDetay: {str(e)}")

if __name__ == "__main__":
    app = EGRCoolerApp()
    app.mainloop()
