#!/usr/bin/env python3
"""
BD Telegram Downloader
======================
Télécharge automatiquement les BD (PDF/CBR/CBZ) depuis des channels Telegram
privés, en évitant les doublons grâce à l'API HTTP du logiciel Everything.
Seuls les messages NON LUS sont traités. Après téléchargement, les messages
traités sont marqués comme lus dans Telegram. Les messages non traités (quota
atteint) restent non lus pour la prochaine exécution.

Usage :
    python main.py                 # Telechargement reel
    python main.py --dry-run       # Simulation (rien telecharge ni marque comme lu)
    python main.py --test          # Teste la connexion a Everything uniquement
    python main.py --list-channels # Liste vos channels Telegram avec leurs IDs
    python main.py --review        # Rapport HTML de comparaison Telegram vs collection
"""
import asyncio
import json
import os
import sys
import argparse
import time
from datetime import datetime, timezone

from telethon import TelegramClient

from logger import log_info, log_success, log_skip, log_error, log_separator
from everything_checker import file_exists_in_everything, test_everything_connection, search_by_keywords
from telegram_scraper import get_bd_files, mark_channels_as_read, list_subscribed_channels
from downloader import download_file
from fuzzy_matcher import rank_matches
from report_generator import generate_html_report, open_in_browser
from gallery_generator import (
    scan_gallery_files, download_all_covers, generate_gallery_html
)

CONFIG_FILE = "config.json"


# ─────────────────────────────────────────────
# Chargement de la configuration
# ─────────────────────────────────────────────

def load_config():
    if not os.path.exists(CONFIG_FILE):
        log_error(f"Fichier de configuration introuvable : {CONFIG_FILE}")
        log_error("Copiez config.example.json en config.json et remplissez vos informations.")
        log_error("Obtenez vos api_id et api_hash sur https://my.telegram.org")
        sys.exit(1)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    required = ["api_id", "api_hash", "channels", "download_path"]
    for key in required:
        if key not in config:
            log_error(f"Clé manquante dans config.json : '{key}'")
            sys.exit(1)

    if config["api_id"] == 12345678:
        log_error("Vous n'avez pas encore rempli api_id dans config.json !")
        log_error("Rendez-vous sur https://my.telegram.org pour obtenir vos credentials.")
        sys.exit(1)

    if config.get("start_date"):
        try:
            config["start_date_dt"] = datetime.strptime(config["start_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            log_error("Format start_date invalide. Utilisez YYYY-MM-DD.")
            sys.exit(1)
    else:
        config["start_date_dt"] = None

    return config


# ─────────────────────────────────────────────
# Commande : tester la connexion Everything
# ─────────────────────────────────────────────

def cmd_test(config):
    everything_url = config.get("everything_api_url", "http://localhost:8070")
    log_separator()
    log_info(f"Test de connexion a Everything : {everything_url}")
    if test_everything_connection(everything_url):
        log_success("Everything est accessible !")
    else:
        log_error("Impossible de contacter Everything.")
        log_error("Verifiez que le serveur HTTP est actif dans Everything ->")
        log_error("  Outils -> Options -> Serveur HTTP -> Port 8070 -> Activer")
    log_separator()


# ─────────────────────────────────────────────
# Commande : lister les channels
# ─────────────────────────────────────────────

async def cmd_list_channels(config):
    api_id       = config["api_id"]
    api_hash     = config["api_hash"]
    session_name = config.get("session_name", "telegram_bd_session")

    log_separator()
    log_info("Liste de vos channels / groupes Telegram")
    log_info("Copiez les IDs voulus dans config.json -> \"channels\"")
    log_separator()

    async with TelegramClient(session_name, api_id, api_hash) as client:
        await list_subscribed_channels(client)


# ─────────────────────────────────────────────
# Commande : rapport de revue HTML
# ─────────────────────────────────────────────

async def cmd_review(config):
    """
    Scanne les messages non lus, recherche les correspondances dans Everything
    via mots-cles + fuzzy matching, et genere un rapport HTML.
    """
    api_id        = config["api_id"]
    api_hash      = config["api_hash"]
    channels      = config["channels"]
    everything_url = config.get("everything_api_url", "http://localhost:8070")
    days_lookback  = config.get("days_lookback", 30)
    session_name   = config.get("session_name", "telegram_bd_session")
    search_paths   = config.get("bd_search_paths", [])  # dossiers BD a fouiller
    threshold_dup  = config.get("fuzzy_threshold_duplicate", 85)
    threshold_rev  = config.get("fuzzy_threshold_review", 50)
    filename_filter = config.get("filename_contains_any", [])

    log_separator()
    log_info("Mode REVUE — generation du rapport HTML")
    log_info(f"Seuil DOUBLON   : {threshold_dup}%  (>= : sera ignore)")
    log_info(f"Seuil INCERTAIN : {threshold_rev}%  (entre {threshold_rev}-{threshold_dup-1}% : a verifier)")
    if search_paths:
        log_info(f"Dossiers BD     : {', '.join(search_paths)}")
    else:
        log_info("Dossiers BD     : tous (bd_search_paths non configure, recherche globale)")
    if filename_filter:
        log_info(f"Filtre noms de fichiers : contient l'un de {filename_filter}")
    log_separator()

    if not test_everything_connection(everything_url):
        log_error("Everything n'est pas accessible. Arret.")
        sys.exit(1)
    log_success("Everything accessible")

    async with TelegramClient(session_name, api_id, api_hash) as client:
        log_success("Connexion Telegram etablie")
        files, _ = await get_bd_files(client, channels, days_lookback,
                                      filename_filter=filename_filter)

    log_separator()
    log_info(f"{len(files)} fichier(s) BD non lu(s) trouve(s) — recherche des correspondances...")

    for i, file_info in enumerate(files, 1):
        fname = file_info["filename"]
        print(f"  [{i}/{len(files)}] {fname}", end="\r")

        results  = search_by_keywords(fname, search_paths, everything_url)
        matches  = rank_matches(fname, results)
        top_score = matches[0]["score"] if matches else 0

        if top_score >= threshold_dup:
            rec = "DOUBLON"
        elif top_score >= threshold_rev:
            rec = "INCERTAIN"
        else:
            rec = "NOUVEAU"

        file_info["matches"]        = matches[:3]
        file_info["recommendation"] = rec

    print()  # newline apres le compteur

    # Generer le rapport
    ts          = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"review_{ts}.html"
    generate_html_report(files, output_path)
    log_success(f"Rapport genere : {output_path}")
    open_in_browser(output_path)


# ─────────────────────────────────────────────
# Commande : galerie visuelle de selection
# ─────────────────────────────────────────────

async def cmd_gallery(config):
    """
    1. Scan Telegram (non lus, filtre annee)
    2. Verifie Everything -> ecarte les DOUBLONS
    3. Limite aux N premiers (max_downloads_per_run)
    4. Telecharge les couvertures (photos Telegram precedentes)
    5. Genere gallery.html + ouvre le navigateur
    """
    api_id         = config["api_id"]
    api_hash       = config["api_hash"]
    channels       = config["channels"]
    everything_url = config.get("everything_api_url", "http://localhost:8070")
    session_name   = config.get("session_name", "telegram_bd_session")
    search_paths   = config.get("bd_search_paths", [])
    threshold_dup  = config.get("fuzzy_threshold_duplicate", 85)
    threshold_rev  = config.get("fuzzy_threshold_review", 50)
    filename_filter   = config.get("filename_contains_any", [])
    # max_gallery_size : nb max de fichiers a scanner/afficher dans la galerie
    # (utilise max_downloads_per_run comme fallback pour compatibilite)
    max_cards         = config.get("max_gallery_size", config.get("max_downloads_per_run", 50))
    if max_cards == 0:
        max_cards = 9999
    thumb_concurrency = config.get("thumb_concurrency", 5)

    log_separator()
    log_info("Mode GALERIE")
    log_info(f"Max cartes dans la galerie : {max_cards}")
    if filename_filter:
        log_info(f"Filtre noms              : {filename_filter}")
    log_separator()

    if not test_everything_connection(everything_url):
        log_error("Everything n'est pas accessible. Arret.")
        sys.exit(1)
    log_success("Everything accessible")

    project_dir    = os.path.abspath(".")
    all_candidates = []
    doublons_list  = []
    scan_boundary  = {}  # {str(channel): max_message_id scanne}

    async with TelegramClient(session_name, api_id, api_hash) as client:
        log_success("Connexion Telegram etablie")

        # 1. Charger les dialogs pour read_inbox_max_id
        log_info("Chargement des dialogs...")
        dialogs = await client.get_dialogs()
        dialog_by_id = {d.entity.id: d for d in dialogs}

        for channel in channels:
            try:
                entity       = await client.get_entity(channel)
                channel_name = getattr(entity, "title", str(channel))
                entity_id    = entity.id
                log_info(f"Scan channel : {channel_name}")

                dialog      = dialog_by_id.get(entity_id)
                read_max_id = dialog.dialog.read_inbox_max_id if dialog else 0

                if dialog and dialog.unread_count == 0:
                    log_skip(f"  Aucun message non lu")
                    continue

                # 2. Scan oldest-first avec detection de couvertures
                raw, max_scanned = await scan_gallery_files(
                    client, entity, channel, channel_name,
                    read_max_id,
                    filename_filter=filename_filter,
                    limit=max_cards,
                    start_date_dt=config.get("start_date_dt")
                )
                # Memoriser la frontiere du scan pour ce channel
                if max_scanned > 0:
                    scan_boundary[str(channel)] = max_scanned
                log_info(f"  {len(raw)} fichier(s) collecte(s) (limite : {max_cards})")

                # 3. Separer doublons / candidats via Everything
                for f in raw:
                    try:
                        exists = file_exists_in_everything(
                            f["filename"], file_size=f["file_size"], api_url=everything_url
                        )
                    except Exception:
                        log_error("Everything inaccessible. Arret.")
                        return
                    if exists:
                        # Chercher la meilleure correspondance pour le tableau
                        results = search_by_keywords(f["filename"], search_paths, everything_url, count=1)
                        matches = rank_matches(f["filename"], results) if results else []
                        doublons_list.append({
                            "filename":     f["filename"],
                            "channel_name": f["channel_name"],
                            "size_mb":      round(f["file_size"] / 1024 / 1024, 1),
                            "match":        matches[0]["filename"] if matches else "(nom exact)",
                            "score":        matches[0]["score"]    if matches else 100,
                        })
                    else:
                        all_candidates.append(f)

            except Exception as e:
                log_error(f"Erreur channel {channel} : {e}")

        log_separator()
        log_info(f"{len(all_candidates)} candidat(s), {len(doublons_list)} doublon(s) ecarte(s)")

        # 4. candidates = ceux qui ne sont pas doublons (deja limites par le scan)
        candidates = all_candidates
        log_info(f"Galerie : {len(candidates)} carte(s) a afficher")

        # 5. Fuzzy matching pour l'affichage (optionnel, ne filtre pas)
        log_info("Calcul des scores de correspondance...")
        for f in candidates:
            results  = search_by_keywords(f["filename"], search_paths, everything_url)
            matches  = rank_matches(f["filename"], results)
            top_score = matches[0]["score"] if matches else 0
            f["matches"]        = matches[:2]
            f["recommendation"] = "INCERTAIN" if top_score >= threshold_rev else "NOUVEAU"
        # 5b. Afficher la liste des candidats dans la console (titre + date)
        log_separator()
        log_info(f"  {'DATE':<12} {'CH':<18} FICHIER")
        log_info(f"  {'-'*11} {'-'*18} {'-'*52}")
        for f in candidates:
            date_str = f["date"].strftime("%d/%m/%Y")
            ch_name  = f["channel_name"][:18]
            fname    = f["filename"]
            rec      = f.get("recommendation", "?")
            marker   = "~" if rec == "INCERTAIN" else " "
            log_info(f"  {date_str:<12} {ch_name:<18}{marker} {fname}")
        log_separator()


        # 6. Telecharger les couvertures
        log_separator()
        thumb_map = await download_all_covers(client, candidates, concurrency=thumb_concurrency)

    # 7. Generer gallery.html
    output_path = "gallery.html"
    generate_gallery_html(candidates, doublons_list, thumb_map,
                          output_path, project_dir, scan_boundary=scan_boundary)
    log_success(f"Galerie generee : {output_path}  ({len(candidates)} cartes)")
    log_info(f"Apres selection -> sauvegarder selection.json dans : {project_dir}")
    log_info("Puis lancer : run.bat --download-selection")
    open_in_browser(output_path)

    # 8. Tableau texte des doublons ecartes
    if doublons_list:
        _print_doublons_table(doublons_list)


def _print_doublons_table(doublons_list):
    """Affiche un tableau texte des doublons ecartes avec leur correspondance Everything."""
    from colorama import Fore, Style
    W_FILE  = 52
    W_SCORE = 7
    W_MATCH = 55
    sep = f"+{'-'*(W_FILE+2)}+{'-'*(W_SCORE+2)}+{'-'*(W_MATCH+2)}+"
    hdr = f"| {'FICHIER TELEGRAM':<{W_FILE}} | {'SCORE':>{W_SCORE}} | {'CORRESPONDANCE COLLECTION':<{W_MATCH}} |"

    print()
    print(Fore.YELLOW + f"  DOUBLONS ECARTES ({len(doublons_list)} fichiers deja dans votre collection)")
    print(Style.DIM + sep)
    print(Style.DIM + hdr)
    print(Style.DIM + sep)
    for d in doublons_list:
        fn    = d["filename"][:W_FILE]
        score = f"{d['score']}%"
        match = d["match"][:W_MATCH]
        print(Style.DIM + f"| {fn:<{W_FILE}} | {score:>{W_SCORE}} | {match:<{W_MATCH}} |")
    print(Style.DIM + sep)
    print()


# ─────────────────────────────────────────────
# Commande : telecharger depuis selection.json
# ─────────────────────────────────────────────

async def cmd_download_selection(config):
    """
    Lit selection.json et telecharge les fichiers choisis.
    Supporte deux formats :
      - Ancien : liste de {channel, message_id, filename}
      - Nouveau : {mark_read, scan_boundary, files: [...]}
    Si mark_read est True, marque les channels comme lus jusqu'a scan_boundary.
    """
    SELECTION_FILE = "selection.json"
    if not os.path.exists(SELECTION_FILE):
        log_error(f"{SELECTION_FILE} introuvable dans le dossier du projet.")
        log_error("Lancez d'abord : run.bat --gallery  puis sauvegardez la selection.")
        sys.exit(1)

    with open(SELECTION_FILE, encoding="utf-8") as fh:
        raw_data = json.load(fh)

    # Compatibilite ancien format (liste simple)
    if isinstance(raw_data, list):
        selection  = raw_data
        mark_read  = False
        scan_boundary = {}
    else:
        selection     = raw_data.get("files", [])
        mark_read     = raw_data.get("mark_read", False)
        scan_boundary = raw_data.get("scan_boundary", {})

    if not selection:
        log_info("selection.json est vide. Rien a telecharger.")
        return

    api_id              = config["api_id"]
    api_hash            = config["api_hash"]
    download_path       = config["download_path"]
    delay_between       = config.get("delay_between_downloads", 5)
    session_name        = config.get("session_name", "telegram_bd_session")
    download_concurrency = config.get("download_concurrency", 1)

    log_separator()
    log_info(f"Telechargement depuis selection.json : {len(selection)} fichier(s)")
    log_info(f"Telechargements simultanes          : {download_concurrency}")
    if mark_read:
        log_info("Option \'Marquer comme lu\' activee")
    log_separator()

    stats = {"downloaded": 0, "errors": 0}
    lock  = asyncio.Lock()

    async with TelegramClient(session_name, api_id, api_hash) as client:
        log_success("Connexion Telegram etablie")

        sem = asyncio.Semaphore(download_concurrency)

        async def download_one(i, entry):
            channel    = entry["channel"]
            message_id = entry["message_id"]
            filename   = entry["filename"]

            async with sem:
                log_info(f"  [{i}/{len(selection)}] {filename}")
                try:
                    entity = await client.get_entity(channel)
                    msg    = await client.get_messages(entity, ids=message_id)
                    if msg is None:
                        log_error(f"  Introuvable : {filename}")
                        async with lock: stats["errors"] += 1
                        return

                    file_info = {
                        "filename":   filename,
                        "file_size":  msg.document.size if msg.document else 0,
                        "message":    msg,
                        "message_id": message_id,
                    }
                    result = await download_file(client, file_info, download_path, task_idx=i)
                    async with lock:
                        if result:
                            stats["downloaded"] += 1
                        else:
                            stats["errors"] += 1

                    # Pause anti-flood apres chaque telechargement
                    if delay_between > 0:
                        await asyncio.sleep(delay_between)

                except Exception as e:
                    log_error(f"  Erreur pour {filename} : {e}")
                    async with lock: stats["errors"] += 1

        await asyncio.gather(*[download_one(i, e) for i, e in enumerate(selection, 1)])

        # Marquer comme lus si demande
        if mark_read and scan_boundary:
            log_separator()
            log_info("Marquage des channels comme lus (curseur Telegram avance)...")
            read_ids = {int(ch): mid for ch, mid in scan_boundary.items()}
            await mark_channels_as_read(client, read_ids)

    log_separator()
    log_success(f"Telecharges : {stats['downloaded']}")
    if stats["errors"]:
        log_error(f"Erreurs     : {stats['errors']}")
    log_separator()

    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    done = f"selection_done_{ts}.json"
    os.rename(SELECTION_FILE, done)
    log_info(f"selection.json archive en : {done}")


# ─────────────────────────────────────────────
# Commande principale : téléchargement
# ─────────────────────────────────────────────

async def run(config, dry_run=False):
    api_id               = config["api_id"]
    api_hash             = config["api_hash"]
    channels             = config["channels"]
    download_path        = config["download_path"]
    everything_url       = config.get("everything_api_url", "http://localhost:8070")
    days_lookback        = config.get("days_lookback", 30)
    session_name         = config.get("session_name", "telegram_bd_session")
    max_downloads        = config.get("max_downloads_per_run", 0)   # 0 = illimite
    delay_between        = config.get("delay_between_downloads", 5)  # secondes
    unlimited            = (max_downloads == 0)
    filename_filter      = config.get("filename_contains_any", [])   # [] = pas de filtre

    log_separator()
    log_info(f"BD Telegram Downloader — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    if dry_run:
        log_info("MODE SIMULATION (--dry-run) : rien ne sera telecharge ni marque comme lu")
    quota_label = "illimite" if unlimited else str(max_downloads)
    log_info(f"Max telechargements / execution : {quota_label}")
    log_info(f"Delai entre telechargements     : {delay_between}s")
    log_info(f"Channels configures             : {len(channels)}")
    log_info(f"Destination                     : {download_path}")
    log_info(f"Everything API                  : {everything_url}")
    log_separator()

    # Vérifier Everything avant de commencer
    if not test_everything_connection(everything_url):
        log_error("Everything n'est pas accessible. Arret du script.")
        log_error("Verifiez que le serveur HTTP Everything est actif (port 8070).")
        sys.exit(1)
    log_success("Everything accessible")

    stats = {
        "found":      0,
        "downloaded": 0,
        "skipped":    0,   # doublons
        "errors":     0,
        "remaining":  0,   # non traités (quota atteint)
    }

    # processed_max_ids : channel → ID du dernier message effectivement traité
    # (téléchargé OU ignoré comme doublon)
    # On avance le curseur même pour les doublons : ils sont "vus" et n'ont pas
    # besoin d'être revérifiés la prochaine fois.
    processed_max_ids = {}

    async with TelegramClient(session_name, api_id, api_hash) as client:
        log_success("Connexion Telegram etablie")
        log_separator()

        # 1. Récupérer tous les fichiers BD non lus (triés oldest-first)
        files, read_ids = await get_bd_files(client, channels, days_lookback,
                                             filename_filter=filename_filter, start_date_dt=config.get("start_date_dt"))
        stats["found"] = len(files)

        log_separator()
        log_info(f"{len(files)} fichier(s) BD non lu(s) trouve(s) au total")

        if not unlimited and len(files) > max_downloads:
            log_info(f"Quota actif : traitement des {max_downloads} premiers "
                     f"({len(files) - max_downloads} seront traites aux prochaines executions)")
        log_separator()

        if not files:
            log_info("Rien a traiter. Tout est deja lu !")
            _print_report(stats)
            return

        # 2. Traiter fichier par fichier dans la limite du quota
        new_downloads = 0          # compteur de vrais téléchargements uniquement
        everything_ok = True

        for file_info in files:
            # Arreter si on a atteint le quota (sauf si illimite)
            if not unlimited and new_downloads >= max_downloads:
                stats["remaining"] = len(files) - files.index(file_info)
                break

            filename     = file_info["filename"]
            channel_name = file_info["channel_name"]
            channel      = file_info["channel"]
            msg_id       = file_info["message_id"]
            date_str     = file_info["date"].strftime("%d/%m/%Y")

            print(f"\n  [{new_downloads + 1}] {filename}")
            print(f"   Channel : {channel_name}  |  Date : {date_str}")

            # Vérifier doublon via Everything
            try:
                exists = file_exists_in_everything(
                    filename,
                    file_size=file_info["file_size"],
                    api_url=everything_url,
                )
            except Exception:
                log_error("Everything inaccessible en cours de traitement. Arret.")
                everything_ok = False
                break

            if exists:
                log_skip(f"Doublon ignore : {filename}")
                stats["skipped"] += 1
                # On avance quand même le curseur pour ce channel
                _update_max_id(processed_max_ids, channel, msg_id)
                continue

            # Télécharger (ou simuler)
            if dry_run:
                size_mb = file_info["file_size"] / 1024 / 1024
                log_info(f"[SIMULATION] A telecharger : {filename} ({size_mb:.1f} Mo)")
                new_downloads += 1
                stats["downloaded"] += 1
                _update_max_id(processed_max_ids, channel, msg_id)
            else:
                result = await download_file(client, file_info, download_path)
                if result:
                    new_downloads += 1
                    stats["downloaded"] += 1
                    _update_max_id(processed_max_ids, channel, msg_id)

                    # Délai anti-flood entre les téléchargements (sauf le dernier)
                    if new_downloads < max_downloads:
                        log_info(f"Pause {delay_between}s avant le prochain telechargement...")
                        await asyncio.sleep(delay_between)
                else:
                    stats["errors"] += 1
                    # On n'avance pas le curseur en cas d'erreur : on réessaiera

        # 3. Marquer comme lus uniquement les messages traités
        if not dry_run and everything_ok and processed_max_ids:
            log_separator()
            log_info("Marquage des messages traites comme lus dans Telegram...")
            await mark_channels_as_read(client, processed_max_ids)

    _print_report(stats)


def _update_max_id(processed_max_ids, channel, msg_id):
    """Met à jour le curseur du channel avec l'ID le plus élevé traité."""
    current = processed_max_ids.get(channel, 0)
    if msg_id > current:
        processed_max_ids[channel] = msg_id


def _print_report(stats):
    log_separator()
    log_info("--- RAPPORT FINAL ---")
    log_info(f"  Fichiers non lus trouves : {stats['found']}")
    log_success(f"  Telecharges              : {stats['downloaded']}")
    log_skip(f"  Doublons ignores         : {stats['skipped']}")
    if stats["errors"]:
        log_error(f"  Erreurs                  : {stats['errors']}")
    if stats["remaining"] > 0:
        log_info(f"  Restants (prochain run)  : {stats['remaining']}")
    log_separator()


# ─────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=(
            "BD Telegram Downloader\n"
            "Recupere les BD (PDF/CBR/CBZ) non lues depuis des channels Telegram\n"
            "en evitant les doublons via Everything. Limite a max_downloads_per_run\n"
            "telechargements par execution pour eviter les blocages Telegram."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulation : liste ce qui serait telecharge sans rien faire",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Teste uniquement la connexion a Everything et quitte",
    )
    parser.add_argument(
        "--list-channels",
        action="store_true",
        help="Liste tous vos channels Telegram avec leurs IDs (a copier dans config.json)",
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help="Genere un rapport HTML de comparaison Telegram vs collection (sans telecharger)",
    )
    parser.add_argument(
        "--gallery",
        action="store_true",
        help="Galerie visuelle : voir les couvertures et selectionner les BD a telecharger",
    )
    parser.add_argument(
        "--download-selection",
        action="store_true",
        help="Telecharge les BD selectionnees dans selection.json (genere par --gallery)",
    )
    args = parser.parse_args()

    config = load_config()

    if args.test:
        cmd_test(config)
        return

    if args.list_channels:
        asyncio.run(cmd_list_channels(config))
        return

    if args.review:
        asyncio.run(cmd_review(config))
        return

    if args.gallery:
        asyncio.run(cmd_gallery(config))
        return

    if args.download_selection:
        asyncio.run(cmd_download_selection(config))
        return

    asyncio.run(run(config, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
