"""
downloader.py — Téléchargement des fichiers depuis Telegram

Utilise le client Telethon pour télécharger un fichier media vers le dossier
de destination, avec barre de progression en console.
"""
import os
from tqdm import tqdm
from logger import log_success, log_error


async def download_file(client, file_info, download_path, task_idx=None):
    """
    Télécharge un fichier depuis Telegram vers le dossier de destination.

    Paramètres :
        client        : TelegramClient authentifié
        file_info     : dict retourné par telegram_scraper.get_bd_files()
        download_path : chemin du dossier de destination
        task_idx      : index de la tâche pour le positionnement de tqdm

    Retourne le chemin du fichier téléchargé, ou None en cas d'erreur.
    """
    filename = file_info["filename"]
    file_size = file_info["file_size"]
    size_mb = file_size / (1024 * 1024)

    # Créer le dossier de destination si nécessaire
    try:
        os.makedirs(download_path, exist_ok=True)
    except OSError as e:
        log_error(f"Impossible de créer le dossier '{download_path}' : {e}")
        return None

    # Chemin final (avec suffixe si le nom existe déjà localement)
    dest_path = os.path.join(download_path, filename)
    dest_path = _unique_path(dest_path)
    final_filename = os.path.basename(dest_path)

    print(f"  ⬇  {final_filename}  ({size_mb:.1f} Mo)")

    try:
        with tqdm(
            total=file_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc="     ",
            ncols=70,
            leave=True,
            position=task_idx if task_idx is not None else 0,
            mininterval=2.0 if os.environ.get("WEB_UI_MODE") == "1" else 0.1,
        ) as pbar:
            def progress_callback(current, total):
                pbar.update(current - pbar.n)

            await client.download_media(
                file_info["message"],
                file=dest_path,
                progress_callback=progress_callback,
            )

        log_success(f"Téléchargé → {final_filename}")
        return dest_path

    except OSError as e:
        log_error(f"Erreur disque pour '{filename}' : {e}")
        _cleanup(dest_path)
        return None
    except Exception as e:
        log_error(f"Erreur téléchargement '{filename}' : {e}")
        _cleanup(dest_path)
        return None


def _unique_path(path):
    """
    Si le chemin existe déjà localement, ajoute un suffixe numérique.
    Ex: MonFichier.cbz → MonFichier_2.cbz
    """
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    counter = 2
    while os.path.exists(f"{base}_{counter}{ext}"):
        counter += 1
    return f"{base}_{counter}{ext}"


def _cleanup(path):
    """Supprime un fichier partiellement téléchargé en cas d'erreur."""
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
