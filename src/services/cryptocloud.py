import logging
import os

import aiohttp


API_KEY = os.getenv("CRYPTOCLOUD_API_KEY")
SHOP_ID = os.getenv("CRYPTOCLOUD_SHOP_ID")

# Базовый URL
BASE_URL = "https://api.cryptocloud.plus/v2"


async def create_invoice(amount: float, order_id: str, currency: str = "USD"):
    """
    Создает счет на оплату.
    """
    url = f"{BASE_URL}/invoice/create"

    headers = {"Authorization": f"Token {API_KEY}", "Content-Type": "application/json"}

    payload = {
        "shop_id": SHOP_ID,
        "amount": amount,
        "currency": currency,  # Валюта цены (USD), платить будут криптой
        "order_id": order_id,  # Твой уникальный ID заказа
        # "email": "user@example.com" # Можно не передавать
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                result = await response.json()

                # CryptoCloud возвращает status="success" или status_code=200
                if response.status == 200 and result.get("status") == "success":
                    return {
                        # Ссылка на страницу оплаты
                        "url": result["result"]["link"],
                        # UUID инвойса для проверки
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
    Проверяет статус платежа по UUID инвойса (не order_id!).
    """
    url = f"{BASE_URL}invoice/info"

    headers = {"Authorization": f"Token {API_KEY}", "Content-Type": "application/json"}

    payload = {"uuid": uuid}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                result = await response.json()

                if response.status == 200 and result.get("status") == "success":
                    # Статусы: created, paid, partial, canceled
                    payment_status = result["result"]["status"]
                    # Проверяем, что статус 'paid' (или 'overpaid' если есть)
                    return payment_status == "paid"
                return False
        except Exception as e:
            logging.error(f"Check Status Error: {e}")
            return False
