import asyncio
import httpx
import sys

BASE_URL = "http://localhost:8000/api/v1"

async def main():
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Login
        login_res = await client.post(f"{BASE_URL}/auth/login", json={
            "email": "e2e_tester@vendorclear.com",
            "password": "Password123!"
        })
        if login_res.status_code != 200:
            print(f"Login failed: {login_res.text}")
            sys.exit(1)
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get first vendor
        v_res = await client.get(f"{BASE_URL}/vendors?skip=0&limit=1", headers=headers)
        vendors = v_res.json()["data"] if "data" in v_res.json() else v_res.json()
        if not vendors:
            print("No vendors found!")
            sys.exit(1)
        
        vid = vendors[0]["id"]
        print(f"Testing endpoints for Vendor ID: {vid}")
        
        for ep in [f"/vendors/{vid}", f"/vendors/{vid}/documents", f"/dashboard/vendors/{vid}/score"]:
            print(f"GET {ep}")
            res = await client.get(f"{BASE_URL}{ep}", headers=headers)
            print(f"Status: {res.status_code}")
            if res.status_code == 200:
                print(f"Response: {str(res.json())[:200]}...")
            else:
                print(f"Response: {res.text}")

if __name__ == "__main__":
    asyncio.run(main())
