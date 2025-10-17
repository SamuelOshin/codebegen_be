BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> e011ab9dd223

CREATE TABLE users (
    email VARCHAR(255) NOT NULL, 
    username VARCHAR(50), 
    full_name VARCHAR(255), 
    hashed_password VARCHAR(255), 
    is_active BOOLEAN NOT NULL, 
    is_superuser BOOLEAN NOT NULL, 
    is_verified BOOLEAN NOT NULL, 
    avatar_url VARCHAR(500), 
    bio TEXT, 
    location VARCHAR(100), 
    website VARCHAR(500), 
    github_id INTEGER, 
    github_username VARCHAR(100), 
    github_access_token VARCHAR(500), 
    preferences JSON, 
    total_generations INTEGER NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (github_id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE UNIQUE INDEX ix_users_username ON users (username);

CREATE TABLE organizations (
    name VARCHAR(255) NOT NULL, 
    slug VARCHAR(100) NOT NULL, 
    description TEXT, 
    owner_id VARCHAR(36) NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    max_members INTEGER NOT NULL, 
    max_projects INTEGER NOT NULL, 
    subscription_plan VARCHAR(50) NOT NULL, 
    stripe_customer_id VARCHAR(100), 
    settings JSON, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE INDEX ix_organizations_name ON organizations (name);

CREATE UNIQUE INDEX ix_organizations_slug ON organizations (slug);

CREATE TABLE organization_members (
    organization_id VARCHAR(36) NOT NULL, 
    user_id VARCHAR(36) NOT NULL, 
    role VARCHAR(20) NOT NULL, 
    permissions JSON, 
    is_active BOOLEAN NOT NULL, 
    invited_by_id VARCHAR(36), 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(invited_by_id) REFERENCES users (id), 
    FOREIGN KEY(organization_id) REFERENCES organizations (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE projects (
    user_id VARCHAR(36) NOT NULL, 
    organization_id VARCHAR(36), 
    name VARCHAR(255) NOT NULL, 
    description TEXT, 
    domain VARCHAR(50), 
    tech_stack VARCHAR(50) NOT NULL, 
    constraints JSON, 
    status VARCHAR(20) NOT NULL, 
    is_public BOOLEAN NOT NULL, 
    github_repo_url VARCHAR(500), 
    github_repo_name VARCHAR(255), 
    settings JSON, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(organization_id) REFERENCES organizations (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_projects_name ON projects (name);

CREATE TABLE generations (
    project_id VARCHAR(36) NOT NULL, 
    user_id VARCHAR(36) NOT NULL, 
    prompt TEXT NOT NULL, 
    context JSON, 
    extracted_schema JSON, 
    output_files JSON, 
    review_feedback JSON, 
    documentation JSON, 
    quality_score FLOAT, 
    status VARCHAR(20) NOT NULL, 
    error_message TEXT, 
    schema_extraction_time FLOAT, 
    code_generation_time FLOAT, 
    review_time FLOAT, 
    docs_generation_time FLOAT, 
    total_time FLOAT, 
    is_iteration BOOLEAN NOT NULL, 
    parent_generation_id VARCHAR(36), 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(parent_generation_id) REFERENCES generations (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE artifacts (
    generation_id VARCHAR(36) NOT NULL, 
    type VARCHAR(20) NOT NULL, 
    storage_url VARCHAR(500) NOT NULL, 
    file_size INTEGER, 
    file_metadata JSON, 
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(generation_id) REFERENCES generations (id)
);

INSERT INTO alembic_version (version_num) VALUES ('e011ab9dd223') RETURNING alembic_version.version_num;

-- Running upgrade e011ab9dd223 -> 39e7f45c72f1

ALTER TABLE generations ADD COLUMN version INTEGER DEFAULT '1' NOT NULL;

ALTER TABLE generations ADD COLUMN version_name VARCHAR(50);

ALTER TABLE generations ADD COLUMN is_active BOOLEAN DEFAULT 'false' NOT NULL;

ALTER TABLE generations ADD COLUMN storage_path VARCHAR(500);

ALTER TABLE generations ADD COLUMN file_count INTEGER DEFAULT '0' NOT NULL;

ALTER TABLE generations ADD COLUMN total_size_bytes INTEGER;

ALTER TABLE generations ADD COLUMN diff_from_previous TEXT;

ALTER TABLE generations ADD COLUMN changes_summary JSON;

ALTER TABLE projects ADD COLUMN latest_version INTEGER DEFAULT '0' NOT NULL;

ALTER TABLE projects ADD COLUMN active_generation_id VARCHAR(36);

ALTER TABLE projects ADD CONSTRAINT fk_projects_active_generation FOREIGN KEY(active_generation_id) REFERENCES generations (id) ON DELETE SET NULL;

UPDATE generations g
        SET 
            version = subq.row_num,
            storage_path = './storage/projects/' || g.id
        FROM (
            SELECT 
                id,
                ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY created_at) as row_num
            FROM generations
        ) subq
        WHERE g.id = subq.id;

UPDATE projects p
        SET latest_version = COALESCE(
            (SELECT MAX(version)
             FROM generations g
             WHERE g.project_id = p.id),
            0
        );

UPDATE projects p
        SET active_generation_id = (
            SELECT g.id
            FROM generations g
            WHERE g.project_id = p.id
            AND g.status = 'completed'
            ORDER BY g.created_at DESC
            LIMIT 1
        );

UPDATE generations g
        SET is_active = true
        FROM projects p
        WHERE g.id = p.active_generation_id;

UPDATE alembic_version SET version_num='39e7f45c72f1' WHERE alembic_version.version_num = 'e011ab9dd223';

COMMIT;

