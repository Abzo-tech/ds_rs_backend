-- ============================================================================
-- DISCOVER SÉNÉGAL — RÉSEAU SOCIAL MOBILE
-- Schéma de base de données PostgreSQL — MVP
-- Version 1.0
--
-- Principes :
--   - UUID comme clé primaire partout (évite les collisions inter-piliers,
--     l'écosystème réservation/social/Maadi partage cette base)
--   - Toutes les tables ont created_at / updated_at
--   - Extension PostGIS pour la géolocalisation native (unlock de filtres,
--     carte interactive)
--   - Cette base est PARTAGÉE avec la plateforme de réservation existante :
--     les tables `partner_establishments` et `bookings` sont supposées déjà
--     exister (référencées ici en FK logique, non recréées)
--
-- Note d'implémentation (backend Django) :
--   - Les noms de tables/colonnes en snake_case ci-dessous correspondent aux
--     conventions par défaut de Django ORM — aucun renommage nécessaire.
--   - `points_of_interest.location` (GEOGRAPHY) se mappe sur un
--     `PointField(geography=True)` de GeoDjango (django.contrib.gis).
--   - Ce schéma est la source de vérité ; les migrations Django
--     (`makemigrations`/`migrate`) doivent être générées pour le reproduire,
--     jamais l'inverse.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "postgis";    -- géolocalisation

-- ============================================================================
-- 1. COMPTE UNIFIÉ (partagé entre réservation / réseau social / Maadi)
-- ============================================================================

CREATE TYPE user_role AS ENUM ('public', 'tourist', 'partner', 'creator', 'admin');
CREATE TYPE app_language AS ENUM ('fr', 'en', 'wo');

CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email               VARCHAR(255) UNIQUE,
    phone_number        VARCHAR(32) UNIQUE,
    password_hash       VARCHAR(255),               -- NULL si connexion OAuth uniquement
    role                user_role NOT NULL DEFAULT 'public',
    preferred_language  app_language NOT NULL DEFAULT 'fr',
    consent_ai_training BOOLEAN NOT NULL DEFAULT false,  -- consentement Maadi AI
    is_active           BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_identifier CHECK (email IS NOT NULL OR phone_number IS NOT NULL)
);

-- Connexions OAuth (Google, Apple) liées à un compte unique
CREATE TABLE auth_providers (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider            VARCHAR(32) NOT NULL,        -- 'google' | 'apple'
    provider_user_id    VARCHAR(255) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (provider, provider_user_id)
);

-- Refresh tokens (JWT rotation)
CREATE TABLE refresh_tokens (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash          VARCHAR(255) NOT NULL,
    expires_at          TIMESTAMPTZ NOT NULL,
    revoked             BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);

-- ============================================================================
-- 2. PROFILS
-- ============================================================================

CREATE TABLE profiles (
    user_id             UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    display_name        VARCHAR(100) NOT NULL,
    username            VARCHAR(50) UNIQUE NOT NULL,
    bio                 TEXT,
    avatar_media_id     UUID,                        -- FK vers media_assets, nullable
    external_link       VARCHAR(255),
    location_label      VARCHAR(150),                -- ville/région affichée sur le profil
    is_certified        BOOLEAN NOT NULL DEFAULT false,  -- badge "Certifié Discover Sénégal"
    partner_establishment_id UUID,                   -- FK logique vers la table existante
                                                       -- `partner_establishments` (plateforme réservation)
    followers_count     INTEGER NOT NULL DEFAULT 0,   -- dénormalisé pour perf, recalculé par job
    following_count      INTEGER NOT NULL DEFAULT 0,
    posts_count         INTEGER NOT NULL DEFAULT 0,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE follows (
    follower_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    followee_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (follower_id, followee_id),
    CONSTRAINT chk_no_self_follow CHECK (follower_id <> followee_id)
);

CREATE INDEX idx_follows_followee ON follows(followee_id);

-- ============================================================================
-- 3. FILTRES AR & GÉOLOCALISATION
--    (définis avant media_assets car un média référence un filtre)
-- ============================================================================

CREATE TYPE filter_category AS ENUM ('culture_traditions', 'lieux_patrimoine', 'joj_2026', 'nature_faune');

CREATE TABLE filters (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                VARCHAR(100) NOT NULL,
    category            filter_category NOT NULL,
    sdk_effect_id       VARCHAR(255) NOT NULL,       -- identifiant du pack Banuba/DeepAR côté CDN
    preview_url         VARCHAR(500),
    is_geolocated       BOOLEAN NOT NULL DEFAULT false,
    is_time_limited     BOOLEAN NOT NULL DEFAULT false,   -- ex : filtres JOJ exclusifs
    available_from      TIMESTAMPTZ,
    available_until     TIMESTAMPTZ,
    is_active           BOOLEAN NOT NULL DEFAULT true,     -- permet le retrait OTA sans supprimer l'historique
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Points d'intérêt (lieux qui débloquent des filtres géolocalisés)
CREATE TABLE points_of_interest (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                VARCHAR(150) NOT NULL,        -- ex: "Île de Gorée", "Lac Rose"
    category            VARCHAR(50),                  -- touristique / culturel / gastronomique
    location            GEOGRAPHY(Point, 4326) NOT NULL,
    unlock_radius_meters INTEGER NOT NULL DEFAULT 200,
    partner_establishment_id UUID,                    -- si POI = établissement partenaire abonné
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_poi_location ON points_of_interest USING GIST(location);

-- Règle de déblocage : quel filtre est débloqué par quel lieu
CREATE TABLE poi_filter_unlocks (
    poi_id              UUID NOT NULL REFERENCES points_of_interest(id) ON DELETE CASCADE,
    filter_id           UUID NOT NULL REFERENCES filters(id) ON DELETE CASCADE,
    PRIMARY KEY (poi_id, filter_id)
);

-- ============================================================================
-- 4. MÉDIAS
-- ============================================================================

CREATE TYPE media_type AS ENUM ('photo', 'video');

CREATE TABLE media_assets (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type                media_type NOT NULL,
    storage_url         VARCHAR(500) NOT NULL,       -- URL Cloudflare R2
    thumbnail_url       VARCHAR(500),
    duration_seconds    SMALLINT,                    -- NULL pour photo, ≤ 60 pour vidéo
    filter_id           UUID REFERENCES filters(id),
    has_watermark       BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- 5. POSTS, STORIES, INTERACTIONS
-- ============================================================================

CREATE TYPE post_status AS ENUM ('published', 'pending_review', 'removed');

CREATE TABLE posts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    media_id            UUID NOT NULL REFERENCES media_assets(id),
    caption             TEXT,
    location             GEOGRAPHY(Point, 4326),
    status              post_status NOT NULL DEFAULT 'published',
    moderation_score    REAL,                         -- score renvoyé par Maadi AI (0-1)
    is_sponsored        BOOLEAN NOT NULL DEFAULT false,
    likes_count         INTEGER NOT NULL DEFAULT 0,
    comments_count      INTEGER NOT NULL DEFAULT 0,
    shares_count        INTEGER NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_posts_author_created ON posts(author_id, created_at DESC);
CREATE INDEX idx_posts_status ON posts(status) WHERE status = 'published';

CREATE TABLE stories (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    media_id            UUID NOT NULL REFERENCES media_assets(id),
    expires_at          TIMESTAMPTZ NOT NULL,          -- created_at + 24h, appliqué en code
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_stories_author_active ON stories(author_id) WHERE expires_at > now();

CREATE TABLE story_views (
    story_id            UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    viewer_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    viewed_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (story_id, viewer_id)
);

CREATE TABLE comments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id             UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    author_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content             TEXT NOT NULL,
    status              post_status NOT NULL DEFAULT 'published',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_comments_post ON comments(post_id, created_at);

CREATE TABLE likes (
    post_id             UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (post_id, user_id)
);

-- ============================================================================
-- 6. MESSAGERIE
-- ============================================================================

CREATE TABLE conversations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE conversation_participants (
    conversation_id     UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    last_read_at        TIMESTAMPTZ,

    PRIMARY KEY (conversation_id, user_id)
);

CREATE TABLE messages (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id     UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id           UUID NOT NULL REFERENCES users(id),
    content             TEXT,
    media_id            UUID REFERENCES media_assets(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);

-- ============================================================================
-- 7. NOTIFICATIONS
-- ============================================================================

CREATE TYPE notification_type AS ENUM (
    'new_follower', 'like', 'comment', 'message', 'filter_unlocked', 'joj_event'
);

CREATE TABLE notifications (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type                notification_type NOT NULL,
    payload             JSONB NOT NULL DEFAULT '{}',   -- données contextuelles (post_id, actor_id, etc.)
    is_read             BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_notifications_recipient ON notifications(recipient_id, created_at DESC) WHERE is_read = false;

-- ============================================================================
-- 8. MODÉRATION
-- ============================================================================

CREATE TYPE report_status AS ENUM ('open', 'reviewed', 'dismissed');

CREATE TABLE reports (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id         UUID NOT NULL REFERENCES users(id),
    post_id             UUID REFERENCES posts(id) ON DELETE CASCADE,
    comment_id          UUID REFERENCES comments(id) ON DELETE CASCADE,
    reason              VARCHAR(100) NOT NULL,
    status              report_status NOT NULL DEFAULT 'open',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- 9. ANALYTICS SIMPLIFIÉ (comptes certifiés / partenaires)
-- ============================================================================

CREATE TABLE post_analytics_daily (
    post_id             UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    day                 DATE NOT NULL,
    views               INTEGER NOT NULL DEFAULT 0,
    reach               INTEGER NOT NULL DEFAULT 0,
    engagement          INTEGER NOT NULL DEFAULT 0,

    PRIMARY KEY (post_id, day)
);

-- ============================================================================
-- FIN DU SCHÉMA MVP
-- Notes de migration :
--   - `partner_establishments` et `bookings` sont supposées exister déjà
--     (plateforme de réservation) — les FK logiques ci-dessus (profiles.partner_establishment_id,
--     points_of_interest.partner_establishment_id) devront être converties en vraies
--     FK une fois le schéma de la plateforme de réservation confirmé.
--   - Toute évolution de schéma doit passer par une migration Prisma versionnée,
--     jamais par une modification manuelle en production.
-- ============================================================================
