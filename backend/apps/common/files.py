"""Utilitaires de gestion des fichiers uploadés."""
import os


def safe_filename(filename, max_base=80):
    """Tronque le nom de fichier (en conservant l'extension) pour éviter
    de dépasser la longueur maximale des champs `FileField`.

    Django ajoute au besoin un suffixe anti-collision ; on garde donc une
    marge confortable même avec des chemins comprenant plusieurs UUID.
    """
    base, ext = os.path.splitext(filename)
    return f"{base[:max_base]}{ext[:12]}"
