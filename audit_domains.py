#!/usr/bin/env python3
import json
import os
import urllib.request
import urllib.error
import ssl
from urllib.parse import urlparse

DIRECTORY = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(DIRECTORY, "data.json")

def audit_domain(domain, expect_tinyauth):
    url = f"https://{domain}"
    
    # Disable redirect following in urllib to see where it directs us first
    class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        def http_error_302(self, req, fp, code, msg, headers):
            return fp
        def http_error_301(self, req, fp, code, msg, headers):
            return fp
        def http_error_307(self, req, fp, code, msg, headers):
            return fp
        def http_error_303(self, req, fp, code, msg, headers):
            return fp

    opener = urllib.request.build_opener(NoRedirectHandler)
    
    status_code = None
    redirect_url = None
    error_msg = None
    
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Caddy-Auth-Auditor/1.0"})
        with opener.open(req, timeout=5) as response:
            status_code = response.getcode()
            redirect_url = response.getheader("Location")
    except urllib.error.HTTPError as e:
        status_code = e.code
        redirect_url = e.headers.get("Location")
    except urllib.error.URLError as e:
        if isinstance(e.reason, ssl.SSLError):
            error_msg = f"SSL Error: {e.reason.reason}"
        else:
            error_msg = f"Connection Error: {e.reason}"
    except Exception as e:
        error_msg = f"Error: {str(e)}"

    # Determine status and match
    if error_msg:
        return "❌ " + error_msg, "Fail"
        
    is_redirect_to_sso = False
    if redirect_url:
        parsed_redirect = urlparse(redirect_url)
        if "sso-gateway.wileyriley.com" in parsed_redirect.netloc:
            is_redirect_to_sso = True

    if expect_tinyauth:
        if is_redirect_to_sso:
            return f"Redirects to SSO (Code {status_code})", "Match"
        else:
            actual = f"Direct Code {status_code}" if not redirect_url else f"Redirects to {redirect_url}"
            return f"⚠️ Mismatch: Expected SSO, got {actual}", "Mismatch"
    else:
        if is_redirect_to_sso:
            return f"⚠️ Mismatch: Public domain redirected to SSO (Code {status_code})", "Mismatch"
        else:
            result = f"Resolves Direct (Code {status_code})"
            if redirect_url:
                result += f" -> {redirect_url}"
            return result, "Match"

def main():
    if not os.path.exists(DATA_PATH):
        print(f"Error: {DATA_PATH} not found. Please run parser.py first.")
        return

    with open(DATA_PATH, "r") as f:
        containers = json.load(f)

    # Gather unique domains
    domains = {}
    for c in containers:
        domain = c.get("caddy_public")
        if domain and domain.strip() and domain != "-":
            # Some labels define multiple comma-separated domains
            for d in domain.split(","):
                d = d.strip()
                if d:
                    expect_ta = c.get("tinyauth", "No").lower() == "yes"
                    # If any container config requires TinyAuth for this domain, expect it
                    domains[d] = domains.get(d, False) or expect_ta

    print("\nStarting Homelab Proxy and Authentication Audit...\n")
    print(f"| {'Domain Name':<35} | {'Expected Auth':<13} | {'Real-time Status':<55} | {'Status':<8} |")
    print(f"| {'-':-<35} | {'-':-<13} | {'-':-<55} | {'-':-<8} |")
    
    matches = 0
    mismatches = 0
    failures = 0

    for domain in sorted(domains.keys()):
        expect_ta = domains[domain]
        status, category = audit_domain(domain, expect_ta)
        
        expect_str = "TinyAuth" if expect_ta else "Public"
        
        if category == "Match":
            matches += 1
            cat_label = "✅ Match"
        elif category == "Mismatch":
            mismatches += 1
            cat_label = "⚠️ Mismatch"
        else:
            failures += 1
            cat_label = "❌ Error"
            
        print(f"| {domain:<35} | {expect_str:<13} | {status:<55} | {cat_label:<8} |")

    total = len(domains)
    print(f"\nAudit complete: {total} domains scanned. {matches} Match, {mismatches} Mismatches, {failures} Connection/SSL Failures.\n")

if __name__ == "__main__":
    main()
