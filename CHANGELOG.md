# Changelog - FinFlow

Toutes les modifications notables du projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [Non publié]

### Ajouté
- Guide de déploiement rapide (`DEPLOY.md`) avec instructions simplifiées
- Guide de démarrage rapide (`QUICK-START.md`) pour test local en 5 minutes
- Script de vérification de déploiement (`deploy-check.sh`)
- Règles de visites terrain conditionnelles par type de client et montant
- Support des photos dans les visites terrain (stockage MinIO)
- Nouveau rôle "Administrateur de crédit" avec séparation des devoirs (SoD)
- Mode d'analyse financière détaillée période par période
- Interface d'administration des règles de visites terrain
- Amélioration du `.gitignore` avec exclusion des backups et coverage
- Fichier `.dockerignore` pour optimiser les builds Docker

### Modifié
- Réorganisation des fichiers de documentation (analyses déplacées dans `documentation/analyses/`)
- Cahier des charges déplacé vers `documentation/cahier-des-charges.txt`
- README.md enrichi avec liens vers guides de démarrage rapide
- Migration 0034: correction des erreurs de syntaxe et références

### Corrigé
- Erreurs de syntaxe dans migration `0034_field_visit_rules.py`
- Références de dépendances migration (common.tenant → tenants.tenant)
- Imports manquants dans le frontend (AlertTriangle de lucide-react)

### Nettoyé
- 22 fichiers d'analyse/rapport déplacés hors de la racine
- Réorganisation de la structure pour déploiement en production
- Documentation de développement isolée de la documentation utilisateur

---

## [1.0.0] - 2026-09-XX

### Première Version Majeure

#### Modules Métier
- Gestion multi-tenants (filiales/agences)
- Gestion des clients (particuliers, professionnels, entreprises)
- Workflow de dossiers de crédit configurable
- Moteur d'approbation avec circuits paramétrables
- Gestion documentaire (GED) avec MinIO S3
- Gestion des garanties et sureties
- Module de recouvrement et contentieux
- Génération de contrats (DOCX/XLSX)
- Connecteurs Core Banking (idempotence, rejeu)
- Reporting consolidé multi-axes

#### Architecture Technique
- Backend: Django 5.1 + Django REST Framework + Python 3.12
- Frontend: React 18 + TypeScript + Vite
- Base de données: PostgreSQL 16
- Cache et broker: Redis 7
- Stockage: MinIO (compatible S3)
- Workers asynchrones: Celery
- Authentification: JWT + MFA TOTP
- RBAC complet avec délégations de pouvoirs

#### Déploiement
- Docker Compose pour développement et production
- Scripts d'installation automatisée Ubuntu
- Support HTTPS avec Let's Encrypt
- Sauvegardes automatiques
- Monitoring et health checks
- CI/CD GitHub Actions

#### Sécurité
- Chiffrement au repos des secrets (Fernet)
- Piste d'audit inaltérable
- Séparation des devoirs (SoD)
- Protection CSRF/XSS
- Rate limiting

---

## Notes de Version

### Migration depuis Développement vers Production

Lors de la mise en production:

1. **Variables d'environnement**
   - Générer de nouvelles clés: `DJANGO_SECRET_KEY`, `FIELD_ENCRYPTION_KEY`
   - Configurer les mots de passe: `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `MINIO_ROOT_PASSWORD`
   - Définir les domaines: `DJANGO_ALLOWED_HOSTS`, `DJANGO_CORS_ALLOWED_ORIGINS`
   - Désactiver le mode debug: `DJANGO_DEBUG=False`
   - Désactiver le seed: `SEED_DEMO=0`

2. **Sécurité**
   - Activer HTTPS: `DJANGO_SECURE_SSL_REDIRECT=True`
   - Configurer HSTS: `DJANGO_SECURE_HSTS_SECONDS=31536000`
   - Vérifier les certificats SMTP: `SMTP_SSL_VERIFY=1`

3. **Sauvegardes**
   - Configurer les sauvegardes automatiques (cron)
   - Tester la restauration d'un snapshot
   - Configurer la copie hors site si nécessaire

4. **Monitoring**
   - Configurer les alertes
   - Tester l'endpoint `/api/v1/health/`
   - Surveiller les logs Celery worker/beat

### Compatibilité

- **Python**: 3.12+
- **Node.js**: 20+
- **PostgreSQL**: 14+ (recommandé: 16)
- **Redis**: 7+
- **Docker**: 24+ avec Compose V2

### Support

- Documentation: [documentation/README.md](documentation/README.md)
- Guide de déploiement: [DEPLOY.md](DEPLOY.md)
- Quick Start: [QUICK-START.md](QUICK-START.md)
- Issues GitHub: https://github.com/Bouma-J/FinFlow/issues
