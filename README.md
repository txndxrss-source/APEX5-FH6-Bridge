<div align="center">

# 🎮 APEX 5 FH6 Adaptive Trigger Bridge

### Flydigi APEX 5 × Forza Horizon 6

**Adaptive Triggers · Vibration · Telemetry · Profiles · GUI**

[![Platform](https://img.shields.io/badge/platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)](#-installation)
[![Controller](https://img.shields.io/badge/controller-Flydigi%20APEX%205-111111?style=for-the-badge)](#-what-is-this)
[![Game](https://img.shields.io/badge/game-Forza%20Horizon%206-8A2BE2?style=for-the-badge)](#-what-is-this)
[![License](https://img.shields.io/badge/license-Non--Commercial-orange?style=for-the-badge)](#-license)

**[⬇️ Download](#-installation) · [🐛 Report a Bug](#-troubleshooting) · [⚙️ Configuration](#-configuration)**

</div>

---

## 🇷🇺 Русский

## 🎯 Что это?

**APEX 5 FH6 Adaptive Trigger Bridge** — независимый сторонний проект для **Flydigi APEX 5** и **Forza Horizon 6**.

Цель проекта — добавить более продвинутую обратную связь в адаптивные курки APEX 5 и использовать её **без необходимости постоянно держать Flydigi Space / Space Station запущенным**.

Проект может использовать телеметрию автомобиля и преобразовывать её в эффекты для курков:

- 🎮 сопротивление RT (газ);
- 🛑 сопротивление LT (тормоз);
- 📳 вибрация RT/LT;
- 🔥 эффект ABS / торможения;
- 🛣️ дорожные эффекты;
- 🌀 уменьшение дорожного эффекта во время дрифта;
- 🚗 отключение дорожного эффекта при нахождении автомобиля в воздухе;
- 📈 зависимость вибрации RT от RPM;
- 🎛️ отдельные профили и настройки.

> **Важно:** это неофициальный проект сообщества. Он не связан с Flydigi, Microsoft, Xbox, Playground Games или Forza.

---

## ✨ Возможности

### 🎮 Adaptive Triggers

Можно отдельно настроить сопротивление:

| Эффект | Настройка |
|---|---|
| RT / Газ | Базовое сопротивление |
| RT / Газ | Сопротивление от нажатия |
| RT / Газ | Сопротивление от RPM |
| LT / Тормоз | Базовое сопротивление |
| LT / Тормоз | Сопротивление от нажатия |
| LT / Тормоз | Дополнительное сопротивление от ABS |
| Ручник | Максимальное сопротивление |

### 📳 Trigger Vibration

Вибрация курков работает независимо от сопротивления и может использовать телеметрию:

- **RT** → частота зависит от RPM;
- **LT** → вибрация может реагировать на ABS;
- **Road** → отдельный дорожный эффект.

### 🛣️ Road Effects

Дорожный эффект можно настроить так, чтобы он:

- уменьшался во время дрифта;
- отключался при нахождении автомобиля в воздухе;
- масштабировался относительно скорости.

### 🎛️ Profiles

В комплекте предусмотрены три профиля:

```text
soft.ini      → мягкие эффекты
medium.ini    → средние эффекты
hard.ini      → сильные эффекты
```

Профили можно редактировать через GUI.

---

## 🖥️ GUI

Проект включает графический интерфейс.

В GUI можно:

- выбирать профиль;
- изменять параметры;
- сохранять настройки;
- запускать bridge;
- видеть состояние системы;
- просматривать телеметрию;
- переключать светлую / тёмную тему.

🌙 **Тёмная тема включена по умолчанию.**

---

## 🏎️ Как это работает?

Упрощённая схема:

```text
┌──────────────────────┐
│   Forza Horizon 6    │
└──────────┬───────────┘
           │
           │ Vehicle telemetry
           ▼
┌──────────────────────┐
│   FH6 Telemetry      │
└──────────┬───────────┘
           │
           ▼
┌─────────────────────────────┐
│   APEX 5 FH6 Bridge         │
│                             │
│  RT Resistance              │
│  LT Resistance              │
│  RT Vibration               │
│  LT Vibration               │
│  ABS / Brake                 │
│  Road Effects                │
└──────────┬──────────────────┘
           │
           ▼
┌──────────────────────┐
│    Flydigi APEX 5    │
└──────────────────────┘
```

---

## 🚀 Installation

### Для обычного пользователя

Если вы скачали готовый установщик из **GitHub Releases**, устанавливать Python, pip или дополнительные Python-библиотеки **не требуется**.

### 1. Скачать

Откройте:

**GitHub → Releases**

и скачайте:

```text
APEX5_FH6_Bridge_Setup.exe
```

### 2. Установить

Запустите установщик и установите программу как обычное Windows-приложение.

### 3. Подключить контроллер

Подключите **Flydigi APEX 5** и убедитесь, что Windows его видит.

### 4. Запустить GUI

Откройте **APEX 5 FH6 Bridge**.

### 5. Выбрать профиль

Для первого запуска рекомендуется начать с:

```text
Soft
```

Если эффекты кажутся слишком слабыми или сильными, их можно изменить в GUI.

---

## ⚙️ Configuration

Основные настройки находятся в профилях `.ini`.

### Resistance

```ini
[resistance]

gas_base
gas_input
gas_rpm

brake_base
brake_input
brake_abs

handbrake_max
```

### Vibration

```ini
[vibration]

r2_max_strength
l2_max_strength

r2_duty
l2_duty

r2_pressure
l2_pressure

r2_freq_min
r2_freq_max

l2_freq_min
l2_freq_max
```

### Road

```ini
[road]

max_strength
drift_reduction
drift_multiplier
airborne_multiplier
road_speed_scale
```

### Recoil / ABS

```ini
[recoil]

enabled
brake_threshold
abs_threshold
strength
stroke
cooldown_ms
```

Обычному пользователю менять `.ini` вручную необязательно — настройки доступны через GUI.

---

## ❗ Troubleshooting

Если что-то не работает, проверьте:

1. APEX 5 подключён к Windows.
2. Windows определяет контроллер как Xbox/XInput gamepad.
3. Forza Horizon 6 запущена.
4. Bridge запущен.
5. Выбран правильный профиль.
6. Нужные параметры не установлены в `0`.
7. Flydigi Space / Space Station не конфликтует с bridge.

Если проблема остаётся, создайте **GitHub Issue** и укажите:

- версию Windows;
- версию/прошивку APEX 5, если известна;
- USB или Wireless;
- версию проекта;
- описание проблемы;
- лог или скриншот ошибки.

**Не публикуйте в Issues пароли, токены, личные данные или содержимое личных файлов.**

---

## 🧪 Project Status

Проект создавался и тестировался на реальном:

- Flydigi APEX 5;
- Windows;
- Forza Horizon 6.

Это экспериментальный community project, а не официальный SDK Flydigi.

Результат может зависеть от версии прошивки контроллера, Windows, игры, способа подключения и другого программного обеспечения.

---

## 🤖 Made with ChatGPT

Этот проект был создан **при значительной помощи ChatGPT**.

Я не являюсь профессиональным программистом и на момент начала проекта практически не разбирался в разработке такого рода программ.

ChatGPT помогал мне:

- исследовать HID и XInput;
- анализировать данные APEX 5;
- разрабатывать bridge;
- разбираться с протоколом adaptive triggers;
- писать и исправлять код;
- создавать конфигурацию;
- разрабатывать GUI;
- собирать EXE через PyInstaller;
- создавать Windows installer;
- находить и исправлять ошибки.

При этом проект **реально тестировался на железе**, а изменения проверялись на APEX 5 и Forza Horizon 6.

Это также небольшой эксперимент в **AI-assisted development** — проект был создан человеком без профессионального опыта программирования с помощью ИИ и реального тестирования.

Если найдёте ошибку или хотите предложить улучшение — создавайте Issue или Pull Request.

---

## 🙏 Credits

Спасибо:

- сообществу Flydigi;
- людям, исследующим протоколы игровых контроллеров;
- авторам открытых проектов, связанных с HID и adaptive triggers;
- **OpenAI / ChatGPT** за помощь во время разработки.

---

# 🇬🇧 English

## 🎯 What is this?

**APEX 5 FH6 Adaptive Trigger Bridge** is an independent community project for the **Flydigi APEX 5** controller and **Forza Horizon 6**.

The goal is to provide advanced adaptive-trigger feedback while **not requiring Flydigi Space / Space Station to stay running all the time**.

The project can use vehicle telemetry and convert it into trigger effects:

- 🎮 RT / throttle resistance;
- 🛑 LT / brake resistance;
- 📳 RT/LT vibration;
- 🔥 ABS / braking effects;
- 🛣️ road effects;
- 🌀 reduced road feedback while drifting;
- 🚗 disabled road feedback while airborne;
- 📈 RPM-dependent RT vibration;
- 🎛️ configurable profiles.

> **Important:** This is an unofficial community project. It is not affiliated with Flydigi, Microsoft, Xbox, Playground Games or Forza.

---

## ✨ Features

### 🎮 Adaptive Triggers

Resistance can be configured separately for:

| Effect | Configuration |
|---|---|
| RT / Throttle | Base resistance |
| RT / Throttle | Input-based resistance |
| RT / Throttle | RPM-based resistance |
| LT / Brake | Base resistance |
| LT / Brake | Input-based resistance |
| LT / Brake | ABS-based resistance |
| Handbrake | Maximum resistance |

### 📳 Trigger Vibration

Trigger vibration can use vehicle telemetry:

- **RT** → frequency based on RPM;
- **LT** → vibration can react to ABS;
- **Road** → independently configurable road feedback.

### 🛣️ Road Effects

Road feedback can be configured to:

- become weaker while drifting;
- turn off while airborne;
- scale with vehicle speed.

### 🎛️ Profiles

Three profiles are included:

```text
soft.ini      → lighter effects
medium.ini    → medium effects
hard.ini      → stronger effects
```

Profiles can be edited through the GUI.

---

## 🖥️ GUI

The project includes a graphical interface for:

- profile selection;
- parameter editing;
- saving settings;
- starting the bridge;
- system status;
- telemetry display;
- light / dark theme.

🌙 **Dark mode is enabled by default.**

---

## 🏎️ How it works

Simplified:

```text
┌──────────────────────┐
│   Forza Horizon 6    │
└──────────┬───────────┘
           │
           │ Vehicle telemetry
           ▼
┌──────────────────────┐
│   FH6 Telemetry      │
└──────────┬───────────┘
           │
           ▼
┌─────────────────────────────┐
│   APEX 5 FH6 Bridge         │
│                             │
│  RT Resistance              │
│  LT Resistance              │
│  RT Vibration               │
│  LT Vibration               │
│  ABS / Brake                │
│  Road Effects               │
└──────────┬──────────────────┘
           │
           ▼
┌──────────────────────┐
│    Flydigi APEX 5    │
└──────────────────────┘
```

---

## 🚀 Installation

### For regular users

If you download the pre-built installer from **GitHub Releases**, you **do not need to install Python, pip or additional Python packages**.

### 1. Download

Go to:

**GitHub → Releases**

and download:

```text
APEX5_FH6_Bridge_Setup.exe
```

### 2. Install

Run the installer and install it like a normal Windows application.

### 3. Connect the controller

Connect your **Flydigi APEX 5** and make sure Windows detects it.

### 4. Launch the GUI

Open **APEX 5 FH6 Bridge**.

### 5. Select a profile

For the first launch, **Soft** is a reasonable starting point.

If the effects are too weak or too strong, adjust them in the GUI.

---

## ⚙️ Configuration

Main settings are stored in `.ini` profiles.

### Resistance

```ini
[resistance]

gas_base
gas_input
gas_rpm

brake_base
brake_input
brake_abs

handbrake_max
```

### Vibration

```ini
[vibration]

r2_max_strength
l2_max_strength

r2_duty
l2_duty

r2_pressure
l2_pressure

r2_freq_min
r2_freq_max

l2_freq_min
l2_freq_max
```

### Road

```ini
[road]

max_strength
drift_reduction
drift_multiplier
airborne_multiplier
road_speed_scale
```

### Recoil / ABS

```ini
[recoil]

enabled
brake_threshold
abs_threshold
strength
stroke
cooldown_ms
```

Most users do not need to edit `.ini` files manually — the GUI provides access to the settings.

---

## ❗ Troubleshooting

Check that:

1. APEX 5 is connected to Windows.
2. Windows detects it as an Xbox/XInput gamepad.
3. Forza Horizon 6 is running.
4. The bridge is running.
5. The correct profile is selected.
6. Required parameters are not set to `0`.
7. Flydigi Space / Space Station is not interfering with the bridge.

If the problem persists, open a **GitHub Issue** and include:

- Windows version;
- APEX 5 version / firmware if known;
- USB or Wireless connection;
- project version;
- description of the problem;
- relevant log or screenshot.

**Do not post passwords, tokens, personal information or private files in Issues.**

---

## 🧪 Project Status

This project was developed and tested with real:

- Flydigi APEX 5 hardware;
- Windows;
- Forza Horizon 6.

It is an experimental community project, not an official Flydigi SDK.

Behavior may vary depending on controller firmware, Windows version, game version, connection type and other software running on the system.

---

## 🤖 Made with ChatGPT

A significant part of this project was created **with the help of ChatGPT**.

I am **not a professional programmer**, and when I started this project I had very limited experience with this type of software development.

ChatGPT helped me with:

- HID and XInput investigation;
- APEX 5 data analysis;
- bridge development;
- adaptive-trigger protocol research;
- writing and debugging code;
- configuration design;
- GUI development;
- PyInstaller builds;
- Windows packaging;
- installer creation;
- troubleshooting and debugging.

The project was also **tested on real hardware**, with changes being checked on an APEX 5 controller and Forza Horizon 6.

This project is also an experiment in **AI-assisted development** — built by someone without professional programming experience, using AI together with real hardware testing.

If you find a bug or have an improvement idea, Issues and Pull Requests are welcome.

---

## 🙏 Credits

Thanks to:

- the Flydigi community;
- people researching game-controller protocols;
- open-source projects related to HID and adaptive triggers;
- **OpenAI / ChatGPT** for assistance during development.

---

# 📜 License

This project uses the **APEX 5 FH6 Bridge Non-Commercial License**.

You may use, study, modify and share the project for **personal and non-commercial purposes**, subject to the terms in the `LICENSE` file.

**Commercial use, commercial distribution, selling the software, selling modified versions, or incorporating the project into a commercial product requires prior written permission from the copyright holder.**

See [`LICENSE`](LICENSE) for the full terms.

---

# ⚠️ Disclaimer

**Forza Horizon, Flydigi, APEX 5, Xbox and related trademarks belong to their respective owners.**

This project is an independent community project and is not affiliated with or endorsed by the respective trademark owners.

Use the software at your own risk. No warranty is provided.

