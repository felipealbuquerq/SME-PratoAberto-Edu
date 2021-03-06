import json
import os
import urllib

import requests

from chatbots.base import BaseBot
from chatbots.model.bot_model import BotDbConnection
from .utils import edu_logger


class TelegramNotification(object):
    def __init__(self, user_data):
        TG_URL = 'https://api.telegram.org/bot{}/'.format(os.environ.get('TG_TOKEN'))
        self.TG_BASE_MESSAGE_URL = TG_URL + 'sendMessage?chat_id={}&text={}&parse_mode=Markdown'
        self.chat_id = user_data.platform_id

    def send_notification_message(self, text):
        """
        :param text:
        :return:
        """
        text = urllib.parse.quote_plus(text)
        url = self.TG_BASE_MESSAGE_URL.format(self.chat_id, text)
        r = requests.get(url)
        edu_logger.debug('telegram send_notification_message: {}'.format(url))
        edu_logger.debug('return: {}-{}'.format(r.status_code, r.text))


class TelegramBot(BaseBot):
    """
        Handle data related to telegram.
        It doesnt handle states
    """

    def __init__(self, payload):
        super().__init__(payload)
        TG_URL = 'https://api.telegram.org/bot{}/'.format(os.environ.get('TG_TOKEN'))
        self.TG_BASE_MESSAGE_URL = TG_URL + 'sendMessage?chat_id={}&text={}&parse_mode=Markdown'
        chat_data = payload['message']['chat']
        self.chat_id = chat_data['id']
        self.text = payload['message']['text'].strip()
        self.chat_name = chat_data['first_name']
        self.last_name = chat_data['last_name']
        self.username = chat_data.get('username', '')
        self.user_conn = BotDbConnection(self.chat_id, 'telegram',
                                         name=self.chat_name,
                                         last_name=self.last_name,
                                         platform_alias=self.username)
        self._check_flow()

    def send_message(self, text, keyboard_opts=None):
        """
        Creates a url with text and buttons

        :param text: text
        :param keyboard_opts: array of string
        :return:
        """
        text = urllib.parse.quote_plus(text)

        url = self.TG_BASE_MESSAGE_URL.format(self.chat_id, text)
        url = self._concat_buttons(keyboard_opts, url)

        r = requests.get(url)

        edu_logger.debug('telegram send message: {}'.format(url))
        edu_logger.debug('return: {}-{}'.format(r.status_code, r.text))

        return r.json()

    #
    # Private
    #

    def _concat_buttons(self, keyboard_opts, url, show_once=True):
        # https://core.telegram.org/bots/api/#keyboardbutton
        if keyboard_opts:
            keyboard_opts = [[text] for text in keyboard_opts]
            reply_markup = {'keyboard': keyboard_opts, 'one_time_keyboard': show_once}
            url += '&reply_markup={}'.format(json.dumps(reply_markup))
        return url
