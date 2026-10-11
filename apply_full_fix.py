import re
import json

with open("web_ui.py", "r", encoding="utf-8") as f:
    content = f.read()

# ==========================================
# 1. HEADER & MODALS HTML
# ==========================================

# Replace the Date block in the header
old_date_html = """              <div style="display:flex; align-items:center; gap:6px; background:#0f172a; padding:3px 8px; border-radius:5px; border:1px solid #334155;">
                  <label for="header-channel-date" style="font-size:12px; color:#94a3b8; font-weight:600; cursor:pointer;" title="Modifier directement la date de départ du canal actif">📅 Date :</label>
                  <span id="header-channel-date-display" onclick="document.getElementById('header-channel-date').showPicker()" style="color:#60a5fa; font-weight:700; cursor:pointer;"></span>
                  <input type="date" id="header-channel-date" onchange="onHeaderDateChange(this.value)" style="visibility:hidden; position:absolute; width:0; height:0;" title="Date de départ">
              </div>"""

new_date_html = """              <div style="display:flex; align-items:center; gap:6px; background:#0f172a; padding:4px 10px; border-radius:5px; border:1px solid #334155; cursor:pointer;" onclick="openHeaderDatePicker()" title="Cliquer pour changer la date de départ du scan chronologique">
                  <span style="font-size:12px; color:#94a3b8; font-weight:600;">📅 Date :</span>
                  <span id="header-channel-date-display" style="color:#60a5fa; font-weight:700; font-size:13px; text-decoration:underline dotted #60a5fa80;">--/--/----</span>
                  <input type="date" id="header-channel-date" onchange="onHeaderDateChange(this.value); updateDateDisplay(this.value);" style="position:absolute; opacity:0; width:1px; height:1px; pointer-events:none;">
              </div>"""

if old_date_html in content:
    content = content.replace(old_date_html, new_date_html)
else:
    # Use regex fallback if whitespace differed
    content = re.sub(
        r'<div style="[^"]*background:#0f172a[^"]*">\s*<label for="header-channel-date".*?<input type="date" id="header-channel-date"[^>]*>\s*</div>',
        new_date_html,
        content,
        flags=re.DOTALL
    )

# Add "Séries exclues" button in Header actions
old_actions = """      <div class="actions">
        <button class="btn" onclick="document.getElementById('settings-modal').style.display='flex'; renderSettingsChannelsList();">⚙️ Config & Canaux</button>
      </div>"""

new_actions = """      <div class="actions" style="display:flex; gap:10px; align-items:center;">
        <button class="btn" style="background:#1e293b; color:#f87171; border:1px solid #ef444460; display:flex; align-items:center; gap:6px; padding:6px 12px;" onclick="openExclusionsModal()" title="Voir et gérer la liste des séries ignorées">🚫 Séries exclues (<span id="header-exclusions-count">0</span>)</button>
        <button class="btn" onclick="document.getElementById('settings-modal').style.display='flex'; renderSettingsChannelsList();">⚙️ Config & Canaux</button>
      </div>"""

content = content.replace(old_actions, new_actions)

# Add Exclusions Modal HTML before closing </body> or after search-modal
exclusions_modal_html = """
<!-- Modal Séries Exclues (Liste Noire) -->
<div class="modal-overlay" id="exclusions-modal" onclick="closeModal('exclusions-modal')">
    <div class="modal-content" onclick="event.stopPropagation()" style="max-width:650px;">
        <div class="modal-hdr">
            <h2 style="color:#ef4444; margin:0; display:flex; align-items:center; gap:8px;">🚫 Séries et BD exclues des scans</h2>
            <button class="modal-close" onclick="closeModal('exclusions-modal')">&times;</button>
        </div>
        <p style="color:#94a3b8; font-size:13px; margin: 8px 0 15px;">
            Ces séries ou mots-clés sont automatiquement ignorés lors des scans Telegram pour ne plus polluer l'affichage.
        </p>
        
        <div style="display:flex; gap:8px; margin-bottom:15px;">
            <input type="text" id="new-exclusion-input" placeholder="Ajouter une série à exclure (ex: Mister No, Bleck, Akim)..." style="flex:1; padding:8px 12px; border-radius:6px; border:1px solid #475569; background:#0f172a; color:white; font-size:13px;" onkeydown="if(event.key==='Enter') addExclusionKeyword()">
            <button class="btn" onclick="addExclusionKeyword()" style="background:#ef4444; color:white; border:none; padding:8px 16px; font-weight:600; cursor:pointer;">➕ Ajouter</button>
        </div>
        
        <div style="font-size:12px; color:#64748b; margin-bottom:6px; font-weight:600; text-transform:uppercase;">Liste des exclusions actives :</div>
        <div id="exclusions-list" style="display:flex; flex-wrap:wrap; gap:8px; max-height:280px; overflow-y:auto; padding:12px; background:#0f172a; border-radius:6px; border:1px solid #334155; min-height:100px; align-content:flex-start;">
            <!-- Badges dynamiques des mots-clés -->
        </div>
    </div>
</div>
"""

if 'id="exclusions-modal"' not in content:
    content = content.replace('<!-- Modal Downloads -->', exclusions_modal_html + '\n<!-- Modal Downloads -->')

# Update Downloads Modal with Global ETA Banner and Pause All button
old_dl_header = """                    <h3 style="font-size:14px; color:#38bdf8; margin:0;">⏳ En cours / Terminés <span id="dl-speed" style="font-size:0.8rem; color:#94a3b8; font-weight:normal;"></span></h3>
                    <button class="btn" style="background:#ef4444; color:white; border:none; padding:4px 8px;" onclick="cancelAllDownloads()">Annuler actifs</button>"""

new_dl_header = """                    <h3 style="font-size:14px; color:#38bdf8; margin:0;">⏳ En cours / Terminés <span id="dl-speed" style="font-size:0.8rem; color:#94a3b8; font-weight:normal;"></span></h3>
                    <div style="display:flex; gap:6px;">
                        <button id="btn-pause-all-dl" class="btn" style="background:#f59e0b; color:white; border:none; padding:4px 8px; font-size:11px;" onclick="toggleAllDownloadsPause()">⏸️ Tout suspendre</button>
                        <button class="btn" style="background:#ef4444; color:white; border:none; padding:4px 8px; font-size:11px;" onclick="cancelAllDownloads()">Annuler actifs</button>
                    </div>"""

content = content.replace(old_dl_header, new_dl_header)

old_dl_list_container = """                <div id="downloads-list" style="flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:8px;">"""
new_dl_list_container = """                <div id="dl-global-eta-banner" style="display:none; background:#0f172a; padding:6px 10px; border-radius:5px; border:1px solid #334155; font-size:12px; color:#38bdf8; margin-bottom:8px;">
                    ⏱️ <span id="dl-global-eta-text">Calcul du temps restant...</span>
                </div>
                <div id="downloads-list" style="flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:8px;">"""

if 'id="dl-global-eta-banner"' not in content:
    content = content.replace(old_dl_list_container, new_dl_list_container)


# ==========================================
# 2. JAVASCRIPT LOGIC
# ==========================================

# Replace formatFr and updateDateDisplay
old_date_fns = """    function formatFr(dateStr) {
        if(!dateStr) return "";
        let d = dateStr.split('T')[0].split(' ')[0];
        let parts = d.split('-');
        if(parts.length===3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
        return d;
    }

    function updateDateDisplay(dateStr) {
        let clean = dateStr || "";
        if (clean.includes('T')) clean = clean.split('T')[0];
        else if (clean.includes(' ')) clean = clean.split(' ')[0];
        
        const hDate = document.getElementById('header-channel-date');
        const titleDate = document.getElementById('title-scan-date');
        if (hDate && hDate.value !== clean) hDate.value = clean;
        if (titleDate) titleDate.innerText = clean ? `[${clean}]` : '';
    }"""

new_date_fns = """    function formatFr(dateStr) {
        if(!dateStr) return "";
        let clean = dateStr;
        if (clean.includes('T')) clean = clean.split('T')[0];
        else if (clean.includes(' ')) clean = clean.split(' ')[0];
        const parts = clean.split('-');
        if(parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
        return clean;
    }

    function openHeaderDatePicker() {
        const inp = document.getElementById('header-channel-date');
        if (!inp) return;
        if (inp.showPicker) {
            try { inp.showPicker(); return; } catch(e) {}
        }
        inp.style.opacity = '1';
        inp.style.position = 'static';
        inp.style.width = 'auto';
        inp.style.height = 'auto';
        inp.focus();
    }

    function updateDateDisplay(dateStr) {
        let clean = dateStr || "";
        if (clean.includes('T')) clean = clean.split('T')[0];
        else if (clean.includes(' ')) clean = clean.split(' ')[0];
        
        const hDate = document.getElementById('header-channel-date');
        const disp = document.getElementById('header-channel-date-display');
        const titleDate = document.getElementById('title-scan-date');
        
        if (hDate && hDate.value !== clean) hDate.value = clean;
        if (disp) disp.innerText = clean ? formatFr(clean) : '--/--/----';
        if (titleDate) titleDate.innerText = clean ? `[${formatFr(clean)}]` : '';
    }"""

content = content.replace(old_date_fns, new_date_fns)

# Add Exclusions Management functions in JS
js_exclusions_code = """
    function openExclusionsModal() {
        document.getElementById('exclusions-modal').style.display = 'flex';
        renderExclusionsModal();
    }
    
    function updateExclusionsCount() {
        fetch('/api/config').then(r=>r.json()).then(c => {
            const arr = c.exclude_keywords || [];
            const cnt = document.getElementById('header-exclusions-count');
            if(cnt) cnt.innerText = arr.length;
        }).catch(()=>{});
    }

    function renderExclusionsModal() {
        fetch('/api/config').then(r=>r.json()).then(c => {
            const arr = c.exclude_keywords || [];
            const cnt = document.getElementById('header-exclusions-count');
            if(cnt) cnt.innerText = arr.length;
            const list = document.getElementById('exclusions-list');
            if(!list) return;
            if(arr.length === 0) {
                list.innerHTML = '<div class="help-text" style="padding:15px; text-align:center; width:100%;">Aucune série exclue pour le moment. Vous pouvez en ajouter avec le champ ci-dessus ou en cliquant sur 🚫 sur une BD.</div>';
                return;
            }
            list.innerHTML = arr.map(kw => {
                const safeKw = kw.replace(/'/g, "\\\\'");
                return `<div style="display:inline-flex; align-items:center; gap:8px; background:#1e293b; border:1px solid #ef444460; padding:6px 12px; border-radius:20px; font-size:13px; color:#f1f5f9;">
                    <span>${kw}</span>
                    <button onclick="removeExclusionKeyword('${safeKw}')" style="background:#ef4444; color:white; border:none; border-radius:50%; width:18px; height:18px; display:inline-flex; align-items:center; justify-content:center; cursor:pointer; font-size:11px; padding:0;" title="Supprimer de la liste noire">✕</button>
                </div>`;
            }).join('');
        });
    }

    function addExclusionKeyword() {
        const inp = document.getElementById('new-exclusion-input');
        if(!inp) return;
        const val = inp.value.trim();
        if(!val) return;
        fetch('/api/config').then(r=>r.json()).then(c => {
            const arr = c.exclude_keywords || [];
            if(!arr.some(k => k.toLowerCase() === val.toLowerCase())) {
                arr.push(val);
                return fetch('/api/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({exclude_keywords: arr})
                });
            }
        }).then(() => {
            inp.value = '';
            renderExclusionsModal();
            filterGridByExclusions(val);
        });
    }

    function removeExclusionKeyword(keyword) {
        fetch('/api/config').then(r=>r.json()).then(c => {
            let arr = c.exclude_keywords || [];
            arr = arr.filter(k => k.toLowerCase() !== keyword.toLowerCase());
            return fetch('/api/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({exclude_keywords: arr})
            });
        }).then(() => {
            renderExclusionsModal();
        });
    }
    
    function filterGridByExclusions(keyword) {
        if (!keyword) return;
        const kwLower = keyword.toLowerCase();
        for (let i = DATA.length - 1; i >= 0; i--) {
            if (DATA[i].filename.toLowerCase().includes(kwLower)) {
                DATA.splice(i, 1);
            }
        }
        applyFilters();
    }

    function excludeBD(msg_id, original_name) {
        let defaultVal = original_name.replace(/\\.[^/.]+$/, "");
        // Clean common tags
        defaultVal = defaultVal.replace(/@\\S+/g, '').replace(/\\(\\d{4}\\)/g, '').replace(/\\[.*?\\]/g, '').trim();
        const val = prompt("Série ou mot-clé à exclure définitivement des scans :", defaultVal);
        if(val && val.trim() !== "") {
            const term = val.trim();
            fetch('/api/config').then(r=>r.json()).then(c => {
                const arr = c.exclude_keywords || [];
                if(!arr.some(k => k.toLowerCase() === term.toLowerCase())) {
                    arr.push(term);
                    return fetch('/api/config', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({exclude_keywords: arr})
                    });
                }
            }).then(() => {
                filterGridByExclusions(term);
                updateExclusionsCount();
            });
        }
    }
"""

if 'function openExclusionsModal' not in content:
    content = content.replace('function toggleFilter(f) {', js_exclusions_code + '\n    function toggleFilter(f) {')

# Fix card-meta date display
content = re.sub(
    r'<div class="card-meta">\$\{d\.date\.split\(\' \'\)\[0\]\}',
    '<div class="card-meta">${formatFr(d.date.split(\' \')[0])}',
    content
)

# Downloads Pause, Resume, and Global ETA in JS
js_dl_enhancements = """
    let currentMeasuredSpeed = 500 * 1024;
    let isAllDownloadsPaused = false;

    function formatDuration(sec) {
        if (sec <= 0 || isNaN(sec)) return "quelques secondes";
        const m = Math.floor(sec / 60);
        const s = Math.floor(sec % 60);
        if (m === 0) return `${s}s`;
        if (m >= 60) {
            const h = Math.floor(m / 60);
            const remM = m % 60;
            return `${h}h ${remM}m`;
        }
        return `${m}m ${s < 10 ? '0' : ''}${s}s`;
    }

    function updateGlobalETA() {
        let totalRemainingBytes = 0;
        let activeOrQueuedCount = 0;
        
        Object.keys(downloadsState).forEach(id => {
            const d = downloadsState[id];
            if (d && !d.status.includes('✅') && !d.status.startsWith('Annulé') && !d.status.startsWith('Erreur')) {
                activeOrQueuedCount++;
                if (d.total && d.total > 0) {
                    totalRemainingBytes += Math.max(0, d.total - d.current);
                } else {
                    totalRemainingBytes += 50 * 1024 * 1024;
                }
            }
        });
        
        downloadQueue.forEach(q => {
            activeOrQueuedCount++;
            const item = DATA.find(d => d.message_id === q.message_id);
            if (item && item.file_size) totalRemainingBytes += item.file_size;
            else totalRemainingBytes += 50 * 1024 * 1024;
        });
        
        const banner = document.getElementById('dl-global-eta-banner');
        const textEl = document.getElementById('dl-global-eta-text');
        if (!banner || !textEl) return;
        
        if (activeOrQueuedCount === 0 || totalRemainingBytes === 0) {
            banner.style.display = 'none';
            return;
        }
        
        banner.style.display = 'block';
        const speed = (currentMeasuredSpeed > 50000) ? currentMeasuredSpeed : (500 * 1024);
        const totalSec = totalRemainingBytes / speed;
        const remMo = (totalRemainingBytes / 1024 / 1024).toFixed(1);
        
        textEl.innerHTML = `Temps restant estimé : <strong>~${formatDuration(totalSec)}</strong> (${remMo} Mo restants sur ${activeOrQueuedCount} fichier(s) à ~${(speed/1024).toFixed(0)} Ko/s)`;
    }

    function toggleAllDownloadsPause() {
        isAllDownloadsPaused = !isAllDownloadsPaused;
        const btn = document.getElementById('btn-pause-all-dl');
        if (btn) {
            btn.innerText = isAllDownloadsPaused ? '▶️ Tout reprendre' : '⏸️ Tout suspendre';
            btn.style.background = isAllDownloadsPaused ? '#0284c7' : '#f59e0b';
        }
        if (dlSocket && dlSocket.readyState === WebSocket.OPEN) {
            dlSocket.send(JSON.stringify({
                action: isAllDownloadsPaused ? "pause_all" : "resume_all"
            }));
        }
        Object.keys(downloadsState).forEach(id => {
            const d = downloadsState[id];
            if (d && !d.status.includes('✅') && !d.status.startsWith('Annulé') && !d.status.startsWith('Erreur')) {
                d.status = isAllDownloadsPaused ? 'En pause ⏸️' : 'Téléchargement...';
            }
        });
        renderDownloadsModal();
    }
    
    function pauseDownload(id) {
        if (downloadsState[id]) {
            downloadsState[id].status = 'En pause ⏸️';
        }
        if (dlSocket && dlSocket.readyState === WebSocket.OPEN) {
            dlSocket.send(JSON.stringify({
                action: "pause_one",
                message_id: parseInt(id)
            }));
        }
        renderDownloadsModal();
    }
    
    function resumeDownload(id) {
        if (downloadsState[id]) {
            downloadsState[id].status = 'Téléchargement...';
        }
        if (dlSocket && dlSocket.readyState === WebSocket.OPEN) {
            dlSocket.send(JSON.stringify({
                action: "resume_one",
                message_id: parseInt(id)
            }));
        }
        renderDownloadsModal();
    }
"""

if 'function toggleAllDownloadsPause' not in content:
    content = content.replace('function cancelAllDownloads() {', js_dl_enhancements + '\n    function cancelAllDownloads() {')

# Replace renderDownloadsModal with pause/resume button and individual ETA
old_render_modal_body = """        keys.forEach(id => {
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
        });"""

new_render_modal_body = """        updateGlobalETA();
        keys.forEach(id => {
            const d = downloadsState[id];
            const div = document.createElement('div');
            div.style.cssText = 'background:#0f172a; padding:10px; border-radius:6px; border:1px solid #334155; font-size:12px; display:flex; justify-content:space-between; align-items:center;';
            
            const isPaused = d.status.includes('pause');
            const isFinished = d.status.includes('✅');
            const isCancelled = d.status.startsWith('Annulé');
            const isError = d.status.startsWith('Erreur');
            const isActive = !isFinished && !isCancelled && !isError;
            
            let progText = '';
            let progWidth = '0%';
            let etaSingle = '';
            if(d.total) {
                progText = `${(d.current/1024/1024).toFixed(1)} / ${(d.total/1024/1024).toFixed(1)} Mo`;
                progWidth = `${(d.current/d.total)*100}%`;
                if (isActive && !isPaused && d.current > 0) {
                    const remBytes = d.total - d.current;
                    const sec = remBytes / (currentMeasuredSpeed > 50000 ? currentMeasuredSpeed : 500 * 1024);
                    etaSingle = ` (reste ~${formatDuration(sec)})`;
                }
            }
            
            const info = document.createElement('div');
            info.style.flexGrow = '1';
            info.innerHTML = `
                <div style="font-weight:bold; margin-bottom:4px; color:#e2e8f0;">${d.filename}</div>
                <div style="color:${isError ? '#ef4444' : isPaused ? '#f59e0b' : '#94a3b8'}; font-size:11px;">
                    Statut : <span style="color:${isError ? '#ef4444' : isPaused ? '#f59e0b' : '#38bdf8'}; font-weight:600;">${d.status}</span> ${progText}${etaSingle}
                </div>
                <div style="width:100%; background:#1e293b; height:4px; border-radius:2px; margin-top:4px;">
                    <div style="width:${progWidth}; background:${isError ? '#ef4444' : isPaused ? '#f59e0b' : '#38bdf8'}; height:100%; border-radius:2px; transition:width 0.2s;"></div>
                </div>
            `;
            
            const btnWrap = document.createElement('div');
            btnWrap.style.display = 'flex';
            btnWrap.style.gap = '5px';
            btnWrap.style.marginLeft = '15px';

            if (isActive) {
                if (isPaused) {
                    const btnResume = document.createElement('button');
                    btnResume.className = 'btn';
                    btnResume.style.cssText = 'background:#0284c7; color:white; border:none; padding:4px 8px; cursor:pointer; font-size:11px;';
                    btnResume.innerText = '▶️';
                    btnResume.title = 'Reprendre ce téléchargement';
                    btnResume.onclick = () => resumeDownload(id);
                    btnWrap.appendChild(btnResume);
                } else {
                    const btnPause = document.createElement('button');
                    btnPause.className = 'btn';
                    btnPause.style.cssText = 'background:#f59e0b; color:white; border:none; padding:4px 8px; cursor:pointer; font-size:11px;';
                    btnPause.innerText = '⏸️';
                    btnPause.title = 'Mettre en pause';
                    btnPause.onclick = () => pauseDownload(id);
                    btnWrap.appendChild(btnPause);
                }
            }

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
        });"""

content = content.replace(old_render_modal_body, new_render_modal_body)

# Update dlSocket.onmessage progress handler to compute speed and update ETA
old_progress_handler = """            } else if (msg.type === "progress") {
                const d = downloadsState[msg.message_id];
                if (d) {
                    if (!d.startTime) d.startTime = Date.now();
                    d.current = msg.current;
                    d.total = msg.total;
                    
                    const bar = document.getElementById(`dl-progress-${msg.message_id}`);
                    const container = document.getElementById(`dl-container-${msg.message_id}`);
                    const statusEl = document.getElementById(`dl-status-${msg.message_id}`);
                    if (bar && container) {
                        container.style.display = 'block';
                        const percent = (msg.current / msg.total) * 100;
                        bar.style.width = percent + '%';
                        if (statusEl) {
                            let etaText = '';
                            const elapsedSec = (Date.now() - d.startTime) / 1000;
                            const speed = msg.current / elapsedSec;
                            if (speed > 0) {
                                const rem = (msg.total - msg.current) / speed;
                                if (rem > 0 && rem < 36000) {
                                    const m = Math.floor(rem / 60);
                                    const s = Math.floor(rem % 60);
                                    etaText = ` - reste ${m}m${s}s (${(speed/1024/1024).toFixed(1)} Mo/s)`;
                                }
                            }
                            statusEl.innerText = `${(msg.current/1024/1024).toFixed(1)} / ${(msg.total/1024/1024).toFixed(1)} Mo` + etaText;
                            statusEl.style.display = 'block';
                        }
                    }
                }
                if(document.getElementById('downloads-modal').style.display === 'flex') renderDownloadsModal();
            }"""

new_progress_handler = """            } else if (msg.type === "progress") {
                const d = downloadsState[msg.message_id];
                if (d) {
                    if (!d.startTime) d.startTime = Date.now();
                    d.current = msg.current;
                    d.total = msg.total;
                    
                    const elapsedSec = (Date.now() - d.startTime) / 1000;
                    if (elapsedSec > 1 && d.current > 0) {
                        currentMeasuredSpeed = d.current / elapsedSec;
                        const spEl = document.getElementById('dl-speed');
                        if (spEl) spEl.innerText = `(${(currentMeasuredSpeed/1024).toFixed(0)} Ko/s)`;
                    }
                    
                    const bar = document.getElementById(`dl-progress-${msg.message_id}`);
                    const container = document.getElementById(`dl-container-${msg.message_id}`);
                    const statusEl = document.getElementById(`dl-status-${msg.message_id}`);
                    if (bar && container) {
                        container.style.display = 'block';
                        const percent = (msg.current / msg.total) * 100;
                        bar.style.width = percent + '%';
                        if (statusEl) {
                            let etaText = '';
                            if (currentMeasuredSpeed > 0) {
                                const rem = (msg.total - msg.current) / currentMeasuredSpeed;
                                etaText = ` - reste ~${formatDuration(rem)}`;
                            }
                            statusEl.innerText = `${(msg.current/1024/1024).toFixed(1)} / ${(msg.total/1024/1024).toFixed(1)} Mo${etaText}`;
                            statusEl.style.display = 'block';
                        }
                    }
                }
                updateGlobalETA();
                if(document.getElementById('downloads-modal').style.display === 'flex') renderDownloadsModal();
            }"""

content = content.replace(old_progress_handler, new_progress_handler)

# Add updateExclusionsCount() call on init
content = content.replace('initDownloadSocket();', 'initDownloadSocket();\n    updateExclusionsCount();')

# ==========================================
# 3. PYTHON BACKEND (downloads_ws)
# ==========================================

old_backend_ws = """is_download_paused = False

@app.websocket("/api/downloads_ws")
async def downloads_ws(websocket: WebSocket):
    global is_download_paused

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

                while is_download_paused:
                    await asyncio.sleep(1)
                    
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
            if data.get("action") == "pause_queue":
                is_download_paused = data.get("pause", False)
            elif data.get("action") == "download":
                task = asyncio.create_task(download_task(data))
                active_download_tasks[data["message_id"]] = task
            elif data.get("action") == "cancel":
                msg_id = data.get("message_id")
                if msg_id in active_download_tasks:
                    active_download_tasks[msg_id].cancel()
    except Exception:
        pass"""

new_backend_ws = """is_download_paused = False
paused_tasks = {}

@app.websocket("/api/downloads_ws")
async def downloads_ws(websocket: WebSocket):
    global is_download_paused, paused_tasks

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
                while is_download_paused or paused_tasks.get(msg_id, False):
                    await asyncio.sleep(0.5)
                    
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
                
                paused_status_sent = False
                async def progress_cb(current, total):
                    nonlocal paused_status_sent
                    while is_download_paused or paused_tasks.get(msg_id, False):
                        if not paused_status_sent:
                            paused_status_sent = True
                            await websocket.send_json({"type": "status", "message_id": msg_id, "status": "En pause ⏸️"})
                        await asyncio.sleep(0.5)
                        
                    if paused_status_sent:
                        paused_status_sent = False
                        await websocket.send_json({"type": "status", "message_id": msg_id, "status": "Téléchargement..."})
                        
                    await websocket.send_json({
                        "type": "progress",
                        "message_id": msg_id,
                        "current": current,
                        "total": total
                    })
                
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
            paused_tasks.pop(msg_id, None)

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            if action == "pause_all":
                is_download_paused = True
            elif action == "resume_all":
                is_download_paused = False
                paused_tasks.clear()
            elif action == "pause_one":
                mid = data.get("message_id")
                if mid:
                    paused_tasks[mid] = True
            elif action == "resume_one":
                mid = data.get("message_id")
                if mid:
                    paused_tasks.pop(mid, None)
            elif action == "download":
                task = asyncio.create_task(download_task(data))
                active_download_tasks[data["message_id"]] = task
            elif action == "cancel":
                msg_id = data.get("message_id")
                paused_tasks.pop(msg_id, None)
                if msg_id in active_download_tasks:
                    active_download_tasks[msg_id].cancel()
    except Exception:
        pass"""

content = content.replace(old_backend_ws, new_backend_ws)

with open("web_ui.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Full fix successfully applied!")
