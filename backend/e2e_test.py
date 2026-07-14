import asyncio
import httpx
import sys

BASE_URL = "http://localhost:8000/api/v1"

async def main():
    async with httpx.AsyncClient(timeout=120.0) as client:
        print("0. Registering test user...")
        # Ignore errors if user already exists
        await client.post(f"{BASE_URL}/auth/register", json={
            "email": "e2e_tester@vendorclear.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "full_name": "E2E Tester"
        })
        
        print("0.5. Logging in...")
        login_res = await client.post(f"{BASE_URL}/auth/login", json={
            "email": "e2e_tester@vendorclear.com",
            "password": "Password123!"
        })
        if login_res.status_code != 200:
            print(f"Login failed: {login_res.text}")
            sys.exit(1)
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        print("1. Creating Test Vendor...")
        res = await client.post(f"{BASE_URL}/vendors", json={
            "name": "E2E Test Vendor LLC",
            "email": "e2e@example.com",
            "contact_name": "Test Contact"
        }, headers=headers)
        if res.status_code != 201:
            print(f"Failed to create vendor: {res.text}")
            sys.exit(1)
        vendor = res.json()
        vendor_id = vendor["id"]
        print(f"Created vendor {vendor['name']} with ID: {vendor_id}\n")

        files_to_test = [
            ("test_documents/sample_coi_compliant.pdf", "COI", "COMPLIANT"),
            ("test_documents/sample_coi_expired.pdf", "COI", "NON_COMPLIANT"),
            ("test_documents/sample_diversity_cert.png", "DIVERSITY_CERT", "COMPLIANT"),
        ]

        for filepath, doc_type, expected_status in files_to_test:
            print(f"--- Testing {filepath} ---")
            with open(filepath, "rb") as f:
                print(f"Uploading file...")
                content_type = "application/pdf" if filepath.endswith(".pdf") else "image/png"
                # Note: Setting a long timeout because Gemini/OCR takes time
                upload_res = await client.post(
                    f"{BASE_URL}/vendors/{vendor_id}/documents",
                    data={"doc_type_hint": doc_type},
                    files={"file": (filepath.split("/")[-1], f, content_type)},
                    headers=headers,
                    timeout=120.0
                )
            
            if upload_res.status_code != 201:
                print(f"Upload failed: {upload_res.status_code} {upload_res.text}")
                continue
                
            upload_data = upload_res.json()
            doc_id = upload_data["document"]["id"]
            print(f"Upload successful. Document ID: {doc_id}")

            print("Fetching analysis results...")
            analysis_res = await client.get(f"{BASE_URL}/vendors/{vendor_id}/documents/{doc_id}/analyses", headers=headers)
            analyses = analysis_res.json()
            
            if not analyses:
                print("No analysis found!")
                continue
                
            latest_analysis = analyses[0]
            status = latest_analysis["status"]
            print(f"Resulting Status: {status}")
            print(f"Expected Status: {expected_status}")
            print(f"Extracted Data: {latest_analysis.get('extracted_data', {})}")
            
            if status == expected_status:
                print("PASS")
            else:
                print("FAIL")
            
            print("Findings:")
            for finding in latest_analysis["findings"]:
                print(f"  - [{finding['severity']}] {finding['message']} (Field: {finding.get('field_name', 'N/A')})")
            print("\n")
            
        print("Done running E2E tests!")

if __name__ == "__main__":
    asyncio.run(main())
