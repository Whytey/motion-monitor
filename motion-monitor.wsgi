#!/usr/bin/env python

from cgi import parse_qs, escape
from wsgiref.simple_server import make_server
import socket
import json
import base64

JSON_TYPE = "JSON"
JPEG_TYPE = "JPEG"

HTTP_200 = "200 OK"
HTTP_500 = "500 Internal Server Error"
HTTP_503 = "503 Service Unavailable"
#
def __validate_request(request):
    assert type(request) == dict, "Request should be a dictionary: %s" % request
    assert "type" in request, "Request does not specify what type it is: %s" % request
    assert request["type"] in ["camera_summary",
                               "get_picture"], "Not a valid request: %s" % request
                               
    if request["type"] == "get_picture":
        return JPEG_TYPE
    
    # By default, we return JSON
    return JSON_TYPE
                               
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
    rxd_data = []
    while True:
        data = sock.recv(65635)
        if not data: break
        rxd_data.append(data)
    return ''.join(rxd_data)

def __error_response(start_response, http_status, error_msg):
    start_response(http_status, [('Content-Type', 'text/plain')])
    return [error_msg]

def __jpeg_response(start_response, response_json):
    # Extract the image bytes from the JSON
    image_bytes = response_json["bytes"]
    decoded_string = base64.b64decode(image_bytes)
    
    # Need to check if this allow-origin is really needed.    
    response_headers = [('Access-Control-Allow-Origin', "*"),
                        ('Content-Type', 'image/jpeg'),
                        ('Content-Length', str(len(decoded_string)))]
    start_response(HTTP_200, response_headers)
    return [decoded_string]

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
        return_type = __validate_request(data)
    except AssertionError as e:
        return __error_response(start_response, HTTP_503, 'Invalid request: %s' % e)
    
    try:
        response = __request_data(data)
    except Exception as e:
        # Socket errors
        return __error_response(start_response, HTTP_500, 'Error processing request: %s' % e)
        
    response_json = json.loads(response)
    print response_json
    
    if "error" in response_json:
        return __error_response(start_response, HTTP_503, str(response_json["error"])) 
        
    # Do the appropriate response now.
    if return_type == JPEG_TYPE:
        return __jpeg_response(start_response, response_json)
    
    elif return_type == JSON_TYPE:
        return __json_response(start_response, response_json)
    else:    
        # If we get to here, we must be in error, return error
        return __error_response(start_response, HTTP_503, "Unexpected return type.")
   

# The following is for test purposes.
if __name__ == '__main__':
    httpd = make_server('localhost', 80, application)
    httpd.serve_forever()
