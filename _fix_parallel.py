import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('main.py', encoding='utf-8') as f:
    content = f.read()

# Replace the download_path/delay/session_name block + the entire download loop
old = '''    api_id        = config["api_id"]
    api_hash      = config["api_hash"]
    download_path = config["download_path"]
    delay_between = config.get("delay_between_downloads", 5)
    session_name  = config.get("session_name", "telegram_bd_session")

    log_separator()
    log_info(f"Telechargement depuis selection.json : {len(selection)} fichier(s)")
    if mark_read:
        log_info("Option 'Marquer comme lu' activee")
    log_separator()

    stats = {"downloaded": 0, "errors": 0}

    async with TelegramClient(session_name, api_id, api_hash) as client:
        log_success("Connexion Telegram etablie")

        for i, entry in enumerate(selection, 1):
            channel    = entry["channel"]
            message_id = entry["message_id"]
            filename   = entry["filename"]

            print(f"\\n  [{i}/{len(selection)}] {filename}")

            try:
                entity = await client.get_entity(channel)
                msg    = await client.get_messages(entity, ids=message_id)
                if msg is None:
                    log_error(f"  Message {message_id} introuvable.")
                    stats["errors"] += 1
                    continue

                file_info = {
                    "filename":   filename,
                    "file_size":  msg.document.size if msg.document else 0,
                    "message":    msg,
                    "message_id": message_id,
                }
                result = await download_file(client, file_info, download_path)
                if result:
                    stats["downloaded"] += 1
                    if i < len(selection):
                        log_info(f"  Pause {delay_between}s...")
                        await asyncio.sleep(delay_between)
                else:
                    stats["errors"] += 1

            except Exception as e:
                log_error(f"  Erreur pour {filename} : {e}")
                stats["errors"] += 1

        # Marquer comme lus si demande
        if mark_read and scan_boundary:
            log_separator()
            log_info("Marquage des channels comme lus (curseur Telegram avance)...")
            read_ids = {int(ch): mid for ch, mid in scan_boundary.items()}
            await mark_channels_as_read(client, read_ids)'''

new = '''    api_id              = config["api_id"]
    api_hash            = config["api_hash"]
    download_path       = config["download_path"]
    delay_between       = config.get("delay_between_downloads", 5)
    session_name        = config.get("session_name", "telegram_bd_session")
    download_concurrency = config.get("download_concurrency", 1)

    log_separator()
    log_info(f"Telechargement depuis selection.json : {len(selection)} fichier(s)")
    log_info(f"Telechargements simultanes          : {download_concurrency}")
    if mark_read:
        log_info("Option \\'Marquer comme lu\\' activee")
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
                    result = await download_file(client, file_info, download_path)
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
            await mark_channels_as_read(client, read_ids)'''

if old in content:
    content = content.replace(old, new)
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Done - parallel downloads added")
else:
    # Try to find where it differs
    for i, (a, b) in enumerate(zip(old, content[content.find('    api_id        = config["api_id"]'):])):
        if a != b:
            print(f"Diff at pos {i}: {repr(old[max(0,i-20):i+20])} vs {repr(b)}")
            break
    print("Not found")
