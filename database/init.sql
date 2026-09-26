-- ==========================================
-- MedSim Database Schema Initialization
-- ==========================================

-- 1. mannequins table
CREATE TABLE mannequins (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    age_range VARCHAR(20),
    character_description TEXT,
    voice_config JSONB,
    ip_address INET NOT NULL,
    esp32_port INTEGER DEFAULT 80,
    allowed_topics TEXT[],
    forbidden_topics TEXT[],
    system_prompt TEXT NOT NULL,
    use_preset_audio BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. scenarios table
CREATE TABLE scenarios (
    id SERIAL PRIMARY KEY,
    mannequin_id INTEGER REFERENCES mannequins(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    difficulty_level VARCHAR(20) CHECK (difficulty_level IN ('oson', 'o''rta', 'qiyin')),
    expected_actions JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. script_qa table
CREATE TABLE script_qa (
    id SERIAL PRIMARY KEY,
    mannequin_id INTEGER REFERENCES mannequins(id) ON DELETE CASCADE,
    scenario_id INTEGER REFERENCES scenarios(id) ON DELETE CASCADE,
    trigger_keywords TEXT[] NOT NULL,
    trigger_pattern VARCHAR(500),
    question_template TEXT,
    answer_template TEXT NOT NULL,
    emotion VARCHAR(50) DEFAULT 'oddiy',
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 4. audio_presets table
CREATE TABLE audio_presets (
    id SERIAL PRIMARY KEY,
    mannequin_id INTEGER REFERENCES mannequins(id) ON DELETE CASCADE,
    trigger_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    duration_seconds FLOAT,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 5. sessions table
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    mannequin_id INTEGER REFERENCES mannequins(id) ON DELETE CASCADE,
    scenario_id INTEGER REFERENCES scenarios(id) ON DELETE CASCADE,
    nurse_name VARCHAR(100),
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    score INTEGER,
    feedback TEXT
);

-- 6. session_logs table
CREATE TABLE session_logs (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    speaker VARCHAR(20) NOT NULL CHECK (speaker IN ('nurse', 'mannequin')),
    message_text TEXT,
    audio_file_path VARCHAR(500),
    response_time_ms INTEGER,
    emotion_detected VARCHAR(50),
    matched_script_id INTEGER REFERENCES script_qa(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ==========================================
-- Indexes for performance
-- ==========================================
CREATE INDEX idx_mannequins_slug ON mannequins(slug);
CREATE INDEX idx_scenarios_mannequin_id ON scenarios(mannequin_id);
CREATE INDEX idx_script_qa_mannequin_id ON script_qa(mannequin_id);
CREATE INDEX idx_script_qa_scenario_id ON script_qa(scenario_id);
CREATE INDEX idx_sessions_mannequin_id ON sessions(mannequin_id);
CREATE INDEX idx_session_logs_session_id ON session_logs(session_id);
