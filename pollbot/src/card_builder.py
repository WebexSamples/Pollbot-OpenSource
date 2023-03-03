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
import inflect
import json

from pollbot.src.settings import Settings

class CardBuilder(object):
    def __init__(self):
        pass

    def duration_to_string(self, duration):
        units = duration
        mystr = "minutes"
        if duration > 60:
            units = duration / 60
            mystr = "hours"
            if units > 24:
                units = units / 24
                mystr = "days"
        return "{0} {1}".format(int(units), mystr)

    def invisible_item(self, id, value):
        return {
            "type": "Input.Text",
            "value": value,
            "isVisible": False,
            "spacing": "None",
            "id": id
        }

    def load_card(self, filepath):
        card_json = {}
        with open(filepath, "r", encoding='utf-8') as f:
            msg = f.read()
            card_json = json.loads(msg)
        return card_json

    def finalize_card_json(self, room_id, markdown, card_json, direct=False):
        card = {
                "markdown": markdown,
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": card_json
                    }
                ]
            }
        if direct:
            card.update({"toPersonId": room_id})
        else:
            card.update({"roomId": room_id})
        return card


    def build_active_help_card(self, poll, actor, room_id, room_type):
        card_json = self.load_card(Settings.help_active_card)
        send_to_id = room_id
        direct = False
        if room_type == "direct":
            send_to_id = actor
            direct = True
            container_template = card_json["body"][1]["items"].pop(0)
            new_templates = []
            for p in poll:
                new_template = copy.deepcopy(container_template)
                new_template["items"][0]["text"] = "You have an active poll in the space:"
                new_template["items"][1]["text"] = p.get('room_title')
                for action in new_template["items"][2]["actions"]:
                    action["data"].update({"room_id":p.get('room_id')})
                new_templates.append(new_template)
            print(new_templates)
            card_json["body"][1]["items"] = new_templates
        else:
            card_json["body"][1]["items"][0]["items"][1]["text"] = "; ".join(poll.get("question_order"))
            for action in card_json["body"][1]["items"][0]["items"][2]["actions"]:
                action["data"].update({"room_id":poll.get('room_id')})
        return self.finalize_card_json(send_to_id, "Adaptive Card - Active Help", card_json, direct)


    def build_setup_card(self, poll, room_title):
        card_json = self.load_card(Settings.setup_card)
        card_json["body"][1]["text"] = room_title
        question_containers = []
        container_template = card_json["body"][2]["items"].pop(0)
        separator = False
        for question in poll.get('questions'):
            new_container = copy.deepcopy(container_template)
            new_container["items"][1]["text"] = question
            answers = poll.get('questions').get(question).get('answer_order')
            new_container["items"][3]["text"] = "; ".join(answers)
            if separator:
                new_container.update({"separator":True})
            question_containers.append(new_container)
            separator = True
        card_json["body"][2]["items"] = question_containers
        card_json["body"][4]["text"] = "Ends in {0} (or when everyone votes)".format(self.duration_to_string(poll.get('duration')))
        card_json["body"][5]["text"] = "Results are {0}".format( "private" if poll.get('private') else "public" )
        card_json["body"][6]["columns"][0]["items"][0]["text"] = "{0} recipients".format(poll.get('max_responded_users'))
        card_json["body"][6]["columns"][1]["items"][0]["text"] = "{0}".format("(including you)" if poll.get('include_self') else "")
        if poll.get('anon') is False:
            card_json["body"][7]["text"] = "Answers are **not** anonymous"
        if poll.get('multi_answers'):
            card_json["body"][8]["text"] = "Multiple answers selectable per question"
        card_json["body"][9]["value"] = poll.get('room_id')
        return self.finalize_card_json(poll.get("creator_id"), "Adaptive Card - Question/Answer", card_json, True)

    def build_edited_setup_card(self, poll):
        card_json = self.load_card(Settings.setup_card)
        card_json["body"][0]["text"] = "Your poll's been updated 👍"
        card_json["body"][1]["text"] = "; ".join(poll.get('question_order'))
        card_json["body"][1].update({"weight": "Bolder", "isSubtle": True, "spacing": "Small"})
        card_json["body"][4]["text"] = "Ends in {0} (or when everyone votes)".format(self.duration_to_string(poll.get('duration')))
        card_json["body"][5]["text"] = "Results are {0}".format( "private" if poll.get('private') else "public" )
        card_json["body"][9]["value"] = poll.get('room_id')
        card_json["body"].pop(8)
        card_json["body"].pop(7)
        card_json["body"].pop(6)
        card_json["body"].pop(2)
        return self.finalize_card_json(poll.get("creator_id"), "Adaptive Card - Updated Setup", card_json, True)

    def build_answer_card(self, room_id, question, creator_name, private, multi_answers, anon):
        card_json = self.load_card(Settings.answer_card)
        card_json["body"][0]["text"] = question.question
        card_json["body"][1]["text"] += creator_name
        choices = []
        for answer in question.answers:
            choices.append({"title": answer, "value": answer})
        card_json["body"][2]["choices"] = choices
        card_json["body"][3]["value"] = question.question
        if multi_answers == 'true':
            card_json["body"][2]["isMultiSelect"] = True
        if anon != 'true':
            card_json["body"][4]["spacing"] = "Small"
            card_json["body"][4]["isVisible"] = True
        if private == 'true':
            card_json["body"][5]["actions"].pop(1)
        return self.finalize_card_json(room_id, "Adaptive Card - Question/Answer", card_json)

    def build_edit_card(self, send_to_id, current_poll):
        card_json = self.load_card(Settings.edit_card)
        options_json = self.load_card(Settings.additional_options_card)
        question = "; ".join(current_poll.get('question_order'))
        options_json["body"][1]["value"] = str(current_poll.get('duration'))
        options_json["body"][3]["value"] = str(current_poll.get('private')).lower()
        options_json["body"].pop(6)
        options_json["body"].pop(5)
        options_json["body"].pop(4)
        options_json["body"].pop(2)
        card_json["body"][1]['text'] = question
        card_json["body"][2]['items'] = options_json["body"]
        card_json["body"][3]['actions'][0]['data'].update({"room_id":current_poll.get('room_id')})
        return self.finalize_card_json(send_to_id, "Adaptive Card - Edit", card_json, True)

    def add_options_card(self, card_json, person_id, multi=False, duration=None, include_self=None, private=None, anon=None, multi_answers=None):
        options_json = self.load_card(Settings.additional_options_card_modified)
        if duration == None:
            options_json["body"][0]["items"][1]["value"] = str(Settings.default_duration)
        if multi:
            card_json["body"][3]["actions"].pop(1)
            if duration:
                options_json["body"][0]["items"][1]["value"] = duration
            if include_self:
                options_json["body"][0]["items"][2]["value"] = include_self
            if private:
                options_json["body"][0]["items"][3]["value"] = private
            if anon:
                options_json["body"][0]["items"][4]["value"] = anon
            if multi_answers:
                options_json["body"][0]["items"][5]["value"] = multi_answers
        else:
            options_json["body"][1]["actions"][0]["data"].update({"person_id":person_id})
            card_json["body"][3]["actions"][1] = options_json["body"][1]["actions"][0]

        card_json["body"].insert(3, options_json["body"][0])

    def build_question_card(self, room_id, room_type, person_id):
        card_json = self.load_card(Settings.create_card)
        if room_type != "direct":
            self.add_options_card(card_json, person_id)
            card_json["body"][4]["actions"][0]["data"].update({"person_id":person_id})
            #card_json["body"][3]["actions"][2]["data"].update({"person_id":person_id})
        else:
            container = card_json["body"][1]["items"]
            container[0]["text"] = "**Step 1: What do you want to ask?**"
            container[1]["text"] = "Enter your question and answer choices"
            actions = card_json["body"][3]["actions"]
            actions[0]["title"] = "Next: Select Recipients"
            actions[0]["data"] = {"submit":"next", "person_id":person_id}
            #actions[2]["data"] = {"submit":"cancel", "person_id":person_id}
            actions.pop(1)
        return self.finalize_card_json(room_id, "Adaptive Card - Create Poll", card_json)

    def build_question_card_step_2(self, room_id, person_id, question="", answers=""):
        card_json = self.load_card(Settings.create_card)
        container = card_json["body"][1]["items"]
        card_json["body"][3]["actions"][0]["data"].update({"person_id":person_id})
        container[0]["text"] = "**Step 2: Who will take this poll?**"
        container[1]["text"] = "Create a new space with a list of users"
        items = card_json["body"][2]["items"][0]["items"]
        items[0]["text"] = "Create new space with these users"
        new_input = copy.deepcopy(items[1])
        new_input["placeholder"] = "Separate email addresses with commas or semicolons"
        new_input["id"] = "users"
        items[3].update({"isVisible":False, "value":answers, "spacing":"None"})
        items[1].update({"isVisible":False, "value":question, "spacing":"None"})
        items.pop(2)
        items.insert(1, new_input)
        self.add_options_card(card_json, person_id)
        return self.finalize_card_json(room_id, "Adaptive Card - Create Poll", card_json)

    def build_multi_question_card(self, room_id, room_type, person_id, question=None, answers=None, users=None, duration=None, include_self=None, private=None, anon=None, multi_answers=None):
        card_json = self.load_card(Settings.create_card)
        text_obj = card_json["body"][0]
        text_obj["text"] = text_obj["text"].replace("a poll", "a multi-question poll")
        question_container = card_json["body"][2]["items"][0]
        new_questions = []
        p = inflect.engine()
        for i in range(1,4):
            print(i)
            new_container = copy.deepcopy(question_container)
            print(new_container)
            items = new_container["items"]
            items[0]["text"] = p.number_to_words(p.ordinal(i)).capitalize() + " Question"
            if i > 1:
                items[0]["text"] += " (Optional)"
                items[1]["placeholder"] = items[1]["placeholder"].replace("would", "else would")
                new_container["separator"] = True
            else:
                if question not in ["", None]:
                    items[1].update({"value":question})
                if answers not in ["", None]:
                    items[3].update({"value":answers})
            items[1]["id"] = "{0}{1}".format(items[1]["id"], i)
            items[3]["id"] = "{0}{1}".format(items[3]["id"], i)
            print(new_container)
            new_questions.append(new_container)
        if users != None:
            new_questions.append(self.invisible_item("users", users))
        print(new_questions)
        actions = card_json["body"][3]["actions"]
        actions[0]["data"] = {"submit":"create_multiple", "person_id":person_id}
        new_action = copy.deepcopy(actions[0])
        new_action["id"] = "cancelid"
        new_action["title"] = "Cancel"
        new_action["data"].update({"submit":"cancel"})
        actions.append(new_action)
        card_json["body"][2]["items"] = new_questions
        self.add_options_card(card_json, person_id, multi=True, duration=duration, include_self=include_self, private=private, anon=anon, multi_answers=multi_answers)
        return self.finalize_card_json(room_id, "Adaptive Card - Multiple Questions", card_json)

    def finalize_poll(self, current_poll):
        direct = True
        send_to_id = current_poll.get('creator_id')
        if not current_poll.get('private'):
            direct = False
            send_to_id = current_poll.get('room_id')
        return self.show_results(send_to_id, current_poll, direct, True)

    def show_results(self, send_to_id, current_poll, direct, is_final=False):
        card_json = self.load_card(Settings.results_card)
        new_body = []
        for question in current_poll.get("questions"):
            body = copy.deepcopy(card_json["body"][0])
            body['items'][0]["text"] = question
            if is_final:
                body['items'][1]["text"] = "The votes are in! And the winner is... 🥁"
            answer_template = body["items"].pop(2)
            first = True
            high_answer = None
            answers = current_poll.get("questions").get(question)
            answers.pop('responded_users')
            answers.pop('answer_order')
            anon = current_poll.get('anon')
            if anon:
                # if anonymous sort by vote count
                sorting_key = answers.get
            else:
                # is not anonymous sort by count of voters
                def sorting_key(k): return len(answers[k])
            for answer in sorted(answers, key=sorting_key, reverse=True):
                if anon is False:
                    answer_count = len(answers.get(answer))
                else:
                    answer_count = answers.get(answer)
                if high_answer == None:
                    high_answer = answer_count
                if answer_count == 0 or answer_count < high_answer:
                    first = False
                use_template = copy.deepcopy(answer_template)
                print(use_template)
                if first:
                    use_template['items'][0].update({"color": "Good", "weight": "Bolder"})
                use_template['items'][0]['text'] = answer
                plural = "s"
                if answer_count == 1:
                    plural = ""
                name_str = ""
                if anon is False:
                    name_str = ", ".join(answers.get(answer))
                    if name_str != "":
                        name_str = " - " + name_str
                num_string = "({0} vote{1}{2})".format(answer_count, plural, name_str)
                use_template['items'][1]['text'] = num_string
                body["items"].append(use_template)
            if len(new_body) > 0:
                body.update({"spacing":"Large", "separator":True})
            new_body.append(body)
        card_json["body"] = new_body
        return self.finalize_card_json(send_to_id, "Adaptive Card - Poll Results", card_json, direct)
