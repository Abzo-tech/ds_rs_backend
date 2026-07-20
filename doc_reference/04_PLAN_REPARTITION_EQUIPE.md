# PLAN DE RÉPARTITION DU TRAVAIL
## Discover Sénégal — Réseau Social Mobile
### 2 développeurs : Dev Mobile (Flutter) + Dev Backend (Django)

**Version 1.0**

---

## 0. Mise en garde honnête, en tant que CTO

Le cahier des charges initial prévoyait une équipe de 7 profils (3 design + 4 dev : mobile, backend, AR, intégrateur Maadi). Vous avez 2 développeurs. Ce n'est pas un problème de méthode, c'est un problème de capacité — donc ce plan fait deux choses en plus de répartir le travail :

1. Il assigne à chaque dev les tâches "spécialisées" qui n'ont plus de propriétaire dédié (le mobile hérite de l'intégration AR, le backend hérite de l'intégration Maadi).
2. Il **priorise** explicitement (P0/P1/P2) pour que si le planning glisse — ce qui est probable avec 2 personnes sur ce périmètre — vous sachiez quoi couper sans improviser au Jour 40.

Si à l'issue de la semaine 2 le rythme réel est très en dessous du plan, mieux vaut le savoir tôt et retirer des filtres AR ou repousser la messagerie en V1.1, plutôt que d'arriver au Jour 45 avec six modules à moitié finis.

---

## 1. Principe de répartition

**Répartition par stack, pas par fonctionnalité.** Chaque développeur possède l'intégralité de sa couche technique sur les 6 modules, plutôt que de se répartir les modules eux-mêmes. Raison : avec seulement 2 personnes, changer de contexte entre modules coûte plus cher que changer de couche — et ça évite qu'un module entier soit bloqué si un seul des deux est absent ou en retard.

| | Dev Mobile (Flutter) | Dev Backend (Django) |
|---|---|---|
| Périmètre | Toute l'app Flutter, les 6 modules côté UI, intégration SDK AR, client WebSocket | Toute l'API Django, les 6 modules côté données, intégration Maadi AI, Channels côté serveur |
| Hérite en plus de | Le rôle "Motion designer / AR designer" pour l'intégration technique (pas la création artistique des filtres, qui reste chez le designer) | Le rôle "Intégrateur Maadi AI" |

**Règle qui rend ce split possible : contrat d'API défini avant le code.** Le point le plus risqué d'un split par stack est que le mobile attende le backend. On l'élimine en figeant le contrat des endpoints (noms, champs, formats) dès la semaine 1, documenté en OpenAPI, avec un serveur mock (ex. Prism, ou simplement des fixtures JSON statiques) que le mobile utilise pour développer sans dépendre de l'avancement réel du backend. Le backend implémente ensuite exactement ce contrat.

---

## 2. Répartition détaillée par module

| Module | Dev Mobile | Dev Backend |
|---|---|---|
| **Authentification** | Écrans login/onboarding/OAuth, stockage sécurisé du token, refresh automatique | Endpoints auth, JWT, OAuth Google/Apple, gestion des rôles |
| **Caméra & Filtres AR** | Intégration SDK Banuba/DeepAR, écran caméra, application des filtres, capture, review | Endpoint manifeste de filtres, logique de déblocage géolocalisé, stockage des packs de filtres sur CDN |
| **Géolocalisation & Carte** | Écran carte (google_maps_flutter), affichage des POI et badges partenaires | Modèle PostGIS, requêtes de proximité, endpoint POI |
| **Messagerie** | Client WebSocket, écrans conversation/chat, gestion de la reconnexion | Django Channels consumers, historique REST, persistance des messages |
| **Feed & Contenus** | Écran feed (scroll infini par curseur), stories, interactions (like/comment) | Endpoints posts/stories, fallback si Maadi indisponible, tâche Celery d'expiration des stories |
| **Profil utilisateur** | Écran profil, dashboard partenaire (UI) | Endpoints profil, analytics simplifié pour comptes certifiés |
| **Maadi AI (transversal)** | Toggle UI vers l'interface de discussion Maadi (déjà existante) | Client HTTP vers Maadi, gestion des timeouts/fallback |
| **Notifications** | Intégration firebase_messaging côté app | Déclenchement des notifications (Celery + FCM) |

---

## 3. Priorisation (à utiliser si le planning glisse)

| Priorité | Contenu | Peut glisser en V1.1 si retard ? |
|---|---|---|
| **P0 — non négociable pour le Jour 45** | Auth, Feed (avec fallback, sans Maadi si besoin), Caméra + 5 filtres minimum (pas 10), Profil de base | Non |
| **P1 — attendu mais négociable** | Carte/géolocalisation, Stories, badge Certifié, mode sombre, filtres restants jusqu'à 10 | Oui, en dernier recours |
| **P2 — confort, coupable en premier** | Messagerie temps réel complète (garder un simple historique REST sans WebSocket comme repli), dashboard analytics partenaire avancé, intégration Maadi complète (garder le fallback comme comportement par défaut) | Oui, en premier |

---

## 4. Planning détaillé semaine par semaine

### Semaine 1 (J1-7) — Fondations & contrat d'API

**Ensemble (jour 1-2, prioritaire avant tout code métier) :**
- [ ] Figer le contrat d'API des endpoints P0 (auth, feed, filtres) en OpenAPI
- [ ] Valider ensemble le choix définitif du SDK AR (Banuba vs DeepAR)
- [ ] Mettre en place le repo, la CI de base (lint + build), Docker Compose

**Dev Backend :**
- [ ] Init projet Django, structure `apps/` (accounts, feed, filters, geo, messaging, notifications, moderation, maadi_integration, partners)
- [ ] Modèle `User` custom, migrations initiales à partir du schéma de référence
- [ ] Config settings dev/staging, déploiement d'un environnement staging minimal (même vide)
- [ ] Génération du contrat OpenAPI avec `drf-spectacular` dès les premiers endpoints

**Dev Mobile :**
- [ ] Init projet Flutter, structure `core/` `features/` `shared/`
- [ ] Application des tokens de design (couleurs, typographie) depuis les maquettes du designer
- [ ] Squelette de navigation (go_router) pour les 6 modules, écrans vides
- [ ] PoC isolé : caméra + 1 filtre via le SDK AR choisi (valider la faisabilité technique avant de s'engager dessus toute la semaine 2)

---

### Semaine 2 (J8-14) — Authentification & premiers filtres

**Dev Backend :**
- [ ] Endpoints auth complets (register, login, refresh, OAuth Google/Apple)
- [ ] Permissions par rôle (`public`, `tourist`, `partner`, `creator`, `admin`)
- [ ] Tests unitaires sur le flux d'authentification

**Dev Mobile :**
- [ ] Écrans login / onboarding / callback OAuth, branchés d'abord sur mock puis sur le backend réel dès qu'il est prêt
- [ ] Design system complet appliqué à tous les écrans existants
- [ ] Intégration de 5 filtres AR (priorité : 2 culturels + les filtres les plus simples techniquement, pas les plus complexes visuellement)

**Sync milieu de semaine :** premier test d'intégration réel mobile ↔ backend sur l'auth (remplacer les mocks).

---

### Semaine 3 (J15-21) — Fonctionnalités cœur

**Dev Backend :**
- [ ] Endpoints posts (CRUD, likes, commentaires), pagination par curseur
- [ ] Modèle stories + tâche Celery d'expiration à 24h
- [ ] Django Channels : consumer de chat 1-to-1 + historique REST

**Dev Mobile :**
- [ ] Écran feed (scroll infini, cartes de posts)
- [ ] Stories bar + viewer plein écran
- [ ] Écran caméra finalisé (review avant publication, capture ≤ 60s)
- [ ] Client WebSocket + écran chat

**Sync dédié (prévoir une demi-journée ensemble) :** intégration du chat temps réel — c'est historiquement le point le plus source de bugs d'un split mobile/backend (gestion de la reconnexion, ordre des messages).

**Fin de semaine 3 :** première version testable en interne (build partagé entre les deux devs, pas encore la démo officielle).

---

### Semaine 4-5 (J22-35) — Fonctionnalités complètes

**Dev Backend :**
- [ ] App `geo` : modèle PostGIS, requêtes de proximité, règles de déblocage de filtres
- [ ] Client `maadi_integration` (appel HTTP, timeout 300ms, fallback obligatoire)
- [ ] Notifications (déclenchement Celery + FCM)
- [ ] Endpoint analytics simplifié pour comptes certifiés

**Dev Mobile :**
- [ ] Écran carte + affichage des POI et badges partenaires
- [ ] Gestion des notifications push côté app
- [ ] Mode sombre
- [ ] Écran profil complet + dashboard partenaire (UI)
- [ ] i18n FR/EN branché sur tous les écrans

**Jalon Jour 22 — Démo intermédiaire (obligatoire, cf. cahier des charges §9) :** les deux devs doivent avoir un build partageable avec les modules P0 fonctionnels, même si P1/P2 sont incomplets.

---

### Semaine 6 (J36-42) — Tests & stabilisation

**Ensemble :**
- [ ] Tests end-to-end des parcours critiques (inscription → capture avec filtre → publication → like/commentaire, envoi de message)
- [ ] Correction des bugs critiques en priorité P0, puis P1
- [ ] Optimisation des performances (temps de chargement du feed, latence de la capture AR)
- [ ] Préparation de la démo finale

**Jour 45 — Démo finale devant le CA.**

---

## 5. Règles de collaboration au quotidien

- **Daily de 15 minutes**, même à deux : qu'est-ce qui bloque, qu'est-ce qui a changé dans le contrat d'API.
- **Le contrat OpenAPI est la source de vérité.** Toute modification (ajout de champ, changement de format) doit être annoncée à l'autre développeur avant d'être codée, pas découverte au moment de l'intégration.
- **Revue de code croisée systématique** avant merge, même sous pression de deadline — avec 2 devs seulement, un bug non détecté coûte proportionnellement plus cher qu'avec une grande équipe.
- **Règle des 48h du cahier des charges** : tout blocage non résolu en 48h est remonté à la direction — avec 2 devs, ce délai doit probablement être raccourci à 24h, vous n'avez pas de marge d'absorption.
- **Branches courtes, intégration fréquente** (trunk-based si possible) plutôt que de longues branches de fonctionnalité — réduit le risque de conflits d'intégration coûteux à 2 personnes.

---

## 6. Ce que ce plan suppose comme acquis

- Les maquettes du designer sont livrées avec toutes les spécifications visuelles nécessaires (états vides, erreurs, chargement) — sinon le dev mobile devra improviser, ce qui ralentit.
- Le SDK AR choisi (Banuba ou DeepAR) est confirmé et sa licence obtenue avant la fin de la semaine 1 — c'est la dépendance externe la plus susceptible de bloquer le développement.
- L'accès à un environnement Maadi AI de test (même minimal) est disponible avant la semaine 4, pour que l'intégration ne soit pas découverte en fin de projet.
