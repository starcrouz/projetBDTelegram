"""
gallery_generator.py — Galerie visuelle de selection des BD
"""
import os
import json
import asyncio
from datetime import datetime

from logger import log_info, log_success, log_skip

THUMBS_DIR = "thumbs"
SUPPORTED_EXTENSIONS = {".pdf", ".cbr", ".cbz"}
MIME_TO_EXT = {
    "application/pdf": ".pdf", "application/x-cbr": ".cbr",
    "application/x-cbz": ".cbz", "application/zip": ".cbz",
    "application/x-zip-compressed": ".cbz",
    "application/x-rar-compressed": ".cbr", "application/vnd.rar": ".cbr",
    "application/vnd.comicbook+zip": ".cbz", "application/vnd.comicbook-rar": ".cbr",
}


async def scan_gallery_files(client, entity, channel_id, channel_name,
                              read_max_id, filename_filter=None, limit=None):
    """
    Parcourt oldest-first, associe photos aux documents, s'arrete a `limit` fichiers.
    Retourne (files, max_message_id_scanne).
    """
    files = []
    last_photo   = None
    max_scanned  = 0  # ID le plus haut vu dans ce scan

    async for message in client.iter_messages(entity, min_id=read_max_id, reverse=True):
        max_scanned = max(max_scanned, message.id)

        if message.photo:
            last_photo = message
            continue

        if message.document:
            filename, ext = _extract_filename_and_ext(message)

            cover = None
            if last_photo is not None:
                same_group = (message.grouped_id and
                              message.grouped_id == last_photo.grouped_id)
                if same_group or (0 <= message.id - last_photo.id <= 5):
                    cover = last_photo
            last_photo = None

            if ext not in SUPPORTED_EXTENSIONS:
                continue
            if filename_filter:
                if not any(t.lower() in filename.lower() for t in filename_filter):
                    continue

            files.append({
                "filename":      filename,
                "file_size":     message.document.size,
                "message_id":    message.id,
                "channel":       channel_id,
                "channel_name":  channel_name,
                "message":       message,
                "cover_message": cover,
                "date":          message.date,
            })
            if limit and len(files) >= limit:
                break

    return files, max_scanned


def _extract_filename_and_ext(message):
    for attr in message.document.attributes:
        if hasattr(attr, "file_name") and attr.file_name:
            fn = attr.file_name.strip()
            return fn, os.path.splitext(fn)[1].lower()
    mime = getattr(message.document, "mime_type", "") or ""
    ext  = MIME_TO_EXT.get(mime, "")
    return (f"telegram_msg_{message.id}{ext}", ext) if ext else (f"telegram_msg_{message.id}", "")


async def download_all_covers(client, candidates, concurrency=5):
    os.makedirs(THUMBS_DIR, exist_ok=True)
    sem       = asyncio.Semaphore(concurrency)
    thumb_map = {}

    async def dl_one(f):
        mid        = f["message_id"]
        cover_msg  = f.get("cover_message")
        thumb_path = os.path.join(THUMBS_DIR, f"thumb_{mid}.jpg")
        if os.path.exists(thumb_path):
            thumb_map[mid] = thumb_path; return
        if cover_msg is None:
            thumb_map[mid] = None; return
        async with sem:
            try:
                await client.download_media(cover_msg, file=thumb_path)
                thumb_map[mid] = thumb_path if os.path.exists(thumb_path) else None
            except Exception:
                thumb_map[mid] = None

    has_cover = sum(1 for f in candidates if f.get("cover_message"))
    log_info(f"Telechargement de {has_cover} couvertures...")
    await asyncio.gather(*[dl_one(f) for f in candidates])
    downloaded = sum(1 for v in thumb_map.values() if v)
    log_success(f"Couvertures : {downloaded}/{has_cover} telechargees")
    return thumb_map


def generate_gallery_html(candidates, doublons_list, thumb_map,
                           output_path, project_dir, scan_boundary=None):
    """
    Genere gallery.html.
    scan_boundary : {str(channel_id): max_message_id} pour marquer comme lu.
    """
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Periode couverte
    dates = [f["date"] for f in candidates if f.get("date")]
    date_min = min(dates).strftime("%d/%m/%Y") if dates else "?"
    date_max = max(dates).strftime("%d/%m/%Y") if dates else "?"

    nb_new = sum(1 for c in candidates if c.get("recommendation") == "NOUVEAU")
    nb_inc = sum(1 for c in candidates if c.get("recommendation") == "INCERTAIN")
    nb_dup = len(doublons_list)

    doublons_json  = json.dumps([
        {"filename": d["filename"], "match": d["match"],
         "score": d["score"], "size_mb": d["size_mb"], "channel_name": d["channel_name"]}
        for d in doublons_list
    ], ensure_ascii=False)

    boundary_json = json.dumps(scan_boundary or {})

    cards_data = []
    for f in candidates:
        mid       = f["message_id"]
        thumb     = thumb_map.get(mid)
        thumb_rel = thumb.replace("\\", "/") if thumb else None
        cards_data.append({
            "channel":        f["channel"],
            "message_id":     mid,
            "filename":       f["filename"],
            "channel_name":   f["channel_name"],
            "date":           f["date"].strftime("%d/%m/%Y"),
            "size_mb":        round(f["file_size"] / 1024 / 1024, 1),
            "recommendation": f.get("recommendation", "NOUVEAU"),
            "thumb":          thumb_rel,
            "top_match":      f["matches"][0]["filename"] if f.get("matches") else "",
            "top_score":      f["matches"][0]["score"]    if f.get("matches") else 0,
        })

    cards_json  = json.dumps(cards_data, ensure_ascii=False)
    project_esc = project_dir.replace("\\", "\\\\")
    dup_btn     = (f'<button class="btn btn-dup" onclick="openDupModal()">'
                   f'Doublons ({nb_dup})</button>') if nb_dup > 0 else ""

    # Bloc JS extrait hors f-string pour eviter les SyntaxWarning sur les \. \s \d \b
    extract_title_js = (
        "function extractTitle(filename) {\n"
        "  let n = filename.replace(/\\.(cbz|cbr|pdf)$/i,'').replace(/_/g,' ');\n"
        "  n = n.replace(/\\s*(T\\d+|Tome\\s*\\d+|\\bOS\\b|\\bHS\\b|\\bO\\.?S\\.?\\b|\\(|\\s-\\s|\\d{4}).*$/i,'');\n"
        "  return n.trim();\n"
        "}\n"
        "function bdtUrl(filename) {\n"
        "  var title = extractTitle(filename);\n"
        "  return 'https://www.google.com/search?q=site%3Abedetheque.com+' + encodeURIComponent(title) + '&btnI=1';\n"
        "}"
    )

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BD Telegram — Galerie</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{--card-w:180px}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}}
header{{position:sticky;top:0;z-index:50;background:#0f172aee;backdrop-filter:blur(8px);
  border-bottom:1px solid #1e293b;padding:10px 16px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}}
h1{{font-size:1.15rem;color:#60a5fa;flex:0 0 auto;white-space:nowrap}}
.pills{{display:flex;gap:6px;flex-wrap:wrap}}
.pill{{background:#1e293b;border-radius:20px;padding:3px 11px;font-size:0.7rem;white-space:nowrap}}
.pill b{{font-weight:700}}
.pill.green b{{color:#22c55e}} .pill.yellow b{{color:#f59e0b}}
.pill.red b{{color:#ef4444}} .pill.blue b{{color:#60a5fa}}
.filters{{display:flex;gap:5px}}
.fb{{background:#1e293b;border:1px solid #334155;color:#94a3b8;padding:4px 11px;
  border-radius:20px;cursor:pointer;font-size:0.75rem;transition:all .2s}}
.fb.active{{background:#3b82f6;border-color:#3b82f6;color:#fff}}
.search-wrap{{flex:1;min-width:140px;max-width:240px}}
#search{{width:100%;background:#1e293b;border:1px solid #334155;color:#e2e8f0;
  padding:5px 12px;border-radius:20px;font-size:0.8rem;outline:none}}
#search:focus{{border-color:#3b82f6}}
.zoom-wrap{{display:flex;align-items:center;gap:5px;font-size:0.72rem;color:#64748b;white-space:nowrap}}
#zoom{{width:70px;accent-color:#3b82f6}}
.actions{{display:flex;gap:7px;align-items:center;flex-wrap:wrap}}
#counter{{font-size:0.72rem;color:#64748b;white-space:nowrap}}
.btn{{background:#1e293b;border:1px solid #334155;color:#94a3b8;padding:4px 10px;
  border-radius:6px;cursor:pointer;font-size:0.75rem;transition:all .2s;white-space:nowrap}}
.btn:hover{{border-color:#3b82f6;color:#60a5fa}}
.btn-dup{{border-color:#ef444440;color:#ef4444}}
.btn-dup:hover{{border-color:#ef4444;background:#1f0707}}
.mark-read-wrap{{display:flex;align-items:center;gap:5px;font-size:0.72rem;color:#94a3b8;
  background:#1e293b;border:1px solid #334155;border-radius:6px;padding:4px 10px;white-space:nowrap}}
.mark-read-wrap input{{accent-color:#3b82f6;cursor:pointer}}
.mark-read-wrap label{{cursor:pointer}}
#export-btn{{background:#22c55e;border:none;color:#fff;padding:5px 14px;
  border-radius:8px;cursor:pointer;font-weight:700;font-size:0.82rem;transition:background .2s;white-space:nowrap}}
#export-btn:hover{{background:#16a34a}}
#export-btn:disabled{{background:#374151;color:#6b7280;cursor:not-allowed}}
/* Grid */
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--card-w),1fr));gap:12px;padding:16px}}
/* Card */
.card{{position:relative;border-radius:10px;overflow:hidden;background:#1e293b;
  cursor:pointer;transition:transform .2s,box-shadow .2s,border-color .2s;border:2px solid transparent}}
.card:hover{{transform:scale(1.04);box-shadow:0 8px 24px #00000070;z-index:2}}
.card.selected{{border-color:#22c55e;box-shadow:0 0 0 3px #22c55e30}}
.cover{{width:100%;aspect-ratio:3/4;object-fit:cover;display:block}}
.placeholder{{width:100%;aspect-ratio:3/4;display:flex;align-items:center;
  justify-content:center;font-size:3rem;font-weight:800;color:rgba(255,255,255,0.12)}}
.card-info{{padding:7px 9px 9px}}
.card-title{{font-size:0.7rem;font-weight:600;line-height:1.3;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
  overflow:hidden;margin-bottom:3px}}
.card-meta{{font-size:0.62rem;color:#64748b;line-height:1.4}}
.badge{{display:inline-block;padding:2px 7px;border-radius:10px;font-size:0.6rem;font-weight:700;margin-top:3px}}
.badge.NOUVEAU{{background:#052e16;color:#22c55e;border:1px solid #22c55e40}}
.badge.INCERTAIN{{background:#1c1407;color:#f59e0b;border:1px solid #f59e0b40}}
.match-hint{{font-size:0.58rem;color:#475569;margin-top:2px;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}}
.checkmark{{position:absolute;top:7px;right:7px;width:22px;height:22px;border-radius:50%;
  background:#22c55e;color:#fff;display:none;align-items:center;justify-content:center;
  font-size:13px;font-weight:700;box-shadow:0 2px 6px #00000060}}
.card.selected .checkmark{{display:flex}}
/* BDtheque picto */
.bdt-link{{position:absolute;top:7px;left:7px;width:22px;height:22px;border-radius:50%;
  background:#1e293bcc;color:#60a5fa;display:flex;align-items:center;justify-content:center;
  font-size:12px;text-decoration:none;opacity:0;transition:opacity .2s;
  border:1px solid #3b82f660}}
.card:hover .bdt-link{{opacity:1}}
/* Tooltip */
#tooltip{{position:fixed;background:#1e293b;color:#e2e8f0;padding:7px 12px;border-radius:7px;
  font-size:0.78rem;pointer-events:none;display:none;z-index:200;max-width:440px;
  word-break:break-all;border:1px solid #334155;box-shadow:0 4px 16px #00000060;line-height:1.5}}
/* Misc */
#no-results{{display:none;text-align:center;padding:60px;color:#4b5563;font-size:1rem}}
.save-hint{{margin:0 16px 12px;background:#0f2a1a;border:1px solid #166534;border-radius:8px;
  padding:10px 16px;font-size:0.78rem;color:#86efac;display:none}}
.save-hint code{{background:#052e16;padding:1px 6px;border-radius:4px;font-family:monospace}}
.info-bar{{background:#080f1a;border-top:1px solid #1e293b;padding:7px 16px;
  font-size:0.7rem;color:#475569;display:flex;gap:16px;flex-wrap:wrap}}
.legend{{margin:8px 16px;background:#1e293b;border-radius:8px;padding:7px 14px;
  font-size:0.7rem;color:#94a3b8;display:flex;gap:14px;flex-wrap:wrap}}
/* Modal shared */
.modal-overlay{{position:fixed;inset:0;background:#000000b0;z-index:100;
  display:none;align-items:center;justify-content:center;padding:16px}}
.modal-overlay.open{{display:flex}}
.modal{{background:#1e293b;border-radius:12px;width:100%;max-width:920px;
  max-height:85vh;display:flex;flex-direction:column;border:1px solid #334155}}
.modal-hdr{{display:flex;align-items:center;justify-content:space-between;
  padding:12px 18px;border-bottom:1px solid #334155;flex-shrink:0}}
.modal-hdr h2{{font-size:0.95rem}}
.modal-close{{background:none;border:none;color:#94a3b8;font-size:1.3rem;cursor:pointer}}
.modal-body{{overflow-y:auto;padding:14px;flex:1}}
/* Doublons table */
.dup-table{{width:100%;border-collapse:collapse;font-size:0.73rem}}
.dup-table th{{background:#0f172a;color:#64748b;padding:7px 10px;text-align:left;
  font-size:0.65rem;text-transform:uppercase;letter-spacing:.04em;position:sticky;top:0}}
.dup-table td{{padding:6px 10px;border-bottom:1px solid #0f172a;vertical-align:top}}
.dup-table tr:hover td{{background:#162032}}
</style>
</head>
<body>

<header>
  <h1>🎨 BD Telegram</h1>
  <div class="pills">
    <div class="pill green">Nouveaux <b id="s-new">{nb_new}</b></div>
    <div class="pill yellow">Incertains <b id="s-inc">{nb_inc}</b></div>
    <div class="pill blue">Période <b>{date_min} → {date_max}</b></div>
  </div>
  <div class="filters">
    <button class="fb active" onclick="setFilter('ALL',this)">Tous</button>
    <button class="fb" onclick="setFilter('NOUVEAU',this)">Nouveaux</button>
    <button class="fb" onclick="setFilter('INCERTAIN',this)">Incertains</button>
  </div>
  <div class="search-wrap">
    <input id="search" type="text" placeholder="🔍 Rechercher..." oninput="applyFilters()">
  </div>
  <div class="zoom-wrap">🔍 <input type="range" id="zoom" min="130" max="320" value="180" oninput="setZoom(this.value)"></div>
  <div class="actions">
    <button class="btn" onclick="selectAllVisible()">Tout cocher</button>
    <button class="btn" onclick="deselectAll()">Décocher</button>
    <span id="counter">0 visible / 0 sélec.</span>
    {dup_btn}
    <div class="mark-read-wrap">
      <input type="checkbox" id="mark-read" checked>
      <label for="mark-read">Marquer comme lu</label>
    </div>
    <button id="export-btn" disabled onclick="exportSelection()">Enregistrer (0)</button>
  </div>
</header>

<div class="legend">
  <span><b style="color:#22c55e">■ NOUVEAU</b> — pas dans ta collection</span>
  <span><b style="color:#f59e0b">■ INCERTAIN</b> — ressemble à un fichier existant</span>
  <span>📚 = recherche BDthèque · Survol = nom complet</span>
  <span style="color:#475569">☑ <i>Marquer comme lu</i> : avance le curseur Telegram pour ne plus revoir les non-sélectionnés</span>
</div>

<div id="grid" class="grid"></div>
<div id="no-results">Aucun album pour ce filtre.</div>

<div class="save-hint" id="save-hint">
  ✅ <b>selection.json</b> téléchargé — sauvegarde-le dans
  <code>{project_esc}</code> puis lance <code>run.bat --download-selection</code>
</div>

<div class="info-bar">
  <span>Généré le {now}</span>
  <span id="info-visible">0 carte(s)</span>
  <span>{nb_dup} doublon(s) écarté(s)</span>
</div>

<!-- Modal doublons -->
<div class="modal-overlay" id="modal-dup" onclick="closeDupModal()">
  <div class="modal" onclick="event.stopPropagation()">
    <div class="modal-hdr">
      <h2>🚫 Doublons écartés — {nb_dup} fichiers déjà dans ta collection</h2>
      <button class="modal-close" onclick="closeDupModal()">✕</button>
    </div>
    <div class="modal-body">
      <table class="dup-table">
        <thead><tr>
          <th>Fichier Telegram</th><th>Correspondance collection</th><th>Score</th>
        </tr></thead>
        <tbody id="dup-body"></tbody>
      </table>
    </div>
  </div>
</div>

<div id="tooltip"></div>

<script>
const DATA     = {cards_json};
const DOUBLONS = {doublons_json};
const SCAN_BOUNDARY = {boundary_json};
const COLORS   = ['#ef4444','#f97316','#eab308','#22c55e','#14b8a6','#3b82f6','#8b5cf6','#ec4899'];

let currentFilter = 'ALL';
let selected      = new Set();

function setZoom(v) {{ document.documentElement.style.setProperty('--card-w', v+'px'); }}

/* Tooltip */
const tt = document.getElementById('tooltip');
document.addEventListener('mousemove', e => {{
  if (tt.style.display==='block') {{
    tt.style.left = Math.min(e.clientX+14, window.innerWidth-460)+'px';
    tt.style.top  = (e.clientY+14)+'px';
  }}
}});
function showTip(text) {{ tt.textContent=text; tt.style.display='block'; }}
function hideTip()     {{ tt.style.display='none'; }}

/* Title extraction for BDtheque */
{extract_title_js}

/* Render */
function renderGrid(items) {{
  const grid = document.getElementById('grid');
  const nr   = document.getElementById('no-results');
  document.getElementById('info-visible').textContent = items.length + ' carte(s)';
  if (!items.length) {{ grid.innerHTML=''; nr.style.display='block'; updateCounter(0); return; }}
  nr.style.display = 'none';
  grid.innerHTML = items.map(d => {{
    const isSel = selected.has(d.message_id);
    const color = COLORS[d.filename.charCodeAt(0) % COLORS.length];
    const entry = JSON.stringify({{channel:d.channel,message_id:d.message_id,filename:d.filename}}).replace(/"/g,'&quot;');
    const displayName = d.filename.replace(/_/g,' ');
    const imgH  = d.thumb
      ? `<img class="cover" src="${{d.thumb}}" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`
        +`<div class="placeholder" style="display:none;background:linear-gradient(135deg,${{color}}44,#0f172a)">${{d.filename[0].toUpperCase()}}</div>`
      : `<div class="placeholder" style="background:linear-gradient(135deg,${{color}}44,#0f172a)">${{d.filename[0].toUpperCase()}}</div>`;
    const matchH = d.top_match ? `<div class="match-hint">${{d.top_score}}% — ${{d.top_match}}</div>` : '';
    return `<div class="card${{isSel?' selected':''}}" data-id="${{d.message_id}}"
        data-rec="${{d.recommendation}}" data-name="${{d.filename.toLowerCase()}}"
        onclick="toggleCard(this)" data-entry="${{entry}}">
      ${{imgH}}
      <a class="bdt-link" href="${{bdtUrl(d.filename)}}" target="_blank"
         onclick="event.stopPropagation()" title="Rechercher sur BDthèque">📚</a>
      <div class="card-info">
        <div class="card-title" data-fn="${{d.filename}}" onmouseenter="showTip(this.dataset.fn)" onmouseleave="hideTip()">${{displayName}}</div>
        <div class="card-meta">${{d.channel_name}}<br>${{d.date}} · ${{d.size_mb}} Mo</div>
        ${{matchH}}
        <span class="badge ${{d.recommendation}}">${{d.recommendation}}</span>
      </div>
      <div class="checkmark">✓</div>
    </div>`;
  }}).join('');
  updateCounter(items.length);
}}

function applyFilters() {{
  const q = document.getElementById('search').value.toLowerCase();
  renderGrid(DATA.filter(d => {{
    if (currentFilter!=='ALL' && d.recommendation!==currentFilter) return false;
    if (q && !d.filename.toLowerCase().includes(q)) return false;
    return true;
  }}));
}}

function setFilter(f,btn) {{
  currentFilter=f;
  document.querySelectorAll('.fb').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}}

function toggleCard(card) {{
  const id=parseInt(card.dataset.id);
  if (selected.has(id)){{selected.delete(id);card.classList.remove('selected');}}
  else{{selected.add(id);card.classList.add('selected');}}
  updateCounter();
}}
function selectAllVisible() {{
  document.querySelectorAll('.card').forEach(c=>{{selected.add(parseInt(c.dataset.id));c.classList.add('selected');}});
  updateCounter();
}}
function deselectAll() {{
  selected.clear();
  document.querySelectorAll('.card').forEach(c=>c.classList.remove('selected'));
  updateCounter();
}}
function updateCounter(vis) {{
  const v = vis!==undefined ? vis : document.querySelectorAll('.card').length;
  const s = selected.size;
  document.getElementById('counter').textContent=`${{v}} visible / ${{s}} sélec.`;
  const btn=document.getElementById('export-btn');
  btn.textContent=`Enregistrer (${{s}})`;
  btn.disabled=s===0;
}}

function exportSelection() {{
  const markRead = document.getElementById('mark-read').checked;
  const files = DATA.filter(d=>selected.has(d.message_id))
    .map(d=>({{channel:d.channel,message_id:d.message_id,filename:d.filename}}));
  const payload = {{ mark_read:markRead, scan_boundary:SCAN_BOUNDARY, files:files }};
  const blob = new Blob([JSON.stringify(payload,null,2)],{{type:'application/json'}});
  const a = Object.assign(document.createElement('a'),{{href:URL.createObjectURL(blob),download:'selection.json'}});
  document.body.appendChild(a);a.click();document.body.removeChild(a);
  document.getElementById('save-hint').style.display='block';
}}

/* Modal doublons */
function openDupModal() {{
  document.getElementById('dup-body').innerHTML = DOUBLONS.map(d=>{{
    const c=d.score>=85?'#22c55e':d.score>=50?'#f59e0b':'#6b7280';
    return `<tr><td><b>${{d.filename}}</b><br><span style="color:#475569;font-size:.6rem">${{d.channel_name}} · ${{d.size_mb}} Mo</span></td>
      <td style="color:#94a3b8">${{d.match}}</td>
      <td style="color:${{c}};font-weight:700;text-align:right">${{d.score}}%</td></tr>`;
  }}).join('');
  document.getElementById('modal-dup').classList.add('open');
}}
function closeDupModal() {{ document.getElementById('modal-dup').classList.remove('open'); }}
document.addEventListener('keydown', e=>{{ if(e.key==='Escape') closeDupModal(); }});

applyFilters();
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return output_path
