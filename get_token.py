import webbrowser, urllib.request, urllib.parse, json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

client_id = "86m7uan69amyiy"
client_secret = input("Paste your Primary Client Secret: ").strip()
redirect_port = 9876
token_result = {}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(self.path).query)
        if 'code' in qs:
            code = qs['code'][0]
            self.send_response(200)
            self.send_header('Content-Type','text/html')
            self.end_headers()
            self.wfile.write(b"<h2>Token received! You can close this tab.</h2>")
            try:
                data = urllib.parse.urlencode({
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': 'https://rochesterschooloffitness.com',
                    'client_id': client_id,
                    'client_secret': client_secret
                }).encode()
                req = urllib.request.Request('https://www.linkedin.com/oauth/v2/accessToken', data=data)
                resp = urllib.request.urlopen(req)
                result = json.loads(resp.read().decode())
                token_result['token'] = result['access_token']
                print("\n" + "="*50)
                print("SUCCESS! Your access token:")
                print("="*50)
                print(result['access_token'])
                print("="*50)
                print(f"Expires in: {result.get('expires_in', 'unknown')} seconds")
                print("\nCopy this token and update your GitHub secret!")
            except Exception as e:
                print(f"\nError exchanging code: {e}")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No code found in URL")

server = HTTPServer(('localhost', redirect_port), Handler)
t = threading.Thread(target=server.handle_request)
t.daemon = True
t.start()

url = (
    f"https://www.linkedin.com/oauth/v2/authorization"
    f"?response_type=code"
    f"&client_id={client_id}"
    f"&redirect_uri=https://rochesterschooloffitness.com"
    f"&scope=w_member_social%20openid%20profile%20email"
    f"&state=TFI123"
)
print(f"\nOpening browser... Click Allow, then wait here.")
webbrowser.open(url)
t.join(timeout=120)
server.server_close()
if 'token' not in token_result:
    print("\nTimed out. Try again.")
