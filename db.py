import asyncpg
from datetime import date

class DB:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(dsn=self.dsn, min_size=1, max_size=5)

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def ensure_user(self, telegram_id: int, username: str | None, role_if_new: str):
        assert self.pool
        await self.pool.execute(
            """
            INSERT INTO users(telegram_id, username, role)
            VALUES ($1, $2, $3)
            ON CONFLICT (telegram_id) DO UPDATE
              SET username = EXCLUDED.username,
                  is_active = TRUE
            """,
            telegram_id, username, role_if_new
        )

    async def get_user_role(self, telegram_id: int) -> str | None:
        assert self.pool
        return await self.pool.fetchval(
            "SELECT role FROM users WHERE telegram_id=$1 AND is_active=TRUE",
            telegram_id
        )

    async def list_machines(self):
        assert self.pool
        return await self.pool.fetch("SELECT id, name FROM machines ORDER BY id")

    async def get_status(self, machine_id: int):
        assert self.pool
        row = await self.pool.fetchrow(
            """
            SELECT m.name, s.last_service_date, s.last_water_date,
                   i.cups, i.lids, i.milk, i.chocolate, i.coffee
            FROM machines m
            JOIN machine_status s ON s.machine_id=m.id
            JOIN inventory i ON i.machine_id=m.id
            WHERE m.id=$1
            """,
            machine_id
        )
        return row

    async def set_today(self, machine_id: int, by: int, field: str):
        """field: 'SERVICE' or 'WATER'"""
        assert self.pool
        today = date.today()
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                if field == "SERVICE":
                    await conn.execute(
                        "UPDATE machine_status SET last_service_date=$2, updated_at=NOW() WHERE machine_id=$1",
                        machine_id, today
                    )
                else:
                    await conn.execute(
                        "UPDATE machine_status SET last_water_date=$2, updated_at=NOW() WHERE machine_id=$1",
                        machine_id, today
                    )
                await conn.execute(
                    "INSERT INTO status_log(machine_id, changed_by, field, new_date) VALUES ($1,$2,$3,$4)",
                    machine_id, by, field, today
                )

    async def change_inventory(self, machine_id: int, by: int, action: str, item: str, qty: int, comment: str | None = None):
        """
        action: ADD/SUB
        item: cups/lids/milk/chocolate/coffee
        qty: >0
        """
        assert self.pool
        col = item  # safe because item is from fixed set in UI
        delta = qty if action == "ADD" else -qty

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # запрет минуса при SUB
                if action == "SUB":
                    current = await conn.fetchval(f"SELECT {col} FROM inventory WHERE machine_id=$1 FOR UPDATE", machine_id)
                    if current is None:
                        raise ValueError("Inventory not found")
                    if current < qty:
                        return False  # не хватает

                await conn.execute(
                    f"UPDATE inventory SET {col} = {col} + $2, updated_at=NOW() WHERE machine_id=$1",
                    machine_id, delta
                )
                await conn.execute(
                    """
                    INSERT INTO inventory_log(machine_id, changed_by, action, item, qty, comment)
                    VALUES ($1,$2,$3,$4,$5,$6)
                    """,
                    machine_id, by, action, item, qty, comment
                )
        return True
