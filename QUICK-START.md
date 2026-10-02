# ⚡ Quick Start - FinFlow

Guide de démarrage ultra-rapide pour tester FinFlow localement en moins de 5 minutes.

## 🎯 Méthode 1 : Docker Compose (Recommandé)

### Prérequis
- Docker Desktop installé ([Télécharger](https://www.docker.com/products/docker-desktop))

### En 3 Commandes

```bash
# 1. Cloner le projet
git clone https://github.com/Bouma-J/FinFlow.git
cd FinFlow

# 2. Démarrer avec données de démonstration
SEED_DEMO=1 docker compose up --build

# 3. Ouvrir dans le navigateur
# http://localhost:8080
```

**C'est tout !** ✨

### Comptes de Démonstration

| Utilisateur | Mot de passe | Rôle |
|------------|--------------|------|
| `group_admin` | `FinFlow2026!` | Administrateur Groupe |
| `fil01_admin` | `FinFlow2026!` | Administrateur Filiale |

---

## 🖥️ Méthode 2 : Installation Locale (Développeurs)

### Prérequis
- Python 3.12+
- Node.js 20+

### Backend

```bash
# 1. Environnement virtuel
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 2. Installer dépendances
pip install -r backend/requirements/dev.txt

# 3. Configurer
cp backend/.env.example backend/.env

# 4. Base de données
python backend/manage.py migrate

# 5. Données de démo
python backend/manage.py seed_demo

# 6. Démarrer serveur
python backend/manage.py runserver
```

**Backend prêt:** http://127.0.0.1:8000

### Frontend

```bash
# Dans un autre terminal
cd frontend

# 1. Installer dépendances
npm install

# 2. Démarrer dev server
npm run dev
```

**Frontend prêt:** http://localhost:5173

---

## 📊 Points d'Accès

### Application
- **Frontend:** http://localhost:8080 (Docker) ou http://localhost:5173 (local)
- **Connexion:** `group_admin` / `FinFlow2026!`

### API
- **Base URL:** http://localhost:8080/api/v1/
- **Documentation:** http://localhost:8080/api/docs/
- **Schéma OpenAPI:** http://localhost:8080/api/schema/

### Administration
- **Django Admin:** http://localhost:8080/django-admin/
- **MinIO Console:** http://localhost:9001 (`minioadmin` / `minioadmin`)

---

## ✅ Vérification Rapide

```bash
# Tester l'API
curl http://localhost:8080/api/v1/health/

# Ou utiliser le script de vérification
bash deploy-check.sh http://localhost:8080
```

**Réponse attendue:**
```json
{
  "status": "ok",
  "ready": true,
  "database": "ok",
  "storage": "ok",
  "cache": "ok"
}
```

---

## 🔄 Commandes Utiles

### Docker Compose

```bash
# Démarrer en arrière-plan
docker compose up -d

# Voir les logs
docker compose logs -f backend

# Arrêter
docker compose down

# Arrêter et supprimer volumes
docker compose down -v

# Reconstruire après modification
docker compose up --build
```

### Django (Backend)

```bash
# Créer superutilisateur
python backend/manage.py createsuperuser

# Shell Django
python backend/manage.py shell

# Migrations
python backend/manage.py makemigrations
python backend/manage.py migrate

# Tests
pytest backend
```

### Frontend

```bash
cd frontend

# Build production
npm run build

# Lint
npm run lint

# Format
npm run format
```

---

## 🐛 Problèmes Courants

### Port déjà utilisé

**Erreur:** `Bind for 0.0.0.0:8080 failed: port is already allocated`

**Solution:**
```bash
# Changer le port dans docker-compose.yml
# Modifier la ligne: "8080:80" → "8081:80"
```

### Erreur de connexion base de données

**Solution:**
```bash
# Attendre que PostgreSQL soit prêt
docker compose logs db

# Ou supprimer et recréer
docker compose down -v
docker compose up --build
```

### Erreur MinIO

**Solution:**
```bash
# Vérifier que MinIO est démarré
docker compose ps minio

# Recréer le bucket
docker compose exec backend python manage.py shell
# >>> from apps.documents.storage import ensure_bucket_exists
# >>> ensure_bucket_exists()
```

---

## 🎓 Prochaines Étapes

1. **Explorer l'interface:** Créer une filiale, un produit, un client
2. **Tester un workflow:** Créer et soumettre un dossier de crédit
3. **Consulter la doc:** [Documentation complète](documentation/README.md)
4. **Déployer:** [Guide de déploiement](DEPLOY.md)

---

## 📚 Ressources

- **Guide de Déploiement:** [DEPLOY.md](DEPLOY.md)
- **Documentation Technique:** [documentation/](documentation/)
- **Architecture:** [documentation/02-architecture-technique.md](documentation/02-architecture-technique.md)
- **Configuration:** [documentation/05-configuration.md](documentation/05-configuration.md)

---

**Besoin d'aide ?** Ouvrez une issue sur [GitHub](https://github.com/Bouma-J/FinFlow/issues)

**FIN_FLOW** — *Démarrez en moins de 5 minutes* ⚡
