import aiohttp
import db


async def get_user_by_id(owner_id: str, cookies: dict):
    try:
        url = f"{db.BACKEND_URL}/api/user/{owner_id}"
        async with aiohttp.ClientSession(cookies=cookies) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    text = await response.text()
                    print(f"Error {response.status}: {text}")
                    return None
                data = await response.json()

                return {
                    "fullName": data.get("fullName"),
                    "telegramId": data.get("telegramId"),
                    "id": data.get("_id")
                }
    except Exception as e:
        print(f"[get_user_by_id] Exception: {e}")
        return None
