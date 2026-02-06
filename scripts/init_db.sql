-- ================================================================
-- REUSE DATABASE - SCRIPT DE INICIALIZACION COMPLETO
-- Sistema de Intercambio Sostenible - PUCE
-- PostgreSQL 14+
--
-- Este script inicializa la base de datos desde cero.
-- Incluye: Tablas, Vistas, Funciones, Triggers, Datos iniciales
-- Implementa SOFT DELETE con campo deleted_at en todas las tablas
-- ================================================================

-- Limpiar base de datos si existe
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ================================================================
-- TIPOS ENUM
-- ================================================================

CREATE TYPE user_role AS ENUM ('estudiante', 'moderador', 'administrador');
CREATE TYPE user_status AS ENUM ('active', 'suspended', 'banned', 'pending_verification');
CREATE TYPE offer_status AS ENUM ('active', 'reserved', 'completed', 'cancelled', 'flagged');
CREATE TYPE offer_condition AS ENUM ('nuevo', 'como_nuevo', 'buen_estado', 'usado', 'para_reparar');
CREATE TYPE exchange_status AS ENUM ('pending', 'accepted', 'in_progress', 'completed', 'cancelled', 'disputed');
CREATE TYPE exchange_event_type AS ENUM ('created', 'accepted', 'rejected', 'check_in_buyer', 'check_in_seller', 'completed', 'cancelled', 'disputed');
CREATE TYPE transaction_type AS ENUM ('initial_grant', 'exchange_payment', 'exchange_received', 'reward_claim', 'admin_adjustment', 'refund');
CREATE TYPE flag_type AS ENUM ('inappropriate_content', 'scam', 'spam', 'offensive', 'other');
CREATE TYPE flag_status AS ENUM ('pending', 'reviewed', 'action_taken', 'dismissed');
CREATE TYPE claim_status AS ENUM ('pending', 'approved', 'delivered', 'rejected');
CREATE TYPE challenge_frequency AS ENUM ('weekly', 'monthly', 'special', 'permanent');
CREATE TYPE challenge_difficulty AS ENUM ('easy', 'medium', 'hard', 'expert');
CREATE TYPE audit_operation AS ENUM ('INSERT', 'UPDATE', 'DELETE');

-- ================================================================
-- TABLAS DE CATALOGOS
-- ================================================================

CREATE TABLE faculties (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    code VARCHAR(20) NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    icon VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

-- ================================================================
-- USUARIOS Y AUTENTICACION
-- ================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    faculty_id INTEGER REFERENCES faculties(id) ON DELETE SET NULL,
    role user_role DEFAULT 'estudiante',
    status user_status DEFAULT 'pending_verification',
    whatsapp VARCHAR(20),
    whatsapp_visible BOOLEAN DEFAULT FALSE,
    profile_photo_url VARCHAR(500),
    bio TEXT,
    sustainability_points INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    experience_points INTEGER DEFAULT 0,
    is_email_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL,
    CONSTRAINT check_points_positive CHECK (sustainability_points >= 0),
    CONSTRAINT check_level_positive CHECK (level >= 1)
);

CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP,
    device_info VARCHAR(500),
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE email_verification_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

-- ================================================================
-- OFERTAS (OBJETOS)
-- ================================================================

CREATE TABLE offers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    condition offer_condition NOT NULL,
    location_id INTEGER REFERENCES locations(id) ON DELETE SET NULL,
    status offer_status DEFAULT 'active',
    credits_value INTEGER DEFAULT 0 CHECK (credits_value >= 0),
    views_count INTEGER DEFAULT 0,
    is_featured BOOLEAN DEFAULT FALSE,
    featured_until TIMESTAMP,
    interests_count INTEGER DEFAULT 0,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE offer_photos (
    id SERIAL PRIMARY KEY,
    offer_id UUID NOT NULL REFERENCES offers(id) ON DELETE CASCADE,
    photo_url VARCHAR(500) NOT NULL,
    object_key VARCHAR(500),
    is_primary BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE offer_interests (
    id SERIAL PRIMARY KEY,
    offer_id UUID NOT NULL REFERENCES offers(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID,
    status VARCHAR(20) DEFAULT 'active',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL,
    UNIQUE(offer_id, user_id)
);

-- ================================================================
-- CHAT Y MENSAJERIA
-- ================================================================

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    offer_id UUID NOT NULL REFERENCES offers(id) ON DELETE CASCADE,
    user1_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user2_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL,
    UNIQUE(offer_id, user1_id, user2_id)
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    from_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

-- ================================================================
-- INTERCAMBIOS
-- ================================================================

CREATE TABLE exchanges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    offer_id UUID NOT NULL REFERENCES offers(id) ON DELETE RESTRICT,
    buyer_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    seller_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    location_id INTEGER REFERENCES locations(id) ON DELETE SET NULL,
    status exchange_status DEFAULT 'pending',
    credits_amount INTEGER NOT NULL CHECK (credits_amount >= 0),
    buyer_confirmed BOOLEAN DEFAULT FALSE,
    seller_confirmed BOOLEAN DEFAULT FALSE,
    buyer_confirmed_at TIMESTAMP,
    seller_confirmed_at TIMESTAMP,
    scheduled_at TIMESTAMP,
    completed_at TIMESTAMP,
    cancellation_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE exchange_events (
    id SERIAL PRIMARY KEY,
    exchange_id UUID NOT NULL REFERENCES exchanges(id) ON DELETE CASCADE,
    event_type exchange_event_type NOT NULL,
    by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    notes TEXT,
    event_metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE exchange_ratings (
    id SERIAL PRIMARY KEY,
    exchange_id UUID NOT NULL REFERENCES exchanges(id) ON DELETE CASCADE,
    rater_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rated_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL,
    UNIQUE(exchange_id, rater_user_id)
);

-- ================================================================
-- SISTEMA DE CREDITOS
-- ================================================================

CREATE TABLE credits_ledger (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    transaction_type transaction_type NOT NULL,
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL CHECK (balance_after >= 0),
    reference_id UUID,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE rewards_catalog (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    credits_cost INTEGER NOT NULL CHECK (credits_cost > 0),
    stock_quantity INTEGER DEFAULT 0 CHECK (stock_quantity >= 0),
    is_active BOOLEAN DEFAULT TRUE,
    image_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE reward_claims (
    id SERIAL PRIMARY KEY,
    reward_id INTEGER NOT NULL REFERENCES rewards_catalog(id) ON DELETE RESTRICT,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    credits_spent INTEGER NOT NULL,
    status claim_status DEFAULT 'pending',
    approved_at TIMESTAMP,
    delivered_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

-- ================================================================
-- GAMIFICACION
-- ================================================================

CREATE TABLE challenges (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    frequency challenge_frequency NOT NULL,
    difficulty challenge_difficulty NOT NULL,
    points_reward INTEGER NOT NULL CHECK (points_reward > 0),
    credits_reward INTEGER DEFAULT 0,
    badge_reward VARCHAR(50),
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    requirement_type VARCHAR(50) NOT NULL,
    requirement_value INTEGER NOT NULL,
    requirement_metadata JSONB,
    icon VARCHAR(50),
    educational_content TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    participants_count INTEGER DEFAULT 0,
    completions_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE user_challenges (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    challenge_id INTEGER NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    progress INTEGER DEFAULT 0,
    target INTEGER NOT NULL,
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL,
    UNIQUE(user_id, challenge_id)
);

CREATE TABLE badges_catalog (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    icon VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    unlock_criteria TEXT NOT NULL,
    unlock_type VARCHAR(50) NOT NULL,
    unlock_value INTEGER DEFAULT 0,
    unlock_metadata JSONB,
    rarity VARCHAR(20) DEFAULT 'common',
    points_value INTEGER DEFAULT 0,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE user_badges (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    badge_id VARCHAR(50) NOT NULL REFERENCES badges_catalog(id) ON DELETE CASCADE,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    progress INTEGER DEFAULT 100,
    is_displayed BOOLEAN DEFAULT TRUE,
    deleted_at TIMESTAMP DEFAULT NULL,
    UNIQUE(user_id, badge_id)
);

-- ================================================================
-- NOTIFICACIONES
-- ================================================================

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    reference_id UUID,
    reference_type VARCHAR(50),
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    action_url VARCHAR(500),
    extra_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

-- ================================================================
-- PREFERENCIAS Y CONFIGURACION
-- ================================================================

CREATE TABLE user_preferences (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    email_notifications BOOLEAN DEFAULT TRUE,
    push_notifications BOOLEAN DEFAULT TRUE,
    notify_new_messages BOOLEAN DEFAULT TRUE,
    notify_interests BOOLEAN DEFAULT TRUE,
    notify_exchanges BOOLEAN DEFAULT TRUE,
    notify_challenges BOOLEAN DEFAULT TRUE,
    notify_badges BOOLEAN DEFAULT TRUE,
    notify_marketing BOOLEAN DEFAULT FALSE,
    profile_visibility VARCHAR(20) DEFAULT 'public',
    show_email BOOLEAN DEFAULT FALSE,
    show_whatsapp BOOLEAN DEFAULT FALSE,
    show_stats BOOLEAN DEFAULT TRUE,
    show_badges BOOLEAN DEFAULT TRUE,
    language VARCHAR(10) DEFAULT 'es',
    theme VARCHAR(20) DEFAULT 'light',
    items_per_page INTEGER DEFAULT 20,
    saved_filters JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

-- ================================================================
-- REPUTACION Y METRICAS
-- ================================================================

CREATE TABLE user_reputation_metrics (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    total_exchanges INTEGER DEFAULT 0,
    successful_exchanges INTEGER DEFAULT 0,
    average_rating DECIMAL(3, 2) DEFAULT 0.00,
    total_ratings_received INTEGER DEFAULT 0,
    total_credits_earned INTEGER DEFAULT 0,
    total_credits_spent INTEGER DEFAULT 0,
    total_interests_received INTEGER DEFAULT 0,
    total_interests_given INTEGER DEFAULT 0,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    rank_in_faculty INTEGER,
    rank_overall INTEGER,
    favorite_category INTEGER REFERENCES categories(id),
    badges JSONB DEFAULT '[]'::jsonb,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

-- ================================================================
-- MODERACION
-- ================================================================

CREATE TABLE content_flags (
    id SERIAL PRIMARY KEY,
    reporter_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    offer_id UUID REFERENCES offers(id) ON DELETE CASCADE,
    exchange_id UUID REFERENCES exchanges(id) ON DELETE CASCADE,
    flag_type flag_type NOT NULL,
    description TEXT NOT NULL,
    status flag_status DEFAULT 'pending',
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP,
    resolution_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL,
    CHECK (
        (offer_id IS NOT NULL AND exchange_id IS NULL) OR
        (offer_id IS NULL AND exchange_id IS NOT NULL)
    )
);

-- ================================================================
-- AUDITORIA
-- ================================================================

CREATE TABLE activity_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    extra_data JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audit_history (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id TEXT NOT NULL,
    operation audit_operation NOT NULL,
    old_data JSONB,
    new_data JSONB,
    changed_fields TEXT[],
    changed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================================
-- INDICES PARA RENDIMIENTO
-- ================================================================

-- Usuarios
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_faculty ON users(faculty_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_status ON users(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_points ON users(sustainability_points DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_deleted ON users(deleted_at) WHERE deleted_at IS NULL;

-- Ofertas
CREATE INDEX idx_offers_user ON offers(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_offers_category ON offers(category_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_offers_status ON offers(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_offers_created ON offers(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_offers_deleted ON offers(deleted_at) WHERE deleted_at IS NULL;

-- Fotos de ofertas
CREATE INDEX idx_offer_photos_offer ON offer_photos(offer_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_offer_photos_deleted ON offer_photos(deleted_at) WHERE deleted_at IS NULL;

-- Intereses
CREATE INDEX idx_offer_interests_offer ON offer_interests(offer_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_offer_interests_user ON offer_interests(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_offer_interests_deleted ON offer_interests(deleted_at) WHERE deleted_at IS NULL;

-- Conversaciones
CREATE INDEX idx_conversations_offer ON conversations(offer_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_conversations_users ON conversations(user1_id, user2_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_conversations_deleted ON conversations(deleted_at) WHERE deleted_at IS NULL;

-- Mensajes
CREATE INDEX idx_messages_conversation ON messages(conversation_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_messages_created ON messages(created_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_messages_deleted ON messages(deleted_at) WHERE deleted_at IS NULL;

-- Intercambios
CREATE INDEX idx_exchanges_buyer ON exchanges(buyer_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_exchanges_seller ON exchanges(seller_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_exchanges_status ON exchanges(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_exchanges_offer ON exchanges(offer_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_exchanges_deleted ON exchanges(deleted_at) WHERE deleted_at IS NULL;

-- Calificaciones
CREATE INDEX idx_exchange_ratings_deleted ON exchange_ratings(deleted_at) WHERE deleted_at IS NULL;

-- Notificaciones
CREATE INDEX idx_notifications_user ON notifications(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_notifications_type ON notifications(user_id, type) WHERE deleted_at IS NULL;
CREATE INDEX idx_notifications_deleted ON notifications(deleted_at) WHERE deleted_at IS NULL;

-- Retos
CREATE INDEX idx_challenges_active ON challenges(is_active, start_date, end_date) WHERE deleted_at IS NULL;
CREATE INDEX idx_user_challenges_user ON user_challenges(user_id) WHERE deleted_at IS NULL;

-- Insignias
CREATE INDEX idx_user_badges_user ON user_badges(user_id) WHERE deleted_at IS NULL;

-- Creditos
CREATE INDEX idx_credits_ledger_user ON credits_ledger(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_credits_ledger_created ON credits_ledger(created_at DESC) WHERE deleted_at IS NULL;

-- Tokens
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_email_verification_tokens_user ON email_verification_tokens(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_email_verification_tokens_token ON email_verification_tokens(token) WHERE deleted_at IS NULL;

-- Actividad y auditoria
CREATE INDEX idx_activity_log_user ON activity_log(user_id);
CREATE INDEX idx_activity_log_created ON activity_log(created_at DESC);
CREATE INDEX idx_activity_log_action_type ON activity_log(action_type);
CREATE INDEX idx_activity_log_entity_type ON activity_log(entity_type);
CREATE INDEX idx_audit_history_table ON audit_history(table_name);
CREATE INDEX idx_audit_history_record ON audit_history(table_name, record_id);
CREATE INDEX idx_audit_history_created ON audit_history(created_at DESC);
CREATE INDEX idx_audit_history_operation ON audit_history(operation);
CREATE INDEX idx_audit_history_changed_by ON audit_history(changed_by);

-- Catalogos
CREATE INDEX idx_faculties_deleted ON faculties(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_categories_deleted ON categories(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_locations_deleted ON locations(deleted_at) WHERE deleted_at IS NULL;

-- ================================================================
-- FUNCIONES UTILITARIAS
-- ================================================================

-- Funcion para actualizar updated_at
CREATE OR REPLACE FUNCTION fn_update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Funcion para soft delete (actualiza deleted_at en lugar de eliminar)
CREATE OR REPLACE FUNCTION fn_soft_delete()
RETURNS TRIGGER AS $$
BEGIN
    -- En lugar de eliminar, actualiza deleted_at
    EXECUTE format('UPDATE %I.%I SET deleted_at = CURRENT_TIMESTAMP WHERE id = $1', TG_TABLE_SCHEMA, TG_TABLE_NAME)
    USING OLD.id;
    RETURN NULL; -- Cancela el DELETE real
END;
$$ LANGUAGE plpgsql;

-- Función para auditoría
CREATE OR REPLACE FUNCTION fn_audit_trigger()
RETURNS TRIGGER AS $$
DECLARE
    v_old_data JSONB;
    v_new_data JSONB;
    v_changed_fields TEXT[];
    v_record_id TEXT;
    v_key TEXT;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_record_id := OLD.id::TEXT;
        v_old_data := to_jsonb(OLD);
        v_new_data := NULL;
    ELSIF TG_OP = 'INSERT' THEN
        v_record_id := NEW.id::TEXT;
        v_old_data := NULL;
        v_new_data := to_jsonb(NEW);
    ELSE -- UPDATE
        v_record_id := NEW.id::TEXT;
        v_old_data := to_jsonb(OLD);
        v_new_data := to_jsonb(NEW);
        v_changed_fields := ARRAY[]::TEXT[];
        FOR v_key IN SELECT jsonb_object_keys(v_new_data)
        LOOP
            IF v_old_data->v_key IS DISTINCT FROM v_new_data->v_key THEN
                v_changed_fields := array_append(v_changed_fields, v_key);
            END IF;
        END LOOP;
    END IF;

    INSERT INTO audit_history (
        table_name, record_id, operation, old_data, new_data, changed_fields, changed_by, created_at
    ) VALUES (
        TG_TABLE_NAME, v_record_id, TG_OP::audit_operation, v_old_data, v_new_data, v_changed_fields,
        NULLIF(current_setting('app.current_user_id', true), '')::UUID, CURRENT_TIMESTAMP
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Funcion: Incrementar contador de intereses
CREATE OR REPLACE FUNCTION fn_increment_offer_interests()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE offers SET interests_count = interests_count + 1 WHERE id = NEW.offer_id AND deleted_at IS NULL;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Funcion: Decrementar contador de intereses (en soft delete)
CREATE OR REPLACE FUNCTION fn_decrement_offer_interests()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.deleted_at IS NOT NULL AND OLD.deleted_at IS NULL THEN
        UPDATE offers SET interests_count = GREATEST(interests_count - 1, 0) WHERE id = OLD.offer_id AND deleted_at IS NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Función: Calcular tasa de exito de intercambios
CREATE OR REPLACE FUNCTION fn_user_exchange_success_rate(p_user_id UUID)
RETURNS TABLE (
    total_exchanges INTEGER,
    completed_exchanges INTEGER,
    cancelled_exchanges INTEGER,
    success_rate DECIMAL(5,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::INTEGER,
        COUNT(*) FILTER (WHERE e.status = 'completed')::INTEGER,
        COUNT(*) FILTER (WHERE e.status = 'cancelled')::INTEGER,
        CASE WHEN COUNT(*) > 0 THEN
            ROUND((COUNT(*) FILTER (WHERE e.status = 'completed')::DECIMAL / COUNT(*)) * 100, 2)
        ELSE 0.00 END
    FROM exchanges e
    WHERE (e.buyer_id = p_user_id OR e.seller_id = p_user_id) AND e.deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql;

-- Función: Obtener ranking de usuario
CREATE OR REPLACE FUNCTION fn_get_user_ranking(p_user_id UUID)
RETURNS TABLE (
    user_id UUID, full_name VARCHAR, sustainability_points INTEGER,
    rank_overall BIGINT, rank_faculty BIGINT, faculty_name VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    WITH ranked_users AS (
        SELECT u.id, u.full_name, u.sustainability_points, u.faculty_id, f.name as faculty_name,
            RANK() OVER (ORDER BY u.sustainability_points DESC) as overall_rank,
            RANK() OVER (PARTITION BY u.faculty_id ORDER BY u.sustainability_points DESC) as faculty_rank
        FROM users u
        LEFT JOIN faculties f ON u.faculty_id = f.id
        WHERE u.status = 'active' AND u.deleted_at IS NULL
    )
    SELECT ru.id, ru.full_name, ru.sustainability_points, ru.overall_rank, ru.faculty_rank, ru.faculty_name
    FROM ranked_users ru WHERE ru.id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Función: Calcular impacto ambiental
CREATE OR REPLACE FUNCTION fn_calculate_environmental_impact(p_user_id UUID)
RETURNS TABLE (
    total_items_exchanged INTEGER,
    estimated_kg_co2_saved DECIMAL(10,2),
    estimated_kg_waste_avoided DECIMAL(10,2),
    equivalent_trees_planted DECIMAL(10,2)
) AS $$
DECLARE
    v_completed_exchanges INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_completed_exchanges
    FROM exchanges
    WHERE (buyer_id = p_user_id OR seller_id = p_user_id) AND status = 'completed' AND deleted_at IS NULL;

    RETURN QUERY SELECT
        v_completed_exchanges,
        (v_completed_exchanges * 2.5)::DECIMAL(10,2),
        (v_completed_exchanges * 1.0)::DECIMAL(10,2),
        (v_completed_exchanges * 2.5 / 21)::DECIMAL(10,2);
END;
$$ LANGUAGE plpgsql;

-- Función: Estadísticas por categoría
CREATE OR REPLACE FUNCTION fn_get_category_stats(p_category_id INTEGER DEFAULT NULL)
RETURNS TABLE (
    category_id INTEGER, category_name VARCHAR, total_offers BIGINT,
    active_offers BIGINT, completed_exchanges BIGINT, avg_credits_value DECIMAL(10,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT c.id, c.name,
        COUNT(DISTINCT o.id),
        COUNT(DISTINCT o.id) FILTER (WHERE o.status = 'active'),
        COUNT(DISTINCT e.id) FILTER (WHERE e.status = 'completed'),
        COALESCE(AVG(o.credits_value), 0)::DECIMAL(10,2)
    FROM categories c
    LEFT JOIN offers o ON c.id = o.category_id AND o.deleted_at IS NULL
    LEFT JOIN exchanges e ON o.id = e.offer_id AND e.deleted_at IS NULL
    WHERE c.is_active = TRUE AND c.deleted_at IS NULL
    AND (p_category_id IS NULL OR c.id = p_category_id)
    GROUP BY c.id, c.name ORDER BY total_offers DESC;
END;
$$ LANGUAGE plpgsql;

-- Función: Detectar usuarios inactivos
CREATE OR REPLACE FUNCTION fn_detect_inactive_users(p_days INTEGER DEFAULT 30)
RETURNS TABLE (
    user_id UUID, email VARCHAR, full_name VARCHAR, last_activity TIMESTAMP, days_inactive INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT u.id, u.email, u.full_name,
        GREATEST(
            COALESCE(u.last_login, u.created_at),
            COALESCE((SELECT MAX(created_at) FROM offers WHERE user_id = u.id AND deleted_at IS NULL), u.created_at),
            COALESCE((SELECT MAX(created_at) FROM messages WHERE from_user_id = u.id AND deleted_at IS NULL), u.created_at)
        ),
        EXTRACT(DAY FROM CURRENT_TIMESTAMP - GREATEST(
            COALESCE(u.last_login, u.created_at),
            COALESCE((SELECT MAX(created_at) FROM offers WHERE user_id = u.id AND deleted_at IS NULL), u.created_at),
            COALESCE((SELECT MAX(created_at) FROM messages WHERE from_user_id = u.id AND deleted_at IS NULL), u.created_at)
        ))::INTEGER
    FROM users u
    WHERE u.status = 'active' AND u.deleted_at IS NULL
    AND GREATEST(
        COALESCE(u.last_login, u.created_at),
        COALESCE((SELECT MAX(created_at) FROM offers WHERE user_id = u.id AND deleted_at IS NULL), u.created_at),
        COALESCE((SELECT MAX(created_at) FROM messages WHERE from_user_id = u.id AND deleted_at IS NULL), u.created_at)
    ) < CURRENT_TIMESTAMP - (p_days || ' days')::INTERVAL
    ORDER BY days_inactive DESC;
END;
$$ LANGUAGE plpgsql;

-- Función: Actualizar métricas de reputación
CREATE OR REPLACE FUNCTION fn_update_user_reputation(p_user_id UUID)
RETURNS VOID AS $$
DECLARE
    v_total_exchanges INTEGER; v_successful_exchanges INTEGER;
    v_avg_rating DECIMAL(3,2); v_total_ratings INTEGER;
    v_total_earned INTEGER; v_total_spent INTEGER;
BEGIN
    SELECT COUNT(*), COUNT(*) FILTER (WHERE status = 'completed')
    INTO v_total_exchanges, v_successful_exchanges
    FROM exchanges WHERE (buyer_id = p_user_id OR seller_id = p_user_id) AND deleted_at IS NULL;

    SELECT COALESCE(AVG(rating), 0), COUNT(*)
    INTO v_avg_rating, v_total_ratings
    FROM exchange_ratings WHERE rated_user_id = p_user_id AND deleted_at IS NULL;

    SELECT COALESCE(SUM(amount) FILTER (WHERE amount > 0), 0),
           COALESCE(ABS(SUM(amount) FILTER (WHERE amount < 0)), 0)
    INTO v_total_earned, v_total_spent
    FROM credits_ledger WHERE user_id = p_user_id AND deleted_at IS NULL;

    INSERT INTO user_reputation_metrics (user_id, total_exchanges, successful_exchanges, average_rating,
        total_ratings_received, total_credits_earned, total_credits_spent, updated_at)
    VALUES (p_user_id, v_total_exchanges, v_successful_exchanges, v_avg_rating,
        v_total_ratings, v_total_earned, v_total_spent, CURRENT_TIMESTAMP)
    ON CONFLICT (user_id) DO UPDATE SET
        total_exchanges = EXCLUDED.total_exchanges,
        successful_exchanges = EXCLUDED.successful_exchanges,
        average_rating = EXCLUDED.average_rating,
        total_ratings_received = EXCLUDED.total_ratings_received,
        total_credits_earned = EXCLUDED.total_credits_earned,
        total_credits_spent = EXCLUDED.total_credits_spent,
        updated_at = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Función: Obtener balance de créditos
CREATE OR REPLACE FUNCTION fn_get_user_credits_balance(p_user_id UUID)
RETURNS TABLE (current_balance INTEGER, total_earned INTEGER, total_spent INTEGER, last_transaction_at TIMESTAMP) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE((SELECT balance_after FROM credits_ledger WHERE user_id = p_user_id AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1), 0)::INTEGER,
        COALESCE(SUM(amount) FILTER (WHERE amount > 0), 0)::INTEGER,
        COALESCE(ABS(SUM(amount) FILTER (WHERE amount < 0)), 0)::INTEGER,
        MAX(created_at)
    FROM credits_ledger WHERE user_id = p_user_id AND deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql;

-- Función: Validar balance de créditos
CREATE OR REPLACE FUNCTION fn_validate_credits_balance()
RETURNS TRIGGER AS $$
DECLARE v_current_balance INTEGER;
BEGIN
    SELECT COALESCE(balance_after, 0) INTO v_current_balance
    FROM credits_ledger WHERE user_id = NEW.user_id AND deleted_at IS NULL
    ORDER BY created_at DESC, id DESC LIMIT 1;

    IF v_current_balance IS NULL THEN v_current_balance := 0; END IF;
    NEW.balance_after := v_current_balance + NEW.amount;

    IF NEW.balance_after < 0 THEN
        RAISE EXCEPTION 'Insufficient credits. Current: %, Attempted: %', v_current_balance, NEW.amount;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Función: Auto actualizar reputación
CREATE OR REPLACE FUNCTION fn_auto_update_reputation()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_TABLE_NAME = 'exchanges' THEN
        PERFORM fn_update_user_reputation(NEW.buyer_id);
        PERFORM fn_update_user_reputation(NEW.seller_id);
    ELSIF TG_TABLE_NAME = 'exchange_ratings' THEN
        PERFORM fn_update_user_reputation(NEW.rated_user_id);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- TRIGGERS
-- ================================================================

-- Triggers de updated_at
CREATE TRIGGER tr_faculties_updated_at BEFORE UPDATE ON faculties FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();
CREATE TRIGGER tr_categories_updated_at BEFORE UPDATE ON categories FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();
CREATE TRIGGER tr_locations_updated_at BEFORE UPDATE ON locations FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();
CREATE TRIGGER tr_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();
CREATE TRIGGER tr_offers_updated_at BEFORE UPDATE ON offers FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();
CREATE TRIGGER tr_conversations_updated_at BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();
CREATE TRIGGER tr_exchanges_updated_at BEFORE UPDATE ON exchanges FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();
CREATE TRIGGER tr_offer_interests_updated_at BEFORE UPDATE ON offer_interests FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();
CREATE TRIGGER tr_challenges_updated_at BEFORE UPDATE ON challenges FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();
CREATE TRIGGER tr_user_preferences_updated_at BEFORE UPDATE ON user_preferences FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();
CREATE TRIGGER tr_rewards_catalog_updated_at BEFORE UPDATE ON rewards_catalog FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();
CREATE TRIGGER tr_reward_claims_updated_at BEFORE UPDATE ON reward_claims FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();

-- Triggers de intereses
CREATE TRIGGER tr_increment_offer_interests AFTER INSERT ON offer_interests FOR EACH ROW EXECUTE FUNCTION fn_increment_offer_interests();
CREATE TRIGGER tr_decrement_offer_interests AFTER UPDATE ON offer_interests FOR EACH ROW EXECUTE FUNCTION fn_decrement_offer_interests();

-- Triggers de auditoría
CREATE TRIGGER tr_audit_offers AFTER INSERT OR UPDATE OR DELETE ON offers FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();
CREATE TRIGGER tr_audit_exchanges AFTER INSERT OR UPDATE OR DELETE ON exchanges FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();
CREATE TRIGGER tr_audit_users AFTER INSERT OR UPDATE OR DELETE ON users FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();
CREATE TRIGGER tr_audit_exchange_ratings AFTER INSERT OR UPDATE OR DELETE ON exchange_ratings FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();
CREATE TRIGGER tr_audit_reward_claims AFTER INSERT OR UPDATE OR DELETE ON reward_claims FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();
CREATE TRIGGER tr_audit_content_flags AFTER INSERT OR UPDATE OR DELETE ON content_flags FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();

-- Triggers de reputación
CREATE TRIGGER tr_update_reputation_exchange AFTER INSERT OR UPDATE ON exchanges FOR EACH ROW WHEN (NEW.status = 'completed') EXECUTE FUNCTION fn_auto_update_reputation();
CREATE TRIGGER tr_update_reputation_rating AFTER INSERT OR UPDATE ON exchange_ratings FOR EACH ROW EXECUTE FUNCTION fn_auto_update_reputation();

-- Trigger de validación de créditos
CREATE TRIGGER tr_validate_credits BEFORE INSERT ON credits_ledger FOR EACH ROW EXECUTE FUNCTION fn_validate_credits_balance();

-- ================================================================
-- VISTAS
-- ================================================================

-- Vista: Landing Stats
CREATE OR REPLACE VIEW v_landing_stats AS
SELECT
    (SELECT COUNT(*) FROM offers WHERE status = 'active' AND deleted_at IS NULL) as active_offers,
    (SELECT COUNT(*) FROM exchanges WHERE status = 'completed' AND deleted_at IS NULL) as completed_exchanges,
    (SELECT COUNT(*) FROM users WHERE status = 'active' AND deleted_at IS NULL) as active_users,
    (SELECT COALESCE(SUM(sustainability_points), 0) FROM users WHERE deleted_at IS NULL) as total_sustainability_points;

-- Vista: Dashboard de Administrador
CREATE OR REPLACE VIEW v_admin_dashboard AS
SELECT
    (SELECT COUNT(*) FROM users WHERE status = 'active' AND deleted_at IS NULL) as total_active_users,
    (SELECT COUNT(*) FROM users WHERE status = 'pending_verification' AND deleted_at IS NULL) as pending_verification_users,
    (SELECT COUNT(*) FROM users WHERE created_at >= CURRENT_DATE - INTERVAL '7 days' AND deleted_at IS NULL) as new_users_week,
    (SELECT COUNT(*) FROM users WHERE created_at >= CURRENT_DATE - INTERVAL '30 days' AND deleted_at IS NULL) as new_users_month,
    (SELECT COUNT(*) FROM offers WHERE status = 'active' AND deleted_at IS NULL) as total_active_offers,
    (SELECT COUNT(*) FROM offers WHERE status = 'flagged' AND deleted_at IS NULL) as flagged_offers,
    (SELECT COUNT(*) FROM offers WHERE created_at >= CURRENT_DATE - INTERVAL '7 days' AND deleted_at IS NULL) as new_offers_week,
    (SELECT COUNT(*) FROM exchanges WHERE status = 'completed' AND deleted_at IS NULL) as total_completed_exchanges,
    (SELECT COUNT(*) FROM exchanges WHERE status = 'pending' AND deleted_at IS NULL) as pending_exchanges,
    (SELECT COUNT(*) FROM exchanges WHERE status = 'disputed' AND deleted_at IS NULL) as disputed_exchanges,
    (SELECT COUNT(*) FROM exchanges WHERE completed_at >= CURRENT_DATE - INTERVAL '7 days' AND deleted_at IS NULL) as exchanges_completed_week,
    (SELECT COUNT(*) FROM content_flags WHERE status = 'pending' AND deleted_at IS NULL) as pending_flags,
    (SELECT COALESCE(SUM(amount), 0) FROM credits_ledger WHERE amount > 0 AND deleted_at IS NULL) as total_credits_issued,
    (SELECT COALESCE(SUM(sustainability_points), 0) FROM users WHERE deleted_at IS NULL) as total_sustainability_points;

-- Vista: Leaderboard de usuarios
CREATE OR REPLACE VIEW v_user_leaderboard AS
SELECT
    u.id, u.full_name, u.profile_photo_url, f.name as faculty_name,
    u.sustainability_points, u.level,
    COALESCE(urm.total_exchanges, 0) as total_exchanges,
    COALESCE(urm.successful_exchanges, 0) as successful_exchanges,
    COALESCE(urm.average_rating, 0) as average_rating,
    RANK() OVER (ORDER BY u.sustainability_points DESC) as overall_rank,
    RANK() OVER (PARTITION BY u.faculty_id ORDER BY u.sustainability_points DESC) as faculty_rank
FROM users u
LEFT JOIN faculties f ON u.faculty_id = f.id
LEFT JOIN user_reputation_metrics urm ON u.id = urm.user_id
WHERE u.status = 'active' AND u.deleted_at IS NULL
ORDER BY u.sustainability_points DESC;

-- Vista: Actividad reciente
CREATE OR REPLACE VIEW v_recent_activity AS
SELECT * FROM (
    SELECT 'offer_created'::VARCHAR(50) as activity_type, o.id::TEXT as entity_id, o.title as description,
        o.user_id, u.full_name as user_name, o.created_at
    FROM offers o JOIN users u ON o.user_id = u.id
    WHERE o.created_at >= CURRENT_DATE - INTERVAL '7 days' AND o.deleted_at IS NULL AND u.deleted_at IS NULL
    UNION ALL
    SELECT 'exchange_completed'::VARCHAR(50), e.id::TEXT, CONCAT('Intercambio de: ', o.title),
        e.seller_id, u.full_name, e.completed_at
    FROM exchanges e
    JOIN offers o ON e.offer_id = o.id JOIN users u ON e.seller_id = u.id
    WHERE e.status = 'completed' AND e.completed_at >= CURRENT_DATE - INTERVAL '7 days'
    AND e.deleted_at IS NULL AND o.deleted_at IS NULL AND u.deleted_at IS NULL
    UNION ALL
    SELECT 'user_registered'::VARCHAR(50), u.id::TEXT, CONCAT('Nuevo usuario: ', u.full_name),
        u.id, u.full_name, u.created_at
    FROM users u WHERE u.created_at >= CURRENT_DATE - INTERVAL '7 days' AND u.deleted_at IS NULL
) activities ORDER BY created_at DESC LIMIT 100;

-- Vista: Salud de ofertas
CREATE OR REPLACE VIEW v_offers_health AS
SELECT c.id as category_id, c.name as category_name,
    COUNT(*) as total_offers,
    COUNT(*) FILTER (WHERE o.status = 'active') as active_offers,
    COUNT(*) FILTER (WHERE o.status = 'completed') as completed_offers,
    COUNT(*) FILTER (WHERE o.status = 'cancelled') as cancelled_offers,
    COUNT(*) FILTER (WHERE o.status = 'flagged') as flagged_offers,
    COUNT(*) FILTER (WHERE o.expires_at < CURRENT_TIMESTAMP AND o.status = 'active') as expired_offers,
    COUNT(*) FILTER (WHERE o.created_at >= CURRENT_DATE - INTERVAL '30 days') as offers_last_month,
    ROUND(AVG(o.views_count), 2) as avg_views,
    ROUND(AVG(o.interests_count), 2) as avg_interests
FROM categories c
LEFT JOIN offers o ON c.id = o.category_id AND o.deleted_at IS NULL
WHERE c.is_active = TRUE AND c.deleted_at IS NULL
GROUP BY c.id, c.name ORDER BY total_offers DESC;

-- Vista: Métricas de intercambios
CREATE OR REPLACE VIEW v_exchange_metrics AS
SELECT DATE_TRUNC('month', created_at) as month,
    COUNT(*) as total_exchanges,
    COUNT(*) FILTER (WHERE status = 'completed') as completed,
    COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled,
    COUNT(*) FILTER (WHERE status = 'disputed') as disputed,
    ROUND(COUNT(*) FILTER (WHERE status = 'completed')::DECIMAL / NULLIF(COUNT(*), 0) * 100, 2) as completion_rate,
    ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 86400) FILTER (WHERE status = 'completed'), 2) as avg_days_to_complete,
    SUM(credits_amount) FILTER (WHERE status = 'completed') as total_credits_exchanged
FROM exchanges
WHERE created_at >= CURRENT_DATE - INTERVAL '12 months' AND deleted_at IS NULL
GROUP BY DATE_TRUNC('month', created_at) ORDER BY month DESC;

-- Vista: Progreso de retos
CREATE OR REPLACE VIEW v_challenges_progress AS
SELECT ch.id, ch.title, ch.description, ch.frequency, ch.difficulty,
    ch.points_reward, ch.credits_reward, ch.start_date, ch.end_date,
    ch.requirement_type, ch.requirement_value,
    COUNT(DISTINCT uc.user_id) as total_participants,
    COUNT(DISTINCT uc.user_id) FILTER (WHERE uc.is_completed = TRUE) as completions,
    ROUND(COUNT(DISTINCT uc.user_id) FILTER (WHERE uc.is_completed = TRUE)::DECIMAL / NULLIF(COUNT(DISTINCT uc.user_id), 0) * 100, 2) as completion_rate,
    CASE WHEN ch.end_date < CURRENT_TIMESTAMP THEN 'ended' WHEN ch.start_date > CURRENT_TIMESTAMP THEN 'upcoming' ELSE 'active' END as challenge_status
FROM challenges ch
LEFT JOIN user_challenges uc ON ch.id = uc.challenge_id AND uc.deleted_at IS NULL
WHERE ch.is_active = TRUE AND ch.deleted_at IS NULL
GROUP BY ch.id ORDER BY ch.end_date DESC;

-- Vista: Cola de moderación
CREATE OR REPLACE VIEW v_moderation_queue AS
SELECT cf.id, cf.flag_type, cf.description, cf.status, cf.created_at,
    reporter.id as reporter_id, reporter.full_name as reporter_name, reporter.email as reporter_email,
    o.id as offer_id, o.title as offer_title,
    offer_owner.id as offer_owner_id, offer_owner.full_name as offer_owner_name,
    e.id as exchange_id, e.status as exchange_status,
    EXTRACT(HOURS FROM CURRENT_TIMESTAMP - cf.created_at) as hours_in_queue
FROM content_flags cf
JOIN users reporter ON cf.reporter_user_id = reporter.id AND reporter.deleted_at IS NULL
LEFT JOIN offers o ON cf.offer_id = o.id AND o.deleted_at IS NULL
LEFT JOIN users offer_owner ON o.user_id = offer_owner.id AND offer_owner.deleted_at IS NULL
LEFT JOIN exchanges e ON cf.exchange_id = e.id AND e.deleted_at IS NULL
WHERE cf.status = 'pending' AND cf.deleted_at IS NULL
ORDER BY cf.created_at ASC;

-- Vista: Análisis de créditos
CREATE OR REPLACE VIEW v_credits_analysis AS
SELECT DATE_TRUNC('month', created_at) as month, transaction_type,
    COUNT(*) as transaction_count, SUM(amount) as total_amount, AVG(amount)::INTEGER as avg_amount
FROM credits_ledger
WHERE created_at >= CURRENT_DATE - INTERVAL '12 months' AND deleted_at IS NULL
GROUP BY DATE_TRUNC('month', created_at), transaction_type
ORDER BY month DESC, transaction_type;

-- Vista: Resumen de facultades
CREATE OR REPLACE VIEW v_faculty_summary AS
SELECT f.id, f.name, f.code,
    COUNT(DISTINCT u.id) as total_users,
    COUNT(DISTINCT u.id) FILTER (WHERE u.status = 'active') as active_users,
    SUM(u.sustainability_points) as total_points,
    ROUND(AVG(u.sustainability_points), 2) as avg_points_per_user,
    COUNT(DISTINCT o.id) as total_offers,
    COUNT(DISTINCT e.id) FILTER (WHERE e.status = 'completed') as completed_exchanges,
    RANK() OVER (ORDER BY SUM(u.sustainability_points) DESC) as faculty_rank
FROM faculties f
LEFT JOIN users u ON f.id = u.faculty_id AND u.deleted_at IS NULL
LEFT JOIN offers o ON u.id = o.user_id AND o.deleted_at IS NULL
LEFT JOIN exchanges e ON (u.id = e.buyer_id OR u.id = e.seller_id) AND e.deleted_at IS NULL
WHERE f.is_active = TRUE AND f.deleted_at IS NULL
GROUP BY f.id, f.name, f.code
ORDER BY total_points DESC NULLS LAST;

-- Vista: Reporte de transacciones
CREATE OR REPLACE VIEW v_transactions_report AS
SELECT o.id, o.title, o.description, o.status, o.condition, o.credits_value,
    o.views_count, o.interests_count, o.is_featured, o.created_at, o.updated_at,
    u.id as owner_id, u.full_name as owner_name, u.email as owner_email,
    c.id as category_id, c.name as category_name,
    l.id as location_id, l.name as location_name,
    fa.id as faculty_id, fa.name as faculty_name,
    (SELECT COUNT(*) FROM exchanges e WHERE e.offer_id = o.id AND e.deleted_at IS NULL) as total_exchanges,
    (SELECT COUNT(*) FROM exchanges e WHERE e.offer_id = o.id AND e.status = 'completed' AND e.deleted_at IS NULL) as completed_exchanges,
    (SELECT COUNT(*) FROM offer_photos op WHERE op.offer_id = o.id AND op.deleted_at IS NULL) as photos_count,
    (SELECT photo_url FROM offer_photos op WHERE op.offer_id = o.id AND op.is_primary = TRUE AND op.deleted_at IS NULL LIMIT 1) as primary_photo_url
FROM offers o
JOIN users u ON o.user_id = u.id AND u.deleted_at IS NULL
LEFT JOIN categories c ON o.category_id = c.id
LEFT JOIN locations l ON o.location_id = l.id
LEFT JOIN faculties fa ON u.faculty_id = fa.id
WHERE o.deleted_at IS NULL
ORDER BY o.created_at DESC;

-- Vista: Reporte de auditoría
CREATE OR REPLACE VIEW v_audit_report AS
SELECT al.id, al.action_type, al.entity_type, al.entity_id, al.extra_data,
    al.ip_address, al.user_agent, al.created_at,
    u.id as user_id, u.full_name as user_name, u.email as user_email, u.role as user_role,
    f.name as user_faculty
FROM activity_log al
LEFT JOIN users u ON al.user_id = u.id
LEFT JOIN faculties f ON u.faculty_id = f.id
ORDER BY al.created_at DESC;

-- Vista: Reporte de triggers
CREATE OR REPLACE VIEW v_triggers_report AS
SELECT ah.id, ah.table_name, ah.record_id, ah.operation, ah.old_data, ah.new_data,
    ah.changed_fields, ah.ip_address, ah.user_agent, ah.created_at,
    u.id as changed_by_id, u.full_name as changed_by_name, u.email as changed_by_email, u.role as changed_by_role,
    CASE
        WHEN ah.operation = 'INSERT' THEN 'Registro creado'
        WHEN ah.operation = 'UPDATE' THEN 'Registro actualizado (' || COALESCE(array_length(ah.changed_fields, 1), 0) || ' campos)'
        WHEN ah.operation = 'DELETE' THEN 'Registro eliminado'
        ELSE ah.operation::TEXT
    END as operation_summary,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - ah.created_at)) / 3600 as hours_ago
FROM audit_history ah
LEFT JOIN users u ON ah.changed_by = u.id
ORDER BY ah.created_at DESC;

-- ================================================================
-- DATOS INICIALES
-- ================================================================

-- Facultades PUCE
INSERT INTO faculties (name, code) VALUES
    ('Facultad de Ingenieria', 'FING'),
    ('Facultad de Ciencias Administrativas y Contables', 'FCAC'),
    ('Facultad de Medicina', 'FMED'),
    ('Facultad de Comunicacion', 'FCOM'),
    ('Facultad de Ciencias Humanas', 'FCH'),
    ('Facultad de Arquitectura y Diseno', 'FAD'),
    ('Facultad de Jurisprudencia', 'FJUR'),
    ('Facultad de Economia', 'FECO');

-- Categorias de objetos
INSERT INTO categories (name, description, icon) VALUES
    ('Libros y Apuntes', 'Libros academicos, apuntes y material de estudio', '📚'),
    ('Material Academico', 'Calculadoras, materiales de laboratorio, instrumentos', '🗂️'),
    ('Ropa Universitaria', 'Uniformes, camisetas, chompas con logo PUCE', '👕'),
    ('Accesorios Electronicos', 'Cargadores, cables, mouse, teclados', '🔌'),
    ('Equipos de Laboratorio', 'Material de laboratorio reutilizable', '🧪');

-- Ubicaciones del campus
INSERT INTO locations (name, description, latitude, longitude) VALUES
    ('Biblioteca Central', 'Entrada principal de la biblioteca', -0.173144, -78.486092),
    ('Cafeteria Central', 'Zona de cafeteria principal', -0.173200, -78.486150),
    ('Edificio de Ingenieria', 'Lobby del edificio de ingenieria', -0.173050, -78.486000),
    ('Plaza Central', 'Plaza central del campus', -0.173100, -78.486100);

-- Catalogo de Insignias
INSERT INTO badges_catalog (id, name, description, icon, category, unlock_criteria, unlock_type, unlock_value, rarity, points_value) VALUES
    ('first_exchange', 'Primer Intercambio', 'Completa tu primer intercambio exitoso', '🌱', 'milestone', 'Completar 1 intercambio', 'exchange_count', 1, 'common', 10),
    ('frequent_trader', 'Reutilizador Frecuente', 'Completa 10 intercambios', '♻️', 'achievement', 'Completar 10 intercambios', 'exchange_count', 10, 'rare', 50),
    ('top_faculty', 'Top Facultad', 'Lidera el ranking de tu facultad', '🏆', 'achievement', 'Alcanzar el primer lugar en tu facultad', 'custom', 0, 'epic', 100),
    ('eco_warrior', 'Estudiante Consciente', 'Completa todos los retos de un mes', '🌍', 'achievement', 'Completar todos los retos mensuales', 'custom', 0, 'legendary', 200),
    ('hundred_points', 'Centenario', 'Alcanza 100 puntos de sostenibilidad', '💯', 'milestone', 'Acumular 100 puntos', 'points_total', 100, 'common', 20),
    ('book_master', 'Maestro Bibliotecario', 'Intercambia 15 libros o apuntes', '📚', 'category', 'Intercambiar 15 items de categoria Libros', 'category_specific', 15, 'rare', 75),
    ('streak_week', 'Semana Activa', 'Manten actividad durante 7 dias consecutivos', '🔥', 'achievement', 'Mantener racha de 7 dias', 'streak_days', 7, 'rare', 50);

-- Retos Iniciales
INSERT INTO challenges (title, description, frequency, difficulty, points_reward, credits_reward, badge_reward, start_date, end_date, requirement_type, requirement_value, icon, educational_content) VALUES
    ('Primer Paso Verde', 'Realiza tu primer intercambio y contribuye a la economia circular', 'weekly', 'easy', 10, 5, 'first_exchange', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '7 days', 'exchange_count', 1, '🌱', 'La economia circular busca mantener productos y materiales en uso el mayor tiempo posible, reduciendo residuos.'),
    ('Semana del Libro', 'Intercambia un libro academico esta semana', 'weekly', 'easy', 15, 0, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '7 days', 'category_specific', 1, '📚', 'Reutilizar libros academicos reduce la demanda de papel y ayuda a otros estudiantes a ahorrar.'),
    ('Reutilizador Activo', 'Completa 3 intercambios en un mes', 'monthly', 'medium', 50, 20, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '30 days', 'exchange_count', 3, '♻️', 'Cada intercambio que realizas evita la produccion de un nuevo producto, reduciendo emisiones de CO2.');

-- ================================================================
-- PERMISOS
-- ================================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- ================================================================
-- STORED PROCEDURES - Operaciones Criticas
-- Garantizan atomicidad y validacion de reglas de negocio
-- ================================================================

-- ================================================================
-- SP 1: sp_complete_exchange (CRITICO)
-- Completa intercambio con confirmacion dual, transferencia de
-- creditos y actualizacion de puntos de forma atomica.
-- ================================================================

CREATE OR REPLACE FUNCTION sp_complete_exchange(
    p_exchange_id UUID,
    p_user_id UUID,
    p_is_buyer BOOLEAN
) RETURNS JSON AS $$
DECLARE
    v_exchange RECORD;
    v_buyer_balance INTEGER;
    v_seller_balance INTEGER;
    v_result JSON;
BEGIN
    -- 1. Lock del exchange para evitar race conditions
    SELECT * INTO v_exchange
    FROM exchanges
    WHERE id = p_exchange_id AND deleted_at IS NULL
    FOR UPDATE;

    -- 2. Validaciones de negocio
    IF v_exchange IS NULL THEN
        RAISE EXCEPTION 'Intercambio no encontrado';
    END IF;

    IF v_exchange.status NOT IN ('accepted', 'in_progress') THEN
        RAISE EXCEPTION 'Estado invalido para confirmar: %', v_exchange.status;
    END IF;

    -- 3. Validar que el usuario es parte del intercambio
    IF p_is_buyer AND v_exchange.buyer_id != p_user_id THEN
        RAISE EXCEPTION 'Usuario no es el comprador de este intercambio';
    END IF;

    IF NOT p_is_buyer AND v_exchange.seller_id != p_user_id THEN
        RAISE EXCEPTION 'Usuario no es el vendedor de este intercambio';
    END IF;

    -- 4. Actualizar confirmacion segun rol
    IF p_is_buyer THEN
        IF v_exchange.buyer_confirmed THEN
            RAISE EXCEPTION 'Comprador ya confirmo';
        END IF;
        UPDATE exchanges SET
            buyer_confirmed = TRUE,
            buyer_confirmed_at = NOW(),
            updated_at = NOW()
        WHERE id = p_exchange_id;
    ELSE
        IF v_exchange.seller_confirmed THEN
            RAISE EXCEPTION 'Vendedor ya confirmo';
        END IF;
        UPDATE exchanges SET
            seller_confirmed = TRUE,
            seller_confirmed_at = NOW(),
            updated_at = NOW()
        WHERE id = p_exchange_id;
    END IF;

    -- 5. Recargar exchange para verificar si ambos confirmaron
    SELECT * INTO v_exchange FROM exchanges WHERE id = p_exchange_id;

    IF v_exchange.buyer_confirmed AND v_exchange.seller_confirmed THEN
        -- 6. Validar balance del buyer ANTES de transferir
        SELECT COALESCE(SUM(amount), 0) INTO v_buyer_balance
        FROM credits_ledger
        WHERE user_id = v_exchange.buyer_id AND deleted_at IS NULL;

        IF v_buyer_balance < v_exchange.credits_amount THEN
            RAISE EXCEPTION 'Saldo insuficiente: tiene % creditos, necesita %',
                v_buyer_balance, v_exchange.credits_amount;
        END IF;

        -- 7. Obtener balance actual del seller
        SELECT COALESCE(SUM(amount), 0) INTO v_seller_balance
        FROM credits_ledger
        WHERE user_id = v_exchange.seller_id AND deleted_at IS NULL;

        -- 8. Completar intercambio
        UPDATE exchanges SET
            status = 'completed',
            completed_at = NOW(),
            updated_at = NOW()
        WHERE id = p_exchange_id;

        -- 9. Registrar evento de completado
        INSERT INTO exchange_events (exchange_id, event_type, triggered_by, extra_data)
        VALUES (p_exchange_id, 'completed', p_user_id, '{"auto_completed": true}'::JSONB);

        -- 10. Actualizar oferta a completada
        UPDATE offers SET
            status = 'completed',
            updated_at = NOW()
        WHERE id = v_exchange.offer_id;

        -- 11. Transferir creditos: debito al buyer
        INSERT INTO credits_ledger (user_id, transaction_type, amount, balance_after, reference_id, description)
        VALUES (
            v_exchange.buyer_id,
            'exchange_payment',
            -v_exchange.credits_amount,
            v_buyer_balance - v_exchange.credits_amount,
            p_exchange_id,
            'Pago por intercambio completado'
        );

        -- 12. Transferir creditos: credito al seller
        INSERT INTO credits_ledger (user_id, transaction_type, amount, balance_after, reference_id, description)
        VALUES (
            v_exchange.seller_id,
            'exchange_received',
            v_exchange.credits_amount,
            v_seller_balance + v_exchange.credits_amount,
            p_exchange_id,
            'Recepcion por intercambio completado'
        );

        -- 13. Otorgar puntos de sostenibilidad a ambos usuarios
        UPDATE users SET
            sustainability_points = sustainability_points + 10,
            experience_points = experience_points + 15,
            updated_at = NOW()
        WHERE id IN (v_exchange.buyer_id, v_exchange.seller_id)
        AND deleted_at IS NULL;

        -- 14. Actualizar metricas de reputacion
        UPDATE user_reputation_metrics SET
            total_exchanges = total_exchanges + 1,
            successful_exchanges = successful_exchanges + 1,
            updated_at = NOW()
        WHERE user_id IN (v_exchange.buyer_id, v_exchange.seller_id);

        -- 15. Crear notificaciones para ambos usuarios
        INSERT INTO notifications (user_id, type, title, message, reference_id, reference_type)
        VALUES
            (v_exchange.buyer_id, 'exchange_completed', 'Intercambio completado',
             'Tu intercambio ha sido completado exitosamente. +10 puntos de sostenibilidad',
             p_exchange_id, 'exchange'),
            (v_exchange.seller_id, 'exchange_completed', 'Intercambio completado',
             'Tu intercambio ha sido completado exitosamente. +10 puntos de sostenibilidad',
             p_exchange_id, 'exchange');

        v_result := json_build_object(
            'success', TRUE,
            'status', 'completed',
            'message', 'Intercambio completado exitosamente',
            'credits_transferred', v_exchange.credits_amount,
            'points_awarded', 10
        );
    ELSE
        v_result := json_build_object(
            'success', TRUE,
            'status', 'waiting',
            'message', 'Esperando confirmacion de la otra parte',
            'buyer_confirmed', v_exchange.buyer_confirmed,
            'seller_confirmed', v_exchange.seller_confirmed
        );
    END IF;

    RETURN v_result;

EXCEPTION WHEN OTHERS THEN
    RAISE;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sp_complete_exchange IS
'Procedimiento para completar intercambios de forma atomica.
Garantiza: confirmacion dual, validacion de saldo, transferencia de creditos,
otorgamiento de puntos y notificaciones. Usa FOR UPDATE para evitar race conditions.';

-- ================================================================
-- SP 2: sp_claim_reward (CRITICO)
-- Reclama una recompensa validando stock y balance atomicamente.
-- ================================================================

CREATE OR REPLACE FUNCTION sp_claim_reward(
    p_user_id UUID,
    p_reward_id INTEGER
) RETURNS JSON AS $$
DECLARE
    v_reward RECORD;
    v_user_balance INTEGER;
    v_new_balance INTEGER;
    v_claim_id INTEGER;
BEGIN
    -- 1. Lock del reward para evitar overselling
    SELECT * INTO v_reward
    FROM rewards_catalog
    WHERE id = p_reward_id AND deleted_at IS NULL
    FOR UPDATE;

    -- 2. Validaciones
    IF v_reward IS NULL THEN
        RAISE EXCEPTION 'Recompensa no encontrada';
    END IF;

    IF NOT v_reward.is_active THEN
        RAISE EXCEPTION 'Recompensa no disponible actualmente';
    END IF;

    IF v_reward.stock_quantity IS NOT NULL AND v_reward.stock_quantity <= 0 THEN
        RAISE EXCEPTION 'Sin stock disponible para esta recompensa';
    END IF;

    -- 3. Obtener balance actual del usuario
    SELECT COALESCE(SUM(amount), 0) INTO v_user_balance
    FROM credits_ledger
    WHERE user_id = p_user_id AND deleted_at IS NULL;

    IF v_user_balance < v_reward.credits_cost THEN
        RAISE EXCEPTION 'Saldo insuficiente: tiene % creditos, necesita %',
            v_user_balance, v_reward.credits_cost;
    END IF;

    -- 4. Decrementar stock si aplica
    IF v_reward.stock_quantity IS NOT NULL THEN
        UPDATE rewards_catalog
        SET stock_quantity = stock_quantity - 1,
            updated_at = NOW()
        WHERE id = p_reward_id;
    END IF;

    -- 5. Crear registro de claim
    INSERT INTO reward_claims (user_id, reward_id, status, credits_spent)
    VALUES (p_user_id, p_reward_id, 'pending', v_reward.credits_cost)
    RETURNING id INTO v_claim_id;

    -- 6. Registrar transaccion de creditos
    v_new_balance := v_user_balance - v_reward.credits_cost;

    INSERT INTO credits_ledger (user_id, transaction_type, amount, balance_after, reference_id, description)
    VALUES (
        p_user_id,
        'reward_claim',
        -v_reward.credits_cost,
        v_new_balance,
        v_claim_id::TEXT::UUID,
        'Canje de recompensa: ' || v_reward.name
    );

    -- 7. Crear notificacion
    INSERT INTO notifications (user_id, type, title, message, reference_id, reference_type)
    VALUES (
        p_user_id,
        'reward_claimed',
        'Recompensa canjeada',
        'Has canjeado exitosamente: ' || v_reward.name || '. Un moderador procesara tu solicitud.',
        v_claim_id,
        'reward'
    );

    RETURN json_build_object(
        'success', TRUE,
        'claim_id', v_claim_id,
        'reward_name', v_reward.name,
        'credits_spent', v_reward.credits_cost,
        'new_balance', v_new_balance
    );

EXCEPTION WHEN OTHERS THEN
    RAISE;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sp_claim_reward IS
'Procedimiento para canjear recompensas de forma atomica.
Garantiza: validacion de stock (FOR UPDATE), validacion de balance,
registro de claim y transaccion de creditos. Previene overselling.';

-- ================================================================
-- SP 3: sp_create_exchange (ALTO)
-- Crea un intercambio validando disponibilidad de oferta.
-- ================================================================

CREATE OR REPLACE FUNCTION sp_create_exchange(
    p_buyer_id UUID,
    p_offer_id UUID,
    p_proposed_location_id INTEGER DEFAULT NULL,
    p_proposed_datetime TIMESTAMP DEFAULT NULL,
    p_message TEXT DEFAULT NULL
) RETURNS JSON AS $$
DECLARE
    v_offer RECORD;
    v_exchange_id UUID;
    v_conversation_id UUID;
BEGIN
    -- 1. Lock de la oferta para evitar doble reserva
    SELECT * INTO v_offer
    FROM offers
    WHERE id = p_offer_id AND deleted_at IS NULL
    FOR UPDATE;

    -- 2. Validaciones
    IF v_offer IS NULL THEN
        RAISE EXCEPTION 'Oferta no encontrada';
    END IF;

    IF v_offer.status != 'active' THEN
        RAISE EXCEPTION 'Oferta no disponible, estado actual: %', v_offer.status;
    END IF;

    IF v_offer.user_id = p_buyer_id THEN
        RAISE EXCEPTION 'No puedes intercambiar tu propia oferta';
    END IF;

    -- 3. Verificar que no exista intercambio pendiente del mismo usuario
    IF EXISTS (
        SELECT 1 FROM exchanges
        WHERE offer_id = p_offer_id
        AND buyer_id = p_buyer_id
        AND status IN ('pending', 'accepted', 'in_progress')
        AND deleted_at IS NULL
    ) THEN
        RAISE EXCEPTION 'Ya existe un intercambio activo tuyo para esta oferta';
    END IF;

    -- 4. Crear intercambio
    INSERT INTO exchanges (
        offer_id, buyer_id, seller_id, credits_amount,
        proposed_location_id, proposed_datetime, status
    ) VALUES (
        p_offer_id, p_buyer_id, v_offer.user_id, v_offer.credits_value,
        p_proposed_location_id, p_proposed_datetime, 'pending'
    ) RETURNING id INTO v_exchange_id;

    -- 5. Registrar evento de creacion
    INSERT INTO exchange_events (exchange_id, event_type, triggered_by, extra_data)
    VALUES (v_exchange_id, 'created', p_buyer_id,
        json_build_object('message', p_message, 'proposed_location_id', p_proposed_location_id)::JSONB);

    -- 6. Reservar oferta
    UPDATE offers SET
        status = 'reserved',
        updated_at = NOW()
    WHERE id = p_offer_id;

    -- 7. Crear o obtener conversacion existente
    SELECT id INTO v_conversation_id
    FROM conversations
    WHERE offer_id = p_offer_id
    AND ((user1_id = p_buyer_id AND user2_id = v_offer.user_id)
         OR (user1_id = v_offer.user_id AND user2_id = p_buyer_id))
    AND deleted_at IS NULL;

    IF v_conversation_id IS NULL THEN
        INSERT INTO conversations (offer_id, user1_id, user2_id)
        VALUES (p_offer_id, p_buyer_id, v_offer.user_id)
        RETURNING id INTO v_conversation_id;
    END IF;

    -- 8. Crear mensaje inicial si se proporciono
    IF p_message IS NOT NULL AND p_message != '' THEN
        INSERT INTO messages (conversation_id, sender_id, content)
        VALUES (v_conversation_id, p_buyer_id, p_message);

        UPDATE conversations SET
            last_message_at = NOW(),
            updated_at = NOW()
        WHERE id = v_conversation_id;
    END IF;

    -- 9. Crear notificacion al vendedor
    INSERT INTO notifications (user_id, type, title, message, reference_id, reference_type)
    VALUES (
        v_offer.user_id,
        'exchange_proposed',
        'Nueva propuesta de intercambio',
        'Tienes una nueva propuesta para: ' || v_offer.title,
        v_exchange_id,
        'exchange'
    );

    RETURN json_build_object(
        'success', TRUE,
        'exchange_id', v_exchange_id,
        'conversation_id', v_conversation_id,
        'status', 'pending',
        'offer_title', v_offer.title
    );

EXCEPTION WHEN OTHERS THEN
    RAISE;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sp_create_exchange IS
'Procedimiento para crear intercambios de forma atomica.
Garantiza: disponibilidad de oferta (FOR UPDATE), creacion de exchange,
reserva de oferta, creacion de conversacion y notificacion.';

-- ================================================================
-- SP 4: sp_cancel_exchange (ALTO)
-- Cancela un intercambio y libera la oferta.
-- ================================================================

CREATE OR REPLACE FUNCTION sp_cancel_exchange(
    p_exchange_id UUID,
    p_user_id UUID,
    p_reason TEXT
) RETURNS JSON AS $$
DECLARE
    v_exchange RECORD;
    v_other_user_id UUID;
BEGIN
    -- 1. Lock del exchange
    SELECT * INTO v_exchange
    FROM exchanges
    WHERE id = p_exchange_id AND deleted_at IS NULL
    FOR UPDATE;

    -- 2. Validaciones
    IF v_exchange IS NULL THEN
        RAISE EXCEPTION 'Intercambio no encontrado';
    END IF;

    IF v_exchange.buyer_id != p_user_id AND v_exchange.seller_id != p_user_id THEN
        RAISE EXCEPTION 'No tienes permiso para cancelar este intercambio';
    END IF;

    IF v_exchange.status = 'completed' THEN
        RAISE EXCEPTION 'No se puede cancelar un intercambio completado';
    END IF;

    IF v_exchange.status = 'cancelled' THEN
        RAISE EXCEPTION 'El intercambio ya esta cancelado';
    END IF;

    -- 3. Determinar el otro usuario para notificacion
    IF v_exchange.buyer_id = p_user_id THEN
        v_other_user_id := v_exchange.seller_id;
    ELSE
        v_other_user_id := v_exchange.buyer_id;
    END IF;

    -- 4. Cancelar intercambio
    UPDATE exchanges SET
        status = 'cancelled',
        cancellation_reason = p_reason,
        updated_at = NOW()
    WHERE id = p_exchange_id;

    -- 5. Registrar evento de cancelacion
    INSERT INTO exchange_events (exchange_id, event_type, triggered_by, extra_data)
    VALUES (p_exchange_id, 'cancelled', p_user_id,
        json_build_object('reason', p_reason, 'cancelled_by', p_user_id)::JSONB);

    -- 6. Liberar oferta (volver a estado activo)
    UPDATE offers SET
        status = 'active',
        updated_at = NOW()
    WHERE id = v_exchange.offer_id
    AND status = 'reserved'
    AND deleted_at IS NULL;

    -- 7. Notificar a la otra parte
    INSERT INTO notifications (user_id, type, title, message, reference_id, reference_type)
    VALUES (
        v_other_user_id,
        'exchange_cancelled',
        'Intercambio cancelado',
        'El intercambio ha sido cancelado. Razon: ' || COALESCE(p_reason, 'No especificada'),
        p_exchange_id,
        'exchange'
    );

    RETURN json_build_object(
        'success', TRUE,
        'status', 'cancelled',
        'offer_released', TRUE,
        'reason', p_reason
    );

EXCEPTION WHEN OTHERS THEN
    RAISE;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sp_cancel_exchange IS
'Procedimiento para cancelar intercambios de forma atomica.
Garantiza: validacion de permisos, actualizacion de estado,
liberacion de oferta y notificacion a la otra parte.';

-- ================================================================
-- SP 5: sp_complete_challenge (ALTO)
-- Completa un reto otorgando puntos, creditos y badges.
-- ================================================================

CREATE OR REPLACE FUNCTION sp_complete_challenge(
    p_user_id UUID,
    p_challenge_id INTEGER
) RETURNS JSON AS $$
DECLARE
    v_challenge RECORD;
    v_user_challenge RECORD;
    v_current_balance INTEGER;
    v_new_balance INTEGER;
BEGIN
    -- 1. Obtener challenge
    SELECT * INTO v_challenge
    FROM challenges
    WHERE id = p_challenge_id AND deleted_at IS NULL;

    IF v_challenge IS NULL THEN
        RAISE EXCEPTION 'Reto no encontrado';
    END IF;

    IF NOT v_challenge.is_active THEN
        RAISE EXCEPTION 'Este reto no esta activo actualmente';
    END IF;

    -- 2. Obtener progreso del usuario con lock
    SELECT * INTO v_user_challenge
    FROM user_challenges
    WHERE user_id = p_user_id AND challenge_id = p_challenge_id
    AND deleted_at IS NULL
    FOR UPDATE;

    IF v_user_challenge IS NULL THEN
        RAISE EXCEPTION 'Usuario no inscrito en este reto';
    END IF;

    IF v_user_challenge.is_completed THEN
        RAISE EXCEPTION 'Este reto ya fue completado';
    END IF;

    IF v_user_challenge.current_progress < v_challenge.requirement_value THEN
        RAISE EXCEPTION 'Progreso insuficiente: % de % requerido',
            v_user_challenge.current_progress, v_challenge.requirement_value;
    END IF;

    -- 3. Marcar como completado
    UPDATE user_challenges SET
        is_completed = TRUE,
        completed_at = NOW(),
        updated_at = NOW()
    WHERE user_id = p_user_id AND challenge_id = p_challenge_id;

    -- 4. Otorgar puntos de sostenibilidad y experiencia
    UPDATE users SET
        sustainability_points = sustainability_points + v_challenge.points_reward,
        experience_points = experience_points + v_challenge.points_reward,
        updated_at = NOW()
    WHERE id = p_user_id AND deleted_at IS NULL;

    -- 5. Otorgar creditos si el reto tiene recompensa de creditos
    IF v_challenge.credits_reward > 0 THEN
        SELECT COALESCE(SUM(amount), 0) INTO v_current_balance
        FROM credits_ledger
        WHERE user_id = p_user_id AND deleted_at IS NULL;

        v_new_balance := v_current_balance + v_challenge.credits_reward;

        INSERT INTO credits_ledger (user_id, transaction_type, amount, balance_after, description)
        VALUES (
            p_user_id,
            'challenge_reward',
            v_challenge.credits_reward,
            v_new_balance,
            'Recompensa por completar reto: ' || v_challenge.title
        );
    ELSE
        v_new_balance := NULL;
    END IF;

    -- 6. Otorgar badge si el reto tiene uno asociado
    IF v_challenge.badge_reward IS NOT NULL THEN
        INSERT INTO user_badges (user_id, badge_id, earned_at)
        VALUES (p_user_id, v_challenge.badge_reward, NOW())
        ON CONFLICT (user_id, badge_id) DO NOTHING;
    END IF;

    -- 7. Actualizar contador de completados del reto
    UPDATE challenges SET
        completions_count = COALESCE(completions_count, 0) + 1,
        updated_at = NOW()
    WHERE id = p_challenge_id;

    -- 8. Crear notificacion
    INSERT INTO notifications (user_id, type, title, message, reference_id, reference_type)
    VALUES (
        p_user_id,
        'challenge_completed',
        'Reto completado!',
        'Has completado el reto: ' || v_challenge.title || '. Ganaste ' ||
        v_challenge.points_reward || ' puntos' ||
        CASE WHEN v_challenge.credits_reward > 0
             THEN ' y ' || v_challenge.credits_reward || ' creditos'
             ELSE '' END ||
        CASE WHEN v_challenge.badge_reward IS NOT NULL
             THEN '. Tambien desbloqueaste una insignia!'
             ELSE '' END,
        p_challenge_id,
        'challenge'
    );

    RETURN json_build_object(
        'success', TRUE,
        'challenge_title', v_challenge.title,
        'points_awarded', v_challenge.points_reward,
        'credits_awarded', COALESCE(v_challenge.credits_reward, 0),
        'badge_awarded', v_challenge.badge_reward,
        'new_credits_balance', v_new_balance
    );

EXCEPTION WHEN OTHERS THEN
    RAISE;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sp_complete_challenge IS
'Procedimiento para completar retos de forma atomica.
Garantiza: validacion de progreso, otorgamiento de puntos,
creditos (si aplica), badges (si aplica) y notificacion.';

-- ================================================================
-- SP 6: sp_transfer_credits (ALTO)
-- Transferencia segura de creditos entre usuarios.
-- ================================================================

CREATE OR REPLACE FUNCTION sp_transfer_credits(
    p_from_user_id UUID,
    p_to_user_id UUID,
    p_amount INTEGER,
    p_reason TEXT DEFAULT 'Transferencia manual'
) RETURNS JSON AS $$
DECLARE
    v_from_balance INTEGER;
    v_to_balance INTEGER;
    v_from_user RECORD;
    v_to_user RECORD;
BEGIN
    -- 1. Validaciones basicas
    IF p_amount <= 0 THEN
        RAISE EXCEPTION 'El monto debe ser positivo';
    END IF;

    IF p_from_user_id = p_to_user_id THEN
        RAISE EXCEPTION 'No puedes transferir creditos a ti mismo';
    END IF;

    -- 2. Verificar que ambos usuarios existen y estan activos
    SELECT * INTO v_from_user
    FROM users
    WHERE id = p_from_user_id AND deleted_at IS NULL;

    IF v_from_user IS NULL THEN
        RAISE EXCEPTION 'Usuario origen no encontrado';
    END IF;

    SELECT * INTO v_to_user
    FROM users
    WHERE id = p_to_user_id AND deleted_at IS NULL;

    IF v_to_user IS NULL THEN
        RAISE EXCEPTION 'Usuario destino no encontrado';
    END IF;

    -- 3. Obtener balance origen (con lock implicito por la transaccion)
    SELECT COALESCE(SUM(amount), 0) INTO v_from_balance
    FROM credits_ledger
    WHERE user_id = p_from_user_id AND deleted_at IS NULL;

    IF v_from_balance < p_amount THEN
        RAISE EXCEPTION 'Saldo insuficiente: tiene % creditos, intenta transferir %',
            v_from_balance, p_amount;
    END IF;

    -- 4. Obtener balance destino
    SELECT COALESCE(SUM(amount), 0) INTO v_to_balance
    FROM credits_ledger
    WHERE user_id = p_to_user_id AND deleted_at IS NULL;

    -- 5. Debito del usuario origen
    INSERT INTO credits_ledger (user_id, transaction_type, amount, balance_after, description)
    VALUES (
        p_from_user_id,
        'transfer_out',
        -p_amount,
        v_from_balance - p_amount,
        p_reason || ' (a ' || v_to_user.full_name || ')'
    );

    -- 6. Credito al usuario destino
    INSERT INTO credits_ledger (user_id, transaction_type, amount, balance_after, description)
    VALUES (
        p_to_user_id,
        'transfer_in',
        p_amount,
        v_to_balance + p_amount,
        p_reason || ' (de ' || v_from_user.full_name || ')'
    );

    -- 7. Notificar al receptor
    INSERT INTO notifications (user_id, type, title, message, reference_type)
    VALUES (
        p_to_user_id,
        'credits_received',
        'Creditos recibidos',
        'Has recibido ' || p_amount || ' creditos de ' || v_from_user.full_name || '. Motivo: ' || p_reason,
        'credits'
    );

    RETURN json_build_object(
        'success', TRUE,
        'amount', p_amount,
        'from_user', v_from_user.full_name,
        'to_user', v_to_user.full_name,
        'from_new_balance', v_from_balance - p_amount,
        'to_new_balance', v_to_balance + p_amount
    );

EXCEPTION WHEN OTHERS THEN
    RAISE;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sp_transfer_credits IS
'Procedimiento para transferir creditos entre usuarios de forma atomica.
Garantiza: validacion de balance, registro de ambas transacciones
(debito y credito) y notificacion al receptor.';

-- ================================================================
-- VERIFICACION FINAL
-- ================================================================

DO $$
DECLARE
    v_table_count INTEGER;
    v_view_count INTEGER;
    v_function_count INTEGER;
    v_trigger_count INTEGER;
    v_sp_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_table_count FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    SELECT COUNT(*) INTO v_view_count FROM information_schema.views WHERE table_schema = 'public';
    SELECT COUNT(*) INTO v_function_count FROM information_schema.routines WHERE routine_schema = 'public' AND routine_type = 'FUNCTION';
    SELECT COUNT(*) INTO v_trigger_count FROM information_schema.triggers WHERE trigger_schema = 'public';
    SELECT COUNT(*) INTO v_sp_count FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name LIKE 'sp_%';

    RAISE NOTICE '==========================================';
    RAISE NOTICE 'REUSE Database initialized successfully';
    RAISE NOTICE 'Tables: %', v_table_count;
    RAISE NOTICE 'Views: %', v_view_count;
    RAISE NOTICE 'Functions: %', v_function_count;
    RAISE NOTICE 'Triggers: %', v_trigger_count;
    RAISE NOTICE 'Stored Procedures: %', v_sp_count;
    RAISE NOTICE 'Soft Delete: ENABLED on all tables';
    RAISE NOTICE '==========================================';
END $$;
