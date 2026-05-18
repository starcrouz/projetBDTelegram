import os
import sys
import json
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import subprocess
import threading
import queue
from telethon import TelegramClient

from contextlib import asynccontextmanager

app = FastAPI(title="BD Telegram Web UI")

# Dossier du projet (racine)
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Variables globales
current_process = None
telegram_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_client
    config_path = os.path.join(PROJECT_DIR, "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        api_id = config.get("api_id")
        api_hash = config.get("api_hash")
        session_name = config.get("session_name", "telegram_bd_session")
        session_path = os.path.join(PROJECT_DIR, session_name)
        
        if api_id and api_hash:
            telegram_client = TelegramClient(session_path, api_id, api_hash)
            # Gestion du lock SQLite : on essaie de se connecter
            try:
                await telegram_client.connect()
                print("TelegramClient connecté dans l'interface Web !")
            except Exception as e:
                print(f"Erreur de connexion Telegram : {e}")
                telegram_client = None
    
    yield
    
    if telegram_client:
        await telegram_client.disconnect()
        print("TelegramClient déconnecté.")

app = FastAPI(title="BD Telegram Web UI", lifespan=lifespan)

# Template de la page d'accueil avec un terminal virtuel
INDEX_HTML = r"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BD Telegram - Web UI</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
        .container { max-width: 95%; margin: 0 auto; }
        h1 { text-align: center; color: #38bdf8; }
        .header-panel { background: #1e293b; padding: 20px; border-radius: 8px; margin-bottom: 20px; display: flex; flex-direction: column; gap: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .settings { display: grid; grid-template-columns: auto 1fr auto 1fr; gap: 15px; align-items: center; background: #334155; padding: 15px; border-radius: 6px; }
        input[type="date"], input[type="text"], input[type="number"] { padding: 8px; border-radius: 4px; border: 1px solid #475569; background: #1e293b; color: white; width: 100%; box-sizing: border-box;}
        .form-label { font-weight: bold; color: #94a3b8; text-align: right; }
        .help-text { font-size: 11px; color: #64748b; margin-top: 2px;}
        .btn { background: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; transition: background 0.2s; }
        .btn:hover { background: #2563eb; }
        .btn-gallery { background: #10b981; }
        .btn-gallery:hover { background: #059669; }
        .btn-download { background: #8b5cf6; }
        .btn-download:hover { background: #7c3aed; }
        .gallery-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin-top: 20px; }
        .card { background: #1e293b; border-radius: 8px; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); display: flex; flex-direction: column; gap: 10px; border: 1px solid #334155; }
        .card img { max-width: 100%; height: auto; border-radius: 4px; max-height: 250px; object-fit: contain; background: #0f172a; }
        .card-title { font-weight: bold; font-size: 14px; word-break: break-all; }
        .card-meta { font-size: 12px; color: #94a3b8; }
        .status-NOUVEAU { color: #10b981; font-weight: bold; }
        .status-INCERTAIN { color: #f59e0b; font-weight: bold; }
        .status-DOUBLON { color: #ef4444; font-weight: bold; text-decoration: line-through; }
        .select-match { background: #334155; color: white; border: 1px solid #475569; padding: 5px; border-radius: 4px; width: 100%; margin-top: 5px;}
        .progress-container { width: 100%; background-color: #0f172a; border-radius: 4px; overflow: hidden; height: 8px; display: none; margin-top: 5px; }
        .progress-bar { width: 0%; height: 100%; background-color: #38bdf8; transition: width 0.2s; }
        .dl-status { font-size: 11px; color: #cbd5e1; text-align: right; }
        
        /* Modal Styles */
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.7); z-index: 1000; justify-content: center; align-items: center; }
        .modal-content { background: #1e293b; padding: 25px; border-radius: 8px; width: 90%; max-width: 600px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #334155; padding-bottom: 10px; }
        .modal-title { font-size: 18px; font-weight: bold; color: #38bdf8; }
        .close-btn { background: none; border: none; color: #94a3b8; font-size: 24px; cursor: pointer; }
        .close-btn:hover { color: white; }
        #modal-results { margin-top: 15px; max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
        .modal-result-item { background: #0f172a; padding: 10px; border-radius: 4px; cursor: pointer; border: 1px solid #334155; font-size: 13px; }
        .modal-result-item:hover { background: #334155; border-color: #38bdf8; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 BD Telegram - Mode SPA (Temps Réel)</h1>
        
        <div class="header-panel">
            <div class="settings">
                <div class="form-label">Date de départ :</div>
                <div>
                    <input type="date" id="start_date" onchange="updateConfig()">
                    <div class="help-text">Laissez vide pour le curseur automatique.</div>
                </div>
                
                <div class="form-label">Mots-clés (Filtre) :</div>
                <div>
                    <input type="text" id="filename_filter" onchange="updateConfig()" placeholder="ex: 2025, 2026, Casterman">
                    <div class="help-text">Séparés par des virgules.</div>
                </div>

                <div class="form-label">Téléchargements // :</div>
                <div>
                    <input type="number" id="download_concurrency" onchange="updateConfig()" min="1" max="20">
                    <div class="help-text">Fichiers téléchargés en simultané.</div>
                </div>
                
                <div class="form-label">Limite Scan (Max) :</div>
                <div>
                    <input type="number" id="max_downloads_per_run" onchange="updateConfig()">
                    <div class="help-text">Nombre max de BD affichées.</div>
                </div>
                
                <div class="form-label">Seuil Doublon :</div>
                <div>
                    <input type="number" id="fuzzy_threshold_duplicate" onchange="updateConfig()" min="0" max="100">
                    <div class="help-text">Score (0-100) pour ROUGE.</div>
                </div>
                
                <div class="form-label">Seuil Incertain :</div>
                <div>
                    <input type="number" id="fuzzy_threshold_review" onchange="updateConfig()" min="0" max="100">
                    <div class="help-text">Score (0-100) pour ORANGE.</div>
                </div>
            </div>    
            <div style="display:flex; gap:10px; justify-content: center; margin-top: 10px;">
                    <button class="btn" onclick="startDynamicScan()">🚀 Lancer le Scan Dynamique</button>
                    <div id="scan-status" style="margin-left: 20px; align-self: center; font-weight: bold; color: #38bdf8;">Prêt.</div>
                </div>
            </div>
        </div>

        <div class="gallery-grid" id="gallery">
            <!-- Les cartes s'ajouteront ici en temps réel -->
        </div>
    </div>

    <!-- Modal Recherche Manuelle -->
    <div class="modal-overlay" id="search-modal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title">🔍 Recherche sur le disque</div>
                <button class="close-btn" onclick="closeModal()">&times;</button>
            </div>
            <div style="display:flex; gap:10px;">
                <input type="text" id="modal-query" style="flex-grow:1; font-size:14px;" placeholder="Titre de la BD...">
                <button class="btn" id="modal-search-btn" onclick="executeModalSearch()">Chercher</button>
            </div>
            <div id="modal-results">
                <div class="help-text">Entrez un titre pour chercher.</div>
            </div>
        </div>
    </div>

    <script>
        const gallery = document.getElementById('gallery');
        const statusDiv = document.getElementById('scan-status');
        let dlSocket = null;
        let currentModalMsgId = null;
        let currentModalOriginal = null;

        // Connecter le websocket de téléchargement
        function initDownloadSocket() {
            dlSocket = new WebSocket(`ws://${window.location.host}/api/downloads_ws`);
            dlSocket.onmessage = function(event) {
                const msg = JSON.parse(event.data);
                if (msg.type === "status") {
                    const statusEl = document.getElementById(`dl-status-${msg.message_id}`);
                    if (statusEl) statusEl.innerText = msg.status;
                } else if (msg.type === "progress") {
                    const bar = document.getElementById(`dl-progress-${msg.message_id}`);
                    const container = document.getElementById(`dl-container-${msg.message_id}`);
                    const statusEl = document.getElementById(`dl-status-${msg.message_id}`);
                    if (bar && container) {
                        container.style.display = 'block';
                        const percent = (msg.current / msg.total) * 100;
                        bar.style.width = percent + '%';
                        if (statusEl) statusEl.innerText = `${(msg.current/1024/1024).toFixed(1)} / ${(msg.total/1024/1024).toFixed(1)} Mo`;
                    }
                }
            };
            dlSocket.onclose = () => setTimeout(initDownloadSocket, 2000);
        }
        initDownloadSocket();

        // Charger la config initiale
        fetch('/api/config').then(r=>r.json()).then(c => {
            if(c.start_date) document.getElementById('start_date').value = c.start_date;
            if(c.filename_filter) document.getElementById('filename_filter').value = c.filename_filter.join(', ');
            if(c.download_concurrency) document.getElementById('download_concurrency').value = c.download_concurrency;
            if(c.max_downloads_per_run) document.getElementById('max_downloads_per_run').value = c.max_downloads_per_run;
            if(c.fuzzy_threshold_duplicate) document.getElementById('fuzzy_threshold_duplicate').value = c.fuzzy_threshold_duplicate;
            if(c.fuzzy_threshold_review) document.getElementById('fuzzy_threshold_review').value = c.fuzzy_threshold_review;
        });

        function updateConfig() {
            const date = document.getElementById('start_date').value;
            const filterStr = document.getElementById('filename_filter').value;
            const filter = filterStr ? filterStr.split(',').map(s => s.trim()).filter(s => s) : [];
            const concurrency = parseInt(document.getElementById('download_concurrency').value) || 5;
            const maxDl = parseInt(document.getElementById('max_downloads_per_run').value) || 50;
            const threshDup = parseInt(document.getElementById('fuzzy_threshold_duplicate').value) || 85;
            const threshRev = parseInt(document.getElementById('fuzzy_threshold_review').value) || 50;
            
            fetch('/api/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    start_date: date,
                    filename_filter: filter,
                    download_concurrency: concurrency,
                    max_downloads_per_run: maxDl,
                    fuzzy_threshold_duplicate: threshDup,
                    fuzzy_threshold_review: threshRev
                })
            });
        }

        function startDynamicScan() {
            gallery.innerHTML = "";
            statusDiv.innerText = "Connexion au WebSocket...";
            
            const wsUrl = `ws://${window.location.host}/api/scan_stream`;
            const ws = new WebSocket(wsUrl);
            
            ws.onmessage = function(event) {
                const msg = JSON.parse(event.data);
                
                if (msg.type === "info") {
                    statusDiv.innerText = msg.message;
                } else if (msg.type === "done") {
                    statusDiv.innerText = "✅ " + msg.message;
                    ws.close();
                } else if (msg.type === "error") {
                    statusDiv.innerText = "❌ ERREUR: " + msg.message;
                } else if (msg.type === "comic") {
                    renderComic(msg);
                }
            };

            ws.onerror = function(e) {
                statusDiv.innerText = "❌ Erreur de connexion WebSocket.";
            };
        }

        function renderComic(comic) {
            const card = document.createElement('div');
            card.className = 'card';
            card.id = `card-${comic.message_id}`;
            
            let imgHtml = comic.thumb_url 
                ? `<img src="${comic.thumb_url}" alt="Cover">` 
                : `<div style="height:100px; display:flex; align-items:center; justify-content:center; background:#0f172a; color:#475569;">Pas de couverture</div>`;
                
            let selectOptions = comic.everything_results.map((r, i) => 
                `<option value="${r.path}">${i === 0 ? '▶ ' : ''}[${r.score}] ${r.filename}</option>`
            ).join('');
            
            let evHtml = comic.everything_results.length > 0 
                ? `<select class="select-match" id="select-${comic.message_id}"><option value="">-- Score de similarité : ${comic.score} --</option>${selectOptions}</select>`
                : `<select class="select-match" id="select-${comic.message_id}" style="display:none;"><option value="">-- Score de similarité : 0 --</option></select><div class="help-text" id="no-res-${comic.message_id}">Aucun résultat automatique.</div>`;

            const cleanName = comic.filename.replace(/_/g, ' ').replace(/\.[^/.]+$/, "");
            const safeOriginal = comic.filename.replace(/'/g, "\\'");

            card.innerHTML = `
                ${imgHtml}
                <div class="card-title ${'status-' + comic.status}">${comic.filename}</div>
                <div class="card-meta">${comic.channel_name} | ${comic.date} | ${(comic.file_size/1024/1024).toFixed(1)} Mo</div>
                ${evHtml}
                <div style="display:flex; justify-content: space-between; margin-top:5px; gap:5px;">
                    <button class="btn" style="flex-grow:1; background:#475569; padding: 6px; font-size: 12px;" onclick="openModal(${comic.message_id}, '${safeOriginal}', '${cleanName}')">🔍 Recherche disque</button>
                    <button class="btn btn-download" id="btn-dl-${comic.message_id}" style="flex-grow:1; padding: 6px; font-size: 12px;" onclick="downloadComic(${comic.message_id}, '${comic.channel}', '${safeOriginal}')">⬇️ Télécharger</button>
                </div>
                <div class="progress-container" id="dl-container-${comic.message_id}">
                    <div class="progress-bar" id="dl-progress-${comic.message_id}"></div>
                </div>
                <div class="dl-status" id="dl-status-${comic.message_id}"></div>
            `;
            gallery.appendChild(card);
        }

        function downloadComic(msgId, channel, filename) {
            const btn = document.getElementById(`btn-dl-${msgId}`);
            if(btn) btn.style.display = 'none';
            if (dlSocket && dlSocket.readyState === WebSocket.OPEN) {
                dlSocket.send(JSON.stringify({
                    action: "download",
                    message_id: msgId,
                    channel: channel,
                    filename: filename
                }));
            } else {
                alert("Erreur: WebSocket de téléchargement non connecté.");
                if(btn) btn.style.display = 'block';
            }
        }

        function openModal(msgId, originalFilename, cleanName) {
            currentModalMsgId = msgId;
            currentModalOriginal = originalFilename;
            document.getElementById('modal-query').value = cleanName;
            document.getElementById('modal-results').innerHTML = '';
            document.getElementById('search-modal').style.display = 'flex';
        }

        function closeModal() {
            document.getElementById('search-modal').style.display = 'none';
        }

        async function executeModalSearch() {
            const query = document.getElementById('modal-query').value;
            const btn = document.getElementById('modal-search-btn');
            const resultsDiv = document.getElementById('modal-results');
            
            btn.innerText = "⏳";
            resultsDiv.innerHTML = '<div class="help-text">Recherche en cours...</div>';
            
            try {
                const res = await fetch(`/api/everything?q=${encodeURIComponent(query)}&original=${encodeURIComponent(currentModalOriginal)}`);
                const results = await res.json();
                
                resultsDiv.innerHTML = '';
                if (results.length === 0) {
                    resultsDiv.innerHTML = '<div class="help-text">Aucun résultat trouvé.</div>';
                } else {
                    results.forEach(r => {
                        const item = document.createElement('div');
                        item.className = 'modal-result-item';
                        item.innerHTML = `<strong>[${r.score}]</strong> ${r.filename}<br><span style="color:#64748b;font-size:11px;">${r.path}</span>`;
                        item.onclick = () => selectManualResult(r);
                        resultsDiv.appendChild(item);
                    });
                }
            } catch (e) {
                resultsDiv.innerHTML = '<div class="help-text" style="color:#ef4444;">Erreur de connexion à Everything.</div>';
            }
            btn.innerText = "Chercher";
        }
        
        function selectManualResult(result) {
            const select = document.getElementById(`select-${currentModalMsgId}`);
            if (select) {
                const opt = document.createElement('option');
                opt.value = result.path;
                opt.innerText = `[${result.score}] ${result.filename} (Manuel)`;
                select.insertBefore(opt, select.options[1]); // Insert after the first default option
                select.selectedIndex = 1;
                select.style.display = 'block';
                
                const noRes = document.getElementById(`no-res-${currentModalMsgId}`);
                if (noRes) noRes.style.display = 'none';
            }
            closeModal();
        }
    </script>
</body>
</html>
"""

@app.get("/")
async def get_index():
    return HTMLResponse(INDEX_HTML)

@app.get("/api/config")
async def get_config():
    config_path = os.path.join(PROJECT_DIR, "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@app.post("/api/config")
async def update_config(request: Request):
    data = await request.json()
    config_path = os.path.join(PROJECT_DIR, "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        config["start_date"] = data.get("start_date", "")
        if "filename_filter" in data:
            config["filename_filter"] = data["filename_filter"]
        if "download_concurrency" in data:
            config["download_concurrency"] = data["download_concurrency"]
        if "max_downloads_per_run" in data:
            config["max_downloads_per_run"] = data["max_downloads_per_run"]
        if "fuzzy_threshold_duplicate" in data:
            config["fuzzy_threshold_duplicate"] = data["fuzzy_threshold_duplicate"]
        if "fuzzy_threshold_review" in data:
            config["fuzzy_threshold_review"] = data["fuzzy_threshold_review"]
            
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    return {"status": "ok"}

@app.post("/api/save_selection")
async def save_selection(request: Request):
    data = await request.json()
    selection_path = os.path.join(PROJECT_DIR, "selection.json")
    with open(selection_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return {"status": "ok"}

@app.get("/api/everything")
async def manual_everything_search(q: str, original: str):
    config_path = os.path.join(PROJECT_DIR, "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {}
        
    everything_url = config.get("everything_api_url", "http://localhost:8070")
    search_paths = config.get("bd_search_paths", [])
    
    import urllib.parse
    import urllib.request
    from fuzzy_matcher import fuzzy_score
    
    # Construction de la requete manuelle
    ext_filter = "ext:cbz;cbr;pdf;epub;rar;zip"
    
    path_filter = ""
    if search_paths:
        path_filter = "( " + " | ".join(f'path:"{p}"' for p in search_paths) + " ) "
        
    final_query = f"{path_filter}{q} {ext_filter}"
    
    url = f"{everything_url}/?search={urllib.parse.quote(final_query)}&json=1&count=50"
    
    try:
        req = urllib.request.urlopen(url, timeout=5)
        data = json.loads(req.read())
        results = data.get('results', [])
        
        scored = []
        for r in results:
            name = r.get('name', '')
            path = r.get('path', '')
            score = fuzzy_score(original, name)
            scored.append({
                'filename': name,
                'path': path,
                'score': score
            })
            
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:20]
    except Exception as e:
        return []

@app.get("/gallery")
async def serve_gallery():
    gallery_path = os.path.join(PROJECT_DIR, "gallery.html")
    if not os.path.exists(gallery_path):
        return HTMLResponse("<h1>Galerie non générée</h1><p>Cliquez d'abord sur 'Générer la Galerie' dans le panneau principal.</p><a href='/'>Retour</a>", status_code=404)
    
    with open(gallery_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    # Injection du script pour intercepter le bouton Enregistrer
    injection = """
<script>
// Override pour Web UI : on POST les données et on redirige pour lancer le téléchargement
exportSelection = function() {
  const markRead = document.getElementById('mark-read').checked;
  const files = DATA.filter(d=>selected.has(d.message_id))
    .map(d=>({channel:d.channel,message_id:d.message_id,filename:d.filename}));
  const payload = { mark_read:markRead, scan_boundary:SCAN_BOUNDARY, files:files };
  fetch('/api/save_selection', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  }).then(r => {
    window.location.href = '/?action=download';
  });
}
</script>
</body>
"""
    html = html.replace("</body>", injection)
    return HTMLResponse(html)

@app.websocket("/api/scan_stream")
async def scan_stream(websocket: WebSocket):
    await websocket.accept()
    if not telegram_client:
        await websocket.send_json({"type": "error", "message": "Telegram client non connecté (vérifiez api_id/hash dans config.json)."})
        await websocket.close()
        return

    # Load config
    config_path = os.path.join(PROJECT_DIR, "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    channels = config.get("channels", [])
    everything_url = config.get("everything_api_url", "http://localhost:8070")
    threshold_dup = config.get("fuzzy_threshold_duplicate", 85)
    threshold_rev = config.get("fuzzy_threshold_review", 50)
    filename_filter = config.get("filename_filter", [])
    search_paths = config.get("bd_search_paths", [])
    
    # Limite du nombre de cartes a afficher
    max_cards = config.get("max_gallery_size", config.get("max_downloads_per_run", 50))
    if max_cards == 0:
        max_cards = 9999
        
    start_date_str = config.get("start_date", "")
    start_date_dt = None
    if start_date_str:
        from datetime import datetime, timezone
        try:
            start_date_dt = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            pass

    from telegram_scraper import SUPPORTED_EXTENSIONS, _extract_filename_and_ext
    from everything_checker import search_by_keywords
    from fuzzy_matcher import rank_matches

    try:
        dialogs = await telegram_client.get_dialogs()
        dialog_by_id = {d.entity.id: d for d in dialogs}
        
        total_found = 0
        
        for channel in channels:
            if total_found >= max_cards:
                break
                
            entity = await telegram_client.get_entity(channel)
            channel_name = getattr(entity, "title", str(channel))
            entity_id = entity.id
            
            dialog = dialog_by_id.get(entity_id)
            read_max_id = dialog.dialog.read_inbox_max_id if dialog else 0
            
            await websocket.send_json({"type": "info", "message": f"Scan du channel : {channel_name}..."})
            
            kwargs = {'reverse': True}
            if start_date_dt:
                kwargs['offset_date'] = start_date_dt
            else:
                kwargs['min_id'] = read_max_id
                
            last_photo = None
            
            async for message in telegram_client.iter_messages(entity, **kwargs):
                if total_found >= max_cards:
                    await websocket.send_json({"type": "info", "message": f"Limite globale de {max_cards} BD atteinte."})
                    break
                    
                if message.photo:
                    last_photo = message
                    continue
                    
                if message.document:
                    filename, ext = _extract_filename_and_ext(message)
                    
                    cover = None
                    if last_photo is not None:
                        same_group = (message.grouped_id and message.grouped_id == last_photo.grouped_id)
                        if same_group or (0 <= message.id - last_photo.id <= 5):
                            cover = last_photo
                    last_photo = None
                    
                    if ext not in SUPPORTED_EXTENSIONS:
                        continue
                    if filename_filter:
                        if not any(t.lower() in filename.lower() for t in filename_filter):
                            continue
                            
                    # Everything search
                    ev_results = search_by_keywords(filename, search_paths, api_url=everything_url)
                    ranked = rank_matches(filename, ev_results)
                    
                    best_match = ranked[0] if ranked else None
                    score = best_match['score'] if best_match else 0
                    
                    status = "NOUVEAU"
                    if score >= threshold_dup:
                        status = "DOUBLON"
                    elif score >= threshold_rev:
                        status = "INCERTAIN"
                        
                    # Download cover
                    thumb_url = None
                    if cover:
                        thumb_dir = os.path.join(PROJECT_DIR, "thumbs")
                        os.makedirs(thumb_dir, exist_ok=True)
                        thumb_path = os.path.join(thumb_dir, f"{message.id}.jpg")
                        if not os.path.exists(thumb_path):
                            await telegram_client.download_media(cover.photo, file=thumb_path)
                        thumb_url = f"/thumbs/{message.id}.jpg"
                        
                    data = {
                        "type": "comic",
                        "channel": channel,
                        "channel_name": channel_name,
                        "message_id": message.id,
                        "filename": filename,
                        "file_size": message.document.size,
                        "date": message.date.strftime("%Y-%m-%d %H:%M"),
                        "thumb_url": thumb_url,
                        "status": status,
                        "score": score,
                        "everything_results": ranked[:5]
                    }
                    await websocket.send_json(data)
                    total_found += 1
                    
        await websocket.send_json({"type": "done", "message": "Scan terminé !"})
        await websocket.close()
        
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
        await websocket.close()

download_semaphore = None

@app.websocket("/api/downloads_ws")
async def downloads_ws(websocket: WebSocket):
    await websocket.accept()
    
    global download_semaphore
    if download_semaphore is None:
        config_path = os.path.join(PROJECT_DIR, "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                c = json.load(f)
            conc = int(c.get("download_concurrency", 5))
        else:
            conc = 5
        download_semaphore = asyncio.Semaphore(conc)
        
    async def download_task(data):
        msg_id = data["message_id"]
        channel = int(data["channel"])
        filename = data["filename"]
        
        await websocket.send_json({"type": "status", "message_id": msg_id, "status": "En attente..."})
        
        async with download_semaphore:
            await websocket.send_json({"type": "status", "message_id": msg_id, "status": "Préparation..."})
            try:
                entity = await telegram_client.get_entity(channel)
                message = await telegram_client.get_messages(entity, ids=msg_id)
                
                dl_dir = config.get("download_folder") if 'config' in locals() and config.get("download_folder") else os.path.join(PROJECT_DIR, "downloads")
                os.makedirs(dl_dir, exist_ok=True)
                file_path = os.path.join(dl_dir, filename)
                
                def progress_cb(current, total):
                    # Call async from sync context is tricky inside Telethon, so we just create a task
                    asyncio.create_task(websocket.send_json({
                        "type": "progress",
                        "message_id": msg_id,
                        "current": current,
                        "total": total
                    }))
                
                await telegram_client.download_media(
                    message.document, 
                    file=file_path,
                    progress_callback=progress_cb
                )
                await websocket.send_json({"type": "status", "message_id": msg_id, "status": "Terminé ✅"})
            except Exception as e:
                await websocket.send_json({"type": "status", "message_id": msg_id, "status": f"Erreur ❌"})

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("action") == "download":
                asyncio.create_task(download_task(data))
    except Exception:
        pass

# Sert le dossier thumbs pour la galerie
app.mount("/thumbs", StaticFiles(directory=os.path.join(PROJECT_DIR, "thumbs")), name="thumbs")

if __name__ == "__main__":
    import uvicorn
    import sys
    import asyncio
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    uvicorn.run("web_ui:app", host="127.0.0.1", port=8000, reload=True)
