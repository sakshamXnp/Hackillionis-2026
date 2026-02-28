"""Capital One Nessie API client using httpx.AsyncClient."""

import httpx

from app.config import get_settings


class CapitalOneClient:
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.capital_one_base_url
        self.api_key = settings.capital_one_api_key
        
        # Debug the API key load
        masked_key = f"{self.api_key[:5]}...{self.api_key[-5:]}" if self.api_key and len(self.api_key) >= 10 else str(self.api_key)
        print(f"DEBUG: Capital One API Key: {masked_key}")
        
        self.client = httpx.AsyncClient(timeout=30.0)

    def _url(self, endpoint: str) -> str:
        return f"{self.base_url}{endpoint}?key={self.api_key}"

    async def get_customers(self) -> list[dict]:
        """Fetch all customers from Capital One."""
        response = await self.client.get(self._url("/customers"))
        response.raise_for_status()
        return response.json()

    async def get_customer(self, customer_id: str) -> dict:
        """Fetch a specific customer by ID from Capital One."""
        response = await self.client.get(self._url(f"/customers/{customer_id}"))
        response.raise_for_status()
        return response.json()

    async def get_customer_accounts(self, customer_id: str) -> list[dict]:
        """Fetch accounts for a customer."""
        response = await self.client.get(
            self._url(f"/customers/{customer_id}/accounts")
        )
        response.raise_for_status()
        return response.json()

    async def get_accounts(self) -> list[dict]:
        """Fetch all accounts from Capital One."""
        response = await self.client.get(self._url("/accounts"))
        response.raise_for_status()
        return response.json()

    async def get_account(self, account_id: str) -> dict:
        """Fetch a specific account by ID from Capital One."""
        response = await self.client.get(self._url(f"/accounts/{account_id}"))
        response.raise_for_status()
        return response.json()

    async def get_account_transactions(self, account_id: str) -> list[dict]:
        """Fetch transactions for an account."""
        response = await self.client.get(
            self._url(f"/accounts/{account_id}/transactions")
        )
        response.raise_for_status()
        return response.json()

    async def create_customer(self, customer_data: dict) -> dict:
        """Create a new customer in Capital One API."""
        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            params = {"key": self.api_key}
            
            url = f"{self.base_url}/customers"
            print(f"DEBUG: Sending to {url}?key={self.api_key}, headers={headers}, body={customer_data}")
            
            response = await self.client.post(
                url,
                params=params,
                json=customer_data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error creating customer. Payload sent to Nessie: {customer_data}")
            if e.response is not None:
                print(f"Nessie API response body: {e.response.text}")
            raise

    async def create_account(self, customer_id: str, account_data: dict) -> dict:
        """Create a new account for a customer in Capital One API."""
        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            params = {"key": self.api_key}
            
            url = f"{self.base_url}/customers/{customer_id}/accounts"
            print(f"DEBUG: Sending to {url}?key={self.api_key}, headers={headers}, body={account_data}")
            
            response = await self.client.post(
                url,
                params=params,
                json=account_data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error creating account. Payload sent to Nessie: {account_data}")
            if e.response is not None:
                print(f"Nessie API response body: {e.response.text}")
            raise

    async def create_purchase(
        self,
        account_id: str,
        amount: float,
        description: str,
        merchant_id: str = "57cf75cea73e494d8675ec49",
    ) -> dict:
        """Create a purchase transaction."""
        payload = {
            "merchant_id": merchant_id,
            "medium": "balance",
            "purchase_date": "2024-01-01",
            "amount": amount,
            "description": description,
        }
        response = await self.client.post(
            self._url(f"/accounts/{account_id}/purchases"),
            json=payload,
        )
        response.raise_for_status()
        return response.json()
