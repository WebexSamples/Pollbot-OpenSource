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
import copy
import traceback

from pymongo import MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError

from datetime import datetime, timedelta

from pollbot.src.settings import Settings


class MongoController(object):
    def __init__(self):
        self.client = MongoClient(Settings.mongo_db)
        self.db = self.client[Settings.db_name]
        self.coll = self.db[Settings.collection_name]

    def count(self):
        return self.coll.estimated_document_count()

    def find(self, args):
        return self.coll.find(args)

    def find_one(self, args):
        return self.unescape(self.coll.find_one(args))

    def sanitize(self, mystr):
        return mystr.replace("~", "~e").replace(".", "~p").replace("$", "~d")

    def desanitize(self, mystr):
        return mystr.replace("~d", "$").replace("~p", ".").replace("~e", "~")

    def escape(self, document):
        document = copy.deepcopy(document)
        for q in dict(document['questions']):
            old_doc = document["questions"].pop(q)
            new_q = self.sanitize(q)
            for a in dict(old_doc):
                old_a = old_doc.pop(a)
                new_a = self.sanitize(a)
                old_doc.update({new_a:old_a})
            document['questions'].update({new_q: old_doc})
        return document

    def unescape(self, document):
        if document != None:
            for q in dict(document['questions']):
                old_doc = document["questions"].pop(q)
                new_q = self.desanitize(q)
                for a in dict(old_doc):
                    old_a = old_doc.pop(a)
                    new_a = self.desanitize(a)
                    old_doc.update({new_a:old_a})
                document['questions'].update({new_q: old_doc})
        return document

    def insert(self, room_id, person_id, creator_name, questions, inputs, num_users):
        result = None
        try:
            include_self = inputs.get('include_self')
            private      = inputs.get('private')
            duration     = int(inputs.get('duration'))
            anon         = inputs.get('anon')
            multi_answers= inputs.get('multi_answers')
            document = {
                        "room_id":room_id,
                        "creator_id":person_id,
                        "max_responded_users":num_users,
                        "creator_name":creator_name.strip(),
                        "questions":{},
                        "question_order":[q.question for q in questions],
                        "private": private == "true",
                        "include_self" : include_self == "true",
                        "anon" : anon == "true",
                        "multi_answers" : multi_answers == "true",
                        "end_date" : datetime.now() + timedelta(minutes=duration),
                        "duration" : duration,
                        "cards" : []
            }
            for question in questions:
                a_doc = {"responded_users": {}, "answer_order":question.answers}
                if not document['anon']:
                    for answer in question.answers:
                        a_doc.update({answer:[]})
                else:
                    for answer in question.answers:
                        a_doc.update({answer:0})
                document["questions"].update({question.question:a_doc})
            inserted = self.coll.insert_one(self.escape(document))
            if inserted.acknowledged:
                result = document
        except DuplicateKeyError as dke:
            print("room_id already exists in Collection")
        return result

    def update(self, room_id, person_id, question, answers, anon, person_name, responded_users_type, prev_vote):
        question = self.sanitize(question)
        query = {"room_id":room_id}
        responded_users = "questions.{0}.responded_users".format(question)
        if responded_users_type == list:#this is to support an older version.  Can probably default to else in the future.
            update = { "$addToSet" : { responded_users : person_id }, "$inc": {} }
        else:
            update = { "$set" : { responded_users+"."+person_id: answers }, "$inc": {} }
        if anon is False:
            update.pop("$inc")
            update.update({"$push": {} })
            update.update({"$pull": {} })
        for answer in answers:
            if answer in prev_vote:
                prev_vote.remove(answer)
                continue
            answer = self.sanitize(answer)
            choice = "questions.{0}.{1}".format(question, answer)
            if anon is False:
                update["$push"].update({choice: person_name})
            else:
                update["$inc"].update({choice:1})
        for answer in prev_vote:
            answer = self.sanitize(answer)
            choice = "questions.{0}.{1}".format(question, answer)
            if anon is False:
                update["$pull"].update({choice: person_name})
            else:
                update["$inc"].update({choice:-1})
        if "$pull" in update and len(update["$pull"]) == 0:
            update.pop("$pull")
        if "$push" in update and len(update["$push"]) == 0:
            update.pop("$push")
        result = self.coll.find_one_and_update(query, update, return_document=ReturnDocument.AFTER)
        return result

    def update_privacy(self, room_id, private):
        query = {"room_id":room_id}
        update = {"$set" : { "private" : private } }
        result = self.coll.find_one_and_update(query, update, return_document=ReturnDocument.AFTER)
        print("mongo_db_controller update_privacy result:{0}".format(result))
        msg = ""
        if result == None:
            msg = "There is currently no active poll in this space.  \n"
        else:
            msg = "Poll results are {0}.  \n".format("private" if result.get('private') else "public")
        return msg

    def update_duration(self, room_id, duration):
        query = {"room_id":room_id}
        poll = self.coll.find_one(query)
        old_duration = poll.get('duration')
        old_date = poll.get('end_date')
        new_date = poll.get('end_date') - timedelta(minutes=old_duration) + timedelta(minutes=int(duration))
        update = {"$set" : { "duration" : int(duration), "end_date" : new_date} }
        result = self.coll.find_one_and_update(query, update, return_document=ReturnDocument.AFTER)
        print("mongo_db_controller update_duration result:{0}".format(result))
        msg = ""
        if result == None:
            msg = "There is currently no active poll in this space.  \n"
        else:
            msg = "Duration is now {0} minutes. Updated end date is now {1}  \n".format(result.get('duration'), result.get('end_date'))
        return msg

    def update_details(self, room_id, private, duration):
        query = {"room_id":room_id}
        poll = self.coll.find_one(query)
        old_duration = poll.get('duration')
        old_date = poll.get('end_date')
        new_date = poll.get('end_date') - timedelta(minutes=old_duration) + timedelta(minutes=int(duration))
        update = {"$set" : { "private" : private, "duration" : int(duration), "end_date" : new_date} }
        result = self.coll.find_one_and_update(query, update, return_document=ReturnDocument.AFTER)
        print("mongo_db_controller update_duration result:{0}".format(result))
        return result

    def add_card(self, room_id, message_id):
        query = {"room_id":room_id}
        update = { "$addToSet" : { "cards" : message_id } }
        result = self.coll.update_one(query, update)
        print("mongo_db_controller add_card result:{0}".format(result))

    def delete_one(self, query):
        deleted_count = 0
        try:
            x = self.coll.delete_one(query)
            deleted_count = x.deleted_count
        except Exception as e:
            traceback.print_exc()
        return deleted_count
