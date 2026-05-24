from aiogram.fsm.state import State, StatesGroup


class ProfileStates(StatesGroup):
    """States for user profile collection dialog"""
    collecting = State()   # Chatting with Claude to gather info
    confirming = State()   # Showing profile summary, waiting for confirmation


class RouteStates(StatesGroup):
    """States for route navigation"""
    viewing = State()       # Viewing route overview
    viewing_step = State()  # Viewing a specific step
