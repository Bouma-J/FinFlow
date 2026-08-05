"""Utilitaires transverses liés aux comptes utilisateurs."""


def user_role_label(user):
    """Libellé lisible du profil/rôle d'un utilisateur.

    Utilisé pour figer (snapshot) le profil de l'auteur d'une analyse ou d'une
    visite terrain, afin que la traçabilité reste fiable même si les rôles de
    l'utilisateur évoluent par la suite.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return ""
    names = list(user.groups.values_list("name", flat=True))
    if names:
        return ", ".join(names)
    if user.is_superuser:
        return "Administrateur"
    if getattr(user, "is_group_level", False):
        return "Responsable Groupe"
    return ""
