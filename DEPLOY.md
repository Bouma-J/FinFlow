# 🚀 Guide de Déploiement Rapide FinFlow

Guide simplifié pour déployer **FinFlow** sur un serveur de production accessible aux utilisateurs.

## 📋 Table des Matières

1. [Déploiement Automatique (Recommandé)](#-déploiement-automatique-recommandé)
2. [Prérequis](#-prérequis)
3. [Options de Déploiement](#-options-de-déploiement)
4. [Accès à l'Application](#-accès-à-lapplication)
5. [Mise à Jour](#-mise-à-jour)
6. [Support](#-support)

---

## 🎯 Déploiement Automatique (Recommandé)

### Option 1 : Avec Nom de Domaine (Production)

Idéal pour un déploiement production avec certificat SSL/TLS Let's Encrypt automatique.

**Prérequis :**
- Un serveur Ubuntu 22.04/24.04 LTS avec accès root
- Un nom de domaine pointant vers l'IP du serveur (ex: `finflow.votredomaine.com`)
- Ports 80, 443, 9000 ouverts dans le pare-feu

**Installation en une commande :**

```bash
sudo bash -c 'curl -fsSL https://raw.githubusercontent.com/Bouma-J/FinFlow/main/deploy/ubuntu-install.sh | bash'
```

Le script vous demandera :
- Votre nom de domaine
- Les mots de passe pour PostgreSQL et MinIO
- Une clé secrète Django (générée automatiquement si vide)
- Configuration email (optionnel)

✅ **Résultat :** Application accessible sur `https://finflow.votredomaine.com`

---

### Option 2 : Avec Adresse IP (Test/Démo)

Pour un déploiement rapide sans nom de domaine (laboratoire, réseau interne).

```bash
sudo bash -c 'curl -fsSL https://raw.githubusercontent.com/Bouma-J/FinFlow/main/deploy/ubuntu-install-ip.sh | bash'
```

Le script configure :
- Accès HTTP par IP : `http://<votre-ip>/`
- Option HTTPS avec certificat auto-signé (si souhaité)

✅ **Résultat :** Application accessible sur `http://<IP-du-serveur>/`

---

## 🔧 Prérequis

### Serveur

| Ressource | Minimum | Recommandé |
|-----------|---------|------------|
| **CPU** | 2 vCPU | 4 vCPU |
| **RAM** | 8 Go | 16 Go |
| **Disque** | 40 Go SSD | 80 Go+ SSD |
| **OS** | Ubuntu 22.04/24.04 LTS | Ubuntu 24.04 LTS |
| **Réseau** | IP publique | IP publique + domaine |

### Ports à Ouvrir

| Port | Usage |
|------|--------|
| **22** | SSH (administration) |
| **80** | HTTP (redirection HTTPS) |
| **443** | HTTPS (application) |
| **9000** | MinIO API (fichiers) |

⚠️ **Sécurité :** Ne pas exposer le port 9001 (console MinIO) publiquement. Utilisez un tunnel SSH si nécessaire.

---

## 🛠 Options de Déploiement

### A. Docker Compose Local (Développement)

Pour tester localement avant le déploiement :

```bash
# Cloner le projet
git clone https://github.com/Bouma-J/FinFlow.git
cd FinFlow

# Démarrer avec Docker Compose
docker compose up --build

# Ou avec données de démonstration
SEED_DEMO=1 docker compose up --build
```

**Accès :**
- Frontend : http://localhost:8080
- API : http://localhost:8080/api/v1/
- Documentation API : http://localhost:8080/api/docs/
- Console MinIO : http://localhost:9001 (minioadmin / minioadmin)

### B. Déploiement Manuel

Pour un contrôle total, consultez le guide détaillé :
👉 [documentation/13-guide-deploiement-ubuntu.md](documentation/13-guide-deploiement-ubuntu.md)

### C. Kubernetes

Pour un déploiement haute disponibilité :
👉 [deploy/k8s/README.md](deploy/k8s/README.md)

---

## 🌐 Accès à l'Application

### Après Installation Réussie

**Avec domaine :**
- Application : `https://finflow.votredomaine.com`
- API : `https://finflow.votredomaine.com/api/v1/`
- Documentation : `https://finflow.votredomaine.com/api/docs/`

**Avec IP :**
- Application : `http://<IP-serveur>/`
- API : `http://<IP-serveur>/api/v1/`
- Documentation : `http://<IP-serveur>/api/docs/`

### Comptes par Défaut (Données de Démo)

⚠️ **Uniquement si vous avez activé `SEED_DEMO=1` lors de l'installation**

| Rôle | Username | Mot de passe |
|------|----------|--------------|
| **Administrateur Groupe** | `group_admin` | `FinFlow2026!` |
| **Administrateur Filiale** | `fil01_admin` | `FinFlow2026!` |

🔒 **IMPORTANT :** Changez immédiatement ces mots de passe en production !

### Premier Compte Administrateur (Production)

Si vous n'avez pas activé le seed, créez votre premier administrateur :

```bash
cd /opt/finflow
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend \
  python manage.py createsuperuser
```

---

## 🔄 Mise à Jour

Pour mettre à jour une instance déjà déployée :

```bash
sudo finflow-update
```

Ou directement :

```bash
sudo bash /opt/finflow/deploy/ubuntu-update.sh
```

Le script effectue automatiquement :
1. ✅ Sauvegarde de la base de données
2. ✅ Récupération des dernières modifications (git pull)
3. ✅ Reconstruction des images Docker
4. ✅ Migrations de base de données
5. ✅ Synchronisation des rôles et permissions
6. ✅ Redémarrage des services

---

## 📊 Vérification du Déploiement

### État des Services

```bash
cd /opt/finflow
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

### Santé de l'API

```bash
curl -fsS https://finflow.votredomaine.com/api/v1/health/
```

**Réponse attendue :**
```json
{
  "status": "ok",
  "ready": true,
  "database": "ok",
  "storage": "ok",
  "cache": "ok"
}
```

### Logs en Temps Réel

```bash
# Backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f backend

# Tous les services
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

---

## 🔐 Sécurité Post-Déploiement

### Checklist de Sécurité

- [ ] Changer tous les mots de passe par défaut
- [ ] Désactiver `SEED_DEMO` en production (`SEED_DEMO=0`)
- [ ] Configurer le pare-feu (UFW)
- [ ] Activer fail2ban pour SSH
- [ ] Configurer les sauvegardes automatiques
- [ ] Limiter l'accès à la console MinIO (port 9001)
- [ ] Configurer HTTPS/TLS
- [ ] Vérifier `DJANGO_ALLOWED_HOSTS`
- [ ] Activer HSTS (`DJANGO_SECURE_HSTS_SECONDS`)

---

## 📦 Sauvegardes

Les scripts d'installation configurent automatiquement des sauvegardes quotidiennes.

### Sauvegarde Manuelle

```bash
sudo FINFLOW_DIR=/opt/finflow /opt/finflow/scripts/backup.sh
```

### Restauration

```bash
sudo /opt/finflow/scripts/restore.sh --target live \
  --snapshot /var/backups/finflow/snapshots/<timestamp> \
  --confirm=RESTORE
```

⚠️ **Attention :** La restauration écrase la base de données actuelle !

---

## 🆘 Support

### Documentation Complète

📚 [documentation/README.md](documentation/README.md)

### Guides Spécifiques

- **Architecture :** [documentation/02-architecture-technique.md](documentation/02-architecture-technique.md)
- **Configuration :** [documentation/05-configuration.md](documentation/05-configuration.md)
- **Déploiement Ubuntu :** [documentation/13-guide-deploiement-ubuntu.md](documentation/13-guide-deploiement-ubuntu.md)
- **Exploitation :** [documentation/10-exploitation-supervision.md](documentation/10-exploitation-supervision.md)

### Problèmes Courants

| Symptôme | Solution |
|----------|----------|
| 502 Bad Gateway | Vérifier logs backend : `docker compose logs backend` |
| Erreur stockage | Vérifier MinIO et variables `AWS_S3_*` |
| Emails non envoyés | Vérifier configuration SMTP dans l'interface |
| Certificat SSL expiré | `sudo certbot renew` |

### Dépannage

```bash
# Vérifier l'état des conteneurs
docker compose ps

# Redémarrer un service
docker compose restart backend

# Logs détaillés
docker compose logs --tail=100 backend worker beat

# Espace disque
df -h
docker system df
```

---

## 🎓 Ressources Additionnelles

- **Dépôt GitHub :** https://github.com/Bouma-J/FinFlow
- **Documentation API :** `https://finflow.votredomaine.com/api/docs/`
- **Scripts de déploiement :** [deploy/](deploy/)
- **Kubernetes :** [deploy/k8s/](deploy/k8s/)

---

## 📝 Notes Importantes

1. **Base de données :** PostgreSQL avec sauvegardes automatiques quotidiennes
2. **Stockage :** MinIO (compatible S3) pour les documents et contrats
3. **Workers :** Celery pour les tâches asynchrones (emails, CBS, génération de contrats)
4. **Monitoring :** Endpoint `/api/v1/health/` pour les checks de santé

---

**FIN_FLOW** — *Plateforme SaaS de gestion du cycle de vie complet des dossiers de crédit*

Pour toute question, consultez la [documentation complète](documentation/README.md) ou ouvrez une issue sur GitHub.
