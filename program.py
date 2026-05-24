import customtkinter as ctk
import math
import os
from tkinter import filedialog, messagebox

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class EGRGelis_mis_Laboratuvar(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("EGR Cooler Ar-Ge ve Termal Analiz Laboratuvarı v5.0 (Tam Entegre)")
        self.geometry("1300x920")
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

        self.son_analiz_raporu = {}

        # Üst Başlık ve İmza (Güncellendi)
        self.lbl_imza = ctk.CTkLabel(
            self,
            text="Bu program Enes Çelik (@enes_ce1ik) tarafından geliştirilmiştir.",
            font=("Arial", 13, "italic"),
            text_color="#aaaaaa"
        )
        self.lbl_imza.pack(side="top", pady=5)

        # Sekmeli Ana Yapı
        self.tabview = ctk.CTkTabview(self, width=1260, height=820)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)

        self.tab_ana = self.tabview.add("Giriş & Termal Simülasyon")
        self.tab_sihirbaz = self.tabview.add("🛠️ Geometri, Alan & U Hesaplama")
        self.tab_reynolds = self.tabview.add("🌊 Reynolds & Akış Analizi")
        self.tab_grafik = self.tabview.add("📊 Gelişmiş Grafik Paneli")

        self.setup_sekme_ana()
        self.setup_sekme_sihirbaz()
        self.setup_sekme_reynolds()
        self.setup_sekme_grafik()

        # İlk Çizim Tetiklemeleri
        self.update()
        self.hesapla(hafizaya_yaz=True)

    # ----------------------------------------------------------------
    # SEKME 1: ANA SİMÜLASYON EKRANI TASARIMI
    # ----------------------------------------------------------------
    def setup_sekme_ana(self):
        self.sol_frame = ctk.CTkScrollableFrame(self.tab_ana, width=460)
        self.sol_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.sag_frame = ctk.CTkFrame(self.tab_ana)
        self.sag_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(self.sol_frame, text="Isı Değiştirici Akış Yönü:", font=("Arial", 12, "bold")).pack(pady=(10, 2), padx=15, anchor="w")
        self.combo_akis_tipi = ctk.CTkOptionMenu(
            self.sol_frame,
            values=["Zıt Akış (Counter-Flow)", "Paralel Akış (Parallel-Flow)"],
            command=lambda x: self.hesapla()
        )
        self.combo_akis_tipi.pack(pady=2, padx=15, fill="x")

        ctk.CTkLabel(self.sol_frame, text="Egzoz Gazı / Yakıt Tipi:", font=("Arial", 12, "bold")).pack(pady=(10, 2), padx=15, anchor="w")
        self.combo_egzoz = ctk.CTkOptionMenu(
            self.sol_frame,
            values=list(self.egzoz_veritabanı.keys()),
            command=lambda x: self.hesapla()
        )
        self.combo_egzoz.pack(pady=2, padx=15, fill="x")

        ctk.CTkLabel(self.sol_frame, text="Soğutucu Akışkan Tipi:", font=("Arial", 12, "bold")).pack(pady=(10, 2), padx=15, anchor="w")
        self.combo_sogutucu = ctk.CTkOptionMenu(
            self.sol_frame,
            values=list(self.sogutucu_veritabanı.keys()),
            command=lambda x: self.hesapla()
        )
        self.combo_sogutucu.pack(pady=2, padx=15, fill="x")

        nav_frame = ctk.CTkFrame(self.sol_frame, fg_color="transparent")
        nav_frame.pack(pady=10, padx=15, fill="x")
        self.btn_geri = ctk.CTkButton(nav_frame, text="⬅ Geri", width=90, command=self.gecmis_geri, state="disabled")
        self.btn_geri.pack(side="left", padx=2)
        self.btn_ileri = ctk.CTkButton(nav_frame, text="İleri ➡", width=90, command=self.gecmis_ileri, state="disabled")
        self.btn_ileri.pack(side="right", padx=2)

        self.ent_motor_gucu = self.create_num_input(self.sol_frame, "Motor Gücü [kW]:", "120")
        self.ent_deb_e = self.create_num_input(self.sol_frame, "Egzoz Debisi (ṁ_e) [kg/s]:", "0.08")
        self.ent_temp_ei = self.create_num_input(self.sol_frame, "Egzoz Giriş Sıcaklığı [°C]:", "450")
        self.ent_deb_s = self.create_num_input(self.sol_frame, "Sıvı Debisi (ṁ_s) [kg/s]:", "0.5")
        self.ent_temp_si = self.create_num_input(self.sol_frame, "Sıvı Giriş Sıcaklığı [°C]:", "85")
        
        # U Katsayısı artık bilgi/çıkış amaçlıdır (Dinamik hesaplanır)
        self.ent_u_katsayi = self.create_num_input(self.sol_frame, "Dinamik U Katsayısı [W/m²K]:", "250")
        self.ent_u_katsayi.configure(fg_color="#2d3436", text_color="#00cec9") # Belirgin renk

        ctk.CTkLabel(self.sol_frame, text="Canlı Alan Ayarı (A) [m²]:", font=("Arial", 12, "bold")).pack(pady=(15, 0), padx=15, anchor="w")
        self.slider_alan = ctk.CTkSlider(self.sol_frame, from_=0.1, to=3.5, number_of_steps=68, command=self.slider_tetiklendi)
        self.slider_alan.set(1.2)
        self.slider_alan.pack(pady=2, padx=15, fill="x")
        self.lbl_slider_deger = ctk.CTkLabel(self.sol_frame, text="Mevcut Alan: 1.20 m²", font=("Arial", 11, "italic"), text_color="cyan")
        self.lbl_slider_deger.pack(pady=0, padx=15, anchor="e")

        self.btn_hesapla = ctk.CTkButton(
            self.sol_frame, text="SİMÜLASYONU ÇALIŞTIR",
            font=("Arial", 14, "bold"), command=self.hesapla, fg_color="#1f538d"
        )
        self.btn_hesapla.pack(pady=15, padx=15, fill="x")

        self.btn_pdf = ctk.CTkButton(
            self.sol_frame, text="📄 METİN RAPORU OLARAK KAYDET",
            font=("Arial", 13, "bold"), command=self.rapor_txt_uret,
            fg_color="#22aa55", hover_color="#1a8844"
        )
        self.btn_pdf.pack(pady=5, padx=15, fill="x")

        # Sağ Panel Şema alanı (Düzeltildi)
        self.canvas_sema = ctk.CTkCanvas(self.sag_frame, width=650, height=320, bg="#1c1c1c", highlightthickness=0)
        self.canvas_sema.pack(pady=10, padx=10, fill="x")

        self.txt_sonuc = ctk.CTkTextbox(self.sag_frame, font=("Courier New", 12))
        self.txt_sonuc.pack(pady=10, padx=10, fill="both", expand=True)

        self.renk_bar = ctk.CTkLabel(
            self.sag_frame, text="Sistem Hazır",
            font=("Arial", 13, "bold"), fg_color="#555555", height=45, text_color="white"
        )
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
    # SEKME 2: GEOMETRİ & ALAN + U KATSAYISI SİHİRBAZI
    # ----------------------------------------------------------------
    def setup_sekme_sihirbaz(self):
        ana = ctk.CTkScrollableFrame(self.tab_sihirbaz)
        ana.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(ana, text="🛠️ Geometri, Yüzey Alanı ve U Katsayısı Hesaplama Merkezi", font=("Arial", 15, "bold")).pack(pady=(12, 2))
        ctk.CTkLabel(ana, text="Kanal profilinizi seçin → boyutları girin → Simülasyona aktarın.", font=("Arial", 11, "italic"), text_color="#aaaaaa").pack(pady=(0, 10))

        frm_alan = ctk.CTkFrame(ana, border_width=2, border_color="#3a6186")
        frm_alan.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(frm_alan, text="📐  YÜZEY ALANI VE HİDROLİK ÇAP HESAPLAYICI", font=("Arial", 13, "bold"), text_color="#74b9ff").pack(pady=(10, 4), padx=15, anchor="w")

        profil_satir = ctk.CTkFrame(frm_alan, fg_color="transparent")
        profil_satir.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(profil_satir, text="Kanal / Boru Profili:", font=("Arial", 11, "bold"), width=220, anchor="w").pack(side="left")
        self.combo_profil = ctk.CTkOptionMenu(
            profil_satir,
            values=["Yuvarlak Boru (Circular)", "Dikdörtgen Kanal (Rectangular)", "Kare Kanal (Square)", "Eliptik Boru (Elliptical)", "Üçgen Kanal (Triangular)", "Altıgen Kanal (Hexagonal)"],
            command=self._profil_degisti, width=260
        )
        self.combo_profil.pack(side="left", padx=8)

        self.frm_profil_giris = ctk.CTkFrame(frm_alan, fg_color="#1e1e2e", corner_radius=8)
        self.frm_profil_giris.pack(fill="x", padx=15, pady=6)

        self.ent_alan_L  = self.create_num_input(frm_alan, "Kanal / Boru Etkin Uzunluğu (L) [mm]:", "350")
        self.ent_alan_N  = self.create_num_input(frm_alan, "Toplam Kanal / Boru Sayısı (N) [Adet]:", "90")

        self.lbl_formul = ctk.CTkLabel(frm_alan, text="", font=("Arial", 10, "italic"), text_color="#fdcb6e", wraplength=800, justify="left")
        self.lbl_formul.pack(padx=15, pady=2, anchor="w")

        sonuc_satir = ctk.CTkFrame(frm_alan, fg_color="transparent")
        sonuc_satir.pack(fill="x", padx=15, pady=(6, 12))
        self.lbl_alan_sonuc = ctk.CTkLabel(sonuc_satir, text="Alan: -- m² | Dh: -- mm", font=("Arial", 13, "bold"), text_color="cyan", width=350, anchor="w")
        self.lbl_alan_sonuc.pack(side="left")
        ctk.CTkButton(sonuc_satir, text="Hesapla & Geometriyi Aktar 💾", font=("Arial", 12, "bold"), width=260, command=self.sihirbazdan_aktar, fg_color="#e67e22", hover_color="#d35400").pack(side="right")

        self._profil_giris_widgetlari = {}
        self._profil_degisti("Yuvarlak Boru (Circular)")

        # U Katsayısı Duvar Direnci Modülü
        frm_u = ctk.CTkFrame(ana, border_width=2, border_color="#6c5ce7")
        frm_u.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(frm_u, text="🔬  DUVAR VE KİRLENME DİRENCİ (U KATSAYISI İÇİN)", font=("Arial", 13, "bold"), text_color="#a29bfe").pack(pady=(10, 4), padx=15, anchor="w")
        ctk.CTkLabel(frm_u, text="Program h_iç katsayısını Reynolds'tan otomatik hesaplar. Aşağıda duvar özelliklerini belirtin.", font=("Arial", 10, "italic"), text_color="#aaaaaa").pack(padx=15, anchor="w")

        malz_satir = ctk.CTkFrame(frm_u, fg_color="transparent")
        malz_satir.pack(fill="x", padx=15, pady=6)
        ctk.CTkLabel(malz_satir, text="Duvar Malzemesi:", font=("Arial", 11, "bold"), width=220, anchor="w").pack(side="left")
        self.malzeme_veritabani = {
            "Paslanmaz Çelik 316L (k=16 W/mK)": 16.0, "Alüminyum 6061 (k=167 W/mK)": 167.0, "Bakır (k=385 W/mK)": 385.0,
            "Titanyum Ti-6Al-4V (k=7 W/mK)": 7.0, "Manuel Giriş": None
        }
        self.combo_malzeme = ctk.CTkOptionMenu(malz_satir, values=list(self.malzeme_veritabani.keys()), command=self._malzeme_degisti, width=300)
        self.combo_malzeme.pack(side="left", padx=8)

        self.ent_u_h_dis  = self.create_num_input(frm_u, "Dış (Soğutucu) Taraf h_dış [W/m²K]:", "4500")
        self.ent_u_t      = self.create_num_input(frm_u, "Boru Et Kalınlığı t [mm]:", "1.0")

        self.frm_k_manuel = ctk.CTkFrame(frm_u, fg_color="transparent")
        self.ent_u_k = self.create_num_input(self.frm_k_manuel, "Isıl İletkenlik k [W/mK]:", "16")

        fouling_satir = ctk.CTkFrame(frm_u, fg_color="transparent")
        fouling_satir.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(fouling_satir, text="Kirlenme (Fouling) Direnci [m²K/W]:", font=("Arial", 11, "bold"), width=340, anchor="w").pack(side="left")
        self.ent_u_fouling = ctk.CTkEntry(fouling_satir, width=100)
        self.ent_u_fouling.insert(0, "0.00015")
        self.ent_u_fouling.pack(side="right")

        ctk.CTkLabel(frm_u, text="* Not: U değeri simülasyon çalıştırıldığında dinamik hesaplanacaktır.", font=("Arial", 10, "italic"), text_color="#fdcb6e").pack(padx=15, pady=10, anchor="w")

    def _profil_degisti(self, secim):
        for w in self.frm_profil_giris.winfo_children():
            w.destroy()
        self._profil_giris_widgetlari = {}

        tanim = {
            "Yuvarlak Boru (Circular)": {"alanlar": [("İç Çap d [mm]", "10")], "formul": "Ak = πd²/4  |  Dh = d"},
            "Dikdörtgen Kanal (Rectangular)": {"alanlar": [("Genişlik a [mm]", "20"), ("Yükseklik b [mm]", "6")], "formul": "Ak = a*b  |  Dh = 2ab/(a+b)"},
            "Kare Kanal (Square)": {"alanlar": [("Kenar a [mm]", "10")], "formul": "Ak = a²  |  Dh = a"},
            "Eliptik Boru (Elliptical)": {"alanlar": [("Büyük Yarı Eksen a [mm]", "12"), ("Küçük Yarı Eksen b [mm]", "5")], "formul": "Ak = πab  |  Dh = 4Ak/Çevre"},
            "Üçgen Kanal (Triangular)": {"alanlar": [("Taban c [mm]", "12"), ("Yükseklik h [mm]", "10")], "formul": "Ak = c*h/2  |  Dh = 4Ak/Çevre"},
            "Altıgen Kanal (Hexagonal)": {"alanlar": [("Kenar s [mm]", "6")], "formul": "Ak = 3√3 s² / 2  |  Dh = s√3"}
        }

        if secim not in tanim: return
        for etiket, varsayilan in tanim[secim]["alanlar"]:
            satir = ctk.CTkFrame(self.frm_profil_giris, fg_color="transparent")
            satir.pack(fill="x", padx=10, pady=3)
            ctk.CTkLabel(satir, text=etiket, font=("Arial", 11, "bold"), width=240, anchor="w").pack(side="left")
            ent = ctk.CTkEntry(satir, width=100)
            ent.insert(0, varsayilan)
            ent.pack(side="right")
            self._profil_giris_widgetlari[etiket] = ent
        self.lbl_formul.configure(text=f"📌 Formül:  {tanim[secim]['formul']}")

    def _malzeme_degisti(self, secim):
        if secim == "Manuel Giriş": self.frm_k_manuel.pack(fill="x", padx=15)
        else: self.frm_k_manuel.pack_forget()

    def sihirbazdan_aktar(self):
        try:
            profil = self.combo_profil.get()
            L = float(self.ent_alan_L.get()) / 1000.0
            N = float(self.ent_alan_N.get())
            if L <= 0 or N <= 0: raise ValueError("L ve N sıfırdan büyük olmalıdır.")

            w = self._profil_giris_widgetlari
            vals = [float(v.get()) for v in w.values()]

            if "Yuvarlak" in profil:
                d = vals[0] / 1000.0
                cevre = math.pi * d
                Ak_m2 = math.pi * (d**2) / 4
                Dh_mm = d * 1000.0
            elif "Dikdörtgen" in profil:
                a, b = vals[0]/1000.0, vals[1]/1000.0
                cevre = 2 * (a + b)
                Ak_m2 = a * b
                Dh_mm = (2 * a * b / (a + b)) * 1000.0
            elif "Kare" in profil:
                a = vals[0] / 1000.0
                cevre = 4 * a
                Ak_m2 = a**2
                Dh_mm = a * 1000.0
            elif "Eliptik" in profil:
                a, b = vals[0]/1000.0, vals[1]/1000.0
                cevre = math.pi * math.sqrt(2*(a**2 + b**2) - (a-b)**2 / 2)
                Ak_m2 = math.pi * a * b
                Dh_mm = (4 * Ak_m2 / cevre) * 1000.0
            elif "Üçgen" in profil:
                c, h = vals[0]/1000.0, vals[1]/1000.0
                kenar = math.sqrt((c/2)**2 + h**2)
                cevre = c + 2 * kenar
                Ak_m2 = c * h / 2
                Dh_mm = (4 * Ak_m2 / cevre) * 1000.0
            elif "Altıgen" in profil:
                s = vals[0] / 1000.0
                cevre = 6 * s
                Ak_m2 = (3 * math.sqrt(3) / 2) * (s**2)
                Dh_mm = s * math.sqrt(3) * 1000.0

            alan = cevre * L * N
            Ak_mm2 = Ak_m2 * 1e6

            self.lbl_alan_sonuc.configure(text=f"Alan: {alan:.4f} m² | Dh: {Dh_mm:.2f} mm | Ak: {Ak_mm2:.1f} mm²")
            self.slider_alan.set(min(max(alan, 0.1), 3.5))
            self.lbl_slider_deger.configure(text=f"Mevcut Alan: {alan:.2f} m²")

            # Ana motor (Akış analizi) değerlerini otomatik güncelle
            self.ent_D_h.delete(0, "end"); self.ent_D_h.insert(0, f"{Dh_mm:.2f}")
            self.ent_A_kesit.delete(0, "end"); self.ent_A_kesit.insert(0, f"{Ak_mm2:.2f}")
            self.ent_N_kanal.delete(0, "end"); self.ent_N_kanal.insert(0, f"{int(N)}")

            messagebox.showinfo("Başarılı", "Geometrik hesaplamalar Akış Analizi ve Simülasyon motoruna aktarıldı!")
            self.tabview.set("Giriş & Termal Simülasyon")
            self.hesapla()
        except Exception as e:
            messagebox.showerror("Hata", f"Geometri Hatası: {str(e)}")

    # ----------------------------------------------------------------
    # SEKME 3: REYNOLDS & AKIŞ ANALİZİ (GÜNCELLENDİ)
    # ----------------------------------------------------------------
    def setup_sekme_reynolds(self):
        ana = ctk.CTkScrollableFrame(self.tab_reynolds)
        ana.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(ana, text="🌊  Dinamik Akışkan & Reynolds Analiz Merkezi", font=("Arial", 15, "bold")).pack(pady=(12, 2))
        ctk.CTkLabel(ana, text="Geometriden aktarılan verilerle gazın akış profili ve U katsayısı %100 entegre hesaplanır.", font=("Arial", 11, "italic"), text_color="#aaaaaa").pack(pady=(0, 10))

        param_frame = ctk.CTkFrame(ana, border_width=1, border_color="#555")
        param_frame.pack(fill="x", padx=10, pady=5)
        
        # Dinamik özellikler burada gösterilir
        self.ent_D_h       = self.create_num_input(param_frame, "Hidrolik Çap D_h [mm]:", "10.0")
        self.ent_N_kanal   = self.create_num_input(param_frame, "Toplam Kanal Sayısı N:", "90")
        self.ent_A_kesit   = self.create_num_input(param_frame, "Tek Kanal Kesit Alanı A_k [mm²]:", "78.5")
        
        ctk.CTkLabel(param_frame, text="* Not: Gaz özellikleri (ρ, μ, Pr, k) giriş sıcaklığına göre sistem tarafından dinamik hesaplanır.", text_color="cyan", font=("Arial", 10, "italic")).pack(pady=5)
        
        self.lbl_re_bar = ctk.CTkLabel(ana, text="— Bekleniyor —", font=("Arial", 13, "bold"), fg_color="#333333", height=42, text_color="white", corner_radius=6)
        self.lbl_re_bar.pack(fill="x", padx=10, pady=10)

        kolon_frame = ctk.CTkFrame(ana, fg_color="transparent")
        kolon_frame.pack(fill="both", expand=True, padx=10)
        sol = ctk.CTkFrame(kolon_frame, border_width=2, border_color="#0984e3")
        sol.pack(side="left", fill="both", expand=True, padx=(0, 6))
        sag = ctk.CTkFrame(kolon_frame, border_width=2, border_color="#00b894")
        sag.pack(side="right", fill="both", expand=True, padx=(6, 0))

        ctk.CTkLabel(sol, text="📐  AKIŞ REJİMİ & NUSSELT", font=("Arial", 12, "bold"), text_color="#74b9ff").pack(pady=(10, 4), padx=12, anchor="w")
        self.txt_re_akis = ctk.CTkTextbox(sol, font=("Courier New", 11), height=260)
        self.txt_re_akis.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        ctk.CTkLabel(sag, text="⚠️  MÜHENDİSLİK UYARILARI", font=("Arial", 12, "bold"), text_color="#fdcb6e").pack(pady=(10, 4), padx=12, anchor="w")
        self.txt_re_uyari = ctk.CTkTextbox(sag, font=("Courier New", 11), height=260)
        self.txt_re_uyari.pack(fill="both", expand=True, padx=8, pady=(0, 10))

    # ----------------------------------------------------------------
    # SEKME 4: GRAFİKLER & ŞEMA ÇİZİMİ
    # ----------------------------------------------------------------
    def setup_sekme_grafik(self):
        self.canvas_grafik = ctk.CTkCanvas(self.tab_grafik, bg="#1a1a1a", highlightthickness=0)
        self.canvas_grafik.pack(fill="both", expand=True, padx=15, pady=15)

    def sema_ciz(self, T_ei, T_si, T_eo, T_so, akis_tipi, profil_ismi):
        if not hasattr(self, 'canvas_sema') or self.canvas_sema is None: return
        self.canvas_sema.delete("all")

        mid_y = 160
        kanal_tipi = profil_ismi.split(" ")[0].upper()

        self.canvas_sema.create_oval(140, mid_y-60, 200, mid_y+60, fill="#2c3e50", outline="#7f8c8d", width=2)
        self.canvas_sema.create_oval(480, mid_y-60, 540, mid_y+60, fill="#2c3e50", outline="#7f8c8d", width=2)
        self.canvas_sema.create_rectangle(170, mid_y-50, 510, mid_y+50, fill="#2b2b2b", outline="#7f8c8d", width=2)

        for i in range(5):
            self.canvas_sema.create_line(175, (mid_y-35) + i*18, 505, (mid_y-35) + i*18, fill="#555555", width=2)

        self.canvas_sema.create_text(340, mid_y, text=f"EGR BUNDLE COOLER GÖVDE ({kanal_tipi})", fill="#ecf0f1", font=("Arial", 11, "bold"))

        self.canvas_sema.create_rectangle(90, mid_y-20, 140, mid_y+20, fill="#3a3a3a", outline="#7f8c8d", width=1)
        self.canvas_sema.create_line(20, mid_y, 95, mid_y, fill="#e74c3c", width=6, arrow="last")
        self.canvas_sema.create_text(55, mid_y-35, text=f"Egzoz Giriş\n{T_ei:.1f} °C", fill="#ff7675", font=("Arial", 11, "bold"), justify="center")

        self.canvas_sema.create_rectangle(540, mid_y-20, 590, mid_y+20, fill="#3a3a3a", outline="#7f8c8d", width=1)
        self.canvas_sema.create_line(585, mid_y, 660, mid_y, fill="#e67e22", width=6, arrow="last")
        self.canvas_sema.create_text(625, mid_y-35, text=f"Egzoz Çıkış\n{T_eo:.1f} °C", fill="#f39c12", font=("Arial", 11, "bold"), justify="center")

        if "Zıt" in akis_tipi:
            self.canvas_sema.create_rectangle(470, mid_y-95, 505, mid_y-50, fill="#2c3e50", outline="#7f8c8d", width=1)
            self.canvas_sema.create_line(488, mid_y-120, 488, mid_y-90, fill="#3498db", width=5, arrow="last")
            self.canvas_sema.create_text(488, mid_y-135, text=f"Sıvı Giriş: {T_si:.1f} °C", fill="#74b9ff", font=("Arial", 10, "bold"), anchor="s")

            self.canvas_sema.create_rectangle(175, mid_y+50, 210, mid_y+95, fill="#2c3e50", outline="#7f8c8d", width=1)
            self.canvas_sema.create_line(192, mid_y+90, 192, mid_y+120, fill="#1abc9c", width=5, arrow="last")
            self.canvas_sema.create_text(192, mid_y+135, text=f"Sıvı Çıkış: {T_so:.1f} °C", fill="#55efc4", font=("Arial", 10, "bold"), anchor="n")
            
            self.canvas_sema.create_text(340, mid_y+85, text="⬅ MODEL YÖNÜ: ZIT AKIŞLI (COUNTER-FLOW)", fill="#74b9ff", font=("Arial", 10, "bold"))
        else:
            self.canvas_sema.create_rectangle(175, mid_y-95, 210, mid_y-50, fill="#2c3e50", outline="#7f8c8d", width=1)
            self.canvas_sema.create_line(192, mid_y-120, 192, mid_y-90, fill="#3498db", width=5, arrow="last")
            self.canvas_sema.create_text(192, mid_y-135, text=f"Sıvı Giriş: {T_si:.1f} °C", fill="#74b9ff", font=("Arial", 10, "bold"), anchor="s")

            self.canvas_sema.create_rectangle(470, mid_y+50, 505, mid_y+95, fill="#2c3e50", outline="#7f8c8d", width=1)
            self.canvas_sema.create_line(488, mid_y+90, 488, mid_y+120, fill="#1abc9c", width=5, arrow="last")
            self.canvas_sema.create_text(488, mid_y+135, text=f"Sıvı Çıkış: {T_so:.1f} °C", fill="#55efc4", font=("Arial", 10, "bold"), anchor="n")
            
            self.canvas_sema.create_text(340, mid_y+85, text="➡ MODEL YÖNÜ: PARALEL AKIŞLI (CO-CURRENT)", fill="#e74c3c", font=("Arial", 10, "bold"))

    def yerli_grafik_ciz(self, T_ei, T_eo, T_si, T_so, NTU, A, C_r, q_max, C_e, U, C_min, akis_tipi):
        if not hasattr(self, 'canvas_grafik') or self.canvas_grafik is None: return
        self.canvas_grafik.delete("all")
        w, h = self.canvas_grafik.winfo_width(), self.canvas_grafik.winfo_height()
        if w < 200: w, h = 1150, 650

        g_w = (w - 160) // 3
        g_h = h - 120
        y_bot = 60 + g_h - 40

        def eksen_ciz(ox, baslik, xl, yl):
            cx = ox + g_w - 30
            self.canvas_grafik.create_text(ox + g_w // 2, 30, text=baslik, fill="white", font=("Arial", 12, "bold"))
            self.canvas_grafik.create_line(ox, y_bot, ox, 60, fill="white", width=2)
            self.canvas_grafik.create_line(ox, y_bot, cx, y_bot, fill="white", width=2)
            self.canvas_grafik.create_text(ox, y_bot + 20, text=xl, fill="#b2bec3", font=("Arial", 9), anchor="n")
            self.canvas_grafik.create_text(ox - 10, (60 + y_bot) // 2, text=yl, fill="#b2bec3", font=("Arial", 9), anchor="e", angle=90)
            return cx

        ox1 = 60
        ex1 = eksen_ciz(ox1, "Sıcaklık Değişim Profili", "Konum (EGR Boyu)", "Sıcaklık [°C]")
        max_t = max(T_ei, T_so, T_eo, T_si) + 40
        min_t = min(T_ei, T_so, T_eo, T_si) - 15
        t_span = max_t - min_t if max_t != min_t else 1.0

        def t_s(t): return y_bot - (((t - min_t) / t_span) * (y_bot - 60))

        self.canvas_grafik.create_line(ox1, t_s(T_ei), ex1, t_s(T_eo), fill="#ff7675", width=3)
        self.canvas_grafik.create_text(ox1 - 8, t_s(T_ei), text=f"{int(T_ei)}°C", fill="#ff7675", font=("Arial", 9), anchor="e")
        self.canvas_grafik.create_text(ex1 + 8, t_s(T_eo), text=f"{int(T_eo)}°C", fill="#f39c12", font=("Arial", 9), anchor="w")

        if "Zıt" in akis_tipi:
            self.canvas_grafik.create_line(ox1, t_s(T_so), ex1, t_s(T_si), fill="#74b9ff", width=3)
            self.canvas_grafik.create_text(ox1 - 8, t_s(T_so), text=f"{int(T_so)}°C", fill="#55efc4", font=("Arial", 9), anchor="e")
            self.canvas_grafik.create_text(ex1 + 8, t_s(T_si), text=f"{int(T_si)}°C", fill="#74b9ff", font=("Arial", 9), anchor="w")
        else:
            self.canvas_grafik.create_line(ox1, t_s(T_si), ex1, t_s(T_so), fill="#74b9ff", width=3)
            self.canvas_grafik.create_text(ox1 - 8, t_s(T_si), text=f"{int(T_si)}°C", fill="#74b9ff", font=("Arial", 9), anchor="e")
            self.canvas_grafik.create_text(ex1 + 8, t_s(T_so), text=f"{int(T_so)}°C", fill="#55efc4", font=("Arial", 9), anchor="w")

        ox2 = ex1 + 80
        ex2 = eksen_ciz(ox2, "NTU - Çıkış Sıcaklığı Analizi", "NTU Sayısı", "Egzoz Çıkış [°C]")
        pts_n = []
        for i in range(35):
            n_t = 0.05 + (i / 34) * 5.0
            if "Zıt" in akis_tipi:
                eps_t = (1 - math.exp(-n_t * (1 - C_r))) / (1 - C_r * math.exp(-n_t * (1 - C_r))) if C_r != 1 else n_t / (1 + n_t)
            else:
                eps_t = (1 - math.exp(-n_t * (1 + C_r))) / (1 + C_r)

            te_out_t = T_ei - ((eps_t * q_max) / C_e)
            px = ox2 + (n_t / 5.0) * (ex2 - ox2)
            py = y_bot - (((te_out_t - min_t) / t_span) * (y_bot - 60))
            pts_n.append((px, py))

        for i in range(len(pts_n) - 1):
            self.canvas_grafik.create_line(pts_n[i][0], pts_n[i][1], pts_n[i + 1][0], pts_n[i + 1][1], fill="#2ecc71", width=2)

        cur_ntu_x = ox2 + (min(NTU, 5.0) / 5.0) * (ex2 - ox2)
        self.canvas_grafik.create_line(cur_ntu_x, y_bot, cur_ntu_x, 60, fill="yellow", dash=(5, 5))
        self.canvas_grafik.create_text(cur_ntu_x, 50, text=f"NTU:{NTU:.2f}", fill="yellow", font=("Arial", 9, "bold"))

        ox3 = ex2 + 80
        ex3 = eksen_ciz(ox3, "Yüzey Alanı - Isı Gücü Etkisi", "Alan [m²]", "Isı Gücü [kW]")
        pts_q = []
        m_a_plot = A * 2.5 if A > 0 else 3.0
        q_lim_kw = (q_max / 1000.0) * 1.15 if q_max > 0 else 1.0

        for i in range(35):
            a_t = 0.05 + (i / 34) * m_a_plot
            ntu_t = (U * a_t) / C_min if C_min > 0 else 0
            if "Zıt" in akis_tipi:
                eps_t = (1 - math.exp(-ntu_t * (1 - C_r))) / (1 - C_r * math.exp(-ntu_t * (1 - C_r))) if C_r != 1 else ntu_t / (1 + ntu_t)
            else:
                eps_t = (1 - math.exp(-ntu_t * (1 + C_r))) / (1 + C_r)

            qk_t = (eps_t * q_max) / 1000.0
            px = ox3 + (a_t / m_a_plot) * (ex3 - ox3)
            py = y_bot - ((qk_t / q_lim_kw) * (y_bot - 60))
            pts_q.append((px, py))

        for i in range(len(pts_q) - 1):
            self.canvas_grafik.create_line(pts_q[i][0], pts_q[i][1], pts_q[i + 1][0], pts_q[i + 1][1], fill="magenta", width=2)

        cur_a_x = ox3 + (A / m_a_plot) * (ex3 - ox3)
        self.canvas_grafik.create_line(cur_a_x, y_bot, cur_a_x, 60, fill="cyan", dash=(5, 5))
        self.canvas_grafik.create_text(cur_a_x, 50, text=f"A:{A:.2f}m²", fill="cyan", font=("Arial", 9, "bold"))

    # ----------------------------------------------------------------
    # TAM ENTEGRE TERMOMÜHENDİSLİK MOTORU
    # ----------------------------------------------------------------
    def hesapla(self, hafizaya_yaz=True):
        try:
            # 1. Temel Girdileri Oku
            akis_tipi = self.combo_akis_tipi.get()
            profil_ismi = self.combo_profil.get()
            egzoz_adi = self.combo_egzoz.get()
            sogutucu_adi = self.combo_sogutucu.get()

            cp_e = self.egzoz_veritabanı[egzoz_adi]
            cp_s = self.sogutucu_veritabanı[sogutucu_adi]

            P_motor = float(self.ent_motor_gucu.get())
            m_dot_e = float(self.ent_deb_e.get())
            T_e_in = float(self.ent_temp_ei.get())
            m_dot_s = float(self.ent_deb_s.get())
            T_s_in = float(self.ent_temp_si.get())
            A = self.slider_alan.get()

            if m_dot_e <= 0 or m_dot_s <= 0 or A <= 0:
                raise ValueError("Debi ve Alan değerleri sıfırdan büyük olmalıdır.")

            # 2. Dinamik Akışkan Özellikleri (T_e_in referans alınarak)
            T_k = T_e_in + 273.15
            rho_gaz = 101325 / (287 * T_k)  # İdeal Gaz Yasası (Hava/Egzoz Yaklaşımı)
            mu_gaz = 1.81e-5 * ((T_k)/293.15)**0.7 # Sutherland Viskozite
            k_gaz = 0.025 * ((T_k)/293.15)**0.8 # Isıl İletkenlik Yaklaşımı
            Pr_gaz = (mu_gaz * cp_e) / k_gaz if k_gaz > 0 else 0.72

            # 3. Geometri Bilgileri (Reynolds sekmesinden çekilir)
            D_h = float(self.ent_D_h.get()) / 1000.0
            N_kanal = float(self.ent_N_kanal.get())
            A_kesit = float(self.ent_A_kesit.get()) * 1e-6

            if D_h <= 0 or N_kanal <= 0 or A_kesit <= 0:
                raise ValueError("Boru çapı, kanal sayısı veya kesit alanı sıfır olamaz. Geometri Sihirbazını kontrol edin.")

            # 4. Reynolds ve Nusselt Hesabı (İç Isı Transferi - h_ic)
            v_kanal = m_dot_e / (N_kanal * A_kesit * rho_gaz)
            Re = (rho_gaz * v_kanal * D_h) / mu_gaz

            if Re < 2300:
                rejim = "LAMİNER"
                Nu = 3.66
            elif Re < 4000:
                rejim = "GEÇİŞ (Transition)"
                Nu = 3.66 + (Re - 2300) * (0.005) # Basit İnterpolasyon
            else:
                rejim = "TÜRBÜLANSLÜ"
                f = (0.790 * math.log(Re) - 1.64)**(-2)
                Nu = (f/8) * (Re - 1000) * Pr_gaz / (1 + 12.7 * math.sqrt(f/8) * (Pr_gaz**(2/3) - 1))

            h_ic = (Nu * k_gaz) / D_h

            # 5. Dış Dirençler ve Dinamik U Katsayısı
            malzeme_adi = self.combo_malzeme.get()
            k_duvar = self.malzeme_veritabani.get(malzeme_adi)
            if k_duvar is None: k_duvar = float(self.ent_u_k.get())
            
            t_duvar = float(self.ent_u_t.get()) / 1000.0
            h_dis = float(self.ent_u_h_dis.get())
            R_fouling = float(self.ent_u_fouling.get())

            R_toplam = (1.0 / h_ic) + (t_duvar / k_duvar) + (1.0 / h_dis) + (2 * R_fouling)
            U_dinamik = 1.0 / R_toplam if R_toplam > 0 else 0.1

            # U Değerini Ana Ekrana Yansıt
            self.ent_u_katsayi.delete(0, "end")
            self.ent_u_katsayi.insert(0, f"{U_dinamik:.2f}")

            # 6. Isı Değiştirici Termal Analizi (NTU-e)
            C_e = m_dot_e * cp_e
            C_s = m_dot_s * cp_s
            C_min = min(C_e, C_s)
            C_max = max(C_e, C_s)
            C_r = C_min / C_max

            NTU = (U_dinamik * A) / C_min

            if "Zıt" in akis_tipi:
                epsilon = (1 - math.exp(-NTU * (1 - C_r))) / (1 - C_r * math.exp(-NTU * (1 - C_r))) if C_r != 1 else NTU / (1 + NTU)
            else:
                epsilon = (1 - math.exp(-NTU * (1 + C_r))) / (1 + C_r)

            epsilon = min(max(epsilon, 0.0), 1.0)
            q_max = C_min * (T_e_in - T_s_in)
            if abs(q_max) < 1e-9:
                raise ValueError("Egzoz ve sıvı giriş sıcaklıkları eşit, ısı transferi yok.")

            q = epsilon * q_max
            T_e_out = T_e_in - (q / C_e)
            T_s_out = T_s_in + (q / C_s)

            if "Zıt" in akis_tipi:
                dt1, dt2 = T_e_in - T_s_out, T_e_out - T_s_in
            else:
                dt1, dt2 = T_e_in - T_s_in, T_e_out - T_s_out

            LMTD = (dt1 - dt2) / math.log(dt1 / dt2) if dt1 > 0 and dt2 > 0 and abs(dt1 - dt2) > 1e-6 else (dt1 + dt2) / 2.0

            # 7. Arayüz Güncellemeleri
            self.sema_ciz(T_e_in, T_s_in, T_e_out, T_s_out, akis_tipi, profil_ismi)
            self.yerli_grafik_ciz(T_e_in, T_e_out, T_s_in, T_s_out, NTU, A, C_r, q_max, C_e, U_dinamik, C_min, akis_tipi)

            self.son_analiz_raporu = {
                "akis_tipi": akis_tipi, "egzoz_adi": egzoz_adi, "sogutucu_adi": sogutucu_adi,
                "P_motor": P_motor, "m_dot_e": m_dot_e, "T_e_in": T_e_in, "m_dot_s": m_dot_s,
                "T_s_in": T_s_in, "U": U_dinamik, "A": A, "T_e_out": T_e_out, "T_s_out": T_s_out,
                "q_kw": q / 1000.0, "verim": epsilon * 100.0, "LMTD": LMTD, "NTU": NTU
            }

            sonuc_txt = (
                f"====================================================================\n"
                f"      EGR COOLER TERMAL MÜHENDİSLİK VE AR-GE ANALİZ RAPORU\n"
                f"====================================================================\n"
                f" Geliştiren Tasarımcı : Enes Çelik (@enes_ce1ik) Simülasyon\n"
                f"--------------------------------------------------------------------\n"
                f" * Hesaplanan Dinamik U Katsayısı : {U_dinamik:.1f} W/m²K\n"
                f" * Sistem Termal Etkinliği (Verim): % {epsilon * 100.0:.2f}\n"
                f" * Geri Kazanılan Toplam Isı Gücü : {q / 1000.0:.2f} kW\n"
                f"--------------------------------------------------------------------\n"
                f" * EGZOZ GAZ Çıkış Sıcaklığı      : {T_e_out:.2f} °C\n"
                f" * SOĞUTUCU SIVI Çıkış Sıcaklığı  : {T_s_out:.2f} °C\n"
                f"===================================================================="
            )
            self.txt_sonuc.delete("0.0", "end")
            self.txt_sonuc.insert("0.0", sonuc_txt)

            # Reynolds Sekmesi Güncellemesi
            self.lbl_re_bar.configure(text=f"Re = {Re:.0f} | {rejim} | Nu = {Nu:.1f} | h_iç = {h_ic:.0f} W/m²K | U = {U_dinamik:.0f}", fg_color="#00695c" if Re<2300 else ("#7f1d1d" if Re>=4000 else "#8d6e00"))
            re_txt = f"Gaz Yoğunluğu (ρ) = {rho_gaz:.3f} kg/m³\nViskozite (μ) = {mu_gaz:.2e} Pa.s\nAkış Hızı (v) = {v_kanal:.2f} m/s\nReynolds (Re) = {Re:.0f}\nİç Taşınım (h_iç) = {h_ic:.1f} W/m²K\nDinamik (U) = {U_dinamik:.1f} W/m²K"
            self.txt_re_akis.delete("0.0", "end")
            self.txt_re_akis.insert("0.0", re_txt)

            uyari_txt = "✅ Sistem İdeal Çalışıyor" if Re > 4000 else "⚠️ UYARI: Laminer/Geçiş Akışı! Gaz iyi soğumayabilir, debiyi artırın veya çapı daraltın."
            self.txt_re_uyari.delete("0.0", "end")
            self.txt_re_uyari.insert("0.0", uyari_txt)

            if T_e_out > 190:
                self.renk_bar.configure(fg_color="#c0392b", text="⚠️ KRİTİK SEVİYE: Egzoz gazı soğumuyor, alanı veya debiyi artırın.")
            elif 110 <= T_e_out <= 190:
                self.renk_bar.configure(fg_color="#27ae60", text="✅ İDEAL TASARIM: Optimum emisyon ve soğutma dengesi yakalandı.")
            else:
                self.renk_bar.configure(fg_color="#d35400", text="⚠️ YOĞUŞMA ALARMI: Çıkış çok soğuk, asit yoğuşabilir.")

            if hafizaya_yaz:
                self.gecmis_hafizaya_ekle([akis_tipi, egzoz_adi, sogutucu_adi, P_motor, m_dot_e, T_e_in, m_dot_s, T_s_in, U_dinamik, A])

        except ValueError as e:
            self.txt_sonuc.delete("0.0", "end")
            self.txt_sonuc.insert("0.0", f"Girdi Hatası: {str(e)}")
            self.renk_bar.configure(fg_color="#7f0000", text=f"⛔ GİRDİ HATASI: {str(e)}")
        except Exception as e:
            self.txt_sonuc.delete("0.0", "end")
            self.txt_sonuc.insert("0.0", f"Beklenmeyen Hata: {str(e)}")
            self.renk_bar.configure(fg_color="#7f0000", text="⛔ BEKLENMEYEN HATA")

    # ----------------------------------------------------------------
    # GARANTİLİ METİN RAPORLAMA ÇIKTI MOTORU (.txt)
    # ----------------------------------------------------------------
    def rapor_txt_uret(self):
        if not self.son_analiz_raporu:
            messagebox.showwarning("Uyarı", "Önce bir simülasyon çalıştırmanız gerekmektedir.")
            return

        try:
            dosya_yolu = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Metin Belgesi", "*.txt")], title="Mühendislik Raporunu Kaydet")
            if not dosya_yolu: return

            r = self.son_analiz_raporu

            rapor_metni = (
                f"====================================================================\n"
                f"      EGR COOLER TERMAL MÜHENDİSLİK VE AR-GE ANALİZ RAPORU\n"
                f"====================================================================\n"
                f" Geliştiren Tasarımcı : Enes Çelik (@enes_ce1ik) Simülasyon\n"
                f" Rapor Detayı         : Otomatik Çıktı ve Matris Şablonu\n"
                f"--------------------------------------------------------------------\n\n"
                f" [1] SİSTEM VE AKIŞKAN ÖZELLİKLERİ\n"
                f" --------------------------------------------------------------------\n"
                f" * Isı Değiştirici Akış Tipi      : {r['akis_tipi']}\n"
                f" * Kullanılan Motor Yakıt/Gaz Tipi: {r['egzoz_adi']}\n"
                f" * Seçilen Soğutucu Akışkan Tipi  : {r['sogutucu_adi']}\n"
                f" * Referans Motor Gücü            : {r['P_motor']:.1f} kW\n\n"
                f" [2] GEOMETRİK VE TERMAL GEÇİŞ VERİLERİ\n"
                f" --------------------------------------------------------------------\n"
                f" * Aktif Isı Transfer Alanı (A)   : {r['A']:.4f} m²\n"
                f" * Dinamik Isı Geçiş Katsayısı (U): {r['U']:.1f} W/m²K\n"
                f" * Logaritmik Ort. Sıcaklık Farkı : {r['LMTD']:.2f} °C\n"
                f" * Hesaplanan Sınır NTU Sayısı    : {r['NTU']:.4f}\n\n"
                f" [3] ENERJİ BİLANÇOSU VE SİMÜLASYON ÇIKTILARI\n"
                f" --------------------------------------------------------------------\n"
                f" * EGZOZ GAZ Giriş Sıcaklığı      : {r['T_e_in']:.1f} °C\n"
                f" * EGZOZ GAZ Çıkış Sıcaklığı      : {r['T_e_out']:.2f} °C\n"
                f" * SOĞUTUCU SIVI Giriş Sıcaklığı  : {r['T_s_in']:.1f} °C\n"
                f" * SOĞUTUCU SIVI Çıkış Sıcaklığı  : {r['T_s_out']:.2f} °C\n"
                f" * Geri Kazanılan Toplam Isı Gücü : {r['q_kw']:.2f} kW\n"
                f" * Sistem Termal Etkinliği (Verim): % {r['verim']:.2f}\n"
                f"====================================================================\n"
            )

            with open(dosya_yolu, "w", encoding="utf-8") as f:
                f.write(rapor_metni)

            messagebox.showinfo("Başarılı", f"Mühendislik analiz raporu başarıyla kaydedildi:\n{dosya_yolu}")
        except Exception as e:
            messagebox.showerror("Rapor Hatası", f"Rapor yazılırken sistemsel hata çıktı: {str(e)}")

    def gecmis_hafizaya_ekle(self, veri):
        if self.suanki_indeks == -1 or self.gecmis_hafiza[self.suanki_indeks] != veri:
            self.gecmis_hafiza = self.gecmis_hafiza[:self.suanki_indeks + 1]
            self.gecmis_hafiza.append(veri)
            self.suanki_indeks = len(self.gecmis_hafiza) - 1
            self.buton_durumlarini_guncelle()

    def buton_durumlarini_guncelle(self):
        self.btn_geri.configure(state="normal" if self.suanki_indeks > 0 else "disabled")
        self.btn_ileri.configure(state="normal" if self.suanki_indeks < len(self.gecmis_hafiza) - 1 else "disabled")

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
