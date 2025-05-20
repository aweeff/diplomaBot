import requests
import db # Your existing db.py for BACKEND_URL
from state.session_store import sessions # Your existing session_store.py
from typing import List, Dict, Optional, Any

# --- API Helper Functions ---
async def get_all_categories(cookies: dict) -> Optional[List[Dict[str, Any]]]:
    """Fetches all available categories from the backend."""
    try:
        response = requests.get(f"{db.BACKEND_URL}/api/books/categories", cookies=cookies)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching categories: {e}")
        return None

async def update_user_preferences_api(category_ids: List[str], cookies: dict) -> bool:
    """Updates user's genre preferences on the backend."""
    try:
        payload = {"preferences": category_ids}
        response = requests.post(
            f"{db.BACKEND_URL}/api/auth/update-preferences",
            json=payload,
            cookies=cookies
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error updating preferences: {e} - {response.text if 'response' in locals() else ''}")
        return False

async def get_all_books_api(cookies: dict) -> Optional[List[Dict[str, Any]]]:
    """Fetches all books from the backend."""
    try:
        response = requests.get(f"{db.BACKEND_URL}/api/books", cookies=cookies)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching books: {e}")
        return None

async def get_user_current_preferences(cookies: dict) -> Optional[Dict[str, int]]:
    """Fetches the user's current preferences object from the backend."""
    try:
        response = requests.get(f"{db.BACKEND_URL}/api/auth/check", cookies=cookies)
        response.raise_for_status()
        user_data = response.json()
        return user_data.get("preferences") # This is an object like {"catId1": count, ...}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching user data for preferences: {e}")
        return None