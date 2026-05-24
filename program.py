"""
EGR Cooler Ar-Ge ve Termal Analiz Laboratuvarı  v5.0
Geliştiren: Enes Çelik Simülasyon Sistemleri

v5.0 Değişiklikleri:
  - Tüm Entry widget'larına StringVar + debounce trace bağlandı (U dahil anlık güncelleme)
  - Eliptik çevre Ramanujan 2. yaklaşım ile düzeltildi
  - NTU-ε paralel akış C_r=1 durumu düzeltildi
  - Laminer Nu profil uyarısı eklendi
  - Sihirbaz → Reynolds D_h & A_kesit otomatik aktarımı
  - Canvas Configure olayı ile grafik yeniden çizimi
  - LMTD negatif ΔT uyarısı
  - txt metin kutuları → renkli kart panellerine dönüştürüldü
  - Renk teması güncellendi (koyu lacivert + turkuaz + amber vurgu)
  - Parametrik tarama tablosu eklendi (farklı A için q ve ε)
  - CSV dışa aktarma eklendi
"""

import customtkinter as ctk
import math
import csv
import os
from tkinter import filedialog, messagebox

# ────────────────────────────────────────────────────────────────────
# TEMA & RENK PALETİ
# ────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Özel renk sabitleri
CLR_BG_DEEP   = "#0d1117"   # en koyu arka plan
CLR_BG_PANEL  = "#161b22"   # panel arka planı
CLR_BG_CARD   = "#1c2128"   # kart arka planı
CLR_BG_INPUT  = "#21262d"   # giriş kutusu
CLR_BORDER    = "#30363d"   # kenarlık
CLR_CYAN      = "#58d1eb"   # birincil vurgu
CLR_AMBER     = "#f0a500"   # uyarı / sıcaklık
CLR_GREEN     = "#3fb950"   # başarı / iyi
CLR_RED       = "#f85149"   # hata / kritik
CLR_PURPLE    = "#bc8cff"   # Reynolds / akış
CLR_TEXT_PRI  = "#e6edf3"   # birincil metin
CLR_TEXT_SEC  = "#8b949e"   # ikincil metin
CLR_TEXT_MUT  = "#484f58"   # soluk metin
CLR_EGZOZ     = "#e05c4b"   # egzoz hattı
CLR_SIVI      = "#4d9de0"   # sıvı hattı


# ────────────────────────────────────────────────────────────────────
# YARDIMCI: Renkli Kart Bileşeni
# ────────────────────────────────────────────────────────────────────
class KartFrame(ctk.CTkFrame):
    """Başlık şeridi olan renkli kart çerçevesi."""
    def __init__(self, parent, baslik="", renk=CLR_CYAN, **kwargs):
        super().__init__(parent, fg_color=CLR_BG_CARD,
                         border_color=CLR_BORDER, border_width=1,
                         corner_radius=10, **kwargs)
        if baslik:
            header = ctk.CTkFrame(self, fg_color=renk, corner_radius=0,
                                  height=32)
            header.pack(fill="x", padx=0, pady=0)
            header.pack_propagate(False)
            ctk.CTkLabel(header, text=baslik, font=("Arial", 11, "bold"),
                         text_color="#0d1117").pack(side="left", padx=12, pady=0)


class SonucSatir(ctk.CTkFrame):
    """İki kolonlu etiket-değer satırı."""
    def __init__(self, parent, etiket, deger="—",
                 deger_renk=CLR_TEXT_PRI, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        ctk.CTkLabel(self, text=etiket, font=("Arial", 11),
                     text_color=CLR_TEXT_SEC, anchor="w", width=230
                     ).pack(side="left", padx=(12, 4))
        self.lbl_deger = ctk.CTkLabel(
            self, text=deger, font=("Arial", 11, "bold"),
            text_color=deger_renk, anchor="e")
        self.lbl_deger.pack(side="right", padx=(4, 12))

    def set(self, deger, renk=None):
        self.lbl_deger.configure(text=deger)
        if renk:
            self.lbl_deger.configure(text_color=renk)


class AyiriciCizgi(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, height=1, fg_color=CLR_BORDER, **kwargs)
        self.pack(fill="x", padx=12, pady=4)


# ────────────────────────────────────────────────────────────────────
# ANA UYGULAMA
# ────────────────────────────────────────────────────────────────────
class EGRLab(ctk.CTk):

    DEBOUNCE_MS = 450   # ms — giriş değişince beklenecek süre

    def __init__(self):
        super().__init__()
        self.title("EGR Cooler Ar-Ge ve Termal Analiz Laboratuvarı  v5.0")
        self.geometry("1340x920")
        self.minsize(1100, 750)
        self.configure(fg_color=CLR_BG_DEEP)

        # ── Akışkan veritabanları ────────────────────────────────────
        self.egzoz_db = {
            "Dizel Egzoz Gazı":     1150,
            "Benzin Egzoz Gazı":    1250,
            "LPG Egzoz Gazı":       1180,
            "Hidrojen Egzoz Gazı":  1420,
        }
        self.sogutucu_db = {
            "Saf Su":                    4184,
            "%50 Etilen Glikol (Antifriz)": 3300,
            "%30 Propilen Glikol":       3700,
        }
        self.malzeme_db = {
            "Paslanmaz Çelik 316L  (k=16 W/mK)":       16.0,
            "Alüminyum Alaşımı 6061  (k=167 W/mK)":   167.0,
            "Bakır  (k=385 W/mK)":                     385.0,
            "Titanyum Ti-6Al-4V  (k=7 W/mK)":           7.0,
            "Dökme Demir  (k=50 W/mK)":                 50.0,
            "Nikel Alaşımı Inconel 625  (k=10 W/mK)":  10.0,
            "Manuel Giriş":                             None,
        }

        # ── Durum değişkenleri ───────────────────────────────────────
        self.gecmis       = []
        self.gec_idx      = -1
        self.son_rapor    = {}
        self._debounce_id = None

        # ── İmza ────────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Bu program Enes Çelik tarafından geliştirilmiştir  •  EGR Lab v5.0",
            font=("Arial", 11, "italic"),
            text_color=CLR_TEXT_MUT,
            fg_color=CLR_BG_DEEP,
        ).pack(side="top", pady=(6, 0))

        # ── Sekme yapısı ─────────────────────────────────────────────
        self.tabview = ctk.CTkTabview(
            self, fg_color=CLR_BG_PANEL,
            segmented_button_fg_color=CLR_BG_CARD,
            segmented_button_selected_color=CLR_CYAN,
            segmented_button_selected_hover_color="#3bbbd4",
            segmented_button_unselected_color=CLR_BG_CARD,
            segmented_button_unselected_hover_color=CLR_BG_INPUT,
            text_color=CLR_TEXT_PRI,
            text_color_disabled=CLR_TEXT_SEC,
        )
        self.tabview.pack(padx=12, pady=(4, 10), fill="both", expand=True)

        self.tab_ana      = self.tabview.add("⚙  Termal Simülasyon")
        self.tab_sihirbaz = self.tabview.add("📐  Geometri & U Hesaplama")
        self.tab_reynolds = self.tabview.add("🌊  Reynolds & Akış Analizi")
        self.tab_grafik   = self.tabview.add("📊  Grafik Paneli")
        self.tab_tarama   = self.tabview.add("🔁  Parametrik Tarama")

        self._build_ana()
        self._build_sihirbaz()
        self._build_reynolds()
        self._build_grafik()
        self._build_tarama()

        self.update()
        self.hesapla(hafizaya_yaz=True)

    # ================================================================
    # YARDIMCI: Entry oluştur + debounce trace bağla
    # ================================================================
    def _entry(self, parent, label, default, row_pad=(3, 0)):
        fr = ctk.CTkFrame(parent, fg_color="transparent")
        fr.pack(pady=row_pad, fill="x", padx=14)
        ctk.CTkLabel(fr, text=label, font=("Arial", 11),
                     text_color=CLR_TEXT_SEC, anchor="w", width=235
                     ).pack(side="left")
        var = ctk.StringVar(value=str(default))
        ent = ctk.CTkEntry(fr, width=105, textvariable=var,
                           fg_color=CLR_BG_INPUT,
                           border_color=CLR_BORDER,
                           text_color=CLR_TEXT_PRI)
        ent.pack(side="right")
        var.trace_add("write", self._debounce_hesapla)
        return ent

    def _debounce_hesapla(self, *_):
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(self.DEBOUNCE_MS, self.hesapla)

    # ================================================================
    # SEKME 1 — TERMAL SİMÜLASYON
    # ================================================================
    def _build_ana(self):
        # Sol kaydırılabilir panel
        self.sol = ctk.CTkScrollableFrame(
            self.tab_ana, width=440, fg_color=CLR_BG_PANEL,
            scrollbar_button_color=CLR_BORDER)
        self.sol.pack(side="left", fill="y", padx=(6, 4), pady=6)

        # Sağ panel
        sag = ctk.CTkFrame(self.tab_ana, fg_color=CLR_BG_PANEL)
        sag.pack(side="right", fill="both", expand=True, padx=(4, 6), pady=6)

        # ── Başlık ──────────────────────────────────────────────────
        ctk.CTkLabel(
            self.sol, text="SİMÜLASYON PARAMETRELERİ",
            font=("Arial", 12, "bold"), text_color=CLR_CYAN,
        ).pack(pady=(12, 6), padx=14, anchor="w")

        # ── Akış tipi ────────────────────────────────────────────────
        self._section_label(self.sol, "Isı Değiştirici Konfigürasyonu")
        self.combo_akis = ctk.CTkOptionMenu(
            self.sol,
            values=["Zıt Akış (Counter-Flow)", "Paralel Akış (Parallel-Flow)"],
            fg_color=CLR_BG_INPUT, button_color=CLR_CYAN,
            button_hover_color="#3bbbd4", text_color=CLR_TEXT_PRI,
            dropdown_fg_color=CLR_BG_CARD, dropdown_text_color=CLR_TEXT_PRI,
            command=lambda _: self.hesapla(),
        )
        self.combo_akis.pack(pady=(2, 4), padx=14, fill="x")

        self.combo_egzoz = self._combo(
            self.sol, list(self.egzoz_db.keys()), "Egzoz Gazı / Yakıt Tipi:")
        self.combo_sogutucu = self._combo(
            self.sol, list(self.sogutucu_db.keys()), "Soğutucu Akışkan Tipi:")

        # ── Geçmiş butonları ─────────────────────────────────────────
        nav = ctk.CTkFrame(self.sol, fg_color="transparent")
        nav.pack(pady=(6, 2), padx=14, fill="x")
        self.btn_geri = ctk.CTkButton(
            nav, text="⬅  Geri", width=95, state="disabled",
            fg_color=CLR_BG_INPUT, hover_color=CLR_BORDER,
            text_color=CLR_TEXT_SEC, command=self._geri)
        self.btn_geri.pack(side="left")
        self.btn_ileri = ctk.CTkButton(
            nav, text="İleri  ➡", width=95, state="disabled",
            fg_color=CLR_BG_INPUT, hover_color=CLR_BORDER,
            text_color=CLR_TEXT_SEC, command=self._ileri)
        self.btn_ileri.pack(side="right")

        # ── Numerik girdiler ─────────────────────────────────────────
        self._section_label(self.sol, "Temel Termal Parametreler")
        self.ent_motor   = self._entry(self.sol, "Motor Gücü [kW]:", "120")
        self.ent_deb_e   = self._entry(self.sol, "Egzoz Debisi ṁₑ [kg/s]:", "0.15")
        self.ent_temp_ei = self._entry(self.sol, "Egzoz Giriş Sıcaklığı [°C]:", "450")
        self.ent_deb_s   = self._entry(self.sol, "Sıvı Debisi ṁₛ [kg/s]:", "0.5")
        self.ent_temp_si = self._entry(self.sol, "Sıvı Giriş Sıcaklığı [°C]:", "80")
        self.ent_U       = self._entry(self.sol, "Isı Transfer Katsayısı U [W/m²K]:", "280")

        self._section_label(self.sol, "Kanal / Geometri Parametreleri")
        self.ent_Dh      = self._entry(self.sol, "Hidrolik Çap Dₕ [mm]:", "11.4")
        self.ent_N       = self._entry(self.sol, "Kanal / Boru Sayısı N [adet]:", "90")
        self.ent_rho     = self._entry(self.sol, "Egzoz Yoğunluğu ρ [kg/m³]:", "0.45")
        self.ent_mu      = self._entry(self.sol, "Dinamik Viskozite μ [×10⁻⁵ Pa·s]:", "3.5")
        self.ent_Pr      = self._entry(self.sol, "Prandtl Sayısı Pr [-]:", "0.72")
        self.ent_k_gaz   = self._entry(self.sol, "Gaz Isıl İletkenliği k_gaz [W/mK]:", "0.055")
        self.ent_Ak      = self._entry(self.sol, "Tek Kanal Kesit Alanı Aₖ [mm²]:", "160")

        # ── Alan slider ──────────────────────────────────────────────
        self._section_label(self.sol, "Canlı Alan Kontrolü")
        self.slider = ctk.CTkSlider(
            self.sol, from_=0.1, to=3.5, number_of_steps=68,
            button_color=CLR_CYAN, button_hover_color="#3bbbd4",
            progress_color=CLR_CYAN, fg_color=CLR_BG_INPUT,
            command=self._slider_cb)
        self.slider.set(1.2)
        self.slider.pack(pady=(2, 0), padx=14, fill="x")
        self.lbl_slider = ctk.CTkLabel(
            self.sol, text="Alan: 1.20 m²",
            font=("Arial", 11, "bold"), text_color=CLR_CYAN)
        self.lbl_slider.pack(pady=(0, 4), padx=14, anchor="e")

        # ── Aksiyon butonları ────────────────────────────────────────
        ctk.CTkButton(
            self.sol, text="▶   SİMÜLASYONU ÇALIŞTIR",
            font=("Arial", 13, "bold"), height=42,
            fg_color=CLR_CYAN, hover_color="#3bbbd4",
            text_color="#0d1117", command=self.hesapla,
        ).pack(pady=(12, 4), padx=14, fill="x")

        ctk.CTkButton(
            self.sol, text="💾  METİN RAPORU KAYDET (.txt)",
            font=("Arial", 12), height=36,
            fg_color="#1c4a2e", hover_color="#245c38",
            text_color=CLR_GREEN, border_color=CLR_GREEN, border_width=1,
            command=self._rapor_kaydet,
        ).pack(pady=(0, 4), padx=14, fill="x")

        ctk.CTkButton(
            self.sol, text="📊  CSV OLARAK DIŞA AKTAR",
            font=("Arial", 12), height=36,
            fg_color="#1a2a3a", hover_color="#1f3348",
            text_color=CLR_CYAN, border_color=CLR_CYAN, border_width=1,
            command=self._csv_aktar,
        ).pack(pady=(0, 12), padx=14, fill="x")

        # ── Sağ panel: şema ──────────────────────────────────────────
        self.canvas_sema = ctk.CTkCanvas(
            sag, height=240, bg=CLR_BG_CARD, highlightthickness=0)
        self.canvas_sema.pack(fill="x", padx=8, pady=(8, 4))

        # ── Sağ panel: sonuç kartları ─────────────────────────────────
        sonuc_scroll = ctk.CTkScrollableFrame(
            sag, fg_color=CLR_BG_PANEL,
            scrollbar_button_color=CLR_BORDER)
        sonuc_scroll.pack(fill="both", expand=True, padx=8, pady=4)

        # Kart 1 — Sistem Özeti
        kart1 = KartFrame(sonuc_scroll, "⚙   SİSTEM VE AKIŞKAN ÖZELLİKLERİ", CLR_CYAN)
        kart1.pack(fill="x", pady=(0, 6))
        self.sr_akis    = SonucSatir(kart1, "Akış Tipi")
        self.sr_akis.pack(fill="x", pady=(4, 0))
        self.sr_egzoz   = SonucSatir(kart1, "Egzoz Gazı")
        self.sr_egzoz.pack(fill="x")
        self.sr_sog     = SonucSatir(kart1, "Soğutucu Akışkan")
        self.sr_sog.pack(fill="x")
        self.sr_motor   = SonucSatir(kart1, "Motor Gücü")
        self.sr_motor.pack(fill="x", pady=(0, 6))

        # Kart 2 — Geometrik Veriler
        kart2 = KartFrame(sonuc_scroll, "📐   GEOMETRİK & TRANSFER VERİLERİ", CLR_PURPLE)
        kart2.pack(fill="x", pady=(0, 6))
        self.sr_A     = SonucSatir(kart2, "Aktif Transfer Alanı A")
        self.sr_A.pack(fill="x", pady=(4, 0))
        self.sr_U     = SonucSatir(kart2, "Isı Geçiş Katsayısı U")
        self.sr_U.pack(fill="x")
        self.sr_LMTD  = SonucSatir(kart2, "Logaritmik Ort. Sıcaklık Farkı")
        self.sr_LMTD.pack(fill="x")
        self.sr_NTU   = SonucSatir(kart2, "NTU Sayısı")
        self.sr_NTU.pack(fill="x", pady=(0, 6))

        # Kart 3 — Enerji Bilançosu
        kart3 = KartFrame(sonuc_scroll, "🔥   ENERJİ BİLANÇOSU VE ÇIKTILAR", CLR_AMBER)
        kart3.pack(fill="x", pady=(0, 6))
        self.sr_Tei   = SonucSatir(kart3, "Egzoz Giriş Sıcaklığı",  deger_renk=CLR_EGZOZ)
        self.sr_Tei.pack(fill="x", pady=(4, 0))
        self.sr_Teo   = SonucSatir(kart3, "Egzoz Çıkış Sıcaklığı",  deger_renk=CLR_AMBER)
        self.sr_Teo.pack(fill="x")
        self.sr_Tsi   = SonucSatir(kart3, "Sıvı Giriş Sıcaklığı",   deger_renk=CLR_SIVI)
        self.sr_Tsi.pack(fill="x")
        self.sr_Tso   = SonucSatir(kart3, "Sıvı Çıkış Sıcaklığı",   deger_renk=CLR_CYAN)
        self.sr_Tso.pack(fill="x")
        AyiriciCizgi(kart3)
        self.sr_q     = SonucSatir(kart3, "Geri Kazanılan Isı Gücü", deger_renk=CLR_GREEN)
        self.sr_q.pack(fill="x")
        self.sr_eps   = SonucSatir(kart3, "Termal Etkinlik ε")
        self.sr_eps.pack(fill="x", pady=(0, 6))

        # ── Durum çubuğu ─────────────────────────────────────────────
        self.lbl_durum = ctk.CTkLabel(
            sag, text="● Sistem Hazır",
            font=("Arial", 12, "bold"),
            fg_color=CLR_BG_CARD, text_color=CLR_GREEN,
            height=38, corner_radius=6)
        self.lbl_durum.pack(fill="x", padx=8, pady=(4, 8))

    # ── Yardımcı section label & combo ──────────────────────────────
    def _section_label(self, parent, text):
        ctk.CTkLabel(
            parent, text=text.upper(),
            font=("Arial", 9, "bold"), text_color=CLR_TEXT_MUT,
        ).pack(pady=(10, 2), padx=14, anchor="w")

    def _combo(self, parent, values, label):
        self._section_label(parent, label)
        cb = ctk.CTkOptionMenu(
            parent, values=values,
            fg_color=CLR_BG_INPUT, button_color=CLR_CYAN,
            button_hover_color="#3bbbd4", text_color=CLR_TEXT_PRI,
            dropdown_fg_color=CLR_BG_CARD, dropdown_text_color=CLR_TEXT_PRI,
            command=lambda _: self.hesapla(),
        )
        cb.pack(pady=(2, 4), padx=14, fill="x")
        return cb

    def _slider_cb(self, val):
        self.lbl_slider.configure(text=f"Alan: {val:.2f} m²")
        self.hesapla(hafizaya_yaz=False)

    # ================================================================
    # SEKME 2 — GEOMETRİ & U HESAPLAMA SİHİRBAZI
    # ================================================================
    def _build_sihirbaz(self):
        ana = ctk.CTkScrollableFrame(
            self.tab_sihirbaz, fg_color=CLR_BG_PANEL,
            scrollbar_button_color=CLR_BORDER)
        ana.pack(fill="both", expand=True, padx=6, pady=6)

        ctk.CTkLabel(
            ana, text="GEOMETRİ, YÜZEY ALANI VE U KATSAYISI HESAPLAMA MERKEZİ",
            font=("Arial", 13, "bold"), text_color=CLR_CYAN,
        ).pack(pady=(12, 2))
        ctk.CTkLabel(
            ana, text="Profil seçin → Boyutları girin → Hesapla → Simülasyona Aktar",
            font=("Arial", 10), text_color=CLR_TEXT_SEC,
        ).pack(pady=(0, 10))

        # ── BÖLÜM 1: YÜZEY ALANI ────────────────────────────────────
        frm_alan = KartFrame(ana, "📐   YÜZEY ALANI HESAPLAYICI", CLR_CYAN)
        frm_alan.pack(fill="x", padx=10, pady=(0, 8))

        profil_row = ctk.CTkFrame(frm_alan, fg_color="transparent")
        profil_row.pack(fill="x", padx=14, pady=(10, 4))
        ctk.CTkLabel(profil_row, text="Kanal / Boru Profili:",
                     font=("Arial", 11), text_color=CLR_TEXT_SEC,
                     width=200, anchor="w").pack(side="left")
        self.combo_profil = ctk.CTkOptionMenu(
            profil_row,
            values=["Yuvarlak Boru (Circular)",
                    "Dikdörtgen Kanal (Rectangular)",
                    "Kare Kanal (Square)",
                    "Eliptik Boru (Elliptical)",
                    "Üçgen Kanal (Triangular)",
                    "Altıgen Kanal (Hexagonal)"],
            fg_color=CLR_BG_INPUT, button_color=CLR_CYAN,
            button_hover_color="#3bbbd4", text_color=CLR_TEXT_PRI,
            dropdown_fg_color=CLR_BG_CARD, dropdown_text_color=CLR_TEXT_PRI,
            width=280, command=self._profil_degisti,
        )
        self.combo_profil.pack(side="left", padx=8)

        self.frm_profil_giris = ctk.CTkFrame(
            frm_alan, fg_color=CLR_BG_INPUT, corner_radius=8)
        self.frm_profil_giris.pack(fill="x", padx=14, pady=6)

        self.ent_alan_L = self._sihirbaz_entry(frm_alan, "Kanal / Boru Etkin Uzunluğu L [mm]:", "350")
        self.ent_alan_N = self._sihirbaz_entry(frm_alan, "Toplam Kanal / Boru Sayısı N [adet]:", "90")

        self.lbl_formul = ctk.CTkLabel(
            frm_alan, text="", font=("Arial", 10, "italic"),
            text_color=CLR_AMBER, wraplength=860, justify="left")
        self.lbl_formul.pack(padx=14, pady=2, anchor="w")

        sonuc_row = ctk.CTkFrame(frm_alan, fg_color="transparent")
        sonuc_row.pack(fill="x", padx=14, pady=(6, 12))
        self.lbl_alan_sonuc = ctk.CTkLabel(
            sonuc_row, text="Toplam Alan: —  m²",
            font=("Arial", 13, "bold"), text_color=CLR_CYAN, width=300, anchor="w")
        self.lbl_alan_sonuc.pack(side="left")
        ctk.CTkButton(
            sonuc_row, text="Hesapla & Simülasyona Aktar  💾",
            font=("Arial", 12, "bold"), width=270,
            fg_color=CLR_AMBER, hover_color="#c8890a",
            text_color="#0d1117", command=self._sihirbaz_aktar,
        ).pack(side="right")

        self._profil_widget = {}
        self._profil_degisti("Yuvarlak Boru (Circular)")

        # ── BÖLÜM 2: U KATSAYISI ─────────────────────────────────────
        frm_u = KartFrame(ana, "🔬   TOPLAM ISI GEÇİŞ KATSAYISI (U) HESAPLAYICI", CLR_PURPLE)
        frm_u.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(
            frm_u,
            text="1/U = 1/h_iç  +  t_duvar/k_duvar  +  1/h_dış  +  2·R_fouling   →   Seri ısıl direnç modeli",
            font=("Arial", 10, "italic"), text_color=CLR_TEXT_SEC,
        ).pack(padx=14, pady=(10, 4), anchor="w")

        # Malzeme seçimi
        malz_row = ctk.CTkFrame(frm_u, fg_color="transparent")
        malz_row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(malz_row, text="Duvar Malzemesi:",
                     font=("Arial", 11), text_color=CLR_TEXT_SEC,
                     width=200, anchor="w").pack(side="left")
        self.combo_malzeme = ctk.CTkOptionMenu(
            malz_row, values=list(self.malzeme_db.keys()),
            fg_color=CLR_BG_INPUT, button_color=CLR_PURPLE,
            button_hover_color="#9a6ee0", text_color=CLR_TEXT_PRI,
            dropdown_fg_color=CLR_BG_CARD, dropdown_text_color=CLR_TEXT_PRI,
            width=320, command=self._malzeme_degisti,
        )
        self.combo_malzeme.pack(side="left", padx=8)

        self.ent_u_hic   = self._sihirbaz_entry(frm_u, "İç Konveksiyon Katsayısı h_iç [W/m²K]:", "250")
        self.ent_u_hdis  = self._sihirbaz_entry(frm_u, "Dış Konveksiyon Katsayısı h_dış [W/m²K]:", "3500")
        self.ent_u_t     = self._sihirbaz_entry(frm_u, "Duvar Kalınlığı t [mm]:", "1.0")

        self.frm_k_manuel = ctk.CTkFrame(frm_u, fg_color="transparent")
        self.ent_u_k = self._sihirbaz_entry(self.frm_k_manuel, "Isıl İletkenlik k [W/mK] (Manuel):", "16")
        self.frm_k_manuel.pack_forget()

        fouling_row = ctk.CTkFrame(frm_u, fg_color="transparent")
        fouling_row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(fouling_row, text="Kirlenme Direnci R_fouling [m²K/W]  (0 = ihmal):",
                     font=("Arial", 11), text_color=CLR_TEXT_SEC,
                     width=360, anchor="w").pack(side="left")
        self.ent_u_fouling = ctk.CTkEntry(
            fouling_row, width=105, fg_color=CLR_BG_INPUT,
            border_color=CLR_BORDER, text_color=CLR_TEXT_PRI)
        self.ent_u_fouling.insert(0, "0.0001")
        self.ent_u_fouling.pack(side="right")

        u_sonuc_row = ctk.CTkFrame(frm_u, fg_color="transparent")
        u_sonuc_row.pack(fill="x", padx=14, pady=(8, 6))
        self.lbl_u_sonuc = ctk.CTkLabel(
            u_sonuc_row, text="Hesaplanan U: —  W/m²K",
            font=("Arial", 13, "bold"), text_color=CLR_PURPLE, width=320, anchor="w")
        self.lbl_u_sonuc.pack(side="left")
        ctk.CTkButton(
            u_sonuc_row, text="Hesapla & U Değerine Aktar  🔬",
            font=("Arial", 12, "bold"), width=270,
            fg_color=CLR_PURPLE, hover_color="#9a6ee0",
            text_color="#0d1117", command=self._u_hesapla,
        ).pack(side="right")

        # U direnç detay kartı
        self.frm_u_detay = KartFrame(frm_u, "Isıl Direnç Dökümü", CLR_TEXT_MUT)
        self.frm_u_detay.pack(fill="x", padx=14, pady=(0, 12))
        self.u_detay_satirlar = {}
        for anahtar, etiket in [
            ("R_ic",    "R_iç  = 1/h_iç"),
            ("R_duvar", "R_duvar  = t/k"),
            ("R_dis",   "R_dış  = 1/h_dış"),
            ("R_foul",  "R_fouling  = 2×Rf"),
            ("R_top",   "R_toplam"),
            ("U_val",   "U  = 1/R_toplam"),
        ]:
            s = SonucSatir(self.frm_u_detay, etiket,
                           deger_renk=CLR_PURPLE if anahtar == "U_val" else CLR_TEXT_PRI)
            s.pack(fill="x", pady=(2 if anahtar != "R_ic" else 6, 0))
            self.u_detay_satirlar[anahtar] = s
        ctk.CTkFrame(self.frm_u_detay, height=6, fg_color="transparent").pack()

    def _sihirbaz_entry(self, parent, label, default):
        fr = ctk.CTkFrame(parent, fg_color="transparent")
        fr.pack(pady=3, fill="x", padx=14)
        ctk.CTkLabel(fr, text=label, font=("Arial", 11),
                     text_color=CLR_TEXT_SEC, anchor="w", width=360
                     ).pack(side="left")
        ent = ctk.CTkEntry(fr, width=105, fg_color=CLR_BG_INPUT,
                           border_color=CLR_BORDER, text_color=CLR_TEXT_PRI)
        ent.insert(0, default)
        ent.pack(side="right")
        return ent

    def _profil_degisti(self, secim):
        for w in self.frm_profil_giris.winfo_children():
            w.destroy()
        self._profil_widget = {}

        tanim = {
            "Yuvarlak Boru (Circular)": {
                "alanlar": [("Dış Çap d [mm]", "12")],
                "formul": "A = π × d × L × N     |    Dₕ = d",
            },
            "Dikdörtgen Kanal (Rectangular)": {
                "alanlar": [("Kanal Genişliği a [mm]", "20"), ("Kanal Yüksekliği b [mm]", "8")],
                "formul": "A = 2(a+b) × L × N    |    Dₕ = 2ab/(a+b)",
            },
            "Kare Kanal (Square)": {
                "alanlar": [("Kenar Uzunluğu a [mm]", "12")],
                "formul": "A = 4a × L × N         |    Dₕ = a",
            },
            "Eliptik Boru (Elliptical)": {
                "alanlar": [("Büyük Yarı Eksen a [mm]", "15"), ("Küçük Yarı Eksen b [mm]", "7")],
                "formul": "A ≈ π(a+b)(1 + 3h/(10+√(4−3h))) × L × N   (Ramanujan 2. yakl.)   |   h = ((a−b)/(a+b))²",
            },
            "Üçgen Kanal (Triangular)": {
                "alanlar": [("Taban c [mm]", "12"), ("Yükseklik h [mm]", "10")],
                "formul": "A = (c + 2√((c/2)²+h²)) × L × N    |    Dₕ = (c×h) / (c/2 + √((c/2)²+h²))",
            },
            "Altıgen Kanal (Hexagonal)": {
                "alanlar": [("Kenar Uzunluğu s [mm]", "8")],
                "formul": "A = 6s × L × N          |    Dₕ = s√3",
            },
        }

        if secim not in tanim:
            return
        for etiket, varsayilan in tanim[secim]["alanlar"]:
            satir = ctk.CTkFrame(self.frm_profil_giris, fg_color="transparent")
            satir.pack(fill="x", padx=10, pady=3)
            ctk.CTkLabel(satir, text=etiket, font=("Arial", 11),
                         text_color=CLR_TEXT_SEC, width=240, anchor="w").pack(side="left")
            ent = ctk.CTkEntry(satir, width=105, fg_color=CLR_BG_CARD,
                               border_color=CLR_BORDER, text_color=CLR_TEXT_PRI)
            ent.insert(0, varsayilan)
            ent.pack(side="right")
            self._profil_widget[etiket] = ent
        self.lbl_formul.configure(text=f"📌  {tanim[secim]['formul']}")

    def _malzeme_degisti(self, secim):
        if secim == "Manuel Giriş":
            self.frm_k_manuel.pack(fill="x", padx=14)
        else:
            self.frm_k_manuel.pack_forget()

    def _sihirbaz_aktar(self):
        """Yüzey alanı hesapla ve simülasyona aktar; D_h & A_k da güncelle."""
        try:
            profil = self.combo_profil.get()
            L = float(self.ent_alan_L.get()) / 1000.0
            N = float(self.ent_alan_N.get())
            if L <= 0 or N <= 0:
                raise ValueError("L ve N > 0 olmalıdır.")

            w = {k: float(v.get()) / 1000.0 for k, v in self._profil_widget.items()}
            vals = list(w.values())

            alan = Dh_m = Ak_m2 = 0.0

            if profil == "Yuvarlak Boru (Circular)":
                d = vals[0]
                if d <= 0: raise ValueError("Çap > 0 olmalı.")
                alan = math.pi * d * L * N
                Dh_m = d
                Ak_m2 = math.pi * (d / 2) ** 2

            elif profil == "Dikdörtgen Kanal (Rectangular)":
                a, b = vals[0], vals[1]
                if a <= 0 or b <= 0: raise ValueError("a, b > 0 olmalı.")
                alan = 2 * (a + b) * L * N
                Dh_m = 2 * a * b / (a + b)
                Ak_m2 = a * b

            elif profil == "Kare Kanal (Square)":
                a = vals[0]
                if a <= 0: raise ValueError("Kenar > 0 olmalı.")
                alan = 4 * a * L * N
                Dh_m = a
                Ak_m2 = a ** 2

            elif profil == "Eliptik Boru (Elliptical)":
                a, b = vals[0], vals[1]
                if a <= 0 or b <= 0: raise ValueError("a, b > 0 olmalı.")
                # Ramanujan 2. yaklaşım (doğru formül)
                h_ram = ((a - b) / (a + b)) ** 2
                cevre = math.pi * (a + b) * (1 + 3 * h_ram / (10 + math.sqrt(4 - 3 * h_ram)))
                alan = cevre * L * N
                # Hidrolik çap: 4A/P ≈ 4(πab)/cevre
                Ak_m2 = math.pi * a * b
                Dh_m = 4 * Ak_m2 / cevre

            elif profil == "Üçgen Kanal (Triangular)":
                c, h = vals[0], vals[1]
                if c <= 0 or h <= 0: raise ValueError("c, h > 0 olmalı.")
                kenar = math.sqrt((c / 2) ** 2 + h ** 2)
                cevre = c + 2 * kenar
                alan = cevre * L * N
                Ak_m2 = 0.5 * c * h
                Dh_m = 4 * Ak_m2 / cevre

            elif profil == "Altıgen Kanal (Hexagonal)":
                s = vals[0]
                if s <= 0: raise ValueError("Kenar > 0 olmalı.")
                alan = 6 * s * L * N
                Ak_m2 = (3 * math.sqrt(3) / 2) * s ** 2
                Dh_m = s * math.sqrt(3)

            else:
                raise ValueError("Bilinmeyen profil.")

            self.lbl_alan_sonuc.configure(text=f"Toplam Alan: {alan:.4f} m²")
            self.slider.set(min(max(alan, 0.1), 3.5))
            self.lbl_slider.configure(text=f"Alan: {alan:.2f} m²")

            # D_h ve A_k de ana simülasyona aktar
            self.ent_Dh.delete(0, "end"); self.ent_Dh.insert(0, f"{Dh_m * 1000:.3f}")
            self.ent_Ak.delete(0, "end"); self.ent_Ak.insert(0, f"{Ak_m2 * 1e6:.2f}")
            self.ent_N.delete(0, "end");  self.ent_N.insert(0, str(int(N)))

            messagebox.showinfo("Başarılı",
                f"[{profil}]\n"
                f"Alan = {alan:.4f} m²\n"
                f"Dₕ   = {Dh_m * 1000:.3f} mm\n"
                f"Aₖ   = {Ak_m2 * 1e6:.2f} mm²\n\n"
                "Tüm değerler simülasyon motoruna aktarıldı.")
            self.tabview.set("⚙  Termal Simülasyon")
            self.hesapla()

        except (ValueError, ZeroDivisionError) as e:
            messagebox.showerror("Geometri Hatası", str(e))

    def _u_hesapla(self):
        try:
            h_ic  = float(self.ent_u_hic.get())
            h_dis = float(self.ent_u_hdis.get())
            t_mm  = float(self.ent_u_t.get())
            R_f   = float(self.ent_u_fouling.get())
            if h_ic <= 0 or h_dis <= 0: raise ValueError("h_iç, h_dış > 0 olmalı.")
            if t_mm < 0: raise ValueError("Duvar kalınlığı ≥ 0 olmalı.")

            mal = self.combo_malzeme.get()
            k = self.malzeme_db.get(mal)
            if k is None:
                k = float(self.ent_u_k.get())
                if k <= 0: raise ValueError("k > 0 olmalı.")

            t = t_mm / 1000.0
            R_ic    = 1.0 / h_ic
            R_duvar = t / k if t > 0 and k > 0 else 0.0
            R_dis   = 1.0 / h_dis
            R_foul  = 2 * R_f
            R_top   = R_ic + R_duvar + R_dis + R_foul
            U       = 1.0 / R_top

            self.lbl_u_sonuc.configure(text=f"Hesaplanan U: {U:.2f} W/m²K")
            self.u_detay_satirlar["R_ic"].set(f"{R_ic:.6f}  m²K/W")
            self.u_detay_satirlar["R_duvar"].set(f"{R_duvar:.6f}  m²K/W")
            self.u_detay_satirlar["R_dis"].set(f"{R_dis:.6f}  m²K/W")
            self.u_detay_satirlar["R_foul"].set(f"{R_foul:.6f}  m²K/W")
            self.u_detay_satirlar["R_top"].set(f"{R_top:.6f}  m²K/W")
            self.u_detay_satirlar["U_val"].set(f"{U:.2f}  W/m²K", renk=CLR_PURPLE)

            # Ana simülasyon U kutusuna yaz
            self.ent_U.delete(0, "end")
            self.ent_U.insert(0, f"{U:.2f}")

            messagebox.showinfo("Başarılı", f"U = {U:.2f} W/m²K hesaplandı ve aktarıldı.")
            self.tabview.set("⚙  Termal Simülasyon")
            self.hesapla()

        except (ValueError, ZeroDivisionError) as e:
            messagebox.showerror("U Hesap Hatası", str(e))

    # ================================================================
    # SEKME 3 — REYNOLDS & AKIŞ ANALİZİ
    # ================================================================
    def _build_reynolds(self):
        ana = ctk.CTkScrollableFrame(
            self.tab_reynolds, fg_color=CLR_BG_PANEL,
            scrollbar_button_color=CLR_BORDER)
        ana.pack(fill="both", expand=True, padx=6, pady=6)

        ctk.CTkLabel(
            ana, text="REYNOLDS SAYISI & AKIŞ REJİMİ ANALİZ MERKEZİ",
            font=("Arial", 13, "bold"), text_color=CLR_PURPLE,
        ).pack(pady=(12, 4))

        ctk.CTkButton(
            ana, text="🔄   Reynolds & Tek Kanal Analizini Hesapla",
            font=("Arial", 13, "bold"), height=42,
            fg_color=CLR_PURPLE, hover_color="#9a6ee0",
            text_color="#0d1117", command=self._reynolds_hesapla,
        ).pack(fill="x", padx=10, pady=(0, 8))

        # Durum çubuğu
        self.lbl_re_bar = ctk.CTkLabel(
            ana, text="— Henüz hesaplanmadı —",
            font=("Arial", 12, "bold"), fg_color=CLR_BG_CARD,
            height=42, text_color=CLR_TEXT_SEC, corner_radius=6)
        self.lbl_re_bar.pack(fill="x", padx=10, pady=(0, 8))

        # İki kolon
        kolon = ctk.CTkFrame(ana, fg_color="transparent")
        kolon.pack(fill="both", expand=True, padx=10)
        kolon.columnconfigure(0, weight=1)
        kolon.columnconfigure(1, weight=1)

        kart_re = KartFrame(kolon, "📐   AKIŞ REJİMİ & NUSSELT ANALİZİ", CLR_PURPLE)
        kart_re.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=0)
        kart_isi = KartFrame(kolon, "🔥   TEK KANAL & TOPLAM ISI TRANSFERİ", CLR_AMBER)
        kart_isi.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=0)

        # Reynolds kart satırları
        re_keys = [
            ("Re",    "Reynolds Sayısı Re",         CLR_PURPLE),
            ("v",     "Kanal Akış Hızı v",           CLR_TEXT_PRI),
            ("Dh",    "Hidrolik Çap Dₕ",             CLR_TEXT_PRI),
            ("rejim", "Akış Rejimi",                 CLR_CYAN),
            ("Nu",    "Nusselt Sayısı Nu",            CLR_PURPLE),
            ("hic",   "h_iç (Reynolds'dan)",         CLR_CYAN),
            ("f",     "Darcy Sürtünme Katsayısı f",  CLR_TEXT_SEC),
            ("dP",    "Baskı Düşümü ΔP",             CLR_AMBER),
            ("yontem","Nusselt Yöntemi",              CLR_TEXT_MUT),
        ]
        self.re_satirlar = {}
        for i, (key, etiket, renk) in enumerate(re_keys):
            s = SonucSatir(kart_re, etiket, deger_renk=renk)
            s.pack(fill="x", pady=(6 if i == 0 else 2, 0))
            self.re_satirlar[key] = s
        ctk.CTkFrame(kart_re, height=8, fg_color="transparent").pack()

        # Isı kart satırları
        isi_keys = [
            ("N",      "Toplam Kanal Sayısı N",        CLR_TEXT_PRI),
            ("A",      "Transfer Alanı A",              CLR_CYAN),
            ("NTU",    "NTU Sayısı",                    CLR_PURPLE),
            ("eps",    "Etkinlik ε",                    CLR_GREEN),
            ("q_max",  "q_max (teorik)",                CLR_TEXT_SEC),
            ("q_top",  "q_toplam (gerçek)",             CLR_GREEN),
            ("Teo",    "Egzoz Çıkış T°C",               CLR_AMBER),
            ("Tso",    "Sıvı Çıkış T°C",                CLR_CYAN),
            ("q_tek",  "Tek Kanal q [W]",               CLR_TEXT_PRI),
            ("hU_oran","h_iç / U oranı",                CLR_AMBER),
        ]
        self.isi_satirlar = {}
        for i, (key, etiket, renk) in enumerate(isi_keys):
            s = SonucSatir(kart_isi, etiket, deger_renk=renk)
            s.pack(fill="x", pady=(6 if i == 0 else 2, 0))
            self.isi_satirlar[key] = s
        ctk.CTkFrame(kart_isi, height=8, fg_color="transparent").pack()

        # Uyarı kartı
        kart_uy = KartFrame(ana, "⚠   TASARIM ÖNERİLERİ & UYARILAR", CLR_AMBER)
        kart_uy.pack(fill="x", padx=10, pady=(8, 8))
        self.frm_uyari_ic = ctk.CTkFrame(kart_uy, fg_color="transparent")
        self.frm_uyari_ic.pack(fill="x", padx=8, pady=(4, 8))

    def _reynolds_hesapla(self):
        try:
            m_e   = float(self.ent_deb_e.get())
            T_ei  = float(self.ent_temp_ei.get())
            T_si  = float(self.ent_temp_si.get())
            U     = float(self.ent_U.get())
            A     = self.slider.get()
            cp_e  = self.egzoz_db[self.combo_egzoz.get()]
            cp_s  = self.sogutucu_db[self.combo_sogutucu.get()]
            m_s   = float(self.ent_deb_s.get())
            akis  = self.combo_akis.get()
            Dh    = float(self.ent_Dh.get()) / 1000.0
            N     = int(float(self.ent_N.get()))
            rho   = float(self.ent_rho.get())
            mu    = float(self.ent_mu.get()) * 1e-5
            Pr    = float(self.ent_Pr.get())
            k_g   = float(self.ent_k_gaz.get())
            Ak    = float(self.ent_Ak.get()) * 1e-6

            if Dh <= 0 or N <= 0 or rho <= 0 or mu <= 0 or Ak <= 0:
                raise ValueError("Geometri/akışkan değerleri > 0 olmalıdır.")

            # Hız ve Reynolds
            v    = m_e / (N * Ak * rho)
            Re   = rho * v * Dh / mu

            # Rejim
            if Re < 2300:
                rejim_txt = "LAMİNER"; bar_renk = "#1a3a2e"; bar_yazi = CLR_GREEN
            elif Re < 4000:
                rejim_txt = "GEÇİŞ (Transition)"; bar_renk = "#3a2a00"; bar_yazi = CLR_AMBER
            else:
                rejim_txt = "TÜRBÜLANSLÜ"; bar_renk = "#3a1010"; bar_yazi = CLR_RED

            # Nusselt
            profil = self.combo_profil.get() if hasattr(self, "combo_profil") else ""
            if Re >= 4000:
                f_D   = (0.790 * math.log(Re) - 1.64) ** -2
                Nu    = ((f_D / 8) * (Re - 1000) * Pr
                         / (1 + 12.7 * math.sqrt(f_D / 8) * (Pr ** (2/3) - 1)))
                nu_y  = "Gnielinski (türbülanslı)"
            elif Re >= 2300:
                def gniel(R):
                    ff = (0.790 * math.log(R) - 1.64) ** -2
                    return ff, (ff/8)*(R-1000)*Pr/(1+12.7*math.sqrt(ff/8)*(Pr**(2/3)-1))
                f2, Nu2 = gniel(2300)
                f4, Nu4 = gniel(4000)
                g = (Re - 2300) / 1700
                Nu = (1 - g) * Nu2 + g * Nu4
                f_D = (1 - g) * f2 + g * f4
                nu_y = "Gnielinski interpolasyon (geçiş)"
            else:
                # Laminer: profile göre
                if "Kare" in profil:
                    Nu = 2.98; nu_y = "Nu=2.98 laminer kare kanal (sabit T_duvar)"
                elif "Dikdörtgen" in profil:
                    Nu = 3.39; nu_y = "Nu=3.39 laminer dikdörtgen (ortalama, sabit T_duvar)"
                else:
                    Nu = 3.66; nu_y = "Nu=3.66 laminer yuvarlak boru (sabit T_duvar)"
                f_D = 64.0 / Re

            h_ic_Re = Nu * k_g / Dh

            # NTU-ε (düzeltilmiş C_r=1 koşulları)
            C_e   = m_e * cp_e
            C_s   = m_s * cp_s
            C_min = min(C_e, C_s)
            C_max = max(C_e, C_s)
            C_r   = C_min / C_max
            NTU   = U * A / C_min
            eps   = _ntu_eps(NTU, C_r, akis)
            q_max = C_min * (T_ei - T_si)
            q_top = eps * q_max
            T_eo  = T_ei - q_top / C_e
            T_so  = T_si + q_top / C_s

            # Baskı düşümü (L = A / (N × Çevre) — yuvarlak yaklaşım)
            L_tah = A / (N * math.pi * Dh) if Dh > 0 and N > 0 else 0.0
            dP    = f_D * (L_tah / Dh) * (rho * v ** 2 / 2) if L_tah > 0 else 0.0

            # Kart güncelle
            self.re_satirlar["Re"].set(f"{Re:.1f}")
            self.re_satirlar["v"].set(f"{v:.3f} m/s")
            self.re_satirlar["Dh"].set(f"{Dh*1000:.2f} mm")
            self.re_satirlar["rejim"].set(rejim_txt,
                renk=CLR_GREEN if Re < 2300 else (CLR_AMBER if Re < 4000 else CLR_RED))
            self.re_satirlar["Nu"].set(f"{Nu:.2f}")
            self.re_satirlar["hic"].set(f"{h_ic_Re:.1f} W/m²K")
            self.re_satirlar["f"].set(f"{f_D:.5f}")
            self.re_satirlar["dP"].set(f"{dP:.1f} Pa  ({dP/1000:.3f} kPa)")
            self.re_satirlar["yontem"].set(nu_y, renk=CLR_TEXT_MUT)

            self.isi_satirlar["N"].set(str(N))
            self.isi_satirlar["A"].set(f"{A:.4f} m²")
            self.isi_satirlar["NTU"].set(f"{NTU:.4f}")
            self.isi_satirlar["eps"].set(f"{eps*100:.2f} %",
                renk=CLR_GREEN if eps >= 0.6 else CLR_AMBER)
            self.isi_satirlar["q_max"].set(f"{q_max/1000:.2f} kW")
            self.isi_satirlar["q_top"].set(f"{q_top/1000:.2f} kW")
            self.isi_satirlar["Teo"].set(f"{T_eo:.2f} °C")
            self.isi_satirlar["Tso"].set(f"{T_so:.2f} °C")
            self.isi_satirlar["q_tek"].set(f"{q_top/N:.2f} W")
            oran = h_ic_Re / U if U > 0 else 0
            self.isi_satirlar["hU_oran"].set(
                f"{oran:.2f}  {'⚠ U > h_iç' if oran < 1 else '✓'}",
                renk=CLR_RED if oran < 1 else CLR_GREEN)

            # Durum çubuğu
            self.lbl_re_bar.configure(
                fg_color=bar_renk, text_color=bar_yazi,
                text=f"Re = {Re:.0f}  |  {rejim_txt}  |  Nu = {Nu:.1f}  "
                     f"|  h_iç = {h_ic_Re:.0f} W/m²K  |  v = {v:.2f} m/s")

            # Uyarılar
            for w in self.frm_uyari_ic.winfo_children():
                w.destroy()
            uyarilar = _olustur_uyarilar(Re, v, dP, h_ic_Re, U, T_eo, eps)
            for ikon, mesaj, renk in uyarilar:
                fr = ctk.CTkFrame(self.frm_uyari_ic, fg_color=CLR_BG_INPUT,
                                  corner_radius=6)
                fr.pack(fill="x", pady=2)
                ctk.CTkLabel(fr, text=ikon, font=("Arial", 14),
                             text_color=renk, width=28).pack(side="left", padx=(8, 4), pady=4)
                ctk.CTkLabel(fr, text=mesaj, font=("Arial", 11),
                             text_color=CLR_TEXT_PRI, anchor="w",
                             wraplength=820).pack(side="left", pady=4)

        except (ValueError, ZeroDivisionError) as e:
            messagebox.showerror("Reynolds Hatası", str(e))

    # ================================================================
    # SEKME 4 — GRAFİK PANELİ
    # ================================================================
    def _build_grafik(self):
        self.canvas_grafik = ctk.CTkCanvas(
            self.tab_grafik, bg=CLR_BG_DEEP, highlightthickness=0)
        self.canvas_grafik.pack(fill="both", expand=True, padx=10, pady=10)
        self.canvas_grafik.bind("<Configure>",
            lambda e: self.after(100, self.hesapla))

    # ================================================================
    # SEKME 5 — PARAMETRİK TARAMA
    # ================================================================
    def _build_tarama(self):
        ana = ctk.CTkFrame(self.tab_tarama, fg_color=CLR_BG_PANEL)
        ana.pack(fill="both", expand=True, padx=6, pady=6)

        ctk.CTkLabel(
            ana, text="PARAMETRİK ALAN TARAMASI — Farklı A değerleri için q ve ε",
            font=("Arial", 13, "bold"), text_color=CLR_CYAN,
        ).pack(pady=(12, 4))

        kontrol = ctk.CTkFrame(ana, fg_color="transparent")
        kontrol.pack(fill="x", padx=14, pady=4)

        ctk.CTkLabel(kontrol, text="A min [m²]:", font=("Arial", 11),
                     text_color=CLR_TEXT_SEC).pack(side="left", padx=(0, 4))
        self.ent_tar_min = ctk.CTkEntry(kontrol, width=70, fg_color=CLR_BG_INPUT,
                                        border_color=CLR_BORDER, text_color=CLR_TEXT_PRI)
        self.ent_tar_min.insert(0, "0.2")
        self.ent_tar_min.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(kontrol, text="A max [m²]:", font=("Arial", 11),
                     text_color=CLR_TEXT_SEC).pack(side="left", padx=(0, 4))
        self.ent_tar_max = ctk.CTkEntry(kontrol, width=70, fg_color=CLR_BG_INPUT,
                                        border_color=CLR_BORDER, text_color=CLR_TEXT_PRI)
        self.ent_tar_max.insert(0, "3.0")
        self.ent_tar_max.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(kontrol, text="Adım sayısı:", font=("Arial", 11),
                     text_color=CLR_TEXT_SEC).pack(side="left", padx=(0, 4))
        self.ent_tar_adim = ctk.CTkEntry(kontrol, width=60, fg_color=CLR_BG_INPUT,
                                          border_color=CLR_BORDER, text_color=CLR_TEXT_PRI)
        self.ent_tar_adim.insert(0, "20")
        self.ent_tar_adim.pack(side="left", padx=(0, 16))

        ctk.CTkButton(
            kontrol, text="Taramayı Başlat", font=("Arial", 12, "bold"),
            fg_color=CLR_CYAN, hover_color="#3bbbd4", text_color="#0d1117",
            command=self._tarama_yap,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            kontrol, text="CSV Kaydet", font=("Arial", 12),
            fg_color="#1a2a3a", hover_color="#1f3348",
            text_color=CLR_CYAN, border_color=CLR_CYAN, border_width=1,
            command=self._tarama_csv,
        ).pack(side="left")

        # Tablo başlığı
        self.frm_tablo = ctk.CTkScrollableFrame(
            ana, fg_color=CLR_BG_PANEL,
            scrollbar_button_color=CLR_BORDER)
        self.frm_tablo.pack(fill="both", expand=True, padx=8, pady=(8, 8))

        baslik = ctk.CTkFrame(self.frm_tablo, fg_color=CLR_BG_CARD, corner_radius=6)
        baslik.pack(fill="x", pady=(0, 2))
        for txt, w in [("Alan A [m²]", 140), ("NTU", 100), ("Etkinlik ε [%]", 130),
                       ("q [kW]", 120), ("T_egzoz_çıkış [°C]", 160), ("T_sıvı_çıkış [°C]", 160)]:
            ctk.CTkLabel(baslik, text=txt, font=("Arial", 11, "bold"),
                         text_color=CLR_CYAN, width=w, anchor="center").pack(side="left", padx=2)

        self._tarama_data = []
        self._tarama_satirlar = []

    def _tarama_yap(self):
        for w in self._tarama_satirlar:
            w.destroy()
        self._tarama_satirlar.clear()
        self._tarama_data.clear()
        try:
            A_min  = float(self.ent_tar_min.get())
            A_max  = float(self.ent_tar_max.get())
            n_adim = int(self.ent_tar_adim.get())
            if A_min >= A_max or n_adim < 2: raise ValueError
        except Exception:
            messagebox.showerror("Tarama Hatası", "Geçerli A min/max/adım girin.")
            return
        try:
            m_e  = float(self.ent_deb_e.get())
            T_ei = float(self.ent_temp_ei.get())
            T_si = float(self.ent_temp_si.get())
            U    = float(self.ent_U.get())
            cp_e = self.egzoz_db[self.combo_egzoz.get()]
            cp_s = self.sogutucu_db[self.combo_sogutucu.get()]
            m_s  = float(self.ent_deb_s.get())
            akis = self.combo_akis.get()
        except Exception:
            messagebox.showerror("Tarama Hatası", "Simülasyon parametrelerini kontrol edin.")
            return

        C_e   = m_e * cp_e; C_s = m_s * cp_s
        C_min = min(C_e, C_s); C_max = max(C_e, C_s)
        C_r   = C_min / C_max

        for i in range(n_adim):
            A    = A_min + (A_max - A_min) * i / (n_adim - 1)
            NTU  = U * A / C_min
            eps  = _ntu_eps(NTU, C_r, akis)
            q    = eps * C_min * (T_ei - T_si)
            Teo  = T_ei - q / C_e
            Tso  = T_si + q / C_s

            self._tarama_data.append([A, NTU, eps*100, q/1000, Teo, Tso])

            if Teo > 190:    renk = CLR_RED
            elif Teo > 110:  renk = CLR_GREEN
            else:            renk = CLR_AMBER

            satir = ctk.CTkFrame(self.frm_tablo,
                                 fg_color=CLR_BG_CARD if i % 2 == 0 else CLR_BG_INPUT,
                                 corner_radius=4)
            satir.pack(fill="x", pady=1)
            for deger, w in [(f"{A:.3f}", 140), (f"{NTU:.3f}", 100),
                             (f"{eps*100:.1f}", 130), (f"{q/1000:.2f}", 120),
                             (f"{Teo:.1f}", 160), (f"{Tso:.1f}", 160)]:
                ctk.CTkLabel(satir, text=deger, font=("Courier New", 11),
                             text_color=renk, width=w, anchor="center").pack(side="left", padx=2)
            self._tarama_satirlar.append(satir)

    def _tarama_csv(self):
        if not self._tarama_data:
            messagebox.showwarning("Uyarı", "Önce tarama yapın.")
            return
        dosya = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            title="Tarama Sonuçlarını Kaydet")
        if not dosya: return
        with open(dosya, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Alan_m2", "NTU", "Etkinlik_%", "q_kW",
                        "T_egzoz_cikis_C", "T_sivi_cikis_C"])
            w.writerows(self._tarama_data)
        messagebox.showinfo("Başarılı", f"CSV kaydedildi:\n{dosya}")

    # ================================================================
    # TERMAL SİMÜLASYON MOTORU
    # ================================================================
    def hesapla(self, hafizaya_yaz=True):
        try:
            akis   = self.combo_akis.get()
            eg_adi = self.combo_egzoz.get()
            so_adi = self.combo_sogutucu.get()
            cp_e   = self.egzoz_db[eg_adi]
            cp_s   = self.sogutucu_db[so_adi]
            P_mot  = float(self.ent_motor.get())
            m_e    = float(self.ent_deb_e.get())
            T_ei   = float(self.ent_temp_ei.get())
            m_s    = float(self.ent_deb_s.get())
            T_si   = float(self.ent_temp_si.get())
            U      = float(self.ent_U.get())
            A      = self.slider.get()

            if m_e <= 0 or m_s <= 0 or U <= 0 or A <= 0:
                raise ValueError("Debi, U ve Alan > 0 olmalıdır.")

            if hafizaya_yaz:
                self._gecmise_ekle([akis, eg_adi, so_adi,
                                    P_mot, m_e, T_ei, m_s, T_si, U, A])

            C_e   = m_e * cp_e
            C_s   = m_s * cp_s
            C_min = min(C_e, C_s)
            C_max = max(C_e, C_s)
            C_r   = C_min / C_max
            NTU   = U * A / C_min
            eps   = _ntu_eps(NTU, C_r, akis)

            if abs(T_ei - T_si) < 1e-6:
                raise ValueError("Giriş sıcaklıkları eşit, ısı transferi sıfır.")

            q_max = C_min * (T_ei - T_si)
            q     = eps * q_max
            T_eo  = T_ei - q / C_e
            T_so  = T_si + q / C_s

            # LMTD
            if "Zıt" in akis:
                dt1, dt2 = T_ei - T_so, T_eo - T_si
            else:
                dt1, dt2 = T_ei - T_si, T_eo - T_so
            if dt1 > 0 and dt2 > 0 and abs(dt1 - dt2) > 1e-6:
                LMTD = (dt1 - dt2) / math.log(dt1 / dt2)
            elif dt1 <= 0 or dt2 <= 0:
                LMTD = float("nan")
            else:
                LMTD = (dt1 + dt2) / 2.0

            # ── Sonuç kartlarını güncelle ─────────────────────────────
            self.sr_akis.set(akis)
            self.sr_egzoz.set(eg_adi)
            self.sr_sog.set(so_adi)
            self.sr_motor.set(f"{P_mot:.1f} kW")
            self.sr_A.set(f"{A:.4f} m²")
            self.sr_U.set(f"{U:.1f} W/m²K")
            self.sr_LMTD.set(
                f"{'NaN — negatif ΔT!' if math.isnan(LMTD) else f'{LMTD:.2f} °C'}",
                renk=CLR_RED if math.isnan(LMTD) else CLR_TEXT_PRI)
            self.sr_NTU.set(f"{NTU:.4f}")
            self.sr_Tei.set(f"{T_ei:.1f} °C")
            self.sr_Teo.set(f"{T_eo:.2f} °C")
            self.sr_Tsi.set(f"{T_si:.1f} °C")
            self.sr_Tso.set(f"{T_so:.2f} °C")
            self.sr_q.set(f"{q/1000:.2f} kW")
            eps_renk = CLR_GREEN if eps >= 0.6 else (CLR_AMBER if eps >= 0.4 else CLR_RED)
            self.sr_eps.set(f"% {eps*100:.2f}", renk=eps_renk)

            # ── Durum çubuğu ──────────────────────────────────────────
            if T_eo > 190:
                self.lbl_durum.configure(
                    fg_color="#3a0f0a", text_color=CLR_RED,
                    text="⚠  KRİTİK: Egzoz yeterince soğutulamıyor → Alanı büyütün")
            elif 110 <= T_eo <= 190:
                self.lbl_durum.configure(
                    fg_color="#0f2a1a", text_color=CLR_GREEN,
                    text="✅  İDEAL TASARIM: Optimum emisyon ve soğutma dengesi sağlandı")
            else:
                self.lbl_durum.configure(
                    fg_color="#2a1f0a", text_color=CLR_AMBER,
                    text="⚠  YOĞUŞMA ALARMI: Çıkış çok soğuk — asit/kurum birikimi riski")

            # ── Şema ve grafik ────────────────────────────────────────
            self._sema_ciz(T_ei, T_si, T_eo, T_so, akis)
            self._grafik_ciz(T_ei, T_eo, T_si, T_so, NTU, A, C_r, q_max, C_e, U, C_min, akis)

            # ── Rapor hafızası ────────────────────────────────────────
            self.son_rapor = {
                "akis": akis, "egzoz": eg_adi, "sogutucu": so_adi,
                "P_motor": P_mot, "m_e": m_e, "T_ei": T_ei,
                "m_s": m_s, "T_si": T_si, "U": U, "A": A,
                "T_eo": T_eo, "T_so": T_so, "q_kw": q/1000,
                "eps": eps*100, "LMTD": LMTD, "NTU": NTU,
            }

        except (ValueError, ZeroDivisionError) as e:
            self.lbl_durum.configure(fg_color="#3a0f0a", text_color=CLR_RED,
                                     text=f"⛔  GİRDİ HATASI: {e}")
        except Exception as e:
            self.lbl_durum.configure(fg_color="#3a0f0a", text_color=CLR_RED,
                                     text=f"⛔  BEKLENMEYEN HATA: {e}")

    # ================================================================
    # ŞEMA ÇİZİCİ
    # ================================================================
    def _sema_ciz(self, T_ei, T_si, T_eo, T_so, akis):
        c = self.canvas_sema
        c.delete("all")
        W = c.winfo_width() or 700
        H = c.winfo_height() or 240

        gx1, gx2 = int(W * 0.20), int(W * 0.80)
        gy1, gy2 = int(H * 0.30), int(H * 0.75)
        my = (gy1 + gy2) // 2

        # Arka plan gradyan efekti (dikdörtgenlerle simüle)
        for i in range(10):
            ratio = i / 10
            r = int(0x1c + (0x0d - 0x1c) * ratio)
            g_c = int(0x21 + (0x11 - 0x21) * ratio)
            b = int(0x28 + (0x17 - 0x28) * ratio)
            c.create_rectangle(
                gx1 + (gx2 - gx1) * i // 10, gy1,
                gx1 + (gx2 - gx1) * (i + 1) // 10, gy2,
                fill=f"#{r:02x}{g_c:02x}{b:02x}", outline="")

        # Gövde
        c.create_rectangle(gx1, gy1, gx2, gy2,
                           outline="#58d1eb", width=2)
        # İç boru çizgileri
        for i in range(5):
            y = gy1 + 10 + i * ((gy2 - gy1 - 20) // 5)
            c.create_line(gx1 + 8, y, gx2 - 8, y,
                          fill="#2a3a4a", width=1, dash=(4, 3))
        c.create_text((gx1 + gx2) // 2, my,
                      text="EGR BUNDLE COOLER",
                      fill=CLR_CYAN, font=("Arial", 11, "bold"))

        # Egzoz giriş (sol)
        arr_y = my
        c.create_line(20, arr_y, gx1, arr_y,
                      fill=CLR_EGZOZ, width=5, arrow="last", arrowshape=(12, 14, 5))
        c.create_text(int(W * 0.10), arr_y - 18,
                      text="Egzoz Giriş", fill=CLR_EGZOZ, font=("Arial", 9, "bold"))
        c.create_text(int(W * 0.10), arr_y - 5,
                      text=f"{T_ei:.1f} °C", fill=CLR_EGZOZ, font=("Arial", 10, "bold"))

        # Egzoz çıkış (sağ)
        c.create_line(gx2, arr_y, W - 20, arr_y,
                      fill=CLR_AMBER, width=5, arrow="last", arrowshape=(12, 14, 5))
        c.create_text(int(W * 0.90), arr_y - 18,
                      text="Egzoz Çıkış", fill=CLR_AMBER, font=("Arial", 9, "bold"))
        c.create_text(int(W * 0.90), arr_y - 5,
                      text=f"{T_eo:.1f} °C", fill=CLR_AMBER, font=("Arial", 10, "bold"))

        # Sıvı bağlantıları
        if "Zıt" in akis:
            # Sıvı giriş: sağ üst
            c.create_line(gx2 - 60, H - 20, gx2 - 60, gy2,
                          fill=CLR_SIVI, width=4, arrow="last", arrowshape=(10, 12, 4))
            c.create_text(gx2 - 60, H - 10,
                          text=f"Sıvı Giriş {T_si:.1f}°C",
                          fill=CLR_SIVI, font=("Arial", 9, "bold"))
            # Sıvı çıkış: sol alt
            c.create_line(gx1 + 60, gy1, gx1 + 60, 20,
                          fill=CLR_CYAN, width=4, arrow="last", arrowshape=(10, 12, 4))
            c.create_text(gx1 + 60, 12,
                          text=f"Sıvı Çıkış {T_so:.1f}°C",
                          fill=CLR_CYAN, font=("Arial", 9, "bold"))
            c.create_text((gx1 + gx2) // 2, H - 8,
                          text="⟵  ZIT AKIŞ (COUNTER-FLOW)",
                          fill=CLR_SIVI, font=("Arial", 9))
        else:
            # Sıvı giriş: sol alt
            c.create_line(gx1 + 60, H - 20, gx1 + 60, gy2,
                          fill=CLR_SIVI, width=4, arrow="last", arrowshape=(10, 12, 4))
            c.create_text(gx1 + 60, H - 10,
                          text=f"Sıvı Giriş {T_si:.1f}°C",
                          fill=CLR_SIVI, font=("Arial", 9, "bold"))
            # Sıvı çıkış: sağ üst
            c.create_line(gx2 - 60, gy1, gx2 - 60, 20,
                          fill=CLR_CYAN, width=4, arrow="last", arrowshape=(10, 12, 4))
            c.create_text(gx2 - 60, 12,
                          text=f"Sıvı Çıkış {T_so:.1f}°C",
                          fill=CLR_CYAN, font=("Arial", 9, "bold"))
            c.create_text((gx1 + gx2) // 2, H - 8,
                          text="⟶  PARALEL AKIŞ (CO-CURRENT)",
                          fill=CLR_EGZOZ, font=("Arial", 9))

    # ================================================================
    # ÜÇLÜ GRAFİK ÇİZİCİ
    # ================================================================
    def _grafik_ciz(self, T_ei, T_eo, T_si, T_so,
                    NTU, A, C_r, q_max, C_e, U, C_min, akis):
        c = self.canvas_grafik
        c.delete("all")
        W = c.winfo_width() or 1100
        H = c.winfo_height() or 600
        if W < 200 or H < 200:
            return

        PAD_L, PAD_R = 60, 20
        PAD_T, PAD_B = 50, 40
        GAP = 30
        g_w = (W - PAD_L - PAD_R - 2 * GAP) // 3
        g_h = H - PAD_T - PAD_B
        y_bot = PAD_T + g_h

        def eksen(ox, baslik, xl, yl):
            ex = ox + g_w
            c.create_text(ox + g_w // 2, PAD_T - 28,
                          text=baslik, fill=CLR_TEXT_PRI, font=("Arial", 10, "bold"))
            c.create_line(ox, y_bot, ox, PAD_T, fill=CLR_BORDER, width=1)
            c.create_line(ox, y_bot, ex, y_bot, fill=CLR_BORDER, width=1)
            # Izgara yatay
            for k in range(1, 5):
                yg = PAD_T + g_h * k // 4
                c.create_line(ox, yg, ex, yg, fill=CLR_BG_CARD, width=1)
            c.create_text(ox - 8, y_bot + 14, text=xl,
                          fill=CLR_TEXT_MUT, font=("Arial", 8), anchor="e")
            c.create_text(ox - 8, PAD_T, text=yl,
                          fill=CLR_TEXT_MUT, font=("Arial", 8), anchor="e")
            return ex

        # ── Grafik 1: Sıcaklık profili ────────────────────────────────
        ox1 = PAD_L
        ex1 = eksen(ox1, "Sıcaklık Profili", "Konum →", "°C")

        all_t = [T_ei, T_eo, T_si, T_so]
        t_min = min(all_t) - 20
        t_max = max(all_t) + 30
        t_sp  = t_max - t_min or 1

        def ty(t):
            return y_bot - (t - t_min) / t_sp * g_h

        # Egzoz çizgisi
        c.create_line(ox1, ty(T_ei), ex1, ty(T_eo),
                      fill=CLR_EGZOZ, width=3)
        # Sıvı çizgisi
        if "Zıt" in akis:
            c.create_line(ox1, ty(T_so), ex1, ty(T_si),
                          fill=CLR_SIVI, width=3)
        else:
            c.create_line(ox1, ty(T_si), ex1, ty(T_so),
                          fill=CLR_SIVI, width=3)

        for val, x_pos, renk, anchor in [
            (T_ei, ox1, CLR_EGZOZ, "e"), (T_eo, ex1, CLR_AMBER, "w"),
            (T_si if "Paralel" in akis else T_so, ox1, CLR_SIVI, "e"),
            (T_so if "Paralel" in akis else T_si, ex1, CLR_CYAN, "w"),
        ]:
            c.create_text(x_pos + (-6 if anchor == "e" else 6),
                          ty(val), text=f"{val:.0f}°", fill=renk,
                          font=("Arial", 9, "bold"), anchor=anchor)

        c.create_text(ox1 + 8, PAD_T + 12,
                      text="— Egzoz", fill=CLR_EGZOZ, font=("Arial", 8), anchor="w")
        c.create_text(ox1 + 8, PAD_T + 24,
                      text="— Sıvı", fill=CLR_SIVI, font=("Arial", 8), anchor="w")

        # ── Grafik 2: NTU analizi ─────────────────────────────────────
        ox2 = ex1 + GAP
        ex2 = eksen(ox2, "NTU — Egzoz Çıkış Sıcaklığı", "NTU →", "T_eo [°C]")
        ntu_max = max(NTU * 2, 4.0)

        pts = []
        for i in range(40):
            nt = ntu_max * i / 39
            ep = _ntu_eps(nt, C_r, akis)
            te = T_ei - (ep * q_max / C_e)
            px = ox2 + (nt / ntu_max) * g_w
            py = y_bot - (te - t_min) / t_sp * g_h
            pts.append((px, py))
        for i in range(len(pts) - 1):
            c.create_line(pts[i][0], pts[i][1],
                          pts[i+1][0], pts[i+1][1],
                          fill=CLR_GREEN, width=2)

        # Mevcut NTU işareti
        cur_x = ox2 + (min(NTU, ntu_max) / ntu_max) * g_w
        c.create_line(cur_x, y_bot, cur_x, PAD_T,
                      fill=CLR_AMBER, dash=(5, 4), width=1)
        c.create_text(cur_x, PAD_T - 8,
                      text=f"NTU={NTU:.2f}", fill=CLR_AMBER, font=("Arial", 8, "bold"))

        # ── Grafik 3: Alan etkisi ─────────────────────────────────────
        ox3 = ex2 + GAP
        ex3 = eksen(ox3, "Yüzey Alanı — Isı Gücü", "A [m²] →", "q [kW]")
        a_max = max(A * 2.5, 3.0)
        q_lim = max(q_max / 1000 * 1.2, 1.0)

        pts2 = []
        for i in range(40):
            at  = a_max * i / 39
            nt  = U * at / C_min if C_min > 0 else 0
            ep  = _ntu_eps(nt, C_r, akis)
            qk  = ep * q_max / 1000
            px  = ox3 + (at / a_max) * g_w
            py  = y_bot - (qk / q_lim) * g_h
            pts2.append((px, py))
        for i in range(len(pts2) - 1):
            c.create_line(pts2[i][0], pts2[i][1],
                          pts2[i+1][0], pts2[i+1][1],
                          fill=CLR_PURPLE, width=2)

        cur_ax = ox3 + (A / a_max) * g_w
        c.create_line(cur_ax, y_bot, cur_ax, PAD_T,
                      fill=CLR_CYAN, dash=(5, 4), width=1)
        c.create_text(cur_ax, PAD_T - 8,
                      text=f"A={A:.2f}m²", fill=CLR_CYAN, font=("Arial", 8, "bold"))

        # Y ekseni etiketleri grafik 3
        for k in range(5):
            yg  = PAD_T + g_h * k // 4
            qv  = q_lim * (1 - k / 4)
            c.create_text(ox3 - 4, yg, text=f"{qv:.1f}",
                          fill=CLR_TEXT_MUT, font=("Arial", 7), anchor="e")

    # ================================================================
    # GEÇMİŞ SİSTEMİ
    # ================================================================
    def _gecmise_ekle(self, veri):
        if self.gec_idx == -1 or self.gecmis[self.gec_idx] != veri:
            self.gecmis = self.gecmis[:self.gec_idx + 1]
            self.gecmis.append(veri)
            self.gec_idx = len(self.gecmis) - 1
            self._btn_guncelle()

    def _btn_guncelle(self):
        self.btn_geri.configure(state="normal" if self.gec_idx > 0 else "disabled")
        self.btn_ileri.configure(state="normal" if self.gec_idx < len(self.gecmis) - 1 else "disabled")

    def _yukle(self, idx):
        v = self.gecmis[idx]
        self.combo_akis.set(v[0]); self.combo_egzoz.set(v[1]); self.combo_sogutucu.set(v[2])
        for ent, val in zip(
            [self.ent_motor, self.ent_deb_e, self.ent_temp_ei,
             self.ent_deb_s, self.ent_temp_si, self.ent_U],
            v[3:9],
        ):
            ent.delete(0, "end"); ent.insert(0, str(val))
        self.slider.set(v[9])
        self.lbl_slider.configure(text=f"Alan: {v[9]:.2f} m²")
        self.hesapla(hafizaya_yaz=False)

    def _geri(self):
        if self.gec_idx > 0:
            self.gec_idx -= 1
            self._yukle(self.gec_idx)
            self._btn_guncelle()

    def _ileri(self):
        if self.gec_idx < len(self.gecmis) - 1:
            self.gec_idx += 1
            self._yukle(self.gec_idx)
            self._btn_guncelle()

    # ================================================================
    # RAPORLAMA
    # ================================================================
    def _rapor_kaydet(self):
        if not self.son_rapor:
            messagebox.showwarning("Uyarı", "Önce bir simülasyon çalıştırın.")
            return
        dosya = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Metin Dosyası", "*.txt")],
            title="Raporu Kaydet")
        if not dosya: return
        r = self.son_rapor
        lmtd_str = "NaN (negatif ΔT)" if math.isnan(r["LMTD"]) else f"{r['LMTD']:.2f} °C"
        metni = (
            "=" * 70 + "\n"
            "       EGR COOLER TERMAL MÜHENDİSLİK VE AR-GE ANALİZ RAPORU\n"
            "=" * 70 + "\n"
            f" Geliştiren : Enes Çelik Simülasyon Sistemleri  |  v5.0\n"
            + "-" * 70 + "\n\n"
            " [1] SİSTEM VE AKIŞKAN ÖZELLİKLERİ\n"
            + "-" * 70 + "\n"
            f" Akış Tipi              : {r['akis']}\n"
            f" Egzoz Gazı             : {r['egzoz']}\n"
            f" Soğutucu Akışkan       : {r['sogutucu']}\n"
            f" Motor Gücü             : {r['P_motor']:.1f} kW\n\n"
            " [2] GEOMETRİK VE TERMAL GEÇİŞ VERİLERİ\n"
            + "-" * 70 + "\n"
            f" Transfer Alanı A       : {r['A']:.4f} m²\n"
            f" U Katsayısı            : {r['U']:.1f} W/m²K\n"
            f" LMTD                   : {lmtd_str}\n"
            f" NTU                    : {r['NTU']:.4f}\n\n"
            " [3] ENERJİ BİLANÇOSU VE SİMÜLASYON ÇIKTILARI\n"
            + "-" * 70 + "\n"
            f" Egzoz Giriş Sıcaklığı  : {r['T_ei']:.1f} °C\n"
            f" Egzoz Çıkış Sıcaklığı  : {r['T_eo']:.2f} °C\n"
            f" Sıvı Giriş Sıcaklığı   : {r['T_si']:.1f} °C\n"
            f" Sıvı Çıkış Sıcaklığı   : {r['T_so']:.2f} °C\n"
            f" Geri Kazanılan Isı     : {r['q_kw']:.2f} kW\n"
            f" Termal Etkinlik ε      : % {r['eps']:.2f}\n"
            "=" * 70 + "\n"
            "                   RAPOR SONU — GÜVENLİ ÇIKTI\n"
            "=" * 70 + "\n"
        )
        with open(dosya, "w", encoding="utf-8") as f:
            f.write(metni)
        messagebox.showinfo("Başarılı", f"Rapor kaydedildi:\n{dosya}")

    def _csv_aktar(self):
        if not self.son_rapor:
            messagebox.showwarning("Uyarı", "Önce bir simülasyon çalıştırın.")
            return
        dosya = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            title="CSV Olarak Kaydet")
        if not dosya: return
        r = self.son_rapor
        with open(dosya, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Parametre", "Değer", "Birim"])
            w.writerows([
                ["Akış Tipi", r["akis"], ""],
                ["Egzoz Gazı", r["egzoz"], ""],
                ["Soğutucu", r["sogutucu"], ""],
                ["Motor Gücü", r["P_motor"], "kW"],
                ["Transfer Alanı A", r["A"], "m²"],
                ["U Katsayısı", r["U"], "W/m²K"],
                ["NTU", r["NTU"], ""],
                ["LMTD", "" if math.isnan(r["LMTD"]) else r["LMTD"], "°C"],
                ["Egzoz Giriş T", r["T_ei"], "°C"],
                ["Egzoz Çıkış T", r["T_eo"], "°C"],
                ["Sıvı Giriş T", r["T_si"], "°C"],
                ["Sıvı Çıkış T", r["T_so"], "°C"],
                ["Isı Gücü q", r["q_kw"], "kW"],
                ["Etkinlik ε", r["eps"], "%"],
            ])
        messagebox.showinfo("Başarılı", f"CSV kaydedildi:\n{dosya}")


# ────────────────────────────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR (modül seviyesi — sınıftan bağımsız)
# ────────────────────────────────────────────────────────────────────
def _ntu_eps(NTU: float, C_r: float, akis: str) -> float:
    """
    NTU-Etkinlik (ε) dönüşümü.
    Düzeltilmiş: Paralel akış C_r=1 koşulu ayrı hesaplanır.
    """
    eps = 0.0
    if "Zıt" in akis:
        if abs(C_r - 1.0) < 1e-9:
            eps = NTU / (1.0 + NTU)
        else:
            num = 1.0 - math.exp(-NTU * (1.0 - C_r))
            den = 1.0 - C_r * math.exp(-NTU * (1.0 - C_r))
            eps = num / den
    else:  # Paralel akış
        if abs(C_r - 1.0) < 1e-9:
            eps = (1.0 - math.exp(-2.0 * NTU)) / 2.0   # ← düzeltildi
        else:
            eps = (1.0 - math.exp(-NTU * (1.0 + C_r))) / (1.0 + C_r)
    return min(max(eps, 0.0), 1.0)


def _olustur_uyarilar(Re, v, dP, h_ic, U, T_eo, eps):
    """
    (ikon, mesaj, renk) üçlüleri listesi döndürür.
    """
    items = []
    if Re < 2300:
        items.append(("⚠", f"LAMİNER AKIŞ (Re={Re:.0f}): Isı transferi zayıf. "
                           f"Kanal kesitini küçültün veya debiyi artırın. "
                           f"Türbülanslı rejim için Re > 4000 hedefleyin.", CLR_AMBER))
    elif Re < 4000:
        items.append(("⚠", f"GEÇİŞ BÖLGESİ (Re={Re:.0f}): Akış kararsız. "
                           "Tasarımı Re > 4000 veya Re < 2300 olacak şekilde optimize edin.", CLR_AMBER))
    else:
        items.append(("✅", f"TÜRBÜLANSLÜ AKIŞ (Re={Re:.0f}): İdeal ısı transferi rejimi.", CLR_GREEN))

    if v > 30:
        items.append(("⚠", f"YÜKSEK HIZ: v = {v:.1f} m/s → Erozyon ve titreşim riski. "
                           "Kanal kesit alanını büyütün.", CLR_RED))
    if dP > 5000:
        items.append(("⚠", f"YÜKSEK BASINÇ DÜŞÜMÜ: ΔP = {dP:.0f} Pa → "
                           "EGR geri basıncını artırır, motor verimliliğini düşürebilir.", CLR_AMBER))
    if h_ic < U * 0.5:
        items.append(("⚠", f"h_iç ({h_ic:.0f} W/m²K) << U ({U:.0f} W/m²K): "
                           "İç taraf ısıl direnç baskın. U değerini veya kanal geometrisini gözden geçirin.", CLR_RED))
    if T_eo < 90:
        items.append(("⚠", "YOĞUŞMA RİSKİ: Egzoz çıkış < 90 °C → "
                           "Asit yoğuşması ve boru korozyonu oluşabilir.", CLR_RED))
    if eps < 0.5:
        items.append(("⚠", f"DÜŞÜK ETKİNLİK: ε = {eps*100:.1f} % → "
                           "Alan artırılmalı veya akış tipi Zıt Akış olarak değiştirilmeli.", CLR_AMBER))
    if not items:
        items.append(("✅", "Tüm parametreler kabul edilebilir aralıkta.", CLR_GREEN))
    return items


# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = EGRLab()
    app.mainloop()
