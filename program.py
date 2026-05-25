"""
EGR Cooler Ar-Ge ve Termal Analiz Laboratuvarı  v6.0
Geliştiren: Enes Çelik Simülasyon Sistemleri

v6.0 Değişiklikleri:
  - Yeni sekme: Motor Çevrimi & Egzoz Sıcaklığı Tahmini
    (Pulkrabek "Engineering Fundamentals of ICE" formülleri)
    Otto / Diesel / Dual çevrim analizi
    P-v diyagramı canvas üzerinde
    T_ex → ana simülasyona otomatik aktarım
  - Motor Gücü input'u ana simülasyondan kaldırıldı
  - Yakıt tipi ana simülasyondan kaldırıldı, yeni sekmede
  - Şematik: silindirik gövde + sıcaklık gradyanı
  - Sıcaklık profili grafiği: eğri profil, etiketler, oklar
  - Diğer grafikler: tam eksenler, tick marks, değerler
  - CSV yerine düzgün formatlanmış TXT raporu
"""

import customtkinter as ctk
import math
from tkinter import filedialog, messagebox

# ────────────────────────────────────────────────────────────────────
# TEMA
# ────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CLR_BG_DEEP   = "#0d1117"
CLR_BG_PANEL  = "#161b22"
CLR_BG_CARD   = "#1c2128"
CLR_BG_INPUT  = "#21262d"
CLR_BORDER    = "#30363d"
CLR_CYAN      = "#58d1eb"
CLR_AMBER     = "#f0a500"
CLR_GREEN     = "#3fb950"
CLR_RED       = "#f85149"
CLR_PURPLE    = "#bc8cff"
CLR_TEXT_PRI  = "#e6edf3"
CLR_TEXT_SEC  = "#8b949e"
CLR_TEXT_MUT  = "#484f58"
CLR_EGZOZ     = "#e05c4b"
CLR_SIVI      = "#4d9de0"


# ────────────────────────────────────────────────────────────────────
# YARDIMCI BİLEŞENLER
# ────────────────────────────────────────────────────────────────────
class KartFrame(ctk.CTkFrame):
    def __init__(self, parent, baslik="", renk=CLR_CYAN, **kwargs):
        super().__init__(parent, fg_color=CLR_BG_CARD,
                         border_color=CLR_BORDER, border_width=1,
                         corner_radius=10, **kwargs)
        if baslik:
            header = ctk.CTkFrame(self, fg_color=renk, corner_radius=0, height=32)
            header.pack(fill="x")
            header.pack_propagate(False)
            ctk.CTkLabel(header, text=baslik, font=("Arial", 11, "bold"),
                         text_color="#0d1117").pack(side="left", padx=12)


class SonucSatir(ctk.CTkFrame):
    def __init__(self, parent, etiket, deger="—", deger_renk=CLR_TEXT_PRI, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        ctk.CTkLabel(self, text=etiket, font=("Arial", 11),
                     text_color=CLR_TEXT_SEC, anchor="w", width=230
                     ).pack(side="left", padx=(12, 4))
        self.lbl = ctk.CTkLabel(self, text=deger, font=("Arial", 11, "bold"),
                                text_color=deger_renk, anchor="e")
        self.lbl.pack(side="right", padx=(4, 12))

    def set(self, deger, renk=None):
        self.lbl.configure(text=deger)
        if renk:
            self.lbl.configure(text_color=renk)


class AyiriciCizgi(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, height=1, fg_color=CLR_BORDER, **kwargs)
        self.pack(fill="x", padx=12, pady=4)


# ────────────────────────────────────────────────────────────────────
# ANA UYGULAMA
# ────────────────────────────────────────────────────────────────────
class EGRLab(ctk.CTk):

    DEBOUNCE_MS = 400

    def __init__(self):
        super().__init__()
        self.title("EGR Cooler Ar-Ge ve Termal Analiz Laboratuvarı  v6.0")
        self.geometry("1400x940")
        self.minsize(1100, 750)
        self.configure(fg_color=CLR_BG_DEEP)

        # Akışkan veri tabanları
        self.sogutucu_db = {
            "Saf Su":                           4184,
            "%50 Etilen Glikol (Antifriz)":     3300,
            "%30 Propilen Glikol":              3700,
        }
        self.malzeme_db = {
            "Paslanmaz Çelik 316L  (k=16 W/mK)":      16.0,
            "Alüminyum Alaşımı 6061  (k=167 W/mK)":  167.0,
            "Bakır  (k=385 W/mK)":                    385.0,
            "Titanyum Ti-6Al-4V  (k=7 W/mK)":          7.0,
            "Dökme Demir  (k=50 W/mK)":                50.0,
            "Nikel Alaşımı Inconel 625  (k=10 W/mK)": 10.0,
            "Manuel Giriş":                            None,
        }

        # Durum
        self.gecmis       = []
        self.gec_idx      = -1
        self.son_rapor    = {}
        self._debounce_id = None

        # Motor çevrimi sonuçları (yeni sekmeden gelir)
        self.motor_sonuc  = {}

        # İmza
        ctk.CTkLabel(
            self,
            text="Bu program Enes Çelik tarafından geliştirilmiştir  •  EGR Lab v6.0",
            font=("Arial", 11, "italic"), text_color=CLR_TEXT_MUT,
        ).pack(side="top", pady=(6, 0))

        # Sekmeler
        self.tabview = ctk.CTkTabview(
            self, fg_color=CLR_BG_PANEL,
            segmented_button_fg_color=CLR_BG_CARD,
            segmented_button_selected_color=CLR_CYAN,
            segmented_button_selected_hover_color="#3bbbd4",
            segmented_button_unselected_color=CLR_BG_CARD,
            segmented_button_unselected_hover_color=CLR_BG_INPUT,
            text_color=CLR_TEXT_PRI,
        )
        self.tabview.pack(padx=12, pady=(4, 10), fill="both", expand=True)

        self.tab_motor    = self.tabview.add("🔥  Motor Çevrimi & Egzoz T°")
        self.tab_ana      = self.tabview.add("⚙   Termal Simülasyon")
        self.tab_sihirbaz = self.tabview.add("📐  Geometri & U Hesaplama")
        self.tab_reynolds = self.tabview.add("🌊  Reynolds & Akış Analizi")
        self.tab_grafik   = self.tabview.add("📊  Grafik Paneli")
        self.tab_tarama   = self.tabview.add("🔁  Parametrik Tarama")

        self._build_motor()
        self._build_ana()
        self._build_sihirbaz()
        self._build_reynolds()
        self._build_grafik()
        self._build_tarama()

        self.update()
        self.hesapla(hafizaya_yaz=True)

    # ================================================================
    # YARDIMCI: Entry + debounce
    # ================================================================
    def _entry(self, parent, label, default, row_pad=(3, 0)):
        fr = ctk.CTkFrame(parent, fg_color="transparent")
        fr.pack(pady=row_pad, fill="x", padx=14)
        ctk.CTkLabel(fr, text=label, font=("Arial", 11),
                     text_color=CLR_TEXT_SEC, anchor="w", width=235).pack(side="left")
        var = ctk.StringVar(value=str(default))
        ent = ctk.CTkEntry(fr, width=105, textvariable=var,
                           fg_color=CLR_BG_INPUT, border_color=CLR_BORDER,
                           text_color=CLR_TEXT_PRI)
        ent.pack(side="right")
        var.trace_add("write", self._debounce_hesapla)
        return ent

    def _debounce_hesapla(self, *_):
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(self.DEBOUNCE_MS, self.hesapla)

    def _section_label(self, parent, text):
        ctk.CTkLabel(parent, text=text.upper(), font=("Arial", 9, "bold"),
                     text_color=CLR_TEXT_MUT).pack(pady=(10, 2), padx=14, anchor="w")

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

    # ================================================================
    # SEKME 1 — MOTOR ÇEVRİMİ & EGZOZ SICAKLIĞI (YENİ)
    # Pulkrabek ICE kitabı formülleri (Bölüm 3)
    # ================================================================
    def _build_motor(self):
        ana = ctk.CTkFrame(self.tab_motor, fg_color=CLR_BG_PANEL)
        ana.pack(fill="both", expand=True, padx=6, pady=6)
        ana.columnconfigure(0, weight=1)
        ana.columnconfigure(1, weight=2)
        ana.rowconfigure(0, weight=1)

        # ── Sol: Giriş Paneli ─────────────────────────────────────────
        sol_scroll = ctk.CTkScrollableFrame(
            ana, width=420, fg_color=CLR_BG_PANEL,
            scrollbar_button_color=CLR_BORDER)
        sol_scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        ctk.CTkLabel(sol_scroll, text="MOTOR ÇEVRİM ANALİZİ",
                     font=("Arial", 13, "bold"), text_color=CLR_AMBER,
                     ).pack(pady=(12, 2), padx=14, anchor="w")
        ctk.CTkLabel(sol_scroll,
                     text="Pulkrabek ICE Kitabı — Bölüm 3 Formülleri",
                     font=("Arial", 10, "italic"), text_color=CLR_TEXT_MUT,
                     ).pack(pady=(0, 8), padx=14, anchor="w")

        # Çevrim seçimi
        self._section_label(sol_scroll, "Motor Çevrim Tipi")
        self.combo_cevrim = ctk.CTkOptionMenu(
            sol_scroll,
            values=["Otto Çevrimi (Benzin / SI)",
                    "Diesel Çevrimi (Dizel / CI)",
                    "Dual Çevrimi (Modern CI)"],
            fg_color=CLR_BG_INPUT, button_color=CLR_AMBER,
            button_hover_color="#c8890a", text_color=CLR_TEXT_PRI,
            dropdown_fg_color=CLR_BG_CARD, dropdown_text_color=CLR_TEXT_PRI,
            command=self._cevrim_degisti,
        )
        self.combo_cevrim.pack(pady=(2, 4), padx=14, fill="x")

        # Yakıt tipi (ana simülasyona aktarılır)
        self._section_label(sol_scroll, "Yakıt / Egzoz Gazı Tipi")
        self.combo_yakit = ctk.CTkOptionMenu(
            sol_scroll,
            values=["Benzin (İsooctan, QHV=44300 kJ/kg)",
                    "Dizel Yakıtı (QHV=42500 kJ/kg)",
                    "LPG (QHV=46000 kJ/kg)",
                    "Hidrojen (QHV=120000 kJ/kg)",
                    "Manuel QHV Girişi"],
            fg_color=CLR_BG_INPUT, button_color=CLR_AMBER,
            button_hover_color="#c8890a", text_color=CLR_TEXT_PRI,
            dropdown_fg_color=CLR_BG_CARD, dropdown_text_color=CLR_TEXT_PRI,
            command=self._yakit_degisti,
        )
        self.combo_yakit.pack(pady=(2, 4), padx=14, fill="x")

        # Manuel QHV (gizli)
        self.frm_qhv_manuel = ctk.CTkFrame(sol_scroll, fg_color="transparent")
        self.ent_qhv_manuel = self._motor_entry(
            self.frm_qhv_manuel, "Yakıt Isıl Değeri Q_HV [kJ/kg]:", "44300")
        self.frm_qhv_manuel.pack_forget()

        # Ortak girdiler
        self._section_label(sol_scroll, "Motor Geometrisi & Çalışma Koşulları")
        self.ent_m_T1   = self._motor_entry(sol_scroll, "Sıkıştırma Başı Sıcaklığı T₁ [°C]:", "60")
        self.ent_m_P1   = self._motor_entry(sol_scroll, "Sıkıştırma Başı Basıncı P₁ [kPa]:", "100")
        self.ent_m_rc   = self._motor_entry(sol_scroll, "Sıkıştırma Oranı rᶜ [-]:", "9")
        self.ent_m_AF   = self._motor_entry(sol_scroll, "Hava-Yakıt Oranı AF [-]:", "15")
        self.ent_m_xr   = self._motor_entry(sol_scroll, "Egzoz Artığı x_r (örn. 0.04):", "0.04")
        self.ent_m_eta_c = self._motor_entry(sol_scroll, "Yanma Verimi η_c (0-1):", "0.98")
        self.ent_m_eta_m = self._motor_entry(sol_scroll, "Mekanik Verim η_m (0-1):", "0.86")
        self.ent_m_Vd   = self._motor_entry(sol_scroll, "Silindir Hacmi V_d [cm³]:", "625")
        self.ent_m_N_sil = self._motor_entry(sol_scroll, "Silindir Sayısı N_sil:", "4")
        self.ent_m_RPM  = self._motor_entry(sol_scroll, "Motor Devri N [RPM]:", "3000")
        self.ent_m_Pex  = self._motor_entry(sol_scroll, "Egzoz Manifold Basıncı P_ex [kPa]:", "100")

        # Dual/Diesel'e özel girdiler
        self.frm_dual = ctk.CTkFrame(sol_scroll, fg_color="transparent")
        self._section_label(self.frm_dual, "Dual Çevrim Parametreleri")
        self.ent_m_alfa  = self._motor_entry(self.frm_dual, "Basınç Oranı α = P₃/P₂ [-]:", "1.5")
        self.ent_m_beta  = self._motor_entry(self.frm_dual, "Kesme Oranı β = V₃/Vₓ [-]:", "1.5")
        self.frm_dual.pack_forget()

        self.frm_diesel = ctk.CTkFrame(sol_scroll, fg_color="transparent")
        self._section_label(self.frm_diesel, "Diesel Çevrim Parametresi")
        self.ent_m_beta_d = self._motor_entry(
            self.frm_diesel, "Kesme Oranı β = V₃/V₂ [-]:", "2.0")
        self.frm_diesel.pack_forget()

        # Buton
        ctk.CTkButton(
            sol_scroll, text="🔥   ÇEVRİMİ HESAPLA & SİMÜLASYONA AKTAR",
            font=("Arial", 13, "bold"), height=44,
            fg_color=CLR_AMBER, hover_color="#c8890a",
            text_color="#0d1117", command=self._motor_hesapla,
        ).pack(pady=(12, 4), padx=14, fill="x")

        ctk.CTkButton(
            sol_scroll, text="💾  RAPOR KAYDET (.txt)",
            font=("Arial", 12), height=36,
            fg_color="#1c2a1a", hover_color="#243522",
            text_color=CLR_GREEN, border_color=CLR_GREEN, border_width=1,
            command=self._motor_rapor_kaydet,
        ).pack(pady=(0, 12), padx=14, fill="x")

        # ── Sağ: Sonuç + P-v Grafik ──────────────────────────────────
        sag = ctk.CTkFrame(ana, fg_color=CLR_BG_PANEL)
        sag.grid(row=0, column=1, sticky="nsew")
        sag.rowconfigure(0, weight=1)
        sag.rowconfigure(1, weight=2)
        sag.columnconfigure(0, weight=1)

        # Sonuç kartları
        sonuc_scroll = ctk.CTkScrollableFrame(
            sag, fg_color=CLR_BG_PANEL,
            scrollbar_button_color=CLR_BORDER)
        sonuc_scroll.grid(row=0, column=0, sticky="nsew", padx=6, pady=(6, 4))

        # Durum çubuğu
        self.lbl_motor_durum = ctk.CTkLabel(
            sonuc_scroll, text="● Hesap Bekleniyor",
            font=("Arial", 12, "bold"), fg_color=CLR_BG_CARD,
            text_color=CLR_TEXT_SEC, height=38, corner_radius=6)
        self.lbl_motor_durum.pack(fill="x", padx=4, pady=(0, 6))

        # İki sütun sonuç
        kolon = ctk.CTkFrame(sonuc_scroll, fg_color="transparent")
        kolon.pack(fill="x")
        kolon.columnconfigure(0, weight=1)
        kolon.columnconfigure(1, weight=1)

        # Durum noktaları kartı
        kart_state = KartFrame(kolon, "📌   DURUM NOKTASI SICAKLIKLARI & BASINÇLARI", CLR_AMBER)
        kart_state.grid(row=0, column=0, sticky="nsew", padx=(0, 3), pady=2)
        state_keys = [
            ("T1",  "T₁  (sıkıştırma başı)",  CLR_SIVI),
            ("T2",  "T₂  (sıkıştırma sonu)",  CLR_TEXT_PRI),
            ("T3",  "T₃  (yanma sonu / T_max)", CLR_EGZOZ),
            ("T4",  "T₄  (genleşme sonu)",     CLR_AMBER),
            ("Tex", "T_ex  (egzoz / EGR giriş)", CLR_RED),
            ("P1",  "P₁  [kPa]",               CLR_TEXT_SEC),
            ("P2",  "P₂  [kPa]",               CLR_TEXT_SEC),
            ("P3",  "P₃  [kPa]",               CLR_EGZOZ),
            ("P4",  "P₄  [kPa]",               CLR_TEXT_SEC),
        ]
        self.m_state = {}
        for i, (k, lbl, renk) in enumerate(state_keys):
            s = SonucSatir(kart_state, lbl, deger_renk=renk)
            s.pack(fill="x", pady=(6 if i == 0 else 2, 0))
            self.m_state[k] = s
        ctk.CTkFrame(kart_state, height=6, fg_color="transparent").pack()

        # Performans kartı
        kart_perf = KartFrame(kolon, "⚡   MOTOR PERFORMANS SONUÇLARI", CLR_GREEN)
        kart_perf.grid(row=0, column=1, sticky="nsew", padx=(3, 0), pady=2)
        perf_keys = [
            ("eta_t",   "Termal Verim η_t",        CLR_GREEN),
            ("eta_act", "Gerçek Verim (0.85×η_t)", CLR_GREEN),
            ("W_net",   "Net İş W_net [kJ/cyl]",   CLR_CYAN),
            ("Q_in",    "Isı Girdisi Q_in [kJ/cyl]", CLR_AMBER),
            ("imep",    "İMEP [kPa]",               CLR_PURPLE),
            ("P_i",     "Gösterilen Güç [kW]",      CLR_CYAN),
            ("P_b",     "Fren (Brake) Gücü [kW]",   CLR_GREEN),
            ("torque",  "Tork [N·m]",               CLR_TEXT_PRI),
            ("xr_calc", "Egzoz Artığı x_r",         CLR_TEXT_SEC),
            ("T1_mix",  "T₁ Karışım (mix) [°C]",    CLR_SIVI),
        ]
        self.m_perf = {}
        for i, (k, lbl, renk) in enumerate(perf_keys):
            s = SonucSatir(kart_perf, lbl, deger_renk=renk)
            s.pack(fill="x", pady=(6 if i == 0 else 2, 0))
            self.m_perf[k] = s
        ctk.CTkFrame(kart_perf, height=6, fg_color="transparent").pack()

        # P-v diyagramı
        self.canvas_pv = ctk.CTkCanvas(
            sag, bg=CLR_BG_DEEP, highlightthickness=0)
        self.canvas_pv.grid(row=1, column=0, sticky="nsew", padx=6, pady=(4, 6))

    def _motor_entry(self, parent, label, default):
        fr = ctk.CTkFrame(parent, fg_color="transparent")
        fr.pack(pady=3, fill="x", padx=14)
        ctk.CTkLabel(fr, text=label, font=("Arial", 11),
                     text_color=CLR_TEXT_SEC, anchor="w", width=300).pack(side="left")
        ent = ctk.CTkEntry(fr, width=100, fg_color=CLR_BG_INPUT,
                           border_color=CLR_BORDER, text_color=CLR_TEXT_PRI)
        ent.insert(0, default)
        ent.pack(side="right")
        return ent

    def _cevrim_degisti(self, secim):
        self.frm_dual.pack_forget()
        self.frm_diesel.pack_forget()
        if "Dual" in secim:
            self.frm_dual.pack(fill="x")
        elif "Diesel" in secim:
            self.frm_diesel.pack(fill="x")

    def _yakit_degisti(self, secim):
        if "Manuel" in secim:
            self.frm_qhv_manuel.pack(fill="x")
        else:
            self.frm_qhv_manuel.pack_forget()

    def _get_qhv(self):
        yakit = self.combo_yakit.get()
        if "Benzin" in yakit:   return 44300.0
        if "Dizel"  in yakit:   return 42500.0
        if "LPG"    in yakit:   return 46000.0
        if "Hidrojen" in yakit: return 120000.0
        return float(self.ent_qhv_manuel.get())

    def _get_egzoz_cp(self):
        """Ana simülasyon için cp tahmini (yakıta göre)"""
        yakit = self.combo_yakit.get()
        if "Benzin" in yakit:   return 1150
        if "Dizel"  in yakit:   return 1100
        if "LPG"    in yakit:   return 1180
        if "Hidrojen" in yakit: return 1420
        return 1150

    # ================================================================
    # MOTOR HESAPLAMA — Pulkrabek Bölüm 3
    # ================================================================
    def _motor_hesapla(self):
        try:
            cevrim = self.combo_cevrim.get()
            T1_C  = float(self.ent_m_T1.get())
            P1    = float(self.ent_m_P1.get())      # kPa
            rc    = float(self.ent_m_rc.get())
            AF    = float(self.ent_m_AF.get())
            xr    = float(self.ent_m_xr.get())
            eta_c = float(self.ent_m_eta_c.get())
            eta_m = float(self.ent_m_eta_m.get())
            Vd_cm3 = float(self.ent_m_Vd.get())     # cm³ / silindir
            N_sil  = int(float(self.ent_m_N_sil.get()))
            RPM    = float(self.ent_m_RPM.get())
            Pex    = float(self.ent_m_Pex.get())     # kPa
            QHV    = self._get_qhv()                 # kJ/kg

            if rc <= 1:    raise ValueError("Sıkıştırma oranı > 1 olmalı.")
            if AF  <= 0:   raise ValueError("AF > 0 olmalı.")
            if eta_c <= 0 or eta_c > 1: raise ValueError("η_c 0-1 arasında olmalı.")

            # Hava özellikleri — Pulkrabek Bölüm 3, k=1.35 egzoz/yanma bölgesi için
            k   = 1.35
            cv  = 0.821   # kJ/kg·K
            cp  = 1.108   # kJ/kg·K
            R   = 0.287   # kJ/kg·K

            T1  = T1_C + 273.15   # K

            # Silindir hacimleri
            Vd  = Vd_cm3 * 1e-6   # m³
            Vc  = Vd / (rc - 1)   # temizleme hacmi
            V1  = Vd + Vc         # BDC
            V2  = Vc              # TDC

            # Gaz kütlesi — State 1
            mm  = P1 * V1 / (R * T1)      # kg
            mf  = mm * (1 - xr) / (AF + 1)  # yakıt kütlesi
            ma  = mf * AF                  # hava kütlesi

            # ── State 2: izentropic sıkıştırma ──────────────────────
            T2  = T1 * (rc ** (k - 1))    # Eq. 3-4
            P2  = P1 * (rc ** k)          # Eq. 3-5

            Q_in = mf * QHV * eta_c       # kJ — toplam ısı girdisi

            # ── Çevrime göre yanma ───────────────────────────────────
            if "Otto" in cevrim:
                # Sabit hacimde yanma 2→3
                # Q_in = mm * cv * (T3 - T2)  → Eq. 3-10
                T3 = T2 + Q_in / (mm * cv)
                P3 = P2 * (T3 / T2)
                V3 = V2

                # State 4: izentropic genleşme 3→4
                T4 = T3 * ((1 / rc) ** (k - 1))   # Eq. 3-16
                P4 = P3 * ((1 / rc) ** k)          # Eq. 3-17

                # Termal verim — Eq. 3-31
                eta_t = 1.0 - (1.0 / (rc ** (k - 1)))

                # Net iş
                W_comp = mm * R * (T2 - T1) / (1 - k)   # W1-2
                W_exp  = mm * R * (T4 - T3) / (1 - k)   # W3-4
                W_net  = W_exp + W_comp

                # Çevrim noktaları P-v için (özel hacimler)
                pv_pts = [
                    (V1/mm, P1), (V2/mm, P2), (V2/mm, P3),
                    (V1/mm, P4), (V1/mm, P1)
                ]

            elif "Diesel" in cevrim:
                beta_d = float(self.ent_m_beta_d.get())
                if beta_d <= 1: raise ValueError("Kesme oranı β > 1 olmalı.")

                # Sabit basınçta yanma 2→3
                # Q_in = mm * cp * (T3 - T2)  → Eq. 3-57
                T3 = T2 + Q_in / (mm * cp)
                P3 = P2
                V3 = V2 * beta_d

                # State 4: izentropic genleşme 3→4  (V4=V1)
                T4 = T3 * ((V3 / V1) ** (k - 1))  # Eq. 3-64
                P4 = P3 * ((V3 / V1) ** k)         # Eq. 3-65

                # Termal verim — Eq. 3-73
                eta_t = 1.0 - (1.0 / (rc ** (k - 1))) * \
                        ((beta_d ** k - 1) / (k * (beta_d - 1)))

                W_comp = mm * R * (T2 - T1) / (1 - k)
                W_xp23 = P2 * (V3 - V2)
                W_exp  = mm * R * (T4 - T3) / (1 - k)
                W_net  = W_comp + W_xp23 + W_exp

                pv_pts = [
                    (V1/mm, P1), (V2/mm, P2), (V3/mm, P3),
                    (V1/mm, P4), (V1/mm, P1)
                ]

            else:  # Dual
                alfa = float(self.ent_m_alfa.get())
                beta = float(self.ent_m_beta.get())
                if alfa < 1: raise ValueError("Basınç oranı α ≥ 1 olmalı.")
                if beta < 1: raise ValueError("Kesme oranı β ≥ 1 olmalı.")

                # Sabit hacimde yanma 2→x  (Eq. 3-76)
                Tx = T2 * alfa          # Px = alfa * P2
                Px = P2 * alfa
                Vx = V2

                # Sabit basınçta yanma x→3  (Eq. 3-81)
                T3 = Tx * beta
                P3 = Px
                V3 = Vx * beta

                # Gerçek Q_in değerini kullan (alfa/beta girildi, kontrol)
                Q_cv = mm * cv * (Tx - T2)
                Q_cp = mm * cp * (T3 - Tx)
                Q_in_hesap = Q_cv + Q_cp
                # Not: alfa ve beta girildiğinde Q_in bundan belirlenir,
                # burada orijinal Q_in'i kullanmak yerine alfa/beta geometrisine
                # güveniyoruz. Eta_t için Eq. 3-89 kullanılır.

                # State 4: izentropic genleşme 3→4
                T4 = T3 * ((V3 / V1) ** (k - 1))
                P4 = P3 * ((V3 / V1) ** k)

                # Termal verim — Eq. 3-88
                eta_t = 1.0 - (T4 - T1) / ((Tx - T2) + k * (T3 - Tx))

                W_comp  = mm * R * (T2 - T1) / (1 - k)
                W_cv    = 0.0
                W_cp23  = P3 * (V3 - Vx)
                W_exp   = mm * R * (T4 - T3) / (1 - k)
                W_net   = W_comp + W_cv + W_cp23 + W_exp
                Q_in    = Q_in_hesap

                pv_pts = [
                    (V1/mm, P1), (V2/mm, P2), (Vx/mm, Px),
                    (V3/mm, P3), (V1/mm, P4), (V1/mm, P1)
                ]

            # ── Egzoz sıcaklığı — Eq. 3-37 ──────────────────────────
            # Tex = T4 * (Pex/P4)^((k-1)/k)
            if P4 > 0 and Pex > 0:
                Tex = T4 * ((Pex / P4) ** ((k - 1) / k))
            else:
                Tex = T4

            # ── Egzoz artığı — Eq. 3-46 ─────────────────────────────
            xr_calc = (1.0 / rc) * (T4 / Tex) * (Pex / P4)

            # ── T1 karışım — Eq. 3-50 ───────────────────────────────
            T_intake = T1   # giriş havası = T1 (manifold ısısı dahil)
            T1_mix   = xr_calc * Tex + (1 - xr_calc) * T_intake

            # ── Güç hesapları ────────────────────────────────────────
            # Gerçek verim (Eq. 3-32)
            eta_act = 0.85 * eta_t
            imep    = W_net / Vd   # kPa — indicated mean effective pressure
            # 4-stroke: n=2 devir/çevrim
            P_i     = W_net * N_sil * (RPM / 60) / 2   # kW
            P_b     = eta_m * P_i                       # kW
            torque  = P_b * 60 / (2 * math.pi * RPM)   # N·m

            # ── Sonuçları kaydet ─────────────────────────────────────
            self.motor_sonuc = {
                "cevrim": cevrim, "yakit": self.combo_yakit.get(),
                "T1": T1, "T2": T2, "T3": T3, "T4": T4, "Tex": Tex,
                "P1": P1, "P2": P2, "P3": P3, "P4": P4,
                "eta_t": eta_t, "eta_act": eta_act,
                "W_net": W_net, "Q_in": Q_in,
                "imep": imep, "P_i": P_i, "P_b": P_b, "torque": torque,
                "xr_calc": xr_calc, "T1_mix": T1_mix - 273.15,
                "rc": rc, "AF": AF, "QHV": QHV, "RPM": RPM,
                "Vd": Vd, "N_sil": N_sil, "pv_pts": pv_pts,
                "k": k,
            }

            # ── Kartları güncelle ─────────────────────────────────────
            Tex_C = Tex - 273.15
            self.m_state["T1"].set(f"{T1-273.15:.1f} °C  ({T1:.0f} K)")
            self.m_state["T2"].set(f"{T2-273.15:.1f} °C  ({T2:.0f} K)")
            self.m_state["T3"].set(f"{T3-273.15:.1f} °C  ({T3:.0f} K)")
            self.m_state["T4"].set(f"{T4-273.15:.1f} °C  ({T4:.0f} K)")
            self.m_state["Tex"].set(f"{Tex_C:.1f} °C  ({Tex:.0f} K)",
                                    renk=CLR_RED if Tex_C > 800 else CLR_AMBER)
            self.m_state["P1"].set(f"{P1:.1f}")
            self.m_state["P2"].set(f"{P2:.1f}")
            self.m_state["P3"].set(f"{P3:.1f}")
            self.m_state["P4"].set(f"{P4:.1f}")

            self.m_perf["eta_t"].set(f"% {eta_t*100:.2f}")
            self.m_perf["eta_act"].set(f"% {eta_act*100:.2f}")
            self.m_perf["W_net"].set(f"{W_net:.4f} kJ")
            self.m_perf["Q_in"].set(f"{Q_in:.4f} kJ")
            self.m_perf["imep"].set(f"{imep:.1f} kPa")
            self.m_perf["P_i"].set(f"{P_i:.2f} kW")
            self.m_perf["P_b"].set(f"{P_b:.2f} kW")
            self.m_perf["torque"].set(f"{torque:.2f} N·m")
            self.m_perf["xr_calc"].set(f"{xr_calc:.4f}")
            self.m_perf["T1_mix"].set(f"{T1_mix-273.15:.1f} °C")

            # ── Durum çubuğu ──────────────────────────────────────────
            self.lbl_motor_durum.configure(
                fg_color="#0f2a1a", text_color=CLR_GREEN,
                text=f"✅  T_ex = {Tex_C:.1f} °C  |  P_brake = {P_b:.1f} kW  "
                     f"|  η_t = {eta_t*100:.1f}%  |  Simülasyona aktarıldı")

            # ── P-v diyagramı ─────────────────────────────────────────
            self._pv_ciz(pv_pts, cevrim)

            # ── Ana simülasyona aktar ──────────────────────────────────
            self.ent_temp_ei.delete(0, "end")
            self.ent_temp_ei.insert(0, f"{Tex_C:.1f}")

            # Debounce'u atla, direkt hesapla
            self.hesapla(hafizaya_yaz=False)

            messagebox.showinfo(
                "Aktarım Başarılı",
                f"Motor çevrimi hesaplandı:\n\n"
                f"  Egzoz Çıkış Sıcaklığı:  {Tex_C:.1f} °C\n"
                f"  Fren Gücü:              {P_b:.1f} kW\n"
                f"  Termal Verim:           {eta_t*100:.1f} %\n\n"
                f"T_ex → EGR Cooler giriş sıcaklığına aktarıldı.")

        except (ValueError, ZeroDivisionError) as e:
            messagebox.showerror("Çevrim Hesap Hatası", str(e))

    # ================================================================
    # P-v DİYAGRAMI ÇİZİCİ
    # ================================================================
    def _pv_ciz(self, pv_pts, cevrim):
        c = self.canvas_pv
        c.delete("all")
        W = c.winfo_width() or 700
        H = c.winfo_height() or 350
        if W < 100 or H < 100:
            return

        PAD_L, PAD_R = 70, 30
        PAD_T, PAD_B = 40, 55
        gx1 = PAD_L; gx2 = W - PAD_R
        gy1 = PAD_T; gy2 = H - PAD_B

        # Başlık
        c.create_text(W // 2, 18, text=f"P-v Diyagramı  —  {cevrim}",
                      fill=CLR_TEXT_PRI, font=("Arial", 11, "bold"))

        # Eksen
        c.create_line(gx1, gy2, gx2, gy2, fill=CLR_TEXT_SEC, width=2,
                      arrow="last", arrowshape=(10, 12, 4))
        c.create_line(gx1, gy2, gx1, gy1, fill=CLR_TEXT_SEC, width=2,
                      arrow="last", arrowshape=(10, 12, 4))
        c.create_text(W // 2, H - 12, text="Özgül Hacim  v  [m³/kg]",
                      fill=CLR_TEXT_SEC, font=("Arial", 10))
        c.create_text(18, (gy1 + gy2) // 2, text="Basınç\nP [kPa]",
                      fill=CLR_TEXT_SEC, font=("Arial", 10), angle=90)

        if not pv_pts:
            return

        all_v = [p[0] for p in pv_pts]
        all_p = [p[1] for p in pv_pts]
        v_min, v_max = min(all_v), max(all_v)
        p_min, p_max = min(all_p), max(all_p)
        v_span = (v_max - v_min) or 1
        p_span = (p_max - p_min) or 1

        v_pad = v_span * 0.12
        p_pad = p_span * 0.15

        def tx(v): return gx1 + (v - v_min + v_pad) / (v_span + 2*v_pad) * (gx2 - gx1)
        def ty(p): return gy2 - (p - p_min + p_pad) / (p_span + 2*p_pad) * (gy2 - gy1)

        # Izgara yatay
        for i in range(1, 5):
            yg = gy1 + (gy2 - gy1) * i // 4
            c.create_line(gx1, yg, gx2, yg, fill=CLR_BG_CARD, width=1)
            pval = p_max - p_span * i / 4
            c.create_text(gx1 - 6, yg, text=f"{pval:.0f}",
                          fill=CLR_TEXT_MUT, font=("Arial", 8), anchor="e")

        # Izgara dikey
        for i in range(1, 5):
            xg = gx1 + (gx2 - gx1) * i // 4
            c.create_line(xg, gy1, xg, gy2, fill=CLR_BG_CARD, width=1)
            vval = v_min + v_span * i / 4
            c.create_text(xg, gy2 + 12, text=f"{vval*1000:.3f}",
                          fill=CLR_TEXT_MUT, font=("Arial", 8), anchor="n")

        # İzentropic eğri çizici
        def izen_egri(v_a, p_a, v_b, n=60, renk=CLR_CYAN, genislik=2):
            """P·v^k = sabit izentropic eğri"""
            C = p_a * (v_a ** 1.35)
            pts = []
            for i in range(n + 1):
                v = v_a + (v_b - v_a) * i / n
                p = C / (v ** 1.35)
                pts.append((tx(v), ty(p)))
            for i in range(len(pts) - 1):
                c.create_line(pts[i][0], pts[i][1],
                              pts[i+1][0], pts[i+1][1],
                              fill=renk, width=genislik)

        # Çevrime göre çiz
        n_pts = len(pv_pts) - 1  # son nokta başa dönüş

        if "Otto" in cevrim:
            # 1-2 izentropic sıkıştırma
            izen_egri(pv_pts[0][0], pv_pts[0][1], pv_pts[1][0], renk=CLR_SIVI)
            # 2-3 sabit hacim yanma
            c.create_line(tx(pv_pts[1][0]), ty(pv_pts[1][1]),
                          tx(pv_pts[2][0]), ty(pv_pts[2][1]),
                          fill=CLR_EGZOZ, width=2)
            # 3-4 izentropic genleşme
            izen_egri(pv_pts[2][0], pv_pts[2][1], pv_pts[3][0], renk=CLR_AMBER)
            # 4-1 sabit hacim ısı atımı
            c.create_line(tx(pv_pts[3][0]), ty(pv_pts[3][1]),
                          tx(pv_pts[4][0]), ty(pv_pts[4][1]),
                          fill=CLR_TEXT_SEC, width=2)
            # Etiketler
            labels = ["1", "2", "3", "4"]
            offsets = [(-10,8),(8,-8),(-10,-10),(10,8)]

        elif "Diesel" in cevrim:
            izen_egri(pv_pts[0][0], pv_pts[0][1], pv_pts[1][0], renk=CLR_SIVI)
            # 2-3 sabit basınç
            c.create_line(tx(pv_pts[1][0]), ty(pv_pts[1][1]),
                          tx(pv_pts[2][0]), ty(pv_pts[2][1]),
                          fill=CLR_EGZOZ, width=2)
            izen_egri(pv_pts[2][0], pv_pts[2][1], pv_pts[3][0], renk=CLR_AMBER)
            c.create_line(tx(pv_pts[3][0]), ty(pv_pts[3][1]),
                          tx(pv_pts[4][0]), ty(pv_pts[4][1]),
                          fill=CLR_TEXT_SEC, width=2)
            labels = ["1", "2", "3", "4"]
            offsets = [(-10,8),(8,-8),(-10,-10),(10,8)]

        else:  # Dual
            izen_egri(pv_pts[0][0], pv_pts[0][1], pv_pts[1][0], renk=CLR_SIVI)
            c.create_line(tx(pv_pts[1][0]), ty(pv_pts[1][1]),
                          tx(pv_pts[2][0]), ty(pv_pts[2][1]),
                          fill=CLR_EGZOZ, width=2)
            c.create_line(tx(pv_pts[2][0]), ty(pv_pts[2][1]),
                          tx(pv_pts[3][0]), ty(pv_pts[3][1]),
                          fill=CLR_RED, width=2)
            izen_egri(pv_pts[3][0], pv_pts[3][1], pv_pts[4][0], renk=CLR_AMBER)
            c.create_line(tx(pv_pts[4][0]), ty(pv_pts[4][1]),
                          tx(pv_pts[5][0]), ty(pv_pts[5][1]),
                          fill=CLR_TEXT_SEC, width=2)
            labels = ["1", "2", "x", "3", "4"]
            offsets = [(-10,8),(8,-8),(8,-8),(-10,-10),(10,8)]

        # Nokta etiketleri
        for i, (lbl, off) in enumerate(zip(labels, offsets)):
            px, py = pv_pts[i]
            c.create_oval(tx(px)-4, ty(py)-4, tx(px)+4, ty(py)+4,
                          fill=CLR_AMBER, outline="")
            c.create_text(tx(px)+off[0], ty(py)+off[1], text=lbl,
                          fill=CLR_AMBER, font=("Arial", 10, "bold"))

        # Renkli legend
        leg = [("Sıkıştırma", CLR_SIVI), ("Yanma", CLR_EGZOZ),
               ("Genleşme", CLR_AMBER), ("Blowdown", CLR_TEXT_SEC)]
        for i, (txt, renk) in enumerate(leg):
            c.create_line(gx2 - 150, gy1 + 12 + i*16,
                          gx2 - 126, gy1 + 12 + i*16, fill=renk, width=2)
            c.create_text(gx2 - 122, gy1 + 12 + i*16,
                          text=txt, fill=renk, font=("Arial", 9), anchor="w")

    def _motor_rapor_kaydet(self):
        if not self.motor_sonuc:
            messagebox.showwarning("Uyarı", "Önce çevrimi hesaplayın.")
            return
        dosya = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Metin Dosyası", "*.txt")],
            title="Motor Çevrim Raporunu Kaydet")
        if not dosya:
            return
        r = self.motor_sonuc
        Tex_C = r["Tex"] - 273.15
        metin = (
            "=" * 70 + "\n"
            "     MOTOR ÇEVRİM ANALİZİ — EGR Lab v6.0\n"
            "=" * 70 + "\n"
            f" Geliştiren : Enes Çelik Simülasyon Sistemleri\n"
            "-" * 70 + "\n\n"
            " [1] ÇEVRİM BİLGİSİ\n"
            "-" * 70 + "\n"
            f" Çevrim Tipi        : {r['cevrim']}\n"
            f" Yakıt              : {r['yakit']}\n"
            f" Isıl Değer Q_HV    : {r['QHV']:.0f} kJ/kg\n"
            f" Sıkıştırma Oranı   : {r['rc']:.1f}\n"
            f" AF Oranı           : {r['AF']:.1f}\n"
            f" Motor Devri        : {r['RPM']:.0f} RPM\n\n"
            " [2] DURUM NOKTASI SICAKLIKLARI\n"
            "-" * 70 + "\n"
            f" T₁ (sıkıştırma başı)  : {r['T1']-273.15:.1f} °C  ({r['T1']:.1f} K)\n"
            f" T₂ (sıkıştırma sonu)  : {r['T2']-273.15:.1f} °C  ({r['T2']:.1f} K)\n"
            f" T₃ (yanma sonu, T_max): {r['T3']-273.15:.1f} °C  ({r['T3']:.1f} K)\n"
            f" T₄ (genleşme sonu)    : {r['T4']-273.15:.1f} °C  ({r['T4']:.1f} K)\n"
            f" T_ex (egzoz / EGR giriş): {Tex_C:.1f} °C  ({r['Tex']:.1f} K)\n\n"
            " [3] PERFORMANS SONUÇLARI\n"
            "-" * 70 + "\n"
            f" Termal Verim η_t    : % {r['eta_t']*100:.2f}\n"
            f" Gerçek Verim        : % {r['eta_act']*100:.2f}\n"
            f" Net İş W_net        : {r['W_net']:.4f} kJ/silindir\n"
            f" Isı Girdisi Q_in    : {r['Q_in']:.4f} kJ/silindir\n"
            f" İMEP                : {r['imep']:.1f} kPa\n"
            f" Gösterilen Güç      : {r['P_i']:.2f} kW\n"
            f" Fren (Brake) Gücü   : {r['P_b']:.2f} kW\n"
            f" Tork                : {r['torque']:.2f} N·m\n"
            "=" * 70 + "\n"
            "              RAPOR SONU\n"
            "=" * 70 + "\n"
        )
        with open(dosya, "w", encoding="utf-8") as f:
            f.write(metin)
        messagebox.showinfo("Başarılı", f"Rapor kaydedildi:\n{dosya}")

    # ================================================================
    # SEKME 2 — TERMAL SİMÜLASYON (Ana sekme)
    # ================================================================
    def _build_ana(self):
        self.sol = ctk.CTkScrollableFrame(
            self.tab_ana, width=420, fg_color=CLR_BG_PANEL,
            scrollbar_button_color=CLR_BORDER)
        self.sol.pack(side="left", fill="y", padx=(6, 4), pady=6)

        sag = ctk.CTkFrame(self.tab_ana, fg_color=CLR_BG_PANEL)
        sag.pack(side="right", fill="both", expand=True, padx=(4, 6), pady=6)

        ctk.CTkLabel(self.sol, text="SİMÜLASYON PARAMETRELERİ",
                     font=("Arial", 12, "bold"), text_color=CLR_CYAN,
                     ).pack(pady=(12, 6), padx=14, anchor="w")

        # Akış tipi
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

        self.combo_sogutucu = self._combo(
            self.sol, list(self.sogutucu_db.keys()), "Soğutucu Akışkan Tipi:")

        # Geçmiş butonları
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

        # Numerik girdiler — Motor Gücü KALDIRILDI
        self._section_label(self.sol, "Temel Termal Parametreler")
        self.ent_deb_e   = self._entry(self.sol, "Egzoz Debisi ṁₑ [kg/s]:", "0.15")
        self.ent_temp_ei = self._entry(self.sol, "Egzoz Giriş Sıcaklığı [°C]:", "450")

        # Motor çevriminden gelir bilgisi
        ctk.CTkLabel(
            self.sol,
            text="↑  'Motor Çevrimi' sekmesinden otomatik aktarılır",
            font=("Arial", 9, "italic"), text_color=CLR_AMBER,
        ).pack(padx=14, anchor="w")

        self.ent_deb_s   = self._entry(self.sol, "Sıvı Debisi ṁₛ [kg/s]:", "0.5")
        self.ent_temp_si = self._entry(self.sol, "Sıvı Giriş Sıcaklığı [°C]:", "80")
        self.ent_U       = self._entry(self.sol, "Isı Transfer Katsayısı U [W/m²K]:", "280")

        self._section_label(self.sol, "Kanal / Geometri Parametreleri")
        self.ent_Dh    = self._entry(self.sol, "Hidrolik Çap Dₕ [mm]:", "11.4")
        self.ent_N     = self._entry(self.sol, "Kanal / Boru Sayısı N [adet]:", "90")
        self.ent_rho   = self._entry(self.sol, "Egzoz Yoğunluğu ρ [kg/m³]:", "0.45")
        self.ent_mu    = self._entry(self.sol, "Dinamik Viskozite μ [×10⁻⁵ Pa·s]:", "3.5")
        self.ent_Pr    = self._entry(self.sol, "Prandtl Sayısı Pr [-]:", "0.72")
        self.ent_k_gaz = self._entry(self.sol, "Gaz Isıl İletkenliği k_gaz [W/mK]:", "0.055")
        self.ent_Ak    = self._entry(self.sol, "Tek Kanal Kesit Alanı Aₖ [mm²]:", "160")

        # Slider
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

        # Butonlar
        ctk.CTkButton(
            self.sol, text="▶   SİMÜLASYONU ÇALIŞTIR",
            font=("Arial", 13, "bold"), height=42,
            fg_color=CLR_CYAN, hover_color="#3bbbd4",
            text_color="#0d1117", command=self.hesapla,
        ).pack(pady=(12, 4), padx=14, fill="x")

        ctk.CTkButton(
            self.sol, text="💾  RAPOR KAYDET (.txt)",
            font=("Arial", 12), height=36,
            fg_color="#1c4a2e", hover_color="#245c38",
            text_color=CLR_GREEN, border_color=CLR_GREEN, border_width=1,
            command=self._rapor_kaydet,
        ).pack(pady=(0, 12), padx=14, fill="x")

        # Şema canvas
        self.canvas_sema = ctk.CTkCanvas(
            sag, height=220, bg=CLR_BG_CARD, highlightthickness=0)
        self.canvas_sema.pack(fill="x", padx=8, pady=(8, 4))

        # Sonuç kartları
        sonuc_scroll = ctk.CTkScrollableFrame(
            sag, fg_color=CLR_BG_PANEL,
            scrollbar_button_color=CLR_BORDER)
        sonuc_scroll.pack(fill="both", expand=True, padx=8, pady=4)

        kart1 = KartFrame(sonuc_scroll, "⚙   SİSTEM VE AKIŞKAN ÖZELLİKLERİ", CLR_CYAN)
        kart1.pack(fill="x", pady=(0, 6))
        self.sr_akis  = SonucSatir(kart1, "Akış Tipi"); self.sr_akis.pack(fill="x", pady=(4, 0))
        self.sr_sog   = SonucSatir(kart1, "Soğutucu Akışkan"); self.sr_sog.pack(fill="x")
        self.sr_yakit_bilgi = SonucSatir(kart1, "Yakıt / Egzoz Tipi")
        self.sr_yakit_bilgi.pack(fill="x", pady=(0, 6))

        kart2 = KartFrame(sonuc_scroll, "📐   GEOMETRİK & TRANSFER VERİLERİ", CLR_PURPLE)
        kart2.pack(fill="x", pady=(0, 6))
        self.sr_A    = SonucSatir(kart2, "Aktif Transfer Alanı A"); self.sr_A.pack(fill="x", pady=(4, 0))
        self.sr_U    = SonucSatir(kart2, "Isı Geçiş Katsayısı U"); self.sr_U.pack(fill="x")
        self.sr_LMTD = SonucSatir(kart2, "LMTD"); self.sr_LMTD.pack(fill="x")
        self.sr_NTU  = SonucSatir(kart2, "NTU"); self.sr_NTU.pack(fill="x", pady=(0, 6))

        kart3 = KartFrame(sonuc_scroll, "🔥   ENERJİ BİLANÇOSU VE ÇIKTILAR", CLR_AMBER)
        kart3.pack(fill="x", pady=(0, 6))
        self.sr_Tei  = SonucSatir(kart3, "Egzoz Giriş T°",  deger_renk=CLR_EGZOZ); self.sr_Tei.pack(fill="x", pady=(4, 0))
        self.sr_Teo  = SonucSatir(kart3, "Egzoz Çıkış T°",  deger_renk=CLR_AMBER); self.sr_Teo.pack(fill="x")
        self.sr_Tsi  = SonucSatir(kart3, "Sıvı Giriş T°",   deger_renk=CLR_SIVI);  self.sr_Tsi.pack(fill="x")
        self.sr_Tso  = SonucSatir(kart3, "Sıvı Çıkış T°",   deger_renk=CLR_CYAN);  self.sr_Tso.pack(fill="x")
        AyiriciCizgi(kart3)
        self.sr_q    = SonucSatir(kart3, "Geri Kazanılan Isı", deger_renk=CLR_GREEN); self.sr_q.pack(fill="x")
        self.sr_eps  = SonucSatir(kart3, "Termal Etkinlik ε"); self.sr_eps.pack(fill="x", pady=(0, 6))

        self.lbl_durum = ctk.CTkLabel(
            sag, text="● Sistem Hazır",
            font=("Arial", 12, "bold"), fg_color=CLR_BG_CARD,
            text_color=CLR_GREEN, height=38, corner_radius=6)
        self.lbl_durum.pack(fill="x", padx=8, pady=(4, 8))

    def _slider_cb(self, val):
        self.lbl_slider.configure(text=f"Alan: {val:.2f} m²")
        self.hesapla(hafizaya_yaz=False)

    # ================================================================
    # SEKME 3 — GEOMETRİ & U HESAPLAMA
    # ================================================================
    def _build_sihirbaz(self):
        ana = ctk.CTkScrollableFrame(
            self.tab_sihirbaz, fg_color=CLR_BG_PANEL,
            scrollbar_button_color=CLR_BORDER)
        ana.pack(fill="both", expand=True, padx=6, pady=6)

        ctk.CTkLabel(ana, text="GEOMETRİ, YÜZEY ALANI VE U KATSAYISI HESAPLAMA MERKEZİ",
                     font=("Arial", 13, "bold"), text_color=CLR_CYAN).pack(pady=(12, 2))
        ctk.CTkLabel(ana, text="Profil seçin → Boyutları girin → Hesapla → Simülasyona Aktar",
                     font=("Arial", 10), text_color=CLR_TEXT_SEC).pack(pady=(0, 10))

        # Alan hesaplayıcı
        frm_alan = KartFrame(ana, "📐   YÜZEY ALANI HESAPLAYICI", CLR_CYAN)
        frm_alan.pack(fill="x", padx=10, pady=(0, 8))

        pr = ctk.CTkFrame(frm_alan, fg_color="transparent")
        pr.pack(fill="x", padx=14, pady=(10, 4))
        ctk.CTkLabel(pr, text="Kanal / Boru Profili:", font=("Arial", 11),
                     text_color=CLR_TEXT_SEC, width=200, anchor="w").pack(side="left")
        self.combo_profil = ctk.CTkOptionMenu(
            pr,
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

        self.frm_profil_giris = ctk.CTkFrame(frm_alan, fg_color=CLR_BG_INPUT, corner_radius=8)
        self.frm_profil_giris.pack(fill="x", padx=14, pady=6)

        self.ent_alan_L = self._sihirbaz_entry(frm_alan, "Kanal / Boru Etkin Uzunluğu L [mm]:", "350")
        self.ent_alan_N = self._sihirbaz_entry(frm_alan, "Toplam Kanal / Boru Sayısı N [adet]:", "90")

        self.lbl_formul = ctk.CTkLabel(frm_alan, text="", font=("Arial", 10, "italic"),
                                       text_color=CLR_AMBER, wraplength=860, justify="left")
        self.lbl_formul.pack(padx=14, pady=2, anchor="w")

        sonuc_r = ctk.CTkFrame(frm_alan, fg_color="transparent")
        sonuc_r.pack(fill="x", padx=14, pady=(6, 12))
        self.lbl_alan_sonuc = ctk.CTkLabel(
            sonuc_r, text="Toplam Alan: —  m²",
            font=("Arial", 13, "bold"), text_color=CLR_CYAN, width=300, anchor="w")
        self.lbl_alan_sonuc.pack(side="left")
        ctk.CTkButton(
            sonuc_r, text="Hesapla & Simülasyona Aktar  💾",
            font=("Arial", 12, "bold"), width=270,
            fg_color=CLR_AMBER, hover_color="#c8890a",
            text_color="#0d1117", command=self._sihirbaz_aktar,
        ).pack(side="right")

        self._profil_widget = {}
        self._profil_degisti("Yuvarlak Boru (Circular)")

        # U katsayısı
        frm_u = KartFrame(ana, "🔬   TOPLAM ISI GEÇİŞ KATSAYISI (U) HESAPLAYICI", CLR_PURPLE)
        frm_u.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(frm_u,
                     text="1/U = 1/h_iç  +  t_duvar/k_duvar  +  1/h_dış  +  2·R_fouling",
                     font=("Arial", 10, "italic"), text_color=CLR_TEXT_SEC,
                     ).pack(padx=14, pady=(10, 4), anchor="w")

        mr = ctk.CTkFrame(frm_u, fg_color="transparent")
        mr.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(mr, text="Duvar Malzemesi:", font=("Arial", 11),
                     text_color=CLR_TEXT_SEC, width=200, anchor="w").pack(side="left")
        self.combo_malzeme = ctk.CTkOptionMenu(
            mr, values=list(self.malzeme_db.keys()),
            fg_color=CLR_BG_INPUT, button_color=CLR_PURPLE,
            button_hover_color="#9a6ee0", text_color=CLR_TEXT_PRI,
            dropdown_fg_color=CLR_BG_CARD, dropdown_text_color=CLR_TEXT_PRI,
            width=320, command=self._malzeme_degisti,
        )
        self.combo_malzeme.pack(side="left", padx=8)

        self.ent_u_hic  = self._sihirbaz_entry(frm_u, "İç Konveksiyon Katsayısı h_iç [W/m²K]:", "250")
        self.ent_u_hdis = self._sihirbaz_entry(frm_u, "Dış Konveksiyon Katsayısı h_dış [W/m²K]:", "3500")
        self.ent_u_t    = self._sihirbaz_entry(frm_u, "Duvar Kalınlığı t [mm]:", "1.0")

        self.frm_k_manuel = ctk.CTkFrame(frm_u, fg_color="transparent")
        self.ent_u_k = self._sihirbaz_entry(self.frm_k_manuel, "Isıl İletkenlik k [W/mK] (Manuel):", "16")
        self.frm_k_manuel.pack_forget()

        fr2 = ctk.CTkFrame(frm_u, fg_color="transparent")
        fr2.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(fr2, text="Kirlenme Direnci R_fouling [m²K/W]  (0=ihmal):",
                     font=("Arial", 11), text_color=CLR_TEXT_SEC, width=360, anchor="w").pack(side="left")
        self.ent_u_fouling = ctk.CTkEntry(fr2, width=105, fg_color=CLR_BG_INPUT,
                                          border_color=CLR_BORDER, text_color=CLR_TEXT_PRI)
        self.ent_u_fouling.insert(0, "0.0001")
        self.ent_u_fouling.pack(side="right")

        ur = ctk.CTkFrame(frm_u, fg_color="transparent")
        ur.pack(fill="x", padx=14, pady=(8, 6))
        self.lbl_u_sonuc = ctk.CTkLabel(
            ur, text="Hesaplanan U: —  W/m²K",
            font=("Arial", 13, "bold"), text_color=CLR_PURPLE, width=320, anchor="w")
        self.lbl_u_sonuc.pack(side="left")
        ctk.CTkButton(
            ur, text="Hesapla & U Değerine Aktar  🔬",
            font=("Arial", 12, "bold"), width=270,
            fg_color=CLR_PURPLE, hover_color="#9a6ee0",
            text_color="#0d1117", command=self._u_hesapla,
        ).pack(side="right")

        self.frm_u_detay = KartFrame(frm_u, "Isıl Direnç Dökümü", CLR_TEXT_MUT)
        self.frm_u_detay.pack(fill="x", padx=14, pady=(0, 12))
        self.u_detay_satirlar = {}
        for key, etiket in [
            ("R_ic",    "R_iç  = 1/h_iç"),
            ("R_duvar", "R_duvar  = t/k"),
            ("R_dis",   "R_dış  = 1/h_dış"),
            ("R_foul",  "R_fouling  = 2×Rf"),
            ("R_top",   "R_toplam"),
            ("U_val",   "U  = 1/R_toplam"),
        ]:
            s = SonucSatir(self.frm_u_detay, etiket,
                           deger_renk=CLR_PURPLE if key == "U_val" else CLR_TEXT_PRI)
            s.pack(fill="x", pady=2)
            self.u_detay_satirlar[key] = s
        ctk.CTkFrame(self.frm_u_detay, height=6, fg_color="transparent").pack()

    def _sihirbaz_entry(self, parent, label, default):
        fr = ctk.CTkFrame(parent, fg_color="transparent")
        fr.pack(pady=3, fill="x", padx=14)
        ctk.CTkLabel(fr, text=label, font=("Arial", 11),
                     text_color=CLR_TEXT_SEC, anchor="w", width=360).pack(side="left")
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
            "Yuvarlak Boru (Circular)":        {"alanlar": [("Dış Çap d [mm]", "12")],                             "formul": "A = π × d × L × N     |    Dₕ = d"},
            "Dikdörtgen Kanal (Rectangular)":  {"alanlar": [("Genişlik a [mm]", "20"), ("Yükseklik b [mm]", "8")],  "formul": "A = 2(a+b) × L × N    |    Dₕ = 2ab/(a+b)"},
            "Kare Kanal (Square)":             {"alanlar": [("Kenar a [mm]", "12")],                                "formul": "A = 4a × L × N         |    Dₕ = a"},
            "Eliptik Boru (Elliptical)":       {"alanlar": [("Büyük eksen a [mm]", "15"), ("Küçük eksen b [mm]", "7")], "formul": "A ≈ Ramanujan 2. yakl. × L × N   |   Dₕ = 4A_k/çevre"},
            "Üçgen Kanal (Triangular)":        {"alanlar": [("Taban c [mm]", "12"), ("Yükseklik h [mm]", "10")],   "formul": "A = (c + 2√((c/2)²+h²)) × L × N"},
            "Altıgen Kanal (Hexagonal)":       {"alanlar": [("Kenar s [mm]", "8")],                                 "formul": "A = 6s × L × N          |    Dₕ = s√3"},
        }
        if secim not in tanim: return
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
        try:
            profil = self.combo_profil.get()
            L = float(self.ent_alan_L.get()) / 1000.0
            N = float(self.ent_alan_N.get())
            if L <= 0 or N <= 0: raise ValueError("L ve N > 0 olmalı.")
            w = {k: float(v.get()) / 1000.0 for k, v in self._profil_widget.items()}
            vals = list(w.values())
            alan = Dh_m = Ak_m2 = 0.0
            if profil == "Yuvarlak Boru (Circular)":
                d = vals[0]
                alan = math.pi * d * L * N; Dh_m = d; Ak_m2 = math.pi*(d/2)**2
            elif profil == "Dikdörtgen Kanal (Rectangular)":
                a, b = vals[0], vals[1]
                alan = 2*(a+b)*L*N; Dh_m = 2*a*b/(a+b); Ak_m2 = a*b
            elif profil == "Kare Kanal (Square)":
                a = vals[0]
                alan = 4*a*L*N; Dh_m = a; Ak_m2 = a**2
            elif profil == "Eliptik Boru (Elliptical)":
                a, b = vals[0], vals[1]
                h_r = ((a-b)/(a+b))**2
                cevre = math.pi*(a+b)*(1+3*h_r/(10+math.sqrt(4-3*h_r)))
                alan = cevre*L*N; Ak_m2 = math.pi*a*b; Dh_m = 4*Ak_m2/cevre
            elif profil == "Üçgen Kanal (Triangular)":
                c, h = vals[0], vals[1]
                kenar = math.sqrt((c/2)**2+h**2)
                cevre = c+2*kenar; alan = cevre*L*N
                Ak_m2 = 0.5*c*h; Dh_m = 4*Ak_m2/cevre
            elif profil == "Altıgen Kanal (Hexagonal)":
                s = vals[0]
                alan = 6*s*L*N; Ak_m2 = (3*math.sqrt(3)/2)*s**2; Dh_m = s*math.sqrt(3)
            self.lbl_alan_sonuc.configure(text=f"Toplam Alan: {alan:.4f} m²")
            self.slider.set(min(max(alan, 0.1), 3.5))
            self.lbl_slider.configure(text=f"Alan: {alan:.2f} m²")
            self.ent_Dh.delete(0, "end"); self.ent_Dh.insert(0, f"{Dh_m*1000:.3f}")
            self.ent_Ak.delete(0, "end"); self.ent_Ak.insert(0, f"{Ak_m2*1e6:.2f}")
            self.ent_N.delete(0, "end");  self.ent_N.insert(0, str(int(N)))
            messagebox.showinfo("Başarılı",
                f"Alan = {alan:.4f} m²\nDₕ = {Dh_m*1000:.3f} mm\nAₖ = {Ak_m2*1e6:.2f} mm²\n\nAktarıldı.")
            self.tabview.set("⚙   Termal Simülasyon")
            self.hesapla()
        except (ValueError, ZeroDivisionError) as e:
            messagebox.showerror("Geometri Hatası", str(e))

    def _u_hesapla(self):
        try:
            h_ic = float(self.ent_u_hic.get()); h_dis = float(self.ent_u_hdis.get())
            t_mm = float(self.ent_u_t.get());  R_f  = float(self.ent_u_fouling.get())
            mal  = self.combo_malzeme.get();   k    = self.malzeme_db.get(mal)
            if k is None: k = float(self.ent_u_k.get())
            t = t_mm / 1000.0
            R_ic = 1/h_ic; R_duvar = t/k if t > 0 else 0; R_dis = 1/h_dis
            R_foul = 2*R_f; R_top = R_ic+R_duvar+R_dis+R_foul; U = 1/R_top
            self.lbl_u_sonuc.configure(text=f"Hesaplanan U: {U:.2f} W/m²K")
            self.u_detay_satirlar["R_ic"].set(f"{R_ic:.6f}  m²K/W")
            self.u_detay_satirlar["R_duvar"].set(f"{R_duvar:.6f}  m²K/W")
            self.u_detay_satirlar["R_dis"].set(f"{R_dis:.6f}  m²K/W")
            self.u_detay_satirlar["R_foul"].set(f"{R_foul:.6f}  m²K/W")
            self.u_detay_satirlar["R_top"].set(f"{R_top:.6f}  m²K/W")
            self.u_detay_satirlar["U_val"].set(f"{U:.2f}  W/m²K", renk=CLR_PURPLE)
            self.ent_U.delete(0, "end"); self.ent_U.insert(0, f"{U:.2f}")
            messagebox.showinfo("Başarılı", f"U = {U:.2f} W/m²K aktarıldı.")
            self.tabview.set("⚙   Termal Simülasyon"); self.hesapla()
        except (ValueError, ZeroDivisionError) as e:
            messagebox.showerror("U Hesap Hatası", str(e))

    # ================================================================
    # SEKME 4 — REYNOLDS & AKIŞ ANALİZİ
    # ================================================================
    def _build_reynolds(self):
        ana = ctk.CTkScrollableFrame(
            self.tab_reynolds, fg_color=CLR_BG_PANEL,
            scrollbar_button_color=CLR_BORDER)
        ana.pack(fill="both", expand=True, padx=6, pady=6)
        ctk.CTkLabel(ana, text="REYNOLDS SAYISI & AKIŞ REJİMİ ANALİZ MERKEZİ",
                     font=("Arial", 13, "bold"), text_color=CLR_PURPLE).pack(pady=(12, 4))
        ctk.CTkButton(
            ana, text="🔄   Reynolds & Tek Kanal Analizini Hesapla",
            font=("Arial", 13, "bold"), height=42,
            fg_color=CLR_PURPLE, hover_color="#9a6ee0",
            text_color="#0d1117", command=self._reynolds_hesapla,
        ).pack(fill="x", padx=10, pady=(0, 8))
        self.lbl_re_bar = ctk.CTkLabel(
            ana, text="— Henüz hesaplanmadı —",
            font=("Arial", 12, "bold"), fg_color=CLR_BG_CARD,
            height=42, text_color=CLR_TEXT_SEC, corner_radius=6)
        self.lbl_re_bar.pack(fill="x", padx=10, pady=(0, 8))
        kolon = ctk.CTkFrame(ana, fg_color="transparent")
        kolon.pack(fill="both", expand=True, padx=10)
        kolon.columnconfigure(0, weight=1); kolon.columnconfigure(1, weight=1)
        kart_re  = KartFrame(kolon, "📐   AKIŞ REJİMİ & NUSSELT ANALİZİ", CLR_PURPLE)
        kart_re.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        kart_isi = KartFrame(kolon, "🔥   TEK KANAL & TOPLAM ISI TRANSFERİ", CLR_AMBER)
        kart_isi.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
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
        isi_keys = [
            ("N",      "Toplam Kanal Sayısı N",     CLR_TEXT_PRI),
            ("A",      "Transfer Alanı A",           CLR_CYAN),
            ("NTU",    "NTU Sayısı",                 CLR_PURPLE),
            ("eps",    "Etkinlik ε",                 CLR_GREEN),
            ("q_max",  "q_max (teorik)",             CLR_TEXT_SEC),
            ("q_top",  "q_toplam (gerçek)",          CLR_GREEN),
            ("Teo",    "Egzoz Çıkış T°C",            CLR_AMBER),
            ("Tso",    "Sıvı Çıkış T°C",             CLR_CYAN),
            ("q_tek",  "Tek Kanal q [W]",            CLR_TEXT_PRI),
            ("hU_oran","h_iç / U oranı",             CLR_AMBER),
        ]
        self.isi_satirlar = {}
        for i, (key, etiket, renk) in enumerate(isi_keys):
            s = SonucSatir(kart_isi, etiket, deger_renk=renk)
            s.pack(fill="x", pady=(6 if i == 0 else 2, 0))
            self.isi_satirlar[key] = s
        ctk.CTkFrame(kart_isi, height=8, fg_color="transparent").pack()
        kart_uy = KartFrame(ana, "⚠   TASARIM ÖNERİLERİ & UYARILAR", CLR_AMBER)
        kart_uy.pack(fill="x", padx=10, pady=(8, 8))
        self.frm_uyari_ic = ctk.CTkFrame(kart_uy, fg_color="transparent")
        self.frm_uyari_ic.pack(fill="x", padx=8, pady=(4, 8))

    def _reynolds_hesapla(self):
        try:
            m_e  = float(self.ent_deb_e.get())
            T_ei = float(self.ent_temp_ei.get())
            T_si = float(self.ent_temp_si.get())
            U    = float(self.ent_U.get())
            A    = self.slider.get()
            cp_s = self.sogutucu_db[self.combo_sogutucu.get()]
            cp_e = self._get_egzoz_cp()
            m_s  = float(self.ent_deb_s.get())
            akis = self.combo_akis.get()
            Dh   = float(self.ent_Dh.get()) / 1000.0
            N    = int(float(self.ent_N.get()))
            rho  = float(self.ent_rho.get())
            mu   = float(self.ent_mu.get()) * 1e-5
            Pr   = float(self.ent_Pr.get())
            k_g  = float(self.ent_k_gaz.get())
            Ak   = float(self.ent_Ak.get()) * 1e-6
            v    = m_e / (N * Ak * rho)
            Re   = rho * v * Dh / mu
            if Re < 2300:
                rejim_txt = "LAMİNER"; bar_renk = "#1a3a2e"; bar_yazi = CLR_GREEN
            elif Re < 4000:
                rejim_txt = "GEÇİŞ"; bar_renk = "#3a2a00"; bar_yazi = CLR_AMBER
            else:
                rejim_txt = "TÜRBÜLANSLÜ"; bar_renk = "#3a1010"; bar_yazi = CLR_RED
            profil = self.combo_profil.get() if hasattr(self, "combo_profil") else ""
            if Re >= 4000:
                f_D  = (0.790*math.log(Re)-1.64)**-2
                Nu   = ((f_D/8)*(Re-1000)*Pr/(1+12.7*math.sqrt(f_D/8)*(Pr**(2/3)-1)))
                nu_y = "Gnielinski (türbülanslı)"
            elif Re >= 2300:
                def g(R):
                    ff=(0.790*math.log(R)-1.64)**-2
                    return ff,(ff/8)*(R-1000)*Pr/(1+12.7*math.sqrt(ff/8)*(Pr**(2/3)-1))
                f2,Nu2=g(2300); f4,Nu4=g(4000); gr=(Re-2300)/1700
                Nu=(1-gr)*Nu2+gr*Nu4; f_D=(1-gr)*f2+gr*f4; nu_y="Gnielinski interpolasyon"
            else:
                Nu = 3.66 if "Kare" not in profil else 2.98
                f_D = 64/Re; nu_y = "Sabit T_duvar laminer"
            h_ic_Re = Nu * k_g / Dh
            C_e=m_e*cp_e; C_s=m_s*cp_s; C_min=min(C_e,C_s); C_max=max(C_e,C_s)
            C_r=C_min/C_max; NTU=U*A/C_min; eps=_ntu_eps(NTU,C_r,akis)
            q_max=C_min*(T_ei-T_si); q_top=eps*q_max
            T_eo=T_ei-q_top/C_e; T_so=T_si+q_top/C_s
            L_tah=A/(N*math.pi*Dh) if Dh>0 and N>0 else 0
            dP=f_D*(L_tah/Dh)*(rho*v**2/2) if L_tah>0 else 0
            self.re_satirlar["Re"].set(f"{Re:.1f}")
            self.re_satirlar["v"].set(f"{v:.3f} m/s")
            self.re_satirlar["Dh"].set(f"{Dh*1000:.2f} mm")
            self.re_satirlar["rejim"].set(rejim_txt,
                renk=CLR_GREEN if Re<2300 else (CLR_AMBER if Re<4000 else CLR_RED))
            self.re_satirlar["Nu"].set(f"{Nu:.2f}")
            self.re_satirlar["hic"].set(f"{h_ic_Re:.1f} W/m²K")
            self.re_satirlar["f"].set(f"{f_D:.5f}")
            self.re_satirlar["dP"].set(f"{dP:.1f} Pa  ({dP/1000:.3f} kPa)")
            self.re_satirlar["yontem"].set(nu_y, renk=CLR_TEXT_MUT)
            self.isi_satirlar["N"].set(str(N))
            self.isi_satirlar["A"].set(f"{A:.4f} m²")
            self.isi_satirlar["NTU"].set(f"{NTU:.4f}")
            self.isi_satirlar["eps"].set(f"{eps*100:.2f} %",
                renk=CLR_GREEN if eps>=0.6 else CLR_AMBER)
            self.isi_satirlar["q_max"].set(f"{q_max/1000:.2f} kW")
            self.isi_satirlar["q_top"].set(f"{q_top/1000:.2f} kW")
            self.isi_satirlar["Teo"].set(f"{T_eo:.2f} °C")
            self.isi_satirlar["Tso"].set(f"{T_so:.2f} °C")
            self.isi_satirlar["q_tek"].set(f"{q_top/N:.2f} W")
            oran = h_ic_Re/U if U>0 else 0
            self.isi_satirlar["hU_oran"].set(
                f"{oran:.2f}  {'⚠ U > h_iç' if oran<1 else '✓'}",
                renk=CLR_RED if oran<1 else CLR_GREEN)
            self.lbl_re_bar.configure(
                fg_color=bar_renk, text_color=bar_yazi,
                text=f"Re = {Re:.0f}  |  {rejim_txt}  |  Nu = {Nu:.1f}  "
                     f"|  h_iç = {h_ic_Re:.0f} W/m²K  |  v = {v:.2f} m/s")
            for w in self.frm_uyari_ic.winfo_children():
                w.destroy()
            uyarilar = _olustur_uyarilar(Re, v, dP, h_ic_Re, U, T_eo, eps)
            for ikon, mesaj, renk in uyarilar:
                fr = ctk.CTkFrame(self.frm_uyari_ic, fg_color=CLR_BG_INPUT, corner_radius=6)
                fr.pack(fill="x", pady=2)
                ctk.CTkLabel(fr, text=ikon, font=("Arial", 14),
                             text_color=renk, width=28).pack(side="left", padx=(8, 4), pady=4)
                ctk.CTkLabel(fr, text=mesaj, font=("Arial", 11),
                             text_color=CLR_TEXT_PRI, anchor="w",
                             wraplength=820).pack(side="left", pady=4)
        except (ValueError, ZeroDivisionError) as e:
            messagebox.showerror("Reynolds Hatası", str(e))

    # ================================================================
    # SEKME 5 — GRAFİK PANELİ
    # ================================================================
    def _build_grafik(self):
        self.canvas_grafik = ctk.CTkCanvas(
            self.tab_grafik, bg=CLR_BG_DEEP, highlightthickness=0)
        self.canvas_grafik.pack(fill="both", expand=True, padx=10, pady=10)
        self.canvas_grafik.bind("<Configure>",
            lambda e: self.after(100, self.hesapla))

    # ================================================================
    # SEKME 6 — PARAMETRİK TARAMA
    # ================================================================
    def _build_tarama(self):
        ana = ctk.CTkFrame(self.tab_tarama, fg_color=CLR_BG_PANEL)
        ana.pack(fill="both", expand=True, padx=6, pady=6)
        ctk.CTkLabel(ana, text="PARAMETRİK ALAN TARAMASI",
                     font=("Arial", 13, "bold"), text_color=CLR_CYAN).pack(pady=(12, 4))
        kontrol = ctk.CTkFrame(ana, fg_color="transparent")
        kontrol.pack(fill="x", padx=14, pady=4)
        for label, attr, default, width in [
            ("A min [m²]:", "ent_tar_min", "0.2", 70),
            ("A max [m²]:", "ent_tar_max", "3.0", 70),
            ("Adım sayısı:", "ent_tar_adim", "20", 60),
        ]:
            ctk.CTkLabel(kontrol, text=label, font=("Arial", 11),
                         text_color=CLR_TEXT_SEC).pack(side="left", padx=(0, 4))
            ent = ctk.CTkEntry(kontrol, width=width, fg_color=CLR_BG_INPUT,
                               border_color=CLR_BORDER, text_color=CLR_TEXT_PRI)
            ent.insert(0, default)
            ent.pack(side="left", padx=(0, 12))
            setattr(self, attr, ent)
        ctk.CTkButton(
            kontrol, text="Taramayı Başlat",
            font=("Arial", 12, "bold"), fg_color=CLR_CYAN,
            hover_color="#3bbbd4", text_color="#0d1117",
            command=self._tarama_yap).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            kontrol, text="Rapor Kaydet (.txt)",
            font=("Arial", 12), fg_color="#1c2a1a",
            hover_color="#243522", text_color=CLR_GREEN,
            border_color=CLR_GREEN, border_width=1,
            command=self._tarama_rapor).pack(side="left")
        self.frm_tablo = ctk.CTkScrollableFrame(
            ana, fg_color=CLR_BG_PANEL, scrollbar_button_color=CLR_BORDER)
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
            cp_e = self._get_egzoz_cp()
            cp_s = self.sogutucu_db[self.combo_sogutucu.get()]
            m_s  = float(self.ent_deb_s.get())
            akis = self.combo_akis.get()
        except Exception:
            messagebox.showerror("Tarama Hatası", "Simülasyon parametrelerini kontrol edin.")
            return
        C_e=m_e*cp_e; C_s=m_s*cp_s; C_min=min(C_e,C_s); C_r=C_min/max(C_e,C_s)
        for i in range(n_adim):
            A   = A_min + (A_max - A_min)*i/(n_adim-1)
            NTU = U*A/C_min; eps=_ntu_eps(NTU,C_r,akis)
            q   = eps*C_min*(T_ei-T_si); Teo=T_ei-q/C_e; Tso=T_si+q/C_s
            self._tarama_data.append([A, NTU, eps*100, q/1000, Teo, Tso])
            renk = CLR_RED if Teo>190 else (CLR_GREEN if Teo>110 else CLR_AMBER)
            satir = ctk.CTkFrame(self.frm_tablo,
                                 fg_color=CLR_BG_CARD if i%2==0 else CLR_BG_INPUT,
                                 corner_radius=4)
            satir.pack(fill="x", pady=1)
            for deger, w in [(f"{A:.3f}",140),(f"{NTU:.3f}",100),
                             (f"{eps*100:.1f}",130),(f"{q/1000:.2f}",120),
                             (f"{Teo:.1f}",160),(f"{Tso:.1f}",160)]:
                ctk.CTkLabel(satir, text=deger, font=("Courier New", 11),
                             text_color=renk, width=w, anchor="center").pack(side="left", padx=2)
            self._tarama_satirlar.append(satir)

    def _tarama_rapor(self):
        if not self._tarama_data:
            messagebox.showwarning("Uyarı", "Önce tarama yapın.")
            return
        dosya = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Metin Dosyası", "*.txt")],
            title="Tarama Sonuçlarını Kaydet")
        if not dosya: return
        baslik = f"{'Alan [m²]':>12}  {'NTU':>10}  {'ε [%]':>10}  {'q [kW]':>10}  {'T_egzoz [°C]':>14}  {'T_sıvı [°C]':>12}"
        ayirici = "-" * len(baslik)
        satirlar = [
            "=" * 70,
            "   EGR Lab v6.0 — PARAMETRİK ALAN TARAMASI RAPORU",
            "=" * 70,
            baslik, ayirici,
        ]
        for row in self._tarama_data:
            satirlar.append(
                f"{row[0]:>12.3f}  {row[1]:>10.3f}  {row[2]:>10.1f}  "
                f"{row[3]:>10.2f}  {row[4]:>14.1f}  {row[5]:>12.1f}"
            )
        satirlar += [ayirici, ""]
        with open(dosya, "w", encoding="utf-8") as f:
            f.write("\n".join(satirlar))
        messagebox.showinfo("Başarılı", f"Rapor kaydedildi:\n{dosya}")

    # ================================================================
    # TERMAL SİMÜLASYON MOTORU
    # ================================================================
    def hesapla(self, hafizaya_yaz=True):
        try:
            akis = self.combo_akis.get()
            so_adi = self.combo_sogutucu.get()
            cp_s = self.sogutucu_db[so_adi]
            cp_e = self._get_egzoz_cp()
            m_e  = float(self.ent_deb_e.get())
            T_ei = float(self.ent_temp_ei.get())
            m_s  = float(self.ent_deb_s.get())
            T_si = float(self.ent_temp_si.get())
            U    = float(self.ent_U.get())
            A    = self.slider.get()
            if m_e<=0 or m_s<=0 or U<=0 or A<=0:
                raise ValueError("Debi, U ve Alan > 0 olmalı.")
            yakit_bilgi = self.combo_yakit.get() if hasattr(self,"combo_yakit") else "—"
            if hafizaya_yaz:
                self._gecmise_ekle([akis, so_adi, m_e, T_ei, m_s, T_si, U, A])
            C_e=m_e*cp_e; C_s=m_s*cp_s; C_min=min(C_e,C_s); C_max=max(C_e,C_s)
            C_r=C_min/C_max; NTU=U*A/C_min; eps=_ntu_eps(NTU,C_r,akis)
            if abs(T_ei-T_si)<1e-6: raise ValueError("Giriş sıcaklıkları eşit.")
            q_max=C_min*(T_ei-T_si); q=eps*q_max
            T_eo=T_ei-q/C_e; T_so=T_si+q/C_s
            if "Zıt" in akis:
                dt1,dt2=T_ei-T_so,T_eo-T_si
            else:
                dt1,dt2=T_ei-T_si,T_eo-T_so
            if dt1>0 and dt2>0 and abs(dt1-dt2)>1e-6:
                LMTD=(dt1-dt2)/math.log(dt1/dt2)
            elif dt1<=0 or dt2<=0:
                LMTD=float("nan")
            else:
                LMTD=(dt1+dt2)/2.0
            # Kartları güncelle
            self.sr_akis.set(akis)
            self.sr_sog.set(so_adi)
            self.sr_yakit_bilgi.set(yakit_bilgi[:40] + "..." if len(yakit_bilgi) > 43 else yakit_bilgi)
            self.sr_A.set(f"{A:.4f} m²")
            self.sr_U.set(f"{U:.1f} W/m²K")
            self.sr_LMTD.set(
                "NaN — negatif ΔT!" if math.isnan(LMTD) else f"{LMTD:.2f} °C",
                renk=CLR_RED if math.isnan(LMTD) else CLR_TEXT_PRI)
            self.sr_NTU.set(f"{NTU:.4f}")
            self.sr_Tei.set(f"{T_ei:.1f} °C")
            self.sr_Teo.set(f"{T_eo:.2f} °C")
            self.sr_Tsi.set(f"{T_si:.1f} °C")
            self.sr_Tso.set(f"{T_so:.2f} °C")
            self.sr_q.set(f"{q/1000:.2f} kW")
            eps_renk=CLR_GREEN if eps>=0.6 else (CLR_AMBER if eps>=0.4 else CLR_RED)
            self.sr_eps.set(f"% {eps*100:.2f}", renk=eps_renk)
            if T_eo>190:
                self.lbl_durum.configure(fg_color="#3a0f0a", text_color=CLR_RED,
                    text="⚠  KRİTİK: Egzoz yeterince soğutulamıyor → Alanı büyütün")
            elif 110<=T_eo<=190:
                self.lbl_durum.configure(fg_color="#0f2a1a", text_color=CLR_GREEN,
                    text="✅  İDEAL TASARIM: Optimum emisyon ve soğutma dengesi sağlandı")
            else:
                self.lbl_durum.configure(fg_color="#2a1f0a", text_color=CLR_AMBER,
                    text="⚠  YOĞUŞMA ALARMI: Çıkış çok soğuk — asit/kurum birikimi riski")
            self.son_rapor = {
                "akis": akis, "sogutucu": so_adi, "yakit": yakit_bilgi,
                "m_e": m_e, "T_ei": T_ei, "m_s": m_s, "T_si": T_si,
                "U": U, "A": A, "T_eo": T_eo, "T_so": T_so,
                "q_kw": q/1000, "eps": eps*100, "LMTD": LMTD, "NTU": NTU,
            }
            self._sema_ciz(T_ei, T_si, T_eo, T_so, akis)
            self._grafik_ciz(T_ei, T_eo, T_si, T_so, NTU, A, C_r, q_max, C_e, U, C_min, akis)
        except (ValueError, ZeroDivisionError) as e:
            self.lbl_durum.configure(fg_color="#3a0f0a", text_color=CLR_RED,
                                     text=f"⛔  GİRDİ HATASI: {e}")
        except Exception as e:
            self.lbl_durum.configure(fg_color="#3a0f0a", text_color=CLR_RED,
                                     text=f"⛔  HATA: {e}")

    # ================================================================
    # ŞEMATİK — Silindirik gövde + sıcaklık gradyanı
    # ================================================================
    def _sema_ciz(self, T_ei, T_si, T_eo, T_so, akis):
        c = self.canvas_sema
        c.delete("all")
        W = c.winfo_width() or 760
        H = c.winfo_height() or 220

        # Koordinatlar
        cx1 = int(W * 0.14)   # gövde sol
        cx2 = int(W * 0.86)   # gövde sağ
        cy  = H // 2           # orta aks
        ry  = int(H * 0.28)    # silindir yarı yüksekliği
        re  = int(H * 0.10)    # elips derinliği (perspektif)

        # ── Gradyan gövde (sıcaktan soğuğa) ─────────────────────────
        # Benzin: sarı-kırmızı sol, mavi-mor sağ (zıt akış için ters)
        n_slices = 80
        gövde_renkleri = _gradyan_renk(n_slices)

        for i in range(n_slices):
            x0 = cx1 + (cx2 - cx1) * i // n_slices
            x1 = cx1 + (cx2 - cx1) * (i + 1) // n_slices
            renk = gövde_renkleri[i] if "Zıt" not in akis else gövde_renkleri[n_slices - 1 - i]
            c.create_rectangle(x0, cy - ry, x1, cy + ry, fill=renk, outline="")

        # Sol kapak (elips)
        c.create_oval(cx1 - re, cy - ry, cx1 + re, cy + ry,
                      fill="#b0450a", outline="#d06020", width=2)
        # Sağ kapak (elips)
        c.create_oval(cx2 - re, cy - ry, cx2 + re, cy + ry,
                      fill="#1a3a8a", outline="#2050cc", width=2)

        # Gövde çevresi
        c.create_line(cx1, cy - ry, cx2, cy - ry, fill="#444", width=2)
        c.create_line(cx1, cy + ry, cx2, cy + ry, fill="#444", width=2)

        # Kesikli merkez çizgisi
        for xi in range(cx1 + 20, cx2 - 20, 20):
            c.create_line(xi, cy, xi + 10, cy, fill="#555", width=1)

        # ── Egzoz giriş ok (sol) ─────────────────────────────────────
        arr_x = cx1 - re
        c.create_line(int(W * 0.04), cy, arr_x, cy,
                      fill=CLR_EGZOZ, width=6, arrow="last", arrowshape=(14, 16, 6))
        # Nozzle silindir
        c.create_rectangle(int(W * 0.04) - 4, cy - 10,
                           int(W * 0.04) + 14, cy + 10, fill="#888", outline="#aaa")
        c.create_text(int(W * 0.04) + 5, cy - 22,
                      text="Egzoz Giriş", fill=CLR_EGZOZ, font=("Arial", 9, "bold"))
        c.create_text(int(W * 0.04) + 5, cy - 10,
                      text=f"{T_ei:.0f} °C", fill=CLR_EGZOZ, font=("Arial", 10, "bold"))

        # ── Egzoz çıkış ok (sağ) ─────────────────────────────────────
        c.create_line(cx2 + re, cy, int(W * 0.96), cy,
                      fill=CLR_AMBER, width=6, arrow="last", arrowshape=(14, 16, 6))
        c.create_rectangle(int(W * 0.96) - 14, cy - 10,
                           int(W * 0.96) + 4, cy + 10, fill="#888", outline="#aaa")
        c.create_text(int(W * 0.96) - 5, cy - 22,
                      text="Egzoz Çıkış", fill=CLR_AMBER, font=("Arial", 9, "bold"))
        c.create_text(int(W * 0.96) - 5, cy - 10,
                      text=f"{T_eo:.0f} °C", fill=CLR_AMBER, font=("Arial", 10, "bold"))

        # ── Sıvı bağlantıları (üstten/alttan nozzle) ─────────────────
        noz_x1 = cx1 + int((cx2 - cx1) * 0.25)
        noz_x2 = cx1 + int((cx2 - cx1) * 0.75)

        if "Zıt" in akis:
            # Sıvı giriş: sağ alt
            c.create_rectangle(noz_x2 - 8, cy + ry, noz_x2 + 8, cy + ry + 16,
                               fill="#888", outline="#aaa")
            c.create_line(noz_x2, cy + ry + 28, noz_x2, cy + ry + 2,
                          fill=CLR_SIVI, width=5, arrow="last", arrowshape=(12, 14, 5))
            c.create_text(noz_x2, cy + ry + 36,
                          text=f"Sıvı Giriş  {T_si:.0f}°C",
                          fill=CLR_SIVI, font=("Arial", 9, "bold"))
            # Sıvı çıkış: sol üst
            c.create_rectangle(noz_x1 - 8, cy - ry - 16, noz_x1 + 8, cy - ry,
                               fill="#888", outline="#aaa")
            c.create_line(noz_x1, cy - ry - 2, noz_x1, cy - ry - 28,
                          fill=CLR_CYAN, width=5, arrow="last", arrowshape=(12, 14, 5))
            c.create_text(noz_x1, cy - ry - 36,
                          text=f"Sıvı Çıkış  {T_so:.0f}°C",
                          fill=CLR_CYAN, font=("Arial", 9, "bold"))
            c.create_text((cx1+cx2)//2, H - 12,
                          text="⟵  ZIT AKIŞ (COUNTER-FLOW)",
                          fill=CLR_SIVI, font=("Arial", 9, "bold"))
        else:
            # Sıvı giriş: sol üst
            c.create_rectangle(noz_x1 - 8, cy - ry - 16, noz_x1 + 8, cy - ry,
                               fill="#888", outline="#aaa")
            c.create_line(noz_x1, cy - ry - 28, noz_x1, cy - ry - 2,
                          fill=CLR_SIVI, width=5, arrow="last", arrowshape=(12, 14, 5))
            c.create_text(noz_x1, cy - ry - 36,
                          text=f"Sıvı Giriş  {T_si:.0f}°C",
                          fill=CLR_SIVI, font=("Arial", 9, "bold"))
            # Sıvı çıkış: sağ alt
            c.create_rectangle(noz_x2 - 8, cy + ry, noz_x2 + 8, cy + ry + 16,
                               fill="#888", outline="#aaa")
            c.create_line(noz_x2, cy + ry + 2, noz_x2, cy + ry + 28,
                          fill=CLR_CYAN, width=5, arrow="last", arrowshape=(12, 14, 5))
            c.create_text(noz_x2, cy + ry + 36,
                          text=f"Sıvı Çıkış  {T_so:.0f}°C",
                          fill=CLR_CYAN, font=("Arial", 9, "bold"))
            c.create_text((cx1+cx2)//2, H - 12,
                          text="⟶  PARALEL AKIŞ (CO-CURRENT)",
                          fill=CLR_EGZOZ, font=("Arial", 9, "bold"))

        # Başlık
        c.create_text((cx1+cx2)//2, cy,
                      text="EGR BUNDLE COOLER",
                      fill="white", font=("Arial", 11, "bold"))

    # ================================================================
    # GRAFİK PANELİ — Kitaptaki gibi eğri profil + eksenler
    # ================================================================
    def _grafik_ciz(self, T_ei, T_eo, T_si, T_so, NTU, A,
                    C_r, q_max, C_e, U, C_min, akis):
        c = self.canvas_grafik
        c.delete("all")
        W = c.winfo_width() or 1100
        H = c.winfo_height() or 580
        if W < 200 or H < 200:
            return

        PAD_L, PAD_R = 72, 28
        PAD_T, PAD_B = 52, 52
        GAP  = 36
        g_w  = (W - PAD_L - PAD_R - 2 * GAP) // 3
        g_h  = H - PAD_T - PAD_B
        y_bot = PAD_T + g_h

        def eksen_kutu(ox, baslik, x_label, y_label,
                       x_min, x_max, y_min, y_max, n_tick=5):
            """Tam etiketli, ızgaralı eksen kutusu. Koordinat fonksiyonlarını döndürür."""
            ex = ox + g_w
            # Başlık
            c.create_text(ox + g_w//2, PAD_T - 32,
                          text=baslik, fill=CLR_TEXT_PRI, font=("Arial", 10, "bold"))
            # Ok eksenler
            c.create_line(ox, y_bot, ex+8, y_bot, fill=CLR_TEXT_SEC, width=1,
                          arrow="last", arrowshape=(8,10,3))
            c.create_line(ox, y_bot, ox, PAD_T-8, fill=CLR_TEXT_SEC, width=1,
                          arrow="last", arrowshape=(8,10,3))
            # Eksen etiketleri
            c.create_text(ox + g_w//2, H - 14,
                          text=x_label, fill=CLR_TEXT_SEC, font=("Arial", 9))
            c.create_text(ox - 54, PAD_T + g_h//2,
                          text=y_label, fill=CLR_TEXT_SEC, font=("Arial", 9), angle=90)

            x_span = (x_max - x_min) or 1
            y_span = (y_max - y_min) or 1

            def tx(x): return ox + (x - x_min) / x_span * g_w
            def ty(y): return y_bot - (y - y_min) / y_span * g_h

            # Y tick + ızgara
            for i in range(n_tick + 1):
                yv = y_min + y_span * i / n_tick
                yp = ty(yv)
                c.create_line(ox - 4, yp, ex, yp, fill=CLR_BG_CARD, width=1)
                c.create_line(ox - 4, yp, ox + 4, yp, fill=CLR_TEXT_SEC, width=1)
                c.create_text(ox - 8, yp, text=f"{yv:.0f}",
                              fill=CLR_TEXT_MUT, font=("Arial", 8), anchor="e")
            # X tick
            for i in range(n_tick + 1):
                xv = x_min + x_span * i / n_tick
                xp = tx(xv)
                c.create_line(xp, y_bot + 4, xp, PAD_T, fill=CLR_BG_CARD, width=1)
                c.create_line(xp, y_bot, xp, y_bot + 4, fill=CLR_TEXT_SEC, width=1)
                c.create_text(xp, y_bot + 12, text=f"{xv:.2f}",
                              fill=CLR_TEXT_MUT, font=("Arial", 8), anchor="n")
            return tx, ty, ex

        # ── GRAFIK 1: Sıcaklık Profili (kitaptaki eğrili profil) ─────
        ox1 = PAD_L
        all_T = [T_ei, T_eo, T_si, T_so]
        T_min = min(all_T) - 20
        T_max = max(all_T) + 40
        tx1, ty1, ex1 = eksen_kutu(
            ox1, "Sıcaklık Profili", "Uzunluk  L →", "Sıcaklık [°C]",
            0, 1, T_min, T_max, n_tick=5)

        # Egzoz eğrisi (exponential decay kitaptaki gibi)
        def exp_curve(T_a, T_b, renk, genislik=2, n=60, reverse=False):
            """Exponential sıcaklık profili çizgisi"""
            pts = []
            for i in range(n + 1):
                t_norm = i / n
                # Üstel yaklaşım: T(x) = T_b + (T_a - T_b)*exp(-3*x)
                T_val = T_b + (T_a - T_b) * math.exp(-3.0 * t_norm)
                x_val = t_norm
                if reverse:
                    x_val = 1.0 - t_norm
                    T_val = T_b + (T_a - T_b) * math.exp(-3.0 * (1 - x_val))
                pts.append((tx1(x_val), ty1(T_val)))
            for i in range(len(pts) - 1):
                c.create_line(pts[i][0], pts[i][1],
                              pts[i+1][0], pts[i+1][1],
                              fill=renk, width=genislik, smooth=True)
            return pts

        # Egzoz: T_ei → T_eo (soldan sağa)
        eg_pts = exp_curve(T_ei, T_eo, CLR_EGZOZ, genislik=3)
        # Sıvı: zıt akışta T_so → T_si (soldan sağa), paralel'de T_si → T_so
        if "Zıt" in akis:
            sv_pts = exp_curve(T_so, T_si, CLR_SIVI, genislik=3, reverse=False)
        else:
            sv_pts = exp_curve(T_si, T_so, CLR_SIVI, genislik=3)

        # Akış yönü okları çizgi üzerinde (kitaptaki gibi)
        mid = len(eg_pts) // 2
        if mid > 0:
            dx = eg_pts[mid][0] - eg_pts[mid-1][0]
            dy = eg_pts[mid][1] - eg_pts[mid-1][1]
            _ok_ciz(c, eg_pts[mid][0], eg_pts[mid][1], dx, dy, CLR_EGZOZ)
        if "Zıt" in akis:
            mid2 = len(sv_pts) // 2
            dx2 = sv_pts[mid2-1][0] - sv_pts[mid2][0]
            dy2 = sv_pts[mid2-1][1] - sv_pts[mid2][1]
            _ok_ciz(c, sv_pts[mid2][0], sv_pts[mid2][1], dx2, dy2, CLR_SIVI)
        else:
            mid2 = len(sv_pts) // 2
            dx2 = sv_pts[mid2][0] - sv_pts[mid2-1][0]
            dy2 = sv_pts[mid2][1] - sv_pts[mid2-1][1]
            _ok_ciz(c, sv_pts[mid2][0], sv_pts[mid2][1], dx2, dy2, CLR_SIVI)

        # Kenar sıcaklık etiketleri (T_h1, T_h2, T_c1, T_c2 stilinde)
        def T_etiket(x, y, text, renk, anchor="w", dy=-14):
            c.create_text(x, y + dy, text=text, fill=renk,
                          font=("Arial", 9, "bold"), anchor=anchor)

        T_etiket(tx1(0)-4, ty1(T_ei), f"T_h1={T_ei:.0f}°C", CLR_EGZOZ, anchor="e", dy=0)
        T_etiket(ex1+4,    ty1(T_eo), f"T_h2={T_eo:.0f}°C", CLR_AMBER, anchor="w", dy=0)
        if "Zıt" in akis:
            T_etiket(tx1(0)-4, ty1(T_so), f"T_c1={T_so:.0f}°C", CLR_SIVI,  anchor="e", dy=0)
            T_etiket(ex1+4,    ty1(T_si), f"T_c2={T_si:.0f}°C", CLR_CYAN,  anchor="w", dy=0)
        else:
            T_etiket(tx1(0)-4, ty1(T_si), f"T_c1={T_si:.0f}°C", CLR_SIVI,  anchor="e", dy=0)
            T_etiket(ex1+4,    ty1(T_so), f"T_c2={T_so:.0f}°C", CLR_CYAN,  anchor="w", dy=0)

        # Legend
        c.create_line(ox1+8, PAD_T+10, ox1+30, PAD_T+10, fill=CLR_EGZOZ, width=3)
        c.create_text(ox1+34, PAD_T+10, text="Egzoz (Sıcak)", fill=CLR_EGZOZ,
                      font=("Arial", 8), anchor="w")
        c.create_line(ox1+8, PAD_T+22, ox1+30, PAD_T+22, fill=CLR_SIVI, width=3)
        c.create_text(ox1+34, PAD_T+22, text="Soğutucu (Soğuk)", fill=CLR_SIVI,
                      font=("Arial", 8), anchor="w")
        akis_adi = "Zıt Akış" if "Zıt" in akis else "Paralel Akış"
        c.create_text(ox1+g_w//2, PAD_T+34, text=akis_adi,
                      fill=CLR_TEXT_MUT, font=("Arial", 8, "italic"))

        # ── GRAFIK 2: NTU → T_egzoz çıkış ──────────────────────────
        ox2  = ex1 + GAP
        ntu_max = max(NTU * 2.2, 5.0)
        T_eo_min = T_si - 5
        T_eo_max = T_ei + 5
        tx2, ty2, ex2 = eksen_kutu(
            ox2, "NTU — Egzoz Çıkış Sıcaklığı",
            "NTU  [-]", "T_egzoz_çıkış [°C]",
            0, ntu_max, T_eo_min, T_eo_max, n_tick=5)

        ntu_pts = []
        for i in range(61):
            nt = ntu_max * i / 60
            ep = _ntu_eps(nt, C_r, akis)
            te = T_ei - (ep * q_max / C_e)
            te = max(T_eo_min, min(T_eo_max, te))
            ntu_pts.append((tx2(nt), ty2(te)))
        for i in range(len(ntu_pts) - 1):
            c.create_line(ntu_pts[i][0], ntu_pts[i][1],
                          ntu_pts[i+1][0], ntu_pts[i+1][1],
                          fill=CLR_GREEN, width=2)

        # Mevcut NTU çizgisi + değer etiketi
        cur_ntu_x = tx2(min(NTU, ntu_max))
        cur_teo_y = ty2(max(T_eo_min, min(T_eo_max, T_eo)))
        c.create_line(cur_ntu_x, y_bot, cur_ntu_x, PAD_T,
                      fill=CLR_AMBER, dash=(6, 4), width=1)
        c.create_line(ox2, cur_teo_y, ex2, cur_teo_y,
                      fill=CLR_AMBER, dash=(6, 4), width=1)
        c.create_oval(cur_ntu_x-5, cur_teo_y-5,
                      cur_ntu_x+5, cur_teo_y+5, fill=CLR_AMBER, outline="")
        c.create_text(cur_ntu_x + 6, cur_teo_y - 12,
                      text=f"NTU={NTU:.2f}\nT_eo={T_eo:.1f}°C",
                      fill=CLR_AMBER, font=("Arial", 8, "bold"), anchor="w")

        # ── GRAFIK 3: Alan → Isı Gücü ───────────────────────────────
        ox3    = ex2 + GAP
        a_max  = max(A * 2.5, 3.5)
        q_lim  = max(q_max / 1000 * 1.15, 1.0)
        tx3, ty3, ex3 = eksen_kutu(
            ox3, "Yüzey Alanı — Isı Gücü",
            "Alan A [m²]", "q [kW]",
            0, a_max, 0, q_lim, n_tick=5)

        alan_pts = []
        for i in range(61):
            at  = a_max * i / 60
            nt  = U * at / C_min if C_min > 0 else 0
            ep  = _ntu_eps(nt, C_r, akis)
            qk  = ep * q_max / 1000
            qk  = max(0, min(q_lim, qk))
            alan_pts.append((tx3(at), ty3(qk)))
        for i in range(len(alan_pts) - 1):
            c.create_line(alan_pts[i][0], alan_pts[i][1],
                          alan_pts[i+1][0], alan_pts[i+1][1],
                          fill=CLR_PURPLE, width=2)

        # Mevcut alan + q değer etiketi
        cur_ax = tx3(min(A, a_max))
        cur_qy = ty3(max(0, min(q_lim, (eps := _ntu_eps(U*A/C_min, C_r, akis)) * q_max / 1000)))
        c.create_line(cur_ax, y_bot, cur_ax, PAD_T,
                      fill=CLR_CYAN, dash=(6, 4), width=1)
        c.create_line(ox3, cur_qy, ex3, cur_qy,
                      fill=CLR_CYAN, dash=(6, 4), width=1)
        c.create_oval(cur_ax-5, cur_qy-5, cur_ax+5, cur_qy+5,
                      fill=CLR_CYAN, outline="")
        q_val = _ntu_eps(U*A/C_min, C_r, akis) * q_max / 1000
        c.create_text(cur_ax + 6, cur_qy - 12,
                      text=f"A={A:.2f} m²\nq={q_val:.1f} kW",
                      fill=CLR_CYAN, font=("Arial", 8, "bold"), anchor="w")

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
        self.btn_ileri.configure(state="normal" if self.gec_idx < len(self.gecmis)-1 else "disabled")

    def _yukle(self, idx):
        v = self.gecmis[idx]
        self.combo_akis.set(v[0]); self.combo_sogutucu.set(v[1])
        for ent, val in zip(
            [self.ent_deb_e, self.ent_temp_ei, self.ent_deb_s,
             self.ent_temp_si, self.ent_U], v[2:7]):
            ent.delete(0, "end"); ent.insert(0, str(val))
        self.slider.set(v[7])
        self.lbl_slider.configure(text=f"Alan: {v[7]:.2f} m²")
        self.hesapla(hafizaya_yaz=False)

    def _geri(self):
        if self.gec_idx > 0:
            self.gec_idx -= 1; self._yukle(self.gec_idx); self._btn_guncelle()

    def _ileri(self):
        if self.gec_idx < len(self.gecmis) - 1:
            self.gec_idx += 1; self._yukle(self.gec_idx); self._btn_guncelle()

    # ================================================================
    # RAPORLAMA
    # ================================================================
    def _rapor_kaydet(self):
        if not self.son_rapor:
            messagebox.showwarning("Uyarı", "Önce simülasyon çalıştırın.")
            return
        dosya = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Metin Dosyası", "*.txt")],
            title="Termal Simülasyon Raporunu Kaydet")
        if not dosya: return
        r = self.son_rapor
        lmtd_str = "NaN (negatif ΔT)" if math.isnan(r["LMTD"]) else f"{r['LMTD']:.2f} °C"

        # Motor çevrim bilgisi de dahil et
        motor_blok = ""
        if self.motor_sonuc:
            mr = self.motor_sonuc
            motor_blok = (
                " [0] MOTOR ÇEVRİMİ (Kaynak)\n"
                + "-" * 70 + "\n"
                f" Çevrim Tipi        : {mr['cevrim']}\n"
                f" Fren Gücü P_b      : {mr['P_b']:.2f} kW\n"
                f" Termal Verim η_t   : % {mr['eta_t']*100:.2f}\n"
                f" Motor T₄           : {mr['T4']-273.15:.1f} °C\n"
                f" Egzoz T_ex         : {mr['Tex']-273.15:.1f} °C  ← EGR Cooler girişi\n\n"
            )

        metin = (
            "=" * 70 + "\n"
            "       EGR COOLER TERMAL MÜHENDİSLİK VE AR-GE ANALİZ RAPORU\n"
            "=" * 70 + "\n"
            f" Geliştiren : Enes Çelik Simülasyon Sistemleri  |  v6.0\n"
            + "-" * 70 + "\n\n"
            + motor_blok +
            " [1] SİSTEM VE AKIŞKAN ÖZELLİKLERİ\n"
            + "-" * 70 + "\n"
            f" Akış Tipi              : {r['akis']}\n"
            f" Soğutucu Akışkan       : {r['sogutucu']}\n"
            f" Yakıt / Egzoz          : {r['yakit']}\n\n"
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
            "                   RAPOR SONU\n"
            "=" * 70 + "\n"
        )
        with open(dosya, "w", encoding="utf-8") as f:
            f.write(metin)
        messagebox.showinfo("Başarılı", f"Rapor kaydedildi:\n{dosya}")


# ────────────────────────────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ────────────────────────────────────────────────────────────────────
def _ntu_eps(NTU: float, C_r: float, akis: str) -> float:
    if "Zıt" in akis:
        if abs(C_r - 1.0) < 1e-9:
            eps = NTU / (1.0 + NTU)
        else:
            num = 1.0 - math.exp(-NTU * (1.0 - C_r))
            den = 1.0 - C_r * math.exp(-NTU * (1.0 - C_r))
            eps = num / den
    else:
        if abs(C_r - 1.0) < 1e-9:
            eps = (1.0 - math.exp(-2.0 * NTU)) / 2.0
        else:
            eps = (1.0 - math.exp(-NTU * (1.0 + C_r))) / (1.0 + C_r)
    return min(max(eps, 0.0), 1.0)


def _olustur_uyarilar(Re, v, dP, h_ic, U, T_eo, eps):
    items = []
    if Re < 2300:
        items.append(("⚠", f"LAMİNER AKIŞ (Re={Re:.0f}): Isı transferi zayıf. "
                           "Re > 4000 hedefleyin.", CLR_AMBER))
    elif Re < 4000:
        items.append(("⚠", f"GEÇİŞ BÖLGESİ (Re={Re:.0f}): Akış kararsız.", CLR_AMBER))
    else:
        items.append(("✅", f"TÜRBÜLANSLÜ AKIŞ (Re={Re:.0f}): İdeal.", CLR_GREEN))
    if v > 30:
        items.append(("⚠", f"YÜKSEK HIZ: v={v:.1f} m/s → Erozyon riski.", CLR_RED))
    if dP > 5000:
        items.append(("⚠", f"YÜKSEK ΔP: {dP:.0f} Pa → EGR geri basıncını artırır.", CLR_AMBER))
    if h_ic < U * 0.5:
        items.append(("⚠", f"h_iç ({h_ic:.0f}) << U ({U:.0f}): İç direnç baskın.", CLR_RED))
    if T_eo < 90:
        items.append(("⚠", "YOĞUŞMA RİSKİ: T_egzoz_çıkış < 90 °C", CLR_RED))
    if eps < 0.5:
        items.append(("⚠", f"DÜŞÜK ETKİNLİK: ε={eps*100:.1f}% → Alan artırılmalı.", CLR_AMBER))
    if not items:
        items.append(("✅", "Tüm parametreler kabul edilebilir aralıkta.", CLR_GREEN))
    return items


def _gradyan_renk(n):
    """Sarı-kırmızı-mor-mavi sıcaktan soğuğa gradyan listesi"""
    stops = [
        (0.00, (255, 240,  0)),   # sarı
        (0.25, (255, 120,  0)),   # turuncu
        (0.50, (220,  40, 20)),   # kırmızı
        (0.75, (130,  30,160)),   # mor
        (1.00, ( 30,  80,200)),   # mavi
    ]
    renkler = []
    for i in range(n):
        t = i / (n - 1)
        for j in range(len(stops) - 1):
            t0, c0 = stops[j];  t1, c1 = stops[j+1]
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0)
                r = int(c0[0] + (c1[0]-c0[0])*f)
                g = int(c0[1] + (c1[1]-c0[1])*f)
                b = int(c0[2] + (c1[2]-c0[2])*f)
                renkler.append(f"#{r:02x}{g:02x}{b:02x}")
                break
    return renkler


def _ok_ciz(c, x, y, dx, dy, renk, boyut=8):
    """Çizgi üzerine yön oku ekler"""
    uzunluk = math.sqrt(dx*dx + dy*dy)
    if uzunluk < 1e-6: return
    ux, uy = dx/uzunluk, dy/uzunluk
    px, py = -uy, ux
    x1 = x - ux*boyut + px*boyut*0.4
    y1 = y - uy*boyut + py*boyut*0.4
    x2 = x - ux*boyut - px*boyut*0.4
    y2 = y - uy*boyut - py*boyut*0.4
    c.create_polygon(x, y, x1, y1, x2, y2, fill=renk, outline="")


# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = EGRLab()
    app.mainloop()
