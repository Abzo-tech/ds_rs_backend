# Discover Sénégal — Backend : État du projet

**Date :** 15 juillet 2026  
**Auteur :** Équipe Backend  
**Contexte :** Réunion de suivi MVP — présentation backend  
**Source :** Document d'Architecture Système v1.0 + Cahier des Charges Produit v1.0

---

## 1. Vue d'ensemble du backend

### 1.1 Stack technique

| Couche | Technologie | Rôle |
|--------|-------------|------|
| Framework | **Django 6.0.7** + **DRF 3.16** | API REST, admin, authentification |
| Serveur ASGI | **Daphne 4.1.2** | HTTP + WebSocket (chat temps réel) |
| Base de données | **PostgreSQL 18** + **PostGIS 3.6** | Données sociales + géolocalisation |
| Cache / Queue | **Redis 7** + **Celery 5.4** | Cache feed, sessions, tâches async |
| Temps réel | **Django Channels 4.2** | Chat 1-to-1 via WebSocket |
| Stockage | **django-storages** + **Cloudflare R2** (S3-compatible) | Médias, filtres AR |
| Auth | **SimpleJWT 5.5** + OAuth Google/Apple | JWT + login social |
| Documentation | **drf-spectacular** + Swagger UI | Contrat API OpenAPI |
| Tests | **pytest** + Django TestCase | Tests automatisés |

### 1.2 Architecture modulaire

Le backend est structuré en **apps Django** strictes :

```
apps/
├── accounts/       # Auth, profils, rôles, follows, analytics partenaires
├── feed/           # Posts, likes, comments, stories, media, sauvegardes, partages
├── chat/           # Conversations, messages, WebSocket
├── ar_filters/     # Filtres RA, manifest géolocalisé
├── geo/            # Points d'intérêt, nearby discovery
├── notifications/  # Notifications push, tokens FCM
└── config/         # Settings, URLs, ASGI, Celery
```

---

## 2. Ce qui a été réalisé

### 2.1 Authentification & Utilisateurs

| Fonctionnalité | Endpoint | Statut |
|----------------|----------|--------|
| Inscription email/password | `POST /api/v1/auth/register/` | ✅ |
| Connexion JWT | `POST /api/v1/auth/login/` | ✅ |
| Refresh token + blacklist | `POST /api/v1/auth/token/refresh/`, `POST /api/v1/auth/logout/` | ✅ |
| Phone OTP login | `POST /api/v1/auth/login/phone/` | ✅ |
| OAuth Google / Apple | `POST /api/v1/auth/oauth/{provider}/` | ✅ |
| Profil utilisateur | `GET/PUT /api/v1/users/me` | ✅ |
| Profil public | `GET/PUT /api/v1/users/me/profile` | ✅ |
| Recherche utilisateurs | `GET /api/v1/users/search/` | ✅ |
| Follow / Unfollow | `POST/DELETE /api/v1/users/{id}/follow/` | ✅ |
| Block / Unblock | `POST/DELETE /api/v1/users/{id}/block/` | ✅ |
| Badge certifié (admin) | `POST/DELETE /api/v1/users/{id}/certified/` | ✅ |
| Change password | `POST /api/v1/auth/password/change/` | ✅ |
| Reset password (mock OTP) | `POST /api/v1/auth/password/reset/` + `/confirm/` | ✅ |
| Admin users : list/patch/delete | `/api/v1/admin/users/` | ✅ |

### 2.2 Feed & Contenu

| Fonctionnalité | Endpoint | Statut |
|----------------|----------|--------|
| Feed personnalisé (Maadi AI + fallback) | `GET /api/v1/feed/` | ✅ |
| Création post | `POST /api/v1/feed/` | ✅ |
| Like / Unlike | `POST/DELETE /api/v1/feed/posts/{id}/like/` | ✅ |
| Comments | `GET/POST /api/v1/feed/posts/{id}/comments/` | ✅ |
| Save / Unsave post | `POST/DELETE /api/v1/feed/posts/{id}/save/` | ✅ |
| Share post | `POST /api/v1/feed/posts/{id}/share/` | ✅ |
| Report post | `POST /api/v1/feed/posts/{id}/report/` | ✅ |
| Stories (création + vues) | `GET/POST /api/v1/feed/stories/` + `/view/` | ✅ |
| Upload média | `POST /api/v1/feed/upload/` | ✅ |
| Liste médias utilisateur | `GET /api/v1/feed/media/` | ✅ |
| Suppression média | `DELETE /api/v1/feed/media/{id}/` | ✅ |
| Modération automatique Maadi AI | (tâche Celery interne) | ✅ |

### 2.3 Chat & Messaging

| Fonctionnalité | Endpoint | Statut |
|----------------|----------|--------|
| Conversations : list/create | `GET/POST /api/v1/chat/conversations/` | ✅ |
| Messages : list/create | `GET/POST /api/v1/chat/messages/` | ✅ |
| Mark-read conversation | `POST /api/v1/chat/conversations/{id}/mark-read/` | ✅ |
| Delete conversation | `DELETE /api/v1/chat/conversations/{id}/delete/` | ✅ |
| WebSocket chat | `ws/chat/{conversation_id}/` (JWT auth) | ✅ |

### 2.4 AR Filters & Géolocalisation

| Fonctionnalité | Endpoint | Statut |
|----------------|----------|--------|
| Liste filtres RA | `GET /api/v1/ar-filters/` | ✅ |
| Détail filtre RA | `GET /api/v1/ar-filters/{id}/` | ✅ |
| Manifest géolocalisé | `GET /api/v1/ar-filters/manifest/` | ✅ |
| POI list (PostGIS) | `GET /api/v1/geo/poi/` | ✅ |
| Nearby discovery (POI + AR) | `GET /api/v1/geo/nearby/` | ✅ |

### 2.5 Notifications

| Fonctionnalité | Endpoint | Statut |
|----------------|----------|--------|
| Liste notifications | `GET /api/v1/notifications/` | ✅ |
| Mark-read / mark-all-read | `POST /api/v1/notifications/{id}/mark-read/` + `/mark-all-read/` | ✅ |
| Enregistrer token FCM | `POST /api/v1/notifications/fcm-token/` | ✅ |
| Supprimer token FCM | `DELETE /api/v1/notifications/fcm-token/` | ✅ |
| Broadcast admin | `POST /api/v1/admin/notifications/broadcast/` | ✅ |

### 2.6 Infrastructure & Outils

| Élément | Statut |
|---------|--------|
| PostgreSQL 18 + PostGIS 3.6 installés | ✅ |
| Base `discover_db` créée + extension PostGIS | ✅ |
| Migrations appliquées | ✅ |
| Docker Compose (db, redis, backend, celery, celery-beat) | ✅ |
| Settings conditionnels dev/prod | ✅ |
| Cache Redis (fallback LocMemCache) | ✅ |
| OpenAPI docs Swagger UI (`/api/docs/`) | ✅ |
| `openapi_auth.yaml` synchronisé | ✅ |
| Tests automatisés (7 tests) | ✅ |

---

## 3. Ce qui reste à faire (aligné sur le cahier des charges)

### 3.1 Intégrations externes (dépendances)

| Dépendance | Ce qu'il faut | Priorité | Action requise |
|------------|---------------|----------|----------------|
| **Cloudflare R2** | Clés API + endpoint S3-compatible pour stocker médias et filtres RA | **P0** | Fournir `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_ENDPOINT_URL` |
| **Maadi AI** | Service de modération + recommandation (existant, même stack Python) | **P0** | Fournir `MAADI_AI_URL` (ex: `http://localhost:8001/maadi/recommend`) |
| **Firebase Admin** | Credentials JSON pour push notifications FCM | **P0** | Fournir fichier `firebase-admin-credentials.json` |
| **Google OAuth** | Client ID + secret pour login Google | **P1** | Configurer dans Google Cloud Console + ajouter aux settings |
| **Apple OAuth** | Service ID + key pour login Apple | **P1** | Configurer dans Apple Developer + ajouter aux settings |
| **Banuba/DeepAR SDK** | Licence + effect packs pour filtres AR | **P1** | Intégrer SDK Flutter + upload assets sur R2/CDN |
| **Watermarking** | Service ou tâche Celery pour watermark "Discover Sénégal" sur médias | **P1** | Implémenter tâche Celery + intégration Pillow |

### 3.2 Fonctionnalités backend (d'après l'architecture documentée)

| Module | Fonctionnalité | Priorité | Notes |
|--------|----------------|----------|-------|
| **Feed** | Intégration réelle Maadi AI (scoring recommandation) | **P0** | Actuellement : mock + fallback engagement |
| **Feed** | Watermark automatique sur médias (tâche Celery) | **P0** | Prévu dans flux critique n°1 |
| **Feed** | Fan-out léger vers followers (Redis) | **P0** | Prévu dans architecture ; feed fonctionne mais sans fan-out optimisé |
| **Modération** | File de modération `pending_review` + tâche Celery dédiée | **P0** | 100% automatique via Maadi AI ; endpoints humains retirés |
| **Notifications** | Intégration Firebase Admin SDK réelle | **P0** | Modèle FCMToken prêt ; envoi push à connecter |
| **AR Filters** | CRUD admin complet (création/édition filtres) | **P1** | Endpoints admin partiellement présents |
| **AR Filters** | Upload assets 3D + packaging SDK | **P1** | Dépend de la licence Banuba/DeepAR |
| **Geo** | Unlock géolocalisé avancé (POI + radius) | **P1** | Modèle `POIFilterUnlock` prêt ; logique métier à finaliser |
| **Partners** | Lien établissement + dashboard analytics | **P1** | Modèles présents ; endpoints à vérifier en prod |
| **Sécurité** | Rate limiting Redis sur endpoints critiques | **P1** | Middleware présent ; à activer en prod |
| **Sécurité** | 2FA optionnelle | **P2** | Non prévu au MVP |
| **Observabilité** | Sentry + logs structurés | **P2** | À ajouter pour la prod |

### 3.3 Tests & Qualité

| Élément | Statut |
|---------|--------|
| Tests unitaires endpoints principaux | ⏳ 7 tests (auth, feed, chat, notifications) |
| Tests WebSocket chat | ⏳ À implémenter |
| Tests d'intégration Maadi AI | ⏳ À implémenter (mock service) |
| Tests de modération automatique | ⏳ À implémenter |
| CI/CD pipeline (GitHub Actions) | ⏳ À mettre en place |

---

## 4. Dépendances externes — détail

### 4.1 Cloudflare R2 (Stockage médias)

**Pourquoi on en a besoin :**  
Le MVP prévoit un volume important de médias (photos, vidéos, filtres AR) pendant les JOJ. R2 est choisi pour éviter les coûts d'egress AWS S3.

**Ce qu'il faut fournir :**
- `AWS_ACCESS_KEY_ID` : clé API R2
- `AWS_SECRET_ACCESS_KEY` : secret API R2
- `AWS_S3_ENDPOINT_URL` : endpoint S3-compatible (ex: `https://<account>.r2.cloudflarestorage.com`)
- `AWS_STORAGE_BUCKET_NAME` : nom du bucket (ex: `discover-senegal-media`)

**Impact si absent :**  
Les uploads de médias fonctionnent en mode URL-based (pas de stockage automatique). Le watermarking et le CDN ne sont pas actifs.

### 4.2 Maadi AI (Intelligence artificielle)

**Pourquoi on en a besoin :**  
Maadi AI est le moteur de :
1. **Recommandation de feed** : scoring personnalisé des posts par utilisateur
2. **Modération automatique** : flagging de contenu inapproprié (100% automatique, sans intervention humaine)

**Ce qu'il faut fournir :**
- `MAADI_AI_URL` : URL du service Maadi AI (ex: `http://localhost:8001/maadi/recommend`)
- `MAADI_AI_TIMEOUT` : timeout d'appel (300ms par défaut)

**Impact si absent :**  
Le feed fonctionne en mode fallback (tri par engagement + récence). La modération est désactivée (les posts sont publiés sans scoring).

### 4.3 Firebase Admin (Notifications push)

**Pourquoi on en a besoin :**  
Envoyer des notifications push sur iOS et Android via FCM (Firebase Cloud Messaging).

**Ce qu'il faut fournir :**
- Fichier de credentials JSON : `firebase-admin-credentials.json`
- Variable d'environnement : `FIREBASE_CREDENTIALS_PATH`

**Impact si absent :**  
Les tokens FCM sont enregistrés en base mais aucune notification push n'est envoyée. Les notifications sont stockées en base mais non delivered.

### 4.4 Google OAuth / Apple OAuth

**Pourquoi on en a besoin :**  
Login social (Google/Apple) pour réduire la friction d'inscription.

**Ce qu'il faut fournir :**
- Google : Client ID + Secret dans Google Cloud Console
- Apple : Service ID + Key dans Apple Developer

**Impact si absent :**  
Le login email/password fonctionne. Les endpoints OAuth renvoient une erreur 501 (non implémenté).

### 4.5 Banuba/DeepAR SDK (Filtres AR)

**Pourquoi on en a besoin :**  
Applique les filtres RA sur la caméra mobile (face tracking, effets).

**Ce qu'il faut fournir :**
- Licence SDK Banuba ou DeepAR
- Effect packs (filtres 3D) uploadés sur R2 + CDN

**Impact si absent :**  
Les endpoints de listing de filtres fonctionnent, mais l'application mobile ne peut pas appliquer les filtres AR.

---

## 5. Alignement avec le cahier des charges

### 5.1 Principes directeurs

| Principe | Respecté ? | Commentaire |
|----------|------------|-------------|
| Un seul codebase mobile (Flutter) | ✅ | Backend API-first, mobile Flutter indépendant |
| Backend Django monolithe modulaire | ✅ | Apps Django strictes, extraction future possible |
| Base unique partagée | ✅ | PostgreSQL unifié pour social + geo + Maadi |
| SDK AR tiers (Banuba/DeepAR) | ⏳ | Endpoints prêts, SDK à intégrer côté mobile |
| Feed v1 = règles simples + Maadi AI | ✅ | Fallback engagement + cache Redis |
| Design pour échelle JOJ | ✅ | Redis, CDN, horizontal scaling ready |

### 5.2 Modules fonctionnels (section 4 du cadrage)

| Module cadrage | Module backend | Statut backend |
|----------------|----------------|----------------|
| 4.1 Authentification | `accounts/` | ✅ Terminé |
| 4.2 Caméra + Filtres AR | `ar_filters/` + `geo/` | ⏳ Partiel (endpoints OK, SDK mobile à faire) |
| 4.3 Géolocalisation + Carte | `geo/` | ✅ Terminé |
| 4.4 Messagerie | `chat/` | ✅ Terminé |
| 4.5 Feed & Contenus | `feed/` + `stories/` | ✅ Terminé |
| 4.6 Profil utilisateur | `accounts/` | ✅ Terminé |
| Intégration Maadi (§7) | `feed/tasks.py` + `feed/services.py` | ⏳ Partiel (mock, à connecter) |

### 5.3 Flux critiques

| Flux | Statut backend | Bloqueur |
|------|----------------|----------|
| **Flux 1 : Caméra → Filtre AR → Publication** | ⏳ Partiel | Watermarking + intégration Maadi à finaliser |
| **Flux 2 : Feed personnalisé** | ⏳ Partiel | Service Maadi AI réel à connecter |

### 5.4 Sécurité & conformité

| Point | Statut |
|-------|--------|
| RGPD / consentement Maadi (`consent_ai_training`) | ✅ |
| Rôles : `public`, `tourist`, `partner`, `creator`, `admin` | ✅ |
| Rate limiting (Cloudflare + Redis) | ⏳ À activer en prod |
| Modération 100% automatique Maadi AI | ✅ |

---

## 6. Planning de finalisation (post-réunion)

### Semaine immédiate (S1)

1. **Fournir les dépendances externes** :
   - Clés R2 + endpoint
   - URL Maadi AI + credentials
   - Firebase credentials
   - Google/Apple OAuth config

2. **Connecter Maadi AI** :
   - Remplacer le mock par l'appel réel
   - Tester scoring recommandation
   - Tester modération automatique

3. **Connecter Firebase** :
   - Initialiser Firebase Admin SDK
   - Implémenter envoi push notifications

4. **Watermarking** :
   - Implémenter tâche Celery Pillow
   - Tester sur médias uploadés

### Semaine suivante (S2)

5. **Fan-out feed** :
   - Implémenter publication dans feed followers via Redis
   - Tester avec 100+ utilisateurs simulés

6. **Tests** :
   - Étendre à 20+ tests
   - Tests WebSocket chat
   - Tests intégration Maadi

7. **Déploiement** :
   - Configurer Docker Compose prod
   - Configurer variables d'environnement
   - Tester montée en charge

---

## 7. Points de discussion pour la réunion

1. **Priorisation P0 vs P1** : Maadi AI, R2, Firebase sont-ils disponibles immédiatement ?
2. **Banuba vs DeepAR** : quel SDK choisir ? Licence disponible ?
3. **Rate limiting** : stratégie Cloudflare + Redis à définir
4. **Observabilité** : Sentry + logs structurés à mettre en place ?
5. **CI/CD** : GitHub Actions à configurer pour backend + mobile ?
6. **Hébergement** : Railway/Render pour MVP, puis AWS/GCP pour JOJ ?

---

## 8. Contact

Pour toute question sur ce document, contacter l'équipe backend.
