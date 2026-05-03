# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
##############################################################################
"""Cliente HTTP para la API de Mercado Pago Suscripciones.

Provee una interfaz pequeña y testeable sobre la API REST de MP. Maneja:

- Autenticación Bearer con ``access_token`` propio del comercio.
- Header ``X-Idempotency-Key`` automático en POSTs mutadores.
- Reintentos exponenciales en respuestas 5xx / errores de conexión /
  timeouts.
- Lectura del JSON con manejo defensivo y mensajes de error claros.

El cliente es agnóstico de Odoo: no importa modelos ni el ORM. La
integración con ``payment.provider`` se hace en
``models/payment_provider.py`` que instancia este cliente con las
credenciales correctas.

Pensado para ser instanciado por request o cacheado a nivel provider —
es liviano y stateless salvo por la sesión HTTP interna.
"""

import json
import logging
import time
import uuid
from typing import Any, Dict, Optional

import requests

from .. import const

_logger = logging.getLogger(__name__)


class MPClientError(Exception):
    """Error genérico del cliente MP."""


class MPClientHTTPError(MPClientError):
    """Error HTTP no recuperable devuelto por la API.

    :ivar int status_code: código HTTP devuelto.
    :ivar dict payload: cuerpo JSON parseado (si lo hubo).
    """

    def __init__(self, status_code: int, payload: Optional[Dict[str, Any]], message: str):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


class MPClient:
    """Cliente HTTP minimalista para la API de Mercado Pago.

    :param str access_token: token Bearer del comercio (TEST o PROD).
    :param str base_url: URL base de la API. Default
        ``https://api.mercadopago.com``.
    :param int timeout: timeout HTTP por request en segundos.
    :param int retries: cantidad de reintentos en 5xx / connection errors.
    :param float backoff_base: segundos del primer backoff (se duplica).
    :param requests.Session session: sesión HTTP reutilizable. Útil para
        tests con ``unittest.mock``.
    """

    def __init__(
        self,
        access_token: str,
        base_url: str = const.MP_API_BASE_URL,
        timeout: int = const.DEFAULT_HTTP_TIMEOUT,
        retries: int = const.DEFAULT_HTTP_RETRIES,
        backoff_base: float = const.DEFAULT_HTTP_BACKOFF_BASE,
        session: Optional[requests.Session] = None,
    ):
        if not access_token:
            raise MPClientError("MP access_token is required.")
        self.access_token = access_token
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retries = retries
        self.backoff_base = backoff_base
        self._session = session or requests.Session()

    # ------------------------------------------------------------------ #
    #  Public API                                                        #
    # ------------------------------------------------------------------ #

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET path returning parsed JSON dict."""
        return self._request('GET', path, params=params)

    def post(
        self,
        path: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """POST path with JSON payload, automatic idempotency key.

        :param idempotency_key: si se omite, se genera un UUID4.
        """
        return self._request(
            'POST',
            path,
            json_body=payload,
            idempotency_key=idempotency_key or str(uuid.uuid4()),
        )

    def put(
        self,
        path: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """PUT path with JSON payload, automatic idempotency key."""
        return self._request(
            'PUT',
            path,
            json_body=payload,
            idempotency_key=idempotency_key or str(uuid.uuid4()),
        )

    def delete(self, path: str) -> Dict[str, Any]:
        """DELETE path."""
        return self._request('DELETE', path)

    # ------------------------------------------------------------------ #
    #  Domain helpers — sugar on top of HTTP verbs                       #
    # ------------------------------------------------------------------ #

    def create_preapproval_plan(
        self,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """``POST /preapproval_plan`` — crea un plan."""
        return self.post('/preapproval_plan', payload, idempotency_key=idempotency_key)

    def get_preapproval_plan(self, plan_id: str) -> Dict[str, Any]:
        """``GET /preapproval_plan/{id}``."""
        return self.get(f'/preapproval_plan/{plan_id}')

    def update_preapproval_plan(
        self,
        plan_id: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """``PUT /preapproval_plan/{id}``."""
        return self.put(f'/preapproval_plan/{plan_id}', payload, idempotency_key=idempotency_key)

    def search_preapproval_plans(
        self,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """``GET /preapproval_plan/search``."""
        return self.get('/preapproval_plan/search', params=params)

    def create_preapproval(
        self,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """``POST /preapproval`` — crea una suscripción."""
        return self.post('/preapproval', payload, idempotency_key=idempotency_key)

    def get_preapproval(self, preapproval_id: str) -> Dict[str, Any]:
        """``GET /preapproval/{id}``."""
        return self.get(f'/preapproval/{preapproval_id}')

    def update_preapproval(
        self,
        preapproval_id: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """``PUT /preapproval/{id}`` — modifica monto, estado, tarjeta."""
        return self.put(f'/preapproval/{preapproval_id}', payload, idempotency_key=idempotency_key)

    def search_preapprovals(
        self,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """``GET /preapproval/search``."""
        return self.get('/preapproval/search', params=params)

    def get_authorized_payment(self, payment_id: str) -> Dict[str, Any]:
        """``GET /authorized_payments/{id}``."""
        return self.get(f'/authorized_payments/{payment_id}')

    def search_authorized_payments(
        self,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """``GET /authorized_payments/search``."""
        return self.get('/authorized_payments/search', params=params)

    def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """``GET /v1/payments/{id}``."""
        return self.get(f'/v1/payments/{payment_id}')

    # ------------------------------------------------------------------ #
    #  Internals                                                         #
    # ------------------------------------------------------------------ #

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path if path.startswith('/') else '/' + path}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json',
        }
        if json_body is not None:
            headers['Content-Type'] = 'application/json'
        if idempotency_key:
            headers[const.HEADER_IDEMPOTENCY_KEY] = idempotency_key

        attempt = 0
        last_exc = None
        while attempt <= self.retries:
            try:
                response = self._session.request(
                    method,
                    url,
                    params=params,
                    data=json.dumps(json_body) if json_body is not None else None,
                    headers=headers,
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                last_exc = exc
                _logger.warning(
                    "MP %s %s: connection error (attempt %s/%s): %s",
                    method, url, attempt + 1, self.retries + 1, exc,
                )
                if attempt >= self.retries:
                    raise MPClientError(
                        f"Connection error talking to Mercado Pago: {exc}"
                    ) from exc
                self._sleep_backoff(attempt)
                attempt += 1
                continue

            # Non-retriable success or client error.
            if response.status_code < 500:
                return self._handle_response(response)

            # 5xx: retry with backoff.
            _logger.warning(
                "MP %s %s: %s server error (attempt %s/%s): %s",
                method, url, response.status_code, attempt + 1, self.retries + 1,
                response.text[:500],
            )
            if attempt >= self.retries:
                payload = self._safe_json(response)
                raise MPClientHTTPError(
                    response.status_code,
                    payload,
                    f"Server error from Mercado Pago after {self.retries + 1} attempts.",
                )
            self._sleep_backoff(attempt)
            attempt += 1

        # Unreachable safeguard.
        raise MPClientError(f"Exhausted retries without response: {last_exc}")

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Process a non-5xx response. Raise for 4xx, return payload for 2xx/3xx."""
        if 200 <= response.status_code < 300:
            return self._safe_json(response) or {}
        # 4xx: client error, do not retry.
        payload = self._safe_json(response)
        message = self._extract_error_message(payload, response)
        raise MPClientHTTPError(response.status_code, payload, message)

    @staticmethod
    def _safe_json(response: requests.Response) -> Optional[Dict[str, Any]]:
        try:
            return response.json()
        except ValueError:
            return None

    @staticmethod
    def _extract_error_message(
        payload: Optional[Dict[str, Any]],
        response: requests.Response,
    ) -> str:
        if payload:
            for key in ('message', 'error', 'cause'):
                value = payload.get(key)
                if value:
                    return f"MP {response.status_code}: {value}"
        return f"MP {response.status_code}: {response.text[:300]}"

    def _sleep_backoff(self, attempt: int) -> None:
        delay = self.backoff_base * (2 ** attempt)
        time.sleep(delay)
