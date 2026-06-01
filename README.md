# 📚 BD Telegram Downloader (Web UI)

Outil d'automatisation pour récupérer des bandes dessinées depuis des channels Telegram privés, avec une interface Web complète pour scanner, rechercher, sélectionner visuellement et gérer vos téléchargements (déduplication via [Everything](https://www.voidtools.com/)).

---

## ✨ Fonctionnalités

- 🌐 **Interface Web moderne** : plus besoin de ligne de commande, tout se passe dans le navigateur !
- 🛒 **Panier de téléchargement** : sélectionnez vos BD, ajoutez-les au panier et lancez tout à la fin pour ne pas ralentir votre navigation.
- 🔍 **Scan intelligent** : ne traite que les messages non lus depuis la dernière session ou une date précise.
- 📚 **Bibliothèque locale & Ma pile à lire** : recherchez directement dans vos dossiers locaux via Everything et épinglez (📌) des BD dans votre pile à lire.
- 🖼️ **Galerie visuelle dynamique** : pochettes des albums affichées en temps réel.
- 🚫 **Déduplication en direct** : comparaison floue (*fuzzy matching*) avec votre collection pour repérer les doublons.
- ⬇️ **Téléchargements parallèles** : configurable directement depuis l'interface Web.

---

## 🛠️ Prérequis

| Outil | Rôle |
|-------|------|
| Python 3.10+ | Runtime |
| [Everything](https://www.voidtools.com/) | Moteur de recherche local (déduplication) |
| Compte Telegram | API id + hash sur [my.telegram.org](https://my.telegram.org) |

### Everything — configuration requise
Dans Everything → **Outils → Options → HTTP Server** :
- Activer le serveur HTTP
- Port : `8070` (ou modifier le port via l'interface Web / `config.json`)

---

## 🚀 Installation

```bat
REM 1. Créer et activer le venv
python -m venv venv
venv\Scripts\activate

REM 2. Installer les dépendances
pip install -r requirements.txt

REM 3. Copier et préparer la configuration
copy config.example.json config.json
REM → Editez config.json avec vos api_id et api_hash Telegram
```

---

## 🎮 Utilisation

Pour lancer l'application, double-cliquez simplement sur :
```bat
run_web.bat
```
*(ou `run.bat` qui redirige désormais vers l'interface Web).*

L'interface sera accessible dans votre navigateur à l'adresse : **http://127.0.0.1:8000**

> ⚠️ Au premier lancement, regardez la fenêtre de commande noire (console) : Telegram vous demandera d'entrer votre numéro de téléphone et le code d'authentification reçu par message pour créer la session (`telegram_bd_session.session`).

### ⚙️ Configuration
Toute la configuration (dossiers de recherche, date de départ, nombre de téléchargements simultanés, etc.) peut désormais être modifiée directement via le bouton **"⚙️ Config"** dans l'interface Web.

---

## 📁 Structure du projet

```
projetBDTelegram/
├── web_ui.py               # Serveur FastAPI et Interface Web
├── telegram_scraper.py     # Logique de communication avec Telegram
├── downloader.py           # Logique de téléchargement asynchrone
├── everything_checker.py   # Connexion à l'API Everything
├── fuzzy_matcher.py        # Comparaison floue des noms
├── logger.py               # Logs console
├── run_web.bat             # Lanceur de l'interface Web
├── run.bat                 # Raccourci vers run_web.bat
├── requirements.txt        # Dépendances Python
├── config.example.json     # Modèle de configuration
├── config.json             # ← Vos identifiants (ignoré par git)
├── thumbs/                 # ← Cache des pochettes (ignoré par git)
└── venv/                   # ← Environnement virtuel (ignoré par git)
```

---

## 🔑 Obtenir les credentials Telegram

1. Allez sur [my.telegram.org](https://my.telegram.org)
2. Connectez-vous avec votre numéro de téléphone
3. **API development tools** → créez une application
4. Copiez `api_id` et `api_hash` dans votre `config.json`
