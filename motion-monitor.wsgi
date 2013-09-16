#!/usr/bin/env python

from cgi import parse_qs, escape
from wsgiref.simple_server import make_server
import socket
import json

def __validate_request(request):
    assert type(request) == dict, "Request should be a dictionary: %s" % request
    assert "type" in request, "Request does not specify what type it is: %s" % request
    assert request["type"] in ["camera_summary",
                               "get_image"], "Not a valid request"
                               
def __get_post_data(environ):
    # the environment variable CONTENT_LENGTH may be empty or missing
    try:
        request_body_size = int(environ.get('CONTENT_LENGTH', 0))
    except (ValueError):
        request_body_size = 0
    
    # Get the query string from the request body
    request_body = environ['wsgi.input'].read(request_body_size)
    return json.loads(request_body)

def __get_get_data(environ):
    qs = parse_qs(environ['QUERY_STRING'])
    for k, v in qs.items():
        if len(v) < 2:
            # This doesn't need to be a list, just get the first value element
            qs[k] = v[0]
    return qs

def __request_data(data):
    # Get the data from the socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.connect(('localhost', 8889))
    sock.send(json.dumps(data))
    return sock.recv(4096)

def application(environ, start_response):
    request_method = environ["REQUEST_METHOD"].lower()
    try:
        if request_method == "post":
            data = __get_post_data(environ)
        elif request_method == "get":
            data = __get_get_data(environ)
    except (TypeError, ValueError) as e:
        # Error
		start_response('503 Service Unavailable', [('Content-Type', 'text/plain')])
		return ['Invalid request type: %s' % e]
    
    try:
        __validate_request(data)
    except AssertionError as e:
        start_response('503 Service Unavailable', [('Content-Type', 'text/plain')])
        return ['Invalid request: %s' % e]
    
    try:
        output = __request_data(data)
    except Exception as e:
        # Socket errors
		print e
		start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
		return ['Error processing request: %s' % e]
    
    # Need to check if this allow-origin is really needed.    
    response_headers = [('Access-Control-Allow-Origin', "*"),
                        ('Content-msg', 'application/json'),
                        ('Content-Length', str(len(output)))]
    start_response('200 OK', response_headers)
    return [output]
    

# The following is for test purposes.
if __name__ == '__main__':
    httpd = make_server('localhost', 80, application)
    httpd.serve_forever()
