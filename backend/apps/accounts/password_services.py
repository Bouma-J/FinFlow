"""Génération et envoi des mots de passe temporaires."""
from __future__ import annotations

import logging
import secrets
import string

from django.conf import settings
from django.utils.html import escape

logger = logging.getLogger("finflow")


def generate_temporary_password(length: int = 14) -> str:
    """Mot de passe aléatoire respectant les contraintes de complexité usuelles."""
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    specials = "!@#$%&*"
    for _ in range(50):
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in specials for c in pwd)
        ):
            return pwd
    return (
        secrets.choice(string.ascii_uppercase)
        + secrets.choice(string.ascii_lowercase)
        + secrets.choice(string.digits)
        + secrets.choice(specials)
        + "".join(secrets.choice(alphabet) for _ in range(max(0, length - 4)))
    )


def _frontend_base() -> str:
    return (getattr(settings, "FRONTEND_BASE_URL", None) or "http://localhost").rstrip(
        "/"
    )


def send_credentials_email(user, raw_password: str, *, reason: str = "created") -> bool:
    """
    Envoie le mot de passe temporaire par e-mail.

    Utilise le SMTP de la filiale de l'utilisateur s'il est configuré,
    sinon le SMTP global Django.
    """
    email = (user.email or "").strip()
    if not email:
        logger.warning(
            "Pas d'e-mail pour envoyer le mot de passe (user=%s)", user.username
        )
        return False

    login_url = f"{_frontend_base()}/login"
    if reason == "reset":
        subject = "[FIN_FLOW] Nouveau mot de passe temporaire"
        title = "Mot de passe régénéré"
        intro = (
            "Un administrateur a régénéré votre mot de passe FIN_FLOW. "
            "Utilisez le mot de passe temporaire ci-dessous pour vous connecter, "
            "puis choisissez immédiatement un nouveau mot de passe."
        )
    else:
        subject = "[FIN_FLOW] Vos identifiants de connexion"
        title = "Bienvenue sur FIN_FLOW"
        intro = (
            "Votre compte FIN_FLOW a été créé. "
            "Connectez-vous avec les identifiants ci-dessous ; "
            "vous devrez changer votre mot de passe à la première connexion."
        )

    display = user.get_full_name() or user.username
    text = (
        f"{title}\n\n"
        f"Bonjour {display},\n\n"
        f"{intro}\n\n"
        f"Identifiant : {user.username}\n"
        f"Mot de passe temporaire : {raw_password}\n\n"
        f"Connexion : {login_url}\n\n"
        "Ne partagez pas ce message. Ce mot de passe est à usage unique "
        "jusqu'à son remplacement.\n"
    )
    html = f"""
    <div style="font-family:Segoe UI,Arial,sans-serif;max-width:560px;margin:0 auto;color:#1a1a1a">
      <h2 style="color:#0b3d2e">{escape(title)}</h2>
      <p>Bonjour <strong>{escape(display)}</strong>,</p>
      <p>{escape(intro)}</p>
      <table style="border-collapse:collapse;margin:16px 0;width:100%">
        <tr>
          <td style="padding:8px;background:#f4f7f5;border:1px solid #dce5e0">Identifiant</td>
          <td style="padding:8px;border:1px solid #dce5e0"><code>{escape(user.username)}</code></td>
        </tr>
        <tr>
          <td style="padding:8px;background:#f4f7f5;border:1px solid #dce5e0">Mot de passe temporaire</td>
          <td style="padding:8px;border:1px solid #dce5e0"><code>{escape(raw_password)}</code></td>
        </tr>
      </table>
      <p><a href="{escape(login_url)}" style="display:inline-block;padding:10px 16px;background:#0b3d2e;color:#fff;text-decoration:none;border-radius:4px">Se connecter</a></p>
      <p style="color:#666;font-size:13px">Ne partagez pas ce message. Changez ce mot de passe dès la première connexion.</p>
    </div>
    """

    try:
        from apps.notifications.mail import send_email_for_tenant

        tenant = getattr(user, "tenant", None)
        send_email_for_tenant(
            tenant=tenant,
            subject=subject,
            text_body=text,
            html_body=html,
            recipients=[email],
        )
        return True
    except Exception:  # noqa: BLE001
        logger.exception(
            "Échec d'envoi du mot de passe temporaire à %s (user=%s)",
            email,
            user.username,
        )
        return False


def issue_temporary_password(
    user,
    *,
    reason: str = "created",
    send_email: bool = True,
    commit: bool = True,
) -> tuple[str, bool]:
    """Définit un mot de passe temporaire et force le changement à la prochaine connexion."""
    raw = generate_temporary_password()
    user.set_password(raw)
    user.must_change_password = True
    if commit:
        user.save(update_fields=["password", "must_change_password"])
        try:
            from apps.common.cache_utils import invalidate_prefix

            invalidate_prefix("me", user.id)
        except Exception:  # noqa: BLE001
            logger.debug("Impossible d'invalider le cache me pour %s", user.pk)
    email_sent = False
    if send_email:
        email_sent = send_credentials_email(user, raw, reason=reason)
    return raw, email_sent
