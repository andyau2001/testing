# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import Response, JsonRequest
from odoo.tools import date_utils

import werkzeug
import urllib3
import base64
import json
import hashlib
import hmac

import logging

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_logger = logging.getLogger(__name__)


def _json_response(self, result=None, error=None):
    lover = self.endpoint.routing.get('lover')
    if lover == 'xero_webhooks':
        if result is not None:
            if 'status' in result and result['status']:
                return Response(None, status=result['status'])
        return Response(None)

    response = {
        'jsonrpc': '2.0',
        'id': self.jsonrequest.get('id')
    }
    if error is not None:
        response['error'] = error
    if result is not None:
        response['result'] = result

    mime = 'application/json'
    body = json.dumps(response, default=date_utils.json_default)

    return Response(
        body, status=error and error.pop('http_status', 200) or 200,
        headers=[('Content-Type', mime), ('Content-Length', len(body))]
    )


setattr(JsonRequest, '_json_response', _json_response)  # overwrite the method


class AbkXeroIntegration(http.Controller):
    @http.route('/abk-xero-integration/get-token/', auth='user')
    def index(self, **kw):
        xero_session = http.request.env['abk.xero.session']
        xero_config = xero_session.get_xero_config()

        data = http.request.params
        code = data.get('code')

        if not code:
            url = 'https://login.xero.com/identity/connect/authorize?response_type=code'
            url += '&client_id=' + xero_config.get('client_id')
            url += '&redirect_uri=' + xero_config.get('login_url')
            url += "&scope=offline_access%20openid%20profile%20email%20accounting.transactions%20accounting.transactions.read%20accounting.reports.read%20accounting.journals.read%20accounting.settings%20accounting.settings.read%20accounting.contacts%20accounting.contacts.read%20accounting.attachments%20accounting.attachments.read%20assets%20projects%20files%20payroll.employees%20payroll.payruns%20payroll.payslip%20payroll.timesheets%20payroll.settings"
            return werkzeug.utils.redirect(url)

        return self.get_access_token(code)

    @http.route('/abk-xero-integration/integrate-page/', auth='none', type='http', cors='*', csrf=False)
    def integrate_page(self, **kwargs):
        _logger.info('___________________________________integrate_page')
        result = {
            'html': """
                        <div>
                            <link href="/module_name/static/src/css/banner.css"
                                rel="stylesheet">
                            <h1>hello, world</h1>
                        </div> 
                    """
        }
        return Response(json.dumps(result), content_type='application/json;charset=utf-8', status=200)

    def get_access_token(self, code):
        url = 'https://identity.xero.com/connect/token'
        client = urllib3.PoolManager()

        xero_session = http.request.env['abk.xero.session']
        xero_config = xero_session.get_xero_config()

        basic = xero_config.get('client_id') + ':' + xero_config.get('client_secret')
        encoded_bytes = base64.b64encode(basic.encode("ascii"))
        encoded = encoded_bytes.decode("ascii")

        headers = {
            'authorization': 'Basic ' + encoded
        }

        body = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': xero_config.get('login_url')
        }

        r = client.request('POST', url, fields=body, headers=headers)

        try:
            result = json.loads(r.data)
        except:
            return r.data

        if result.get('error'):
            return json.dumps(result).encode('utf-8')
        else:
            xero_session.save_xero_session(result)
            return 'Success!'

    @http.route('/abk-xero-integration/process-webhooks/', auth='none', type='json', cors='*', csrf=False,
                method=['POST'], lover='xero_webhooks')
    def process_webhooks(self, **kw):
        _logger.info('---------------------------- process_webhooks')

        headers = http.request.httprequest.headers
        data = http.request.jsonrequest

        _logger.info(data)

        if 'X-Xero-Signature' in headers:
            if data.get('firstEventSequence') == data.get('lastEventSequence') == 0:
                signature = headers['X-Xero-Signature']
                webhook_key = 'uRI9vUQhpGKJoK9J/xPGyNPs6HE1qBQEsepRXdemqsXPh0UrXWXi6HJbA6Ie/2r9u31ln28KcXorQKIMenOOFA=='
                body = http.request.httprequest.get_data()

                if self.intent_to_receive_check(body, signature, webhook_key):
                    return {'status': 200}
                else:
                    return {'status': 401}

        for event in data.get('events'):
            http.request.env['res.company'].sudo().process_webhooks_event(event)

        return {'status': 200}

    def intent_to_receive_check(self, body, xero_signature, webhooks_key):
        # Convert the our webhooks key to bytes with utf-8 encoding.
        webhooks_key = bytes(webhooks_key, 'utf-8')
        # Convert the request of the body to bytes with utf-8 encoding.
        # body = bytes(body, 'utf-8')

        # HMAC SHA-256 sign the body with our Xero webhooks key
        hashed = hmac.new(webhooks_key, body, hashlib.sha256)

        # Base64 encode the HMAC hash
        response_signature = base64.b64encode(hashed.digest()).decode('utf-8')
        _logger.info(response_signature + ' <--> ' + xero_signature)

        # Compare the body (HMAC signed & Base64 encoded) to the signature provided
        if response_signature == xero_signature:
            return True
        else:
            return False
