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
    <title>BD Telegram Tracker</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📚</text></svg>">
    <style>
* {box-sizing:border-box;margin:0;padding:0}
:root {--card-w:180px}
body {font-family:'Segoe UI',system-ui,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
header {position:sticky;top:0;z-index:50;background:#0f172aee;backdrop-filter:blur(8px);
  border-bottom:1px solid #1e293b;padding:6px 16px;display:flex;flex-wrap:wrap;gap:5px;align-items:center}
h1 {font-size:1.15rem;color:#60a5fa;flex:0 0 auto;white-space:nowrap; margin-right:10px;}
.pills {display:flex;gap:6px;flex-wrap:wrap}
.filters {display:flex;gap:5px; margin-left: 10px;}
.fb {background:#1e293b;border:1px solid #334155;color:#94a3b8;padding:4px 11px;
  border-radius:20px;cursor:pointer;font-size:0.75rem;transition:all .2s;white-space:nowrap;}
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
.btn:hover:not(:disabled) {border-color:#3b82f6;color:#60a5fa;}
.btn:disabled {opacity:0.5; cursor:not-allowed;}
.btn-primary { background:#3b82f6; color:white; border-color:#2563eb; font-weight:bold; }
.btn-primary:hover:not(:disabled) { background:#2563eb; color:white; }
.btn-download {background:#8b5cf6;border:none;color:#fff;padding:5px 14px;
  border-radius:8px;cursor:pointer;font-weight:700;font-size:0.82rem;transition:background .2s;white-space:nowrap}
.btn-download:hover:not(:disabled) {background:#7c3aed}
.btn-download:disabled {opacity:0.5; cursor:not-allowed}

/* Grid & Cards */
.grid {display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--card-w),1fr));gap:12px;padding:16px}
.card {position:relative;border-radius:10px;overflow:hidden;background:#1e293b;
  cursor:pointer;transition:transform .2s,box-shadow .2s,border-color .2s;border:2px solid transparent}
.card:hover {transform:scale(1.04);box-shadow:0 8px 24px #00000070;z-index:2}
.card.selected {border-color:#22c55e;box-shadow:0 0 0 3px #22c55e30}
.cover {width:100%;aspect-ratio:3/4;object-fit:cover;display:block;background:#0f172a;cursor:zoom-in;}
.card-info {padding:7px 9px 9px; display:flex; flex-direction:column; gap:4px;}
.card-title {font-size:0.75rem;font-weight:600;line-height:1.3;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-bottom:2px}
.card-meta {font-size:0.65rem;color:#64748b;line-height:1.4}
.badge {display:inline-block;padding:2px 7px;border-radius:10px;font-size:0.65rem;font-weight:700; align-self:flex-start; cursor:pointer; transition: filter 0.2s;}
.badge:hover {filter: brightness(1.3);}
.badge.NOUVEAU {background:#052e16;color:#22c55e;border:1px solid #22c55e40}
.badge.INCERTAIN {background:#1c1407;color:#f59e0b;border:1px solid #f59e0b40}
.badge.DOUBLON {background:#2e0505;color:#ef4444;border:1px solid #ef444440}
.checkmark {position:absolute;top:7px;right:7px;width:24px;height:24px;border-radius:50%;
  background:#0f172acc;border:2px solid #94a3b8;color:#94a3b8;display:flex;align-items:center;justify-content:center;
  font-size:13px;font-weight:700;cursor:pointer;transition:all .2s;z-index:10;box-shadow:0 2px 6px #00000080}
.checkmark:hover {border-color:#22c55e;color:#22c55e;background:#0f172a;transform:scale(1.15)}
.card.selected .checkmark {background:#22c55e;border-color:#22c55e;color:#fff;box-shadow:0 0 8px #22c55e80;transform:scale(1.05)}
.bdt-link {position:absolute;top:7px;left:7px;width:22px;height:22px;border-radius:50%;
  background:#1e293bcc;color:#60a5fa;display:flex;align-items:center;justify-content:center;
  font-size:12px;text-decoration:none;opacity:0;transition:opacity .2s;border:1px solid #3b82f660}
.card:hover .bdt-link {opacity:1}

.pin-link {position:absolute;top:7px;right:36px;width:24px;height:24px;border-radius:50%;
  background:#0f172acc;color:#94a3b8;display:flex;align-items:center;justify-content:center;
  font-size:13px;cursor:pointer;opacity:0;transition:all .2s;border:1px solid #94a3b860; z-index:10;}
.card:hover .pin-link {opacity:1}
.pin-link:hover {transform:scale(1.15);border-color:#f59e0b;color:#f59e0b;}
.pin-link.pinned {opacity:1 !important; background:#f59e0b !important; color:#ffffff !important; border:2px solid #fbbf24 !important; box-shadow:0 0 10px rgba(245,158,11,0.8); transform:scale(1.1);}
.pin-link.pinned:hover {background:#d97706 !important; transform:scale(1.2);}


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

<header style="flex-direction: column; gap: 10px; align-items: stretch; padding: 10px 20px;">
  <div style="display:flex; justify-content:space-between; align-items:center; width:100%; flex-wrap:wrap; gap:10px;">
      <div style="display:flex; align-items:center; gap:16px; flex-wrap:wrap;">
          <h1 style="margin:0;">📚 BD Telegram</h1>
          <div style="display:flex; align-items:center; gap:10px; background:#1e293b; padding:4px 12px; border-radius:8px; border:1px solid #334155; flex-wrap:wrap;">
              <div style="display:flex; align-items:center; gap:6px;">
                  <span style="font-size:12px; font-weight:600; color:#94a3b8; text-transform:uppercase;">📡 Canal :</span>
                  <select id="header-channel-select" onchange="changeActiveChannel(parseInt(this.value))" style="background:#0f172a; color:#38bdf8; font-weight:700; border:1px solid #38bdf860; border-radius:5px; padding:4px 10px; font-size:13px; cursor:pointer; outline:none; max-width:280px;">
                  </select>
              </div>
              <div style="display:flex; align-items:center; gap:6px; background:#0f172a; padding:3px 8px; border-radius:5px; border:1px solid #334155;">
                  <label for="header-channel-date" style="font-size:12px; color:#94a3b8; font-weight:600; cursor:pointer;" title="Modifier directement la date de départ du canal actif">📅 Date :</label>
                  <input type="date" id="header-channel-date" onchange="onHeaderDateChange(this.value)" style="background:transparent; color:#60a5fa; font-weight:700; border:none; padding:1px 4px; font-size:12px; cursor:pointer; outline:none;" title="Date de départ pour le scan chronologique de ce canal">
              </div>
          </div>
      </div>
      <div class="actions">
        <button class="btn" onclick="document.getElementById('settings-modal').style.display='flex'; renderSettingsChannelsList();">⚙️ Config & Canaux</button>
      </div>
  </div>
  
  <div style="display:flex; gap: 20px; flex-wrap: wrap; background: #1e293b; padding: 10px; border-radius: 8px; align-items: stretch;" id="header-4-zones">
      <!-- Catégorie: Bibliothèque Locale -->
      <div style="flex: 1; display:flex; flex-direction:column; gap:8px; border-right: 1px solid #334155; padding-right: 20px;">
          <h3 style="font-size: 13px; color: #94a3b8; margin:0; text-transform:uppercase;">Bibliothèque Locale</h3>
          <div style="display:flex; gap:10px;">
              <button class="btn" id="btn-pile" style="background:#f59e0b; color:white; border:none; white-space:nowrap;" onclick="togglePileALire()">📚 Ma pile à lire</button>
              <input type="text" id="local-search" placeholder="Recherche (Everything)..." style="padding:6px; border-radius:4px; border:1px solid #475569; background:#0f172a; color:white; font-size:13px; width:100%;" onkeydown="if(event.key==='Enter') executeLocalSearch()">
              <button class="btn btn-primary" id="btn-everything" onclick="executeLocalSearch()" style="padding:6px 10px;">🔍</button>
              <button class="btn" id="btn-everything-back" onclick="goBack()" style="display:none; background:#64748b; color:white; border:none; padding:6px 10px;">🔙 Retour</button>
          </div>
      </div>
      
      <!-- Catégorie: Scan Telegram -->
      <div style="flex: 1; display:flex; flex-direction:column; gap:8px; border-right: 1px solid #334155; padding-right: 20px;">
          <h3 style="font-size: 13px; color: #94a3b8; margin:0; text-transform:uppercase;">Scan Chronologique <span id="title-scan-date" style="color:#60a5fa; font-weight:bold;"></span></h3>
          <div style="display:flex; gap:10px; align-items:center;">
              <button class="btn" id="btn-scan-prev" style="display:none; background:#8b5cf6; color:white; border:none; white-space:nowrap;" onclick="goPreviousPage()">⏪ Précédentes</button>
              <button class="btn btn-primary" id="btn-scan" onclick="startDynamicScan()" style="white-space:nowrap;">🚀 Scanner</button>
              <button class="btn" id="btn-scan-next" style="display:none; background:#8b5cf6; color:white; border:none; white-space:nowrap;" onclick="startDynamicScan(true, null)">⏩ Suivantes</button>
              <button class="btn" id="btn-scan-stop" style="display:none; background:#ef4444; color:white; border:none; white-space:nowrap;" onclick="stopScan()">🛑 Arrêter</button>
          </div>
      </div>
      
      <!-- Catégorie: Recherche Telegram -->
      <div style="flex: 1; display:flex; flex-direction:column; gap:8px; border-right: 1px solid #334155; padding-right: 20px;">
          <h3 style="font-size: 13px; color: #94a3b8; margin:0; text-transform:uppercase;">Recherche Spécifique (Telegram)</h3>
          <div style="display:flex; gap:10px;">
              <input type="text" id="tg-search" placeholder="Titre de la BD..." style="padding:6px; border-radius:4px; border:1px solid #475569; background:#0f172a; color:white; font-size:13px; width:100%;" onkeydown="if(event.key==='Enter') startTgSearch()">
              <button class="btn" id="btn-search-prev" style="display:none; background:#8b5cf6; color:white; border:none; white-space:nowrap;" onclick="goPreviousPage()">⏪ Précédentes</button>
              <button class="btn btn-primary" id="btn-search-main" onclick="startTgSearch()" style="padding:6px 10px;">🔍</button>
              <button class="btn" id="btn-search-next" style="display:none; background:#8b5cf6; color:white; border:none; white-space:nowrap;" onclick="startDynamicScan(true, currentSearchQuery)">⏩ Suivantes</button>
              <button class="btn" id="btn-search-stop" style="display:none; background:#ef4444; color:white; border:none; white-space:nowrap;" onclick="stopScan()">🛑 Arrêter</button>
          </div>
      </div>
      
      <!-- Catégorie: Téléchargements -->
      <div style="flex: 1; display:flex; flex-direction:column; gap:8px;">
          <h3 style="font-size: 13px; color: #94a3b8; margin:0; text-transform:uppercase;">Téléchargements</h3>
          <div style="display:flex; flex-direction:column; gap:4px; height:100%;">
              <div id="queue-indicator" style="color:white; font-size:13px; line-height:1.4; cursor:pointer;" onclick="document.getElementById('downloads-modal').style.display='flex'; renderDownloadsModal();">
                  <span style="color:#64748b;">🛒 À télécharger vide</span>
              </div>
              <div id="global-dl-indicator" style="color:white; font-size:13px; line-height:1.4; cursor:pointer; display:none;" onclick="document.getElementById('downloads-modal').style.display='flex'; renderDownloadsModal();">
              </div>
          </div>
      </div>
  </div>
  
  <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 2px; gap: 20px;" id="scan-controls">
      <!-- Bloc Gauche (1/3): Filtres et Statut -->
      <div style="flex: 1; display: flex; align-items: center; justify-content: flex-start; gap: 10px;" id="filter-container">
        <div class="filters" style="display:flex;">
            <button class="fb active" data-f="ALL" onclick="toggleFilter('ALL')">Tous <span id="cnt-ALL"></span></button>
            <button class="fb" data-f="NOUVEAU" onclick="toggleFilter('NOUVEAU')">Nouveaux <span id="cnt-NOUVEAU"></span></button>
            <button class="fb" data-f="INCERTAIN" onclick="toggleFilter('INCERTAIN')">Incertains <span id="cnt-INCERTAIN"></span></button>
            <button class="fb" data-f="DOUBLON" onclick="toggleFilter('DOUBLON')">Doublons <span id="cnt-DOUBLON"></span></button>
        </div>
        <span id="scan-status" style="font-size: 0.8rem; color: #38bdf8; white-space: nowrap;">Prêt.</span>
      </div>
      
      <!-- Bloc Centre (1/3): Recherche et Zoom -->
      <div style="flex: 1; display: flex; align-items: center; justify-content: center; gap: 15px;">
          <div class="search-wrap" style="width: 100%; max-width: 300px;">
            <input id="search" type="text" placeholder="🔍 Filtrer résultats affichés..." oninput="applyFilters()" style="width: 100%;">
          </div>
          <div class="zoom-wrap" style="white-space: nowrap;">🔍 <input type="range" id="zoom" min="130" max="320" value="180" oninput="setZoom(this.value)"></div>
      </div>
      
      <!-- Bloc Droite (1/3): Actions de sélection et téléchargement -->
      <div style="flex: 1; display: flex; align-items: center; justify-content: flex-end; gap: 10px;" class="actions">
        <span id="counter" style="white-space: nowrap; font-size: 0.9rem; color: #94a3b8;">0 visible / 0 sélec.</span>
        <button class="btn" onclick="selectAllVisible()">Tout cocher</button>
        <button class="btn" onclick="deselectAll()">Décocher</button>
        <button id="export-btn" class="btn-download" disabled onclick="addToQueueFromSelection()">📥 Panier (0)</button>
      </div>
  </div>
</header>


<div id="grid" class="grid"></div>
<div id="pile-grid" class="grid" style="display:none;"></div>
<div id="everything-grid" style="display:none; flex-direction:column; gap:5px; margin: 20px;"></div>
<div id="no-results">Aucun album pour ce filtre ou la galerie est vide.</div>

<!-- Modal Config -->
<div class="modal-overlay" id="settings-modal" onclick="closeModal('settings-modal')">
  <div class="modal-content" onclick="event.stopPropagation()" style="max-width: 720px; width: 95%;">
    <div class="modal-hdr">
      <h2>⚙️ Paramètres & Gestion des Canaux</h2>
      <button class="modal-close" onclick="closeModal('settings-modal')">&times;</button>
    </div>
    
    <div style="overflow-y: auto; max-height: 72vh; padding-right: 5px; display: flex; flex-direction: column; gap: 16px;">
        <!-- Section Canaux Telegram & Dates -->
        <div style="background: #0f172a; padding: 14px; border-radius: 8px; border: 1px solid #334155;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 10px;">
                <h3 style="font-size: 13px; color: #38bdf8; margin:0; text-transform:uppercase; font-weight: bold;">📡 Canaux Telegram & Dates de Départ</h3>
                <span style="font-size: 11px; color: #94a3b8;">Progression individuelle par canal</span>
            </div>
            
            <div id="settings-channels-list" style="display:flex; flex-direction:column; gap:8px;">
                <!-- Rendu dynamique des canaux -->
            </div>

            <!-- Formulaire d'ajout de canal -->
            <div style="display:flex; gap:8px; align-items:center; margin-top: 12px; background: #1e293b; padding: 10px; border-radius: 6px; border: 1px dashed #475569; flex-wrap:wrap;">
                <input type="text" id="new-channel-id" placeholder="ID du canal (ex: -1001774120183)" style="flex:1; min-width:180px; padding:6px 10px; border-radius:4px; border:1px solid #475569; background:#0f172a; color:white; font-size:12px;">
                <div style="display:flex; align-items:center; gap:6px;">
                    <label for="new-channel-date" style="font-size:11px; color:#94a3b8;">Départ :</label>
                    <input type="date" id="new-channel-date" style="padding:5px 8px; border-radius:4px; border:1px solid #475569; background:#0f172a; color:white; font-size:12px;" title="Date de départ (optionnelle)">
                </div>
                <button class="btn btn-primary" onclick="addNewChannel()" style="padding:6px 12px; font-size:12px; white-space:nowrap;">➕ Ajouter</button>
            </div>
        </div>

        <!-- Section Paramètres Généraux -->
        <div class="settings-grid" style="gap: 12px;">
            <div class="form-label">Dossiers BD Locaux :</div>
            <div>
                <input type="text" id="bd_search_paths" onchange="updateConfig()" placeholder="ex: F:\BD, F:\Téléchargements">
                <div class="help-text">Dossiers pour Everything séparés par des virgules.</div>
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
            <div class="form-label">Limite d'affichage (Max) :</div>
            <div>
                <input type="number" id="max_gallery_size" onchange="updateConfig()">
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
</div>

<!-- Modal Recherche -->
<div class="modal-overlay" id="search-modal" onclick="closeModal('search-modal')">
    <div class="modal-content" onclick="event.stopPropagation()">
        <div class="modal-hdr">
            <h2>🔍 Recherche sur le disque</h2>
            <button class="modal-close" onclick="closeModal('search-modal')">&times;</button>
        </div>
        <div style="display:flex; gap:10px;">
            <input type="text" id="modal-query" style="flex-grow:1; font-size:14px;" placeholder="Titre de la BD..." onkeydown="if(event.key==='Enter') executeModalSearch()">
            <button class="btn btn-primary" id="modal-search-btn" onclick="executeModalSearch()">Chercher</button>
            <button class="btn" style="background:#ef4444; color:white; border:none;" onclick="resetManualResult()">Annuler</button>
        </div>
        <div id="modal-results">
            <div class="help-text">Entrez un titre pour chercher.</div>
        </div>
    </div>
</div>


<!-- Modal Downloads -->
<div class="modal-overlay" id="downloads-modal" onclick="closeModal('downloads-modal')">
    <div class="modal-content" onclick="event.stopPropagation()" style="max-width:800px;">
        <div class="modal-hdr">
            <h2>📥 Gestion des Téléchargements</h2>
            <button class="modal-close" onclick="closeModal('downloads-modal')">&times;</button>
        </div>
        <div style="display:flex; gap:20px; height:450px;">
            <!-- Colonne Panier -->
            <div style="flex:1; display:flex; flex-direction:column; border-right:1px solid #334155; padding-right:15px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <h3 style="font-size:14px; color:#38bdf8; margin:0;">🛒 À télécharger (<span id="modal-queue-count">0</span>)</h3>
                    <div>
                        <button id="btn-clear-queue" class="btn" style="background:#ef4444; color:white; border:none; padding:4px 8px; margin-right:5px; display:none;" onclick="clearQueue()">🗑️ Vider</button>
                        <button id="btn-start-queue" class="btn" style="background:#22c55e; color:white; border:none; padding:4px 8px; display:none;" onclick="startQueuedDownloads()">🚀 Lancer Tout</button>
                    </div>
                </div>
                <div id="queue-list" style="flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:8px;">
                    <div class="help-text">Le panier est vide.</div>
                </div>
            </div>
            <!-- Colonne En Cours -->
            <div style="flex:1; display:flex; flex-direction:column; padding-left:5px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <h3 style="font-size:14px; color:#38bdf8; margin:0;">⏳ En cours / Terminés <span id="dl-speed" style="font-size:0.8rem; color:#94a3b8; font-weight:normal;"></span></h3>
                    <button class="btn" style="background:#ef4444; color:white; border:none; padding:4px 8px;" onclick="cancelAllDownloads()">Annuler actifs</button>
                </div>
                <div id="downloads-list" style="flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:8px;">
                    <div class="help-text">Aucun téléchargement en cours.</div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Modal Zoom Pochette (Lightbox) -->
<div class="modal-overlay" id="image-modal" onclick="closeModal('image-modal')" style="background: rgba(0, 0, 0, 0.88); backdrop-filter: blur(6px); z-index: 2000; cursor: zoom-out;">
    <div style="position: relative; max-width: 95vw; max-height: 95vh; display: flex; flex-direction: column; align-items: center; justify-content: center;" onclick="event.stopPropagation()">
        <button class="modal-close" onclick="closeModal('image-modal')" style="position: absolute; top: -14px; right: -14px; background: #1e293b; color: white; border: 2px solid #475569; border-radius: 50%; width: 34px; height: 34px; font-size: 20px; line-height: 1; display: flex; align-items: center; justify-content: center; z-index: 2001; cursor: pointer; box-shadow: 0 4px 12px rgba(0,0,0,0.6);" title="Fermer (Échap)">&times;</button>
        <img id="image-modal-img" src="" alt="Pochette BD" style="max-width: 90vw; max-height: 82vh; object-fit: contain; border-radius: 8px; box-shadow: 0 12px 40px rgba(0,0,0,0.9); border: 1px solid #334155; display: block; cursor: default;">
        <div id="image-modal-title" style="margin-top: 12px; color: #f1f5f9; font-size: 1rem; font-weight: 600; text-align: center; max-width: 85vw; text-shadow: 0 2px 6px rgba(0,0,0,0.9); word-break: break-word;"></div>
    </div>
</div>

<div id="tooltip"></div>


<script>
    const DATA = [];
    let toReadList = new Set();
    fetch('/api/list_to_read').then(r=>r.json()).then(items => {
        if(items) items.forEach(i => toReadList.add(i.filename));
    });
    const grid = document.getElementById('grid');
    const statusDiv = document.getElementById('scan-status');
    const btnScan = document.getElementById('btn-scan');
    let dlSocket = null;
    let currentFilter = 'ALL';
    let selected = new Set();

    let activeDownloadsCount = 0;
    let downloadsState = {};
    let downloadQueue = [];
    let scanHistory = [];
    let lastScanDate = null;
    let lastTotalBytes = 0;
    let currentSearchQuery = null;
    let searchSkipCount = 0;
    let currentWebSocket = null;
    
    function customConfirm(msg, showSaveOption = false) {
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.style.position = 'fixed';
            overlay.style.top = '0'; overlay.style.left = '0';
            overlay.style.width = '100vw'; overlay.style.height = '100vh';
            overlay.style.backgroundColor = 'rgba(0,0,0,0.7)';
            overlay.style.zIndex = '10000';
            overlay.style.display = 'flex';
            overlay.style.alignItems = 'center';
            overlay.style.justifyContent = 'center';
            
            const box = document.createElement('div');
            box.style.background = '#1e293b';
            box.style.border = '1px solid #475569';
            box.style.borderRadius = '8px';
            box.style.padding = '25px';
            box.style.maxWidth = '450px';
            box.style.color = 'white';
            box.style.textAlign = 'center';
            box.style.boxShadow = '0 10px 25px rgba(0,0,0,0.5)';
            
            const text = document.createElement('div');
            text.innerHTML = msg.replace(/\n/g, '<br>');
            text.style.marginBottom = '25px';
            text.style.lineHeight = '1.5';
            text.style.fontSize = '1.1rem';
            
            const btnWrap = document.createElement('div');
            btnWrap.style.display = 'flex';
            btnWrap.style.gap = '15px';
            btnWrap.style.justifyContent = 'center';
            btnWrap.style.flexDirection = showSaveOption ? 'column' : 'row';
            
            if (showSaveOption) {
                const btnSave = document.createElement('button');
                btnSave.className = 'btn';
                btnSave.style.background = '#22c55e';
                btnSave.style.color = 'white';
                btnSave.style.border = 'none';
                btnSave.style.padding = '10px 15px';
                btnSave.style.fontWeight = 'bold';
                btnSave.innerText = '✅ Valider et ajouter à la liste des téléchargements';
                btnSave.onclick = () => { document.body.removeChild(overlay); resolve('save'); };
                btnWrap.appendChild(btnSave);
            }
            
            const subWrap = document.createElement('div');
            subWrap.style.display = 'flex';
            subWrap.style.gap = '15px';
            subWrap.style.justifyContent = 'center';
            
            const btnOk = document.createElement('button');
            btnOk.className = 'btn';
            btnOk.style.background = '#ef4444';
            btnOk.style.color = 'white';
            btnOk.style.border = 'none';
            btnOk.innerText = showSaveOption ? 'Continuer sans garder' : 'Oui, continuer';
            btnOk.onclick = () => { document.body.removeChild(overlay); resolve('continue'); };
            
            const btnCancel = document.createElement('button');
            btnCancel.className = 'btn';
            btnCancel.style.background = '#64748b';
            btnCancel.style.color = 'white';
            btnCancel.style.border = 'none';
            btnCancel.innerText = 'Annuler';
            btnCancel.onclick = () => { document.body.removeChild(overlay); resolve('cancel'); };
            
            subWrap.appendChild(btnCancel);
            subWrap.appendChild(btnOk);
            btnWrap.appendChild(subWrap);
            box.appendChild(text);
            box.appendChild(btnWrap);
            overlay.appendChild(box);
            document.body.appendChild(overlay);
        });
    }

    function updateQueueIndicator() {
        const ind = document.getElementById('queue-indicator');
        const count = document.getElementById('modal-queue-count');
        const btnStart = document.getElementById('btn-start-queue');
        const btnClear = document.getElementById('btn-clear-queue');
        
        if (downloadQueue.length > 0) {
            ind.innerHTML = `🛒 <b style="color:#38bdf8;">${downloadQueue.length} BD</b> en attente`;
            ind.style.display = 'block';
            if(count) count.innerText = downloadQueue.length;
            if(btnStart) btnStart.style.display = 'inline-block';
            if(btnClear) btnClear.style.display = 'inline-block';
        } else {
            ind.innerHTML = `<span style="color:#64748b;">🛒 À télécharger vide</span>`;
            if(count) count.innerText = "0";
            if(btnStart) btnStart.style.display = 'none';
            if(btnClear) btnClear.style.display = 'none';
        }
        if(document.getElementById('downloads-modal').style.display === 'flex') {
            renderQueueList();
        }
    }
    
    function clearSelection() {
        selected.forEach(id => {
            const item = DATA.find(d => d.message_id === id);
            if (item && toReadList.has(item.filename) && !downloadQueue.some(q => q.message_id === id)) {
                toReadList.delete(item.filename);
                const btn = document.getElementById('btn-read-' + id);
                if (btn) btn.classList.remove('pinned');
                const bRead = document.getElementById('badge-read-' + id);
                if (bRead) bRead.style.display = 'none';
            }
        });
        selected.clear();
    }

    function clearQueue() {
        downloadQueue.forEach(q => {
            if (q.to_read && toReadList.has(q.filename)) {
                toReadList.delete(q.filename);
            }
        });
        downloadQueue = [];
        updateQueueIndicator();
        renderQueueList();
        renderGrid(DATA);
    }

    function setNavigationDisabled(disabled) {
        document.getElementById('btn-scan').disabled = disabled;
        document.getElementById('btn-search-main').disabled = disabled;
        document.getElementById('btn-scan-prev').disabled = disabled;
        document.getElementById('btn-scan-next').disabled = disabled;
        document.getElementById('btn-search-prev').disabled = disabled;
        document.getElementById('btn-search-next').disabled = disabled;
    }
    
    // Speed tracking
    setInterval(() => {
        let currentTotalBytes = 0;
        let isDownloading = false;
        Object.values(downloadsState).forEach(d => {
            if (d.status === 'Préparation...' || d.status === 'En cours') isDownloading = true; // Wait, we don't set "En cours"
            if (d.current) {
                currentTotalBytes += d.current;
                if(d.status !== "Terminé ✅" && d.status !== "Annulé ❌" && !d.status.startsWith("Erreur")) isDownloading = true;
            }
        });
        
        const speedSpan = document.getElementById('dl-speed');
        if (isDownloading && lastTotalBytes > 0 && currentTotalBytes >= lastTotalBytes) {
            const bytesPerSec = currentTotalBytes - lastTotalBytes;
            if (bytesPerSec > 1024 * 1024) {
                speedSpan.innerText = `(${(bytesPerSec / 1024 / 1024).toFixed(1)} Mo/s)`;
            } else if (bytesPerSec > 1024) {
                speedSpan.innerText = `(${(bytesPerSec / 1024).toFixed(0)} Ko/s)`;
            } else {
                speedSpan.innerText = `(${bytesPerSec} o/s)`;
            }
        } else {
            speedSpan.innerText = '';
        }
        lastTotalBytes = currentTotalBytes;
    }, 1000);

    function renderDownloadsModal() {
        renderQueueList();
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
                <div style="color:${d.status.startsWith('Erreur') ? '#ef4444' : '#94a3b8'}; font-size:11px;">Statut : <span style="color:${d.status.startsWith('Erreur') ? '#ef4444' : '#38bdf8'}">${d.status}</span> ${progText}</div>
                <div style="width:100%; background:#1e293b; height:4px; border-radius:2px; margin-top:4px;">
                    <div style="width:${progWidth}; background:${d.status.startsWith('Erreur') ? '#ef4444' : '#38bdf8'}; height:100%; border-radius:2px; transition:width 0.2s;"></div>
                </div>
            `;
            
            const btnWrap = document.createElement('div');
            btnWrap.style.display = 'flex';
            btnWrap.style.gap = '5px';
            btnWrap.style.marginLeft = '15px';

            const btnCancel = document.createElement('button');
            btnCancel.className = 'btn';
            btnCancel.style.cssText = 'background:#ef4444; color:white; border:none; padding:4px 8px; cursor:pointer; font-size: 11px;';
            btnCancel.innerText = '✕';
            btnCancel.onclick = () => {
                if (d.status.startsWith('Erreur') || d.status === 'Terminé ✅' || d.status.startsWith('Annulé')) {
                    delete downloadsState[id];
                    renderDownloadsModal();
                } else {
                    cancelDownload(id);
                }
            };
            
            if(d.status === 'Terminé ✅' || d.status.startsWith('Annulé')) {
                btnCancel.style.display = 'none';
            } else if (d.status.startsWith('Erreur')) {
                const btnRetry = document.createElement('button');
                btnRetry.className = 'btn';
                btnRetry.style.cssText = 'background:#f59e0b; color:white; border:none; padding:4px 8px; cursor:pointer; font-size: 11px;';
                btnRetry.innerText = '🔄';
                btnRetry.title = 'Recommencer';
                btnRetry.onclick = () => retryDownload(id);
                btnWrap.appendChild(btnRetry);
                btnCancel.title = 'Effacer';
            }
            
            btnWrap.appendChild(btnCancel);
            
            div.appendChild(info);
            div.appendChild(btnWrap);
            list.appendChild(div);
        });
    }

    function retryDownload(id) {
        const d = downloadsState[id];
        if(!d) return;
        d.status = 'En file d\'attente...';
        d.current = 0;
        d.total = 0;
        if(dlSocket && dlSocket.readyState === WebSocket.OPEN) {
            activeDownloadsCount++;
            updateGlobalDownloadIndicator();
            dlSocket.send(JSON.stringify({
                action: "download",
                message_id: parseInt(id),
                channel: d.channel,
                filename: d.filename,
                to_read: d.to_read || false
            }));
        }
        renderDownloadsModal();
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
            if(!downloadsState[msg.message_id]) downloadsState[msg.message_id] = {filename: msg.filename || 'Fichier inconnu', status: 'En file d\'attente', current:0, total:0};
            
            if (msg.type === "status") {
                downloadsState[msg.message_id].status = msg.status;
                if (msg.filename) downloadsState[msg.message_id].filename = msg.filename;
                
                if (msg.status === "Terminé ✅" || msg.status.startsWith("Erreur") || msg.status.startsWith("Annulé")) {
                    activeDownloadsCount--;
                    if(activeDownloadsCount < 0) activeDownloadsCount = 0;
                    updateGlobalDownloadIndicator();
                    if (!msg.status.startsWith("Erreur")) {
                        // Clean up state after 10 seconds if done to prevent memory leak
                        setTimeout(() => { 
                            if(downloadsState[msg.message_id] && !downloadsState[msg.message_id].status.startsWith("Erreur")) {
                                delete downloadsState[msg.message_id]; 
                                if(document.getElementById('downloads-modal').style.display === 'flex') renderDownloadsModal();
                            }
                        }, 10000);
                    }
                    
                    // Hide progress bar on the card
                    const container = document.getElementById(`dl-container-${msg.message_id}`);
                    if (container) {
                        setTimeout(() => { container.style.display = 'none'; }, 2000); // Hide after 2s
                    }
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

    initDownloadSocket();

    let appConfig = {};
    let channelsList = [];
    let activeChannelId = null;

    function updateDateDisplay(dateStr) {
        let clean = dateStr || "";
        if (clean.includes('T')) clean = clean.split('T')[0];
        else if (clean.includes(' ')) clean = clean.split(' ')[0];
        
        const hDate = document.getElementById('header-channel-date');
        const titleDate = document.getElementById('title-scan-date');
        if (hDate && hDate.value !== clean) hDate.value = clean;
        if (titleDate) titleDate.innerText = clean ? `[${clean}]` : '';
    }

    function renderSettingsChannelsList() {
        const list = document.getElementById('settings-channels-list');
        if (!list) return;
        if (!channelsList || channelsList.length === 0) {
            list.innerHTML = '<div class="help-text" style="text-align:center; padding:10px;">Aucun canal configuré. Ajoutez-en un ci-dessous.</div>';
            return;
        }
        
        list.innerHTML = channelsList.map(ch => {
            const isActive = (ch.id === activeChannelId);
            let sDate = ch.start_date || "";
            if (sDate.includes('T')) sDate = sDate.split('T')[0];
            else if (sDate.includes(' ')) sDate = sDate.split(' ')[0];
            
            return `<div style="display:flex; align-items:center; justify-content:space-between; background:#1e293b; padding:8px 12px; border-radius:6px; border:1px solid ${isActive ? '#38bdf8' : '#334155'}; gap:10px; flex-wrap:wrap;">
                <div style="display:flex; align-items:center; gap:10px; flex:1; min-width:200px;">
                    <button class="btn" style="padding:3px 8px; font-size:11px; ${isActive ? 'background:#0284c7; color:white; font-weight:bold;' : 'background:#334155; color:#94a3b8;'}" onclick="changeActiveChannel(${ch.id})" title="Définir comme canal actif">${isActive ? 'Actif ★' : 'Activer'}</button>
                    <div style="display:flex; flex-direction:column;">
                        <span style="font-weight:600; color:white; font-size:13px;">${ch.name}</span>
                        <span style="color:#64748b; font-size:11px;">ID: ${ch.id}</span>
                    </div>
                </div>
                
                <div style="display:flex; align-items:center; gap:8px;">
                    <label style="font-size:11px; color:#94a3b8;">Date de départ :</label>
                    <input type="date" value="${sDate}" onchange="updateChannelDate(${ch.id}, this.value)" style="padding:4px 8px; border-radius:4px; border:1px solid #475569; background:#0f172a; color:white; font-size:12px; width:130px;" title="Changer la date de départ pour ce canal">
                    <button class="btn" style="background:#ef4444; color:white; border:none; padding:4px 8px; font-size:11px; cursor:pointer;" onclick="removeChannel(${ch.id})" title="Supprimer ce canal">🗑️</button>
                </div>
            </div>`;
        }).join('');
    }

    function onHeaderDateChange(newVal) {
        if (!activeChannelId) return;
        updateChannelDate(activeChannelId, newVal);
    }

    function updateChannelDate(chId, newDate) {
        if (!appConfig.channel_start_dates) appConfig.channel_start_dates = {};
        appConfig.channel_start_dates[chId.toString()] = newDate;
        
        const ch = channelsList.find(c => c.id === chId);
        if (ch) ch.start_date = newDate;
        
        if (chId === activeChannelId) {
            lastScanDate = newDate || null;
            updateDateDisplay(newDate);
        }
        
        renderSettingsChannelsList();
        
        fetch('/api/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                start_date: (chId === activeChannelId) ? newDate : (appConfig.start_date || ""),
                active_channel: activeChannelId,
                channel_start_dates: appConfig.channel_start_dates
            })
        });
    }

    async function addNewChannel() {
        const idInput = document.getElementById('new-channel-id');
        const dateInput = document.getElementById('new-channel-date');
        let rawVal = idInput.value.trim();
        if (!rawVal) return;
        
        let chId = parseInt(rawVal);
        if (isNaN(chId)) {
            alert("Veuillez saisir un identifiant numérique valide pour le canal (ex: -1001774120183)");
            return;
        }
        
        if (channelsList.some(c => c.id === chId)) {
            alert("Ce canal est déjà présent dans la liste.");
            return;
        }
        
        const initDate = dateInput.value || "";
        if (!appConfig.channels) appConfig.channels = [];
        appConfig.channels.push(chId);
        
        if (!appConfig.channel_start_dates) appConfig.channel_start_dates = {};
        appConfig.channel_start_dates[chId.toString()] = initDate;
        
        idInput.value = "";
        dateInput.value = "";
        
        await fetch('/api/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                channels: appConfig.channels,
                channel_start_dates: appConfig.channel_start_dates
            })
        });
        
        loadChannelsAndConfig();
    }

    async function removeChannel(chId) {
        if (!confirm("Voulez-vous vraiment supprimer ce canal de la liste ?")) return;
        
        appConfig.channels = (appConfig.channels || []).filter(id => id !== chId);
        if (appConfig.channel_start_dates) {
            delete appConfig.channel_start_dates[chId.toString()];
        }
        
        if (activeChannelId === chId) {
            activeChannelId = appConfig.channels.length > 0 ? appConfig.channels[0] : null;
        }
        
        await fetch('/api/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                channels: appConfig.channels,
                active_channel: activeChannelId,
                channel_start_dates: appConfig.channel_start_dates
            })
        });
        
        loadChannelsAndConfig();
    }

    function loadChannelsAndConfig() {
        fetch('/api/channels_list').then(r=>r.json()).then(data => {
            channelsList = data.channels || [];
            activeChannelId = data.active_channel || (channelsList[0] ? channelsList[0].id : null);
            
            const hSelect = document.getElementById('header-channel-select');
            if (hSelect) hSelect.innerHTML = '';
            
            channelsList.forEach(ch => {
                const opt1 = document.createElement('option');
                opt1.value = ch.id;
                opt1.innerText = ch.name;
                if (ch.id === activeChannelId) opt1.selected = true;
                if (hSelect) hSelect.appendChild(opt1);
            });
            
            const currentCh = channelsList.find(c => c.id === activeChannelId);
            const sDate = currentCh ? currentCh.start_date : "";
            lastScanDate = sDate || null;
            updateDateDisplay(sDate);
            renderSettingsChannelsList();
        });

        fetch('/api/config').then(r=>r.json()).then(c => {
            appConfig = c;
            if(c.filename_filter) document.getElementById('filename_filter').value = c.filename_filter.join(', ');
            if(c.bd_search_paths) document.getElementById('bd_search_paths').value = c.bd_search_paths.join(', ');
            if(c.download_concurrency) document.getElementById('download_concurrency').value = c.download_concurrency;
            if(c.max_gallery_size) document.getElementById('max_gallery_size').value = c.max_gallery_size;
            if(c.fuzzy_threshold_duplicate) document.getElementById('fuzzy_threshold_duplicate').value = c.fuzzy_threshold_duplicate;
            if(c.fuzzy_threshold_review) document.getElementById('fuzzy_threshold_review').value = c.fuzzy_threshold_review;
        });
    }

    loadChannelsAndConfig();

    async function changeActiveChannel(newChannelId) {
        if (newChannelId === activeChannelId) return;
        if (selected.size > 0) {
            const confirmed = await customConfirm("Vous avez " + selected.size + " BD sélectionnée(s) qui n'ont pas été ajoutées au panier.\nVoulez-vous vraiment changer de canal et perdre cette sélection ?", true);
            if (confirmed === 'cancel') {
                if (document.getElementById('header-channel-select')) document.getElementById('header-channel-select').value = activeChannelId;
                return;
            }
            if (confirmed === 'save') {
                addToQueueFromSelection();
            } else {
                clearSelection();
            }
        }
        
        activeChannelId = newChannelId;
        if (document.getElementById('header-channel-select')) document.getElementById('header-channel-select').value = activeChannelId;
        
        const ch = channelsList.find(c => c.id === activeChannelId);
        let sDate = (ch && ch.start_date) ? ch.start_date : "";
        if (sDate.includes('T')) sDate = sDate.split('T')[0];
        else if (sDate.includes(' ')) sDate = sDate.split(' ')[0];
        
        updateDateDisplay(sDate);
        lastScanDate = sDate || null;
        renderSettingsChannelsList();
        
        // Nettoyer la vue pour le nouveau canal
        grid.innerHTML = "";
        DATA.length = 0;
        scanHistory = [];
        statusDiv.innerText = `Canal actif : ${ch ? ch.name : activeChannelId}`;
        statusDiv.style.color = "#38bdf8";
        
        document.getElementById('btn-scan-prev').style.display = 'none';
        document.getElementById('btn-scan-next').style.display = 'none';
        document.getElementById('btn-search-prev').style.display = 'none';
        document.getElementById('btn-search-next').style.display = 'none';
        
        updateCounter(0);
        
        fetch('/api/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ active_channel: activeChannelId })
        });
    }

    function updateConfig() {
        const filterStr = document.getElementById('filename_filter').value;
        const filter = filterStr ? filterStr.split(',').map(s => s.trim()).filter(s => s) : [];
        const bdPathsStr = document.getElementById('bd_search_paths').value;
        const bdPaths = bdPathsStr ? bdPathsStr.split(',').map(s => s.trim()).filter(s => s) : [];
        const concurrency = parseInt(document.getElementById('download_concurrency').value) || 5;
        const maxGal = parseInt(document.getElementById('max_gallery_size').value) || 50;
        const threshDup = parseInt(document.getElementById('fuzzy_threshold_duplicate').value) || 85;
        const threshRev = parseInt(document.getElementById('fuzzy_threshold_review').value) || 50;
        
        fetch('/api/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                active_channel: activeChannelId,
                channel_start_dates: appConfig.channel_start_dates,
                filename_filter: filter,
                download_concurrency: concurrency,
                max_gallery_size: maxGal,
                fuzzy_threshold_duplicate: threshDup,
                fuzzy_threshold_review: threshRev,
                channels: appConfig.channels,
                bd_search_paths: bdPaths
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
      return 'https://duckduckgo.com/?q=' + encodeURIComponent('!lucky site:bedetheque.com ' + title);
    }
    function closeModal(id) { document.getElementById(id).style.display='none'; }
    document.addEventListener('keydown', e=>{ 
        if(e.key==='Escape') { 
            closeModal('settings-modal'); 
            closeModal('search-modal'); 
            closeModal('downloads-modal'); 
            closeModal('image-modal'); 
        } 
    });

    function openImagePreview(src, title) {
        if (!src) return;
        const modal = document.getElementById('image-modal');
        const img = document.getElementById('image-modal-img');
        const titleEl = document.getElementById('image-modal-title');
        img.src = src;
        titleEl.textContent = title || '';
        modal.style.display = 'flex';
    }

    /* Scanner Dynamique */
    
    
    
    function addDownloadTask(msg_id, channel, filename, toRead) {
        if (!downloadQueue.find(q => q.message_id === msg_id)) {
            downloadQueue.push({
                message_id: msg_id,
                channel: channel,
                filename: filename,
                to_read: toRead
            });
        } else {
            const item = downloadQueue.find(q => q.message_id === msg_id);
            if (toRead) item.to_read = true;
        }
        updateQueueIndicator();
    }

    function addToRead(msg_id, status, filename, channel) {
        const btn = document.getElementById('btn-read-' + msg_id);
        const bRead = document.getElementById('badge-read-' + msg_id);
        
        if (toReadList.has(filename)) {
            if(btn) { btn.classList.remove('pinned'); btn.title = 'Ajouter à la pile à lire'; btn.style.transform = 'scale(0.8)'; setTimeout(()=>btn.style.transform='none',200); }
            if(bRead) { bRead.style.display = 'none'; }
            toReadList.delete(filename);
            fetch('/api/remove_to_read', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({filename: filename})
            });
            const qItem = downloadQueue.find(q => q.message_id === msg_id);
            if (qItem) {
                qItem.to_read = false;
            }
            return;
        }
        
        if (status === 'DOUBLON') {
            const item = DATA.find(d => d.message_id === msg_id);
            if (item && item.everything_results && item.everything_results.length > 0) {
                const localPath = item.everything_results[0].path;
                const localName = item.everything_results[0].filename;
                const fullLocalPath = localPath.endsWith("\\") ? localPath + localName : localPath + "\\" + localName;
                
                if(btn) { btn.classList.add('pinned'); btn.title = 'Retirer de la pile à lire'; btn.style.transform = 'scale(1.2)'; setTimeout(()=>btn.style.transform='none',200); }
                if(bRead) { 
                    bRead.className = 'badge'; 
                    bRead.style.cssText = 'background:#78350f; color:#fde68a; border:1px solid #f59e0b80; cursor:pointer;'; 
                    bRead.innerText = '📚 Pile à lire'; 
                    bRead.title = 'Retirer de la pile à lire'; 
                    bRead.style.display = 'inline-block'; 
                    bRead.onclick = (e) => { e.stopPropagation(); addToRead(msg_id, status, filename, channel); };
                }
                toReadList.add(filename);
                
                fetch('/api/add_to_read_local', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        local_path: fullLocalPath,
                        message_id: msg_id,
                        filename: filename
                    })
                });
            }
        } else {
            if(btn) { btn.classList.add('pinned'); btn.title = 'Retirer de la pile à lire'; btn.style.transform = 'scale(1.2)'; setTimeout(()=>btn.style.transform='none',200); }
            if(bRead) { 
                bRead.className = 'badge'; 
                bRead.style.cssText = 'background:#78350f; color:#fde68a; border:1px solid #f59e0b80; cursor:pointer;'; 
                bRead.innerText = '📚 Pile à lire'; 
                bRead.title = 'Retirer de la pile à lire'; 
                bRead.style.display = 'inline-block'; 
                bRead.onclick = (e) => { e.stopPropagation(); addToRead(msg_id, status, filename, channel); };
            }
            toReadList.add(filename);
            
            const qItem = downloadQueue.find(q => q.message_id === msg_id);
            if (qItem) {
                qItem.to_read = true;
            } else if (!selected.has(msg_id)) {
                selected.add(msg_id);
                updateCounter(DATA.length);
                const card = document.querySelector(`.card[data-id="${msg_id}"]`);
                if (card) card.classList.add('selected');
            }
        }
    }

    let currentView = 'scan'; // 'scan', 'pile', 'everything'
    let viewHistory = ['scan'];
    
    function switchView(view) {
        if (currentView === view) return;
        viewHistory.push(currentView);
        currentView = view;
        applyViewParams();
    }
    
    function goBack() {
        if (viewHistory.length > 0) {
            currentView = viewHistory.pop();
            applyViewParams();
        } else {
            currentView = 'scan';
            applyViewParams();
        }
    }
    
    function applyViewParams() {
        document.getElementById('grid').style.display = 'none';
        document.getElementById('pile-grid').style.display = 'none';
        document.getElementById('everything-grid').style.display = 'none';
        document.getElementById('scan-controls').style.display = 'none';
        
        Array.from(document.getElementById('header-4-zones').children).forEach((el, i) => { if(i>0) el.style.opacity = '1'; el.style.pointerEvents = 'auto'; });
        document.getElementById('btn-pile').innerHTML = "📚 Ma pile à lire";
        document.getElementById('btn-pile').style.background = "#f59e0b";
        document.getElementById('btn-everything').innerHTML = "🔍";
        document.getElementById('btn-everything').style.background = "#3b82f6";
        document.getElementById('btn-everything').style.display = "block";
        document.getElementById('btn-everything-back').style.display = "none";
        
        if (currentView === 'scan') {
            document.getElementById('grid').style.display = 'grid';
            document.getElementById('scan-controls').style.display = 'flex';
        } else if (currentView === 'pile') {
            document.getElementById('pile-grid').style.display = 'grid';
            document.getElementById('btn-pile').innerHTML = "🔙 Retour";
            document.getElementById('btn-pile').style.background = "#64748b";
            Array.from(document.getElementById('header-4-zones').children).forEach((el, i) => { if(i>0) { el.style.opacity = '0.3'; el.style.pointerEvents = 'none'; } });
        } else if (currentView === 'everything') {
            document.getElementById('everything-grid').style.display = 'flex';
            document.getElementById('btn-everything').style.display = "none";
            document.getElementById('btn-everything-back').style.display = "block";
            Array.from(document.getElementById('header-4-zones').children).forEach((el, i) => { if(i>0) { el.style.opacity = '0.3'; el.style.pointerEvents = 'none'; } });
        }
    }
    
    function togglePileALire() {
        if (currentView === 'pile') {
            goBack();
        } else {
            switchView('pile');
            const pGrid = document.getElementById('pile-grid');
            pGrid.innerHTML = "<h2 style='grid-column: 1 / -1; color: white;'>Chargement de la pile à lire...</h2>";
            document.getElementById('no-results').style.display = 'none';
            fetch('/api/list_to_read').then(r=>r.json()).then(items => {
                if (!items || items.length === 0) { pGrid.innerHTML = "<h2 style='grid-column: 1 / -1; color: white;'>La pile à lire est vide.</h2>"; return; }
                pGrid.innerHTML = items.map(d => {
                    const cleanName = d.filename.replace(/_/g,' ').replace(/\.(cbz|cbr|pdf)$/i,'');
                    const safeClean = cleanName.replace(/'/g, "\\'").replace(/"/g, "&quot;");
                    const imgH = `<img class="cover" src="${d.thumb_url}" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'" onclick="openImagePreview('${d.thumb_url}', '${safeClean}')"><div class="cover" style="display:none;align-items:center;justify-content:center;color:#475569;font-size:3rem;background:#0f172a">${d.filename[0].toUpperCase()}</div>`;
                    const extMatch = d.filename.match(/\.([a-z0-9]+)$/i);
                    const ext = extMatch ? extMatch[1].toUpperCase() : '';
                    return `<div class="card">${imgH}<div class="pin-link pinned" onclick="event.stopPropagation(); removeFromRead('${d.filename.replace(/'/g, "\\'")}')" title="Retirer de la pile à lire">📌</div><div class="card-info" style="margin-top:auto;"><div class="card-title">${cleanName} <span style="font-size:9px; background:#334155; padding:2px 4px; border-radius:4px; vertical-align:middle; color:#e2e8f0; font-weight:normal;">${ext}</span></div></div></div>`;
                }).join('');
            });
        }
    }
    
    function removeFromRead(filename) {
        toReadList.delete(filename);
        fetch('/api/remove_to_read', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({filename: filename})
        }).then(() => {
            // refresh pile
            currentView = 'scan';
            togglePileALire();
        });
    }

    async function executeLocalSearch() {
        const query = document.getElementById('local-search').value.trim();
        if(!query) return;
        
        switchView('everything');
        const eGrid = document.getElementById('everything-grid');
        eGrid.innerHTML = "<h2 style='color: white;'>Recherche locale en cours...</h2>";
        
        try {
            const res = await fetch(`/api/everything?q=${encodeURIComponent(query)}&original=`);
            const results = await res.json();
            
            if (results.length === 0) {
                eGrid.innerHTML = "<h2 style='color: white;'>Aucun résultat local trouvé.</h2>";
                return;
            }
            
            eGrid.innerHTML = '<h2 style="color: white; font-size: 1.1rem; margin-bottom: 10px;">Résultats Everything (' + results.length + ') :</h2>' + results.map(r => {
                const extMatch = r.filename.match(/\.([a-z0-9]+)$/i);
                const ext = extMatch ? extMatch[1].toUpperCase() : '';
                const titleHtml = `<span style="font-size:9px; background:#334155; padding:2px 4px; border-radius:4px; vertical-align:middle; color:#e2e8f0; font-weight:normal; margin-right:4px;">${ext}</span>${r.filename.replace(/_/g,' ').replace(/\.(cbz|cbr|pdf)$/i,'')}`;
                const sizeStr = (r.size / 1024 / 1024).toFixed(1) + ' Mo';
                
                return `<div style="display:flex; align-items:center; background:#1e293b; padding:10px 15px; border-radius:6px; border-left: 4px solid #3b82f6; gap: 15px;">
                  <div style="flex:1;">
                      <div style="font-weight:bold; color:white; font-size:14px; display:flex; align-items:center;">${titleHtml}</div>
                      <div style="color:#94a3b8; font-size:11px; margin-top:2px; word-break: break-all;">${r.path}</div>
                  </div>
                  <div style="color:#94a3b8; font-size:12px; min-width: 60px; text-align:right;">${sizeStr}</div>
                  <div style="color:#64748b; font-size:12px; min-width: 80px; text-align:right;">Fichier local</div>
                </div>`;
            }).join('');
            
        } catch(e) {
            eGrid.innerHTML = "<h2 style='color: #ef4444;'>Erreur lors de la recherche Everything.</h2>";
        }
    }

    async function startTgSearch() {
        const q = document.getElementById('tg-search').value.trim();
        if(!q) return;
        if (selected.size > 0) {
            const confirmed = await customConfirm("Vous avez " + selected.size + " BD sélectionnée(s) qui n'ont pas été ajoutées au panier.\nVoulez-vous vraiment lancer la recherche et perdre cette sélection ?", true);
            if (confirmed === 'cancel') return;
            if (confirmed === 'save') {
                addToQueueFromSelection();
            } else {
                clearSelection();
            }
        }
        currentSearchQuery = q;
        searchSkipCount = 0;
        startDynamicScan(false, q);
    }

    async function goPreviousPage() {
        if (scanHistory.length < 2) return;
        if (selected.size > 0) {
            const confirmed = await customConfirm("Vous avez " + selected.size + " BD sélectionnée(s) qui n'ont pas été ajoutées au panier.\nVoulez-vous vraiment changer de page et perdre cette sélection ?", true);
            if (confirmed === 'cancel') return;
            if (confirmed === 'save') {
                addToQueueFromSelection();
            } else {
                clearSelection();
            }
        }
        scanHistory.pop(); // Remove current page state
        const prev = scanHistory.pop(); // Get previous page state
        startDynamicScan(false, null, prev);
    }

    function stopScan() {
        if (currentWebSocket) {
            currentWebSocket.close();
            currentWebSocket = null;
        }
        statusDiv.innerText = "Scan arrêté manuellement.";
        statusDiv.style.color = "#f59e0b";
        setNavigationDisabled(false);
        document.getElementById('btn-scan-stop').style.display = 'none';
        document.getElementById('btn-search-stop').style.display = 'none';
        
        if (lastScanDate && currentView === 'scan') {
             document.getElementById('btn-scan-next').style.display = 'inline-block';
        }
    }

    async function startDynamicScan(continueFromLast = false, searchQuery = null, restoreState = null) {
        if (selected.size > 0) {
            const confirmed = await customConfirm("Vous avez " + selected.size + " BD sélectionnée(s) qui n'ont pas été ajoutées au panier.\nVoulez-vous vraiment continuer et perdre cette sélection ?", true);
            if (confirmed === 'cancel') return;
            if (confirmed === 'save') {
                addToQueueFromSelection();
            } else {
                clearSelection();
            }
        }
        currentView = 'scan';
        viewHistory = [];
        applyViewParams();
        
        if (restoreState) {
            currentSearchQuery = restoreState.query;
            searchSkipCount = restoreState.skip;
            lastScanDate = restoreState.date;
            if (currentSearchQuery) {
                document.getElementById('tg-search').value = currentSearchQuery;
            }
            continueFromLast = restoreState.isContinue;
            searchQuery = currentSearchQuery;
        } else if (!continueFromLast) {
            scanHistory = [];
        }
        
        if (!restoreState) {
            scanHistory.push({
                query: searchQuery,
                skip: continueFromLast && searchQuery ? searchSkipCount : 0,
                date: continueFromLast && !searchQuery ? lastScanDate : null,
                isContinue: continueFromLast
            });
        } else {
            scanHistory.push(restoreState);
        }
        
        if (!continueFromLast || restoreState) {
            grid.innerHTML = "";
            DATA.length = 0;
            selected.clear();
        }
        DATA.length = 0;
        selected.clear();
        
        const showPrev = scanHistory.length > 1;
        document.getElementById('btn-scan-prev').style.display = showPrev && !searchQuery ? 'inline-block' : 'none';
        document.getElementById('btn-search-prev').style.display = showPrev && searchQuery ? 'inline-block' : 'none';
        document.getElementById('btn-scan-next').style.display = 'none'; 
        document.getElementById('btn-search-next').style.display = 'none';
        
        if (continueFromLast && lastScanDate && !searchQuery) {
            const titleDate = document.getElementById('title-scan-date');
            let dateOnly = lastScanDate;
            if (lastScanDate.includes('T')) {
                dateOnly = lastScanDate.split('T')[0];
            } else if (lastScanDate.includes(' ')) {
                dateOnly = lastScanDate.split(' ')[0];
            }
            if (titleDate) {
                titleDate.innerText = '[' + dateOnly + ']';
            }
        }
        
        updateCounter();
        
        setNavigationDisabled(true);
        statusDiv.innerText = "Connexion...";
        
        let wsUrl = `ws://${window.location.host}/api/scan_stream`;
        const params = [];
        if (activeChannelId) {
            params.push(`channel_id=${activeChannelId}`);
        }
        if (searchQuery) {
            params.push(`search_query=${encodeURIComponent(searchQuery)}`);
            if (continueFromLast) {
                params.push(`skip=${searchSkipCount}`);
            }
        } else {
            currentSearchQuery = null;
            if (continueFromLast && lastScanDate) {
                params.push(`continue_date=${encodeURIComponent(lastScanDate)}`);
                let dateOnly = lastScanDate;
                if (dateOnly.includes('T')) dateOnly = dateOnly.split('T')[0];
                else if (dateOnly.includes(' ')) dateOnly = dateOnly.split(' ')[0];
                updateDateDisplay(dateOnly);
            }
        }
        if (params.length > 0) wsUrl += "?" + params.join('&');
        
        if (currentWebSocket) currentWebSocket.close();
        currentWebSocket = new WebSocket(wsUrl);
        const ws = currentWebSocket;
        
        document.getElementById('btn-scan-stop').style.display = !searchQuery ? 'inline-block' : 'none';
        document.getElementById('btn-search-stop').style.display = searchQuery ? 'inline-block' : 'none';
        
        ws.onmessage = function(event) {
            const msg = JSON.parse(event.data);
            if (msg.type === "info") {
                statusDiv.innerText = msg.message;
            } else if (msg.type === "done") {
                const parts = msg.message.split('parmi ');
                statusDiv.innerText = parts.length > 1 ? "Terminé ! " + parts[1] : msg.message;
                statusDiv.style.color = "#4ade80";
                setNavigationDisabled(false);
                document.getElementById('btn-scan-stop').style.display = 'none';
                document.getElementById('btn-search-stop').style.display = 'none';
                
                if (msg.last_date) {
                    lastScanDate = msg.last_date;
                    if (!searchQuery && activeChannelId) {
                        if (!appConfig.channel_start_dates) appConfig.channel_start_dates = {};
                        appConfig.channel_start_dates[activeChannelId.toString()] = msg.last_date;
                        const ch = channelsList.find(c => c.id === activeChannelId);
                        if (ch) ch.start_date = msg.last_date;
                        updateDateDisplay(msg.last_date);
                        renderSettingsChannelsList();
                    }
                }
                
                if (currentSearchQuery) {
                    document.getElementById('btn-search-next').style.display = 'inline-block';
                } else if (msg.last_date) {
                    document.getElementById('btn-scan-next').style.display = 'inline-block';
                }
                
                applyFilters();
                ws.close();
            } else if (msg.type === "error") {
                statusDiv.innerText = "❌ ERREUR: " + msg.message;
                setNavigationDisabled(false);
            } else if (msg.type === "comic") {
                DATA.push(msg);
                if (currentSearchQuery) searchSkipCount++;
                applyFilters();
            }
        };

        ws.onerror = function(e) {
            statusDiv.innerText = "❌ Erreur WebSocket.";
            setNavigationDisabled(false);
        };
    }

    /* Rendu et filtres */
    let activeFilters = new Set(['ALL']);
    
    function applyFilters() {
      const q = document.getElementById('search').value.toLowerCase();
      const filtered = DATA.filter(d => {
        if (!activeFilters.has('ALL') && !activeFilters.has(d.status)) return false;
        if (q && !d.filename.toLowerCase().includes(q)) return false;
        return true;
      });
      renderGrid(filtered);
    }

    function toggleFilter(f) {
        if (f === 'ALL') {
            activeFilters.clear();
            activeFilters.add('ALL');
        } else {
            activeFilters.delete('ALL');
            if (activeFilters.has(f)) {
                activeFilters.delete(f);
                if (activeFilters.size === 0) activeFilters.add('ALL');
            } else {
                activeFilters.add(f);
            }
        }
        
        document.querySelectorAll('.fb').forEach(b => {
            if (activeFilters.has(b.dataset.f)) b.classList.add('active');
            else b.classList.remove('active');
        });
        applyFilters();
    }
    
    function updateFilterCounts() {
        const counts = {'ALL': DATA.length, 'NOUVEAU': 0, 'INCERTAIN': 0, 'DOUBLON': 0};
        DATA.forEach(d => { if(counts[d.status] !== undefined) counts[d.status]++; });
        document.getElementById('cnt-ALL').innerText = `(${counts['ALL']})`;
        document.getElementById('cnt-NOUVEAU').innerText = `(${counts['NOUVEAU']})`;
        document.getElementById('cnt-INCERTAIN').innerText = `(${counts['INCERTAIN']})`;
        document.getElementById('cnt-DOUBLON').innerText = `(${counts['DOUBLON']})`;
    }

    function renderGrid(items) {
      updateFilterCounts();
      const nr = document.getElementById('no-results');
      if (!items.length) { grid.innerHTML=''; nr.style.display='block'; updateCounter(0); return; }
      nr.style.display = 'none';
      
      grid.innerHTML = items.map(d => {
        const isSel = selected.has(d.message_id);
        const displayName = d.filename.replace(/_/g,' ').replace(/\.(cbz|cbr|pdf)$/i,'');
        const cleanName = displayName;
        const safeOriginal = d.filename.replace(/'/g, "\\'").replace(/"/g, "&quot;");
        const safeClean = cleanName.replace(/'/g, "\\'").replace(/"/g, "&quot;");
        const safeResults = encodeURIComponent(JSON.stringify(d.everything_results||[])).replace(/'/g, "%27");
        const color = COLORS[d.filename.charCodeAt(0) % COLORS.length];
        const isPinned = toReadList.has(d.filename);
        const inQueue = downloadQueue.some(q => q.message_id === d.message_id);
        
        const extMatch = d.filename.match(/\.([a-z0-9]+)$/i);
        const ext = extMatch ? extMatch[1].toUpperCase() : '';
        const titleHtml = `<span style="font-size:9px; background:#334155; padding:2px 4px; border-radius:4px; vertical-align:middle; color:#e2e8f0; font-weight:normal; margin-right:4px;">${ext}</span>${cleanName}`;
        
        const imgH  = d.thumb_url
          ? `<img class="cover" src="${d.thumb_url}" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"><div class="cover" style="display:none;align-items:center;justify-content:center;color:#475569;font-size:3rem;background:linear-gradient(135deg,${color}44,#0f172a)">${d.filename[0].toUpperCase()}</div>`
          : `<div class="cover" style="display:flex;align-items:center;justify-content:center;color:#475569;font-size:3rem;background:linear-gradient(135deg,${color}44,#0f172a)">${d.filename[0].toUpperCase()}</div>`;
          
        const bdtH = (u => u ? `<a class="bdt-link" href="${u}" target="_blank" onclick="event.stopPropagation()" title="BDthèque">📚</a>` : '')(bdtUrl(d.filename));
        
        return `<div class="card${isSel?' selected':''}" data-id="${d.message_id}" data-status="${d.status}" onclick="openImagePreview('${d.thumb_url || ''}', '${safeClean}')" title="Cliquer pour voir la couverture en grand">
          ${imgH}
          ${bdtH}
          
          <div class="checkmark" onclick="event.stopPropagation(); toggleCardSelection(${d.message_id})" title="${isSel ? 'Désélectionner' : 'Sélectionner pour télécharger'}">✓</div>
          <div class="pin-link ${isPinned ? 'pinned' : ''}" id="btn-read-${d.message_id}" onclick="event.stopPropagation(); addToRead(${d.message_id}, '${d.status}', '${safeOriginal}', ${d.channel})" title="${isPinned ? 'Retirer de la pile à lire' : 'Ajouter à la pile à lire'}">📌</div>

          <div class="card-info">
            <div class="card-title" data-fn="${d.filename}" onmouseenter="showTip(this.dataset.fn)" onmouseleave="hideTip()" style="display:flex; align-items:center;">${titleHtml}</div>
            <div class="card-meta">${d.date.split(' ')[0]} · ${(d.file_size/1024/1024).toFixed(1)} Mo</div>
            <div style="display:flex; gap:5px; align-items:center; flex-wrap:wrap; margin-top:2px;">
                <span class="badge ${d.status}" onclick="event.stopPropagation(); openModal(${d.message_id}, '${safeOriginal}', '${safeClean}', '${safeResults}')" title="Cliquez pour voir/modifier la correspondance">${d.status}</span>
                ${isPinned ? `<span class="badge" id="badge-read-${d.message_id}" style="background:#78350f; color:#fde68a; border:1px solid #f59e0b80; cursor:pointer;" onclick="event.stopPropagation(); addToRead(${d.message_id}, '${d.status}', '${safeOriginal}', ${d.channel})" title="Retirer de la pile à lire">📚 Pile à lire</span>` : `<span id="badge-read-${d.message_id}" style="display:none;"></span>`}
                ${inQueue ? '<span class="badge" style="background:#064e3b; color:#10b981; border:1px solid #10b98140; cursor:default;">🛒 À télécharger</span>' : ''}
            </div>
            <div class="progress-container" id="dl-container-${d.message_id}">
                <div class="progress-bar" id="dl-progress-${d.message_id}"></div>
            </div>
            <div class="dl-status" id="dl-status-${d.message_id}"></div>
          </div>
        </div>`;
      }).join('');
      
      let nextCardHtml = '';
      if (currentView === 'scan' && document.getElementById('btn-scan-next').style.display !== 'none' && !currentSearchQuery) {
          nextCardHtml = `
          <div class="card" style="display:flex; flex-direction:column; align-items:center; justify-content:center; background:#0f172a; border:2px dashed #3b82f6; cursor:pointer; min-height: 250px; transition: all 0.2s; box-shadow: none;" onmouseover="this.style.background='#1e293b'; this.style.borderColor='#60a5fa';" onmouseout="this.style.background='#0f172a'; this.style.borderColor='#3b82f6';" onclick="document.getElementById('btn-scan-next').click()">
             <div style="font-size:3rem; margin-bottom:10px;">⏩</div>
             <div style="color:#60a5fa; font-weight:bold; font-size:1.1rem; text-align:center;">Page<br>Suivante</div>
          </div>`;
      } else if (currentView === 'scan' && document.getElementById('btn-search-next').style.display !== 'none' && currentSearchQuery) {
          nextCardHtml = `
          <div class="card" style="display:flex; flex-direction:column; align-items:center; justify-content:center; background:#0f172a; border:2px dashed #8b5cf6; cursor:pointer; min-height: 250px; transition: all 0.2s; box-shadow: none;" onmouseover="this.style.background='#1e293b'; this.style.borderColor='#a78bfa';" onmouseout="this.style.background='#0f172a'; this.style.borderColor='#8b5cf6';" onclick="document.getElementById('btn-search-next').click()">
             <div style="font-size:3rem; margin-bottom:10px;">⏩</div>
             <div style="color:#a78bfa; font-weight:bold; font-size:1.1rem; text-align:center;">Résultats<br>Suivants</div>
          </div>`;
      }
      grid.innerHTML += nextCardHtml;
      
      updateCounter(items.length);
    }
    
    const COLORS = ['#ef4444','#f97316','#eab308','#22c55e','#14b8a6','#3b82f6','#8b5cf6','#ec4899'];

    function selectAllVisible() {
        document.querySelectorAll('.card').forEach(el => {
            if(el.style.display !== 'none' && el.dataset.id) {
                const id = parseInt(el.dataset.id);
                if (!isNaN(id)) {
                    selected.add(id);
                    el.classList.add('selected');
                    const chk = el.querySelector('.checkmark');
                    if (chk) chk.title = 'Désélectionner';
                }
            }
        });
        updateCounter(DATA.length);
    }
    function deselectAll() {
        clearSelection();
        updateCounter(DATA.length);
        renderGrid(DATA);
    }
    
    function toggleCardSelection(id) {
        if (!id) return;
        const card = document.querySelector(`.card[data-id="${id}"]`);
        const chk = card ? card.querySelector('.checkmark') : null;
        if (selected.has(id)) {
            selected.delete(id);
            if (card) card.classList.remove('selected');
            if (chk) chk.title = 'Sélectionner pour télécharger';
            const item = DATA.find(d => d.message_id === id);
            if (item && toReadList.has(item.filename) && !downloadQueue.some(q => q.message_id === id)) {
                toReadList.delete(item.filename);
                const btn = document.getElementById('btn-read-' + id);
                if (btn) btn.classList.remove('pinned');
            }
        } else {
            selected.add(id);
            if (card) card.classList.add('selected');
            if (chk) chk.title = 'Désélectionner';
        }
        updateCounter(DATA.length);
    }
    
    function toggleCard(el) {
        if (!el || !el.dataset.id) return;
        toggleCardSelection(parseInt(el.dataset.id));
    }
    function updateCounter(vis) {
      const v = vis!==undefined ? vis : document.querySelectorAll('.card:not([style*="display: none"])').length;
      const s = selected.size;
      document.getElementById('counter').textContent=`${v} visible / ${s} sélec.`;
      const btn=document.getElementById('export-btn');
      btn.textContent=`📥 Panier (${s})`;
      btn.disabled=s===0;
    }
    
    function updateGlobalDownloadIndicator() {
        let ind = document.getElementById('global-dl-indicator');
        if(activeDownloadsCount > 0) {
            ind.style.display = 'block';
            ind.innerHTML = `<b>⏳ ${activeDownloadsCount} téléchargement(s)</b>`;
        } else {
            ind.style.display = 'none';
        }
    }
    
    function addToQueueFromSelection() {
        const toDownload = DATA.filter(d => selected.has(d.message_id));
        if (toDownload.length === 0) return;
        
        toDownload.forEach(d => {
            if (!downloadQueue.find(q => q.message_id === d.message_id)) {
                downloadQueue.push({
                    message_id: d.message_id,
                    channel: d.channel,
                    filename: d.filename,
                    to_read: toReadList.has(d.filename)
                });
            }
        });
        deselectAll();
        updateQueueIndicator();
        renderGrid(DATA);
    }
    
    function removeFromQueue(msg_id) {
        const qIdx = downloadQueue.findIndex(q => q.message_id === msg_id);
        if (qIdx !== -1) {
            const q = downloadQueue[qIdx];
            if (q.to_read && toReadList.has(q.filename)) {
                toReadList.delete(q.filename);
                const btn = document.getElementById('btn-read-' + msg_id);
                if (btn) btn.classList.remove('pinned');
            }
            downloadQueue.splice(qIdx, 1);
        }
        updateQueueIndicator();
        renderQueueList();
        renderGrid(DATA);
    }
    
    function startQueuedDownloads() {
        if (!dlSocket || dlSocket.readyState !== WebSocket.OPEN) {
            alert("Erreur: WebSocket de téléchargement non connecté.");
            return;
        }
        if (downloadQueue.length === 0) return;
        
        const toProcess = [...downloadQueue];
        downloadQueue = []; // clear queue immediately
        updateQueueIndicator();
        renderGrid(DATA);
        
        activeDownloadsCount += toProcess.length;
        updateGlobalDownloadIndicator();
        
        toProcess.forEach(d => {
            downloadsState[d.message_id] = {filename: d.filename, channel: d.channel, to_read: d.to_read || false, status: 'En file d\'attente...', current:0, total:0};
            dlSocket.send(JSON.stringify({
                action: "download",
                message_id: d.message_id,
                channel: d.channel,
                filename: d.filename,
                to_read: d.to_read || false
            }));
        });
        if(document.getElementById('downloads-modal').style.display === 'flex') {
            renderDownloadsModal();
        }
    }

    function renderQueueList() {
        const list = document.getElementById('queue-list');
        if (!list) return;
        list.innerHTML = '';
        if (downloadQueue.length === 0) {
            list.innerHTML = '<div class="help-text">La liste est vide.</div>';
            return;
        }
        
        downloadQueue.forEach(q => {
            const div = document.createElement('div');
            div.style.cssText = 'background:#0f172a; padding:8px 10px; border-radius:6px; border:1px solid #334155; font-size:12px; display:flex; justify-content:space-between; align-items:center;';
            
            const info = document.createElement('div');
            info.style.flexGrow = '1';
            info.style.whiteSpace = 'nowrap';
            info.style.overflow = 'hidden';
            info.style.textOverflow = 'ellipsis';
            info.innerHTML = `<span style="color:#e2e8f0;">${q.filename}</span>${q.to_read ? ' <span style="font-size:10px; background:#f59e0b; color:white; padding:1px 4px; border-radius:3px;">À lire</span>' : ''}`;
            
            const btn = document.createElement('button');
            btn.className = 'btn';
            btn.style.cssText = 'background:#ef4444; color:white; border:none; margin-left:10px; padding:3px 6px; cursor:pointer; font-size:10px; flex-shrink:0;';
            btn.innerText = '🗑️';
            btn.onclick = () => removeFromQueue(q.message_id);
            
            div.appendChild(info);
            div.appendChild(btn);
            list.appendChild(div);
        });
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
        const item = DATA.find(d => d.message_id === currentModalMsgId);
        if (item) {
            item.status = 'DOUBLON';
            item.everything_results = [result];
        }
        const card = document.querySelector(`.card[data-id="${currentModalMsgId}"]`);
        if(card) {
            card.dataset.status = 'DOUBLON';
            const badge = card.querySelector('.badge');
            if(badge) {
                badge.className = 'badge DOUBLON';
                badge.innerText = 'DOUBLON (Manuel)';
            }
            const btn = document.getElementById('btn-read-' + currentModalMsgId);
            if(btn) {
                btn.style.display = 'flex';
                // Update onclick params
                btn.onclick = (e) => { e.stopPropagation(); addToRead(currentModalMsgId, 'DOUBLON', item.filename, item.channel); };
            }
        }
        closeModal('search-modal');
    }
    function resetManualResult() {
        const card = document.querySelector(`.card[data-id="${currentModalMsgId}"]`);
        if(card) {
            const badge = card.querySelector('.badge');
            if(badge) {
                const origStatus = card.dataset.status;
                badge.className = 'badge ' + origStatus;
                badge.innerText = origStatus;
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

@app.get("/api/channels_list")
async def get_channels_list():
    config_path = os.path.join(PROJECT_DIR, "config.json")
    if not os.path.exists(config_path):
        return {"channels": [], "active_channel": None, "channel_start_dates": {}}
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    channels = config.get("channels", [])
    active_channel = config.get("active_channel", channels[0] if channels else None)
    channel_start_dates = config.get("channel_start_dates", {})
    fallback_start_date = config.get("start_date", "")

    result = []
    dialogs_map = {}
    if telegram_client and telegram_client.is_connected():
        try:
            dialogs = await telegram_client.get_dialogs()
            dialogs_map = {d.entity.id: getattr(d.entity, "title", str(d.entity.id)) for d in dialogs}
        except Exception as e:
            print("Erreur get_dialogs:", e)

    for ch_id in channels:
        name = dialogs_map.get(ch_id)
        if not name:
            try:
                raw_id = int(str(ch_id).replace("-100", ""))
                name = dialogs_map.get(raw_id)
            except Exception:
                pass
        if not name and telegram_client and telegram_client.is_connected():
            try:
                ent = await telegram_client.get_entity(ch_id)
                name = getattr(ent, "title", str(ch_id))
            except Exception:
                name = f"Canal {ch_id}"
        if not name:
            name = f"Canal {ch_id}"
        
        start_d = channel_start_dates.get(str(ch_id), fallback_start_date)
        result.append({
            "id": ch_id,
            "name": name,
            "start_date": start_d,
            "is_active": (ch_id == active_channel)
        })
    
    return {
        "channels": result,
        "active_channel": active_channel,
        "channel_start_dates": channel_start_dates
    }

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
        if "start_date" in data:
            config["start_date"] = data.get("start_date", "")
        if "active_channel" in data:
            config["active_channel"] = data.get("active_channel")
        if "channel_start_dates" in data and isinstance(data["channel_start_dates"], dict):
            config["channel_start_dates"] = data["channel_start_dates"]
        if "filename_filter" in data:
            config["filename_filter"] = data["filename_filter"]
        if "download_concurrency" in data:
            config["download_concurrency"] = data["download_concurrency"]
        if "max_gallery_size" in data:
            config["max_gallery_size"] = data["max_gallery_size"]
        if "fuzzy_threshold_duplicate" in data:
            config["fuzzy_threshold_duplicate"] = data["fuzzy_threshold_duplicate"]
        if "fuzzy_threshold_review" in data:
            config["fuzzy_threshold_review"] = data["fuzzy_threshold_review"]
        if "channels" in data and isinstance(data["channels"], list):
            config["channels"] = data["channels"]
        if "bd_search_paths" in data and isinstance(data["bd_search_paths"], list):
            config["bd_search_paths"] = data["bd_search_paths"]
            
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
        path_parts = " | ".join(f'<"{p}">' for p in search_paths)
        path_filter = f"<{path_parts}> "
        
    final_query = f"{path_filter}{q} {ext_filter}"
    
    url = f"{everything_url}/?search={urllib.parse.quote(final_query)}&json=1&count=50&path_column=1&size_column=1"
    
    try:
        req = urllib.request.urlopen(url, timeout=5)
        data = json.loads(req.read())
        results = data.get('results', [])
        
        scored = []
        for r in results:
            name = r.get('name', '')
            path = r.get('path', '')
            size = r.get('size', '0')
            try:
                size_int = int(size)
            except:
                size_int = 0
            score = fuzzy_score(original, name)
            scored.append({
                'filename': name,
                'path': path,
                'size': size_int,
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

from fastapi.responses import FileResponse
from fastapi import HTTPException

thumb_semaphore = None

async def download_thumb_task(client, photo, path):
    global thumb_semaphore
    if thumb_semaphore is None:
        thumb_semaphore = asyncio.Semaphore(4)
        
    try:
        if not os.path.exists(path):
            tmp_path = path + ".tmp"
            async with thumb_semaphore:
                await client.download_media(photo, file=tmp_path)
            if os.path.exists(tmp_path):
                os.replace(tmp_path, path)
    except Exception as e:
        print("Erreur download thumb:", e)

@app.get("/api/wait_thumb/{message_id}")
async def wait_thumb(message_id: int):
    thumb_path = os.path.join(PROJECT_DIR, "thumbs", f"{message_id}.jpg")
    for _ in range(60): # 30 seconds max
        if os.path.exists(thumb_path):
            return FileResponse(thumb_path)
        await asyncio.sleep(0.5)
    raise HTTPException(status_code=404, detail="Thumbnail timeout")

@app.websocket("/api/scan_stream")
async def scan_stream(websocket: WebSocket, continue_date: str = None, search_query: str = None, skip: int = 0, channel_id: int = None):
    await websocket.accept()
    if not telegram_client:
        await websocket.send_json({"type": "error", "message": "Telegram client non connecté (vérifiez api_id/hash dans config.json)."})
        await websocket.close()
        return

    # Load config
    config_path = os.path.join(PROJECT_DIR, "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    all_channels = config.get("channels", [])
    active_channel = config.get("active_channel", all_channels[0] if all_channels else None)
    channel_start_dates = config.get("channel_start_dates", {})
    
    if channel_id:
        target_channels = [channel_id]
    elif active_channel:
        target_channels = [active_channel]
    else:
        target_channels = all_channels

    everything_url = config.get("everything_api_url", "http://localhost:8070")
    threshold_dup = config.get("fuzzy_threshold_duplicate", 85)
    threshold_rev = config.get("fuzzy_threshold_review", 50)
    filename_filter = config.get("filename_filter", [])
    search_paths = config.get("bd_search_paths", [])
    
    # Limite du nombre de cartes a afficher
    max_cards = config.get("max_gallery_size", config.get("max_downloads_per_run", 50))
    if max_cards == 0:
        max_cards = 9999

    from telegram_scraper import SUPPORTED_EXTENSIONS, _extract_filename_and_ext
    from everything_checker import search_by_keywords
    from fuzzy_matcher import rank_matches
    from datetime import datetime, timezone, timedelta

    try:
        dialogs = await telegram_client.get_dialogs()
        dialog_by_id = {d.entity.id: d for d in dialogs}
        
        total_found = 0
        total_scanned = 0
        global_last_date = None
        
        for channel in target_channels:
            if total_found >= max_cards:
                break
                
            entity = await telegram_client.get_entity(channel)
            channel_name = getattr(entity, "title", str(channel))
            entity_id = entity.id
            
            dialog = dialog_by_id.get(entity_id)
            read_max_id = dialog.dialog.read_inbox_max_id if dialog else 0
            
            await websocket.send_json({"type": "info", "message": f"Scan du channel : {channel_name}..."})
            
            # Calculer la date de départ pour ce canal spécifique
            ch_start_str = channel_start_dates.get(str(channel), config.get("start_date", ""))
            start_date_dt = None
            if ch_start_str:
                try:
                    start_date_dt = datetime.fromisoformat(ch_start_str)
                    if start_date_dt.tzinfo is None:
                        start_date_dt = start_date_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    try:
                        start_date_dt = datetime.strptime(ch_start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    except Exception:
                        pass

            skipped_so_far = 0
            if search_query:
                kwargs = {'search': search_query, 'limit': None}
            else:
                kwargs = {'reverse': True}
                if continue_date:
                    kwargs["offset_date"] = datetime.fromisoformat(continue_date) - timedelta(seconds=2)
                elif start_date_dt:
                    kwargs['offset_date'] = start_date_dt
                else:
                    kwargs['min_id'] = read_max_id
                
            last_photo = None
            
            async for message in telegram_client.iter_messages(entity, **kwargs):
                if message.date:
                    global_last_date = message.date.isoformat()
                if total_found >= max_cards:
                    await websocket.send_json({"type": "info", "message": f"Limite globale de {max_cards} BD atteinte."})
                    break
                
                total_scanned += 1
                if total_scanned % 100 == 0:
                    await websocket.send_json({"type": "info", "message": f"Scan {channel_name} : {total_scanned} messages analysés..."})
                    
                if message.photo:
                    last_photo = message
                    continue
                    
                if message.document:
                    if search_query and skipped_so_far < skip:
                        skipped_so_far += 1
                        continue
                        
                    filename, ext = _extract_filename_and_ext(message)
                    
                    cover = None
                    if last_photo is not None:
                        same_group = (message.grouped_id and message.grouped_id == last_photo.grouped_id)
                        if same_group or (0 <= message.id - last_photo.id <= 5):
                            cover = last_photo
                    
                    if cover is None:
                        try:
                            context_msgs = await telegram_client.get_messages(entity, limit=4, offset_id=message.id, add_offset=-2)
                            for c_msg in context_msgs:
                                if c_msg.photo:
                                    same_group = (message.grouped_id and message.grouped_id == c_msg.grouped_id)
                                    if same_group or abs(message.id - c_msg.id) <= 5:
                                        cover = c_msg
                                        break
                        except Exception:
                            pass
                                    
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
                            asyncio.create_task(download_thumb_task(telegram_client, cover.photo, thumb_path))
                            thumb_url = f"/api/wait_thumb/{message.id}"
                        else:
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
                    
        # Sauvegarde de la progression par canal
        if global_last_date and target_channels and not search_query:
            scanned_ch = target_channels[0]
            if "channel_start_dates" not in config:
                config["channel_start_dates"] = {}
            config["channel_start_dates"][str(scanned_ch)] = global_last_date
            if scanned_ch == active_channel:
                config["start_date"] = global_last_date
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)

        await websocket.send_json({"type": "done", "message": f"Terminé ! {total_found} BD trouvées parmi {total_scanned} messages scannés.", "last_date": global_last_date, "channel_id": target_channels[0] if target_channels else None})
        await websocket.close()
        
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
        await websocket.close()



def trigger_yacreader_update():
    import subprocess
    alire_dir = os.path.join(PROJECT_DIR, "A_lire_yacreader")
    exe_path = r"C:\Program Files\YACReader\YACReaderLibraryServer.exe"
    if os.path.exists(exe_path):
        try:
            subprocess.Popen([exe_path, "update-library", alire_dir], creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            print(f"Erreur update YACReader: {e}")


import shutil

@app.post("/api/add_to_read_local")
async def add_to_read_local(request: Request):
    data = await request.json()
    local_path = data.get("local_path")
    message_id = data.get("message_id")
    filename = data.get("filename")
    
    if not local_path or not os.path.exists(local_path):
        return {"status": "error", "message": "Fichier local introuvable."}
        
    alire_dir = os.path.join(PROJECT_DIR, "A_lire_yacreader")
    os.makedirs(alire_dir, exist_ok=True)
    
    # Copier la BD
    dest_path = os.path.join(alire_dir, filename)
    try:
        shutil.copy2(local_path, dest_path)
    except Exception as e:
        return {"status": "error", "message": str(e)}
        
    # Copier la miniature
    thumb_src = os.path.join(PROJECT_DIR, "thumbs", f"{message_id}.jpg")
    name_no_ext = os.path.splitext(filename)[0]
    thumb_dest = os.path.join(alire_dir, f"{name_no_ext}.jpg")
    
    if os.path.exists(thumb_src):
        try:
            shutil.copy2(thumb_src, thumb_dest)
        except:
            pass
            
    trigger_yacreader_update()
    return {"status": "ok"}

@app.get("/api/list_to_read")
async def list_to_read():
    alire_dir = os.path.join(PROJECT_DIR, "A_lire_yacreader")
    if not os.path.exists(alire_dir):
        return []
        
    files = []
    for f in os.listdir(alire_dir):
        if f.lower().endswith(('.cbz', '.cbr', '.pdf', '.epub', '.rar', '.zip')):
            name_no_ext = os.path.splitext(f)[0]
            thumb_url = ""
            if os.path.exists(os.path.join(alire_dir, f"{name_no_ext}.jpg")):
                thumb_url = f"/alire/{name_no_ext}.jpg"
            files.append({
                "filename": f,
                "thumb_url": thumb_url
            })
    return files

@app.post("/api/remove_to_read")
async def remove_to_read(request: Request):
    data = await request.json()
    filename = data.get("filename")
    if not filename: return {"status": "error"}
    
    alire_dir = os.path.join(PROJECT_DIR, "A_lire_yacreader")
    file_path = os.path.join(alire_dir, filename)
    name_no_ext = os.path.splitext(filename)[0]
    thumb_path = os.path.join(alire_dir, f"{name_no_ext}.jpg")
    
    if os.path.exists(file_path):
        try: os.remove(file_path)
        except: pass
    if os.path.exists(thumb_path):
        try: os.remove(thumb_path)
        except: pass
        
    trigger_yacreader_update()
    return {"status": "ok"}

download_semaphore = None
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
        is_to_read = data.get("to_read", False)
        
        await websocket.send_json({"type": "status", "message_id": msg_id, "status": "En file d'attente..."})
        file_path = None
        
        try:
            async with download_semaphore:
                await websocket.send_json({"type": "status", "message_id": msg_id, "status": "Préparation..."})
                
                entity = await telegram_client.get_entity(channel)
                message = await telegram_client.get_messages(entity, ids=msg_id)
                
                config_path = os.path.join(PROJECT_DIR, "config.json")
                dl_dir = os.path.join(PROJECT_DIR, "downloads")
                if os.path.exists(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        temp_c = json.load(f)
                        if temp_c.get("download_path"):
                            dl_dir = temp_c.get("download_path")
                            
                os.makedirs(dl_dir, exist_ok=True)
                file_path = os.path.join(dl_dir, filename)
                temp_file_path = file_path + ".part"
                
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
                    file=temp_file_path,
                    progress_callback=progress_cb
                )
                
                if os.path.exists(temp_file_path):
                    os.rename(temp_file_path, file_path)
                    
                if is_to_read:
                    alire_dir = os.path.join(PROJECT_DIR, "A_lire_yacreader")
                    os.makedirs(alire_dir, exist_ok=True)
                    try: shutil.copy2(file_path, os.path.join(alire_dir, filename))
                    except: pass
                    
                    thumb_src = os.path.join(PROJECT_DIR, "thumbs", f"{msg_id}.jpg")
                    name_no_ext = os.path.splitext(filename)[0]
                    thumb_dest = os.path.join(alire_dir, f"{name_no_ext}.jpg")
                    if os.path.exists(thumb_src):
                        try: shutil.copy2(thumb_src, thumb_dest)
                        except: pass
                    trigger_yacreader_update()
                    
                await websocket.send_json({"type": "status", "message_id": msg_id, "status": "Terminé ✅"})
        except asyncio.CancelledError:
            await websocket.send_json({"type": "status", "message_id": msg_id, "status": "Annulé ❌"})
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                try: os.remove(temp_file_path)
                except: pass
        except Exception as e:
            await websocket.send_json({"type": "status", "message_id": msg_id, "status": f"Erreur ❌ ({str(e)[:50]})"})
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                try: os.remove(temp_file_path)
                except: pass
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
    except Exception:
        pass

# Sert le dossier thumbs pour la galerie
app.mount("/thumbs", StaticFiles(directory=os.path.join(PROJECT_DIR, "thumbs")), name="thumbs")
os.makedirs(os.path.join(PROJECT_DIR, "A_lire_yacreader"), exist_ok=True)
app.mount("/alire", StaticFiles(directory=os.path.join(PROJECT_DIR, "A_lire_yacreader")), name="alire")


if __name__ == "__main__":
    import uvicorn
    import sys
    import asyncio
    
    # Cleanup .part files on startup
    import json
    dl_dir = os.path.join(PROJECT_DIR, "downloads")
    config_path = os.path.join(PROJECT_DIR, "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                c = json.load(f)
                if c.get("download_path"):
                    dl_dir = c.get("download_path")
        except:
            pass

    dirs_to_clean = [dl_dir]
    for ddir in dirs_to_clean:
        if os.path.exists(ddir):
            for file in os.listdir(ddir):
                if file.endswith(".part"):
                    try:
                        os.remove(os.path.join(ddir, file))
                    except:
                        pass
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    uvicorn.run("web_ui:app", host="127.0.0.1", port=8000, reload=True)
