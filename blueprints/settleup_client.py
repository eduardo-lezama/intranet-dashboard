import threading
from datetime import UTC, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

import requests

# Module-level token cache for SettleUp Firebase auth
_token_cache = {"token": None, "expires_at": None, "key": None}
_token_lock = threading.Lock()

"""
Funciones estaticas auxiliares para tema de timezone, errores de deriva y gmt+1
"""


def _D(x):
    try:
        return Decimal(str(x))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _round2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _parse_tz_offset(tz_str: str | None):
    # tz_str típico: "+01:00"
    if not tz_str or len(tz_str) < 6:
        return UTC
    sign = 1 if tz_str[0] == "+" else -1
    hh = int(tz_str[1:3])
    mm = int(tz_str[4:6])
    return timezone(sign * timedelta(hours=hh, minutes=mm))


"""
Fin funciones aux
"""


class SettleUpClient:
    def __init__(self, email, password, group_id, api_key=None, env="sandbox"):
        """
        Cliente para Settle Up API usando Firebase REST

        Docs oficiales:
        - https://api.settleup.io/
        - https://firebase.google.com/docs/reference/rest/auth

        - env='sandbox' -> usa endpoints sandbox
        - env='live'    -> usa endpoints de producción
        """
        self.env = env
        self.group_id = group_id

        # Endpoints oficiales documentados
        if not api_key:
            raise ValueError(
                "SETTLEUP_API_KEY es obligatorio. "
                "Configúralo en .env (sandbox o live key según entorno)."
            )
        self.api_key = api_key

        if env == "sandbox":
            self.base_url = "https://settle-up-sandbox.firebaseio.com"
        else:
            self.base_url = "https://settle-up-live.firebaseio.com"

        self.id_token = self._authenticate(email, password)

    def _authenticate(self, email, password):
        """
        Autenticación Firebase REST API oficial con token caching.
        Firebase tokens duran 1 hora; re-usamos el token si no ha expirado.
        https://firebase.google.com/docs/reference/rest/auth#section-sign-in-email-password
        """
        cache_key = f"{email}:{self.env}"

        with _token_lock:
            if (
                _token_cache["token"]
                and _token_cache["key"] == cache_key
                and _token_cache["expires_at"]
                and datetime.now(UTC) < _token_cache["expires_at"]
            ):
                return _token_cache["token"]

        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.api_key}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        response = requests.post(url, json=payload)

        if response.ok:
            data = response.json()
            token = data["idToken"]
            # Firebase tokens expire in 3600s; use 3000s margin for safety
            expires_in = int(data.get("expiresIn", 3600))
            with _token_lock:
                _token_cache["token"] = token
                _token_cache["key"] = cache_key
                _token_cache["expires_at"] = datetime.now(UTC) + timedelta(seconds=expires_in - 600)
            return token
        else:
            error = response.json().get("error", {})
            raise Exception(f"Auth failed: {error.get('message', 'Unknown error')}")

    def get_group_members(self):
        """
        GET /members/<group_id>.json
        Documentado en https://api.settleup.io/
        """
        url = f"{self.base_url}/members/{self.group_id}.json?auth={self.id_token}"
        response = requests.get(url)
        return response.json() if response.ok else {}

    def get_group_entries(self):
        """
        Old name was entries, changed to transactions
        GET /transactions/<group_id>.json
        Retorna todos los gastos del grupo
        """
        url = f"{self.base_url}/transactions/{self.group_id}.json?auth={self.id_token}"
        response = requests.get(url)
        return response.json() if response.ok else {}

    """
    Funciones auxiliares para evitar deriva, zona horaria y tema de gmt+1
    """

    def get_monthly_expenses(self, year=None, month=None):
        if year is None:
            now = datetime.now()
            year, month = now.year, now.month

        entries = self.get_group_entries()
        total = Decimal("0")

        for _, entry in (entries or {}).items():
            if (entry.get("type") or "").lower() == "transfer":
                continue

            dt_ms = entry.get("dateTime")
            if not dt_ms:
                continue

            tzinfo = _parse_tz_offset(entry.get("timezone"))
            dt_utc = datetime.fromtimestamp(int(float(dt_ms)) / 1000, tz=UTC)
            dt_local = dt_utc.astimezone(tzinfo)

            if dt_local.year != year or dt_local.month != month:
                continue

            for item in entry.get("items") or []:
                total += _D(item.get("amount", "0"))

        return float(_round2(total))

    def calculate_group_balance(self):
        members = self.get_group_members()
        entries = self.get_group_entries()

        if not members:
            raise Exception("No hay miembros en el grupo")

        stats = {
            mid: {
                "paid": Decimal("0"),
                "spent": Decimal("0"),
                "transfers": Decimal("0"),
                "incomes": Decimal("0"),
            }
            for mid in members.keys()
        }

        def ensure(mid):
            if mid and mid not in stats:
                stats[mid] = {
                    "paid": Decimal("0"),
                    "spent": Decimal("0"),
                    "transfers": Decimal("0"),
                    "incomes": Decimal("0"),
                }

        for _, entry in (entries or {}).items():
            ttype = (entry.get("type") or "").lower()
            who_paid = entry.get("whoPaid") or []
            items = entry.get("items") or []

            for p in who_paid:
                ensure(p.get("memberId"))
            for it in items:
                for fw in it.get("forWhom") or []:
                    ensure(fw.get("memberId"))

            for it in items:
                amount = _D(it.get("amount", "0"))
                fw = it.get("forWhom") or []

                sum_wp = sum(_D(p.get("weight", "0")) for p in who_paid) or Decimal("1")
                sum_fw = sum(_D(x.get("weight", "0")) for x in fw) or Decimal("1")

                if ttype == "transfer":
                    # whoPaid = receptor (+), forWhom = emisor (-)
                    for r in who_paid:
                        mid = r.get("memberId")
                        w = _D(r.get("weight", "0"))
                        stats[mid]["transfers"] += amount * (w / sum_wp)

                    for s in fw:
                        mid = s.get("memberId")
                        w = _D(s.get("weight", "0"))
                        stats[mid]["transfers"] -= amount * (w / sum_fw)

                else:
                    if amount >= 0:
                        # expense normal
                        for p in who_paid:
                            mid = p.get("memberId")
                            w = _D(p.get("weight", "0"))
                            stats[mid]["paid"] += amount * (w / sum_wp)

                        for x in fw:
                            mid = x.get("memberId")
                            w = _D(x.get("weight", "0"))
                            stats[mid]["spent"] += amount * (w / sum_fw)

                    else:
                        # INCOME (amount negativo): se refleja en "incomes" (no en paid/spent)
                        inc = abs(amount)

                        shares = {}
                        for x in fw:
                            mid = x.get("memberId")
                            w = _D(x.get("weight", "0"))
                            shares[mid] = inc * (w / sum_fw)

                        receivers = [p.get("memberId") for p in who_paid if p.get("memberId")]
                        if not receivers:
                            continue

                        # participantes que NO reciben: +share
                        total_other = Decimal("0")
                        for mid, sh in shares.items():
                            if mid not in receivers:
                                stats[mid]["incomes"] += sh
                                total_other += sh

                        # receptores: -total_other (repartido por peso de whoPaid)
                        sum_wr = sum(_D(p.get("weight", "0")) for p in who_paid) or Decimal("1")
                        for p in who_paid:
                            rid = p.get("memberId")
                            w = _D(p.get("weight", "0"))
                            stats[rid]["incomes"] -= total_other * (w / sum_wr)

        balances = {}
        for mid in members.keys():
            paid = stats[mid]["paid"]
            spent = stats[mid]["spent"]
            transfers = stats[mid]["transfers"]
            incomes = stats[mid]["incomes"]
            balances[mid] = _round2(paid - spent + transfers + incomes)

            # redondea stats para devolverlos limpios
            stats[mid] = {k: _round2(v) for k, v in stats[mid].items()}

        return {
            "members": {mid: members[mid].get("name", "Unknown") for mid in members.keys()},
            "balances": balances,
            "stats": stats,
        }
