#!/usr/bin/env python

from cgi import parse_qs, escape
from wsgiref.simple_server import make_server
import base64
import json
import re
import socket
import sys


JSON_TYPE = "JSON"
JPEG_TYPE = "JPEG"

HTTP_200 = "200 OK"
HTTP_500 = "500 Internal Server Error"
HTTP_503 = "503 Service Unavailable"
#
def __validate_request(request):
    assert type(request) == dict, "Request should be a dictionary: %s" % request
    assert "method" in request, "Request does not specify what method it is: %s" % request
#    assert request["method"] in ["camera.get",
#                                 "image.get"], "Not a valid request: %s" % request
                                                              
def __get_post_data(environ):
    # the environment variable CONTENT_LENGTH may be empty or missing
    try:
        request_body_size = int(environ.get('CONTENT_LENGTH', 0))
    except (ValueError):
        request_body_size = 0
    
    # Get the query string from the request body
    request_body = environ['wsgi.input'].read(request_body_size)
    return json.loads(request_body)

def __qs_parse(params):
    """
    Takes a one-dimensional dictionary and converts it into a correctly
    formed multi-dimensional dictionary.
    """
    results = {}
    for key in params:
        if '[' in key:
            key_list = re.split("[\[\]]+", key)
            key_list.remove('')

            d = results
            for partial_key in key_list[:-1]:
                if partial_key not in d:
                    d[partial_key] = dict()
                d = d[partial_key]
            d[key_list[-1]] = params[key]
        else:
            results[key] = params[key]
    return results

def __get_get_data(environ):
    # Get a list of params from the qs.
    qs = parse_qs(environ['QUERY_STRING'])
    
    # Ensure there are no duplicates and remove erroneous list formatting
    for k, v in qs.items():
        if len(v) > 1:
            raise ValueError("Same parameter listed more than once: %s" % k)
        qs[k] = v[0] # No need for lists.
        
    # Take the 1-dim dict and inflate it to multi-dim.
    qs = __qs_parse(qs)
    print qs
    return qs

def __request_data(data):
    # Get the data from the socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.connect(('192.168.0.100', 8889))
    sock.send(json.dumps(data))
    rxd_data = []
    while True:
        print >> sys.stderr, "Waiting for data"
        data = sock.recv(65635)
        print >> sys.stderr, "Got data"
        if not data: break
        rxd_data.append(data)
    return ''.join(rxd_data)

def __error_response(start_response, http_status, error_msg):
    start_response(http_status, [('Content-Type', 'text/plain')])
    return [error_msg]

def __json_response(start_response, response_json):
    response_string = json.dumps(response_json)
    # Need to check if this allow-origin is really needed.    
    response_headers = [('Access-Control-Allow-Origin', "*"),
                        ('Content-Type', 'application/json'),
                        ('Content-Length', str(len(response_string)))]
    start_response(HTTP_200, response_headers)
    return [response_string]

def application(environ, start_response):
    request_method = environ["REQUEST_METHOD"].lower()
    try:
        if request_method == "post":
            data = __get_post_data(environ)
        elif request_method == "get":
            data = __get_get_data(environ)
    except (TypeError, ValueError) as e:
        # Error
        return __error_response(start_response, HTTP_503, 'Invalid request type: %s' % e)
    
    try:
        __validate_request(data)
    except AssertionError as e:
        return __error_response(start_response, HTTP_503, 'Invalid request: %s' % e)
    
    try:
        response = __request_data(data)
    except Exception as e:
        # Socket errors
        return __error_response(start_response, HTTP_500, 'Error processing request: %s' % e)
        
    response_json = json.loads(response)
    print response_json
    
#    if "error" in response_json:
#        return __error_response(start_response, HTTP_503, str(response_json["error"])) 
        
    return __json_response(start_response, response_json)
   

# The following is for test purposes.
if __name__ == '__main__':
    httpd = make_server('localhost', 8080, application)
    httpd.serve_forever()
