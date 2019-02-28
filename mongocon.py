import datetime
import json
import os

from dotenv import load_dotenv
from mongoengine import (connect, EmbeddedDocument, DateTimeField,
                         StringField, BooleanField, IntField, Document,
                         EmbeddedDocumentField, ListField)

load_dotenv('.env')


class Evaluation(EmbeddedDocument):
    school = StringField(required=True, max_length=100)
    meal = StringField(required=True, max_length=300)
    age = StringField(required=True, max_length=25)
    comment = StringField(required=False, max_length=300)
    satisfied = BooleanField(required=True)
    menu_date = DateTimeField(default=datetime.datetime.utcnow)


class FlowControl(EmbeddedDocument):
    flow_name = StringField(required=False, max_length=15)
    flow_step = IntField(required=False)
    school = StringField(required=False, max_length=100)
    age = StringField(required=False, max_length=25)
    menu_date = DateTimeField(default=datetime.datetime.utcnow)
    satisfied = BooleanField(required=False)
    evaluation = StringField(required=False, max_length=15)  # Bom, normal, muito bom, ruim...
    comment = StringField(required=False, max_length=300)
    meal = StringField(required=False, max_length=300)


class Notification(EmbeddedDocument):
    school = StringField(required=False, max_length=100)
    age = StringField(required=False, max_length=25)


class UserData(Document):
    platform = StringField(required=True, max_length=20)  # telegram | facebook
    platform_id = IntField(required=True)
    platform_alias = StringField(required=False, max_length=20)  # ex @fulano no telegram
    name = StringField(required=True, max_length=20)
    last_name = StringField(required=False, max_length=20)
    flow_control = EmbeddedDocumentField(FlowControl)
    notification = EmbeddedDocumentField(Notification, required=False)
    evaluations = ListField(EmbeddedDocumentField(Evaluation))


class BotDbConnection(object):
    connect(host=os.environ.get('MONGO_HOST'))

    def __init__(self, platform_id, platform, **kwargs):
        self.platform_id = platform_id
        self.platform = platform
        self.user_data = self._get_of_create_user(**kwargs)

    def update_flow_control(self, **kwargs):
        user = self._get_user()
        if user:
            flow_control = FlowControl(flow_name=kwargs.get('flow_name', None),
                                       flow_step=kwargs.get('flow_name', None),
                                       school=kwargs.get('school', None),
                                       age=kwargs.get('age', None),
                                       menu_date=kwargs.get('menu_date', None),
                                       satisfied=kwargs.get('satisfied', None),
                                       evaluation=kwargs.get('evaluation', None),
                                       comment=kwargs.get('comment', None),
                                       meal=kwargs.get('meal', None))
            user.flow_control = flow_control
            user.save()
        return user

    def clean_flow_control_data(self):
        user = self._get_user()
        if user:
            user.flow_control = None
            user.save()
        return user

    def save_notification(self):
        user = self._get_user()
        if user:
            user.notification = Notification(school=user.flow_control.school,
                                             age=user.flow_control.age)
            user.save()
        return user

    def save_evaluation(self):
        user = self._get_user()
        if user:
            evaluation = Evaluation(school=user.flow_control.school,
                                    meal=user.flow_control.school,
                                    age=user.flow_control.age,
                                    comment=user.flow_control.comment,
                                    satisfied=user.flow_control.satisfied,
                                    menu_date=user.flow_control.menu_date)
            user.evaluations.append(evaluation)
            user.save()
        return user

    def to_dict(self):
        return json.loads(self.user_data.to_json())

    #
    # Private
    #

    def _get_of_create_user(self, **kwargs):
        user = self._get_user()
        if not user:
            user = self._create_user(self.platform_id, self.platform, **kwargs)
        return user

    def _get_user(self):
        """returns user object or None"""
        users = UserData.objects.filter(platform_id=self.platform_id, platform=self.platform)
        if users:
            assert len(users) == 1
            return users[0]

    def _create_user(self, platform_id, platform, **kwargs):
        assert platform in ['facebook', 'telegram']
        user = self._get_user()
        if not user:
            user = UserData(platform_id=platform_id,
                            platform=platform,
                            name=kwargs.get('name', None),
                            platform_alias=kwargs.get('platform_alias', None),
                            last_name=kwargs.get('name', None))
            user.save()
        return user

    def __repr__(self):
        return self.user_data.to_json()


if __name__ == '__main__':
    g = BotDbConnection(564654, 'facebook', name='asdasd', fulano='asdasda')
    g.update_flow_control(age='55555555555555')
    g.save_evaluation()
    print(g)
