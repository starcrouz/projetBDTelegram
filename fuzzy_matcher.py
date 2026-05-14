"""
fuzzy_matcher.py — Comparaison floue de noms de fichiers BD
"""
import os
import re
from difflib import SequenceMatcher

# Mots à ignorer pour la recherche (qualificatifs techniques, pas le titre)
STOP_WORDS = {
    'scan', 'hd', 'fr', 'vf', 'vo', 'int', 'complet', 'complete',
    'digital', 'retail', 'webrip', 'cbz', 'cbr', 'pdf',
    'de', 'du', 'des', 'le', 'la', 'les', 'un', 'une', 'et', 'en',
    'the', 'a', 'an', 'of', 'and', 'in', 'to',
}


def normalize(filename):
    """Normalise un nom de fichier BD pour comparaison."""
    name = os.path.splitext(filename)[0]
    name = name.lower()
    name = re.sub(r'[\-_\.\[\]\(\)\{\}]+', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def get_search_keywords(filename, max_keywords=5):
    """Extrait les mots-clés les plus distinctifs d'un nom de fichier."""
    name = normalize(filename)
    words = name.split()
    keywords = [w for w in words if len(w) >= 2 and w not in STOP_WORDS]
    if not keywords:
        keywords = [w for w in words if len(w) >= 2]
    # Priorité aux mots les plus longs (plus distinctifs)
    return sorted(keywords, key=len, reverse=True)[:max_keywords]


def fuzzy_score(telegram_filename, collection_filename):
    """Retourne un score de similarité 0-100 entre deux noms de fichiers."""
    a = normalize(telegram_filename)
    b = normalize(collection_filename)
    return int(SequenceMatcher(None, a, b).ratio() * 100)


def rank_matches(telegram_filename, everything_results):
    """
    Score et classe les résultats Everything par rapport au fichier Telegram.
    Retourne une liste de dicts triée par score décroissant.
    """
    scored = []
    for result in everything_results:
        name = result.get('name', '')
        path = result.get('path', '')
        score = fuzzy_score(telegram_filename, name)
        scored.append({
            'filename': name,
            'path':     path,
            'score':    score,
            'full_path': os.path.join(path, name),
        })
    return sorted(scored, key=lambda x: x['score'], reverse=True)
