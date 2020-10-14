from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch, Mock
from pony.orm import db_session, rollback
from vk_api.bot_longpoll import VkBotEvent
from ticket import make_ticket
from bot import Bot
import settings


def isolate_db(test_func):
    def wrapper(*args, **kwargs):
        with db_session:
            test_func(*args, **kwargs)
            rollback()
    return wrapper


class Test1(TestCase):
    RAW_EVENT = {
        'type': 'message_new',
        'object': {
            'message': {'date': 1589100576, 'from_id': 3070727, 'id': 145, 'out': 0, 'peer_id': 3070727,
                        'text': 'new test', 'conversation_message_id': 145, 'fwd_messages': [], 'important': False,
                        'random_id': 0, 'attachments': [], 'is_hidden': False},
            'client_info': {'button_actions': ['text', 'vkpay', 'open_app', 'location', 'open_link'], 'keyboard': True,
                            'inline_keyboard': True, 'lang_id': 0}
        },
        'group_id': 194926720,
        'event_id': '82fb2251778c479e62278a8e96f2d8c1b8649d9c'}

    def test_run(self):
        count = 5
        obj = {}
        events = [obj] * count  # [obj, obj, ...]
        long_poll_mock = Mock(return_value=events)
        long_poll_listen_mock = Mock()
        long_poll_listen_mock.listen = long_poll_mock

        with patch('bot.vk_api.VkApi'):
            with patch('bot.VkBotLongPoll', return_value=long_poll_listen_mock):
                bot = Bot('', '')
                bot.on_event = Mock()
                bot.send_image = Mock()
                bot.run()
                bot.on_event.assert_called()
                bot.on_event.assert_any_call(obj)
                assert bot.on_event.call_count == count

    INPUTS = [
        "ыовыовыров",
        "Привет",
        "/ticket",
        "Москва",
        "Гонконг",
        "04-06-2020",
        "1",
        "тестовый коммент",
        "1",
        "тестовый коммент",
        "да",
        "8917",
        "89172051234",
    ]

    EXPECTED_OUTPUTS = [
        settings.DEFAULT_ANSWER,
        settings.INTENTS_TICKET[0]['answer'],
        settings.SCENARIOS_TICKET['purchase']['steps']['step1']['text'],
        settings.SCENARIOS_TICKET['purchase']['steps']['step2']['text'],
        settings.SCENARIOS_TICKET['purchase']['steps']['step3']['text'],
        settings.SCENARIOS_TICKET['purchase']['steps']['step4']['text'].format(
            option1='1 : Москва - Гонконг, 2020-06-05, FL001',
            option2='2 : Москва - Гонконг, 2020-06-08, FL001',
            option3='3 : Москва - Гонконг, 2020-06-09, FL002',
            option4='4 : Москва - Гонконг, 2020-06-12, FL001',
            option5='5 : Москва - Гонконг, 2020-06-15, FL001'),
        settings.SCENARIOS_TICKET['purchase']['steps']['step5']['text'],
        settings.SCENARIOS_TICKET['purchase']['steps']['step5']['failure_text'],
        settings.SCENARIOS_TICKET['purchase']['steps']['step6']['text'],
        settings.SCENARIOS_TICKET['purchase']['steps']['step7']['text'].format(
            departure='Москва',
            arrival='Гонконг',
            date='2020-06-05',
            number_of_flight='FL001',
            number_of_seats='1',
            comment='тестовый коммент'),
        settings.SCENARIOS_TICKET['purchase']['steps']['step8']['text'],
        settings.SCENARIOS_TICKET['purchase']['steps']['step8']['failure_text'],
        settings.SCENARIOS_TICKET['purchase']['steps']['step9']['text'].format(phone='89172051234'),
    ]

    @isolate_db
    def test_on_event_ticket(self):
        send_mock = Mock()
        api_mock = Mock()
        api_mock.messages.send = send_mock

        events = []
        for input_text in self.INPUTS:
            event = deepcopy(self.RAW_EVENT)
            event['object']['message']['text'] = input_text
            events.append(VkBotEvent(event))

        long_poller_mock = Mock()
        long_poller_mock.listen = Mock(return_value=events)

        with patch('bot.VkBotLongPoll', return_value=long_poller_mock):
            bot = Bot('', '')
            bot.api = api_mock
            bot.send_image = Mock()
            bot.run()
        assert send_mock.call_count == len(self.INPUTS)

        real_outputs = []
        for call in send_mock.call_args_list:
            args, kwargs = call
            real_outputs.append(kwargs['message'])
        assert real_outputs == self.EXPECTED_OUTPUTS

    def test_image_generation(self):
        ticket_file = make_ticket('Иванов Иван Иванович', 'Москва', 'Гонконг', '2020-06-05')
        with open('./images/ticket_template_Иванов.png', 'rb') as expected_file:
            expected_bytes = expected_file.read()
        assert ticket_file.read() == expected_bytes
