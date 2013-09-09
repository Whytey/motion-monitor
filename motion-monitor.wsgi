#!/usr/bin/env python

from cgi import parse_qs, escape
from wsgiref.simple_server import make_server
import socket
import json

def application(environ, start_response):

	# the environment variable CONTENT_LENGTH may be empty or missing
	try:
		request_body_size = int(environ.get('CONTENT_LENGTH', 0))
	except (ValueError):
		request_body_size = 0
	
	# Get the query string from the request body
	request_body = environ['wsgi.input'].read(request_body_size)
	params = parse_qs(request_body)
	
	msg = params.get('msg', [''])[0]
	msg = escape(msg)
	
	# For testing
	msg = {'type': 'camera_summary'}
	
	
	
	# Get the data from the socket
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

	sock.connect(('localhost', 8889))
	sock.send(json.dumps(msg))
	output = sock.recv(4096)

	status = '200 OK'

	response_headers = [('Content-msg', 'application/json'),
						('Content-Length', str(len(output)))]
	start_response(status, response_headers)

	return [output]
	

# The following is for test purposes.
if __name__ == '__main__':
	httpd = make_server('localhost', 8051, application)
	httpd.serve_forever()
