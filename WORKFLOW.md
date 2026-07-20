# Workflow - Équipe Backend (discover_senegal_backend)

## Règles
- On travaille **uniquement** dans le dossier `discover_senegal_backend/`.
- On ne touche **jamais** aux fichiers/dossiers extérieurs (mobile, docs) : ce sont d'autres équipes.
- On ne travaille **jamais** directement sur `main` ni sur `dev`.
- Toute fonctionnalité se fait sur une branche `feature` (ex: `ds_backend_v1`).

## Cycle de vie d'une fonctionnalité

### 1. Démarrer une feature (depuis dev à jour)
```bash
git checkout dev
git pull origin dev
git checkout -b ds_backend_v1        # nom de la feature
```

### 2. Travailler dans le backend
```bash
cd discover_senegal_backend
# ... coder ...
git add discover_senegal_backend
git commit -m "feat: description de la fonctionnalité"
```

### 3. Terminer la feature → intégrer dans dev
```bash
git checkout dev
git pull origin dev                  # récupérer le travail de l'équipe
git merge ds_backend_v1              # fusionner la feature dans dev
git push origin dev                  # publier dev pour l'équipe
```

### 4. Nettoyage (optionnel)
```bash
git branch -d ds_backend_v1
```

## Rappels sécurité
- `venv/`, `.env`, `secrets/` sont ignorés (ne jamais les committer).
- Partager `secrets/firebase-admin-credentials.json` par un canal privé, pas via Git.
- Toujours `git pull origin dev` AVANT de merger/pusher pour éviter les conflits.

## Migrations Django
À chaque modification de modèle, générer et appliquer les migrations (nécessite PostgreSQL + PostGIS) :
```bash
python manage.py makemigrations
python manage.py migrate
```
Les migrations sont versionnées dans `apps/<app>/migrations/`.

## Routes de modération (admin)
- `POST /api/v1/feed/moderation/post/<id>/<approve|reject>/`
- `POST /api/v1/feed/moderation/comment/<id>/<approve|reject>/`
- `GET  /api/v1/feed/moderation/queue/` (posts en attente)
- `GET  /api/v1/feed/moderation/comments/queue/` (commentaires en attente)

## Consentement Maadi AI
- `POST /api/v1/users/me/consent/`  body: `{"consent_ai_training": true|false}`
- Variable d'env `MAADI_MOCK` (True/False) : active/désactive le mock de modération Maadi.

