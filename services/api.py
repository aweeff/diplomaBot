import requests
import db

def login_user(email, password):
    try:
        response = requests.post(f"{db.BACKEND_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return {"success": True, "user": response.json()}
        return {"success": False, "message": response.json().get("message", "Ошибка входа")}
    except Exception as e:
        return {"success": False, "message": str(e)}
