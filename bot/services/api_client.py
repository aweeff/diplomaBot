import requests
from bot.config import BACKEND_URL
from typing import Optional, Dict, Any, List

def _make_request(method: str, endpoint: str, cookies: Optional[Dict] = None, json_data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
    url = f"{BACKEND_URL}{endpoint}"
    try:
        response = requests.request(method, url, json=json_data, cookies=cookies, params=params)
        response.raise_for_status()
        if response.status_code == 204:
             return {"success": True, "data": None}
        return {"success": True, "data": response.json()}
    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error occurred: {http_err}"
        try:
            error_details = http_err.response.json()
            error_message = error_details.get("message", str(http_err.response.text))
        except ValueError:
            error_message = str(http_err.response.text if http_err.response.text else http_err)
        return {"success": False, "error": error_message, "status_code": http_err.response.status_code if http_err.response else None}
    except requests.exceptions.RequestException as req_err:
        return {"success": False, "error": f"Request exception: {req_err}"}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

def login_user(email: str, password: str) -> Dict[str, Any]:
    try:
        s = requests.Session()
        response = s.post(f"{BACKEND_URL}/api/auth/login", json={"email": email, "password": password})
        response.raise_for_status()
        return {"success": True, "data": response.json(), "cookies": s.cookies.get_dict()}
    except requests.exceptions.HTTPError as http_err:
        error_message = "Login failed."
        try:
            error_details = http_err.response.json()
            error_message = error_details.get("message", str(http_err.response.text))
        except ValueError:
            error_message = str(http_err.response.text if http_err.response.text else http_err) 
        return {"success": False, "error": error_message, "status_code": http_err.response.status_code if http_err.response else None}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


def register_user(full_name: str, email: str, password: str) -> Dict[str, Any]:
    try:
        s = requests.Session()
        response = s.post(f"{BACKEND_URL}/api/auth/signup", json={"fullName": full_name, "email": email, "password": password})
        response.raise_for_status()
        return {"success": True, "data": response.json(), "cookies": s.cookies.get_dict()}
    except requests.exceptions.HTTPError as http_err:
        error_message = "Registration failed."
        try:
            error_details = http_err.response.json()
            error_message = error_details.get("message", str(http_err.response.text))
        except ValueError:
             error_message = str(http_err.response.text if http_err.response.text else http_err)
        return {"success": False, "error": error_message, "status_code": http_err.response.status_code if http_err.response else None}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


def logout_user(cookies: Dict) -> Dict[str, Any]:
    return _make_request("POST", "/api/auth/logout", cookies=cookies)

def check_auth_status(cookies: Dict) -> Dict[str, Any]:
    return _make_request("GET", "/api/auth/check", cookies=cookies)

def update_user_profile(cookies: Dict, profile_data: Dict) -> Dict[str, Any]:
    return _make_request("PUT", "/api/auth/update-profile", cookies=cookies, json_data=profile_data)

# --- Books ---
def get_all_books(cookies: Optional[Dict] = None) -> Dict[str, Any]:
    return _make_request("GET", "/api/books", cookies=cookies)

def get_my_books(cookies: Dict) -> Dict[str, Any]:
    return _make_request("GET", "/api/books/my-books", cookies=cookies)

def create_book(cookies: Dict, book_data: Dict) -> Dict[str, Any]:
    return _make_request("POST", "/api/books/create", cookies=cookies, json_data=book_data)

def update_book(cookies: Dict, book_id: str, book_data: Dict) -> Dict[str, Any]:
    return _make_request("PUT", f"/api/books/update/{book_id}", cookies=cookies, json_data=book_data)

def delete_book(cookies: Dict, book_id: str) -> Dict[str, Any]:
    return _make_request("DELETE", f"/api/books/{book_id}", cookies=cookies)

def get_all_categories(cookies: Dict) -> Dict[str, Any]:
    return _make_request("GET", "/api/books/categories", cookies=cookies)

def update_user_preferences(cookies: Dict, category_ids: List[str]) -> Dict[str, Any]:
    return _make_request("POST", "/api/auth/update-preferences", cookies=cookies, json_data={"preferences": category_ids})

def get_user_current_preferences(cookies: Dict) -> Dict[str, Any]:
    auth_status = check_auth_status(cookies)
    if auth_status["success"] and auth_status["data"]:
        return {"success": True, "data": auth_status["data"].get("preferences")}
    return {"success": False, "error": auth_status.get("error", "Could not fetch user preferences")}


# --- User ---
async def get_user_by_id_async(owner_id: str, cookies: dict):
    import aiohttp # Local import for async function
    try:
        url = f"{BACKEND_URL}/api/user/{owner_id}"
        async with aiohttp.ClientSession(cookies=cookies) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    text = await response.text()
                    return {"success": False, "error": f"Error {response.status}: {text}", "status_code": response.status}
                data = await response.json()
                return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": f"[get_user_by_id_async] Exception: {e}"}