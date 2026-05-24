import customtkinter as ctk
import math
import os

ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("blue") 

AYAR_DOSYASI = "parametreler.txt"

if not os.path.exists(AYAR_DOSYASI):
    with open(AYAR_DOSYASI, "w", encoding="utf-8") as f:
        f.write("# EGR Cooler Gelis_mis_ Ayar Dosyası\n")
        f.write("Motor Gücü (P_m) [kW] | 100\n")
        f.write("Egzoz Gazı Debisi (ṁ_e) [kg/s] | 0.15\n")
        f.write("Egzoz Özgül Isısı (C_pe) [J/kgK] | 1150\n")
        f.write("Egzoz Giriş Sıcaklığı (T_ei) [°C] | 500\n")
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

        self.title("EGR Cooler Termal Analiz Laboratuvarı v2.0")
        self.geometry("1100x820")
        self.resizable(True, True)

        self.gecmis_hafiza = []
        self.suanki_indeks = -1

        # Telif / İmza Bölümü
        self.lbl_imza = ctk.CTkLabel(self, text="Bu program Enes Çelik tarafından yapılmıştır.", font=("Arial", 12, "italic"), text_color="#aaaaaa")
        self.lbl_imza.pack(side="top", pady=5)

        # Sekmeli Yapı
        self.tabview = ctk.CTkTabview(self, width=1050, height=740)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)
        
        self.tab_ana = self.tabview.add("Giriş & Hesaplama & Şema")
        self.tab_grafik = self.tabview.add("Grafiksel Analiz Paneli")

        # --- SEKME 1 DÜZENİ ---
        self.sol_frame = ctk.CTkFrame(self.tab_ana, width=420)
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
        self.nav_frame.pack(pady=5, padx=20, fill="x")
        
        self.btn_geri = ctk.CTkButton(self.nav_frame, text="⬅ Geri", width=100, command=self.gecmis_geri, state="disabled")
        self.btn_geri.pack(side="left", padx=5)
        
        self.btn_ileri = ctk.CTkButton(self.nav_frame, text="İleri ➡", width=100, command=self.gecmis_ileri, state="disabled")
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

        # Şema Alanı
        self.lbl_sema_title = ctk.CTkLabel(self.sag_frame, text="EGR Cooler Ters Akış (Counter-Flow) Şematik Gösterimi", font=("Arial", 13, "bold"))
        self.lbl_sema_title.pack(pady=5)
        
        self.canvas_sema = ctk.CTkCanvas(self.sag_frame, width=550, height=180, bg="#1e1e1e", highlightthickness=0)
        self.canvas_sema.pack(pady=5, padx=10, fill="x")
        
        self.txt_sonuc = ctk.CTkTextbox(self.sag_frame, height=200, font=("Courier New", 12))
        self.txt_sonuc.pack(pady=10, padx=10, fill="both", expand=True)
        self.txt_sonuc.insert("0.0", "Değerleri girip HESAPLA butonuna basın veya ENTER'a tıklayın.")

        self.renk_bar = ctk.CTkLabel(self.sag_frame, text="Sistem Durumu: Bekleniyor", font=("Arial", 13, "bold"), fg_color="#555555", height=40, text_color="white")
        self.renk_bar.pack(pady=5, padx=10, fill="x")

        # --- SEKME 2 DÜZENİ (Yerli Grafik Motoru) ---
        self.lbl_grafik_info = ctk.CTkLabel(self.tab_grafik, text="📊 Gelişmiş Termal Analiz Grafikleri (Sıcaklık Profili - NTU Analizi - Alan Etkisi)", font=("Arial", 14, "bold"))
        self.lbl_grafik_info.pack(pady=10)

        self.canvas_grafik = ctk.CTkCanvas(self.tab_grafik, bg="#1e1e1e", highlightthickness=0)
        self.canvas_grafik.pack(fill="both", expand=True, padx=20, pady=10)

        self.sema_ciz(500, 85, 250, 95)

    def create_input(self, parent, label_text, default_val):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(pady=2, fill="x", padx=15)
        lbl = ctk.CTkLabel(frame, text=label_text, width=260, anchor="w", font=("Arial", 11, "bold"))
        lbl.pack(side="left")
        entry = ctk.CTkEntry(frame, width=110)
        entry.pack(side="right")
        entry.insert(0, default_val)
        return entry

    def motor_tipi_degisti(self, secim):
        if "Benzinli" in secim:
            self.kutular[3].delete(0, "end")
            self.kutular[3].insert(0, "750")
        else:
            self.kutular[3].delete(0, "end")
            self.kutular[3].insert(0, "500")

    def sema_ciz(self, T_ei, T_si, T_eo, T_so):
        self.canvas_sema.delete("all")
        self.canvas_sema.create_rectangle(100, 50, 450, 130, fill="#333333", outline="#555555", width=2)
        self.canvas_sema.create_text(275, 90, text="EGR GÖVDE / ISI DEĞİŞTİRİCİ", fill="#aaaaaa", font=("Arial", 10, "bold"))

        self.canvas_sema.create_line(30, 70, 100, 70, fill="#ff4444", width=5, arrow="last")
        self.canvas_sema.create_text(65, 50, text=f"Egzoz Giriş\n{T_ei:.1f}°C", fill="#ff6666", font=("Arial", 9, "bold"))
        
        self.canvas_sema.create_line(450, 70, 520, 70, fill="#ff8800", width=5, arrow="last")
        self.canvas_sema.create_text(485, 50, text=f"Egzoz Çıkış\n{T_eo:.1f}°C", fill="#ffaa44", font=("Arial", 9, "bold"))

        self.canvas_sema.create_line(480, 110, 410, 110, fill="#0088ff", width=4, arrow="last")
        self.canvas_sema.create_text(485, 135, text=f"Sıvı Giriş\n{T_si:.1f}°C", fill="#66bbff", font=("Arial", 9, "bold"))

        self.canvas_sema.create_line(140, 110, 50, 110, fill="#00bb99", width=4, arrow="last")
        self.canvas_sema.create_text(65, 135, text=f"Sıvı Çıkış\n{T_so:.1f}°C", fill="#44ffee", font=("Arial", 9, "bold"))

    def yerli_grafik_ciz(self, T_ei, T_eo, T_si, T_so, NTU, A, C_r, q_max, C_e, U, C_min):
        self.canvas_grafik.delete("all")
        w = self.canvas_grafik.winfo_width()
        h = self.canvas_grafik.winfo_height()
        if w < 100 or h < 100: 
            w, h = 1000, 400 # Varsayılan boyutlar

        g_width = (w - 120) // 3
        g_height = h - 80

        # --- GRAFİK 1: SIFIRDAN SICAKLIK PROFİLİ ---
        x1, y1_top = 50, 40
        x2 = x1 + g_width - 30
        y_bot = y1_top + g_height - 40

        self.canvas_grafik.create_text(x1 + g_width//2, 20, text="Sıcaklık Değişim Profili", fill="white", font=("Arial", 11, "bold"))
        self.canvas_grafik.create_line(x1, y_bot, x1, y1_top, fill="white", width=2) # Y ekseni
        self.canvas_grafik.create_line(x1, y_bot, x2, y_bot, fill="white", width=2) # X ekseni

        max_t = max(T_ei, T_so) + 50
        def t_scale(t): return y_bot - ((t / max_t) * (y_bot - y1_top))

        # Egzoz Çizgisi (Kırmızı)
        self.canvas_grafik.create_line(x1, t_scale(T_ei), x2, t_scale(T_eo), fill="#ff4444", width=3)
        self.canvas_grafik.create_oval(x1-4, t_scale(T_ei)-4, x1+4, t_scale(T_ei)+4, fill="#ff4444")
        self.canvas_grafik.create_oval(x2-4, t_scale(T_eo)-4, x2+4, t_scale(T_eo)+4, fill="#ff4444")
        # Sıvı Çizgisi (Mavi - Ters Akış)
        self.canvas_grafik.create_line(x1, t_scale(T_so), x2, t_scale(T_si), fill="#0088ff", width=3)
        self.canvas_grafik.create_oval(x1-4, t_scale(T_so)-4, x1+4, t_scale(T_so)+4, fill="#0088ff")
        self.canvas_grafik.create_oval(x2-4, t_scale(T_si)-4, x2+4, t_scale(T_si)+4, fill="#0088ff")

        self.canvas_grafik.create_text(x1, y_bot+15, text="Giriş Bölgesi", fill="#aaaaaa", font=("Arial", 8))
        self.canvas_grafik.create_text(x2, y_bot+15, text="Çıkış Bölgesi", fill="#aaaaaa", font=("Arial", 8))
        self.canvas_grafik.create_text(x1-25, t_scale(T_ei), text=f"{int(T_ei)}°C", fill="#ff6666", font=("Arial", 8))
        self.canvas_grafik.create_text(x2+25, t_scale(T_eo), text=f"{int(T_eo)}°C", fill="#ffaa44", font=("Arial", 8))

        # --- GRAFİK 2: NTU - SICAKLIK GRAFİĞİ ---
        ox2 = x2 + 60
        ex2 = ox2 + g_width - 30
        self.canvas_grafik.create_text(ox2 + g_width//2, 20, text="NTU - Çıkış Sıcaklığı Analizi", fill="white", font=("Arial", 11, "bold"))
        self.canvas_grafik.create_line(ox2, y_bot, ox2, y1_top, fill="white", width=2)
        self.canvas_grafik.create_line(ox2, y_bot, ex2, y_bot, fill="white", width=2)

        points = []
        for i in range(20):
            n_t = 0.1 + (i / 19) * 3.5
            eps_t = (1 - math.exp(-n_t * (1 - C_r))) / (1 - C_r * math.exp(-n_t * (1 - C_r))) if C_r != 1 else n_t / (1 + n_t)
            t_out_t = T_ei - ((eps_t * q_max) / C_e)
            
            px = ox2 + (n_t / 4.0) * (ex2 - ox2)
            py = y_bot - ((t_out_t / max_t) * (y_bot - y1_top))
            points.append((px, py))

        for i in range(len(points)-1):
            self.canvas_grafik.create_line(points[i][0], points[i][1], points[i+1][0], points[i+1][1], fill="#22aa55", width=2)

        # Mevcut NTU Çizgisi
        cur_ntu_x = ox2 + (min(NTU, 4.0) / 4.0) * (ex2 - ox2)
        self.canvas_grafik.create_line(cur_ntu_x, y_bot, cur_ntu_x, y1_top, fill="yellow", dash=(4,4))
        self.canvas_grafik.create_text(cur_ntu_x, y1_top-10, text=f"NTU:{NTU:.2f}", fill="yellow", font=("Arial", 8))

        # --- GRAFİK 3: YÜZEY ALANI - ISI GÜCÜ ---
        ox3 = ex2 + 60
        ex3 = ox3 + g_width - 30
        self.canvas_grafik.create_text(ox3 + g_width//2, 20, text="Yüzey Alanı - Isı Transferi", fill="white", font=("Arial", 11, "bold"))
        self.canvas_grafik.create_line(ox3, y_bot, ox3, y1_top, fill="white", width=2)
        self.canvas_grafik.create_line(ox3, y_bot, ex3, y_bot, fill="white", width=2)

        points_q = []
        max_area = A * 2.5 if A > 0 else 2.5
        for i in range(20):
            a_t = 0.1 + (i / 19) * max_area
            ntu_t = (U * a_t) / C_min
            eps_t = (1 - math.exp(-ntu_t * (1 - C_r))) / (1 - C_r * math.exp(-ntu_t * (1 - C_r))) if C_r != 1 else ntu_t / (1 + ntu_t)
            q_t = (eps_t * q_max) / 1000 # kW

            px = ox3 + (a_t / max_area) * (ex3 - ox3)
            py = y_bot - ((q_t / (q_max/1000 * 1.2)) * (y_bot - y1_top))
            points_q.append((px, py))

        for i in range(len(points_q)-1):
            self.canvas_grafik.create_line(points_q[i][0], points_q[i][1], points_q[i+1][0], points_q[i+1][1], fill="#magenta", width=2)

        cur_a_x = ox3 + (A / max_area) * (ex3 - ox3)
        self.canvas_grafik.create_line(cur_a_x, y_bot, cur_a_x, y1_top, fill="cyan", dash=(4,4))
        self.canvas_grafik.create_text(cur_a_x, y1_top-10, text=f"A:{A:.2f}m²", fill="cyan", font=("Arial", 8))

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

            C_e = m_dot_e * cp_e
            C_s = m_dot_s * cp_s
            C_min = min(C_e, C_s)
            C_max = max(C_e, C_s)
            C_r = C_min / C_max
            
            NTU = (U * A) / C_min
            epsilon = (1 - math.exp(-NTU * (1 - C_r))) / (1 - C_r * math.exp(-NTU * (1 - C_r))) if C_r != 1 else NTU / (1 + NTU)
            
            q_max = C_min * (T_e_in - T_s_in)
            q = epsilon * q_max
            
            T_e_out = T_e_in - (q / C_e)
            T_s_out = T_s_in + (q / C_s)

            delta_T1 = T_e_in - T_s_out
            delta_T2 = T_e_out - T_s_in
            LMTD = (delta_T1 - delta_T2) / math.log(delta_T1 / delta_T2) if delta_T1 != delta_T2 and delta_T1/delta_T2 > 0 else 0

            self.sema_ciz(T_e_in, T_s_in, T_e_out, T_s_out)

            if T_e_out > 200:
                durum_renk = "#aa2222"
                durum_mesaj = f"⚠️ KRİTİK DURUM: {motor_tipi} Çıkış Sıcaklığı Çok Yüksek! Soğutma yetersiz."
            elif 120 <= T_e_out <= 200:
                durum_renk = "#22aa55"
                durum_mesaj = f"✅ OPTİMUM TASARIM: {motor_tipi} İdeal Isı Transfer Bölgesinde."
            else:
                durum_renk = "#aaaa22"
                durum_mesaj = f"⚠️ UYARI: Sıcaklık çok düşük. Egzoz gazı yoğuşma ve kurumlanma yapabilir."

            self.renk_bar.configure(fg_color=durum_renk, text=durum_mesaj)

            sonuc_metni = (
                f"====================================================================\n"
                f" ANALİZ RAPORU TİPİ : {motor_tipi.upper()}\n"
                f"====================================================================\n"
                f" Motor Gücü Başlangıç Değeri  : {P_motor:.2f} kW\n"
                f" Egzoz Gazı Çıkış Sıcaklığı   : {T_e_out:.2f} °C\n"
                f" Soğutma Sıvısı Çıkış Sıcaklığı: {T_s_out:.2f} °C\n"
                f" Gerçekleşen Isı Transferi    : {q/1000:.2f} kW\n"
                f" Cihaz Etkinlik Oranı (Verim) : % {epsilon*100:.2f}\n"
                f" LMTD Değeri                  : {LMTD:.2f} °C\n"
                f" Hesaplanan NTU Boyutsuz Sayısı: {NTU:.4f}\n"
                f"===================================================================="
            )
            self.txt_sonuc.delete("0.0", "end")
            self.txt_sonuc.insert("0.0", sonuc_metni)

            # Yerli çizim motorunu tetikle
            self.update()
            self.yerli_grafik_ciz(T_e_in, T_e_out, T_s_in, T_s_out, NTU, A, C_r, q_max, C_e, U, C_min)

        except Exception as e:
            self.txt_sonuc.delete("0.0", "end")
            self.txt_sonuc.insert("0.0", f"Hata Oluştu! Detay: {str(e)}")

if __name__ == "__main__":
    app = EGRCoolerApp()
    app.mainloop()
