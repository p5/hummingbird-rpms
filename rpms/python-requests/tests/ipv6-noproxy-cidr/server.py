from http.server import SimpleHTTPRequestHandler, HTTPServer
import socket
import sys
class IPv6OnlyHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        client_address = self.client_address[0]
        # Check if the client address is an IPv6 address
        if ":" in client_address:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Hello')
        else:
            # Raise a RuntimeError if the client address is an IPv4 address
            raise SystemExit(f"IPv4 address ({client_address}) detected. Only IPv6 addresses are allowed.")

class HTTPServerV6(HTTPServer):
  address_family = socket.AF_INET6

if __name__ == '__main__':
    # Use IPv6 address and port 8080
    server_address = ('::', 8888)
    httpd = HTTPServerV6(server_address, IPv6OnlyHandler)
    print('Server running on port 8888...')
    httpd.serve_forever()
