import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")

auth_code = None

class AuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = parse_qs(urlparse(self.path).query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2>Autenticacion exitosa. Puedes cerrar esta ventana.</h2>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Error: no se recibio el codigo.")

    def log_message(self, format, *args):
        pass  # silencia los logs del servidor

def main():
    url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri=http://localhost:8000"
        f"&approval_prompt=force"
        f"&scope=read,activity:read_all"
    )

    print("Abriendo Strava en tu navegador...")
    webbrowser.open(url)

    server = HTTPServer(("localhost", 8000), AuthHandler)
    print("Esperando autorizacion de Strava...")
    server.handle_request()

    if not auth_code:
        print("No se recibio codigo. Intenta de nuevo.")
        return

    # Intercambiar codigo por tokens
    response = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code"
    })

    if response.status_code != 200:
        print(f"Error al obtener tokens: {response.text}")
        return

    tokens = response.json()
    refresh_token = tokens["refresh_token"]
    athlete = tokens.get("athlete", {})

    print(f"\n✓ Autenticado como: {athlete.get('firstname', '')} {athlete.get('lastname', '')}")
    print(f"\nCopia este refresh token en tu archivo .env:")
    print(f"\nSTRAVA_REFRESH_TOKEN={refresh_token}\n")

if __name__ == "__main__":
    main()