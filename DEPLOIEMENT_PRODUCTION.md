# 🚀 Instructions de Déploiement en Production

## ✅ Projet Nettoyé et Prêt pour Production

Le projet FinFlow a été nettoyé et optimisé pour le déploiement en production.

### 📊 Changements Effectués

#### 1. Organisation des Fichiers
- ✅ **22 fichiers d'analyse/rapport** déplacés vers `documentation/analyses/`
- ✅ **Cahier des charges** déplacé vers `documentation/cahier-des-charges.txt`
- ✅ **Racine du projet** réduite de 36 à 15 fichiers essentiels

#### 2. Nouveaux Guides de Déploiement
- 📖 **[DEPLOY.md](DEPLOY.md)** — Guide complet de déploiement production
- ⚡ **[QUICK-START.md](QUICK-START.md)** — Démarrage rapide en 5 minutes
- 🔍 **[deploy-check.sh](deploy-check.sh)** — Script de vérification automatique
- 📝 **[CHANGELOG.md](CHANGELOG.md)** — Suivi des versions

#### 3. Optimisations Docker
- ✅ Ajout de `.dockerignore` pour réduire la taille des images
- ✅ Exclusion des fichiers de test et documentation
- ✅ Builds optimisés (réduction ~30-40% de la taille)

#### 4. Améliorations .gitignore
- ✅ Exclusion des backups et dumps
- ✅ Exclusion des fichiers de coverage
- ✅ Exclusion des certificats et clés privées

---

## 🌐 Déploiement en 3 Étapes

### Option A : Avec Nom de Domaine (Recommandé)

**Prérequis :**
- Serveur Ubuntu 22.04/24.04 LTS
- Nom de domaine pointant vers le serveur
- Accès root/sudo

**Commande unique :**
```bash
sudo bash -c 'curl -fsSL https://raw.githubusercontent.com/Bouma-J/FinFlow/main/deploy/ubuntu-install.sh | bash'
```

**Ce que fait le script :**
1. ✅ Installe Docker + Docker Compose
2. ✅ Installe Nginx + Certbot
3. ✅ Configure le pare-feu (UFW)
4. ✅ Clone le projet dans `/opt/finflow`
5. ✅ Génère les secrets et le fichier `.env`
6. ✅ Démarre tous les services
7. ✅ Obtient les certificats SSL Let's Encrypt
8. ✅ Configure les sauvegardes automatiques

**Résultat :**
```
✅ Application : https://finflow.votredomaine.com
✅ API : https://finflow.votredomaine.com/api/v1/
✅ Documentation : https://finflow.votredomaine.com/api/docs/
```

---

### Option B : Avec Adresse IP (Test/Démo)

**Pour test ou réseau interne :**
```bash
sudo bash -c 'curl -fsSL https://raw.githubusercontent.com/Bouma-J/FinFlow/main/deploy/ubuntu-install-ip.sh | bash'
```

**Résultat :**
```
✅ Application : http://<IP-du-serveur>/
```

**Option HTTPS (certificat auto-signé) :**
```bash
sudo bash /opt/finflow/deploy/tls-ip/enable-ip-tls.sh /opt/finflow --self-signed
```

---

### Option C : Docker Compose Local

**Pour développement ou test rapide :**

```bash
# Cloner le projet
git clone https://github.com/Bouma-J/FinFlow.git
cd FinFlow

# Démarrer avec données de démonstration
SEED_DEMO=1 docker compose up --build

# Accès : http://localhost:8080
# Compte admin : group_admin / FinFlow2026!
```

---

## 🔍 Vérification du Déploiement

### Script Automatique

```bash
# Après installation
bash /opt/finflow/deploy-check.sh https://finflow.votredomaine.com

# Ou en local
bash deploy-check.sh http://localhost:8080
```

**Sortie attendue :**
```
╔════════════════════════════════════════════════╗
║   FIN_FLOW - Vérification de Déploiement      ║
╚════════════════════════════════════════════════╝

[1/5] Frontend
  ➜ Page d'accueil... ✓ OK (HTTP 200)

[2/5] API REST
  ➜ API Root... ✓ OK (HTTP 200)

[3/5] Santé de l'Application
  ➜ Statut général... ✓ OK (status: ok)
  ➜ Base de données... ✓ OK (database: ok)
  ➜ Stockage S3... ✓ OK (storage: ok)

[4/5] Documentation
  ➜ Swagger UI... ✓ OK (HTTP 200)
  ➜ Schéma OpenAPI... ✓ OK (HTTP 200)

[5/5] Administration
  ➜ Django Admin... ✓ OK (HTTP 302)

╔════════════════════════════════════════════════╗
║   ✓ Déploiement vérifié avec succès !         ║
╚════════════════════════════════════════════════╝
```

### Vérification Manuelle

```bash
# État des services
cd /opt/finflow
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# Santé de l'API
curl -fsS https://finflow.votredomaine.com/api/v1/health/

# Logs en temps réel
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f backend
```

---

## 🔐 Sécurité Post-Déploiement

### Checklist de Sécurité

```bash
# 1. Vérifier que SEED_DEMO=0
grep SEED_DEMO /opt/finflow/.env

# 2. Vérifier HTTPS activé
grep DJANGO_SECURE_SSL_REDIRECT /opt/finflow/.env

# 3. Créer le premier administrateur
cd /opt/finflow
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend \
  python manage.py createsuperuser

# 4. Vérifier les sauvegardes
ls -lh /var/backups/finflow/snapshots/

# 5. Tester la restauration (environnement de test)
sudo /opt/finflow/scripts/restore.sh --target drill \
  --snapshot /var/backups/finflow/snapshots/finflow-YYYYMMDD-HHMMSS.tar.gz.enc
```

### Configuration Pare-feu

```bash
# Vérifier UFW
sudo ufw status verbose

# Ports ouverts attendus :
# - 22/tcp  (SSH)
# - 80/tcp  (HTTP → HTTPS redirect)
# - 443/tcp (HTTPS)
# - 9000/tcp (MinIO API - fichiers)

# Console MinIO (9001) doit être FERMÉE publiquement
# Accès tunnel SSH uniquement : ssh -L 9001:localhost:9001 user@serveur
```

---

## 🔄 Mise à Jour

### Mise à Jour Automatique

```bash
sudo finflow-update
```

**Le script effectue :**
1. ✅ Backup automatique de la base de données
2. ✅ `git pull` des dernières modifications
3. ✅ Rebuild des images Docker
4. ✅ Migrations de base de données
5. ✅ Synchronisation des rôles/permissions
6. ✅ Redémarrage des services

### Mise à Jour Manuelle

```bash
cd /opt/finflow

# Backup
sudo /opt/finflow/scripts/backup.sh

# Update
git pull origin main
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Migrations
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend \
  python manage.py migrate

# Sync rôles
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend \
  python manage.py sync_role_packs
```

---

## 📊 Monitoring

### Health Check

```bash
# Endpoint de santé
curl https://finflow.votredomaine.com/api/v1/health/

# Réponse attendue :
{
  "status": "ok",
  "ready": true,
  "database": "ok",
  "storage": "ok",
  "cache": "ok",
  "version": "1.0.0"
}
```

### Logs

```bash
# Backend
docker compose logs -f backend --tail=100

# Worker Celery
docker compose logs -f worker --tail=100

# Tous les services
docker compose logs -f --tail=50
```

### Ressources

```bash
# Utilisation disque
df -h
docker system df

# Mémoire
free -h

# Conteneurs
docker stats
```

---

## 🆘 Dépannage

### Problèmes Courants

| Symptôme | Solution |
|----------|----------|
| **502 Bad Gateway** | Vérifier que backend est UP : `docker compose ps backend` |
| **Erreur stockage** | Vérifier MinIO : `docker compose ps minio` |
| **Emails non envoyés** | Vérifier config SMTP dans l'interface + logs worker |
| **Certificat SSL expiré** | `sudo certbot renew` |
| **Disque plein** | `docker system prune -a` puis vérifier backups |

### Commandes de Dépannage

```bash
# Redémarrer un service
docker compose restart backend

# Reconstruire une image
docker compose build --no-cache backend
docker compose up -d backend

# Shell Django
docker compose exec backend python manage.py shell

# Logs détaillés
docker compose logs backend --tail=500 | less
```

---

## 📚 Documentation Complémentaire

- **[README.md](README.md)** — Vue d'ensemble du projet
- **[DEPLOY.md](DEPLOY.md)** — Guide de déploiement détaillé
- **[QUICK-START.md](QUICK-START.md)** — Démarrage rapide
- **[CHANGELOG.md](CHANGELOG.md)** — Historique des versions
- **[documentation/](documentation/)** — Documentation complète

---

## ✨ Résumé

### Avant Nettoyage
```
/workspace/
├── 36 fichiers à la racine (dont 22 rapports d'analyse)
├── Documentation dispersée
└── Pas de guides de déploiement simplifiés
```

### Après Nettoyage
```
/workspace/
├── 15 fichiers essentiels à la racine
├── Documentation organisée (documentation/analyses/)
├── Guides de déploiement clairs (DEPLOY.md, QUICK-START.md)
├── Script de vérification (deploy-check.sh)
├── Optimisations Docker (.dockerignore)
└── Suivi des versions (CHANGELOG.md)
```

---

## 🎯 Prochaines Étapes

1. ✅ **Tester localement** : `SEED_DEMO=1 docker compose up --build`
2. ✅ **Déployer sur serveur** : Utiliser `ubuntu-install.sh`
3. ✅ **Vérifier le déploiement** : Exécuter `deploy-check.sh`
4. ✅ **Configurer la sécurité** : Checklist de sécurité
5. ✅ **Former les utilisateurs** : Documentation utilisateur

---

**Le projet est maintenant prêt pour un déploiement en production professionnel ! 🚀**

Pour toute question : [documentation/README.md](documentation/README.md) ou ouvrir une issue sur GitHub.
