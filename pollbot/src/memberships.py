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
import json

import tornado.gen
import tornado.web


class MembershipsHandler(tornado.web.RequestHandler):
    def printf(self, line):
        log = self.application.settings.get('log')
        if log != None:
            log.info(line)
        else:
            print(line)

    @tornado.gen.coroutine
    def intro_msg(self, event):
        pass


    @tornado.gen.coroutine
    def post(self):
        retVal = "true"
        try:
            req = self.request.body
            data = json.loads(req)
            self.printf("POST data:{0}".format(data))
            msg = None
            if data['data']['personId'] == self.application.settings['settings'].bot_id:
                if data['event'] == "created":
                    yield self.intro_msg(data)
                if data['data']['isModerator'] == True:
                    try:
                        membership_id = data['data']['id']
                        result = yield self.application.settings['spark'].put("https://webexapis.com/v1/memberships/{0}".format(membership_id),
                                                                          {"isModerator":False})
                        msg = "I automatically removed myself from being a space moderator."
                    except Exception as e:
                        self.printf("UpdateMembership Exception: {0}".format(e))
                        msg = "I failed to remove myself as a moderator. "
                        try:
                            msg += "{0} {1}\n\n".format(e.code, e.message)
                            self.printf("Tracking ID: {0}".format(e.response.headers['Trackingid']))
                        except Exception as ex:
                            self.printf("Code or Body exception: {0}".format(ex))
                        self.printf(msg)
            if msg != None:
                result = yield self.application.settings['spark'].post("https://webexapis.com/v1/messages",
                                                                       {"toPersonId": data['actorId'], "markdown": msg})
        except Exception as exx:
            self.printf("Memberships General Exception: {0}".format(exx))
            retVal = "false"
        self.write(retVal)
