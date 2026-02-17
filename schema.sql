CREATE TABLE IF NOT EXISTS machines (
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
  telegram_id BIGINT PRIMARY KEY,
  username TEXT,
  role TEXT NOT NULL CHECK (role IN ('admin','staff')),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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

CREATE TABLE IF NOT EXISTS inventory_log (
  id BIGSERIAL PRIMARY KEY,
  machine_id INT NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
  changed_by BIGINT NOT NULL REFERENCES users(telegram_id),
  changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  action TEXT NOT NULL CHECK (action IN ('ADD','SUB')),
  item TEXT NOT NULL CHECK (item IN ('cups','lids','milk','chocolate','coffee')),
  qty INT NOT NULL CHECK (qty > 0),
  comment TEXT
);

CREATE TABLE IF NOT EXISTS status_log (
  id BIGSERIAL PRIMARY KEY,
  machine_id INT NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
  changed_by BIGINT NOT NULL REFERENCES users(telegram_id),
  changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  field TEXT NOT NULL CHECK (field IN ('SERVICE','WATER')),
  new_date DATE NOT NULL
);

-- 4 точки
INSERT INTO machines(name) VALUES
  ('КЕРУЕН'), ('АДЕЛИЯ'), ('ИНМАРТ'), ('ДЕКО')
ON CONFLICT (name) DO NOTHING;

-- пустой склад и статус
INSERT INTO inventory(machine_id)
SELECT id FROM machines
ON CONFLICT (machine_id) DO NOTHING;

INSERT INTO machine_status(machine_id)
SELECT id FROM machines
ON CONFLICT (machine_id) DO NOTHING;
