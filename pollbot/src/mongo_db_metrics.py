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
import re
import traceback
from bson.son import SON

from pymongo import MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError

from datetime import datetime, timedelta

try:
    from pollbot.src.metrics_settings import MetricsSettings
except Exception as e:
    from metrics_settings import MetricsSettings


class MetricsDB(object):
    def __init__(self):
        self.my_bot_id = MetricsSettings.metrics_bot_id
        self.client = MongoClient(MetricsSettings.mongo_db)
        self.db = self.client[MetricsSettings.db_name]
        self.metrics = self.db["metrics"]
        self.domains = self.db["domains"]
        self.bots = self.db["bots"]
        self.strformat = '%Y-%m-%d %H:%M:%S'

    def count(self, coll_name, query={}):
        return self.db[coll_name].count_documents(query)

    def find(self, args, coll_name):
        return self.db[coll_name].find(args)

    def find_one(self, args, coll_name):
        return self.db[coll_name].find_one(args)

    def getNextSequence(self):
        return self.db["counters"].find_and_modify(query= { '_id': "domain_id" },update= { '$inc': {'seq': 1}}, new=True ).get('seq');

    def get_search(self, term, coll_name, query):
        term = term.replace(" ", ".*")
        cdl= re.compile(".*{0}.*".format(term), re.IGNORECASE)
        docs = self.db[coll_name].find(query, sort=[("rating",1)])
        count_docs = self.db[coll_name].count_documents(query)
        return docs, count_docs

    def insert(self, personEmail, command, query=None):
        ret_val = False
        domain = personEmail
        try:
            try:
                user, domain = personEmail.split("@",1)
            except Exception as e:
                print("personEmail split exception in metrics framework:{0}".format(e))
            time_stamp = datetime.now()
            domain_res = self.domains.find_one({"name":domain})
            if domain_res != None:
                domainId = domain_res["id"]
            else:
                domainId = self.getNextSequence()
                self.domains.insert_one({"id":domainId, "name":domain})
            document = {"botId":self.my_bot_id,
                        "personEmail":personEmail,
                        "domainId":domainId,
                        "time_stamp":time_stamp,
                        "command":command,
                        "query": query}
            inserted = self.metrics.insert_one(document)
            ret_val = True
        except Exception as e:
            traceback.print_exc()
        return ret_val

    def get_bots(self):
        result = []
        try:
            result = list(self.bots.find({}))
        except Exception as e:
            traceback.print_exc()
        return result

    def get_all_unique_domains(self, _from=None, _to=None):
        if _from == None and _to == None:
            return list(self.domains.distinct('name'))
        elif _to == None:
            match = {"time_stamp": {
                    "$gte": datetime.strptime(_from, self.strformat)
                }}
        elif _from == None:
            match = {"time_stamp": {
                    "$lt": datetime.strptime(_to, self.strformat)
                }}
        else:
            match = {"time_stamp": {
                    "$gte": datetime.strptime(_from, self.strformat),
                    "$lt": datetime.strptime(_to, self.strformat)
                }}
        result = self.metrics.aggregate([
            {"$match": match},
            {"$lookup": {"from" : "domains",
                        "localField" : "domainId",
                        "foreignField" : "id",
                        "as" : "domainIds"}},
            {"$project": {"name": "$domainIds.name"}},
            {"$unwind": "$name"},
            {"$project": {"_id":0}},
            {"$group": {"_id": "$name"}},
          ])
        result = [val["_id"] for val in result]
        return result

    def get_all_unique_users(self, _from=None, _to=None):
        if _from == None and _to == None:
            match = {}
        elif _to == None:
            match = {"time_stamp": {
                    "$gte": datetime.strptime(_from, self.strformat)
                }}
        elif _from == None:
            match = {"time_stamp": {
                    "$lt": datetime.strptime(_to, self.strformat)
                }}
        else:
            match = {"time_stamp": {
                    "$gte": datetime.strptime(_from, self.strformat),
                    "$lt": datetime.strptime(_to, self.strformat)
                }}
        result = self.metrics.aggregate([
            {"$match": match},
            {"$project": {"email": "$personEmail"}},
            {"$unwind": "$email"},
            {"$project": {"_id":0}},
            {"$group": {"_id": "$email"}},
          ])
        result = [val["_id"] for val in result]
        return result

    def get_unique_domains_per_bot(self, botId, _from=None, _to=None):
        if _from == None and _to == None:
            match = {}
        elif _to == None:
            match = {"time_stamp": {
                    "$gte": datetime.strptime(_from, self.strformat)
                }}
        elif _from == None:
            match = {"time_stamp": {
                    "$lt": datetime.strptime(_to, self.strformat)
                }}
        else:
            match = {"time_stamp": {
                    "$gte": datetime.strptime(_from, self.strformat),
                    "$lt": datetime.strptime(_to, self.strformat)
                }}
        match.update({"botId":botId})
        result = self.metrics.aggregate([
            {"$match": match},
            {"$lookup": {"from" : "domains",
                        "localField" : "domainId",
                        "foreignField" : "id",
                        "as" : "domainIds"}},
            {"$project": {"name": "$domainIds.name"}},
            {"$unwind": "$name"},
            {"$project": {"_id":0}},
            {"$group": {"_id": "$name"}},
          ])
        result = [val["_id"] for val in result]
        return result

    def get_unique_users_per_bot(self, botId, _from=None, _to=None):
        if _from == None and _to == None:
            match = {}
        elif _to == None:
            match = {"time_stamp": {
                    "$gte": datetime.strptime(_from, self.strformat)
                }}
        elif _from == None:
            match = {"time_stamp": {
                    "$lt": datetime.strptime(_to, self.strformat)
                }}
        else:
            match = {"time_stamp": {
                    "$gte": datetime.strptime(_from, self.strformat),
                    "$lt": datetime.strptime(_to, self.strformat)
                }}
        match.update({"botId":botId})
        result = self.metrics.aggregate([
            {"$match": match},
            {"$project": {"email": "$personEmail"}},
            {"$unwind": "$email"},
            {"$project": {"_id":0}},
            {"$group": {"_id": "$email"}},
          ])
        result = [val["_id"] for val in result]
        return result

    def get_daily_active_users_per_bot(self, botId, _from=None, _to=None):
        if _from == None and _to == None:
            match = {}
        elif _to == None:
            match = {"time_stamp": {
                    "$gte": datetime.strptime(_from, self.strformat)
                }}
        elif _from == None:
            match = {"time_stamp": {
                    "$lt": datetime.strptime(_to, self.strformat)
                }}
        else:
            match = {"time_stamp": {
                    "$gte": datetime.strptime(_from, self.strformat),
                    "$lt": datetime.strptime(_to, self.strformat)
                }}
        match.update({"botId":botId})
        result = self.metrics.aggregate([
            {"$match": match},
            { '$group' : {
              '_id': { '$dateToString': { 'format': "%Y-%m-%d", 'date': "$time_stamp" } },
              'emails':{ '$addToSet': '$personEmail' }
           } },
           {"$addFields":{ 'emails':{'$size':'$emails'}}},
           {"$sort": {"_id":1}}
          ])
        return list(result)

    def get_daily_active_users(self, _from=None, _to=None):
        if _from == None and _to == None:
            match = {}
        elif _to == None:
            match = {"time_stamp": {
                    "$gte": datetime.strptime(_from, self.strformat)
                }}
        elif _from == None:
            match = {"time_stamp": {
                    "$lt": datetime.strptime(_to, self.strformat)
                }}
        else:
            match = {"time_stamp": {
                    "$gte": datetime.strptime(_from, self.strformat),
                    "$lt": datetime.strptime(_to, self.strformat)
                }}
        result = self.metrics.aggregate([
            {"$match": match},
            { '$group' : {
              '_id': { '$dateToString': { 'format': "%Y-%m-%d", 'date': "$time_stamp" } },
              'emails':{ '$addToSet': '$personEmail' }
           } },
           {"$addFields":{ 'emails':{'$size':'$emails'}}},
           {"$sort": {"_id":1}}
          ])
        return list(result)





if __name__ == "__main__":
    import time
    rdb = MetricsDB()
    #print(rdb.get_all_unique_domains())
    #print(rdb.get_all_unique_domains('2020-11-04 00:00:00', '2020-11-10 00:00:00'))
    #print(rdb.get_all_unique_domains2('2020-11-04 00:00:00', '2020-11-10 00:00:00'))
    #print(len(rdb.get_all_unique_domains()))
    #print(len(rdb.get_all_unique_domains('2020-11-06 00:00:00')))
    #print(len(rdb.get_all_unique_domains('2020-11-04 00:00:00', '2020-11-10 00:00:00')))

    #print(len(rdb.get_all_unique_users()))
    #print(len(rdb.get_all_unique_users('2020-11-06 00:00:00')))
    #print(len(rdb.get_all_unique_users('2020-11-04 00:00:00', '2020-11-10 00:00:00')))

    #print(rdb.get_daily_active_users())
    #print(rdb.get_daily_active_users('2020-11-04 00:00:00', '2020-11-10 00:00:00'))
    #print(rdb.get_daily_active_users('2020-11-04 00:00:00', '2020-11-10 00:00:00'))
    #print(len(rdb.get_daily_active_users()))
    #print(len(rdb.get_daily_active_users('2020-11-06 00:00:00')))
    #print(len(rdb.get_daily_active_users('2020-11-04 00:00:00', '2020-11-10 00:00:00')))

    for botId in [1,4,7]:
        print("botId:{0}".format(botId))
        print(rdb.get_unique_users_per_bot(botId))
        print(len(rdb.get_unique_users_per_bot(botId)))

        print(rdb.get_daily_active_users_per_bot(botId))
        print(len(rdb.get_daily_active_users_per_bot(botId)))

        print(rdb.get_unique_domains_per_bot(botId))
        print(len(rdb.get_unique_domains_per_bot(botId)))

        print(rdb.get_unique_users_per_bot(botId, '2020-11-06 00:00:00'))
        print(len(rdb.get_unique_users_per_bot(botId, '2020-11-06 00:00:00')))

        print(rdb.get_daily_active_users_per_bot(botId, '2020-11-06 00:00:00'))
        print(len(rdb.get_daily_active_users_per_bot(botId, '2020-11-06 00:00:00')))

        print(rdb.get_unique_domains_per_bot(botId, '2020-11-06 00:00:00'))
        print(len(rdb.get_unique_domains_per_bot(botId, '2020-11-06 00:00:00')))

        print(rdb.get_unique_users_per_bot(botId, '2020-11-04 00:00:00', '2020-11-10 00:00:00'))
        print(len(rdb.get_unique_users_per_bot(botId, '2020-11-04 00:00:00', '2020-11-10 00:00:00')))

        print(rdb.get_daily_active_users_per_bot(botId, '2020-11-04 00:00:00', '2020-11-10 00:00:00'))
        print(len(rdb.get_daily_active_users_per_bot(botId, '2020-11-04 00:00:00', '2020-11-10 00:00:00')))

        print(rdb.get_unique_domains_per_bot(botId, '2020-11-04 00:00:00', '2020-11-10 00:00:00'))
        print(len(rdb.get_unique_domains_per_bot(botId, '2020-11-04 00:00:00', '2020-11-10 00:00:00')))
