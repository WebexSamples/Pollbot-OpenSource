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
import re
import traceback

import tornado.gen
import tornado.web

from tornado.httpclient import HTTPError

from pollbot.src.settings import Settings

from pollbot.src.memberships import MembershipsHandler

class Question(object):
    def __init__(self, question, answers):
        self.question = question
        self.answers = []
        answers = answers.split(';')
        for a in answers:
            if a.strip() != "":
                self.answers.append(a.strip())
        seen = set()
        seen_add = seen.add
        self.answers = [x for x in self.answers if not (x in seen or seen_add(x))] #remove duplicate answers, preserve order

class BaseHandler(tornado.web.RequestHandler):
    def help_msg(self):
        msg = ">**Create a Poll with Buttons and Cards**  \n>*The best way for most users to create a poll.*  \n"
        msg += ">**Command** - **PollBot** `create poll`  \n  \n"
        msg += ">**Get Help**  \n>*The appropriate help card will be displayed for the space. This is the best way for most users to get started.*  \n"
        msg += ">**Command** - **PollBot** `help`  \n  \n"
        msg += ">**Get Help with Typed Commands**  \n>*Display this message.*  \n"
        msg += ">**Command** - **PollBot** `help typed`  \n  \n"
        msg += ">**Get Poll Status**  \n>*Display the results of the current poll. This command will only be successful in group spaces, and its reply will always be sent as a direct message.*  \n"
        msg += ">**Command** - **PollBot** `status`  \n  \n"
        msg += ">**Stop a Poll**  \n>*Stops the active poll in this space. This command will only be successful in group spaces.*  \n"
        msg += ">**Command** - **PollBot** `stop`  \n  \n"
        msg += "For users that prefer to create a poll through text based commands, please see below:  \n"
        msg += "*Keywords should be separated by* `|`  \n  \n"
        msg += "Simple Format:  \n"
        msg += "**PollBot** `create {QUESTION} : {ANSWER}; {ANSWER}; {ANSWER...}`  \n  \n"
        msg += "Full Format:  \n"
        msg += "**PollBot** `create {QUESTION} : {ANSWER}; {ANSWER}; {ANSWER...} | duration {MINUTES} | users {EMAIL}, {EMAIL}, {EMAIL...} | {PUBLIC} | {ANONYMITY} | {MULTIANSWER}`  \n  \n"
        msg += "Multi-Question Format:  \n"
        msg += "**PollBot** `create {QUESTION} : {ANSWER}; {ANSWER}; {ANSWER...} | create {QUESTION} : {ANSWER}, {ANSWER}, {ANSWER...}`  \n  \n"
        msg += "Example 1:  \n"
        msg += "*This example creates a private (default) poll with a duration of 8 hours (default) for all users in the current space.*  \n"
        msg += "*Only one answer can be selected per question (default) and answers for this poll are anonymous (default).*  \n"
        msg += "**PollBot** `create What's for lunch? : Burgers; Pizza; Tacos`  \n  \n"
        msg += "Example 2:  \n"
        msg += "*This example creates a poll with a duration of 60 minutes in a new space based on the list of users. The results will be shared in that space (public).*  \n"
        msg += "**PollBot** `create What's for lunch? : Burgers; Pizza; Tacos | duration 60 | users persona@example.com, personb@example.com | public`  \n  \n"
        msg += "Example 3:  \n"
        msg += "*This example creates a poll with a duration of 120 minutes for all users in the current space. The results will be private (default, shared only with the creator), "
        msg += "but the answers will not be anonymous, and multiple answers will be selectable per question.*  \n"
        msg += "**PollBot** `create What's for lunch? : Burgers; Pizza; Tacos | duration 120 | not anonymous | multi-answer`  \n  \n"
        msg += "**Duration:**  \n"
        msg += "The default poll duration is 3 days (4320 minutes); however if provided, the duration must always be represented as an integer number of minutes.  \n  \n"
        msg += ">**Edit Duration**  \n>*You can edit the duration of a poll after its creation by using the duration command by itself. *  \n"
        msg += ">**Command** - **PollBot** `duration 180`  \n  \n"
        msg += "**Please Note:**  \n"
        msg += "Editing the duration does not alter or reset the start time, so it is possible to end the poll immediately if lowering the duration.  \n"
        msg += "**Please Note:**  \n"
        msg += "If including the `users` command, Pollbot will create a new group space with the provided list of users.  \n"
        msg += "Pollbot now always allows every user in a space to answer the poll.  \n"
        msg += ">**Set Private [default]**  \n>*Final results will only be provided to the poll creator, and current status cannot be retrieved by poll particpants.*  \n"
        msg += ">**Command** - **PollBot** `private`  \n  \n"
        msg += ">**Set Public**  \n>*Final results will be shared with all participating users, and current status can be retrievd by poll particpants.*  \n"
        msg += ">**Command** - **PollBot** `public`  \n  \n"
        msg += "**Please Note:**  \n"
        msg += "As of the latest pollbot update, a poll must be mostly created in a single command if using text based/typed commands.  \n"
        msg += "**Once a poll has been created, the `{QUESTION}`, `{ANSWER}s`, user `{EMAIL}`s, `{ANONYMITY}`, and `{MULTIANSWER}` cannot be modified.**  \n"
        return msg


    @tornado.gen.coroutine
    def help(self, actor, room_id, room_type):
        markdown = "Adaptive Card - Help"
        poll = None
        if room_type == "direct":
            poll = self.application.settings['db'].find({"creator_id":actor})
            if poll.count() == 0:
                poll = None
            else:
                polls = []
                for p in poll:
                    room_details = yield self.application.settings['spark'].get_with_retries_v2('https://webexapis.com/v1/rooms/{0}'.format(p.get('room_id')))
                    room_title = room_details.body.get('title')
                    p.update({"room_title":room_title})
                    polls.append(p)
                poll = polls
        else:
            poll = self.application.settings['db'].find_one({"room_id":room_id})
        if poll != None:
            card_json = self.application.settings['card_builder'].build_active_help_card(poll, actor, room_id, room_type)
            resp = yield self.send_and_reset_card_json(card_json, False)
            message_id = resp.body.get('id')
            self.application.settings['db'].add_card(room_id, message_id)
            raise tornado.gen.Return({})
        elif room_type == "direct":
            raise tornado.gen.Return(self.send_card(Settings.help_direct_card, actor, markdown, True))
        else:
            raise tornado.gen.Return(self.send_card(Settings.help_group_card, room_id, markdown))

    @tornado.gen.coroutine
    def get_num_users(self, room_id, include_self):
        num_users = 0
        url = 'https://webexapis.com/v1/memberships?roomId={0}&max=251'.format(room_id)
        while url != None and num_users < 500:
            memberships = yield self.application.settings['spark'].get_with_retries_v2(url)
            for item in memberships.body.get('items', []):
                if not "@webex.bot" in item.get('personEmail') and not "@sparkbot.io" in item.get('personEmail'):
                    num_users += 1
            print("get_num_users: {0}".format(num_users))
            url = memberships.headers.get('Link')
            if url != None:
                url = url.split(">;")[0]
                url = url[1:]
        if include_self != 'true':
            if num_users > 0:
                print('get_num_users subtracting one user for self')
                num_users -= 1
        if num_users > 500:
            num_users = 500
        raise tornado.gen.Return(num_users)

    @tornado.gen.coroutine
    def delete_message(self, message_id):
        yield self.application.settings['spark'].delete('https://webexapis.com/v1/messages/{0}'.format(message_id))

    @tornado.gen.coroutine
    def stop_poll(self, actor, room_id, from_card=False):
        current_poll = self.get_current_poll(room_id)
        msg = self.stop_poll_permission(actor, current_poll)
        try:
            if msg == "":
                card_json = self.application.settings['card_builder'].finalize_poll(current_poll)
                card_json = yield self.send_and_reset_card_json(card_json)
                msg = yield self.application.settings['app_helper'].delete_poll(current_poll)
                if msg == "":
                    if from_card:
                        if not current_poll.get('private'):
                            msg = "The poll has been stopped. Results have been sent to the space.  \n"
                        else:
                            markdown_obj = {"roomId": room_id, "markdown": "The poll has been manually stopped. Results have been sent to the poll creator.  \n"}
                            yield self.application.settings['spark'].post_with_retries('https://webexapis.com/v1/messages', markdown_obj)
                    elif current_poll.get('private'):
                        msg = "The poll has been stopped. Results have been sent to the poll creator.  \n"
        except HTTPError as he:
            if he.code == 404:
                msg = "It appears the bot is no longer in the space.  \n"
        raise tornado.gen.Return(msg)

    def stop_poll_permission(self, creator_id, current_poll):
        msg = ""
        if current_poll:
            if current_poll.get('creator_id') != creator_id:
                msg = "Only the creator can stop this poll.  \n"
        else:
            msg = "There is no active poll in this space.  \n"
        return msg

    def edit_poll_permission(self, creator_id, current_poll):
        msg = ""
        if current_poll:
            if current_poll.get('creator_id') != creator_id:
                msg = "Only the creator can edit this poll.  \n"
        else:
            msg = "There is no active poll in this space.  \n"
        return msg

    @tornado.gen.coroutine
    def create_poll_space(self, person_id, user_list, creator_name, first_question):
        msg_obj = {"title":'"{0}" - poll created by {1}'.format(first_question, creator_name)}
        result = yield self.application.settings['spark'].post_with_retries('https://webexapis.com/v1/rooms', msg_obj)
        room_id = result.body.get('id')
        membership_obj = {"roomId":room_id, "personId":person_id}
        yield self.application.settings['spark'].post_with_retries('https://webexapis.com/v1/memberships', membership_obj)
        failed_users = []
        for user in user_list:
            user = user.strip()
            if user != "":
                membership_obj = {"roomId":room_id, "personEmail":user}
                try:
                    yield self.application.settings['spark'].post_with_retries('https://webexapis.com/v1/memberships', membership_obj)
                except HTTPError as he:
                    if he.code == 409:
                        print("409: {0}".format(user))#user probably tried to add themself or same user twice.
                    else:
                        failed_users.append(user)
        if len(failed_users) > 0:
            msg = "Unfortunately, I was not able to add these users to the poll space: {0}".format(", ".join(failed_users))
            yield self.application.settings['spark'].post_with_retries('https://webexapis.com/v1/messages', {"toPersonId":person_id, "markdown":msg})
        raise tornado.gen.Return(room_id)

    @tornado.gen.coroutine
    def create_poll(self, room_id, person_id, questions, users, inputs):
        msg = ''
        user_list = []
        print("users:{0}".format(users))
        if users:
            user_list = re.split(",|;", users)
        creator = yield self.application.settings['spark'].get_with_retries_v2('https://webexapis.com/v1/people/{0}'.format(person_id))
        creator_name = creator.body.get("displayName")
        if len(user_list) > 0:
            room_id = yield self.create_poll_space(person_id, user_list, creator_name, questions[0].question)
        attachments = []
        exists = self.application.settings['db'].find_one({"room_id":room_id})
        if exists != None:
            msg += "An active poll created by {0} already exists for this space.  \n".format(exists.get('creator_name'))
        else:
            num_users = yield self.get_num_users(room_id, inputs.get('include_self'))
            if num_users == 0:
                msg = "Error - No users were added, or I was unable to retrieve the memberships of this room. "
                msg += "The poll was not created.  \n"
            else:
                result = self.application.settings['db'].insert(room_id, person_id, creator_name, questions, inputs, num_users)
                for question in questions:
                    card_json = self.application.settings['card_builder'].build_answer_card(room_id, question, creator_name, inputs.get('private', 'true'), inputs.get('multi_answers'), inputs.get('anon'))
                    yield self.send_and_add_card(card_json, room_id)
                room_details = yield self.application.settings['spark'].get_with_retries_v2('https://webexapis.com/v1/rooms/{0}'.format(room_id))
                room_title = room_details.body.get('title')
                card_json = self.application.settings['card_builder'].build_setup_card(result, room_title)
                yield self.application.settings['app_helper'].poll_check(room_id)
                yield self.send_and_add_card(card_json, room_id)
        raise tornado.gen.Return(msg)

    def build_typed_create(self, in_message):
        msg = ""
        sections = in_message.split("|")
        questions = []
        users = ""
        inputs = {"private": "true", "duration": Settings.default_duration, "include_self": "true", "anon": "true", "multi_answers": False}
        for sect in sections:
            sect = sect.strip()
            if sect.lower().startswith("create"):
                create = sect[6:].strip()
                try:
                    question, answers = create.split(":")
                    question_obj = Question(question.strip(), answers.strip())
                    if len(question_obj.answers) <= 1:
                        msg += "Question must have more than one unique answer (separate answers with semicolons).  \n"
                    else:
                        questions.append(question_obj)
                except ValueError as ve:
                    msg += "`create` question and answers were not properly formatted.  \n"
            elif sect.lower().startswith("users"):
                users = sect[5:].strip()
            elif sect.lower().startswith("duration"):
                duration = sect[8:].strip()
                try:
                    inputs["duration"] = int(duration)
                except Exception as e:
                    msg += "`duration` must be an integer value.  \n"
            elif sect.lower() == "public":
                inputs["private"] = False
            elif sect.lower() in ['not anonymous', 'non anonymous', 'anon false', 'anonymous false', 'non anon']:
                inputs["anon"] = False
            elif sect.lower() in ['multi answer', 'multi-answer', 'multi answers', 'multiple answers', 'multi-answers']:
                inputs["multi_answers"] = "true"
        return questions, users, inputs, msg

    @tornado.gen.coroutine
    def track_answer(self, room_id, person_id, inputs):
        msg = ""
        print(inputs)
        responded_users = "questions.{0}.responded_users".format(inputs["question"])
        result = self.application.settings['db'].find_one({"room_id":room_id})
        print(result)
        responded_users_obj = result["questions"][inputs["question"]]['responded_users']
        if not person_id in responded_users_obj or type(responded_users_obj) == dict:
            if person_id == result.get('creator_id') and not result.get('include_self'):
                msg = "Sorry, you chose to exclude yourself from this poll when the poll was created.  \n"
            else:
                if inputs.get('choice') != None:
                    choice = inputs['choice']
                    if result.get('multi_answers'):
                        len_answers = sorted(result["questions"][inputs["question"]]['answer_order'], key=len, reverse=True)
                        print("len_answers:{0}".format(len_answers))
                        choices = []
                        for answer in len_answers:
                            if answer in choice:
                                choice = choice.replace(answer,"")
                                choices.append(answer)
                    else:
                        choices = [choice]
                    print("choices:{0}".format(choices))
                    try:
                        already_voted = responded_users_obj.get(person_id, [])
                    except AttributeError as ae:
                        already_voted = []
                    if already_voted == choices:
                        msg = "You already voted for this selection. You may not vote more than once for the same answer."
                    else:
                        if len(already_voted) > 0:
                            msg = "You changed your answer to: **{0}**".format(", ".join(choices))
                        person_name = ""
                        if result.get('anon') is False:
                            person = yield self.application.settings['spark'].get_with_retries_v2('https://webexapis.com/v1/people/{0}'.format(person_id))
                            person_name = person.body.get("displayName","").split(" ",1)[0]
                        poll = self.application.settings['db'].update(room_id, person_id, inputs['question'], choices, result.get('anon'), person_name, type(result["questions"][inputs["question"]]['responded_users']), already_voted)
                        all_responded = True
                        for question in poll.get('questions'):
                            num_users = len(poll.get('questions')[question].get('responded_users'))
                            if num_users != poll.get('max_responded_users'):
                                all_responded = False
                                break
                        if all_responded:
                            self.application.settings['app_helper'].close_dead(poll, all_responded)
                else:
                    msg = 'Sorry, I didn\'t catch your response to "{0}"'.format(inputs["question"])
        else:
            msg = "Sorry, you already sent in your answer. No take-backs."
        raise tornado.gen.Return(msg)


    def get_current_poll(self, room_id):
        return self.application.settings['db'].find_one({"room_id":room_id})

    def get_result_permission(self, room_id, person_id, current_poll):
        msg = ""
        if current_poll != None:
            if current_poll.get('private') and person_id != current_poll.get("creator_id"):
                msg = "This poll's results are private. If you'd like to see the results ask {0}.  \n".format(current_poll.get('creator_name'))
        else:
            msg = "There is currently no active poll in this space.  \n"
        return msg


    def add_attachment(self, card_json):
        return {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": card_json
        }

    @tornado.gen.coroutine
    def send_and_add_card(self, card_json, room_id):
        #print(json.dumps(card_json, indent=4))
        resp = yield self.application.settings['spark'].post_with_retries('https://webexapis.com/v1/messages', card_json)
        message_id = resp.body.get('id')
        self.application.settings['db'].add_card(room_id, message_id)

    @tornado.gen.coroutine
    def send_and_reset_card_json(self, card_json, reset=True):
        #print(json.dumps(card_json, indent=4))
        resp = yield self.application.settings['spark'].post_with_retries('https://webexapis.com/v1/messages', card_json)
        if reset:
            raise tornado.gen.Return({})
        else:
            raise tornado.gen.Return(resp)

    def send_card(self, filepath, room_id, markdown, direct=False):
        card_json = self.application.settings['card_builder'].load_card(filepath)
        return self.application.settings['card_builder'].finalize_card_json(room_id, markdown, card_json, direct)


class CustomMembershipsHandler(MembershipsHandler, BaseHandler):

    @tornado.gen.coroutine
    def intro_msg(self, event):
        if event['data']['roomType'] == "group":
            card_json = yield self.help(event['actorId'], event['data']['roomId'], event['data']['roomType'])
            yield self.send_and_reset_card_json(card_json)
