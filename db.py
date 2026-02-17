import asyncpg
from datetime import date

ALLOWED_ITEMS = {"cups", "lids", "milk", "chocolate", "coffee"}

class DB:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(dsn=self.dsn, min_size=1, max_size=5)

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def list_machines(self):
        assert self.pool
        return await self.pool.fetch("SELECT id, name FROM machines ORDER BY id")

    async def get_status(self, machine_id: int):
        assert self.pool
        return await self.pool.fetchrow(
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

    async def set_today(self, machine_id: int, by: int, field: str):
        assert self.pool
        today = date.today()
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                if field == "SERVICE":
                    await conn.execute(
                        "UPDATE machine_status SET last_service_date=$2, updated_at=NOW() WHERE machine_id=$1",
                        machine_id, today
                    )
                elif field == "WATER":
                    await conn.execute(
                        "UPDATE machine_status SET last_water_date=$2, updated_at=NOW() WHERE machine_id=$1",
                        machine_id, today
                    )
                else:
                    raise ValueError("Bad field")

                await conn.execute(
                    "INSERT INTO status_log(machine_id, changed_by, field, new_date) VALUES ($1,$2,$3,$4)",
                    machine_id, by, field, today
                )

    async def change_inventory(self, machine_id: int, by: int, action: str, item: str, qty: int):
        assert self.pool
        if item not in ALLOWED_ITEMS:
            raise ValueError("Bad item")
        if qty <= 0:
            raise ValueError("Bad qty")

        col = item
        delta = qty if action == "ADD" else -qty

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # запрет минуса при списании
                if action == "SUB":
                    current = await conn.fetchval(f"SELECT {col} FROM inventory WHERE machine_id=$1 FOR UPDATE", machine_id)
                    if current is None or current < qty:
                        return False

                await conn.execute(
                    f"UPDATE inventory SET {col} = {col} + $2, updated_at=NOW() WHERE machine_id=$1",
                    machine_id, delta
                )
                await conn.execute(
                    """
                    INSERT INTO inventory_log(machine_id, changed_by, action, item, qty)
                    VALUES ($1,$2,$3,$4,$5)
                    """,
                    machine_id, by, action, item, qty
                )
        return True

    async def apply_schema(self, sql_text: str):
        """Запуск schema.sql из кода (1 раз при старте)"""
        assert self.pool
        async with self.pool.acquire() as conn:
            await conn.execute(sql_text)
