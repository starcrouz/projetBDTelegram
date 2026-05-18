# 📚 BD Telegram Downloader

Outil d'automatisation pour récupérer des bandes dessinées depuis des channels Telegram privés, avec interface de sélection visuelle par pochettes et déduplication via [Everything](https://www.voidtools.com/).

---

## ✨ Fonctionnalités

- 🔍 **Scan intelligent** : ne traite que les messages non lus depuis la dernière session
- 📅 **Filtre par année** : ex. `["2025", "2026"]` dans le nom du fichier
- 🖼️ **Galerie visuelle** : pochettes des albums pour sélection manuelle (HTML dark mode)
- 🚫 **Déduplication** : comparaison floue (*fuzzy matching*) avec ta collection via l'API Everything
- 📚 **Recherche BDthèque** : picto 📚 sur chaque carte → Google `site:bedetheque.com` (1er résultat)
- ⬇️ **Téléchargements parallèles** : configurable (1, 2, 3… simultanés)
- 🔖 **Curseur Telegram** : option pour marquer les messages comme lus après sélection
- 🛡️ **Respect des ToS** : délai anti-flood configurable entre téléchargements

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
- Port : `8070` (ou modifier `everything_api_url` dans `config.json`)

---

## 🚀 Installation

```bat
REM 1. Créer et activer le venv
python -m venv venv
venv\Scripts\activate

REM 2. Installer les dépendances
pip install -r requirements.txt

REM 3. Copier et remplir la configuration
copy config.example.json config.json
REM → Editer config.json avec vos paramètres
```

---

## ⚙️ Configuration (`config.json`)

```json
{
    "api_id": 12345678,
    "api_hash": "votre_api_hash",
    "channels": [-1001234567890],
    "download_path": "F:\\Téléchargements\\_BD\\Telegram",
    "everything_api_url": "http://localhost:8070",

    "max_downloads_per_run": 10,
    "max_gallery_size": 50,
    "download_concurrency": 2,
    "delay_between_downloads": 5,

    "filename_contains_any": ["2025", "2026"],

    "bd_search_paths": ["F:\\BD", "F:\\BD Topectra"],
    "fuzzy_threshold_duplicate": 85,
    "fuzzy_threshold_review": 50,

    "thumb_concurrency": 5,
    "session_name": "telegram_bd_session"
}
```

| Paramètre | Description |
|-----------|-------------|
| `api_id` / `api_hash` | Credentials Telegram ([my.telegram.org](https://my.telegram.org)) |
| `channels` | IDs des channels (négatifs pour les channels publics/privés) |
| `download_path` | Dossier de destination des téléchargements |
| `max_gallery_size` | Nb max de BD affichées dans la galerie (par session) |
| `max_downloads_per_run` | Nb max de téléchargements pour `run.bat` sans `--gallery` |
| `download_concurrency` | Téléchargements simultanés (1=séquentiel, 2-3 recommandé) |
| `delay_between_downloads` | Pause en secondes entre chaque téléchargement (anti-flood) |
| `filename_contains_any` | Filtre : ne garder que les fichiers contenant l'un de ces termes |
| `bd_search_paths` | Dossiers de ta collection (pour la déduplication fuzzy) |
| `fuzzy_threshold_duplicate` | Score ≥ ce seuil → considéré doublon (écarté) |
| `fuzzy_threshold_review` | Score ≥ ce seuil → affiché comme INCERTAIN dans la galerie |

---

## 📋 Workflow recommandé

### 1. Premier lancement — récupérer les IDs des channels

```bat
.\run.bat --list-channels
```
Copier les IDs dans `config.json` → `channels`.

### 2. Galerie visuelle (workflow principal)

```bat
.\run.bat --gallery
```

- Scanne Telegram (messages non lus, filtre année)
- Télécharge les pochettes
- Affiche dans le navigateur une galerie de cartes avec :
  - Pochette + titre (sans underscores) + channel + date + taille
  - Badge **NOUVEAU** (pas dans ta collection) ou **INCERTAIN** (ressemble à un fichier existant)
  - Picto 📚 → recherche directe BDthèque (Google `site:bedetheque.com`)
  - Curseur zoom, filtres, recherche textuelle
  - Modal "Doublons écartés" avec correspondances Everything
- Cocher les albums voulus → **Enregistrer la sélection** → sauvegarder `selection.json` dans le dossier projet

### 3. Télécharger la sélection

```bat
.\run.bat --download-selection
```

- Télécharge uniquement les fichiers cochés
- Si "Marquer comme lu" était coché dans la galerie : avance le curseur Telegram

### 4. Rapport de revue (optionnel)

```bat
.\run.bat --review
```
Génère un rapport HTML comparatif Telegram vs collection (sans télécharger).

### 5. Mode automatique (sans galerie)

```bat
.\run.bat
```
Télécharge automatiquement les `max_downloads_per_run` premiers fichiers non-doublons.

```bat
.\run.bat --dry-run
```
Simulation : liste ce qui serait téléchargé sans rien faire.

---

## 📁 Structure du projet

```
projetBDTelegram/
├── main.py                 # Point d'entrée principal
├── telegram_scraper.py     # Scan des messages Telegram
├── gallery_generator.py    # Galerie HTML + téléchargement pochettes
├── downloader.py           # Téléchargement des fichiers
├── everything_checker.py   # Connexion à l'API Everything
├── fuzzy_matcher.py        # Comparaison floue des noms
├── report_generator.py     # Rapport HTML --review
├── logger.py               # Logs colorés console
├── run.bat                 # Lanceur (active le venv automatiquement)
├── install_task.bat        # Installation dépendances
├── requirements.txt        # Dépendances Python
├── config.example.json     # Modèle de configuration
├── config.json             # ← À créer (ignoré par git)
├── thumbs/                 # ← Cache des pochettes (ignoré par git)
└── venv/                   # ← Environnement virtuel (ignoré par git)
```

---

## 🔑 Obtenir les credentials Telegram

1. Aller sur [my.telegram.org](https://my.telegram.org)
2. Se connecter avec son numéro de téléphone
3. **API development tools** → créer une application
4. Copier `api_id` et `api_hash` dans `config.json`

> ⚠️ Au premier lancement, Telegram demande une authentification par SMS. Une fois la session créée (`telegram_bd_session.session`), les lancements suivants sont automatiques.

---

## ⚡ Performance & limites Telegram

- **Vitesse** : limitée à ~500 kB/s pour les comptes non-Premium. Telegram Premium supprime cette limite.
- **`download_concurrency: 2`** peut doubler le débit effectif si la limite est par connexion.
- **FloodWait** : géré automatiquement (pause en cas de rate-limit Telegram).
- **ToS** : ne pas dépasser 3-5 téléchargements simultanés pour rester dans les clous.

---

## 🐍 Activer le venv manuellement

```bat
venv\Scripts\activate
```

`run.bat` l'active automatiquement à chaque lancement.
