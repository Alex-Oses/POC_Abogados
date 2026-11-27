-- MariaDB 11.4+ · equivalente de migrations/V1__create_usuarios.sql
-- UUID -> CHAR(36) ascii_bin; gen_random_uuid() -> UUID(); TIMESTAMPTZ -> DATETIME(6) UTC.
-- Ver README.md (matriz de tipos y funciones).

CREATE TABLE usuarios (
    id              CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT (UUID()),
    email           VARCHAR(255) NOT NULL,
    nombre_completo VARCHAR(200) NOT NULL,
    rol             VARCHAR(50) NOT NULL
                    COMMENT 'Columna histórica; V15 la sustituye por usuarios_roles (transcriptor, revisor, admin)',
    activo          BOOLEAN NOT NULL DEFAULT true,
    creado_en       DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    actualizado_en  DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_usuarios PRIMARY KEY (id),
    CONSTRAINT uq_usuarios_email UNIQUE (email),
    CONSTRAINT chk_usuarios_rol CHECK (rol IN ('transcriptor', 'revisor', 'admin', 'supervisor'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Personal del sistema: transcriptores, revisores, admins';
