-- ====== TABLES ======

CREATE TABLE IF NOT EXISTS machines (
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
  machine_id INT PRIMARY KEY REFERENCES machines(id) ON DELETE CASCADE,
  cups INT NOT NULL DEFAULT 0,
  lids INT NOT NULL DEFAULT 0,
  milk INT NOT NULL DEFAULT 0,
  chocolate INT NOT NULL DEFAULT 0,
  coffee INT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS machine_status (
  machine_id INT PRIMARY KEY REFERENCES machines(id) ON DELETE CASCADE,
  last_service_date DATE,
  last_water_date DATE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Логи склада (без users / без FK на changed_by)
CREATE TABLE IF NOT EXISTS inventory_log (
  id BIGSERIAL PRIMARY KEY,
  machine_id INT NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
  changed_by BIGINT NOT NULL,
  changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  action TEXT NOT NULL CHECK (action IN ('ADD','SUB')),
  item TEXT NOT NULL CHECK (item IN ('cups','lids','milk','chocolate','coffee')),
  qty INT NOT NULL CHECK (qty > 0),
  comment TEXT
);

-- Логи дат (без users / без FK на changed_by)
CREATE TABLE IF NOT EXISTS status_log (
  id BIGSERIAL PRIMARY KEY,
  machine_id INT NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
  changed_by BIGINT NOT NULL,
  changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  field TEXT NOT NULL CHECK (field IN ('SERVICE','WATER')),
  new_date DATE NOT NULL
);

-- ====== INIT 4 MACHINES ======

INSERT INTO machines(name) VALUES
  ('КЕРУЕН'), ('АДЕЛИЯ'), ('ИНМАРТ'), ('ДЕКО')
ON CONFLICT (name) DO NOTHING;

-- Пустой склад и статус для всех точек
INSERT INTO inventory(machine_id)
SELECT id FROM machines
ON CONFLICT (machine_id) DO NOTHING;

INSERT INTO machine_status(machine_id)
SELECT id FROM machines
ON CONFLICT (machine_id) DO NOTHING;
