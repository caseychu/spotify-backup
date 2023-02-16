import http.server
import logging
import re


class Server(http.server.HTTPServer):
    def __init__(self, host, port):
        http.server.HTTPServer.__init__(self, (host, port), _RequestHandler)

    # Disable the default error handling.
    def handle_error(self, request, client_address):
        raise


class _RequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # The Spotify API has redirected here, but access_token is hidden in the URL fragment.
        # Read it using JavaScript and send it to /token as an actual query string...
        if self.path.startswith('/redirect'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<script>location.replace("token?" + location.hash.slice(1));</script>')

        # Read access_token and use an exception to kill the server listening...
        elif self.path.startswith('/token?'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<script>close()</script>Thanks! You may now close this window.')

            access_token = re.search('access_token=([^&]*)', self.path).group(1)
            logging.info(f'Received access token from Spotify: {access_token}')
            raise Authorization(access_token)

        else:
            self.send_error(404)

    # Disable the default logging.
    def log_message(self, format, *args):
        pass


class Authorization(Exception):
    def __init__(self, access_token):
        self.access_token = access_token
