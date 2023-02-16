import http.server
import secrets
import urllib.parse


class _RequestHandler(http.server.BaseHTTPRequestHandler):
    server: "Server"

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        if url.path == self.server.REDIRECT_PATH:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                f"<script>location.replace(\"{self.server.TOKEN_PATH}?\" + "
                "location.hash.slice(1));</script>"
                .encode()
            )
        elif url.path == self.server.TOKEN_PATH:
            query = urllib.parse.parse_qs(url.query)
            if query["state"][0] != self.server.state:
                self.send_error(401)
            self.server.token = query["access_token"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<script>close()</script>Thanks! You may now close this "
                b"window."
            )

    def log_message(self, format, *args) -> None:
        pass


class Server(http.server.HTTPServer):
    _HOST = "127.0.0.1"
    _PORT = 43019
    REDIRECT_PATH = "/redirect"
    TOKEN_PATH = "/token"

    def __init__(self) -> None:
        self.state = "".join(
            chr(secrets.choice(range(0x20, 0x7E + 1))) for _ in range(32)
        )
        self.token: str | None = None
        super().__init__((self._HOST, self._PORT), _RequestHandler)

    @classmethod
    def redirect_uri(cls) -> str:
        return f"http://{cls._HOST}:{cls._PORT}{cls.REDIRECT_PATH}"
