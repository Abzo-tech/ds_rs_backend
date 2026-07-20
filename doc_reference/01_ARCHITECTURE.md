# Discover Sénégal — Réseau Social Mobile
## Document d'Architecture Système — MVP

**Version 1.0 · Rédigé par : CTO / Lead Engineering**
**Contexte source :** Document de Cadrage Produit v1.0 (Juin 2026) + Document Product Designer v1.0
**Contrainte majeure :** MVP livrable et testable en 45 jours, prêt pour JOJ Dakar 2026 (600 000+ visiteurs attendus)

---

## 1. Principes directeurs de l'architecture

| Principe | Raison |
|---|---|
| **Un seul codebase mobile** (Flutter) | Impossible de tenir 2 équipes natives (iOS + Android) en 45 jours. Flutter compile nativement (pas de bridge JS), ce qui donne de meilleures performances caméra/AR — le point le plus critique du produit. Choix aligné avec la compétence la plus forte de l'équipe |
| **Backend en Django**, pas de microservices au MVP | Alignement avec Maadi AI (déjà en Python) — mutualisation de compétences et d'outillage entre l'équipe social et l'équipe IA. Django REST Framework + admin intégré permettent d'aller vite sur les CRUD en 45 jours. Le monolithe est découpé en apps Django strictes pour permettre une extraction future sans réécriture |
| **Base de données unique partagée** (réservation + social + Maadi) | Exigence explicite du cadrage produit : "compte unique inter-plateformes" |
| **SDK AR tiers** (Banuba ou DeepAR) plutôt que développement AR maison | OTA obligatoire sans passage App Store — ces SDK le font nativement. Développer un moteur AR facial tracking en 45 jours est hors de portée |
| **Feed v1 = règles simples, pas de ML maison** | Maadi AI fournit déjà l'intelligence de recommandation via API. Le backend social ne réinvente pas l'algorithme, il consomme le score de Maadi et retombe sur un fallback chronologique/engagement si Maadi ne répond pas |
| **Design pour l'échelle JOJ dès le MVP**, sans sur-ingénierie | Cache Redis, CDN pour médias/filtres, et une architecture qui supporte l'ajout de read-replicas Postgres sans changement de code applicatif |

---

## 2. Vue d'ensemble du système

```
                          ┌────────────────────────────────────────────┐
                          │              CLIENTS MOBILES                │
                          │   Flutter (Dart) — iOS & Android            │
                          │   - Module Auth, Caméra/AR, Feed, Carte,    │
                          │     Messagerie, Profil                      │
                          └───────────────┬──────────────────────────────┘
                                          │ HTTPS (REST) + WSS (temps réel)
                                          ▼
                          ┌────────────────────────────────────────────┐
                          │            API GATEWAY / CDN EDGE           │
                          │   Cloudflare (CDN + WAF + rate limiting)    │
                          └───────────────┬──────────────────────────────┘
                                          ▼
        ┌───────────────────────────────────────────────────────────────────┐
        │              BACKEND — MONOLITHE MODULAIRE (Django + DRF)          │
        │           servi en ASGI (Django Channels) via Daphne/Uvicorn        │
        │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────────┐  │
        │  │   Auth     │ │   Users/   │ │   Feed &   │ │   Filtres AR &     │  │
        │  │  (JWT +    │ │  Profils   │ │  Stories   │ │  Géolocalisation   │  │
        │  │  OAuth)    │ │            │ │            │ │  (unlock rules)    │  │
        │  └───────────┘ └───────────┘ └───────────┘ └───────────────────┘  │
        │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────────┐  │
        │  │ Messagerie │ │Notifications│ │ Modération │ │ Intégration Maadi  │  │
        │  │ (Channels  │ │   (FCM)    │ │  (Celery)  │ │ AI (client HTTP,   │  │
        │  │ consumers) │ │            │ │            │ │ même langage !)    │  │
        │  └───────────┘ └───────────┘ └───────────┘ └───────────────────┘  │
        └──────┬───────────────┬──────────────┬───────────────┬─────────────┘
               ▼               ▼              ▼               ▼
        ┌───────────┐  ┌─────────────┐  ┌───────────┐  ┌──────────────────┐
        │ PostgreSQL │  │    Redis     │  │  S3 / R2   │  │   Maadi AI       │
        │ (données   │  │ (cache,      │  │ (médias:   │  │   (service       │
        │  unifiées) │  │  sessions,   │  │  photos,   │  │   externe déjà    │
        │            │  │  feed rank,  │  │  vidéos,   │  │   existant,       │
        │            │  │  Celery      │  │  packs     │  │   appelé en REST  │
        │            │  │  broker,     │  │  filtres)  │  │   — même stack    │
        │            │  │  Channels    │  │            │  │   Python, appels   │
        │            │  │  layer)      │  │            │  │   internes         │
        │            │  │              │  │            │  │   facilités)      │
        └───────────┘  └─────────────┘  └───────────┘  └──────────────────┘
                                              │
                                              ▼
                                     ┌──────────────────┐
                                     │   CDN Filtres AR   │
                                     │  (Banuba/DeepAR    │
                                     │  effect packs, OTA)│
                                     └──────────────────┘
```

---

## 3. Choix technologiques détaillés

### 3.1 Mobile
| Composant | Choix | Justification |
|---|---|---|
| Framework | **Flutter (Dart)** | Un seul codebase, compilation native (pas de bridge JS) → meilleure performance caméra/AR, aligné avec la compétence de l'équipe |
| État global | **Riverpod** | Standard moderne Flutter, testable, évite le boilerplate de Bloc pour un MVP |
| Navigation | **go_router** | Routing déclaratif officiel recommandé par l'équipe Flutter |
| AR / Filtres | **Banuba SDK** (ou DeepAR en alternative) — plugin Flutter officiel | Compatible ARKit/ARCore sous le capot, gestion native de l'OTA des effets, face tracking prêt à l'emploi |
| Caméra | **package `camera`** (officiel Flutter) | Intégration directe avec le plugin AR choisi |
| Cartes | **google_maps_flutter** | Standard, gratuit à cette échelle |
| Notifications push | **firebase_messaging** | Cross-platform, gratuit, intégration simple |
| Temps réel (chat) | **web_socket_channel** | Client WebSocket léger, compatible avec Django Channels côté serveur |
| i18n | **easy_localization** (FR/EN au MVP, WO préparé en V2) | Structure de traduction déjà prête pour le wolof |
| Distribution OTA du code Dart | **Shorebird** (optionnel, à évaluer) | Moins mature que l'OTA JS d'Expo — non bloquant : le vrai besoin OTA (les filtres) est couvert par le SDK AR, pas par le framework |

### 3.2 Backend
| Composant | Choix | Justification |
|---|---|---|
| Framework | **Django + Django REST Framework** | Alignement stack avec Maadi AI (Python) ; DRF + admin intégré = vélocité élevée en 45 jours |
| Serveur ASGI | **Daphne ou Uvicorn** (au lieu de WSGI classique) | Obligatoire pour faire tourner Django Channels (WebSocket du chat) à côté du REST classique |
| Base de données | **PostgreSQL 16** | Relationnel, transactionnel, extension PostGIS (via `django.contrib.gis`) pour la géolocalisation native |
| ORM | **Django ORM** | Migrations intégrées nativement (`makemigrations`/`migrate`), pas de dépendance supplémentaire |
| Cache / Queue | **Redis + Celery** | Cache du feed, sessions, rate-limiting, jobs asynchrones (notifications, modération, watermarking) |
| Temps réel | **Django Channels** (consumers WebSocket) | Chat 1-to-1 synchronisé web/mobile, même serveur que le REST |
| Stockage médias | **django-storages + Cloudflare R2 (S3-compatible)** | Pas de coûts de sortie (egress) contrairement à AWS S3, important vu le volume JOJ |
| Auth | **djangorestframework-simplejwt + django-allauth** (OAuth Google/Apple) | Compte unique inter-plateformes, stateless, scalable horizontalement |
| Recherche/Feed | **PostgreSQL + Redis Sorted Sets** pour le ranking | Suffisant au MVP ; migration vers Elasticsearch/OpenSearch si besoin de recherche full-text avancée en V2 |

### 3.3 Infrastructure
| Composant | Choix | Justification |
|---|---|---|
| Hébergement | **Cloud managé (Railway/Render pour le MVP, migration AWS/GCP pour la charge JOJ)** | Vitesse de mise en place ; conteneurs Docker (Django ASGI + worker Celery séparé) portables donc migration sans réécriture |
| CDN | **Cloudflare** | CDN médias + edge cache + protection DDoS pour l'afflux JOJ |
| CI/CD | **GitHub Actions** | Build, tests, déploiement mobile (Codemagic ou Fastlane pour Flutter) et backend (Docker) |
| Observabilité | **Sentry (erreurs) + logs structurés (structlog)** | Minimum viable pour un MVP, alertes sur les blocages critiques (règle des 48h du cadrage produit) |

---

## 4. Modules fonctionnels (mapping avec le cadrage produit §4)

| Module cadrage produit | Module backend | Module mobile |
|---|---|---|
| 4.1 Authentification | apps `accounts/` | `features/auth/` |
| 4.2 Caméra + Filtres AR | app `filters/` | `features/camera/`, SDK Banuba intégré |
| 4.3 Géolocalisation + Carte | app `geo/` | `features/map/` |
| 4.4 Messagerie | app `messaging/` (Channels consumers) | `features/messaging/` |
| 4.5 Feed & Contenus | apps `feed/`, `stories/`, `moderation/` | `features/feed/`, `features/stories/` |
| 4.6 Profil utilisateur | apps `accounts/`, `partners/` | `features/profile/` |
| Intégration Maadi (§7) | app `maadi_integration/` (client HTTP vers le service Maadi existant, même stack Python) | Invisible dans l'UI — un seul toggle vers l'interface de discussion Maadi, comme précisé dans le doc designer |

---

## 5. Flux critique n°1 : Caméra → Filtre AR → Publication

```
1. Utilisateur ouvre l'app → accès caméra en 1 geste (écran d'accueil)
2. App mobile récupère le manifeste des filtres disponibles :
   GET /filters/manifest?lat=X&lng=Y
   → Backend croise la position GPS avec la table `poi_filter_unlocks`
   → Retourne : filtres globaux (toujours dispo) + filtres géolocalisés débloqués
3. SDK Banuba télécharge (ou lit depuis le cache local) les packs d'effets
   correspondants depuis le CDN — c'est le mécanisme OTA : aucun redéploiement
   d'app nécessaire pour ajouter/modifier un filtre
4. Utilisateur capture photo/vidéo (≤ 60s) avec le filtre appliqué en local
5. Upload du média vers /media/upload → stocké sur R2 via django-storages,
   watermark "Discover Sénégal" appliqué côté serveur (tâche Celery asynchrone)
6. Création du post : POST /posts { media_id, caption, filter_id, geo }
   (DRF ViewSet + serializer, validation métier dans le service layer)
7. Le post est inséré en base et poussé dans le feed des followers
   (fan-out léger via Redis pour le MVP ; fan-out-on-write à grande échelle)
8. Appel asynchrone (tâche Celery) à Maadi AI pour :
   - scoring de personnalisation du feed (best-effort, fallback = tri chronologique)
   - modération de contenu (si Maadi renvoie un flag → post mis en `pending_review`)
```

---

## 6. Flux critique n°2 : Feed personnalisé

```
GET /feed?cursor=...
  1. La vue DRF appelle le client `maadi_integration` : POST /maadi/recommend
     { user_id, behavior_signals, location } — requests/httpx avec timeout court
  2. Si Maadi répond (timeout 300ms) → utilise son classement de post_ids
  3. Si Maadi ne répond pas à temps (exception attrapée explicitement,
     jamais de crash de la requête) → fallback : requête ORM Django locale
     (posts récents des comptes suivis + score d'engagement, order_by)
  4. Le backend hydrate les post_ids avec les données complètes
     (auteur, médias, compteurs, badge certifié) depuis Postgres/Redis cache
     — `select_related`/`prefetch_related` pour éviter le N+1
  5. Réponse paginée par curseur (pas d'offset — plus stable en scroll infini),
     via un `CursorPagination` DRF
```

Ce pattern (Maadi = intelligence, backend social = fallback + orchestration) permet de livrer un feed fonctionnel dès le Jour 1 sans bloquer sur la disponibilité de Maadi, conformément à l'esprit "Maadi invisible dans l'UI" du document designer.

---

## 7. Sécurité, conformité & consentement données

- **RGPD-like / consentement Maadi** : un flag `consent_ai_training` par utilisateur (opt-in explicite à l'onboarding), conforme à la mention du cadrage produit "les données générées (avec consentement) alimentent... l'entraînement de l'IA".
- **Rôles** : `public`, `tourist`, `partner`, `creator`, `admin` — enforced via guards NestJS (RBAC), pas seulement côté UI.
- **Accessibilité** : WCAG 2.1 AA — géré côté mobile (composants accessibles, tailles de police dynamiques, `accessibilityLabel` systématiques).
- **Rate limiting** : au niveau Cloudflare (edge) + niveau applicatif (Redis) pour absorber les pics JOJ sans dégrader le service.
- **Modération** : tout contenu passe par une file `moderation_queue` (BullMQ) — Maadi AI donne un premier verdict automatique, un contenu ambigu est mis en `pending_review` pour une revue humaine légère (pas de blocage bloquant l'UX : le post est visible par défaut sauf si Maadi le flague avec confiance haute).

---

## 8. Scalabilité — préparation à la charge JOJ (600 000+ visiteurs)

Le MVP n'est **pas** dimensionné dès le jour 1 pour 600k utilisateurs simultanés, mais l'architecture ne bloque aucune montée en charge :

| Levier | Effort au MVP | Effort si charge JOJ confirmée |
|---|---|---|
| Read replicas Postgres | Non activé | Ajout de replicas, lecture routée par Prisma sans changement de code métier |
| Cache Redis du feed | Activé dès le MVP | Augmentation de la taille du cluster Redis |
| CDN médias/filtres | Activé dès le MVP (Cloudflare) | Aucun changement — déjà conçu pour l'échelle |
| Backend horizontal scaling | Un seul conteneur ASGI | Le monolithe est stateless (JWT, pas de session serveur Django classique) → réplication horizontale immédiate derrière un load balancer |
| WebSocket (chat) | Instance unique | Django Channels utilise déjà Redis comme *channel layer* par défaut → le pub/sub multi-instances est natif, pas de réécriture nécessaire pour scaler horizontalement |
| Workers Celery | 1 worker | Ajout de workers supplémentaires (queue `moderation`, `notifications`, `media` séparées) sans changement de code |

---

## 9. Ce qui est volontairement hors-scope du MVP (V2+)

- Recherche full-text avancée (Elasticsearch)
- Support NLP wolof dans l'app (prévu V2 selon le cadrage produit lui-même)
- Microservices dédiés (extraction du module `filters/` et `feed/` si la charge le justifie)
- Modération 100% automatisée sans supervision humaine
- Multi-région / réplication géographique de la base de données

---

## 10. Alignement avec la feuille de route à 45 jours du cadrage produit

L'architecture ci-dessus est conçue pour être livrable selon le planning déjà validé par le CA (§8 du cadrage produit) :

- **Sem. 1** : setup infra (Docker, CI/CD, Postgres + migrations Django, squelette Django/DRF + squelette Flutter)
- **Sem. 2** : app `accounts` complète (auth) + design system Flutter + premiers filtres AR (intégration SDK Banuba)
- **Sem. 3** : Caméra/filtres + Feed basique + Stories + Messagerie via Channels (version testable en interne)
- **Sem. 4–5** : Géoloc/Carte + intégration Maadi + notifications + mode sombre + sync web
- **Sem. 6** : tests end-to-end, stabilisation, démo finale Jour 45
