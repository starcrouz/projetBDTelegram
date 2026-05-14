"""
report_generator.py — Generateur du rapport HTML de comparaison Telegram / collection
"""
import os
import webbrowser
from datetime import datetime


def generate_html_report(files_with_matches, output_path):
    """
    Genere un rapport HTML avec la liste des fichiers Telegram et leurs
    meilleures correspondances trouvees dans Everything.

    files_with_matches : liste de dicts enrichis par cmd_review() dans main.py
      {filename, file_size, channel_name, date, recommendation, matches: [{filename, path, score}]}
    """
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    total = len(files_with_matches)
    nb_new       = sum(1 for f in files_with_matches if f["recommendation"] == "NOUVEAU")
    nb_uncertain = sum(1 for f in files_with_matches if f["recommendation"] == "INCERTAIN")
    nb_duplicate = sum(1 for f in files_with_matches if f["recommendation"] == "DOUBLON")

    rows_html = ""
    for f in files_with_matches:
        rec   = f["recommendation"]
        color = {"NOUVEAU": "#22c55e", "INCERTAIN": "#f59e0b", "DOUBLON": "#ef4444"}[rec]
        bg    = {"NOUVEAU": "#052e16", "INCERTAIN": "#1c1407", "DOUBLON": "#1f0707"}[rec]

        size_mb  = f["file_size"] / 1024 / 1024
        date_str = f["date"].strftime("%d/%m/%Y")

        # Colonne correspondances Everything
        if f["matches"]:
            matches_html = ""
            for m in f["matches"][:3]:
                bar_w  = m["score"]
                bar_col = "#22c55e" if m["score"] >= 80 else "#f59e0b" if m["score"] >= 50 else "#6b7280"
                matches_html += f"""
                <div class="match">
                  <div class="match-score-bar">
                    <div class="bar" style="width:{bar_w}%; background:{bar_col}"></div>
                  </div>
                  <span class="score-label" style="color:{bar_col}">{m['score']}%</span>
                  <span class="match-name" title="{m['full_path']}">{m['filename']}</span>
                  <span class="match-path">{m['path']}</span>
                </div>"""
        else:
            matches_html = '<span class="no-match">Aucune correspondance trouvee</span>'

        rows_html += f"""
        <tr style="background:{bg}">
          <td>
            <span class="badge" style="background:{color}">{rec}</span>
          </td>
          <td>
            <div class="tg-filename">{f['filename']}</div>
            <div class="tg-meta">{f['channel_name']} &nbsp;|&nbsp; {date_str} &nbsp;|&nbsp; {size_mb:.1f} Mo</div>
          </td>
          <td>{matches_html}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BD Telegram — Rapport de revue</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: #0f172a; color: #e2e8f0;
    padding: 24px;
  }}
  h1 {{ font-size: 1.6rem; color: #60a5fa; margin-bottom: 6px; }}
  .subtitle {{ color: #94a3b8; font-size: 0.9rem; margin-bottom: 20px; }}
  .stats {{
    display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap;
  }}
  .stat {{
    background: #1e293b; border-radius: 10px;
    padding: 12px 20px; text-align: center; min-width: 120px;
  }}
  .stat-num {{ font-size: 2rem; font-weight: 700; }}
  .stat-label {{ font-size: 0.75rem; color: #94a3b8; margin-top: 4px; }}
  .legend {{
    font-size: 0.8rem; color: #94a3b8; margin-bottom: 16px;
    border: 1px solid #334155; border-radius: 8px; padding: 10px 16px;
    background: #1e293b;
  }}
  .legend span {{ margin-right: 20px; }}
  table {{
    width: 100%; border-collapse: collapse;
    background: #1e293b; border-radius: 12px; overflow: hidden;
  }}
  th {{
    background: #0f172a; color: #94a3b8;
    font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
    padding: 12px 16px; text-align: left; letter-spacing: 0.05em;
  }}
  td {{ padding: 12px 16px; border-bottom: 1px solid #0f172a; vertical-align: top; }}
  .badge {{
    display: inline-block; padding: 3px 10px;
    border-radius: 20px; font-size: 0.7rem; font-weight: 700;
    color: #fff; white-space: nowrap;
  }}
  .tg-filename {{ font-weight: 600; font-size: 0.9rem; word-break: break-all; }}
  .tg-meta {{ color: #64748b; font-size: 0.75rem; margin-top: 4px; }}
  .match {{ margin-bottom: 8px; }}
  .match-score-bar {{
    display: inline-block; width: 60px; height: 6px;
    background: #334155; border-radius: 3px; vertical-align: middle;
    margin-right: 6px; overflow: hidden;
  }}
  .bar {{ height: 100%; border-radius: 3px; }}
  .score-label {{
    font-size: 0.75rem; font-weight: 700;
    display: inline-block; width: 32px; text-align: right;
    margin-right: 8px; vertical-align: middle;
  }}
  .match-name {{
    font-size: 0.82rem; font-weight: 500;
    word-break: break-all; vertical-align: middle;
  }}
  .match-path {{
    display: block; font-size: 0.7rem; color: #64748b;
    margin-left: 106px; margin-top: 2px;
  }}
  .no-match {{ color: #4b5563; font-style: italic; font-size: 0.82rem; }}
  tr:last-child td {{ border-bottom: none; }}
</style>
</head>
<body>
<h1>BD Telegram — Rapport de revue</h1>
<div class="subtitle">Genere le {now} &nbsp;|&nbsp; {total} fichier(s) non lu(s) sur Telegram</div>

<div class="stats">
  <div class="stat">
    <div class="stat-num" style="color:#22c55e">{nb_new}</div>
    <div class="stat-label">NOUVEAU</div>
  </div>
  <div class="stat">
    <div class="stat-num" style="color:#f59e0b">{nb_uncertain}</div>
    <div class="stat-label">INCERTAIN</div>
  </div>
  <div class="stat">
    <div class="stat-num" style="color:#ef4444">{nb_duplicate}</div>
    <div class="stat-label">DOUBLON probable</div>
  </div>
  <div class="stat">
    <div class="stat-num" style="color:#60a5fa">{total}</div>
    <div class="stat-label">TOTAL</div>
  </div>
</div>

<div class="legend">
  <strong>Legende :</strong>
  <span><span style="color:#22c55e">&#9632;</span> NOUVEAU — aucune correspondance (&lt;50%) → sera telecharge</span>
  <span><span style="color:#f59e0b">&#9632;</span> INCERTAIN — correspondance partielle (50–84%) → verifiez manuellement</span>
  <span><span style="color:#ef4444">&#9632;</span> DOUBLON — forte correspondance (&ge;85%) → sera ignore</span>
</div>

<table>
  <thead>
    <tr>
      <th style="width:100px">Statut</th>
      <th style="width:35%">Fichier Telegram</th>
      <th>Meilleures correspondances dans votre collection</th>
    </tr>
  </thead>
  <tbody>
    {rows_html}
  </tbody>
</table>

<div class="subtitle" style="margin-top:16px">
  Pour agir sur les INCERTAINS : ajoutez le nom exact de fichier Telegram dans
  <code>skip_list.txt</code> (un par ligne) pour les exclure du prochain telechargement.
</div>

</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


def open_in_browser(path):
    """Ouvre le fichier HTML dans le navigateur par defaut."""
    webbrowser.open(f"file:///{os.path.abspath(path)}")
