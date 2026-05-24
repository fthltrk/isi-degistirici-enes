import customtkinter as ctk
import math
import os
from tkinter import filedialog, messagebox
 
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
 
 
class EGRGelis_mis_Laboratuvar(ctk.CTk):
    def __init__(self):
        super().__init__()
 
        self.title("EGR Cooler Ar-Ge ve Termal Analiz Laboratuvarı v4.8")
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
 
        # DÜZELTMİŞ: son_analiz_raporu başlangıç değeri tanımlandı (AttributeError önlenir)
        self.son_analiz_raporu = {}
 
        # Üst Başlık ve İmza
        self.lbl_imza = ctk.CTkLabel(
            self,
            text="Bu program Enes Çelik tarafından geliştirilmiştir.",
            font=("Arial", 13, "italic"),
            text_color="#aaaaaa"
        )
        self.lbl_imza.pack(side="top", pady=5)
 
        # Sekmeli Ana Yapı
        self.tabview = ctk.CTkTabview(self, width=1220, height=780)
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
 
        # 1. Akış Tipi Seçimi
        ctk.CTkLabel(self.sol_frame, text="Isı Değiştirici Akış Yönü:", font=("Arial", 12, "bold")).pack(pady=(10, 2), padx=15, anchor="w")
        self.combo_akis_tipi = ctk.CTkOptionMenu(
            self.sol_frame,
            values=["Zıt Akış (Counter-Flow)", "Paralel Akış (Parallel-Flow)"],
            command=lambda x: self.hesapla()
        )
        self.combo_akis_tipi.pack(pady=2, padx=15, fill="x")
 
        # 2. Egzoz Gazı Tipi
        ctk.CTkLabel(self.sol_frame, text="Egzoz Gazı / Yakıt Tipi:", font=("Arial", 12, "bold")).pack(pady=(10, 2), padx=15, anchor="w")
        self.combo_egzoz = ctk.CTkOptionMenu(
            self.sol_frame,
            values=list(self.egzoz_veritabanı.keys()),
            command=lambda x: self.hesapla()
        )
        self.combo_egzoz.pack(pady=2, padx=15, fill="x")
 
        # 3. Soğutucu Akışkan Tipi
        ctk.CTkLabel(self.sol_frame, text="Soğutucu Akışkan Tipi:", font=("Arial", 12, "bold")).pack(pady=(10, 2), padx=15, anchor="w")
        self.combo_sogutucu = ctk.CTkOptionMenu(
            self.sol_frame,
            values=list(self.sogutucu_veritabanı.keys()),
            command=lambda x: self.hesapla()
        )
        self.combo_sogutucu.pack(pady=2, padx=15, fill="x")
 
        # Geçmiş Butonları
        nav_frame = ctk.CTkFrame(self.sol_frame, fg_color="transparent")
        nav_frame.pack(pady=10, padx=15, fill="x")
        self.btn_geri = ctk.CTkButton(nav_frame, text="⬅ Geri", width=90, command=self.gecmis_geri, state="disabled")
        self.btn_geri.pack(side="left", padx=2)
        self.btn_ileri = ctk.CTkButton(nav_frame, text="İleri ➡", width=90, command=self.gecmis_ileri, state="disabled")
        self.btn_ileri.pack(side="right", padx=2)
 
        # Numerik Girdiler
        self.ent_motor_gucu = self.create_num_input(self.sol_frame, "Motor Gücü [kW]:", "120")
        self.ent_deb_e = self.create_num_input(self.sol_frame, "Egzoz Debisi (ṁ_e) [kg/s]:", "0.15")
        self.ent_temp_ei = self.create_num_input(self.sol_frame, "Egzoz Giriş Sıcaklığı [°C]:", "450")
        self.ent_deb_s = self.create_num_input(self.sol_frame, "Sıvı Debisi (ṁ_s) [kg/s]:", "0.5")
        self.ent_temp_si = self.create_num_input(self.sol_frame, "Sıvı Giriş Sıcaklığı [°C]:", "80")
        self.ent_u_katsayi = self.create_num_input(self.sol_frame, "Isı Transfer Katsayısı (U) [W/m²K]:", "280")
 
        # Reynolds & Tek Kanal Analizi Girdileri
        ctk.CTkLabel(self.sol_frame, text="── Reynolds & Tek Kanal Analizi ──",
                     font=("Arial", 11, "bold"), text_color="#fdcb6e").pack(pady=(12, 2), padx=15, anchor="w")
        self.ent_D_h       = self.create_num_input(self.sol_frame, "Hidrolik Çap D_h [mm]:", "11.4")
        self.ent_N_kanal   = self.create_num_input(self.sol_frame, "Toplam Kanal / Boru Sayısı N [adet]:", "90")
        self.ent_rho_egzoz = self.create_num_input(self.sol_frame, "Egzoz Gazı Yoğunluğu ρ [kg/m³]:", "0.45")
        self.ent_mu_egzoz  = self.create_num_input(self.sol_frame, "Dinamik Viskozite μ [×10⁻⁵ Pa·s]:", "3.5")
        self.ent_Pr_egzoz  = self.create_num_input(self.sol_frame, "Prandtl Sayısı Pr [-]:", "0.72")
        self.ent_k_gaz     = self.create_num_input(self.sol_frame, "Gaz Isıl İletkenliği k_gaz [W/mK]:", "0.055")
        self.ent_A_kesit   = self.create_num_input(self.sol_frame, "Tek Kanal Kesit Alanı A_k [mm²]:", "160")
 
        # Canlı Slider Kontrolü (Alan)
        ctk.CTkLabel(self.sol_frame, text="Canlı Alan Ayarı (A) [m²]:", font=("Arial", 12, "bold")).pack(pady=(15, 0), padx=15, anchor="w")
        self.slider_alan = ctk.CTkSlider(self.sol_frame, from_=0.1, to=3.5, number_of_steps=68, command=self.slider_tetiklendi)
        self.slider_alan.set(1.2)
        self.slider_alan.pack(pady=2, padx=15, fill="x")
        self.lbl_slider_deger = ctk.CTkLabel(self.sol_frame, text="Mevcut Alan: 1.20 m²", font=("Arial", 11, "italic"), text_color="cyan")
        self.lbl_slider_deger.pack(pady=0, padx=15, anchor="e")
 
        # Aksiyon Butonları
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
 
        # Sağ Panel Şema ve Çıktı Alanları
        self.canvas_sema = ctk.CTkCanvas(self.sag_frame, width=600, height=270, bg="#1c1c1c", highlightthickness=0)
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
        # Ana kaydırılabilir çerçeve
        ana = ctk.CTkScrollableFrame(self.tab_sihirbaz)
        ana.pack(fill="both", expand=True, padx=20, pady=10)
 
        # ── BAŞLIK ──────────────────────────────────────────────────
        ctk.CTkLabel(ana, text="🛠️ Geometri, Yüzey Alanı ve U Katsayısı Hesaplama Merkezi",
                     font=("Arial", 15, "bold")).pack(pady=(12, 2))
        ctk.CTkLabel(ana,
                     text="Kanal profilinizi seçin → boyutları girin → Hesapla → Simülasyona Aktar",
                     font=("Arial", 11, "italic"), text_color="#aaaaaa").pack(pady=(0, 10))
 
        # ════════════════════════════════════════════════════════════
        # BÖLÜM 1 — YÜZEY ALANI HESAPLAYICI
        # ════════════════════════════════════════════════════════════
        frm_alan = ctk.CTkFrame(ana, border_width=2, border_color="#3a6186")
        frm_alan.pack(fill="x", padx=10, pady=8)
 
        ctk.CTkLabel(frm_alan, text="📐  YÜZEY ALANI HESAPLAYICI",
                     font=("Arial", 13, "bold"), text_color="#74b9ff").pack(pady=(10, 4), padx=15, anchor="w")
 
        # Profil seçim satırı
        profil_satir = ctk.CTkFrame(frm_alan, fg_color="transparent")
        profil_satir.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(profil_satir, text="Kanal / Boru Profili:", font=("Arial", 11, "bold"), width=220, anchor="w").pack(side="left")
        self.combo_profil = ctk.CTkOptionMenu(
            profil_satir,
            values=[
                "Yuvarlak Boru (Circular)",
                "Dikdörtgen Kanal (Rectangular)",
                "Kare Kanal (Square)",
                "Eliptik Boru (Elliptical)",
                "Üçgen Kanal (Triangular)",
                "Altıgen Kanal (Hexagonal)"
            ],
            command=self._profil_degisti,
            width=260
        )
        self.combo_profil.pack(side="left", padx=8)
 
        # Dinamik boyut giriş alanı
        self.frm_profil_giris = ctk.CTkFrame(frm_alan, fg_color="#1e1e2e", corner_radius=8)
        self.frm_profil_giris.pack(fill="x", padx=15, pady=6)
 
        # Kanal sayısı ve uzunluk — her profil için ortak
        self.ent_alan_L  = self.create_num_input(frm_alan, "Kanal / Boru Etkin Uzunluğu (L) [mm]:", "350")
        self.ent_alan_N  = self.create_num_input(frm_alan, "Toplam Kanal / Boru Sayısı (N) [Adet]:", "90")
 
        # Formül açıklama etiketi
        self.lbl_formul = ctk.CTkLabel(frm_alan, text="", font=("Arial", 10, "italic"),
                                       text_color="#fdcb6e", wraplength=800, justify="left")
        self.lbl_formul.pack(padx=15, pady=2, anchor="w")
 
        # Sonuç + buton satırı
        sonuc_satir = ctk.CTkFrame(frm_alan, fg_color="transparent")
        sonuc_satir.pack(fill="x", padx=15, pady=(6, 12))
        self.lbl_alan_sonuc = ctk.CTkLabel(sonuc_satir, text="Toplam Alan: -- m²",
                                           font=("Arial", 13, "bold"), text_color="cyan", width=280, anchor="w")
        self.lbl_alan_sonuc.pack(side="left")
        ctk.CTkButton(sonuc_satir, text="Hesapla & Simülasyona Aktar 💾",
                      font=("Arial", 12, "bold"), width=260,
                      command=self.sihirbazdan_aktar,
                      fg_color="#e67e22", hover_color="#d35400").pack(side="right")
 
        # İlk profil widget'larını oluştur
        self._profil_giris_widgetlari = {}
        self._profil_degisti("Yuvarlak Boru (Circular)")
 
        # ════════════════════════════════════════════════════════════
        # BÖLÜM 2 — U KATSAYISI HESAPLAYICI
        # ════════════════════════════════════════════════════════════
        frm_u = ctk.CTkFrame(ana, border_width=2, border_color="#6c5ce7")
        frm_u.pack(fill="x", padx=10, pady=8)
 
        ctk.CTkLabel(frm_u, text="🔬  TOPLAM ISI GEÇİŞ KATSAYISI (U) HESAPLAYICI",
                     font=("Arial", 13, "bold"), text_color="#a29bfe").pack(pady=(10, 4), padx=15, anchor="w")
        ctk.CTkLabel(frm_u,
                     text="1/U = 1/h_iç + (t_duvar / k_duvar) + 1/h_dış    →    Seri ısıl direnç modeli",
                     font=("Arial", 10, "italic"), text_color="#aaaaaa").pack(padx=15, anchor="w")
 
        # Malzeme seçimi
        malz_satir = ctk.CTkFrame(frm_u, fg_color="transparent")
        malz_satir.pack(fill="x", padx=15, pady=6)
        ctk.CTkLabel(malz_satir, text="Duvar Malzemesi:", font=("Arial", 11, "bold"), width=220, anchor="w").pack(side="left")
        self.malzeme_veritabani = {
            "Paslanmaz Çelik 316L  (k=16 W/mK)": 16.0,
            "Alüminyum Alaşımı 6061  (k=167 W/mK)": 167.0,
            "Bakır  (k=385 W/mK)": 385.0,
            "Titanyum Ti-6Al-4V  (k=7 W/mK)": 7.0,
            "Dökme Demir  (k=50 W/mK)": 50.0,
            "Nikel Alaşımı Inconel 625  (k=10 W/mK)": 10.0,
            "Manuel Giriş": None
        }
        self.combo_malzeme = ctk.CTkOptionMenu(
            malz_satir,
            values=list(self.malzeme_veritabani.keys()),
            command=self._malzeme_degisti,
            width=300
        )
        self.combo_malzeme.pack(side="left", padx=8)
 
        # U hesap girdileri
        self.ent_u_h_ic   = self.create_num_input(frm_u, "İç Taraf Konveksiyon Katsayısı h_iç [W/m²K]:", "250")
        self.ent_u_h_dis  = self.create_num_input(frm_u, "Dış Taraf Konveksiyon Katsayısı h_dış [W/m²K]:", "3500")
        self.ent_u_t      = self.create_num_input(frm_u, "Duvar Kalınlığı t [mm]:", "1.0")
 
        # Manuel k girişi (başlangıçta gizli)
        self.frm_k_manuel = ctk.CTkFrame(frm_u, fg_color="transparent")
        self.frm_k_manuel.pack(fill="x", padx=15)
        self.ent_u_k = self.create_num_input(self.frm_k_manuel, "Isıl İletkenlik k [W/mK]  (Manuel):", "16")
        self.frm_k_manuel.pack_forget()
 
        # Kirlenme direnci (fouling) — opsiyonel
        fouling_satir = ctk.CTkFrame(frm_u, fg_color="transparent")
        fouling_satir.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(fouling_satir, text="Kirlenme Direnci R_fouling [m²K/W]  (0 = ihmal):",
                     font=("Arial", 11, "bold"), width=340, anchor="w").pack(side="left")
        self.ent_u_fouling = ctk.CTkEntry(fouling_satir, width=100)
        self.ent_u_fouling.insert(0, "0.0001")
        self.ent_u_fouling.pack(side="right")
 
        # U sonuç + buton
        u_sonuc_satir = ctk.CTkFrame(frm_u, fg_color="transparent")
        u_sonuc_satir.pack(fill="x", padx=15, pady=(8, 12))
        self.lbl_u_sonuc = ctk.CTkLabel(u_sonuc_satir, text="Hesaplanan U: -- W/m²K",
                                        font=("Arial", 13, "bold"), text_color="#a29bfe", width=300, anchor="w")
        self.lbl_u_sonuc.pack(side="left")
        ctk.CTkButton(u_sonuc_satir, text="Hesapla & U Değerine Aktar 🔬",
                      font=("Arial", 12, "bold"), width=260,
                      command=self.u_hesapla_aktar,
                      fg_color="#6c5ce7", hover_color="#4834d4").pack(side="right")
 
        # Detaylı direnç gösterimi
        self.lbl_u_detay = ctk.CTkLabel(frm_u, text="", font=("Courier New", 10),
                                        text_color="#dfe6e9", justify="left", wraplength=900)
        self.lbl_u_detay.pack(padx=15, pady=(0, 10), anchor="w")
 
    # ── Profil değiştiğinde dinamik widget güncelleme ──────────────
    def _profil_degisti(self, secim):
        # Eski widget'ları temizle
        for w in self.frm_profil_giris.winfo_children():
            w.destroy()
        self._profil_giris_widgetlari = {}
 
        tanim = {
            "Yuvarlak Boru (Circular)": {
                "alanlar": [("Dış Çap d [mm]", "12")],
                "formul": "A_toplam = π × d × L × N"
            },
            "Dikdörtgen Kanal (Rectangular)": {
                "alanlar": [("Kanal Genişliği a [mm]", "20"), ("Kanal Yüksekliği b [mm]", "8")],
                "formul": "A_toplam = 2 × (a + b) × L × N    |   Hidrolik çap: Dh = 2ab/(a+b)"
            },
            "Kare Kanal (Square)": {
                "alanlar": [("Kenar Uzunluğu a [mm]", "12")],
                "formul": "A_toplam = 4 × a × L × N    |   Hidrolik çap: Dh = a"
            },
            "Eliptik Boru (Elliptical)": {
                "alanlar": [("Büyük Yarı Eksen a [mm]", "15"), ("Küçük Yarı Eksen b [mm]", "7")],
                "formul": "A_toplam ≈ π × √(2(a²+b²)−(a−b)²/2) × L × N   (Ramanujan yaklaşımı)"
            },
            "Üçgen Kanal (Triangular)": {
                "alanlar": [("Taban c [mm]", "12"), ("Yükseklik h [mm]", "10")],
                "formul": "A_toplam = (c + 2×√((c/2)²+h²)) × L × N    |   Dh = (c×h) / (c/2 + √((c/2)²+h²))"
            },
            "Altıgen Kanal (Hexagonal)": {
                "alanlar": [("Kenar Uzunluğu s [mm]", "8")],
                "formul": "A_toplam = 6 × s × L × N    |   Hidrolik çap: Dh = s√3"
            },
        }
 
        if secim not in tanim:
            return
 
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
        if secim == "Manuel Giriş":
            self.frm_k_manuel.pack(fill="x", padx=15)
        else:
            self.frm_k_manuel.pack_forget()
 
    # ── Yüzey alanı hesapla ve simülasyona aktar ──────────────────
    def sihirbazdan_aktar(self):
        try:
            profil = self.combo_profil.get()
            L = float(self.ent_alan_L.get()) / 1000.0
            N = float(self.ent_alan_N.get())
            if L <= 0 or N <= 0:
                raise ValueError("L ve N sıfırdan büyük olmalıdır.")
 
            w = self._profil_giris_widgetlari
            degerler = {k: float(v.get()) / 1000.0 for k, v in w.items()}
 
            if profil == "Yuvarlak Boru (Circular)":
                d = list(degerler.values())[0]
                if d <= 0: raise ValueError("Çap sıfırdan büyük olmalıdır.")
                alan = math.pi * d * L * N
 
            elif profil == "Dikdörtgen Kanal (Rectangular)":
                vals = list(degerler.values())
                a, b = vals[0], vals[1]
                if a <= 0 or b <= 0: raise ValueError("a ve b sıfırdan büyük olmalıdır.")
                alan = 2 * (a + b) * L * N
 
            elif profil == "Kare Kanal (Square)":
                a = list(degerler.values())[0]
                if a <= 0: raise ValueError("Kenar uzunluğu sıfırdan büyük olmalıdır.")
                alan = 4 * a * L * N
 
            elif profil == "Eliptik Boru (Elliptical)":
                vals = list(degerler.values())
                a, b = vals[0], vals[1]
                if a <= 0 or b <= 0: raise ValueError("a ve b sıfırdan büyük olmalıdır.")
                cevre = math.pi * math.sqrt(2 * (a**2 + b**2) - (a - b)**2 / 2)
                alan = cevre * L * N
 
            elif profil == "Üçgen Kanal (Triangular)":
                vals = list(degerler.values())
                c, h = vals[0], vals[1]
                if c <= 0 or h <= 0: raise ValueError("c ve h sıfırdan büyük olmalıdır.")
                kenar = math.sqrt((c / 2)**2 + h**2)
                cevre = c + 2 * kenar
                alan = cevre * L * N
 
            elif profil == "Altıgen Kanal (Hexagonal)":
                s = list(degerler.values())[0]
                if s <= 0: raise ValueError("Kenar uzunluğu sıfırdan büyük olmalıdır.")
                alan = 6 * s * L * N
 
            else:
                raise ValueError("Bilinmeyen profil seçimi.")
 
            self.lbl_alan_sonuc.configure(text=f"Toplam Alan: {alan:.4f} m²")
            self.slider_alan.set(min(max(alan, 0.1), 3.5))
            self.lbl_slider_deger.configure(text=f"Mevcut Alan: {alan:.2f} m²")
 
            messagebox.showinfo("Başarılı",
                f"[{profil}]\nHesaplanan alan: {alan:.4f} m²\nSimülasyon motoruna aktarıldı.")
            self.tabview.set("Giriş & Termal Simülasyon")
            self.hesapla()
 
        except ValueError as e:
            messagebox.showerror("Geometri Hatası", str(e))
        except Exception as e:
            messagebox.showerror("Geometri Hatası", f"Beklenmeyen hata: {str(e)}")
 
    # ── U katsayısı hesapla ve simülasyona aktar ──────────────────
    def u_hesapla_aktar(self):
        try:
            h_ic  = float(self.ent_u_h_ic.get())
            h_dis = float(self.ent_u_h_dis.get())
            t_mm  = float(self.ent_u_t.get())
            R_f   = float(self.ent_u_fouling.get())
 
            if h_ic <= 0 or h_dis <= 0:
                raise ValueError("h_iç ve h_dış sıfırdan büyük olmalıdır.")
            if t_mm < 0:
                raise ValueError("Duvar kalınlığı negatif olamaz.")
 
            t = t_mm / 1000.0
 
            # k değeri
            malzeme_adi = self.combo_malzeme.get()
            k = self.malzeme_veritabani.get(malzeme_adi)
            if k is None:  # Manuel
                k = float(self.ent_u_k.get())
                if k <= 0:
                    raise ValueError("k değeri sıfırdan büyük olmalıdır.")
 
            # Direnç hesapları
            R_ic    = 1.0 / h_ic
            R_duvar = t / k if k > 0 and t > 0 else 0.0
            R_dis   = 1.0 / h_dis
            R_toplam = R_ic + R_duvar + R_dis + 2 * R_f  # İç + dış fouling
 
            U = 1.0 / R_toplam
 
            detay = (
                f"  R_iç        = 1/h_iç   = 1/{h_ic:.1f}       = {R_ic:.6f}  m²K/W\n"
                f"  R_duvar     = t/k       = {t_mm:.2f}mm/{k:.1f}  = {R_duvar:.6f}  m²K/W\n"
                f"  R_dış       = 1/h_dış   = 1/{h_dis:.1f}     = {R_dis:.6f}  m²K/W\n"
                f"  R_fouling   = 2×{R_f:.5f}          = {2*R_f:.6f}  m²K/W\n"
                f"  ─────────────────────────────────────────────────\n"
                f"  R_toplam    = {R_toplam:.6f}  m²K/W\n"
                f"  U = 1/R     = {U:.2f}  W/m²K"
            )
 
            self.lbl_u_sonuc.configure(text=f"Hesaplanan U: {U:.2f} W/m²K")
            self.lbl_u_detay.configure(text=detay)
 
            # Ana simülasyon U giriş kutusuna yaz
            self.ent_u_katsayi.delete(0, "end")
            self.ent_u_katsayi.insert(0, f"{U:.2f}")
 
            messagebox.showinfo("Başarılı",
                f"U = {U:.2f} W/m²K hesaplandı ve simülasyona aktarıldı.\n\n{detay}")
            self.tabview.set("Giriş & Termal Simülasyon")
            self.hesapla()
 
        except ValueError as e:
            messagebox.showerror("U Hesap Hatası", str(e))
        except Exception as e:
            messagebox.showerror("U Hesap Hatası", f"Beklenmeyen hata: {str(e)}")
 
    # ----------------------------------------------------------------
    # SEKME 3: REYNOLDS & AKIŞ ANALİZİ
    # ----------------------------------------------------------------
    def setup_sekme_reynolds(self):
        ana = ctk.CTkScrollableFrame(self.tab_reynolds)
        ana.pack(fill="both", expand=True, padx=20, pady=10)
 
        ctk.CTkLabel(ana, text="🌊  Reynolds Sayısı & Akış Rejimi Analiz Merkezi",
                     font=("Arial", 15, "bold")).pack(pady=(12, 2))
        ctk.CTkLabel(ana,
                     text="Giriş parametrelerini sol panelden girin → Hesapla tuşuna basın → Akış analizi otomatik güncellenir",
                     font=("Arial", 11, "italic"), text_color="#aaaaaa").pack(pady=(0, 10))
 
        # ── Hesapla butonu ───────────────────────────────────────────
        ctk.CTkButton(ana, text="🔄  Reynolds & Tek Kanal Analizini Hesapla",
                      font=("Arial", 13, "bold"), height=40,
                      command=self.reynolds_hesapla,
                      fg_color="#0984e3", hover_color="#0667b0").pack(fill="x", padx=10, pady=(0, 10))
 
        # ── Akış rejimi gösterge çubuğu ─────────────────────────────
        self.lbl_re_bar = ctk.CTkLabel(ana, text="— Henüz hesaplanmadı —",
                                       font=("Arial", 13, "bold"), fg_color="#333333",
                                       height=42, text_color="white", corner_radius=6)
        self.lbl_re_bar.pack(fill="x", padx=10, pady=(0, 10))
 
        # ── İki kolon düzeni ────────────────────────────────────────
        kolon_frame = ctk.CTkFrame(ana, fg_color="transparent")
        kolon_frame.pack(fill="both", expand=True, padx=10)
 
        sol = ctk.CTkFrame(kolon_frame, border_width=2, border_color="#0984e3")
        sol.pack(side="left", fill="both", expand=True, padx=(0, 6))
        sag = ctk.CTkFrame(kolon_frame, border_width=2, border_color="#00b894")
        sag.pack(side="right", fill="both", expand=True, padx=(6, 0))
 
        ctk.CTkLabel(sol, text="📐  AKIŞ REJİMİ & NUSSELT ANALİZİ",
                     font=("Arial", 12, "bold"), text_color="#74b9ff").pack(pady=(10, 4), padx=12, anchor="w")
        self.txt_re_akis = ctk.CTkTextbox(sol, font=("Courier New", 11), height=340)
        self.txt_re_akis.pack(fill="both", expand=True, padx=8, pady=(0, 10))
 
        ctk.CTkLabel(sag, text="🔥  TEK KANAL & TÜM EGR ISI TRANSFERİ",
                     font=("Arial", 12, "bold"), text_color="#55efc4").pack(pady=(10, 4), padx=12, anchor="w")
        self.txt_re_isi = ctk.CTkTextbox(sag, font=("Courier New", 11), height=340)
        self.txt_re_isi.pack(fill="both", expand=True, padx=8, pady=(0, 10))
 
        # ── Uyarılar / Öneriler kutusu ──────────────────────────────
        ctk.CTkLabel(ana, text="⚠️  TASARIM ÖNERİLERİ & UYARILAR",
                     font=("Arial", 12, "bold"), text_color="#fdcb6e").pack(padx=10, anchor="w", pady=(8, 2))
        self.txt_re_uyari = ctk.CTkTextbox(ana, font=("Courier New", 11), height=160)
        self.txt_re_uyari.pack(fill="x", padx=10, pady=(0, 12))
 
    def reynolds_hesapla(self):
        """Reynolds, Nusselt, tek kanal ve tüm EGR ısı transferi hesabı."""
        try:
            # ── Girdileri oku ────────────────────────────────────────
            m_dot_e  = float(self.ent_deb_e.get())
            T_e_in   = float(self.ent_temp_ei.get())
            T_s_in   = float(self.ent_temp_si.get())
            U        = float(self.ent_u_katsayi.get())
            A        = self.slider_alan.get()
            cp_e     = self.egzoz_veritabanı[self.combo_egzoz.get()]
            cp_s     = self.sogutucu_veritabanı[self.combo_sogutucu.get()]
            m_dot_s  = float(self.ent_deb_s.get())
            akis     = self.combo_akis_tipi.get()
 
            D_h      = float(self.ent_D_h.get()) / 1000.0       # m
            N        = int(float(self.ent_N_kanal.get()))
            rho      = float(self.ent_rho_egzoz.get())          # kg/m³
            mu       = float(self.ent_mu_egzoz.get()) * 1e-5    # Pa·s
            Pr       = float(self.ent_Pr_egzoz.get())
            k_gaz    = float(self.ent_k_gaz.get())              # W/mK
            A_kesit  = float(self.ent_A_kesit.get()) * 1e-6     # m²
 
            if D_h <= 0 or N <= 0 or rho <= 0 or mu <= 0 or A_kesit <= 0:
                raise ValueError("Tüm geometri/akışkan değerleri sıfırdan büyük olmalıdır.")
 
            # ── Reynolds hesabı ──────────────────────────────────────
            v_kanal = m_dot_e / (N * A_kesit * rho)   # m/s, tek kanalda hız
            Re = rho * v_kanal * D_h / mu
 
            # ── Akış rejimi ─────────────────────────────────────────
            if Re < 2300:
                rejim = "LAMİNER"
                renk  = "#00b894"
                re_bar_renk = "#00695c"
            elif Re < 4000:
                rejim = "GEÇİŞ (Transition)"
                renk  = "#fdcb6e"
                re_bar_renk = "#8d6e00"
            else:
                rejim = "TÜRBÜLANSLÜ"
                renk  = "#e17055"
                re_bar_renk = "#7f1d1d"
 
            # ── Nusselt hesabı ───────────────────────────────────────
            # Türbülanslı: Gnielinski korelasyonu (Re > 3000, 0.5 < Pr < 2000)
            # f = Darcy friction factor (Petukhov): f = (0.790·ln(Re) - 1.64)^-2
            if Re >= 4000:
                f   = (0.790 * math.log(Re) - 1.64) ** -2
                Nu  = (f / 8) * (Re - 1000) * Pr / (1 + 12.7 * math.sqrt(f / 8) * (Pr ** (2/3) - 1))
                nu_yontem = "Gnielinski (türbülanslı, ASHRAE/VDI)"
            elif Re >= 2300:
                # Geçiş: Gnielinski genişletilmiş (Re=2300..4000 arası interpolasyon)
                f2300 = (0.790 * math.log(2300) - 1.64) ** -2
                f4000 = (0.790 * math.log(4000) - 1.64) ** -2
                Nu2300 = (f2300/8)*(2300-1000)*Pr/(1+12.7*math.sqrt(f2300/8)*(Pr**(2/3)-1))
                Nu4000 = (f4000/8)*(4000-1000)*Pr/(1+12.7*math.sqrt(f4000/8)*(Pr**(2/3)-1))
                gamma  = (Re - 2300) / (4000 - 2300)
                Nu     = (1 - gamma) * Nu2300 + gamma * Nu4000
                f      = (1 - gamma) * f2300  + gamma * f4000
                nu_yontem = "Gnielinski lineer interpolasyon (geçiş bölgesi)"
            else:
                # Laminer: Nu sabit ısı akısı için = 48/11 ≈ 4.364 (yuvarlak boru)
                # Dikdörtgen için Shah & London korelasyonu (genel kullanım)
                Nu = 3.66   # sabit duvar sıcaklığı, yuvarlak boru
                f  = 64.0 / Re  # Darcy
                nu_yontem = "Nu=3.66 sabit (laminer, sabit T_duvar, yuvarlak yaklaşım)"
 
            h_ic_Re = Nu * k_gaz / D_h   # W/m²K — Reynolds'dan hesaplanan iç h
 
            # ── Tek kanal ısı transferi ──────────────────────────────
            # NTU-ε metoduyla tüm EGR için sonuçları al
            C_e   = m_dot_e * cp_e
            C_s   = m_dot_s * cp_s
            C_min = min(C_e, C_s)
            C_max = max(C_e, C_s)
            C_r   = C_min / C_max
            NTU   = (U * A) / C_min
 
            if "Zıt" in akis:
                eps = (1 - math.exp(-NTU*(1-C_r))) / (1 - C_r*math.exp(-NTU*(1-C_r))) if C_r != 1 else NTU/(1+NTU)
            else:
                eps = (1 - math.exp(-NTU*(1+C_r))) / (1+C_r)
            eps = min(max(eps, 0.0), 1.0)
 
            q_max_toplam = C_min * (T_e_in - T_s_in)
            q_toplam     = eps * q_max_toplam       # W
            q_tek_kanal  = q_toplam / N              # W
 
            T_e_out = T_e_in - q_toplam / C_e
            T_s_out = T_s_in + q_toplam / C_s
 
            # Tek kanal için enerji dengesi (eşit dağılım varsayımı)
            m_dot_e_tek  = m_dot_e / N
            q_tek_check  = m_dot_e_tek * cp_e * (T_e_in - T_e_out)  # egzoz tarafı
 
            # ── Baskı düşümü (Darcy-Weisbach) ───────────────────────
            # ΔP = f * (L/D_h) * (ρv²/2)
            # L: kanal uzunluğunu A ve N üzerinden tahmin et (A = P_çevre * L * N)
            L_tahmini = A / (N * math.pi * D_h) if D_h > 0 and N > 0 else 0.0  # yuvarlak boru varsayımı
            delta_P   = f * (L_tahmini / D_h) * (rho * v_kanal**2 / 2) if L_tahmini > 0 else 0.0
 
            # ── Sonuç metinleri ─────────────────────────────────────
            akis_txt = (
                f"  Re sayısı           = {Re:.1f}\n"
                f"  Akış hızı (tek kanal) = {v_kanal:.3f} m/s\n"
                f"  Hidrolik çap D_h    = {D_h*1000:.2f} mm\n"
                f"  Akış Rejimi         = *** {rejim} ***\n"
                f"\n"
                f"  ── Nusselt Analizi ──────────────────────────────\n"
                f"  Yöntem              : {nu_yontem}\n"
                f"  Nu sayısı           = {Nu:.2f}\n"
                f"  h_iç (Re'den)       = {h_ic_Re:.1f} W/m²K\n"
                f"  f (Darcy sürtünme)  = {f:.5f}\n"
                f"\n"
                f"  ── Baskı Düşümü (tahmini) ───────────────────────\n"
                f"  Kanal uzunluğu L    ≈ {L_tahmini*1000:.1f} mm (geometrik tahmin)\n"
                f"  ΔP (tek kanal)      ≈ {delta_P:.1f} Pa  ({delta_P/1000:.3f} kPa)\n"
                f"\n"
                f"  ── Akış Rejimi Sınıflandırması ──────────────────\n"
                f"  Re < 2300           → Laminer (düzenli, katmanlı akış)\n"
                f"  2300 ≤ Re < 4000    → Geçiş (kararsız, tahmin güç)\n"
                f"  Re ≥ 4000           → Türbülanslı (yüksek ısı transferi)\n"
            )
 
            isi_txt = (
                f"  ── TÜM EGR COOLER ─────────────────────────────\n"
                f"  Toplam kanal sayısı N    = {N}\n"
                f"  Toplam ısı transfer alanı= {A:.4f} m²\n"
                f"  Toplam egzoz debisi      = {m_dot_e:.4f} kg/s\n"
                f"  NTU                      = {NTU:.4f}\n"
                f"  Etkinlik ε               = {eps*100:.2f} %\n"
                f"  q_max (teorik maks)      = {q_max_toplam/1000:.2f} kW\n"
                f"  q_toplam (gerçek)        = {q_toplam/1000:.2f} kW\n"
                f"  T_egzoz çıkış            = {T_e_out:.2f} °C\n"
                f"  T_sıvı çıkış             = {T_s_out:.2f} °C\n"
                f"\n"
                f"  ── TEK KANAL (eşit dağılım varsayımı) ──────────\n"
                f"  Tek kanalda egzoz debisi = {m_dot_e_tek*1000:.4f} g/s\n"
                f"  Tek kanalda q_kanal      = {q_tek_kanal:.2f} W\n"
                f"  Tek kanalda q_kanal      = {q_tek_kanal/1000:.4f} kW\n"
                f"  Tek kanal enerji dengesi = {q_tek_check:.2f} W\n"
                f"  Fark (dağılım hatası)    = {abs(q_tek_kanal-q_tek_check):.4f} W\n"
                f"\n"
                f"  ── PERFORMANS KARŞILAŞTIRMASI ───────────────────\n"
                f"  h_iç (Reynolds'dan)      = {h_ic_Re:.1f} W/m²K\n"
                f"  U (kullanıcı girişi)     = {U:.1f} W/m²K\n"
                f"  h_iç / U oranı           = {h_ic_Re/U:.2f}  {'⚠ U > h_iç, kontrol et' if U > h_ic_Re else '✓'}\n"
            )
 
            # ── Uyarı ve öneriler ────────────────────────────────────
            uyarilar = []
 
            if Re < 2300:
                uyarilar.append("⚠  LAMİNER AKIŞ: Isı transfer katsayısı düşük. Kanal kesitini küçültün "
                                "veya debiyi artırın (Re > 4000 hedefleyin).")
                uyarilar.append(f"   Türbülanslı rejime geçmek için gereken min. hız ≈ "
                                f"{4000 * mu / (rho * D_h):.2f} m/s")
            elif Re < 4000:
                uyarilar.append("⚠  GEÇİŞ BÖLGESİ: Akış kararsız. Nusselt tahmini güvenilirliği düşük. "
                                "Tasarımı Re > 4000 veya Re < 2300 olacak şekilde optimize edin.")
            else:
                uyarilar.append("✅ TÜRBÜLANSLÜ AKIŞ: İyi ısı transferi rejimi.")
 
            if v_kanal > 30:
                uyarilar.append(f"⚠  YÜKSEK HIZ: v={v_kanal:.1f} m/s → Erozyon ve titreşim riski. "
                                "Kanal kesit alanını büyütün.")
            if delta_P > 5000:
                uyarilar.append(f"⚠  YÜKSEK BASINÇ DÜŞÜMÜ: ΔP={delta_P:.0f} Pa → EGR sistemi geri basıncını "
                                "artırır, motor verimliliğini düşürebilir.")
            if h_ic_Re < U * 0.5:
                uyarilar.append(f"⚠  h_iç ({h_ic_Re:.1f} W/m²K) << U ({U:.1f} W/m²K): "
                                "İç taraf ısıl direnç baskın, U değerini düşürün.")
            if T_e_out < 90:
                uyarilar.append("⚠  YOĞUŞMA RİSKİ: T_egzoz_çıkış < 90°C → Asit yoğuşması, borularda korozyon.")
            if eps < 0.5:
                uyarilar.append(f"⚠  DÜŞÜK ETKİNLİK: ε = {eps*100:.1f}% → Alan artırılmalı veya akış tipi "
                                "Zıt Akış olarak değiştirilmeli.")
 
            if not uyarilar:
                uyarilar.append("✅ Tüm parametreler kabul edilebilir aralıkta.")
 
            # ── Arayüzü güncelle ─────────────────────────────────────
            self.lbl_re_bar.configure(
                fg_color=re_bar_renk,
                text=f"Re = {Re:.0f}  |  {rejim}  |  Nu = {Nu:.1f}  |  h_iç = {h_ic_Re:.0f} W/m²K  |  v = {v_kanal:.2f} m/s"
            )
 
            self.txt_re_akis.delete("0.0", "end")
            self.txt_re_akis.insert("0.0", akis_txt)
 
            self.txt_re_isi.delete("0.0", "end")
            self.txt_re_isi.insert("0.0", isi_txt)
 
            self.txt_re_uyari.delete("0.0", "end")
            self.txt_re_uyari.insert("0.0", "\n".join(uyarilar))
 
        except ValueError as e:
            messagebox.showerror("Reynolds Hatası", str(e))
        except Exception as e:
            messagebox.showerror("Reynolds Hatası", f"Beklenmeyen hata: {str(e)}")
 
    # ----------------------------------------------------------------
    # SEKME 4: YERLİ GRAFİK MOTORU EKRANI
    # ----------------------------------------------------------------
    def setup_sekme_grafik(self):
        self.canvas_grafik = ctk.CTkCanvas(self.tab_grafik, bg="#1a1a1a", highlightthickness=0)
        self.canvas_grafik.pack(fill="both", expand=True, padx=15, pady=15)
 
    # ----------------------------------------------------------------
    # DİNAMİK ISI DEĞİŞTİRİCİ ŞEMATİK GÖSTERİM MOTORU
    # ----------------------------------------------------------------
    def sema_ciz(self, T_ei, T_si, T_eo, T_so, akis_tipi):
        self.canvas_sema.delete("all")
 
        # ── Koordinat sabitleri (canvas yüksekliği: 270px) ──
        # Gövde merkez bandı: y=90..175, üst bağlantı fitingleri: y=30..90, alt: y=175..230
        GOVDE_Y1, GOVDE_Y2 = 90, 175
        GOVDE_X1, GOVDE_X2 = 135, 465
        MID_Y = (GOVDE_Y1 + GOVDE_Y2) // 2          # 132
        OVAL_X1_L, OVAL_X2_L = 108, 162
        OVAL_X1_R, OVAL_X2_R = 438, 492
 
        # Gövde çerçevesi
        self.canvas_sema.create_oval(OVAL_X1_L, GOVDE_Y1, OVAL_X2_L, GOVDE_Y2,
                                     fill="#2c3e50", outline="#7f8c8d", width=2)
        self.canvas_sema.create_oval(OVAL_X1_R, GOVDE_Y1, OVAL_X2_R, GOVDE_Y2,
                                     fill="#2c3e50", outline="#7f8c8d", width=2)
        self.canvas_sema.create_rectangle(GOVDE_X1, GOVDE_Y1 + 10, GOVDE_X2, GOVDE_Y2 - 10,
                                          fill="#2b2b2b", outline="#7f8c8d", width=2)
 
        # İç boru çizgileri
        for i in range(4):
            self.canvas_sema.create_line(GOVDE_X1 + 5, GOVDE_Y1 + 20 + i * 16,
                                         GOVDE_X2 - 5, GOVDE_Y1 + 20 + i * 16,
                                         fill="#555555", width=2)
 
        self.canvas_sema.create_text(300, MID_Y,
                                     text="EGR BUNDLE COOLER GÖVDE",
                                     fill="#ecf0f1", font=("Arial", 11, "bold"))
 
        # ── Egzoz girişi (sol, yatay) ──
        self.canvas_sema.create_rectangle(72, MID_Y - 16, OVAL_X1_L, MID_Y + 16,
                                          fill="#3a3a3a", outline="#7f8c8d", width=1)
        self.canvas_sema.create_line(20, MID_Y, 80, MID_Y, fill="#e74c3c", width=6, arrow="last")
        self.canvas_sema.create_text(46, MID_Y - 28,
                                     text=f"Egzoz Giriş", fill="#ff7675", font=("Arial", 9, "bold"))
        self.canvas_sema.create_text(46, MID_Y - 15,
                                     text=f"{T_ei:.1f}°C", fill="#ff7675", font=("Arial", 10, "bold"))
 
        # ── Egzoz çıkışı (sağ, yatay) ──
        self.canvas_sema.create_rectangle(OVAL_X2_R, MID_Y - 16, 528, MID_Y + 16,
                                          fill="#3a3a3a", outline="#7f8c8d", width=1)
        self.canvas_sema.create_line(520, MID_Y, 580, MID_Y, fill="#e67e22", width=6, arrow="last")
        self.canvas_sema.create_text(554, MID_Y - 28,
                                     text=f"Egzoz Çıkış", fill="#f39c12", font=("Arial", 9, "bold"))
        self.canvas_sema.create_text(554, MID_Y - 15,
                                     text=f"{T_eo:.1f}°C", fill="#f39c12", font=("Arial", 10, "bold"))
 
        # ── Sıvı akış okları (akış tipine göre) ──
        if "Zıt" in akis_tipi:
            # Sıvı GİRİŞ → sağ üstten aşağı giriyor
            self.canvas_sema.create_rectangle(450, 30, 480, GOVDE_Y1,
                                              fill="#2c3e50", outline="#7f8c8d", width=1)
            self.canvas_sema.create_line(465, 8, 465, GOVDE_Y1,
                                         fill="#3498db", width=5, arrow="last")
            self.canvas_sema.create_text(465, 22,
                                         text=f"Sıvı Giriş: {T_si:.1f}°C",
                                         fill="#74b9ff", font=("Arial", 9, "bold"))
 
            # Sıvı ÇIKIŞ → sol alttan aşağı çıkıyor
            self.canvas_sema.create_rectangle(120, GOVDE_Y2, 150, GOVDE_Y2 + 40,
                                              fill="#2c3e50", outline="#7f8c8d", width=1)
            self.canvas_sema.create_line(135, GOVDE_Y2, 135, GOVDE_Y2 + 55,
                                         fill="#1abc9c", width=5, arrow="last")
            self.canvas_sema.create_text(135, GOVDE_Y2 + 62,
                                         text=f"Sıvı Çıkış: {T_so:.1f}°C",
                                         fill="#55efc4", font=("Arial", 9, "bold"))
 
            self.canvas_sema.create_text(300, 258,
                                         text="⬅ AKIŞ YÖNÜ: ZIT AKIŞ (COUNTER-FLOW)",
                                         fill="#74b9ff", font=("Arial", 9, "bold"))
        else:
            # Sıvı GİRİŞ → sol üstten aşağı giriyor
            self.canvas_sema.create_rectangle(120, 30, 150, GOVDE_Y1,
                                              fill="#2c3e50", outline="#7f8c8d", width=1)
            self.canvas_sema.create_line(135, 8, 135, GOVDE_Y1,
                                         fill="#3498db", width=5, arrow="last")
            self.canvas_sema.create_text(135, 22,
                                         text=f"Sıvı Giriş: {T_si:.1f}°C",
                                         fill="#74b9ff", font=("Arial", 9, "bold"))
 
            # Sıvı ÇIKIŞ → sağ alttan aşağı çıkıyor
            self.canvas_sema.create_rectangle(450, GOVDE_Y2, 480, GOVDE_Y2 + 40,
                                              fill="#2c3e50", outline="#7f8c8d", width=1)
            self.canvas_sema.create_line(465, GOVDE_Y2, 465, GOVDE_Y2 + 55,
                                         fill="#1abc9c", width=5, arrow="last")
            self.canvas_sema.create_text(465, GOVDE_Y2 + 62,
                                         text=f"Sıvı Çıkış: {T_so:.1f}°C",
                                         fill="#55efc4", font=("Arial", 9, "bold"))
 
            self.canvas_sema.create_text(300, 258,
                                         text="➡ AKIŞ YÖNÜ: PARALEL AKIŞ (CO-CURRENT)",
                                         fill="#e74c3c", font=("Arial", 9, "bold"))
 
    # ----------------------------------------------------------------
    # GELİŞMİŞ YERLİ ÜÇLÜ GRAFİK MOTORU
    # ----------------------------------------------------------------
    def yerli_grafik_ciz(self, T_ei, T_eo, T_si, T_so, NTU, A, C_r, q_max, C_e, U, C_min, akis_tipi):
        self.canvas_grafik.delete("all")
        w = self.canvas_grafik.winfo_width()
        h = self.canvas_grafik.winfo_height()
        if w < 200 or h < 200:
            w, h = 1150, 650
 
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
 
        # --- GRAFİK 1: SICAKLIK PROFİLİ ---
        ox1 = 60
        ex1 = eksen_ciz(ox1, "Sıcaklık Değişim Profili", "Konum (EGR Boyu)", "Sıcaklık [°C]")
        max_t = max(T_ei, T_so, T_eo, T_si) + 40
        min_t = min(T_ei, T_so, T_eo, T_si) - 15
        t_span = max_t - min_t if max_t != min_t else 1.0
 
        def t_s(t):
            return y_bot - (((t - min_t) / t_span) * (y_bot - 60))
 
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
 
        # --- GRAFİK 2: NTU ANALİZİ ---
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
            # DÜZELTİLMİŞ: width int olarak verildi (float → TypeError riski giderildi)
            self.canvas_grafik.create_line(pts_n[i][0], pts_n[i][1], pts_n[i + 1][0], pts_n[i + 1][1], fill="#2ecc71", width=2)
 
        cur_ntu_x = ox2 + (min(NTU, 5.0) / 5.0) * (ex2 - ox2)
        self.canvas_grafik.create_line(cur_ntu_x, y_bot, cur_ntu_x, 60, fill="yellow", dash=(5, 5))
        self.canvas_grafik.create_text(cur_ntu_x, 50, text=f"NTU:{NTU:.2f}", fill="yellow", font=("Arial", 9, "bold"))
 
        # --- GRAFİK 3: ALAN ETKİSİ GRAFİĞİ ---
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
            # DÜZELTİLMİŞ: width int
            self.canvas_grafik.create_line(pts_q[i][0], pts_q[i][1], pts_q[i + 1][0], pts_q[i + 1][1], fill="magenta", width=2)
 
        cur_a_x = ox3 + (A / m_a_plot) * (ex3 - ox3)
        self.canvas_grafik.create_line(cur_a_x, y_bot, cur_a_x, 60, fill="cyan", dash=(5, 5))
        self.canvas_grafik.create_text(cur_a_x, 50, text=f"A:{A:.2f}m²", fill="cyan", font=("Arial", 9, "bold"))
 
    # ----------------------------------------------------------------
    # TERMOMÜHENDİSLİK HESAPLAMA MOTORU
    # ----------------------------------------------------------------
    def hesapla(self, hafizaya_yaz=True):
        try:
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
 
            # DÜZELTİLMİŞ: Negatif veya sıfır giriş koruması
            if m_dot_e <= 0 or m_dot_s <= 0 or U <= 0 or A <= 0:
                raise ValueError("Debi, U katsayısı ve Alan değerleri sıfırdan büyük olmalıdır.")
 
            if hafizaya_yaz:
                self.gecmis_hafizaya_ekle([akis_tipi, egzoz_adi, sogutucu_adi, P_motor, m_dot_e, T_e_in, m_dot_s, T_s_in, U, A])
 
            C_e = m_dot_e * cp_e
            C_s = m_dot_s * cp_s
            C_min = min(C_e, C_s)
            C_max = max(C_e, C_s)
            C_r = C_min / C_max
 
            NTU = (U * A) / C_min
 
            if "Zıt" in akis_tipi:
                epsilon = (1 - math.exp(-NTU * (1 - C_r))) / (1 - C_r * math.exp(-NTU * (1 - C_r))) if C_r != 1 else NTU / (1 + NTU)
            else:
                epsilon = (1 - math.exp(-NTU * (1 + C_r))) / (1 + C_r)
 
            epsilon = min(max(epsilon, 0.0), 1.0)
 
            # DÜZELTİLMİŞ: Giriş sıcaklıkları eşitse q_max=0 → sıfıra bölme koruması
            q_max = C_min * (T_e_in - T_s_in)
            if abs(q_max) < 1e-9:
                raise ValueError("Egzoz ve sıvı giriş sıcaklıkları birbirine çok yakın, ısı transferi hesaplanamaz.")
 
            q = epsilon * q_max
 
            T_e_out = T_e_in - (q / C_e)
            T_s_out = T_s_in + (q / C_s)
 
            if "Zıt" in akis_tipi:
                dt1 = T_e_in - T_s_out
                dt2 = T_e_out - T_s_in
            else:
                dt1 = T_e_in - T_s_in
                dt2 = T_e_out - T_s_out
 
            # DÜZELTİLMİŞ: LMTD hesabında log(0) ve negatif dt koruması
            if dt1 > 0 and dt2 > 0 and abs(dt1 - dt2) > 1e-6:
                LMTD = (dt1 - dt2) / math.log(dt1 / dt2)
            else:
                LMTD = (dt1 + dt2) / 2.0
 
            self.sema_ciz(T_e_in, T_s_in, T_e_out, T_s_out, akis_tipi)
            self.yerli_grafik_ciz(T_e_in, T_e_out, T_s_in, T_s_out, NTU, A, C_r, q_max, C_e, U, C_min, akis_tipi)
 
            self.son_analiz_raporu = {
                "akis_tipi": akis_tipi, "egzoz_adi": egzoz_adi, "sogutucu_adi": sogutucu_adi,
                "P_motor": P_motor, "m_dot_e": m_dot_e, "T_e_in": T_e_in, "m_dot_s": m_dot_s,
                "T_s_in": T_s_in, "U": U, "A": A, "T_e_out": T_e_out, "T_s_out": T_s_out,
                "q_kw": q / 1000.0, "verim": epsilon * 100.0, "LMTD": LMTD, "NTU": NTU
            }
 
            sonuc_txt = (
                f"====================================================================\n"
                f"      EGR COOLER TERMAL MÜHENDİSLİK VE AR-GE ANALİZ RAPORU\n"
                f"====================================================================\n"
                f" Geliştiren Tasarımcı : Enes Çelik Simülasyon Sistemleri\n"
                f"--------------------------------------------------------------------\n\n"
                f" [1] SİSTEM VE AKIŞKAN ÖZELLİKLERİ\n"
                f" --------------------------------------------------------------------\n"
                f" * Isı Değiştirici Akış Tipi      : {akis_tipi}\n"
                f" * Kullanılan Motor Yakıt/Gaz Tipi : {egzoz_adi}\n"
                f" * Seçilen Soğutucu Akışkan Tipi  : {sogutucu_adi}\n"
                f" * Referans Motor Gücü            : {P_motor:.1f} kW\n\n"
                f" [2] GEOMETRİK VE TERMAL GEÇİŞ VERİLERİ\n"
                f" --------------------------------------------------------------------\n"
                f" * Aktif Isı Transfer Alanı (A)   : {A:.4f} m²\n"
                f" * Toplam Isı Geçiş Katsayısı (U) : {U:.1f} W/m²K\n"
                f" * Logaritmik Ort. Sıcaklık Farkı : {LMTD:.2f} °C\n"
                f" * Hesaplanan Sınır NTU Sayısı    : {NTU:.4f}\n\n"
                f" [3] ENERJİ BİLANÇOSU VE SİMÜLASYON ÇIKTILARI\n"
                f" --------------------------------------------------------------------\n"
                f" * EGZOZ GAZ Giriş Sıcaklığı      : {T_e_in:.1f} °C\n"
                f" * EGZOZ GAZ Çıkış Sıcaklığı     : {T_e_out:.2f} °C\n"
                f" * SOĞUTUCU SIVI Giriş Sıcaklığı  : {T_s_in:.1f} °C\n"
                f" * SOĞUTUCU SIVI Çıkış Sıcaklığı : {T_s_out:.2f} °C\n"
                f" * Geri Kazanılan Toplam Isı Gücü : {q / 1000.0:.2f} kW\n"
                f" * Sistem Termal Etkinliği (Verim): % {epsilon * 100.0:.2f}\n"
                f"====================================================================\n"
                f"                    RAPOR SONU - GÜVENLİ ÇIKTI\n"
                f"===================================================================="
            )
            self.txt_sonuc.delete("0.0", "end")
            self.txt_sonuc.insert("0.0", sonuc_txt)
 
            if T_e_out > 190:
                self.renk_bar.configure(fg_color="#c0392b", text="⚠️ KRİTİK SEVİYE: Egzoz gazı yeterince soğutulamıyor, alanı büyütün.")
            elif 110 <= T_e_out <= 190:
                self.renk_bar.configure(fg_color="#27ae60", text="✅ İDEAL TASARIM: Optimum emisyon ve soğutma dengesi yakalandı.")
            else:
                self.renk_bar.configure(fg_color="#d35400", text="⚠️ YOĞUŞMA ALARMI: Çıkış çok soğuk, borularda kurum ve asit birikebilir.")
 
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
        # DÜZELTİLMİŞ: Rapor boşsa kullanıcıyı uyar, AttributeError olmaz
        if not self.son_analiz_raporu:
            messagebox.showwarning("Uyarı", "Önce bir simülasyon çalıştırmanız gerekmektedir.")
            return
 
        try:
            dosya_yolu = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Metin Belgesi", "*.txt")],
                title="Mühendislik Raporunu Kaydet"
            )
            if not dosya_yolu:
                return
 
            r = self.son_analiz_raporu
 
            rapor_metni = (
                f"====================================================================\n"
                f"      EGR COOLER TERMAL MÜHENDİSLİK VE AR-GE ANALİZ RAPORU\n"
                f"====================================================================\n"
                f" Geliştiren Tasarımcı : Enes Çelik Simülasyon Sistemleri\n"
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
                f" * Toplam Isı Geçiş Katsayısı (U) : {r['U']:.1f} W/m²K\n"
                f" * Logaritmik Ort. Sıcaklık Farkı : {r['LMTD']:.2f} °C\n"
                f" * Hesaplanan Sınır NTU Sayısı    : {r['NTU']:.4f}\n\n"
                f" [3] ENERJİ BİLANÇOSU VE SİMÜLASYON ÇIKTILARI\n"
                f" --------------------------------------------------------------------\n"
                f" * EGZOZ GAZ Giriş Sıcaklığı      : {r['T_e_in']:.1f} °C\n"
                f" * EGZOZ GAZ Çıkış Sıcaklığı     : {r['T_e_out']:.2f} °C\n"
                f" * SOĞUTUCU SIVI Giriş Sıcaklığı  : {r['T_s_in']:.1f} °C\n"
                f" * SOĞUTUCU SIVI Çıkış Sıcaklığı : {r['T_s_out']:.2f} °C\n"
                f" * Geri Kazanılan Toplam Isı Gücü : {r['q_kw']:.2f} kW\n"
                f" * Sistem Termal Etkinliği (Verim): % {r['verim']:.2f}\n"
                f"====================================================================\n"
                f"                    RAPOR SONU - GÜVENLİ ÇIKTI\n"
                f"====================================================================\n"
            )
 
            with open(dosya_yolu, "w", encoding="utf-8") as f:
                f.write(rapor_metni)
 
            messagebox.showinfo("Başarılı", f"Mühendislik analiz raporu sıfır hatayla kaydedildi:\n{dosya_yolu}")
        except Exception as e:
            messagebox.showerror("Rapor Hatası", f"Rapor yazılırken sistemsel hata çıktı: {str(e)}")
 
    # ----------------------------------------------------------------
    # GEÇMİŞ YÖNETİMİ HAFİZA SİSTEMİ
    # ----------------------------------------------------------------
    def gecmis_hafizaya_ekle(self, veri):
        # DÜZELTİLMİŞ: float karşılaştırması yerine indeks kontrolü ile güvenli ekleme
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
