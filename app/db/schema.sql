-- Esquema do catálogo de perfis / aços / projetos.
-- Nomes de coluna seguem literalmente os cabeçalhos das abas do Excel
-- ("ELU Compressão.xlsx"), eliminando o acesso posicional (v[0], v[1], ...)
-- usado pelos scripts originais (Codigocompleto.py / CodigocomPDF.py).

CREATE TABLE IF NOT EXISTS steel_types (
    designacao   TEXT PRIMARY KEY,
    fy_mpa       REAL NOT NULL,
    fu_mpa       REAL NOT NULL
);

-- Aba "Perfis W e HP" (perfis laminados: séries W e HP).
CREATE TABLE IF NOT EXISTS profiles_laminados (
    bitola           TEXT PRIMARY KEY,
    massa_linear_kgm REAL,
    d_mm             REAL NOT NULL,
    bf_mm            REAL NOT NULL,
    tw_mm            REAL NOT NULL,
    tf_mm            REAL NOT NULL,
    h_mm             REAL NOT NULL,
    d_linha_mm       REAL NOT NULL,
    ag_cm2           REAL NOT NULL,
    ix_cm4           REAL NOT NULL,
    wx_cm3           REAL,
    rx_cm            REAL NOT NULL,
    zx_cm3           REAL,
    iy_cm4           REAL NOT NULL,
    wy_cm3           REAL,
    ry_cm            REAL NOT NULL,
    zy_cm3           REAL,
    rt_cm            REAL,
    j_cm4            REAL NOT NULL,
    lambda_f         REAL,
    lambda_w         REAL,
    cw_cm6           REAL NOT NULL,
    u_m2m            REAL,
    bitola_in        TEXT
);

-- Aba "PerfilCS" (perfis soldados: série CS / built-up).
CREATE TABLE IF NOT EXISTS profiles_soldados (
    bitola           TEXT PRIMARY KEY,
    massa_linear_kgm REAL,
    ag_cm2           REAL NOT NULL,
    d_mm             REAL NOT NULL,
    tw_mm            REAL NOT NULL,
    h_mm             REAL NOT NULL,
    tf_mm            REAL NOT NULL,
    bf_mm            REAL NOT NULL,
    ix_cm4           REAL NOT NULL,
    wx_cm3           REAL,
    rx_cm            REAL NOT NULL,
    zx_cm3           REAL,
    iy_cm4           REAL NOT NULL,
    wy_cm3           REAL,
    ry_cm            REAL NOT NULL,
    zy_cm3           REAL,
    rt_cm            REAL,
    j_cm4            REAL NOT NULL,
    cw_cm5           REAL NOT NULL,
    h_tw             REAL,
    b_2tf            REAL,
    d_af_cm_1        REAL,
    ec_mm            REAL,
    u_m2m            REAL,
    u_a_m_1          REAL
);

-- Projetos de dimensionamento salvos pelo usuário. Guarda apenas os DADOS DE
-- ENTRADA: os resultados (Nc,Rd etc.) são sempre recalculados a partir do
-- catálogo atual quando o projeto é reaberto, para que edições no catálogo
-- se reflitam automaticamente em todos os projetos que usam aquele perfil/aço.
CREATE TABLE IF NOT EXISTS projects (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    nome              TEXT NOT NULL,
    autor             TEXT,
    criado_em         TEXT NOT NULL,
    atualizado_em     TEXT NOT NULL,
    family            TEXT NOT NULL CHECK (family IN ('laminado', 'soldado')),
    bitola            TEXT NOT NULL,
    steel_designacao  TEXT NOT NULL,
    ea_gpa            REAL NOT NULL DEFAULT 200,
    ga_gpa            REAL NOT NULL DEFAULT 77,
    ncsd_kn           REAL NOT NULL,
    kx                REAL NOT NULL DEFAULT 1.0,
    lx_m              REAL NOT NULL,
    ky                REAL NOT NULL DEFAULT 1.0,
    ly_m              REAL NOT NULL,
    kz                REAL NOT NULL DEFAULT 1.0,
    lz_m              REAL NOT NULL
);
