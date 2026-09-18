import configparser
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

APP_TITLE = "APEX 5 · FH6 Adaptive Trigger Bridge"
# In a PyInstaller one-file build, __file__ points into the temporary
# extraction directory. Runtime files (profiles, logs, bridge EXE) must
# instead live beside the GUI EXE.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent
PROFILES_DIR = BASE_DIR / "profiles"
STATE_PATH = BASE_DIR / "telemetry_state.json"
LOG_PATH = BASE_DIR / "bridge_gui.log"
UI_STATE_PATH = BASE_DIR / "ui_state.json"
PROFILE_NAMES = ["soft", "medium", "hard"]
SECTIONS = ["resistance", "vibration", "road", "recoil"]

LABELS = {
    "profile.name": "Имя профиля",
    "resistance.gas_base": "RT · базовое сопротивление",
    "resistance.gas_input": "RT · от нажатия газа",
    "resistance.gas_rpm": "RT · от RPM",
    "resistance.brake_base": "LT · базовое сопротивление",
    "resistance.brake_input": "LT · от нажатия тормоза",
    "resistance.brake_abs": "LT · добавка ABS",
    "resistance.handbrake_max": "LT · handbrake максимум",
    "vibration.r2_max_strength": "RT · сила вибрации",
    "vibration.l2_max_strength": "LT · сила вибрации",
    "vibration.r2_duty": "RT · duty",
    "vibration.l2_duty": "LT · duty",
    "vibration.r2_pressure": "RT · pressure",
    "vibration.l2_pressure": "LT · pressure",
    "vibration.r2_freq_min": "RT · частота min",
    "vibration.r2_freq_max": "RT · частота max",
    "vibration.l2_freq_min": "LT · ABS частота min",
    "vibration.l2_freq_max": "LT · ABS частота max",
    "road.max_strength": "Road · максимум",
    "road.drift_reduction": "Road · подавление в дрифте",
    "road.drift_multiplier": "Road · остаток в дрифте",
    "road.airborne_multiplier": "Road · сила в воздухе",
    "road.road_speed_scale": "Road · масштаб скорости",
    "road.airborne_susp_low": "Road · airborne low",
    "road.airborne_susp_high": "Road · airborne high",
    "road.airborne_wheel_votes": "Road · wheel votes",
    "recoil.enabled": "Recoil · включён",
    "recoil.brake_threshold": "Recoil · порог тормоза",
    "recoil.abs_threshold": "Recoil · порог ABS",
    "recoil.strength": "Recoil · сила",
    "recoil.stroke": "Recoil · ход",
    "recoil.cooldown_ms": "Recoil · cooldown, ms",
}

DARK = {
    "bg": "#080A0D",
    "surface": "#101318",
    "surface2": "#151A20",
    "surface3": "#1A2028",
    "border": "#202731",
    "border2": "#2A3340",
    "fg": "#F4F7FB",
    "muted": "#8893A2",
    "accent": "#6AA8FF",
    "accent2": "#8C7CFF",
    "good": "#4ED28A",
    "warn": "#F2C45B",
    "bad": "#FF6E73",
    "entry": "#0C0F14",
}

LIGHT = {
    "bg": "#F3F5F8",
    "surface": "#FFFFFF",
    "surface2": "#F7F9FC",
    "surface3": "#EEF2F7",
    "border": "#DDE3EA",
    "border2": "#C9D2DD",
    "fg": "#1D2630",
    "muted": "#687585",
    "accent": "#2777E8",
    "accent2": "#735FE8",
    "good": "#258C58",
    "warn": "#A56A00",
    "bad": "#C93636",
    "entry": "#FFFFFF",
}

PROFILE_INFO = {
    "soft": ("Soft", "Лёгкая реакция · комфорт для долгих заездов"),
    "medium": ("Medium", "Сбалансированный вариант для повседневной езды"),
    "hard": ("Hard", "Более плотное сопротивление и выраженная отдача"),
}


def resource_path(name: str) -> Path:
    # Source mode: files live beside the script. Frozen mode: runtime
    # files are shipped beside the EXE in the portable release folder.
    return BASE_DIR / name


def pythonw_path() -> str:
    exe = Path(sys.executable)
    if exe.name.lower() == "python.exe":
        candidate = exe.with_name("pythonw.exe")
        if candidate.exists():
            return str(candidate)
    return str(exe)


def read_ini(path: Path):
    cfg = configparser.ConfigParser()
    cfg.optionxform = str
    cfg.read(path, encoding="utf-8")
    return cfg


def write_ini(cfg, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        cfg.write(f)
    tmp.replace(path)


def profile_path(name: str) -> Path:
    return PROFILES_DIR / f"{name}.ini"


def root_profile_path(name: str) -> Path:
    return BASE_DIR / f"{name}.ini"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1280x840")
        self.root.minsize(1080, 720)
        self.theme_dark = self.load_ui_state().get("dark", True)
        self.colors = DARK if self.theme_dark else LIGHT
        self.proc = None
        self.current_profile = "soft"
        self.entry_vars = {}
        self.status_q = queue.Queue()
        self.sensor_window = None
        self.sensor_labels = {}
        self.log_lines = []
        self.last_state = None
        self.profile_dirty = False
        self.page = "dashboard"
        self._mouse_canvas = None

        self.configure_root()
        self.build_ui()
        self.select_profile("soft")
        self.poll_state()
        self.poll_process()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_ui_state(self):
        try:
            return json.loads(UI_STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save_ui_state(self):
        try:
            UI_STATE_PATH.write_text(json.dumps({"dark": self.theme_dark}, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def configure_root(self):
        c = self.colors
        self.root.configure(bg=c["bg"])
        self.root.option_add("*Font", ("Segoe UI", 10))
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Modern.Vertical.TScrollbar", background=c["surface3"], troughcolor=c["surface"], bordercolor=c["surface"], arrowcolor=c["muted"])
        style.map("Modern.Vertical.TScrollbar", background=[("active", c["border2"])])

    def build_ui(self):
        for child in self.root.winfo_children():
            child.destroy()

        self.root.configure(bg=self.colors["bg"])
        self.main = tk.Frame(self.root, bg=self.colors["bg"])
        self.main.pack(fill="both", expand=True)

        self.build_sidebar()
        self.build_main_area()

    def make_card(self, parent, pad=1):
        return tk.Frame(parent, bg=self.colors["surface"], highlightthickness=1, highlightbackground=self.colors["border"], padx=pad, pady=pad)

    def label(self, parent, text="", size=10, weight="normal", color=None, bg=None, anchor="w"):
        return tk.Label(parent, text=text, font=("Segoe UI", size, weight), fg=color or self.colors["fg"], bg=bg or self.colors["surface"], anchor=anchor)

    def button(self, parent, text, command, accent=False, compact=False):
        c = self.colors
        bg = c["accent"] if accent else c["surface2"]
        fg = "#FFFFFF" if accent else c["fg"]
        active = c["accent2"] if accent else c["surface3"]
        b = tk.Button(parent, text=text, command=command, font=("Segoe UI", 9, "bold" if accent else "normal"), fg=fg, bg=bg, activebackground=active, activeforeground="#FFFFFF" if accent else fg, relief="flat", bd=0, cursor="hand2", padx=12 if not compact else 9, pady=8 if not compact else 6, highlightthickness=0)
        return b

    def build_sidebar(self):
        c = self.colors
        self.sidebar = tk.Frame(self.main, bg=c["surface"], width=250, highlightthickness=1, highlightbackground=c["border"])
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg=c["surface"])
        brand.pack(fill="x", padx=20, pady=(22, 16))
        self.label(brand, "APEX 5", 20, "bold", c["fg"]).pack(anchor="w")
        self.label(brand, "FH6 Adaptive Bridge", 10, "normal", c["muted"]).pack(anchor="w", pady=(2, 0))

        status = tk.Frame(self.sidebar, bg=c["surface2"], highlightthickness=1, highlightbackground=c["border"], padx=12, pady=10)
        status.pack(fill="x", padx=14, pady=(0, 14))
        self.side_status_dot = tk.Label(status, text="●", font=("Segoe UI", 11, "bold"), fg=c["muted"], bg=c["surface2"])
        self.side_status_dot.pack(side="left")
        self.side_status = self.label(status, "Bridge stopped", 9, "bold", c["muted"], c["surface2"])
        self.side_status.pack(side="left", padx=7)

        self.label(self.sidebar, "PROFILES", 9, "bold", c["muted"]).pack(anchor="w", padx=18, pady=(2, 8))
        self.profile_buttons = {}
        for name in PROFILE_NAMES:
            btn = tk.Button(self.sidebar, text="", command=lambda n=name: self.select_profile(n), relief="flat", bd=0, anchor="w", cursor="hand2", padx=14, pady=10, highlightthickness=0)
            btn.pack(fill="x", padx=12, pady=3)
            self.profile_buttons[name] = btn

        tk.Frame(self.sidebar, bg=c["border"], height=1).pack(fill="x", padx=18, pady=16)
        self.label(self.sidebar, "VIEW", 9, "bold", c["muted"]).pack(anchor="w", padx=18, pady=(0, 8))
        self.nav_buttons = {}
        for key, title in (("dashboard", "⌂  Dashboard"), ("tuning", "⚙  Настройка"), ("log", "≡  Log")):
            btn = tk.Button(self.sidebar, text=title, command=lambda k=key: self.show_page(k), relief="flat", bd=0, anchor="w", cursor="hand2", padx=14, pady=10, highlightthickness=0, font=("Segoe UI", 10))
            btn.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[key] = btn

        spacer = tk.Frame(self.sidebar, bg=c["surface"])
        spacer.pack(fill="both", expand=True)
        self.button(self.sidebar, "◐  Тема", self.toggle_theme, compact=True).pack(fill="x", padx=12, pady=(10, 6))
        self.button(self.sidebar, "▣  Сенсоры 2-й монитор", self.open_sensors, compact=True).pack(fill="x", padx=12, pady=6)
        self.button(self.sidebar, "Открыть profiles", self.open_profile_folder, compact=True).pack(fill="x", padx=12, pady=(6, 16))

        self.refresh_sidebar()

    def build_main_area(self):
        c = self.colors
        self.content = tk.Frame(self.main, bg=c["bg"])
        self.content.pack(side="left", fill="both", expand=True)

        header = tk.Frame(self.content, bg=c["bg"])
        header.pack(fill="x", padx=24, pady=(22, 16))
        left = tk.Frame(header, bg=c["bg"])
        left.pack(side="left")
        self.page_title = self.label(left, "Dashboard", 24, "bold", c["fg"], c["bg"])
        self.page_title.pack(anchor="w")
        self.page_subtitle = self.label(left, "Живая телеметрия и состояние адаптивных триггеров", 10, "normal", c["muted"], c["bg"])
        self.page_subtitle.pack(anchor="w", pady=(4, 0))
        right = tk.Frame(header, bg=c["bg"])
        right.pack(side="right")
        self.theme_small = self.button(right, "☾ Темная" if self.theme_dark else "☀ Светлая", self.toggle_theme, compact=True)
        self.theme_small.pack(side="left", padx=(0, 8))
        self.save_btn = self.button(right, "Сохранить профиль", self.save_profile, accent=True, compact=True)
        self.save_btn.pack(side="left", padx=(0, 8))
        self.start_btn = self.button(right, "▶  Запустить", self.start_bridge, compact=True)
        self.start_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = self.button(right, "■  Стоп", self.stop_bridge, compact=True)
        self.stop_btn.pack(side="left")

        self.page_host = tk.Frame(self.content, bg=c["bg"])
        self.page_host.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.show_page("dashboard")

    def refresh_sidebar(self):
        c = self.colors
        for name, btn in self.profile_buttons.items():
            title, desc = PROFILE_INFO[name]
            btn.configure(text=f"{title}\n{desc}", bg=c["surface3"] if name == self.current_profile else c["surface"], fg=c["fg"], activebackground=c["surface3"], activeforeground=c["fg"], font=("Segoe UI", 9, "bold" if name == self.current_profile else "normal"))
        for key, btn in self.nav_buttons.items():
            active = key == self.page
            btn.configure(bg=c["surface3"] if active else c["surface"], fg=c["fg"], activebackground=c["surface3"], activeforeground=c["fg"], font=("Segoe UI", 10, "bold" if active else "normal"))
        if hasattr(self, "theme_small"):
            self.theme_small.configure(text="☾ Темная" if self.theme_dark else "☀ Светлая")

    def clear_page(self):
        for child in self.page_host.winfo_children():
            child.destroy()

    def show_page(self, page):
        self.page = page
        self.clear_page()
        titles = {
            "dashboard": ("Dashboard", "Живая телеметрия и состояние адаптивных триггеров"),
            "tuning": ("Настройка профиля", "Все параметры сохранены отдельно для Soft / Medium / Hard"),
            "log": ("Bridge log", "Диагностика запуска и телеметрии без консольного окна"),
        }
        self.page_title.configure(text=titles[page][0])
        self.page_subtitle.configure(text=titles[page][1])
        if page == "dashboard":
            self.build_dashboard()
        elif page == "tuning":
            self.build_tuning()
        else:
            self.build_log()
        self.refresh_sidebar()

    def build_dashboard(self):
        c = self.colors
        top = tk.Frame(self.page_host, bg=c["bg"])
        top.pack(fill="x", pady=(0, 12))
        metrics = [("speed_kmh", "SPEED", "km/h"), ("rpm", "RPM", ""), ("gear", "GEAR", ""), ("telemetry_age_ms", "TEL", "ms")]
        self.metric_cards = {}
        for i, (key, title, unit) in enumerate(metrics):
            top.grid_columnconfigure(i, weight=1)
            card = self.make_card(top)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0))
            tk.Label(card, text=title, font=("Segoe UI", 9, "bold"), fg=c["muted"], bg=c["surface"]).pack(anchor="w", padx=14, pady=(12, 2))
            wrap = tk.Frame(card, bg=c["surface"])
            wrap.pack(fill="x", padx=14, pady=(0, 12))
            val = tk.Label(wrap, text="—", font=("Segoe UI", 22, "bold"), fg=c["accent"], bg=c["surface"])
            val.pack(side="left")
            tk.Label(wrap, text=unit, font=("Segoe UI", 9), fg=c["muted"], bg=c["surface"]).pack(side="left", padx=7, pady=(8, 0))
            self.metric_cards[key] = val

        row = tk.Frame(self.page_host, bg=c["bg"])
        row.pack(fill="both", expand=True)
        left = self.make_card(row)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        right = self.make_card(row)
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))

        self.live_rows = {}
        left_specs = [
            ("throttle", "Газ"), ("brake", "Тормоз"), ("handbrake", "Ручник"),
            ("rt_resistance", "RT force"), ("rt_base_configured", "RT base"), ("lt_resistance", "LT force"), ("rt_hz", "RT Hz"),
        ]
        right_specs = [
            ("lt_hz", "ABS / Road Hz"), ("road_strength", "Road"), ("slip", "Slip"), ("gforce", "G-force"),
            ("surface", "Surface"), ("rumble", "Rumble"), ("drift", "Drift"), ("airborne", "Airborne"),
        ]
        self.build_live_rows(left, left_specs)
        self.build_live_rows(right, right_specs)

        footer = tk.Frame(self.page_host, bg=c["bg"])
        footer.pack(fill="x", pady=(12, 0))
        self.rt_chip = tk.Label(footer, text="RT · FREE", font=("Segoe UI", 9, "bold"), fg=c["muted"], bg=c["surface2"], padx=12, pady=8)
        self.rt_chip.pack(side="left", padx=(0, 8))
        self.lt_chip = tk.Label(footer, text="LT · —", font=("Segoe UI", 9, "bold"), fg=c["muted"], bg=c["surface2"], padx=12, pady=8)
        self.lt_chip.pack(side="left")
        self.profile_chip = tk.Label(footer, text=f"Profile · {self.current_profile}", font=("Segoe UI", 9, "bold"), fg=c["muted"], bg=c["surface2"], padx=12, pady=8)
        self.profile_chip.pack(side="right")

    def build_live_rows(self, parent, specs):
        c = self.colors
        for key, name in specs:
            row = tk.Frame(parent, bg=c["surface2"], highlightthickness=1, highlightbackground=c["border"])
            row.pack(fill="x", padx=10, pady=5)
            tk.Label(row, text=name, font=("Segoe UI", 10), fg=c["fg"], bg=c["surface2"]).pack(side="left", padx=12, pady=10)
            val = tk.Label(row, text="—", font=("Segoe UI", 10, "bold"), fg=c["accent"], bg=c["surface2"])
            val.pack(side="right", padx=12, pady=10)
            self.live_rows[key] = val

    def build_tuning(self):
        c = self.colors
        outer = tk.Frame(self.page_host, bg=c["bg"])
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=c["bg"], highlightthickness=0)
        scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview, style="Modern.Vertical.TScrollbar")
        inner = tk.Frame(canvas, bg=c["bg"])
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window_id, width=max(760, e.width)))
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._mouse_canvas = canvas
        canvas.bind_all("<MouseWheel>", self.on_mousewheel, add="+")
        self.param_frame = inner
        self.rebuild_profile_fields()

    def on_mousewheel(self, event):
        if self.page == "tuning" and self._mouse_canvas:
            self._mouse_canvas.yview_scroll(int(-event.delta / 120), "units")

    def build_section(self, parent, section, cfg):
        c = self.colors
        card = self.make_card(parent)
        card.pack(fill="x", pady=7)
        header = tk.Frame(card, bg=c["surface"])
        header.pack(fill="x", padx=16, pady=(14, 8))
        title = section.capitalize()
        tk.Label(header, text=title, font=("Segoe UI", 14, "bold"), fg=c["fg"], bg=c["surface"]).pack(side="left")
        count = len(cfg[section])
        tk.Label(header, text=f"{count} параметров", font=("Segoe UI", 9), fg=c["muted"], bg=c["surface"]).pack(side="left", padx=10)
        help_text = self.section_help(section)
        tk.Label(card, text=help_text, font=("Segoe UI", 9), fg=c["muted"], bg=c["surface"], justify="left", wraplength=900).pack(anchor="w", padx=16, pady=(0, 10))
        grid = tk.Frame(card, bg=c["surface"])
        grid.pack(fill="x", padx=12, pady=(0, 14))
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        keys = list(cfg[section].keys())
        for idx, key in enumerate(keys):
            r = idx // 2
            col = idx % 2
            item = tk.Frame(grid, bg=c["surface2"], highlightthickness=1, highlightbackground=c["border"])
            item.grid(row=r, column=col, sticky="ew", padx=4, pady=4)
            tk.Label(item, text=LABELS.get(f"{section}.{key}", key), font=("Segoe UI", 9, "bold"), fg=c["fg"], bg=c["surface2"], anchor="w", wraplength=310).pack(fill="x", padx=10, pady=(8, 2))
            if key == "enabled":
                var = tk.BooleanVar(value=cfg[section][key].strip().lower() in ("true", "1", "yes", "on"))
                self.entry_vars[(section, key)] = var
                check = tk.Checkbutton(item, text="Включено", variable=var, bg=c["surface2"], fg=c["fg"], activebackground=c["surface2"], activeforeground=c["fg"], selectcolor=c["surface3"], highlightthickness=0, bd=0, command=self.mark_dirty)
                check.pack(anchor="w", padx=9, pady=(2, 8))
            else:
                var = tk.StringVar(value=cfg[section][key])
                self.entry_vars[(section, key)] = var
                e = tk.Entry(item, textvariable=var, font=("Segoe UI", 10), bg=c["entry"], fg=c["fg"], insertbackground=c["fg"], selectbackground=c["accent"], selectforeground="#FFFFFF", relief="flat", bd=0, highlightthickness=1, highlightbackground=c["border2"], highlightcolor=c["accent"])
                e.pack(fill="x", padx=9, pady=(2, 9), ipady=5)
                e.bind("<KeyRelease>", lambda _e: self.mark_dirty())
        return card

    def rebuild_profile_fields(self):
        if not hasattr(self, "param_frame"):
            return
        for child in self.param_frame.winfo_children():
            child.destroy()
        self.entry_vars.clear()
        path = profile_path(self.current_profile)
        if not path.exists():
            # Backward-compatible fallback for packages that kept profiles
            # at the release root.
            legacy = root_profile_path(self.current_profile)
            if legacy.exists():
                PROFILES_DIR.mkdir(parents=True, exist_ok=True)
                try:
                    legacy.replace(path)
                except Exception:
                    path = legacy
        cfg = read_ini(path)
        if not cfg.sections():
            self.label(self.param_frame, "Профиль не найден", 14, "bold", self.colors["bad"], self.colors["bg"]).pack(anchor="w", padx=8, pady=(18, 4))
            self.label(self.param_frame, f"Нет файла: {path}", 9, "normal", self.colors["muted"], self.colors["bg"]).pack(anchor="w", padx=8, pady=(0, 8))
            self.label(self.param_frame, "Положи soft.ini / medium.ini / hard.ini в папку profiles рядом с EXE.", 9, "normal", self.colors["fg"], self.colors["bg"], anchor="w").pack(anchor="w", padx=8)
            return
        self.label(self.param_frame, f"Профиль {self.current_profile.upper()}", 13, "bold", self.colors["fg"], self.colors["bg"]).pack(anchor="w", padx=8, pady=(6, 2))
        self.label(self.param_frame, "RT: gas_* управляют только сопротивлением. r2_* — отдельная вибрация.", 9, "normal", self.colors["muted"], self.colors["bg"]).pack(anchor="w", padx=8, pady=(0, 8))
        for section in SECTIONS:
            if section in cfg:
                self.build_section(self.param_frame, section, cfg)
        self.profile_dirty = False

    def section_help(self, section):
        return {
            "resistance": "Главная механика сопротивления. gas_base + gas_input·газ + gas_rpm·RPM дают базовую RT Race-силу без скрытого добавления RT vibration.",
            "vibration": "Отдельная текстура/вибрация. Она не увеличивает вычисляемое RT force.",
            "road": "Дорожный эффект, подавление в дрифте и airborne-эвристика по подвеске.",
            "recoil": "Только LT. В RT recoil никогда не отправляется.",
        }.get(section, "")

    def mark_dirty(self):
        self.profile_dirty = True

    def select_profile(self, name):
        if name not in PROFILE_NAMES:
            return
        if self.profile_dirty and name != self.current_profile:
            # Keep switching frictionless: the current values stay untouched in file until the user saves.
            self.profile_dirty = False
        self.current_profile = name
        self.rebuild_profile_fields()
        if hasattr(self, "profile_chip"):
            self.profile_chip.configure(text=f"Profile · {name}")
        self.refresh_sidebar()

    def validate(self, cfg):
        for section in SECTIONS:
            if section not in cfg:
                continue
            for key, value in cfg[section].items():
                if key == "enabled":
                    if value.strip().lower() not in ("true", "false", "1", "0", "yes", "no", "on", "off"):
                        raise ValueError(f"{section}.{key}: ожидается true/false")
                else:
                    float(value)

    def save_profile(self, silent=False):
        path = profile_path(self.current_profile)
        cfg = read_ini(path)
        for (section, key), var in self.entry_vars.items():
            value = var.get()
            cfg[section][key] = ("true" if value else "false") if key == "enabled" else str(value).strip()
        self.validate(cfg)
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        write_ini(cfg, path)
        # Keep a root-level mirror for compatibility with older package layouts.
        write_ini(cfg, root_profile_path(self.current_profile))
        self.profile_dirty = False
        self.append_log(f"Saved {path}")
        if not silent:
            messagebox.showinfo("Профиль", f"Сохранено: {path.name}\n\nНовый эффект применяется после перезапуска bridge.")

    def start_bridge(self):
        try:
            self.save_profile(silent=True)
        except Exception as e:
            messagebox.showerror("Ошибка профиля", str(e))
            return
        if self.proc and self.proc.poll() is None:
            self.append_log("Bridge already running")
            return
        if getattr(sys, "frozen", False):
            bridge_exe = BASE_DIR / "APEX5_FH6_Bridge.exe"
            if not bridge_exe.exists():
                messagebox.showerror("Bridge not found", f"Не найден {bridge_exe}")
                return
            cmd = [str(bridge_exe), str(profile_path(self.current_profile))]
        else:
            worker = resource_path("bridge_worker.py")
            cmd = [pythonw_path(), str(worker), str(profile_path(self.current_profile))]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        env = os.environ.copy()
        env["APEX5_GUI_STATE_PATH"] = str(STATE_PATH)
        try:
            self.proc = subprocess.Popen(cmd, cwd=str(BASE_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True, bufsize=1, creationflags=creationflags, env=env)
        except Exception as e:
            messagebox.showerror("Запуск", str(e))
            return
        self.append_log("START: " + " ".join(cmd))
        threading.Thread(target=self.read_process_output, args=(self.proc,), daemon=True).start()

    def read_process_output(self, proc):
        try:
            for line in proc.stdout:
                self.status_q.put(line.rstrip())
        except Exception as e:
            self.status_q.put(f"[bridge output error] {e}")

    def stop_bridge(self):
        if not self.proc or self.proc.poll() is not None:
            return
        self.append_log("STOP requested")
        try:
            self.proc.terminate()
        except Exception:
            pass
        threading.Thread(target=self._kill_if_needed, args=(self.proc,), daemon=True).start()

    def _kill_if_needed(self, proc):
        try:
            proc.wait(timeout=2.0)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def poll_process(self):
        try:
            while True:
                self.status_q.get_nowait()
                # Logs remain available in the Log page; do not flood the UI every frame.
        except queue.Empty:
            pass
        running = self.proc is not None and self.proc.poll() is None
        c = self.colors
        if running:
            self.side_status_dot.configure(fg=c["good"])
            self.side_status.configure(text="Bridge running", fg=c["good"])
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
        else:
            self.side_status_dot.configure(fg=c["muted"])
            self.side_status.configure(text="Bridge stopped", fg=c["muted"])
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
        self.root.after(250, self.poll_process)

    def append_log(self, line):
        self.log_lines.append(line)
        self.log_lines = self.log_lines[-800:]
        if hasattr(self, "log_text"):
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.insert("end", "\n".join(self.log_lines))
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        try:
            with LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def build_log(self):
        c = self.colors
        top = tk.Frame(self.page_host, bg=c["bg"])
        top.pack(fill="x", pady=(0, 8))
        self.label(top, "Последние сообщения bridge", 10, "bold", c["muted"], c["bg"]).pack(side="left")
        self.button(top, "Очистить", self.clear_log, compact=True).pack(side="right")
        wrap = self.make_card(self.page_host)
        wrap.pack(fill="both", expand=True)
        self.log_text = tk.Text(wrap, bg=c["entry"], fg=c["fg"], insertbackground=c["fg"], selectbackground=c["accent"], relief="flat", bd=0, font=("Consolas", 10), padx=12, pady=12)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")
        if self.log_lines:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", "\n".join(self.log_lines))
            self.log_text.configure(state="disabled")

    def clear_log(self):
        self.log_lines = []
        try:
            LOG_PATH.unlink(missing_ok=True)
        except Exception:
            pass
        if hasattr(self, "log_text"):
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.configure(state="disabled")

    def open_profile_folder(self):
        PROFILES_DIR.mkdir(exist_ok=True)
        if os.name == "nt":
            os.startfile(str(PROFILES_DIR))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(PROFILES_DIR)])
        else:
            subprocess.Popen(["xdg-open", str(PROFILES_DIR)])

    def load_state(self):
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None

    def poll_state(self):
        state = self.load_state()
        if state:
            self.last_state = state
            if self.page == "dashboard":
                self.update_dashboard(state)
            self.update_sensor_window(state)
        self.root.after(100, self.poll_state)

    @staticmethod
    def fmt(v, digits=1):
        if v is None:
            return "—"
        try:
            return f"{float(v):.{digits}f}"
        except Exception:
            return str(v)

    def update_dashboard(self, s):
        self.metric_cards["speed_kmh"].configure(text=self.fmt(s.get("speed_kmh"), 1))
        self.metric_cards["rpm"].configure(text=self.fmt(s.get("rpm"), 0))
        self.metric_cards["gear"].configure(text=str(s.get("gear", "—")))
        self.metric_cards["telemetry_age_ms"].configure(text=self.fmt(s.get("telemetry_age_ms"), 0))
        vals = {
            "throttle": f"{s.get('accel', 0)} / 255",
            "brake": f"{s.get('brake', 0)} / 255",
            "handbrake": f"{s.get('handbrake', 0)} / 255",
            "rt_resistance": self.fmt(s.get("rt_resistance"), 1),
            "rt_base_configured": self.fmt(s.get("rt_base_configured"), 1),
            "lt_resistance": self.fmt(s.get("lt_resistance"), 1),
            "rt_hz": f"{self.fmt(s.get('rt_hz'), 1)} Hz",
            "lt_hz": f"{self.fmt(s.get('lt_hz'), 1)} Hz",
            "road_strength": self.fmt(s.get("road_strength"), 1),
            "slip": self.fmt(s.get("slip"), 3),
            "gforce": self.fmt(s.get("gforce"), 2),
            "surface": self.fmt(s.get("surface"), 3),
            "rumble": self.fmt(s.get("rumble"), 3),
            "drift": self.fmt(s.get("drift"), 3),
            "airborne": "YES" if s.get("airborne") else "NO",
        }
        for k, v in vals.items():
            if k in self.live_rows:
                self.live_rows[k].configure(text=v)
        c = self.colors
        if s.get("rt_control_enabled"):
            self.rt_chip.configure(text=f"RT · FORCE {self.fmt(s.get('rt_resistance'), 1)} · VIB {'ON' if s.get('use_r_vib') else 'OFF'}", fg=c["good"], bg=c["surface2"])
        else:
            self.rt_chip.configure(text="RT · FREE · force 0", fg=c["muted"], bg=c["surface2"])
        self.lt_chip.configure(text=f"LT · FORCE {self.fmt(s.get('lt_resistance'), 1)} · VIB {'ON' if s.get('use_l_vib') else 'OFF'}", fg=c["accent"], bg=c["surface2"])
        self.profile_chip.configure(text=f"Profile · {s.get('profile', self.current_profile)}")

    def open_sensors(self):
        if self.sensor_window and self.sensor_window.winfo_exists():
            self.sensor_window.lift()
            return
        self.sensor_window = tk.Toplevel(self.root)
        self.sensor_window.title("APEX 5 · FH6 Live Sensors")
        self.sensor_window.configure(bg=self.colors["bg"])
        self.sensor_window.geometry("1480x860")
        self.sensor_window.minsize(1150, 700)
        self.place_on_second_monitor(self.sensor_window)
        c = self.colors
        head = tk.Frame(self.sensor_window, bg=c["bg"])
        head.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(head, text="FH6 LIVE TELEMETRY", font=("Segoe UI", 24, "bold"), fg=c["fg"], bg=c["bg"]).pack(side="left")
        tk.Label(head, text="для второго монитора", font=("Segoe UI", 10), fg=c["muted"], bg=c["bg"]).pack(side="left", padx=12, pady=(9, 0))
        self.button(head, "Закрыть", self.sensor_window.destroy, compact=True).pack(side="right")

        grid = tk.Frame(self.sensor_window, bg=c["bg"])
        grid.pack(fill="both", expand=True, padx=20, pady=8)
        for col in range(4):
            grid.grid_columnconfigure(col, weight=1)
        for row in range(5):
            grid.grid_rowconfigure(row, weight=1)

        specs = [
            ("speed_kmh", "SPEED", "km/h"), ("rpm", "RPM", ""), ("gear", "GEAR", ""), ("telemetry_age_ms", "TEL AGE", "ms"),
            ("accel", "THROTTLE", "/255"), ("brake", "BRAKE", "/255"), ("handbrake", "HANDBRAKE", "/255"), ("rt_resistance", "RT FORCE", ""),
            ("rt_base_configured", "RT BASE", ""), ("lt_resistance", "LT FORCE", ""), ("rt_hz", "RT VIB", "Hz"), ("lt_hz", "ABS / ROAD", "Hz"),
            ("slip", "SLIP", ""), ("surface", "SURFACE", ""), ("road_strength", "ROAD", ""), ("gforce", "G-FORCE", "g"),
            ("drift", "DRIFT", ""), ("airborne", "AIRBORNE", ""), ("susp0", "SUSP FL", ""), ("susp1", "SUSP FR", ""),
        ]
        self.sensor_labels = {}
        for idx, (key, title, unit) in enumerate(specs):
            r, col = divmod(idx, 4)
            card = self.make_card(grid)
            card.grid(row=r, column=col, sticky="nsew", padx=5, pady=5)
            tk.Label(card, text=title, font=("Segoe UI", 9, "bold"), fg=c["muted"], bg=c["surface"]).pack(anchor="w", padx=14, pady=(12, 2))
            val = tk.Label(card, text="—", font=("Segoe UI", 25, "bold"), fg=c["accent"], bg=c["surface"])
            val.pack(anchor="w", padx=14, pady=(0, 2))
            tk.Label(card, text=unit, font=("Segoe UI", 9), fg=c["muted"], bg=c["surface"]).pack(anchor="w", padx=14, pady=(0, 12))
            self.sensor_labels[key] = val
        bottom = self.make_card(self.sensor_window)
        bottom.pack(fill="x", padx=20, pady=(2, 20))
        self.susp_text = tk.Label(bottom, text="Suspension: —", font=("Segoe UI", 11, "bold"), fg=c["fg"], bg=c["surface"])
        self.susp_text.pack(anchor="w", padx=14, pady=10)

    def update_sensor_window(self, s):
        if not self.sensor_window or not self.sensor_window.winfo_exists():
            return
        vals = {
            "speed_kmh": self.fmt(s.get("speed_kmh"), 1), "rpm": self.fmt(s.get("rpm"), 0), "gear": str(s.get("gear", "—")),
            "telemetry_age_ms": self.fmt(s.get("telemetry_age_ms"), 0), "accel": str(s.get("accel", 0)), "brake": str(s.get("brake", 0)),
            "handbrake": str(s.get("handbrake", 0)), "rt_resistance": self.fmt(s.get("rt_resistance"), 1), "rt_base_configured": self.fmt(s.get("rt_base_configured"), 1),
            "lt_resistance": self.fmt(s.get("lt_resistance"), 1), "rt_hz": self.fmt(s.get("rt_hz"), 1), "lt_hz": self.fmt(s.get("lt_hz"), 1),
            "slip": self.fmt(s.get("slip"), 3), "surface": self.fmt(s.get("surface"), 3), "road_strength": self.fmt(s.get("road_strength"), 1),
            "gforce": self.fmt(s.get("gforce"), 2), "drift": self.fmt(s.get("drift"), 3), "airborne": "YES" if s.get("airborne") else "NO",
            "susp0": self.fmt((s.get("susp_norm") or [0,0,0,0])[0], 3), "susp1": self.fmt((s.get("susp_norm") or [0,0,0,0])[1], 3),
        }
        for k, v in vals.items():
            if k in self.sensor_labels:
                self.sensor_labels[k].configure(text=v)
        susp = s.get("susp_norm") or [0, 0, 0, 0]
        while len(susp) < 4:
            susp.append(0)
        self.susp_text.configure(text=f"Suspension   FL {self.fmt(susp[0],3)}   ·   FR {self.fmt(susp[1],3)}   ·   RL {self.fmt(susp[2],3)}   ·   RR {self.fmt(susp[3],3)}")

    def place_on_second_monitor(self, win):
        if os.name != "nt":
            return
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            monitors = []
            proc_type = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
            def cb(_hmon, _hdc, rect_ptr, _lparam):
                r = rect_ptr.contents
                monitors.append((r.left, r.top, r.right, r.bottom))
                return 1
            user32.EnumDisplayMonitors(0, 0, proc_type(cb), 0)
            if len(monitors) >= 2:
                left, top, right, bottom = monitors[1]
                win.geometry(f"{right-left}x{bottom-top}+{left}+{top}")
                win.after(80, win.state, "zoomed")
        except Exception:
            pass

    def toggle_theme(self):
        self.theme_dark = not self.theme_dark
        self.colors = DARK if self.theme_dark else LIGHT
        self.save_ui_state()
        if self.sensor_window and self.sensor_window.winfo_exists():
            self.sensor_window.destroy()
            self.sensor_window = None
        self.build_ui()
        self.select_profile(self.current_profile)

    def on_close(self):
        self.stop_bridge()
        self.save_ui_state()
        self.root.destroy()


if __name__ == "__main__":
    PROFILES_DIR.mkdir(exist_ok=True)
    root = tk.Tk()
    App(root)
    root.mainloop()
