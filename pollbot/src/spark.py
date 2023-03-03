"""
Copyright 2022 Cisco Systems Inc

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
#import asyncio
import base64, json, requests
import hashlib
import hmac
import io
import os
import tornado.gen
import time

from tornado.httpclient import AsyncHTTPClient, HTTPClient, HTTPRequest, HTTPError
from requests_toolbelt import MultipartEncoder

class Result(object):
    def __init__(self, result, as_file=False):
        self.headers = result.headers
        self.errors = None
        self.code = result.code
        try:
            print("Code:{0}, TrackingId:{1}".format(result.code, result.headers.get("Trackingid")))
        except Exception as ex:
            print("Code:{0}, No TrackingId.".format(result.code))
            print(result.headers)
        try:
            if as_file:
                self.body = result.body
            else:
                self.body = json.loads(result.body.decode("utf-8"))
        except ValueError as e:
            self.errors = e

class Spark(object):

    def __init__(self, token, log=None):
        self.token = token
        self.log = log

    def printf(self, line):
        if self.log != None:
            log.info(line)
        else:
            print(line)

    @classmethod
    def compare_secret(cls, raw, signature_header, phrase):
        hashed = hmac.new(bytes(phrase, 'latin-1'), raw, hashlib.sha1)
        validatedSignature = hashed.hexdigest()
        print('validatedSignature:{0}'.format(validatedSignature))
        print('X-Spark-Signature:{0}'.format(signature_header))
        equal = validatedSignature == signature_header
        print('Equal? {0}'.format(equal))
        return equal

    def simple_request(self, url, data=None, method="GET"):
        headers={"Accept" : "application/json",
                "Content-Type":"application/json",
                "Authorization": "Bearer " + self.token}
        if os.environ.get('MY_USER_AGENT'):
            headers.update({"User-Agent":os.environ.get('MY_USER_AGENT')})
        if data != None:
            if method in [None, "GET"]:
                method = "POST"
            print("User-Agent:{0}- {1} {2}".format(headers.get('User-Agent'), method, url))
            return HTTPRequest(url, method=method, headers=headers, body=data, request_timeout=40)
        else:
            print("User-Agent:{0}- {1} {2}".format(headers.get('User-Agent'), method, url))
            return HTTPRequest(url, method=method, headers=headers, request_timeout=40)

    @tornado.gen.coroutine
    def get(self, url, as_file=False):
        request = self.simple_request(url)
        http_client = AsyncHTTPClient()
        response = yield http_client.fetch(request)
        raise tornado.gen.Return(Result(response, as_file))

    def get_with_retries_std(self, url, results, index, as_file=False):
        retries = 0
        result = None
        while retries <= 3:
            try:
                request = self.simple_request(url)
                http_client = HTTPClient()
                response = http_client.fetch(request)
                result = Result(response, as_file)
                break
            except HTTPError as e:
                retries += 1
                msg = "HTTP Exception get_with_retries_std:{0}".format(e)
                self.printf("{0} {1}".format(e.code, msg))
                try:
                    self.printf("TrackingId:{0}".format(e.response.headers.get("Trackingid")))
                except Exception as te:
                    self.printf("No TrackingId.")
                try:
                    try:
                        msg = json.loads(e.response.body.decode('utf8'))
                    except Exception as ex:
                        msg = e.response.body.decode('utf8')
                except Exception as exx:
                    pass#probably a 599 timeout
                if e.code in [400, 409, 429] or e.code >= 500:
                    if e.code == 429:
                        retry_after = None
                        try:
                            retry_after = e.response.headers.get("Retry-After")
                        except Exception as e:
                            pass
                        if retry_after == None:
                            retry_after = 30
                    else:
                        retry_after = 10
                    msg = "{0} hit, waiting for {1} seconds and then retrying...".format(e.code, retry_after)
                    self.printf(msg)
                    time.sleep(int(retry_after))
                else:
                    print("Not handling HTTPError:{0}.  url:{1}".format(e, url))
                    results[index] = [e, False]
                    return
        results[index] = [result, True]
        return

    @tornado.gen.coroutine
    def get_with_retries_v2(self, url, websocket=None, max_retry_times=3, as_file=False):
        """
        Use this function.
        """
        try:
            #print("started get_with_retries")
            request = self.simple_request(url)
            http_client = AsyncHTTPClient()
            response = yield http_client.fetch(request)
            result = Result(response, as_file)
        except HTTPError as e:
            msg = "HTTP Exception get_with_retries_v2:{0}".format(e)
            self.printf("{0} {1}".format(e.code, msg))
            try:
                self.printf("TrackingId:{0}".format(e.response.headers.get("Trackingid")))
            except Exception as te:
                self.printf("No TrackingId.")
            try:
                try:
                    msg = json.loads(e.response.body.decode('utf8'))
                except Exception as ex:
                    msg = e.response.body.decode('utf8')
            except Exception as exx:
                pass#probably a 599 timeout
            #self.printf("New msg: {0}".format(msg))
            if (e.code in [400, 409, 429] or e.code >= 500) and max_retry_times > 0:
                if e.code == 429:
                    retry_after = None
                    try:
                        retry_after = e.response.headers.get("Retry-After")
                    except Exception as e:
                        pass
                    if retry_after == None:
                        retry_after = 30
                else:
                    retry_after = 10
                msg = "{0} hit, waiting for {1} seconds and then retrying...".format(e.code, retry_after)
                self.printf(msg)
                if websocket != None:
                    update_obj = {"resource":"http_error", "message":msg, "update":True}
                    websocket.write_message(json.dumps(update_obj))
                yield tornado.gen.sleep(int(retry_after))
                max_retry_times-=1
                result = yield self.get_with_retries(url, websocket, max_retry_times)
            else:
                raise HTTPError(e.code, response=e.response) from e
        raise tornado.gen.Return(result)

    @tornado.gen.coroutine
    def get_with_retries(self, url, websocket=None, max_retry_times=3, as_file=False):
        """
        deprecated, use get_with_retries_v2 instead
        """
        try:
            #print("started get_with_retries")
            request = self.simple_request(url)
            http_client = AsyncHTTPClient()
            response = yield http_client.fetch(request)
            result = Result(response, as_file)
        except HTTPError as e:
            msg = "HTTP Exception get_with_retries:{0}".format(e)
            self.printf("{0} {1}".format(e.code, msg))
            try:
                self.printf("TrackingId:{0}".format(e.response.headers.get("Trackingid")))
            except Exception as te:
                self.printf("No TrackingId.")
            try:
                try:
                    msg = json.loads(e.response.body.decode('utf8'))
                except Exception as ex:
                    msg = e.response.body.decode('utf8')
            except Exception as exx:
                pass#probably a 599 timeout
            #self.printf("New msg: {0}".format(msg))
            if (e.code in [400, 409, 429] or e.code >= 500) and max_retry_times > 0:
                if e.code == 429:
                    retry_after = None
                    try:
                        retry_after = e.response.headers.get("Retry-After")
                    except Exception as e:
                        pass
                    if retry_after == None:
                        retry_after = 30
                else:
                    retry_after = 10
                msg = "{0} hit, waiting for {1} seconds and then retrying...".format(e.code, retry_after)
                self.printf(msg)
                if websocket != None:
                    update_obj = {"resource":"http_error", "message":msg, "update":True}
                    websocket.write_message(json.dumps(update_obj))
                yield tornado.gen.sleep(int(retry_after))
                max_retry_times-=1
                result = yield self.get_with_retries(url, websocket, max_retry_times)
            else:
                raise Exception("Not handling HTTPError") from e
        #print("finished get_with_retries")
        raise tornado.gen.Return(result)

    @tornado.gen.coroutine
    def get_me(self):
        url = 'https://webexapis.com/v1/people/me'
        response = yield self.get(url)
        raise tornado.gen.Return(response)

    @tornado.gen.coroutine
    def put(self, url, data):
        request = self.simple_request(url, json.dumps(data), method="PUT")
        http_client = AsyncHTTPClient()
        response = yield http_client.fetch(request)
        raise tornado.gen.Return(Result(response))

    @tornado.gen.coroutine
    def delete(self, url):
        request = self.simple_request(url, method="DELETE")
        http_client = AsyncHTTPClient()
        response = yield http_client.fetch(request)
        raise tornado.gen.Return(Result(response))


    def delete_std(self, url, results, index):
        try:
            request = self.simple_request(url, method="DELETE")
            http_client = HTTPClient()
            response = http_client.fetch(request)
            results[index] = Result(response)
        except HTTPError as e:
            results[index] = e

    @tornado.gen.coroutine
    def post(self, url, data):
        request = self.simple_request(url, json.dumps(data))
        http_client = AsyncHTTPClient()
        response = yield http_client.fetch(request)
        raise tornado.gen.Return(Result(response))

    @tornado.gen.coroutine
    def post_long_message(self, msg, my_dict, split_char="\n", websocket=None, max_retry_times=3):
        url = "https://webexapis.com/v1/messages"
        results = []
        msgs = []
        max_chars = 7439
        while len(msg) >= max_chars:
            chunk = msg[:max_chars]
            rindex = chunk.rfind(split_char)
            if rindex != -1:
                corrected_chunk = msg[:rindex]
                msgs.append(corrected_chunk)
                msg = msg[rindex+1:].strip()
            else:
              msgs.append(chunk)
              msg = msg[max_chars:]
        msgs.append(msg)
        for msg in msgs:
            data = {}
            data.update(my_dict)
            data.update({"markdown":msg})
            result = yield self.post_with_retries(url, data, websocket, max_retry_times)
            results.append(result)
        raise tornado.gen.Return(results)

    @tornado.gen.coroutine
    def post_with_retries(self, url, data, websocket=None, max_retry_times=3):
        try:
            request = self.simple_request(url, json.dumps(data))
            http_client = AsyncHTTPClient()
            response = yield http_client.fetch(request)
            raise tornado.gen.Return(Result(response))
        except HTTPError as e:
            msg = "HTTP Exception post_with_retries:{0}".format(e)
            self.printf("{0} {1}".format(e.code, msg))
            try:
                self.printf("TrackingId:{0}".format(e.response.headers.get("Trackingid")))
            except Exception as te:
                self.printf("No TrackingId.")
            try:
                try:
                    msg = json.loads(e.response.body.decode('utf8'))
                except Exception as ex:
                    msg = e.response.body.decode('utf8')
            except Exception as exx:
                pass#probably a 599 timeout
            #self.printf("New msg: {0}".format(msg))
            if (e.code in [400, 429] or e.code >= 500) and max_retry_times > 0:
                if e.code == 429:
                    retry_after = None
                    try:
                        retry_after = e.response.headers.get("Retry-After")
                    except Exception as e:
                        pass
                    if retry_after == None:
                        retry_after = 30
                else:
                    retry_after = 10
                msg = "{0} hit, waiting for {1} seconds and then retrying...".format(e.code, retry_after)
                self.printf(msg)
                if websocket != None:
                    update_obj = {"resource":"http_error", "message":msg, "update":True}
                    websocket.write_message(json.dumps(update_obj))
                yield tornado.gen.sleep(int(retry_after))
                max_retry_times-=1
                result = yield self.post_with_retries(url, data, websocket, max_retry_times)
            else:
                raise HTTPError(e.code, response=e.response) from e
        raise tornado.gen.Return(result)

    def upload(self, roomId, name, path, filetype, markdown='', personId=None):
        jmsg = {}
        try:
            url = "https://webexapis.com/v1/messages"
            my_fields={'markdown': markdown,
                       'files': (name, open(path, 'rb'), filetype)
                       }
            if roomId == None:
                my_fields.update({'toPersonId': personId})
            else:
                my_fields.update({'roomId': roomId})
            print(my_fields)
            m = MultipartEncoder(fields=my_fields)
            attempts = 0
            while attempts < 3:
                try:
                    r = requests.post(url, data=m,
                                      headers={'Content-Type': m.content_type,
                                               'Authorization': 'Bearer ' + self.token})
                    print("Code:{}".format(r.status_code))
                    if r.status_code == 200:
                        break
                    attempts += 1
                except Exception as ex:
                    print("UPLOAD file send error:{}".format(ex))
                    attempts += 1
            try:
                jmsg.update({"Code":r.status_code})
                jmsg.update(r.json())
                print("TrackingId:{0}".format(r.headers.get("Trackingid")))
                if jmsg.get("errorCode") != None:
                    jmsg.update({"message": "{0} {1}".format(r.status_code, jmsg.get("message"))})
                #print(jmsg)
            except Exception as ex:
                print("Exception:{}".format(ex))
                print("TrackingId:{0}".format(r.headers.get("Trackingid")))
                jmsg.update({"errorCode":r.status_code, "message":"{0} {1}".format(r.status_code, r.reason)})
                #print(jmsg)
        except Exception as e:
            print("MAIN UPLOAD file error:{}".format(e))
        return jmsg

    def upload_queue(self, roomId, name, path, filetype, markdown, queue, parentId=None, personId=None, personEmail=None, isBinary=None):
        try:
            url = "https://webexapis.com/v1/messages"
            my_fields={'markdown': markdown}
            if isBinary == None:
                my_fields.update({'files': (name, open(path, 'rb'), filetype)})
            else:
                my_fields.update({'files': (name, io.BytesIO(isBinary), filetype)})
            if roomId == None:
                if personId != None:
                    my_fields.update({'toPersonId': personId})
                else:
                    my_fields.update({'toPersonEmail': personEmail})
            else:
                my_fields.update({'roomId': roomId})
            if parentId != None:
                my_fields.update({"parentId":parentId})
            m = MultipartEncoder(fields=my_fields)
            jmsg = {}
            attempts = 0
            while attempts < 3:
                r = requests.post(url, data=m,
                                  headers={'Content-Type': m.content_type,
                                           'Authorization': 'Bearer ' + self.token})
                self.printf("Code: {0}".format(r.status_code))
                attempts += 1
                try:
                    jmsg = r.json()
                    jmsg.update({"Code":r.status_code})
                    self.printf("TrackingId:{0}".format(r.headers.get("Trackingid")))
                    if jmsg.get('errors') != None:
                        jmsg.update({"message": "{0} {1}".format(r.status_code, jmsg.get("message"))})
                        jmsg.update({"errorCode":r.status_code})
                    if r.status_code == 200:
                        self.printf('success upload')
                        break
                    else:
                        self.printf('failed upload. No exception raised.')
                except Exception as ex:
                    self.printf("Exception {0}".format(ex))
                    self.printf("TrackingId:{0}".format(r.headers.get("Trackingid")))
                    jmsg = {"errorCode":r.status_code, "message":"{0} {1}".format(r.status_code, r.reason)}
                    self.printf('failed upload.')
            self.printf('putting jmsg to queue.')
            queue.put(jmsg)
            self.printf("upload_queue finished")
        except Exception as e:
            self.printf("UPLOAD file error {0}".format(e))
            queue.put(e)
