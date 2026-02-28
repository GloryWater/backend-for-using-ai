# Copyright (c) 2026 Yauheni Sytsevich. All Rights Reserved.
# Unauthorized copying of this file, via any medium is strictly prohibited.
# Proprietary and confidential.

import logging
import os

import aiohttp


API_KEY = os.getenv("CRYPTOCLOUD_API_KEY")
SHOP_ID = os.getenv("CRYPTOCLOUD_SHOP_ID")

# Base URL
BASE_URL = "https://api.cryptocloud.plus/v2"


async def create_invoice(amount: float, order_id: str, currency: str = "USD"):
    """
    Creates an invoice.
    """
    url = f"{BASE_URL}/invoice/create"

    headers = {"Authorization": f"Token {API_KEY}", "Content-Type": "application/json"}

    payload = {
        "shop_id": SHOP_ID,
        "amount": amount,
        "currency": currency,  # Currency (USD), payment will be in crypto
        "order_id": order_id,  # Your unique order ID
        # "email": "user@example.com" # Optional
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                result = await response.json()

                # CryptoCloud returns status="success" or status_code=200
                if response.status == 200 and result.get("status") == "success":
                    return {
                        # Payment page URL
                        "url": result["result"]["link"],
                        # Invoice UUID for verification
                        "uuid": result["result"]["uuid"],
                    }
                else:
                    logging.error(f"CryptoCloud Error: {result}")
                    return None
        except Exception as e:
            logging.error(f"Request Error: {e}")
            return None


async def check_invoice_status(uuid: str):
    """
    Checks payment status by invoice UUID (not order_id!).
    """
    url = f"{BASE_URL}invoice/info"

    headers = {"Authorization": f"Token {API_KEY}", "Content-Type": "application/json"}

    payload = {"uuid": uuid}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                result = await response.json()

                if response.status == 200 and result.get("status") == "success":
                    # Statuses: created, paid, partial, canceled
                    payment_status = result["result"]["status"]
                    # Check if status is 'paid' (or 'overpaid' if exists)
                    return payment_status == "paid"
                return False
        except Exception as e:
            logging.error(f"Check Status Error: {e}")
            return False
