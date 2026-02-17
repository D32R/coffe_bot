from aiogram.fsm.state import State, StatesGroup

class InvQty(StatesGroup):
    waiting_qty = State()
