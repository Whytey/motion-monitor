#!/usr/bin/env python

from cgi import parse_qs, escape
from wsgiref.simple_server import make_server
import json
import re
import socket
import sys
from monitor.stream.handlers import SnapshotFrameHandler, MotionFrameHandler, TimelapseVideoHandler, LiveFrameHandler, LiveVideoHandler


JSON_TYPE = "JSON"
JPEG_TYPE = "JPEG"

HTTP_200 = "200 OK"
HTTP_500 = "500 Internal Server Error"
HTTP_503 = "503 Service Unavailable"
#
def __validate_request(request):
    assert type(request) == dict, "Request should be a dictionary: %s" % request
    assert "method" in request, "Request does not specify what method it is: %s" % request
    
    return request["method"]
                                                              
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

def __error_response(start_response, http_status, error_msg):
    start_response(http_status, [('Content-Type', 'text/plain')])
    return [error_msg]

def __byte_response(start_response, handler):
    response_headers = []
    for k, v in handler.getResponseHeaders().items():
        response_headers.append((k, v))
        
    start_response(HTTP_200, response_headers)
    
    # handler is an Iterator
    return handler

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
        request_type = __validate_request(data)
    except AssertionError as e:
        return __error_response(start_response, HTTP_503, 'Invalid request: %s' % e)
    
    try:
        if request_type.lower() == "snapshotframe":
            handler = SnapshotFrameHandler(data)
        elif request_type.lower() == "motionframe":
            handler = MotionFrameHandler(data)
        elif request_type.lower() == "timelapsevideo":
            handler = TimelapseVideoHandler(data)
        elif request_type.lower() == "liveframe":
            handler = LiveFrameHandler(data)
        elif request_type.lower() == "livevideo":
            handler = LiveVideoHandler(data)
        else:
            raise KeyError("Unknown method requested: %s" % request_type)
        return __byte_response(start_response, handler)
    except Exception as e:
        # Socket errors
        import traceback
        traceback.print_exc()
        return __error_response(start_response, HTTP_500, 'Error processing request: %s' % e)
        

# The following is for test purposes.
if __name__ == '__main__':
    httpd = make_server('localhost', 8080, application)
    httpd.serve_forever()
