sessions: dict = {}

def get_session(user_id):
    return sessions.get(user_id)

def set_session_data(user_id, key, value):
    if user_id not in sessions:
        sessions[user_id] = {}
    sessions[user_id][key] = value

def get_session_data(user_id, key, default=None):
    session = get_session(user_id)
    return session.get(key, default) if session else default

def clear_session_data(user_id, key):
    session = get_session(user_id)
    if session and key in session:
        del session[key]

def clear_entire_session(user_id):
    if user_id in sessions:
        del sessions[user_id]

def get_cookies(user_id):
    return get_session_data(user_id, "cookies")

def get_user(user_id):
    return get_session_data(user_id, "user")