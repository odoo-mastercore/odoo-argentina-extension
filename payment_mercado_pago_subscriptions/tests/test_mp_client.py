# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
##############################################################################
"""Tests unitarios de ``services.mp_client``.

Estos tests no requieren Odoo: el cliente es agnóstico del ORM. Se
ejecutan tanto vía ``odoo-bin --test-tags`` como con pytest puro contra
el archivo (siempre que ``requests`` esté disponible).
"""

import json
from unittest import mock
from unittest.mock import MagicMock

import requests

from odoo.tests.common import TransactionCase

from ..services.mp_client import MPClient, MPClientError, MPClientHTTPError


def _mock_response(status_code, json_payload=None, text=''):
    response = MagicMock(spec=requests.Response)
    response.status_code = status_code
    response.text = text or (json.dumps(json_payload) if json_payload else '')
    if json_payload is None:
        response.json.side_effect = ValueError('no json')
    else:
        response.json.return_value = json_payload
    return response


class TestMPClient(TransactionCase):

    def _make_client(self, retries=0, backoff_base=0):
        session = MagicMock(spec=requests.Session)
        client = MPClient(
            access_token='TEST-token',
            base_url='https://api.mercadopago.com',
            timeout=5,
            retries=retries,
            backoff_base=backoff_base,
            session=session,
        )
        return client, session

    def test_init_requires_access_token(self):
        with self.assertRaises(MPClientError):
            MPClient(access_token='')

    def test_get_returns_json_payload(self):
        client, session = self._make_client()
        session.request.return_value = _mock_response(200, {'id': 'PA-1', 'status': 'authorized'})

        result = client.get('/preapproval/PA-1')

        self.assertEqual(result, {'id': 'PA-1', 'status': 'authorized'})
        session.request.assert_called_once()
        args, kwargs = session.request.call_args
        self.assertEqual(args[0], 'GET')
        self.assertEqual(args[1], 'https://api.mercadopago.com/preapproval/PA-1')
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer TEST-token')
        self.assertEqual(kwargs['headers']['Accept'], 'application/json')
        self.assertNotIn('X-Idempotency-Key', kwargs['headers'])

    def test_post_includes_idempotency_key_when_omitted(self):
        client, session = self._make_client()
        session.request.return_value = _mock_response(201, {'id': 'PA-1'})

        client.post('/preapproval', {'reason': 'test'})

        args, kwargs = session.request.call_args
        self.assertEqual(args[0], 'POST')
        self.assertIn('X-Idempotency-Key', kwargs['headers'])
        self.assertTrue(kwargs['headers']['X-Idempotency-Key'])
        self.assertEqual(kwargs['headers']['Content-Type'], 'application/json')
        self.assertEqual(json.loads(kwargs['data']), {'reason': 'test'})

    def test_post_respects_explicit_idempotency_key(self):
        client, session = self._make_client()
        session.request.return_value = _mock_response(201, {})

        client.post('/preapproval', {'x': 1}, idempotency_key='my-key-123')

        _, kwargs = session.request.call_args
        self.assertEqual(kwargs['headers']['X-Idempotency-Key'], 'my-key-123')

    def test_put_uses_put_verb(self):
        client, session = self._make_client()
        session.request.return_value = _mock_response(200, {'id': 'PA-1'})

        client.put('/preapproval/PA-1', {'auto_recurring': {'transaction_amount': 80000.0}})

        args, _ = session.request.call_args
        self.assertEqual(args[0], 'PUT')

    def test_4xx_raises_http_error_with_payload(self):
        client, session = self._make_client()
        session.request.return_value = _mock_response(400, {
            'message': 'invalid currency_id',
            'error': 'bad_request',
        })

        with self.assertRaises(MPClientHTTPError) as ctx:
            client.post('/preapproval', {})

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.payload, {
            'message': 'invalid currency_id',
            'error': 'bad_request',
        })

    def test_5xx_retries_then_raises(self):
        client, session = self._make_client(retries=2, backoff_base=0)
        session.request.return_value = _mock_response(503, text='upstream down')

        with self.assertRaises(MPClientHTTPError) as ctx:
            client.get('/preapproval/PA-1')

        self.assertEqual(ctx.exception.status_code, 503)
        # 1 inicial + 2 reintentos = 3 calls.
        self.assertEqual(session.request.call_count, 3)

    def test_5xx_retries_then_succeeds(self):
        client, session = self._make_client(retries=2, backoff_base=0)
        session.request.side_effect = [
            _mock_response(502, text='bad gateway'),
            _mock_response(200, {'id': 'PA-OK'}),
        ]

        result = client.get('/preapproval/PA-OK')

        self.assertEqual(result, {'id': 'PA-OK'})
        self.assertEqual(session.request.call_count, 2)

    def test_connection_error_retries_then_raises(self):
        client, session = self._make_client(retries=1, backoff_base=0)
        session.request.side_effect = requests.ConnectionError("dns fail")

        with self.assertRaises(MPClientError):
            client.get('/preapproval/PA-1')

        self.assertEqual(session.request.call_count, 2)

    def test_connection_error_recovers_on_retry(self):
        client, session = self._make_client(retries=2, backoff_base=0)
        session.request.side_effect = [
            requests.ConnectionError("transient"),
            _mock_response(200, {'id': 'PA-OK'}),
        ]

        result = client.get('/preapproval/PA-OK')

        self.assertEqual(result, {'id': 'PA-OK'})
        self.assertEqual(session.request.call_count, 2)

    def test_create_preapproval_plan_helper(self):
        client, session = self._make_client()
        session.request.return_value = _mock_response(201, {'id': 'PLAN-1'})

        result = client.create_preapproval_plan({'reason': 'My plan'})

        self.assertEqual(result, {'id': 'PLAN-1'})
        args, _ = session.request.call_args
        self.assertEqual(args[0], 'POST')
        self.assertEqual(args[1], 'https://api.mercadopago.com/preapproval_plan')

    def test_get_preapproval_helper_uses_correct_path(self):
        client, session = self._make_client()
        session.request.return_value = _mock_response(200, {'id': 'PA-9'})

        client.get_preapproval('PA-9')

        args, _ = session.request.call_args
        self.assertEqual(args[1], 'https://api.mercadopago.com/preapproval/PA-9')

    def test_update_preapproval_helper_pads_idempotency(self):
        client, session = self._make_client()
        session.request.return_value = _mock_response(200, {'id': 'PA-9'})

        client.update_preapproval('PA-9', {'auto_recurring': {'transaction_amount': 99000}})

        args, kwargs = session.request.call_args
        self.assertEqual(args[0], 'PUT')
        self.assertIn('X-Idempotency-Key', kwargs['headers'])

    def test_get_payment_uses_v1_path(self):
        client, session = self._make_client()
        session.request.return_value = _mock_response(200, {'id': 12345})

        client.get_payment('12345')

        args, _ = session.request.call_args
        self.assertEqual(args[1], 'https://api.mercadopago.com/v1/payments/12345')

    def test_search_with_params(self):
        client, session = self._make_client()
        session.request.return_value = _mock_response(200, {'results': []})

        client.search_preapprovals({'status': 'authorized', 'limit': 10})

        _, kwargs = session.request.call_args
        self.assertEqual(kwargs['params'], {'status': 'authorized', 'limit': 10})

    def test_2xx_with_no_json_body_returns_empty_dict(self):
        client, session = self._make_client()
        session.request.return_value = _mock_response(204)

        result = client.delete('/something/123')

        self.assertEqual(result, {})
