"""
telegram_scraper.py — Connexion Telegram et récupération des fichiers BD non lus

Stratégie "non lus" :
  - Pour chaque channel, on lit le `read_inbox_max_id` depuis le dialog.
    Ce champ correspond à l'ID du dernier message que le compte Telegram a
    marqué comme lu. On ne récupère que les messages au-delà de cet ID.
  - Les résultats sont triés par ID croissant (plus ancien en premier) pour
    traiter les messages dans l'ordre chronologique.
  - `days_lookback` n'est utilisé QUE si le dialog est introuvable (cas rare).
  - Après téléchargement, main.py appelle mark_channels_as_read() avec
    uniquement les IDs des messages effectivement traités.
"""
import os
from datetime import datetime, timedelta, timezone
from logger import log_info, log_error, log_skip, log_success

# Extensions BD supportées
SUPPORTED_EXTENSIONS = {".pdf", ".cbr", ".cbz"}

# Correspondance MIME type → extension
MIME_TO_EXT = {
    "application/pdf":               ".pdf",
    "application/x-cbr":             ".cbr",
    "application/x-cbz":             ".cbz",
    "application/zip":               ".cbz",
    "application/x-zip-compressed":  ".cbz",
    "application/x-rar-compressed":  ".cbr",
    "application/vnd.rar":           ".cbr",
    "application/vnd.comicbook+zip": ".cbz",
    "application/vnd.comicbook-rar": ".cbr",
}


async def list_subscribed_channels(client):
    """
    Liste tous les channels et groupes auxquels le compte est abonné,
    avec leurs IDs (format à copier dans config.json) et le nb de non-lus.
    """
    from telethon.tl.types import Channel, Chat

    dialogs = await client.get_dialogs()

    channels = []
    for d in dialogs:
        entity = d.entity
        # Ne garder que les channels et supergroupes (pas les chats privés)
        if isinstance(entity, Channel):
            channels.append({
                "name":    entity.title,
                "id":      -(1000000000000 + entity.id),  # format négatif pour config
                "unread":  d.unread_count,
                "type":    "Groupe" if entity.megagroup else "Channel",
            })

    if not channels:
        log_info("Aucun channel/groupe trouve.")
        return

    log_info(f"{len(channels)} channel(s)/groupe(s) trouve(s) :\n")
    print(f"  {'NOM':<45} {'ID (pour config.json)':<22} {'TYPE':<10} {'NON LUS'}")
    print(f"  {'-'*45} {'-'*22} {'-'*10} {'-'*7}")
    for ch in sorted(channels, key=lambda x: x["name"].lower()):
        unread = str(ch["unread"]) if ch["unread"] else "-"
        print(f"  {ch['name']:<45} {ch['id']:<22} {ch['type']:<10} {unread}")

    print()
    log_info("Copiez les IDs negatifs dans config.json -> \"channels\": [ id1, id2, ... ]")




async def get_bd_files(client, channels, days_lookback=30, filename_filter=None, start_date_dt=None):
    """
    Parcourt les channels Telegram et retourne UNIQUEMENT les fichiers BD
    presents dans les messages non lus, tries du plus ancien au plus recent.

    `days_lookback` n'est utilise QUE comme fallback si le dialog n'est pas
    trouve (valeur par defaut large : 30 jours).
    `filename_filter` : liste de chaines — le fichier doit en contenir au moins une
                        (insensible a la casse). Ex: ["2025", "2026"]. [] = pas de filtre.

    Retourne un tuple :
        files     : liste de dicts, triee par message_id ASC (oldest first)
        read_ids  : dict {channel: read_inbox_max_id} — point de reprise par channel
    """
    found_files = []
    read_ids = {}  # Pour savoir où on en était AVANT ce scan (point de reprise)

    # Charger tous les dialogs une seule fois
    log_info("Chargement des dialogs Telegram...")
    dialogs = await client.get_dialogs()
    dialog_by_id = {d.entity.id: d for d in dialogs}

    for channel in channels:
        log_info(f"Analyse du channel : {channel}")
        try:
            entity = await client.get_entity(channel)
            channel_name = getattr(entity, "title", str(channel))
            entity_id = entity.id
            log_info(f"  → Nom : {channel_name}")

            dialog = dialog_by_id.get(entity_id)

            if dialog:
                read_max_id = dialog.dialog.read_inbox_max_id
                unread_count = dialog.unread_count
                read_ids[channel] = read_max_id

                if unread_count == 0:
                    log_skip(f"  → Aucun message non lu dans {channel_name}")
                    continue

                log_info(f"  → {unread_count} message(s) non lu(s) "
                         f"(depuis message ID #{read_max_id})")

                # Scan des messages non lus (min_id exclut les deja lus)
                channel_files = await _scan_messages(
                    client, entity, channel, channel_name,
                    min_id=read_max_id,
                    cutoff_date=None,
                    filename_filter=filename_filter,
                    start_date_dt=start_date_dt,
                )

            else:
                # Fallback : dialog introuvable, scan limité dans le temps
                log_info(f"  → Dialog introuvable, fallback sur {days_lookback} jours")
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_lookback)
                channel_files = await _scan_messages(
                    client, entity, channel, channel_name,
                    min_id=0,
                    cutoff_date=cutoff_date,
                    filename_filter=filename_filter,
                    start_date_dt=start_date_dt,
                )

            log_info(f"  → {len(channel_files)} fichier(s) BD non lu(s) trouvé(s)")
            found_files.extend(channel_files)

        except ValueError as e:
            log_error(f"Channel introuvable : {channel} — {e}")
            log_error("  Vérifiez l'ID du channel dans config.json")
        except Exception as e:
            log_error(f"Erreur sur le channel {channel} : {e}")

    # Trier globalement par ID croissant : traiter les plus anciens en premier
    found_files.sort(key=lambda f: f["message_id"])
    return found_files, read_ids


async def _scan_messages(client, entity, channel, channel_name, min_id, cutoff_date, filename_filter=None, start_date_dt=None):
    """
    Parcourt les messages d'un channel et retourne les fichiers BD trouves.
    filename_filter : liste de chaines dont au moins une doit apparaitre dans
                      le nom du fichier (insensible a la casse). None = pas de filtre.
    """
    channel_files = []
    skipped_filter = 0

    kwargs = {}
    if start_date_dt:
        kwargs['offset_date'] = start_date_dt
        kwargs['reverse'] = True
    else:
        kwargs['min_id'] = min_id

    async for message in client.iter_messages(entity, **kwargs):
        # Reverse=True gives oldest first. If we didn't use reverse=True, we get newest first.

        # Fallback date uniquement si pas de min_id
        if cutoff_date and message.date < cutoff_date:
            break

        if not message.document:
            continue

        filename, ext = _extract_filename_and_ext(message)
        if ext not in SUPPORTED_EXTENSIONS:
            continue

        # Filtre sur le contenu du nom de fichier (ex: annee 2025/2026)
        if filename_filter:
            fname_lower = filename.lower()
            if not any(term.lower() in fname_lower for term in filename_filter):
                skipped_filter += 1
                continue

        channel_files.append({
            "filename":     filename,
            "file_size":    message.document.size,
            "message_id":   message.id,
            "channel":      channel,
            "channel_name": channel_name,
            "message":      message,
            "date":         message.date,
        })

    if skipped_filter:
        log_info(f"  → {skipped_filter} fichier(s) ignore(s) (hors filtre filename_contains_any)")

    return channel_files


async def mark_channels_as_read(client, processed_max_ids):
    """
    Marque comme lus uniquement les messages effectivement traités.
    processed_max_ids : dict {channel: max_message_id_traité}

    Les messages non traités (au-delà du quota max_downloads_per_run)
    restent non lus et seront récupérés à la prochaine exécution.
    """
    for channel, max_id in processed_max_ids.items():
        try:
            entity = await client.get_entity(channel)
            await client.send_read_acknowledge(entity, max_id=max_id)
            channel_name = getattr(entity, "title", str(channel))
            log_info(f"  Marqué comme lu jusqu'au message #{max_id} dans : {channel_name}")
        except Exception as e:
            log_error(f"Impossible de marquer comme lu le channel {channel} : {e}")


def _extract_filename_and_ext(message):
    """
    Extrait le nom de fichier et son extension depuis un message Telegram.
    Fallback sur le MIME type si l'attribut filename est absent.
    """
    for attr in message.document.attributes:
        if hasattr(attr, "file_name") and attr.file_name:
            filename = attr.file_name.strip()
            ext = os.path.splitext(filename)[1].lower()
            return filename, ext

    mime = getattr(message.document, "mime_type", "") or ""
    ext = MIME_TO_EXT.get(mime, "")
    if ext:
        return f"telegram_msg_{message.id}{ext}", ext

    return f"telegram_msg_{message.id}", ""
