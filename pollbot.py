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
# -*- coding: utf-8 -*-
#!/usr/bin/env python
import inflect
import json
import os
import traceback

import tornado.gen
import tornado.httpserver
import tornado.ioloop
import tornado.web

from pollbot.src.app_helper import AppHelper
from pollbot.src.basehandler import BaseHandler, Question, CustomMembershipsHandler
from pollbot.src.card_builder import CardBuilder
from pollbot.src.mongo_db_controller import MongoController
from pollbot.src.settings import Settings

from pollbot.src.alive import AliveHandler
from pollbot.src.mongo_db_metrics import MetricsDB
from pollbot.src.spark import Spark

from tornado.options import define, options, parse_command_line
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPError

define("debug", default=False, help="run in debug mode")

class MainHandler(BaseHandler):

    @tornado.gen.coroutine
    def post(self):
        """
        """
        try:
            card_json = {}
            msg = ""
            direct_msg = ""
            in_message = None
            print("Webhook BODY: {0}".format(self.request.body))
            print("Webhook HEADERS: {0}".format(self.request.headers))
            webhook = json.loads(self.request.body)
            if webhook['data']['personId'] != Settings.bot_id:
                if webhook['data']['personEmail'].endswith('@sparkbot.io') or webhook['data']['personEmail'].endswith('@webex.bot'):
                    print("Message from another bot. Ignoring.")
                else:
                    secret_equal = Spark.compare_secret(self.request.body, self.request.headers.get('X-Spark-Signature'), Settings.secret_phrase)
                    if secret_equal or Settings.secret_phrase.lower()=="none":
                        result = yield self.application.settings['spark'].get_with_retries_v2('https://webexapis.com/v1/messages/{0}'.format(webhook['data']['id']))
                        print("RESULT.BODY:{0}".format(result.body))
                        original_in_message = result.body.get('text','')
                        print(Settings.bot_names)
                        in_message = original_in_message
                        for name in Settings.bot_names:
                            in_message = in_message.replace(name, "", 1).strip()
                        print("in_message:{0}".format(in_message))
                        in_message_lower = in_message.lower()
                        print("^^^^^^^^^^^^^^^^^")
                        room_id = webhook['data']['roomId']
                        actor = webhook['actorId']
                        room_type = webhook['data']['roomType']
                        command = in_message_lower
                        if in_message_lower in ["hi", "hello", "help"]:
                            card_json = yield self.help(actor, room_id, room_type)
                        elif in_message_lower in ["typed commands", "help typed", "help typed commands", "help commands", "commands"]:
                            msg = self.help_msg()
                        elif in_message_lower in ["create poll", "createcard"]:
                            exists = self.application.settings['db'].find_one({"room_id":room_id})
                            if exists != None:
                                msg += 'An active poll created by {0} already exists for this space.  \n'.format(exists.get('creator_name'))
                            else:
                                card_json = self.application.settings['card_builder'].build_question_card(room_id, room_type, actor)
                        elif in_message_lower in ["results", "status"]:
                            current_poll = self.get_current_poll(room_id)
                            direct_msg = self.get_result_permission(room_id, actor, current_poll)
                            if direct_msg == "":
                                card_json = self.application.settings['card_builder'].show_results(actor, current_poll, True)
                        elif in_message_lower in ["stop", "stop poll"]:
                            msg = yield self.stop_poll(actor, room_id)
                        elif in_message_lower.startswith("create"):
                            command = "create"
                            questions, users, inputs, msg = self.build_typed_create(in_message)
                            if msg == "":
                                msg += yield self.create_poll(room_id, actor, questions, users, inputs)
                        elif in_message_lower.startswith("edit"):
                            current_poll = self.get_current_poll(room_id)
                            direct_msg = self.edit_poll_permission(actor, current_poll)
                            if direct_msg == "":
                                card_json = self.application.settings['card_builder'].build_edit_card(actor, current_poll)
                        elif in_message_lower.startswith("public"):
                            command = "public"
                            msg = self.application.settings['db'].update_privacy(room_id, False)
                        elif in_message_lower.startswith("private"):
                            command = "private"
                            msg = self.application.settings['db'].update_privacy(room_id, True)
                        elif in_message_lower.startswith("duration"):
                            command = "duration"
                            in_message_lower = in_message_lower.replace('duration','').strip()
                            msg = self.application.settings['db'].update_duration(room_id, in_message_lower)
                        elif options.debug:
                            if in_message_lower == "answer card":
                                card_json = self.application.settings['card_builder'].build_answer_card(room_id, {"Why is the sky blue?":["Because", "It just is", "idk what's up with you?"]}, "Test User")
                            elif in_message_lower == "options card":
                                card_json = self.send_card(Settings.additional_options_card, room_id, "Adaptive Card - Additional Options")
                            elif in_message_lower == "multiple questions":
                                card_json = self.application.settings['card_builder'].build_multi_question_card(room_id, room_type, actor)
                            elif in_message_lower == "step 2":
                                card_json = self.application.settings['card_builder'].build_question_card_step_2(room_id, actor)
                            else:
                                card_json = yield self.help(actor, room_id, room_type)
                        else:
                            command = "unrecognized"
                            card_json = yield self.help(actor, room_id, room_type)

                        if direct_msg != '':
                            yield self.application.settings['spark'].post_with_retries('https://webexapis.com/v1/messages', {'markdown':direct_msg, 'toPersonId':actor})
                        if card_json != {}:
                            print(json.dumps(card_json, indent=4))
                            yield self.application.settings['spark'].post_with_retries('https://webexapis.com/v1/messages', card_json)
                        elif msg != "":
                            yield self.application.settings['spark'].post_with_retries('https://webexapis.com/v1/messages', {'markdown':msg, 'roomId':room_id})
                        self.application.settings['metrics_db'].insert(webhook['data']['personEmail'], command, in_message)
                    else:
                        print("Secret does not match!  Doing nothing.")
        except Exception as ex:
            print("Main Exception")
            traceback.print_exc()
        self.write("true")


class CardsHandler(BaseHandler):

    @tornado.gen.coroutine
    def post(self):
        try:
            secret_equal = Spark.compare_secret(self.request.body, self.request.headers.get('X-Spark-Signature'), Settings.secret_phrase)
            if secret_equal or Settings.secret_phrase.lower()=="none":
                webhook = json.loads(self.request.body)
                print("CardsHandler Webhook Attachment Action Received:")
                print(webhook)
                attachment = yield self.application.settings['spark'].get_with_retries_v2('https://webexapis.com/v1/attachment/actions/{0}'.format(webhook['data']['id']))
                print("attachment.BODY:{0}".format(attachment.body))
                message_id = attachment.body['messageId']
                room_id = attachment.body['roomId']
                person_id = attachment.body['personId']
                inputs = attachment.body.get('inputs', {})
                print("messageId:{0}".format(message_id))
                print("roomId:{0}".format(room_id))
                print("personId:{0}".format(person_id))
                print("inputs:{0}".format(inputs))
                reply_msg = ''
                direct_msg = ''
                card_json = {}
                question = inputs.get('question')
                answers  = inputs.get('answers')
                users    = inputs.get('users')
                command = None
                if inputs.get('person_id') != None and inputs.get('person_id') != person_id:
                    direct_msg += "Hold up! This is someone else's poll. You can start yours by typing **@pollbot create poll.**  \n"
                else:
                    if type(question) == str:
                        question = question.strip()
                    if type(answers) == str:
                        answers = answers.strip()
                    if type(users) == str and users.strip() == "":
                        reply_msg += "Users field cannot be empty.  \n"
                    else: #users can be None, just can't be empty string if included.
                        command = "card_" + inputs.get('submit')
                        if inputs.get('submit') == "help_typed":
                            direct_msg += self.help_msg()
                        elif inputs.get('submit') == "start":
                            room_details = yield self.application.settings['spark'].get_with_retries_v2('https://webexapis.com/v1/rooms/{0}'.format(room_id))
                            exists = self.application.settings['db'].find_one({"room_id":room_id})
                            if exists != None:
                                room_name = room_details.body.get("title")
                                direct_msg += 'An active poll created by {0} already exists for the space, "{1}".  \n'.format(exists.get('creator_name'), room_name)
                            else:
                                room_type = room_details.body.get("type")
                                card_json = self.application.settings['card_builder'].build_question_card(room_id, room_type, person_id)
                        elif inputs.get('submit') == "cancel":
                            yield self.delete_message(message_id)
                        elif inputs.get('submit') == "stop":
                            yield self.delete_message(message_id)
                            direct_msg = yield self.stop_poll(person_id, inputs.get('room_id'), True)
                        elif inputs.get('submit') == "edit":
                            current_poll = self.get_current_poll(inputs.get('room_id'))
                            direct_msg = self.edit_poll_permission(person_id, current_poll)
                            if direct_msg == "":
                                card_json = self.application.settings['card_builder'].build_edit_card(person_id, current_poll)
                        elif inputs.get('submit') == "save":
                            yield self.delete_message(message_id)
                            current_poll = self.get_current_poll(inputs.get('room_id'))
                            direct_msg = self.edit_poll_permission(person_id, current_poll)
                            if direct_msg == "":
                                private = inputs.get('private', 'true') == 'true'
                                current_poll = self.application.settings['db'].update_details(inputs.get('room_id'), private, inputs.get('duration'))
                                yield self.application.settings['app_helper'].poll_check(current_poll.get('room_id'))
                                card_json = self.application.settings['card_builder'].build_edited_setup_card(current_poll)
                        elif inputs.get('submit') == "status":
                            current_poll = self.get_current_poll(inputs.get('room_id'))
                            direct_msg = self.get_result_permission(inputs.get('room_id'), person_id, current_poll)
                            if direct_msg == "":
                                card_json = self.application.settings['card_builder'].show_results(person_id, current_poll, True)
                        elif inputs.get('submit') == "answer":
                            direct_msg = yield self.track_answer(room_id, person_id, inputs)
                        elif inputs.get('submit') == "results":
                            current_poll = self.get_current_poll(room_id)
                            direct_msg = self.get_result_permission(room_id, person_id, current_poll)
                            if direct_msg == "":
                                card_json = self.application.settings['card_builder'].show_results(person_id, current_poll, True)
                        elif inputs.get('submit') == "multiple":
                            duration = inputs.get('duration')
                            include_self = inputs.get('include_self')
                            private  = inputs.get('private')
                            anon = inputs.get('anon')
                            multi_answers = inputs.get('multi_answers')
                            room_type = "group"
                            if users:
                                room_type = "direct"
                            card_json = self.application.settings['card_builder'].build_multi_question_card(room_id, room_type, person_id, question, answers, users, duration, include_self, private, anon, multi_answers)
                            yield self.delete_message(message_id)
                        else:
                            command = None
                            if question == "":
                                reply_msg += "Question field cannot be empty.  \n"
                            if answers == "":
                                reply_msg += "Answers field cannot be empty.  \n"
                            if reply_msg == "":
                                if inputs.get('submit') in ["next", "create"]:
                                    if inputs.get('submit') == "next": #Must be step 1 in a direct space, if this is True
                                        card_json = self.application.settings['card_builder'].build_question_card_step_2(room_id, person_id, question, answers)
                                        yield self.delete_message(message_id)
                                        command = "card_" + inputs.get('submit')
                                    else:
                                        question_obj = Question(question, answers)
                                        if len(question_obj.answers) > 1:
                                            yield self.delete_message(message_id)
                                            reply_msg += yield self.create_poll(room_id, person_id, [question_obj], users, inputs)
                                            command = "card_" + inputs.get('submit')
                                        else:
                                            reply_msg += "Question must have more than one unique answer (separate answers with semicolons).  \n"
                                elif inputs.get('submit') == "create_multiple":
                                    questions = []
                                    keys = sorted(inputs)
                                    for k in keys:
                                        if k.startswith('question'):
                                            i = k.replace('question','')
                                            p = inflect.engine()
                                            place = p.number_to_words(p.ordinal(i)).capitalize()
                                            quest = inputs.get(k).strip()
                                            answ = inputs.get('answers'+i).strip()
                                            print('i:{0}'.format(i))
                                            print('quest:{0}, answ:{1}'.format(quest, answ))
                                            if quest != "" and answ != "":
                                                question_obj = Question(quest, answ)
                                                if len(question_obj.answers) > 1:
                                                    questions.append(question_obj)
                                                else:
                                                    reply_msg += "{0} question must have more than one unique answer (separate answers with semicolons).  \n".format(place)
                                            elif quest != "" and answ == "":
                                                reply_msg += "It looks like you missed the answers field for the {0} question.  \n".format(place)
                                            elif quest == "" and answ != "":
                                                reply_msg += "It looks like you missed the question field for the {0} set of answers.  \n".format(place)
                                    if questions == [] and reply_msg == "":
                                        reply_msg += "It looks like you missed some fields. To finish creating your poll, I need help filling in at least the first question and answer set.  \n"
                                    elif reply_msg == "":
                                        yield self.delete_message(message_id)
                                        reply_msg += yield self.create_poll(room_id, person_id, questions, users, inputs)
                                        command = "card_" + inputs.get('submit')
                                else:
                                    print("unrecognized card submit value.")
                if direct_msg != '':
                    yield self.application.settings['spark'].post_with_retries('https://webexapis.com/v1/messages', {'markdown':direct_msg, 'toPersonId':person_id})
                if reply_msg != '':
                    yield self.application.settings['spark'].post_with_retries('https://webexapis.com/v1/messages', {'markdown':reply_msg, 'roomId':room_id})
                elif card_json != {}:
                    #print(json.dumps(card_json, indent=4))
                    yield self.application.settings['spark'].post_with_retries('https://webexapis.com/v1/messages', card_json)
                if command != None:
                    person_details = yield self.application.settings['spark'].get('https://webexapis.com/v1/people/{0}'.format(person_id))
                    self.application.settings['metrics_db'].insert(person_details.body.get('emails')[0], command, json.dumps(inputs))
            else:
                print("CardsHandler Secret does not match")
        except Exception as e:
            print("CardsHandler General Error:{0}".format(e))
            traceback.print_exc()


@tornado.gen.coroutine
def main():
    try:
        parse_command_line()
        app = tornado.web.Application(
            [
                (r"/", MainHandler),
                (r"/cards", CardsHandler),
                (r"/alive", AliveHandler),
                (r"/ready", AliveHandler),
                (r"/memberships", CustomMembershipsHandler),
            ],
            login_url="/login",
            cookie_secret="supercali;awjrioqjadosfragiledd1edfbg",
            xsrf_cookies=False,
            debug=options.debug,
            )
        app.settings['debug'] = options.debug
        app.settings['settings'] = Settings
        app.settings['spark'] = Spark(Settings.token)
        db = MongoController()
        app.settings['db'] = db
        ah = AppHelper(db)
        app.settings['app_helper'] = ah
        print(app.settings['db'].coll)
        print(app.settings['db'].count())
        app.settings['metrics_db'] = MetricsDB()
        app.settings['card_builder'] = CardBuilder()
        server = tornado.httpserver.HTTPServer(app)
        server.bind(Settings.port)  # port
        print("Serving... on port {0}".format(Settings.port))
        print("Debug: {0}".format(app.settings["debug"]))
        server.start()
        tornado.ioloop.IOLoop.instance().spawn_callback(ah.time_loop)
        tornado.ioloop.IOLoop.instance().start()
        print('Done')
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    main()
