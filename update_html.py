import re

html_content = r'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BD Telegram — Mode SPA</title>
<style>
* {box-sizing:border-box;margin:0;padding:0}
:root {--card-w:180px}
body {font-family:'Segoe UI',system-ui,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
header {position:sticky;top:0;z-index:50;background:#0f172aee;backdrop-filter:blur(8px);
  border-bottom:1px solid #1e293b;padding:10px 16px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}
h1 {font-size:1.15rem;color:#60a5fa;flex:0 0 auto;white-space:nowrap; margin-right:10px;}
.pills {display:flex;gap:6px;flex-wrap:wrap}
.filters {display:flex;gap:5px; margin-left: 10px;}
.fb {background:#1e293b;border:1px solid #334155;color:#94a3b8;padding:4px 11px;
  border-radius:20px;cursor:pointer;font-size:0.75rem;transition:all .2s}
.fb.active {background:#3b82f6;border-color:#3b82f6;color:#fff}
.search-wrap {flex:1;min-width:140px;max-width:240px}
#search {width:100%;background:#1e293b;border:1px solid #334155;color:#e2e8f0;
  padding:5px 12px;border-radius:20px;font-size:0.8rem;outline:none}
#search:focus {border-color:#3b82f6}
.zoom-wrap {display:flex;align-items:center;gap:5px;font-size:0.72rem;color:#64748b;white-space:nowrap}
#zoom {width:70px;accent-color:#3b82f6}
.actions {display:flex;gap:7px;align-items:center;flex-wrap:wrap; margin-left:auto;}
#counter {font-size:0.72rem;color:#64748b;white-space:nowrap}
.btn {background:#1e293b;border:1px solid #334155;color:#94a3b8;padding:4px 10px;
  border-radius:6px;cursor:pointer;font-size:0.75rem;transition:all .2s;white-space:nowrap}
.btn:hover {border-color:#3b82f6;color:#60a5fa;}
.btn-primary { background:#3b82f6; color:white; border-color:#2563eb; font-weight:bold; }
.btn-primary:hover { background:#2563eb; color:white; }
.btn-download {background:#8b5cf6;border:none;color:#fff;padding:5px 14px;
  border-radius:8px;cursor:pointer;font-weight:700;font-size:0.82rem;transition:background .2s;white-space:nowrap}
.btn-download:hover {background:#7c3aed}
.btn-download:disabled {background:#374151;color:#6b7280;cursor:not-allowed}

/* Grid & Cards */
.grid {display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--card-w),1fr));gap:12px;padding:16px}
.card {position:relative;border-radius:10px;overflow:hidden;background:#1e293b;
  cursor:pointer;transition:transform .2s,box-shadow .2s,border-color .2s;border:2px solid transparent}
.card:hover {transform:scale(1.04);box-shadow:0 8px 24px #00000070;z-index:2}
.card.selected {border-color:#22c55e;box-shadow:0 0 0 3px #22c55e30}
.cover {width:100%;aspect-ratio:3/4;object-fit:cover;display:block;background:#0f172a;}
.card-info {padding:7px 9px 9px; display:flex; flex-direction:column; gap:4px;}
.card-title {font-size:0.75rem;font-weight:600;line-height:1.3;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
  overflow:hidden;margin-bottom:2px}
.card-meta {font-size:0.65rem;color:#64748b;line-height:1.4}
.badge {display:inline-block;padding:2px 7px;border-radius:10px;font-size:0.65rem;font-weight:700; align-self:flex-start;}
.badge.NOUVEAU {background:#052e16;color:#22c55e;border:1px solid #22c55e40}
.badge.INCERTAIN {background:#1c1407;color:#f59e0b;border:1px solid #f59e0b40}
.badge.DOUBLON {background:#2e0505;color:#ef4444;border:1px solid #ef444440}
.match-hint {font-size:0.6rem;color:#94a3b8;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.checkmark {position:absolute;top:7px;right:7px;width:22px;height:22px;border-radius:50%;
  background:#22c55e;color:#fff;display:none;align-items:center;justify-content:center;
  font-size:13px;font-weight:700;box-shadow:0 2px 6px #00000060}
.card.selected .checkmark {display:flex}
.bdt-link {position:absolute;top:7px;left:7px;width:22px;height:22px;border-radius:50%;
  background:#1e293bcc;color:#60a5fa;display:flex;align-items:center;justify-content:center;
  font-size:12px;text-decoration:none;opacity:0;transition:opacity .2s;border:1px solid #3b82f660}
.card:hover .bdt-link {opacity:1}

/* Progress bar inside card */
.progress-container { width:100%; background-color:#0f172a; border-radius:4px; overflow:hidden; height:6px; display:none; margin-top:4px;}
.progress-bar { width:0%; height:100%; background-color:#38bdf8; transition:width 0.2s; }
.dl-status { font-size:10px; color:#cbd5e1; text-align:right; display:none; margin-top:2px;}

/* Tooltip */
#tooltip {position:fixed;background:#1e293b;color:#e2e8f0;padding:7px 12px;border-radius:7px;
  font-size:0.78rem;pointer-events:none;display:none;z-index:200;max-width:440px;
  word-break:break-all;border:1px solid #334155;box-shadow:0 4px 16px #00000060;line-height:1.5}

/* Modals */
.modal-overlay {position:fixed;inset:0;background:#000000b0;z-index:100;
  display:none;align-items:center;justify-content:center;padding:16px}
.modal-content {background:#1e293b;border-radius:12px;width:100%;max-width:700px;
  max-height:85vh;display:flex;flex-direction:column;border:1px solid #334155; padding:20px;}
.modal-hdr {display:flex;align-items:center;justify-content:space-between;
  margin-bottom:15px; border-bottom:1px solid #334155; padding-bottom:10px;}
.modal-hdr h2 {font-size:1.1rem; color:#38bdf8;}
.modal-close {background:none;border:none;color:#94a3b8;font-size:1.5rem;cursor:pointer}
.modal-close:hover {color:white;}
.settings-grid {display:grid; grid-template-columns:auto 1fr auto 1fr; gap:15px; align-items:center;}
input[type="date"], input[type="text"], input[type="number"] {padding:6px 10px;border-radius:4px;border:1px solid #475569;background:#0f172a;color:white;width:100%;}
.form-label {font-size:0.85rem;font-weight:600;color:#cbd5e1;text-align:right;}
.help-text {font-size:0.65rem;color:#64748b;margin-top:2px;}

#modal-results { margin-top: 15px; max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
.modal-result-item { background: #0f172a; padding: 10px; border-radius: 4px; cursor: pointer; border: 1px solid #334155; font-size: 13px; }
.modal-result-item:hover { background: #334155; border-color: #38bdf8; }

#no-results {display:none;text-align:center;padding:60px;color:#4b5563;font-size:1rem}
</style>
</head>
<body>

<header>
  <h1>📚 BD Telegram</h1>
  <div class="pills">
     <button class="btn btn-primary" id="btn-scan" onclick="startDynamicScan()">🚀 Scanner</button>
     <button class="btn" onclick="document.getElementById('settings-modal').style.display='flex'">⚙️ Config</button>
     <span id="scan-status" style="margin-left: 10px; align-self: center; font-size: 0.8rem; color: #38bdf8;">Prêt.</span>
  </div>
  <div class="filters">
    <button class="fb active" onclick="setFilter('ALL',this)">Tous</button>
    <button class="fb" onclick="setFilter('NOUVEAU',this)">Nouveaux</button>
    <button class="fb" onclick="setFilter('INCERTAIN',this)">Incertains</button>
    <button class="fb" onclick="setFilter('DOUBLON',this)">Doublons</button>
  </div>
  <div class="search-wrap">
    <input id="search" type="text" placeholder="🔍 Filtrer résultats..." oninput="applyFilters()">
  </div>
  <div class="zoom-wrap">🔍 <input type="range" id="zoom" min="130" max="320" value="180" oninput="setZoom(this.value)"></div>
  <div class="actions">
    <button class="btn" onclick="selectAllVisible()">Tout cocher</button>
    <button class="btn" onclick="deselectAll()">Décocher</button>
    <span id="counter">0 visible / 0 sélec.</span>
    <button id="export-btn" class="btn-download" disabled onclick="downloadSelection()">⬇️ Télécharger (0)</button>
  </div>
</header>

<div id="grid" class="grid"></div>
<div id="no-results">Aucun album pour ce filtre ou la galerie est vide.</div>

<!-- Modal Config -->
<div class="modal-overlay" id="settings-modal" onclick="closeModal('settings-modal')">
  <div class="modal-content" onclick="event.stopPropagation()">
    <div class="modal-hdr">
      <h2>⚙️ Paramètres de Scan</h2>
      <button class="modal-close" onclick="closeModal('settings-modal')">&times;</button>
    </div>
    <div class="settings-grid">
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
  </div>
</div>

<!-- Modal Recherche -->
<div class="modal-overlay" id="search-modal" onclick="closeModal('search-modal')">
    <div class="modal-content" onclick="event.stopPropagation()">
        <div class="modal-hdr">
            <h2>🔍 Recherche sur le disque</h2>
            <button class="modal-close" onclick="closeModal('search-modal')">&times;</button>
        </div>
        <div style="display:flex; gap:10px;">
            <input type="text" id="modal-query" style="flex-grow:1; font-size:14px;" placeholder="Titre de la BD...">
            <button class="btn btn-primary" id="modal-search-btn" onclick="executeModalSearch()">Chercher</button>
        </div>
        <div id="modal-results">
            <div class="help-text">Entrez un titre pour chercher.</div>
        </div>
    </div>
</div>

<div id="tooltip"></div>

<script>
    const DATA = [];
    const grid = document.getElementById('grid');
    const statusDiv = document.getElementById('scan-status');
    const btnScan = document.getElementById('btn-scan');
    let dlSocket = null;
    let currentFilter = 'ALL';
    let selected = new Set();
    
    let currentModalMsgId = null;
    let currentModalOriginal = null;

    // Connecter WebSocket Download
    function initDownloadSocket() {
        dlSocket = new WebSocket(`ws://${window.location.host}/api/downloads_ws`);
        dlSocket.onmessage = function(event) {
            const msg = JSON.parse(event.data);
            if (msg.type === "status") {
                const statusEl = document.getElementById(`dl-status-${msg.message_id}`);
                if (statusEl) {
                    statusEl.innerText = msg.status;
                    statusEl.style.display = 'block';
                }
            } else if (msg.type === "progress") {
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
            }
        };
        dlSocket.onclose = () => setTimeout(initDownloadSocket, 2000);
    }
    initDownloadSocket();

    // Config initialisation
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
                start_date: date, filename_filter: filter, download_concurrency: concurrency,
                max_downloads_per_run: maxDl, fuzzy_threshold_duplicate: threshDup, fuzzy_threshold_review: threshRev
            })
        });
    }

    /* Utilitaires UI */
    function setZoom(v) { document.documentElement.style.setProperty('--card-w', v+'px'); }

    const tt = document.getElementById('tooltip');
    document.addEventListener('mousemove', e => {
      if (tt.style.display==='block') {
        tt.style.left = Math.min(e.clientX+14, window.innerWidth-460)+'px';
        tt.style.top  = (e.clientY+14)+'px';
      }
    });
    function showTip(text) { tt.textContent=text; tt.style.display='block'; }
    function hideTip()     { tt.style.display='none'; }

    function extractTitle(filename) {
      let n = filename.replace(/\.(cbz|cbr|pdf)$/i,'').replace(/_/g,' ');
      n = n.replace(/\s*(T\d+|Tome\s*\d+|\bOS\b|\bHS\b|\bO\s+S\b|\bO\.?S\.?\b|\(|\s-\s|\d{4}).*$/i,'');
      return n.trim();
    }
    function bdtUrl(filename) {
      var title = extractTitle(filename);
      if (!title || title.length < 2) return null;
      if (title.trim().split(/\s+/).length > 5) return null;
      return 'https://www.google.com/search?q=site%3Abedetheque.com+' + encodeURIComponent(title) + '&btnI=1';
    }
    function closeModal(id) { document.getElementById(id).style.display='none'; }
    document.addEventListener('keydown', e=>{ if(e.key==='Escape') { closeModal('settings-modal'); closeModal('search-modal'); } });

    /* Scanner Dynamique */
    function startDynamicScan() {
        grid.innerHTML = "";
        DATA.length = 0;
        selected.clear();
        updateCounter();
        
        btnScan.disabled = true;
        statusDiv.innerText = "Connexion...";
        
        const wsUrl = `ws://${window.location.host}/api/scan_stream`;
        const ws = new WebSocket(wsUrl);
        
        ws.onmessage = function(event) {
            const msg = JSON.parse(event.data);
            if (msg.type === "info") {
                statusDiv.innerText = msg.message;
            } else if (msg.type === "done") {
                statusDiv.innerText = "✅ " + msg.message;
                btnScan.disabled = false;
                ws.close();
            } else if (msg.type === "error") {
                statusDiv.innerText = "❌ ERREUR: " + msg.message;
                btnScan.disabled = false;
            } else if (msg.type === "comic") {
                DATA.push(msg);
                applyFilters();
            }
        };

        ws.onerror = function(e) {
            statusDiv.innerText = "❌ Erreur WebSocket.";
            btnScan.disabled = false;
        };
    }

    /* Rendu et filtres */
    function applyFilters() {
      const q = document.getElementById('search').value.toLowerCase();
      const filtered = DATA.filter(d => {
        if (currentFilter!=='ALL' && d.status!==currentFilter) return false;
        if (q && !d.filename.toLowerCase().includes(q)) return false;
        return true;
      });
      renderGrid(filtered);
    }

    function setFilter(f,btn) {
      currentFilter=f;
      document.querySelectorAll('.fb').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      applyFilters();
    }

    function renderGrid(items) {
      const nr = document.getElementById('no-results');
      if (!items.length) { grid.innerHTML=''; nr.style.display='block'; updateCounter(0); return; }
      nr.style.display = 'none';
      
      grid.innerHTML = items.map(d => {
        const isSel = selected.has(d.message_id);
        const displayName = d.filename.replace(/_/g,' ').replace(/\.(cbz|cbr|pdf)$/i,'');
        const cleanName = displayName;
        const safeOriginal = d.filename.replace(/'/g, "\\'");
        const color = COLORS[d.filename.charCodeAt(0) % COLORS.length];
        
        const imgH  = d.thumb_url
          ? `<img class="cover" src="${d.thumb_url}" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"><div class="cover" style="display:none;align-items:center;justify-content:center;color:#475569;font-size:3rem;background:linear-gradient(135deg,${color}44,#0f172a)">${d.filename[0].toUpperCase()}</div>`
          : `<div class="cover" style="display:flex;align-items:center;justify-content:center;color:#475569;font-size:3rem;background:linear-gradient(135deg,${color}44,#0f172a)">${d.filename[0].toUpperCase()}</div>`;
          
        const matchH = (d.everything_results && d.everything_results.length > 0) 
            ? `<div class="match-hint" id="match-${d.message_id}">Auto: ${d.everything_results[0].score}% - ${d.everything_results[0].filename}</div>` 
            : `<div class="match-hint" id="match-${d.message_id}">Aucun match automatique</div>`;
            
        const bdtH = (u => u ? `<a class="bdt-link" href="${u}" target="_blank" onclick="event.stopPropagation()" title="BDthèque">📚</a>` : '')(bdtUrl(d.filename));
        
        return `<div class="card${isSel?' selected':''}" data-id="${d.message_id}" onclick="toggleCard(this)">
          ${imgH}
          ${bdtH}
          <div class="card-info">
            <div class="card-title" data-fn="${d.filename}" onmouseenter="showTip(this.dataset.fn)" onmouseleave="hideTip()">${displayName}</div>
            <div class="card-meta">${d.channel_name}<br>${d.date} · ${(d.file_size/1024/1024).toFixed(1)} Mo</div>
            <span class="badge ${d.status}">${d.status}</span>
            ${matchH}
            <div style="margin-top:4px; display:flex; justify-content:center;">
                <button class="btn" style="padding:4px; font-size:11px; background:#475569; width:100%; border:none; color:white;" onclick="event.stopPropagation(); openModal(${d.message_id}, '${safeOriginal}', '${cleanName}')">🔍 Recherche manuelle</button>
            </div>
            <div class="progress-container" id="dl-container-${d.message_id}">
                <div class="progress-bar" id="dl-progress-${d.message_id}"></div>
            </div>
            <div class="dl-status" id="dl-status-${d.message_id}"></div>
          </div>
          <div class="checkmark">✓</div>
        </div>`;
      }).join('');
      updateCounter(items.length);
    }
    
    const COLORS = ['#ef4444','#f97316','#eab308','#22c55e','#14b8a6','#3b82f6','#8b5cf6','#ec4899'];

    function toggleCard(card) {
      const id=parseInt(card.dataset.id);
      if (selected.has(id)){selected.delete(id);card.classList.remove('selected');}
      else{selected.add(id);card.classList.add('selected');}
      updateCounter();
    }
    function selectAllVisible() {
      document.querySelectorAll('.card').forEach(c=>{
          const id = parseInt(c.dataset.id);
          if(c.style.display !== 'none') {
              selected.add(id); c.classList.add('selected');
          }
      });
      updateCounter();
    }
    function deselectAll() {
      selected.clear();
      document.querySelectorAll('.card').forEach(c=>c.classList.remove('selected'));
      updateCounter();
    }
    function updateCounter(vis) {
      const v = vis!==undefined ? vis : document.querySelectorAll('.card').length;
      const s = selected.size;
      document.getElementById('counter').textContent=`${v} visible / ${s} sélec.`;
      const btn=document.getElementById('export-btn');
      btn.textContent=`⬇️ Télécharger (${s})`;
      btn.disabled=s===0;
    }
    
    function downloadSelection() {
        if (!dlSocket || dlSocket.readyState !== WebSocket.OPEN) {
            alert("Erreur: WebSocket de téléchargement non connecté.");
            return;
        }
        DATA.filter(d => selected.has(d.message_id)).forEach(d => {
            dlSocket.send(JSON.stringify({
                action: "download",
                message_id: d.message_id,
                channel: d.channel,
                filename: d.filename
            }));
        });
        deselectAll();
    }

    /* Modale Recherche Manuelle */
    function openModal(msgId, originalFilename, cleanName) {
        currentModalMsgId = msgId;
        currentModalOriginal = originalFilename;
        document.getElementById('modal-query').value = cleanName;
        document.getElementById('modal-results').innerHTML = '';
        document.getElementById('search-modal').style.display = 'flex';
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
            resultsDiv.innerHTML = '<div class="help-text" style="color:#ef4444;">Erreur Everything.</div>';
        }
        btn.innerText = "Chercher";
    }
    
    function selectManualResult(result) {
        const matchHint = document.getElementById(`match-${currentModalMsgId}`);
        if (matchHint) {
            matchHint.innerHTML = `Manuel: ${result.score}% - ${result.filename}`;
            matchHint.style.color = '#38bdf8';
        }
        closeModal('search-modal');
    }
</script>
</body>
</html>'''

import re
with open('C:\\Users\\steph\\Documents\\projetBDTelegram\\web_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

parts = content.split('INDEX_HTML = r"""')
if len(parts) == 2:
    prefix = parts[0]
    suffix = parts[1].split('"""', 1)[1]
    new_content = prefix + 'INDEX_HTML = r"""\n' + html_content + '\n"""' + suffix
    with open('C:\\Users\\steph\\Documents\\projetBDTelegram\\web_ui.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Done")
else:
    print("INDEX_HTML not found")
