import re
import os

with open('web_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update INDEX_HTML UI
html_repl = r"""
<!-- Pagination button -->
<button class="btn btn-primary" id="btn-scan" onclick="startDynamicScan()">🚀 Scanner</button>
<button class="btn" id="btn-scan-next" style="display:none; background:#8b5cf6; color:white; border:none;" onclick="startDynamicScan(true)">⏪ Continuer plus ancien</button>
"""
content = content.replace('<button class="btn btn-primary" id="btn-scan" onclick="startDynamicScan()">🚀 Scanner</button>', html_repl)

# Downloads Modal HTML
downloads_modal = r"""
<!-- Modal Downloads -->
<div class="modal-overlay" id="downloads-modal" onclick="closeModal('downloads-modal')">
    <div class="modal-content" onclick="event.stopPropagation()">
        <div class="modal-hdr">
            <h2>⏳ Téléchargements en cours</h2>
            <div>
                <button class="btn" style="background:#ef4444; color:white; border:none;" onclick="cancelAllDownloads()">Tout Annuler</button>
                <button class="modal-close" onclick="closeModal('downloads-modal')">&times;</button>
            </div>
        </div>
        <div id="downloads-list" style="max-height: 400px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px;">
            <div class="help-text">Aucun téléchargement en cours.</div>
        </div>
    </div>
</div>
<div id="tooltip"></div>
"""
content = content.replace('<div id="tooltip"></div>', downloads_modal)

# JS Updates
js_repl = r"""
    let activeDownloadsCount = 0;
    let downloadsState = {};
    let lastScanDate = null;
    
    // Add onclick to indicator
    document.getElementById('global-dl-indicator').onclick = function() {
        renderDownloadsModal();
        document.getElementById('downloads-modal').style.display='flex';
    };
    
    function renderDownloadsModal() {
        const list = document.getElementById('downloads-list');
        list.innerHTML = '';
        const keys = Object.keys(downloadsState);
        if(keys.length === 0) {
            list.innerHTML = '<div class="help-text">Aucun téléchargement.</div>';
            return;
        }
        keys.forEach(id => {
            const d = downloadsState[id];
            const div = document.createElement('div');
            div.style.cssText = 'background:#0f172a; padding:10px; border-radius:6px; border:1px solid #334155; font-size:12px; display:flex; justify-content:space-between; align-items:center;';
            
            const info = document.createElement('div');
            info.style.flexGrow = '1';
            let progText = '';
            let progWidth = '0%';
            if(d.total) {
                progText = `${(d.current/1024/1024).toFixed(1)} / ${(d.total/1024/1024).toFixed(1)} Mo`;
                progWidth = `${(d.current/d.total)*100}%`;
            }
            
            info.innerHTML = `
                <div style="font-weight:bold; margin-bottom:4px; color:#e2e8f0;">${d.filename}</div>
                <div style="color:#94a3b8; font-size:11px;">Statut : <span style="color:#38bdf8">${d.status}</span> ${progText}</div>
                <div style="width:100%; background:#1e293b; height:4px; border-radius:2px; margin-top:4px;">
                    <div style="width:${progWidth}; background:#38bdf8; height:100%; border-radius:2px; transition:width 0.2s;"></div>
                </div>
            `;
            
            const btn = document.createElement('button');
            btn.className = 'btn';
            btn.style.cssText = 'background:#ef4444; color:white; border:none; margin-left:15px; padding:4px 8px; cursor:pointer;';
            btn.innerText = '✕';
            btn.onclick = () => cancelDownload(id);
            
            if(d.status === 'Terminé ✅' || d.status.startsWith('Erreur') || d.status.startsWith('Annulé')) {
                btn.style.display = 'none';
            }
            
            div.appendChild(info);
            div.appendChild(btn);
            list.appendChild(div);
        });
    }

    function cancelDownload(id) {
        if(dlSocket && dlSocket.readyState === WebSocket.OPEN) {
            dlSocket.send(JSON.stringify({action: "cancel", message_id: parseInt(id)}));
        }
    }
    
    function cancelAllDownloads() {
        Object.keys(downloadsState).forEach(id => {
            if(!downloadsState[id].status.includes('✅') && !downloadsState[id].status.includes('❌')) {
                cancelDownload(id);
            }
        });
    }

    // Connecter WebSocket Download (Update)
    function initDownloadSocket() {
        dlSocket = new WebSocket(`ws://${window.location.host}/api/downloads_ws`);
        dlSocket.onmessage = function(event) {
            const msg = JSON.parse(event.data);
            if(!downloadsState[msg.message_id]) downloadsState[msg.message_id] = {filename: msg.filename || 'Fichier inconnu', status: 'En file d\\'attente', current:0, total:0};
            
            if (msg.type === "status") {
                downloadsState[msg.message_id].status = msg.status;
                if (msg.filename) downloadsState[msg.message_id].filename = msg.filename;
                
                if (msg.status === "Terminé ✅" || msg.status.startsWith("Erreur") || msg.status.startsWith("Annulé")) {
                    activeDownloadsCount--;
                    if(activeDownloadsCount < 0) activeDownloadsCount = 0;
                    updateGlobalDownloadIndicator();
                    // Clean up state after 10 seconds if done to prevent memory leak
                    setTimeout(() => { delete downloadsState[msg.message_id]; if(document.getElementById('downloads-modal').style.display === 'flex') renderDownloadsModal(); }, 10000);
                }
                const statusEl = document.getElementById(`dl-status-${msg.message_id}`);
                if (statusEl) {
                    statusEl.innerText = msg.status;
                    statusEl.style.display = 'block';
                }
                if(document.getElementById('downloads-modal').style.display === 'flex') renderDownloadsModal();
                
            } else if (msg.type === "progress") {
                downloadsState[msg.message_id].current = msg.current;
                downloadsState[msg.message_id].total = msg.total;
                
                const bar = document.getElementById(`dl-progress-${msg.message_id}`);
                const container = document.getElementById(`dl-container-${msg.message_id}`);
                const statusEl = document.getElementById(`dl-status-${msg.message_id}`);
                if (bar && container) {
                    container.style.display = 'block';
                    const percent = (msg.current / msg.total) * 100;
                    bar.style.width = percent + '%';
                    if (statusEl) {
                        statusEl.innerText = `${(msg.current/1024/1024).toFixed(1)} / ${(msg.total/1024/1024).toFixed(1)} Mo`;
                        statusEl.style.display = 'block';
                    }
                }
                if(document.getElementById('downloads-modal').style.display === 'flex') renderDownloadsModal();
            }
        };
        dlSocket.onclose = () => setTimeout(initDownloadSocket, 2000);
    }
"""
content = re.sub(r'    let activeDownloads = 0;[\s\S]*?dlSocket\.onclose = \(\) => setTimeout\(initDownloadSocket, 2000\);\n    \}', js_repl, content)

js_repl2 = r"""
    function updateGlobalDownloadIndicator() {
        let ind = document.getElementById('global-dl-indicator');
        if(activeDownloadsCount > 0) {
            ind.style.display = 'block';
            ind.innerHTML = `<b>⏳ ${activeDownloadsCount} téléchargement(s)</b> (cliquer pour détails)`;
            ind.style.cursor = 'pointer';
        } else {
            ind.style.display = 'none';
        }
    }
    
    function downloadSelection(isToRead) {
        if (!dlSocket || dlSocket.readyState !== WebSocket.OPEN) {
            alert("Erreur: WebSocket de téléchargement non connecté.");
            return;
        }
        const toDownload = DATA.filter(d => selected.has(d.message_id));
        if (toDownload.length === 0) return;
        
        activeDownloadsCount += toDownload.length;
        updateGlobalDownloadIndicator();
        
        toDownload.forEach(d => {
            downloadsState[d.message_id] = {filename: d.filename, status: 'En file d\'attente...', current:0, total:0};
            dlSocket.send(JSON.stringify({
                action: "download",
                message_id: d.message_id,
                channel: d.channel,
                filename: d.filename,
                to_read: isToRead === true
            }));
        });
        deselectAll();
    }
    
    function markAsToRead() {
        const toSave = DATA.filter(d => selected.has(d.message_id)).map(d => ({
            title: d.filename,
            channel: d.channel_name,
            date_added: new Date().toISOString()
        }));
        if(toSave.length === 0) return;
        
        fetch('/api/add_to_read', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(toSave)
        }).then(() => {
            alert(toSave.length + " BD ajoutées à la liste 'À Lire' !");
            deselectAll();
        });
    }

    function startDynamicScan(continueFromLast = false) {
        if(!continueFromLast) {
            grid.innerHTML = "";
            DATA.length = 0;
            selected.clear();
            document.getElementById('btn-scan-next').style.display = 'none';
        }
        updateCounter();
        
        btnScan.disabled = true;
        statusDiv.innerText = "Connexion...";
        
        let wsUrl = `ws://${window.location.host}/api/scan_stream`;
        if (continueFromLast && lastScanDate) {
            wsUrl += `?continue_date=${encodeURIComponent(lastScanDate)}`;
        }
        const ws = new WebSocket(wsUrl);
        
        ws.onmessage = function(event) {
            const msg = JSON.parse(event.data);
            if (msg.type === "info") {
                statusDiv.innerText = msg.message;
            } else if (msg.type === "done") {
                statusDiv.innerText = "✅ " + msg.message;
                btnScan.disabled = false;
                if (msg.last_date) {
                    lastScanDate = msg.last_date;
                    document.getElementById('btn-scan-next').style.display = 'inline-block';
                }
                ws.close();
            } else if (msg.type === "error") {
                statusDiv.innerText = "❌ ERREUR: " + msg.message;
                btnScan.disabled = false;
            } else if (msg.type === "comic") {
                DATA.push(msg);
                applyFilters();
            }
        };
"""
content = re.sub(r'    function updateGlobalDownloadIndicator\(\) \{[\s\S]*?applyFilters\(\);\n            \}\n        \};\n', js_repl2, content)

content = content.replace('downloadSelection(true)', 'markAsToRead()').replace('📚 À Lire', '🔖 Marquer À Lire')
content = content.replace('function updateCounter(vis) {\n      const v = vis!==undefined ? vis : document.querySelectorAll(\'.card\').length;', 'function updateCounter(vis) {\n      const v = vis!==undefined ? vis : document.querySelectorAll(\'.card:not([style*="display: none"])\').length;')

# BACKEND REPLACEMENTS
backend_toread = r"""
@app.post("/api/add_to_read")
async def add_to_read(request: Request):
    data = await request.json()
    toread_path = os.path.join(PROJECT_DIR, "to_read.json")
    existing = []
    if os.path.exists(toread_path):
        with open(toread_path, "r", encoding="utf-8") as f:
            try: existing = json.load(f)
            except: pass
    existing.extend(data)
    with open(toread_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4, ensure_ascii=False)
    return {"status": "ok"}

@app.get("/gallery")
"""
content = content.replace('@app.get("/gallery")', backend_toread)

content = content.replace('async def scan_stream(websocket: WebSocket):', 'async def scan_stream(websocket: WebSocket, continue_date: str = None):')

content = content.replace('if start_date_dt:', 'if continue_date:\n                import dateutil.parser\n                kwargs["offset_date"] = dateutil.parser.parse(continue_date)\n            elif start_date_dt:')

content = content.replace('await websocket.send_json({"type": "done", "message": f"Terminé ! {total_found} BD trouvées parmi {total_scanned} messages scannés."})', 
'await websocket.send_json({"type": "done", "message": f"Terminé ! {total_found} BD trouvées parmi {total_scanned} messages scannés.", "last_date": last_photo.date.isoformat() if last_photo else None})')

dl_ws_replacement = r"""
active_download_tasks = {}

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
        
        await websocket.send_json({"type": "status", "message_id": msg_id, "filename": filename, "status": "En file d'attente..."})
        
        try:
            async with download_semaphore:
                await websocket.send_json({"type": "status", "message_id": msg_id, "filename": filename, "status": "Préparation..."})
                
                entity = await telegram_client.get_entity(channel)
                message = await telegram_client.get_messages(entity, ids=msg_id)
                
                dl_dir = config.get("download_folder") if 'config' in locals() and config.get("download_folder") else os.path.join(PROJECT_DIR, "downloads")
                os.makedirs(dl_dir, exist_ok=True)
                file_path = os.path.join(dl_dir, filename)
                
                def progress_cb(current, total):
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
                await websocket.send_json({"type": "status", "message_id": msg_id, "filename": filename, "status": "Terminé ✅"})
        except asyncio.CancelledError:
            await websocket.send_json({"type": "status", "message_id": msg_id, "filename": filename, "status": "Annulé ❌"})
        except Exception as e:
            await websocket.send_json({"type": "status", "message_id": msg_id, "filename": filename, "status": f"Erreur ❌"})
        finally:
            active_download_tasks.pop(msg_id, None)

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("action") == "download":
                task = asyncio.create_task(download_task(data))
                active_download_tasks[data["message_id"]] = task
            elif data.get("action") == "cancel":
                msg_id = data.get("message_id")
                if msg_id in active_download_tasks:
                    active_download_tasks[msg_id].cancel()
    except:
        pass
"""
# Replace from active_download_tasks definition or @app.websocket if it doesn't exist
content = re.sub(r'download_semaphore = None\n\n@app\.websocket\("/api/downloads_ws"\)[\s\S]*?elif data\.get\("action"\) == "download":\n                asyncio\.create_task\(download_task\(data\)\)', 'download_semaphore = None\n' + dl_ws_replacement, content)

with open('web_ui.py', 'w', encoding='utf-8') as f:
    f.write(content)
