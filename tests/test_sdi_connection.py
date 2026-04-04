"""Quick test of OpenAPI SDI connection."""
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djafatt.settings.dev")
django.setup()

import httpx  # noqa: E402

from apps.common.exceptions import SdiClientError  # noqa: E402
from apps.sdi.services.openapi_client import OpenApiSdiClient  # noqa: E402

try:
    client = OpenApiSdiClient()
    print(f"Base URL: {client.base_url}")
    print(f"Token: {client.token[:6]}...{client.token[-4:]}")
    print()

    # Test 1: list supplier invoices
    print("--- GET /invoices?type=1&page=1&per_page=10 ---")
    result = client.get_supplier_invoices(page=1, per_page=10)
    print(f"Status: OK")
    print(f"Response keys: {list(result.keys())}")

    if "data" in result:
        invoices = result["data"]
        print(f"Fatture in pagina: {len(invoices)}")
        if result.get("meta"):
            print(f"Meta: {result['meta']}")
        for inv in invoices:
            print(f"  - {inv.get('number', '?')} | {inv.get('date', '?')} | {inv.get('sender_name', inv.get('sender', '?'))}")
    else:
        print(f"Full response: {result}")

except SdiClientError as e:
    print(f"SdiClientError: {e}")
except httpx.HTTPStatusError as e:
    print(f"HTTP Error {e.response.status_code}: {e.response.text[:500]}")
except Exception as e:
    print(f"Error ({type(e).__name__}): {e}")
