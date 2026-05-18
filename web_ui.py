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
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-bottom:2px}
.card-meta {font-size:0.65rem;color:#64748b;line-height:1.4}
.badge {display:inline-block;padding:2px 7px;border-radius:10px;font-size:0.65rem;font-weight:700; align-self:flex-start; cursor:pointer; transition: filter 0.2s;}
.badge:hover {filter: brightness(1.3);}
.badge.NOUVEAU {background:#052e16;color:#22c55e;border:1px solid #22c55e40}
.badge.INCERTAIN {background:#1c1407;color:#f59e0b;border:1px solid #f59e0b40}
.badge.DOUBLON {background:#2e0505;color:#ef4444;border:1px solid #ef444440}
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
      return 'https://www.bedetheque.com/search/albums?RechTexte=' + encodeURIComponent(title);
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
          
        const bdtH = (u => u ? `<a class="bdt-link" href="${u}" target="_blank" onclick="event.stopPropagation()" title="BDthèque">📚</a>` : '')(bdtUrl(d.filename));
        
        return `<div class="card${isSel?' selected':''}" data-id="${d.message_id}" onclick="toggleCard(this)">
          ${imgH}
          ${bdtH}
          <div class="card-info">
            <div class="card-title" data-fn="${d.filename}" onmouseenter="showTip(this.dataset.fn)" onmouseleave="hideTip()">${displayName}</div>
            <div class="card-meta">${d.channel_name}<br>${d.date} · ${(d.file_size/1024/1024).toFixed(1)} Mo</div>
            <span class="badge ${d.status}" onclick="event.stopPropagation(); openModal(${d.message_id}, '${safeOriginal}', '${cleanName}', '${encodeURIComponent(JSON.stringify(d.everything_results))}')" title="Cliquez pour voir/modifier la correspondance">${d.status}</span>
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
    function openModal(msgId, originalFilename, cleanName, autoResultsJson) {
        currentModalMsgId = msgId;
        currentModalOriginal = originalFilename;
        document.getElementById('modal-query').value = cleanName;
        
        const resultsDiv = document.getElementById('modal-results');
        resultsDiv.innerHTML = '';
        
        let autoResults = [];
        try { if(autoResultsJson) autoResults = JSON.parse(decodeURIComponent(autoResultsJson)); } catch(e){}
        
        if (autoResults && autoResults.length > 0) {
            const title = document.createElement('div');
            title.className = 'help-text';
            title.innerHTML = '<b>Résultats automatiques :</b>';
            title.style.marginBottom = '5px';
            resultsDiv.appendChild(title);
            
            autoResults.forEach(r => {
                const item = document.createElement('div');
                item.className = 'modal-result-item';
                item.innerHTML = `<strong>[${r.score}]</strong> ${r.filename}<br><span style="color:#64748b;font-size:11px;">${r.path}</span>`;
                item.onclick = () => selectManualResult(r);
                resultsDiv.appendChild(item);
            });
            
            const sep = document.createElement('div');
            sep.style.borderTop = '1px solid #334155';
            sep.style.margin = '10px 0';
            resultsDiv.appendChild(sep);
        } else {
            resultsDiv.innerHTML = '<div class="help-text">Aucun résultat automatique. Cherchez ci-dessus.</div>';
        }
        
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
        const card = document.querySelector(`.card[data-id="${currentModalMsgId}"]`);
        if(card) {
            const badge = card.querySelector('.badge');
            if(badge) {
                badge.className = 'badge DOUBLON';
                badge.innerText = 'DOUBLON (Manuel)';
            }
        }
        closeModal('search-modal');
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
