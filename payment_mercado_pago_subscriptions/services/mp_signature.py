# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
##############################################################################
"""Validación de firmas de webhooks de Mercado Pago.

MP firma cada webhook con HMAC-SHA256 sobre un manifest construido con
``id``, ``request-id`` y ``ts``. La firma viaja en el header
``x-signature`` con formato ``ts=<unix>,v1=<hex>``.

Documentación oficial:
https://www.mercadopago.com.ar/developers/es/docs/your-integrations/notifications/webhooks
"""

import hmac
import hashlib
import logging
import time
from typing import Optional, Tuple

_logger = logging.getLogger(__name__)


class MPSignatureError(Exception):
    """Error de validación de firma del webhook."""


# Threshold para detectar timestamps en milisegundos. En la práctica MP
# envía ``ts`` en milisegundos (~1.7e12 en 2026), aunque la doc oficial
# no lo aclara. Cualquier valor por encima de este threshold se asume
# en milisegundos. Segundos epoch desde 1973 hasta ~5138 caen por
# debajo; milisegundos epoch desde ~1973 caen por encima.
_MS_THRESHOLD = 10 ** 11


def _ts_to_seconds(ts: int) -> int:
    """Normaliza un timestamp epoch a segundos.

    Si el valor es mayor al threshold, se asume en milisegundos y se
    divide por 1000. Se usa exclusivamente para la verificación de
    tolerancia temporal — el manifest HMAC debe construirse con el
    valor ORIGINAL recibido en el header, no el normalizado.
    """
    return ts // 1000 if ts > _MS_THRESHOLD else ts


def parse_signature_header(header_value: str) -> Tuple[Optional[int], Optional[str]]:
    """Parsea el header ``x-signature`` con formato ``ts=...,v1=...``.

    Devuelve ``ts`` como int **tal como viene** en el header (sin
    normalizar), porque el manifest HMAC se arma con ese valor exacto.
    Para la verificación de tolerancia temporal usar
    :func:`_ts_to_seconds` antes de comparar contra ``time.time()``.

    :param str header_value: contenido crudo del header.
    :return: tupla ``(ts, v1)`` con ``ts`` como int en la unidad
        original (típicamente milisegundos en MP) y ``v1`` como str hex.
        Cualquiera puede ser ``None`` si no estaba presente o no parsea.
    """
    if not header_value:
        return None, None
    ts: Optional[int] = None
    v1: Optional[str] = None
    for part in header_value.split(','):
        chunk = part.strip()
        if '=' not in chunk:
            continue
        key, _, value = chunk.partition('=')
        key = key.strip().lower()
        value = value.strip()
        if key == 'ts':
            try:
                ts = int(value)
            except (ValueError, TypeError):
                ts = None
        elif key == 'v1':
            v1 = value
    return ts, v1


def build_manifest(data_id: str, request_id: Optional[str], ts: int) -> str:
    """Arma el manifest según especificación MP.

    Formato canónico:
        ``id:{data_id};request-id:{request_id};ts:{ts};``

    Si ``request_id`` viene vacío o ``None``, omitimos el segmento
    ``request-id`` para mantener bit-exact compatibilidad con la
    implementación de referencia.

    :param str data_id: ``data.id`` del payload del webhook.
    :param str request_id: header ``x-request-id`` del request.
    :param int ts: timestamp (segundos epoch) del header ``x-signature``.
    :return str: cadena lista para hashear.
    """
    parts = [f"id:{data_id};"]
    if request_id:
        parts.append(f"request-id:{request_id};")
    parts.append(f"ts:{ts};")
    return ''.join(parts)


def verify_signature(
    secret: str,
    data_id: str,
    signature_header: str,
    request_id: Optional[str] = None,
    tolerance_seconds: int = 600,
) -> bool:
    """Valida un webhook MP contra el secret del comercio.

    :param str secret: webhook secret obtenido del panel MP.
    :param str data_id: ``data.id`` del payload.
    :param str signature_header: contenido del header ``x-signature``.
    :param str request_id: contenido del header ``x-request-id``.
    :param int tolerance_seconds: ventana en segundos para aceptar el
        timestamp del header. 0 desactiva la validación temporal (para
        tests).
    :return bool: ``True`` si la firma es válida, ``False`` si no.
    :raises MPSignatureError: si los argumentos requeridos están vacíos.
    """
    if not secret:
        raise MPSignatureError("Webhook secret is empty; cannot verify signatures.")
    if not data_id:
        raise MPSignatureError("data.id is required to verify signature.")
    if not signature_header:
        return False

    ts, v1 = parse_signature_header(signature_header)
    if ts is None or not v1:
        return False

    if tolerance_seconds > 0:
        now = int(time.time())
        ts_seconds = _ts_to_seconds(ts)
        if abs(now - ts_seconds) > tolerance_seconds:
            _logger.warning(
                "MP webhook signature timestamp out of tolerance: "
                "ts_raw=%s ts_seconds=%s now=%s tol=%ss",
                ts, ts_seconds, now, tolerance_seconds,
            )
            return False

    # El manifest se arma con el ``ts`` ORIGINAL (sin normalizar) porque
    # MP firma con ese valor exacto.
    manifest = build_manifest(data_id=data_id, request_id=request_id, ts=ts)
    expected = hmac.new(
        secret.encode('utf-8'),
        manifest.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, v1)
