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

app = FastAPI(title="BD Telegram Web UI")

# Dossier du projet (racine)
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Variables globales pour le process en cours
current_process = None

# Template de la page d'accueil avec un terminal virtuel
INDEX_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BD Telegram - Web UI</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; }
        h1 { text-align: center; color: #38bdf8; }
        .header-panel { background: #1e293b; padding: 20px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .btn { background: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; transition: background 0.2s; }
        .btn:hover { background: #2563eb; }
        .btn-gallery { background: #10b981; }
        .btn-gallery:hover { background: #059669; }
        .btn-download { background: #8b5cf6; }
        .btn-download:hover { background: #7c3aed; }
        .terminal { background: #000; color: #0f0; padding: 15px; border-radius: 8px; font-family: 'Courier New', Courier, monospace; height: 60vh; overflow-y: auto; white-space: pre-wrap; font-size: 14px; box-shadow: inset 0 0 10px rgba(0,0,0,0.8); }
        .settings { margin-bottom: 15px; display: grid; grid-template-columns: auto 1fr; gap: 10px; align-items: center; background: #334155; padding: 15px; border-radius: 6px;}
        input[type="date"], input[type="text"], input[type="number"] { padding: 8px; border-radius: 4px; border: 1px solid #475569; background: #1e293b; color: white; width: 100%; box-sizing: border-box;}
        .form-label { font-weight: bold; color: #94a3b8; }
        .help-text { font-size: 11px; color: #64748b; margin-top: 2px;}
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 BD Telegram - Contrôle Web</h1>
        
        <div class="header-panel">
            <div>
                <div class="settings">
                    <div class="form-label">Date de départ :</div>
                    <div>
                        <input type="date" id="start_date" onchange="updateConfig()">
                        <div class="help-text">Laissez vide pour utiliser le curseur du dernier scan lu.</div>
                    </div>
                    
                    <div class="form-label">Mots-clés (Filtre) :</div>
                    <div>
                        <input type="text" id="filename_filter" onchange="updateConfig()" placeholder="ex: 2025, 2026, Casterman">
                        <div class="help-text">Mots-clés séparés par des virgules. Laissez vide pour tout scanner.</div>
                    </div>

                    <div class="form-label">Téléchargements // :</div>
                    <div>
                        <input type="number" id="download_concurrency" onchange="updateConfig()" min="1" max="20">
                        <div class="help-text">Nombre de fichiers téléchargés en simultané.</div>
                    </div>
                </div>
                <div style="display:flex; gap:10px;">
                    <button class="btn" onclick="runCommand('gallery')">🔍 1. Générer la Galerie</button>
                    <button class="btn btn-gallery" onclick="window.location.href='/gallery'">🖼️ 2. Voir la Galerie</button>
                    <button class="btn btn-download" onclick="runCommand('download')">⬇️ 3. Lancer Téléchargements</button>
                </div>
            </div>
        </div>

        <div class="terminal" id="terminal">Prêt.
</div>
    </div>

    <script>
        const term = document.getElementById('terminal');

        // Charger la config initiale
        fetch('/api/config').then(r=>r.json()).then(c => {
            if(c.start_date) document.getElementById('start_date').value = c.start_date;
            if(c.filename_filter) document.getElementById('filename_filter').value = c.filename_filter.join(', ');
            if(c.download_concurrency) document.getElementById('download_concurrency').value = c.download_concurrency;
        });

        function updateConfig() {
            const date = document.getElementById('start_date').value;
            const filterStr = document.getElementById('filename_filter').value;
            const filter = filterStr ? filterStr.split(',').map(s => s.trim()).filter(s => s) : [];
            const concurrency = parseInt(document.getElementById('download_concurrency').value) || 5;
            
            fetch('/api/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    start_date: date,
                    filename_filter: filter,
                    download_concurrency: concurrency
                })
            });
        }

        function runCommand(action) {
            term.innerHTML = "Lancement en cours...\\n";
            const wsUrl = `ws://${window.location.host}/api/run/${action}`;
            const ws = new WebSocket(wsUrl);
            
            ws.onmessage = function(event) {
                if (event.data === "[DONE]") {
                    term.innerHTML += "\\n\\n--- TERMINÉ ---";
                    term.scrollTop = term.scrollHeight;
                    ws.close();
                } else {
                    let text = event.data;
                    text = text.replace(/___NEWLINE___/g, "\\n");
                    const parts = text.split('___CR___');
                    
                    for (let i = 0; i < parts.length; i++) {
                        if (i > 0) {
                            const lines = term.innerHTML.split('\\n');
                            lines.pop();
                            term.innerHTML = lines.join('\\n');
                        }
                        const safeText = parts[i].replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                        term.innerHTML += safeText;
                    }
                    term.scrollTop = term.scrollHeight;
                }
            };

            ws.onerror = function(e) {
                console.error("WebSocket error:", e);
                term.innerHTML += "\\n\\n--- ERREUR DE CONNEXION WEBSOCKET ---";
            };
            
            ws.onclose = function(e) {
                if(!term.innerHTML.includes("TERMINÉ")) {
                    term.innerHTML += "\\n\\n--- CONNEXION FERMÉE ---";
                }
            };
        }

        // Si on revient de la galerie avec l'action download
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('action') === 'download') {
            runCommand('download');
            // Nettoyer l'URL
            window.history.replaceState({}, document.title, "/");
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

@app.websocket("/api/run/{action}")
async def run_action_ws(websocket: WebSocket, action: str):
    await websocket.accept()
    
    python_exe = os.path.join(PROJECT_DIR, "venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = "python"
    
    args = [python_exe, "main.py"]
    if action == "gallery":
        args.append("--gallery")
    elif action == "download":
        args.append("--download-selection")
    else:
        await websocket.send_text("Action non reconnue")
        await websocket.close()
        return
        
    try:
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=PROJECT_DIR,
            env={**os.environ, "PYTHONUNBUFFERED": "1", "WEB_UI_MODE": "1"}
        )
        
        q = queue.Queue()
        def read_output(proc, out_q):
            while True:
                data = proc.stdout.read(128)
                if not data:
                    break
                out_q.put(data)
            out_q.put(None)
            
        t = threading.Thread(target=read_output, args=(process, q), daemon=True)
        t.start()
        
        while True:
            try:
                chunk = q.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue
                
            if chunk is None:
                break
                
            text = chunk.decode('utf-8', errors='replace').replace('\\n', '___NEWLINE___').replace('\\r', '___CR___')
            await websocket.send_text(text)
            
        process.wait()
        await websocket.send_text("[DONE]")
    except Exception as e:
        await websocket.send_text(f"ERREUR CRITIQUE: {repr(e)}")
        await websocket.send_text("[DONE]")
    finally:
        try:
            await websocket.close()
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
