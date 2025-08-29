import os
import logging
from typing import Dict
import json
import urllib.request
import urllib.parse
import urllib.error

# ------------------------------------------------------------
# Graph email (application permissions) — no MSAL dependency
# ------------------------------------------------------------

def read_graph_config() -> Dict[str, str]:
    """
    Retrieve Microsoft Graph connection settings from environment variables only.
    Requires: GRAPH_TENANT_ID, GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET, GRAPH_SENDER_UPN
    """
    conf = {
        "tenant_id":    os.getenv("GRAPH_TENANT_ID"),
        "client_id":    os.getenv("GRAPH_CLIENT_ID"),
        "client_secret":os.getenv("GRAPH_CLIENT_SECRET"),
        "sender_upn":   os.getenv("GRAPH_SENDER_UPN"),
    }

    missing = [k for k, v in conf.items() if not v]
    if missing:
        logging.error("Graph env vars missing: %s", ", ".join(missing))
        raise RuntimeError("Missing Microsoft Graph environment variables: " + ", ".join(missing))

    logging.info("Microsoft Graph connection settings retrieved")
    return conf

def _graph_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    """
    Fetch a Microsoft Graph access token using the client-credentials flow.
    """
    if not tenant_id or not client_id or not client_secret:
        raise RuntimeError('Graph client credentials are missing (tenant_id/client_id/client_secret).')
    token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'https://graph.microsoft.com/.default',
        'grant_type': 'client_credentials',
    }
    encoded = urllib.parse.urlencode(data).encode('utf-8')
    req = urllib.request.Request(token_url, data=encoded, method='POST')
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode('utf-8'))
    token = payload.get('access_token')
    if not token:
        raise RuntimeError('Failed to obtain Graph access token.')
    return token

def send_email_graph(to_addr: str, cc1: str, cc2: str, subject: str, html_body: str, graph_conf: Dict[str, str]) -> None:
    """
    Send an HTML email via Microsoft Graph using app credentials.
    Builds a POST to `v1.0/users/{sender_upn}/sendMail` with `saveToSentItems=True`.
    """

    sender = graph_conf.get('sender_upn')
    tenant = graph_conf.get('tenant_id')
    client_id = graph_conf.get('client_id')
    client_secret = graph_conf.get('client_secret')

    if not to_addr:
        logging.warning('No recipient provided; skipping send.')
        return

    token = _graph_token(tenant, client_id, client_secret)

    url = f'https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(sender)}/sendMail'
    body = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": [{"emailAddress": {"address": to_addr}}],
            "ccRecipients": [
                {"emailAddress": {"address": cc1}},
                {"emailAddress": {"address": cc2}}
            ],
        },
        "saveToSentItems": True,
    }
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            # Expect 202 Accepted, with no content
            if resp.status not in (200, 202):
                raise RuntimeError(f'Unexpected Graph status code: {resp.status}')
        logging.info(f'Graph email sent to {to_addr} (subject: {subject}).')
    except urllib.error.HTTPError as e:
        details = ''
        try:
            details = e.read().decode('utf-8', errors='ignore')
        except Exception:
            pass
        logging.exception(f'Graph HTTPError {e.code}: {details}')
        raise
    except Exception as e:
        logging.exception(f'Failed to send Graph email to {to_addr}: {e}')
        raise