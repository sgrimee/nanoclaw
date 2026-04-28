"""
Tricount API client for read-only access to shared registries.

Usage:
    client = TricntClient(
        app_id="your_app_id",
        client_request_id="your_client_request_id",
        private_key_path="/path/to/private_key.pem"
    )
    client.authenticate()
    info = client.get_registry_info("your_registry_token")
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

logger = logging.getLogger(__name__)


@dataclass
class RegistryInfo:
    id: int
    title: str
    currency: str
    emoji: str
    web_link: str
    member_count: int
    expense_count: int


@dataclass
class Member:
    id: int
    name: str
    status: str


@dataclass
class Expense:
    id: int
    description: str
    amount: float
    currency: str
    date: str
    payer: str
    category: str
    beneficiaries: List[str]
    allocations: Dict[str, float]  # name -> actual amount owed per person


class TricntError(Exception):
    pass


class TricntClient:
    def __init__(
        self,
        app_id: str,
        client_request_id: str,
        private_key_path: str,
    ):
        self.base_url = "https://api.tricount.bunq.com"
        self.app_id = app_id
        self.client_request_id = client_request_id
        self.private_key_path = private_key_path

        self._session_token: Optional[str] = None
        self._user_id: Optional[int] = None
        self._http_client: Optional[httpx.Client] = None

    def _get_http_client(self) -> httpx.Client:
        if not self._http_client:
            self._http_client = httpx.Client(
                headers={
                    "User-Agent": "com.bunq.tricount.android:RELEASE:7.0.7:3174:ANDROID:13:C",
                    "app-id": self.app_id,
                    "X-Bunq-Client-Request-Id": self.client_request_id,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._http_client

    def _load_or_generate_key(self) -> RSAPrivateKey:
        try:
            with open(self.private_key_path, "rb") as f:
                key = serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )
                if not isinstance(key, rsa.RSAPrivateKey):
                    raise TricntError("Key file contains non-RSA key")
                return key
        except FileNotFoundError:
            key_dir = os.path.dirname(self.private_key_path)
            if key_dir:
                os.makedirs(key_dir, exist_ok=True)

            private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=2048, backend=default_backend()
            )

            pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )

            with open(self.private_key_path, "wb") as f:
                f.write(pem)
            os.chmod(self.private_key_path, 0o600)

            logger.info(f"Generated new private key at {self.private_key_path}")
            return private_key

    def _get_public_key_pem(self) -> str:
        private_key = self._load_or_generate_key()
        public_key = private_key.public_key()
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return pem.decode("utf-8")

    def authenticate(self) -> bool:
        """Authenticate with the Tricount API. Generates a new key pair if needed."""
        try:
            public_key = self._get_public_key_pem()

            response = self._get_http_client().post(
                f"{self.base_url}/v1/session-registry-installation",
                json={
                    "app_installation_uuid": self.app_id,
                    "client_public_key": public_key,
                    "device_description": "Android",
                },
            )

            if response.status_code != 200:
                raise TricntError(f"Authentication failed: HTTP {response.status_code}")

            data = response.json()

            self._session_token = None
            self._user_id = None

            for item in data.get("Response", []):
                if "Token" in item and not self._session_token:
                    self._session_token = item["Token"]["token"]
                elif "UserPerson" in item and not self._user_id:
                    self._user_id = item["UserPerson"]["id"]

            if not self._session_token or not self._user_id:
                raise TricntError("Authentication response missing token or user ID")

            self._get_http_client().headers["X-Bunq-Client-Authentication"] = (
                self._session_token
            )

            logger.info("Successfully authenticated with Tricount API")
            return True

        except httpx.RequestError as e:
            raise TricntError(f"Network error during authentication: {e}")

    def _get_registry_data(self, registry_token: str) -> Dict[str, Any]:
        if not self._user_id:
            raise TricntError("Not authenticated - call authenticate() first")

        try:
            response = self._get_http_client().get(
                f"{self.base_url}/v1/user/{self._user_id}/registry",
                params={"public_identifier_token": registry_token},
            )
            response.raise_for_status()

            data = response.json()
            if not data.get("Response"):
                raise TricntError(f"Registry {registry_token} not found")

            return data["Response"][0]["Registry"]

        except httpx.HTTPStatusError as e:
            raise TricntError(
                f"HTTP error getting registry data: {e.response.status_code}"
            )

    def get_registry_info(self, registry_token: str) -> RegistryInfo:
        if not self._user_id:
            raise TricntError("Not authenticated - call authenticate() first")

        try:
            response = self._get_http_client().get(
                f"{self.base_url}/v1/user/{self._user_id}/registry",
                params={"public_identifier_token": registry_token},
            )
            response.raise_for_status()

            data = response.json()
            if not data.get("Response"):
                raise TricntError(f"Registry {registry_token} not found")

            registry = data["Response"][0]["Registry"]

            return RegistryInfo(
                id=registry["id"],
                title=registry["title"],
                currency=registry["currency"],
                emoji=registry.get("emoji", ""),
                web_link=f"https://tricount.com/{registry_token}",
                member_count=len(registry.get("memberships", [])),
                expense_count=len(registry.get("all_registry_entry", [])),
            )

        except httpx.HTTPStatusError as e:
            raise TricntError(
                f"HTTP error getting registry info: {e.response.status_code}"
            )

    def get_members(self, registry_token: str) -> List[Member]:
        registry_data = self._get_registry_data(registry_token)
        members = []

        for membership in registry_data.get("memberships", []):
            member_data = membership["RegistryMembershipNonUser"]
            members.append(
                Member(
                    id=member_data["id"],
                    name=member_data["alias"]["display_name"],
                    status=member_data["status"],
                )
            )

        return members

    def get_expenses(self, registry_token: str) -> List[Expense]:
        registry_data = self._get_registry_data(registry_token)
        expenses = []

        for entry in registry_data.get("all_registry_entry", []):
            expense_data = entry["RegistryEntry"]

            payer = expense_data["membership_owned"]["RegistryMembershipNonUser"]
            payer_name = payer["alias"]["display_name"]

            beneficiaries = []
            allocations = {}
            for alloc in expense_data.get("allocations", []):
                if alloc.get("membership", {}).get("RegistryMembershipNonUser"):
                    member = alloc["membership"]["RegistryMembershipNonUser"]
                    name = member["alias"]["display_name"]
                    beneficiaries.append(name)
                    allocations[name] = abs(float(alloc.get("amount", {}).get("value", 0)))

            expenses.append(
                Expense(
                    id=expense_data["id"],
                    description=expense_data["description"],
                    amount=abs(float(expense_data["amount"]["value"])),
                    currency=expense_data["amount"]["currency"],
                    date=expense_data["date"],
                    payer=payer_name,
                    category=expense_data.get("category", "UNCATEGORIZED"),
                    beneficiaries=beneficiaries,
                    allocations=allocations,
                )
            )

        return expenses

    def calculate_balances(self, registry_token: str) -> Dict[str, float]:
        members = self.get_members(registry_token)
        expenses = self.get_expenses(registry_token)

        balances = {member.name: 0.0 for member in members}

        for expense in expenses:
            if expense.payer in balances:
                balances[expense.payer] += expense.amount

            if expense.allocations:
                for beneficiary, amount in expense.allocations.items():
                    if beneficiary in balances:
                        balances[beneficiary] -= amount
            elif expense.beneficiaries:
                per_person = expense.amount / len(expense.beneficiaries)
                for beneficiary in expense.beneficiaries:
                    if beneficiary in balances:
                        balances[beneficiary] -= per_person

        return {name: round(balance, 2) for name, balance in balances.items()}

    def close(self) -> None:
        if self._http_client:
            self._http_client.close()
            self._http_client = None

    def __enter__(self) -> "TricntClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
