"""
everything_checker.py — Verification des doublons via l'API HTTP d'Everything

L'API HTTP d'Everything doit etre activee dans :
  Everything -> Outils -> Options -> Serveur HTTP
  Port : 8070 (configure dans config.json)
"""
import requests
from logger import log_info, log_error, log_skip

# Extensions BD a prendre en compte dans la recherche par taille
BD_EXTENSIONS = ["pdf", "cbr", "cbz"]


def file_exists_in_everything(filename, file_size=None, api_url="http://localhost:8070"):
    """
    Verifie si un fichier existe deja dans la collection via l'API HTTP d'Everything.

    Strategie 1 : Recherche par nom de fichier exact (insensible a la casse)
    Strategie 2 : Recherche par taille exacte si le nom n'est pas trouve (doublons renommes)

    Retourne True si le fichier existe, False sinon.
    Leve une exception si Everything n'est pas accessible.
    """
    # Strategie 1 : nom exact
    if _search_by_name(filename, api_url):
        return True

    # Strategie 2 : taille (si disponible et significative > 100 Ko)
    if file_size and file_size > 102400:
        if _search_by_size(file_size, api_url):
            log_skip(f"Doublon detecte par taille ({file_size / 1024 / 1024:.1f} Mo) pour : {filename}")
            return True

    return False


def _search_by_name(filename, api_url):
    """Recherche un fichier par nom exact dans Everything."""
    try:
        params = {
            "s":    f'"{filename}"',
            "json": 1,
            "count": 5,
        }
        response = requests.get(api_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        return len(data.get("results", [])) > 0

    except requests.exceptions.ConnectionError:
        log_error(
            "Impossible de se connecter a Everything. "
            "Verifiez que le serveur HTTP est actif sur le port 8070."
        )
        raise
    except requests.exceptions.Timeout:
        log_error("Timeout lors de la connexion a Everything (port 8070).")
        raise
    except Exception as e:
        log_error(f"Erreur inattendue Everything API : {e}")
        raise


def _search_by_size(file_size, api_url):
    """Recherche des fichiers BD de taille exacte dans Everything."""
    try:
        ext_filter = ";".join(BD_EXTENSIONS)
        query = f"size:{file_size} ext:{ext_filter}"
        params = {"s": query, "json": 1, "count": 5}
        response = requests.get(api_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        return len(data.get("results", [])) > 0
    except Exception:
        return False


def test_everything_connection(api_url):
    """Teste la connexion a Everything. Retourne True si OK, False sinon."""
    try:
        response = requests.get(api_url, params={"json": 1, "count": 1}, timeout=5)
        response.raise_for_status()
        return True
    except Exception:
        return False


def search_by_keywords(filename, search_paths=None, api_url="http://localhost:8070", count=50):
    """
    Recherche dans Everything par mots-cles extraits du nom de fichier Telegram,
    optionnellement limitee aux dossiers BD configures dans bd_search_paths.

    Retourne une liste de dicts {name, path} a scorer par fuzzy_matcher.

    Exemple de requete generee :
      ( path:"F:\\BD" | path:"F:\\BD Topectra" ) batman noel ext:cbz;cbr;pdf
    """
    from fuzzy_matcher import get_search_keywords

    keywords = get_search_keywords(filename)
    if not keywords:
        return []

    ext_filter = "ext:cbz;cbr;pdf;epub;rar;zip"
    keyword_str = " ".join(keywords)

    if search_paths:
        path_parts = " | ".join(f'<"{p}">' for p in search_paths)
        query = f"<{path_parts}> {keyword_str} {ext_filter}"
    else:
        query = f"{keyword_str} {ext_filter}"

    try:
        params = {
            "s":           query,
            "json":        1,
            "count":       count,
            "path_column": 1,
        }
        response = requests.get(api_url, params=params, timeout=8)
        response.raise_for_status()
        return response.json().get("results", [])
    except Exception:
        return []
