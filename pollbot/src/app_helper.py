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
import time
import tornado.gen
import traceback

from datetime import datetime, timedelta
from threading import Timer

from pollbot.src.card_builder import CardBuilder
from pollbot.src.settings import Settings

from pollbot.src.spark import Spark

from tornado.httpclient import HTTPError


class AppHelper(object):
    def __init__(self, db):
        self.db = db
        self.active_events = {}
        self.spark = Spark(Settings.token)
        self.card_builder = CardBuilder()
        self.lock = False

    def schedule_event(self, difference, item):
        print("Difference:{0}".format(difference))
        if difference < 3600 and difference > 0:
            print("Creating Event timer: {0}".format(item.get('room_id')))
            event = Timer(difference, self.close_dead, args=[item])
            event.daemon = True
            event.start()
            self.active_events.update({item.get('room_id'):event})
        else:
            print("Not creating Event timer yet, too far away.")

    @tornado.gen.coroutine
    def delete_poll(self, current_poll):
        msg = ""
        for card in current_poll.get('cards'):
            try:
                yield self.spark.delete('https://webexapis.com/v1/messages/{0}'.format(card))
            except HTTPError as he:
                print(he)
                print("(this is probably okay) failed to delete card for poll created by {0}".format(current_poll.get('creator_name')))
        room_id = current_poll.get('room_id')
        deleted = self.db.delete_one({"room_id":room_id})
        if deleted <= 0:
            msg = "There was an error stopping this poll.  \n"
        raise tornado.gen.Return(msg)

    @tornado.gen.coroutine
    def close_dead(self, poll, all_answered=False):
        print("close_dead poll:{0}".format(poll))
        poll = self.db.find_one({"room_id":poll["room_id"]})
        card_json = self.card_builder.finalize_poll(poll)
        #print(json.dumps(card_json, indent=4))
        try:
            yield self.spark.post_with_retries('https://webexapis.com/v1/messages', card_json)
        except HTTPError as he:
            if he.code == 404:
                msg = "A poll has ended, but it appears the bot was removed from the space before the poll was finalized.  \n"
                msg_obj = {"markdown": msg, "toPersonId":poll.get("creator_id")}
                yield self.spark.post_with_retries('https://webexapis.com/v1/messages', msg_obj)
        try:
            self.active_events.pop(poll.get('room_id'))
        except KeyError as ke:
            print("EntryID: {0} must already be deleted.".format(ke))
        delete_msg = yield self.delete_poll(poll)
        print("close_dead delete_msg: {0}".format(delete_msg))
        if delete_msg == "":
            print("poll deleted: {0}".format(poll.get('room_id')))
            if poll.get('private'):
                if all_answered:
                    msg = "All participants have completed the poll."
                else:
                    msg = "The poll has now ended."
                msg += " Results have been sent to the poll creator.  \n"
                msg_obj = {"markdown": msg, "roomId":poll.get("room_id")}
                yield self.spark.post_with_retries('https://webexapis.com/v1/messages', msg_obj)


    @tornado.gen.coroutine
    def poll_check(self, room_id=None):
        while self.lock:
            print("app_helper is locked - delaying time_loop for 2 seconds")
            yield tornado.gen.sleep(2)
        self.lock = True
        try:
            now = datetime.now()
            print("Get old/ended polls: {0}".format(now.strftime("%Y-%m-%d %H:%M:%S")))
            query = {"end_date":{"$lte":now}}
            if room_id != None:
                event = self.active_events.get(room_id)
                if event != None:
                    print("cancelling event for room_id: {0}".format(room_id))
                    event.cancel()
                    self.active_events.pop(room_id)
                query.update({"room_id":room_id})
            results = self.db.find(query)
            counter = 0
            for item in results:
                missed_event = Timer(counter, self.close_dead, args=[item])
                missed_event.daemon = True
                missed_event.start()
                counter += 0.5
                print(counter)
            t = now + timedelta(hours=1)
            query.update({"end_date":{"$lte":t}})
            print("Get polls ending soon (+1 hour): {0}".format(t.strftime("%Y-%m-%d %H:%M:%S")))
            results = self.db.find(query)
            for item in results:
                print(item)
                if item.get('room_id') not in self.active_events:
                    difference = (item.get('end_date') - now).total_seconds()
                    self.schedule_event(difference, item)
                else:
                    print("EventId:{0} is already in the active events!".format(item.get('room_id')))
        except Exception as ex:
            traceback.print_exc()
        self.lock = False

    @tornado.gen.coroutine
    def time_loop(self):
        while True:
            yield self.poll_check()
            yield tornado.gen.sleep(Settings.time_loop_sleep_seconds)
