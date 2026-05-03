# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
##############################################################################
"""Tests unitarios de ``services.mp_signature``."""

import hmac
import hashlib
import time

from odoo.tests.common import TransactionCase

from ..services.mp_signature import (
    MPSignatureError,
    build_manifest,
    parse_signature_header,
    verify_signature,
)


def _sign(secret, manifest):
    return hmac.new(secret.encode('utf-8'), manifest.encode('utf-8'), hashlib.sha256).hexdigest()


class TestParseSignatureHeader(TransactionCase):

    def test_well_formed_header(self):
        ts, v1 = parse_signature_header('ts=1714665600,v1=abc123def456')
        self.assertEqual(ts, 1714665600)
        self.assertEqual(v1, 'abc123def456')

    def test_header_with_spaces_is_tolerant(self):
        ts, v1 = parse_signature_header(' ts=1714665600 , v1=abc123 ')
        self.assertEqual(ts, 1714665600)
        self.assertEqual(v1, 'abc123')

    def test_uppercase_keys_normalize(self):
        ts, v1 = parse_signature_header('TS=1714665600,V1=abc')
        self.assertEqual(ts, 1714665600)
        self.assertEqual(v1, 'abc')

    def test_missing_ts(self):
        ts, v1 = parse_signature_header('v1=abc')
        self.assertIsNone(ts)
        self.assertEqual(v1, 'abc')

    def test_missing_v1(self):
        ts, v1 = parse_signature_header('ts=1714665600')
        self.assertEqual(ts, 1714665600)
        self.assertIsNone(v1)

    def test_empty_returns_none(self):
        ts, v1 = parse_signature_header('')
        self.assertIsNone(ts)
        self.assertIsNone(v1)

    def test_garbage_input_returns_none(self):
        ts, v1 = parse_signature_header('not-a-signature')
        self.assertIsNone(ts)
        self.assertIsNone(v1)

    def test_non_int_ts_is_none(self):
        ts, v1 = parse_signature_header('ts=not-a-number,v1=abc')
        self.assertIsNone(ts)
        self.assertEqual(v1, 'abc')


class TestBuildManifest(TransactionCase):

    def test_with_request_id(self):
        m = build_manifest(data_id='2c93808475', request_id='req-1', ts=1714665600)
        self.assertEqual(m, 'id:2c93808475;request-id:req-1;ts:1714665600;')

    def test_without_request_id(self):
        m = build_manifest(data_id='2c93808475', request_id=None, ts=1714665600)
        self.assertEqual(m, 'id:2c93808475;ts:1714665600;')

    def test_empty_request_id_treated_as_missing(self):
        m = build_manifest(data_id='2c93808475', request_id='', ts=1714665600)
        self.assertEqual(m, 'id:2c93808475;ts:1714665600;')


class TestVerifySignature(TransactionCase):

    SECRET = 'wh_sk_test_super_secreto'
    DATA_ID = '2c93808475a200000172750000000000'
    REQUEST_ID = 'req-abc-123'

    def _make_header(self, ts):
        manifest = build_manifest(self.DATA_ID, self.REQUEST_ID, ts)
        v1 = _sign(self.SECRET, manifest)
        return f'ts={ts},v1={v1}'

    def test_valid_signature_passes(self):
        ts = int(time.time())
        header = self._make_header(ts)

        result = verify_signature(
            secret=self.SECRET,
            data_id=self.DATA_ID,
            signature_header=header,
            request_id=self.REQUEST_ID,
        )

        self.assertTrue(result)

    def test_wrong_secret_fails(self):
        ts = int(time.time())
        header = self._make_header(ts)

        result = verify_signature(
            secret='wrong-secret',
            data_id=self.DATA_ID,
            signature_header=header,
            request_id=self.REQUEST_ID,
        )

        self.assertFalse(result)

    def test_wrong_data_id_fails(self):
        ts = int(time.time())
        header = self._make_header(ts)

        result = verify_signature(
            secret=self.SECRET,
            data_id='other-data-id',
            signature_header=header,
            request_id=self.REQUEST_ID,
        )

        self.assertFalse(result)

    def test_wrong_request_id_fails(self):
        ts = int(time.time())
        header = self._make_header(ts)

        result = verify_signature(
            secret=self.SECRET,
            data_id=self.DATA_ID,
            signature_header=header,
            request_id='other-request-id',
        )

        self.assertFalse(result)

    def test_old_ts_outside_tolerance_fails(self):
        old_ts = int(time.time()) - 3600  # 1h en el pasado
        header = self._make_header(old_ts)

        result = verify_signature(
            secret=self.SECRET,
            data_id=self.DATA_ID,
            signature_header=header,
            request_id=self.REQUEST_ID,
            tolerance_seconds=600,  # 10 min de ventana
        )

        self.assertFalse(result)

    def test_zero_tolerance_skips_temporal_check(self):
        old_ts = int(time.time()) - 3600
        header = self._make_header(old_ts)

        result = verify_signature(
            secret=self.SECRET,
            data_id=self.DATA_ID,
            signature_header=header,
            request_id=self.REQUEST_ID,
            tolerance_seconds=0,
        )

        self.assertTrue(result)

    def test_empty_signature_header_returns_false(self):
        result = verify_signature(
            secret=self.SECRET,
            data_id=self.DATA_ID,
            signature_header='',
            request_id=self.REQUEST_ID,
        )

        self.assertFalse(result)

    def test_empty_secret_raises(self):
        ts = int(time.time())
        header = self._make_header(ts)

        with self.assertRaises(MPSignatureError):
            verify_signature(
                secret='',
                data_id=self.DATA_ID,
                signature_header=header,
                request_id=self.REQUEST_ID,
            )

    def test_empty_data_id_raises(self):
        with self.assertRaises(MPSignatureError):
            verify_signature(
                secret=self.SECRET,
                data_id='',
                signature_header='ts=123,v1=abc',
                request_id=self.REQUEST_ID,
            )

    def test_signature_without_request_id_works(self):
        ts = int(time.time())
        manifest = build_manifest(self.DATA_ID, None, ts)
        v1 = _sign(self.SECRET, manifest)
        header = f'ts={ts},v1={v1}'

        result = verify_signature(
            secret=self.SECRET,
            data_id=self.DATA_ID,
            signature_header=header,
            request_id=None,
        )

        self.assertTrue(result)
