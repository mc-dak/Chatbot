import logging

import requests
import vk_api
from pony.orm import db_session
from vk_api.bot_longpoll import VkBotEventType, VkBotLongPoll
from vk_api.utils import get_random_id

import handlers
from models import UserState, TicketRequest

try:
    import settings
except ImportError:
    exit('DO CP settings.py.default settings.py and set TOKEN')

log = logging.getLogger('bot')


def configure_logging():
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(levelname)s;%(message)s'))
    log.addHandler(stream_handler)
    stream_handler.setLevel(logging.INFO)

    file_handler = logging.FileHandler('bot.log')
    file_handler.setFormatter(logging.Formatter("%(asctime)s;%(levelname)s;%(message)s",
                                                "%d-%m-%Y %H:%M"))

    log.addHandler(file_handler)
    file_handler.setLevel(logging.DEBUG)
    log.setLevel(logging.DEBUG)


class Bot:
    """
    Сценарий регистрации на конференции "Skillbox Conf" через vk.com
    Use python 3.7

    Поддерживает ответы на вопросы про дату, место проведения и сценарий регистарции:
    - спрашивает имя
    - спрашивает e-mail
    - говорим об успешной регистрации
    Если шаг не пройден, задаем уточняющий вопрос пока шаг не будет пройден
    """

    def __init__(self, group_id, token):
        """
        :param group_id: group_id из vk.com
        :param token: секретный токен
        """
        self.group_id = group_id
        self.token = token
        self.vk = vk_api.VkApi(token=token)
        self.long_poll = VkBotLongPoll(self.vk, self.group_id)
        self.api = self.vk.get_api()

    def run(self):
        """Запуск бота"""
        for event in self.long_poll.listen():
            try:
                self.on_event(event)
            except Exception:
                log.exception('ошибка в обработке события')

    @db_session
    def on_event(self, event):
        """
        Отправляет сообщение назад, если сообщение текст
        :param event: VKBotMessageEvent event
        :return: None
        """
        if event.type != VkBotEventType.MESSAGE_NEW:
            log.info('мы еще не умеем обрабатывать такой тип событий %s', event.type)
            return

        user_id = event.object.message['peer_id']
        text = event.object.message['text']
        state = UserState.get(user_id=str(user_id))

        if state is not None:
            # continue scenario
            self.continue_scenario(text, state, event)
        else:
            # search intent
            for intent in settings.INTENTS_TICKET:
                if any(token in text.lower() for token in intent['tokens']):
                    log.debug(f'User gets {intent}')
                    # run intent
                    if intent['answer']:
                        self.send_text(event, intent['answer'])
                    else:
                        self.start_scenario(user_id, intent['scenario'], event, text)
                    break
            else:
                self.send_text(event, settings.DEFAULT_ANSWER)

    def send_text(self, event, text_to_send):
        self.api.messages.send(
            message=text_to_send,
            random_id=get_random_id(),
            peer_id=event.object.message['peer_id']
        )

    def send_image(self, event, image):
        upload_url = self.api.photos.getMessagesUploadServer()['upload_url']
        upload_data = requests.post(url=upload_url, files={'photo': ('image.png', image, 'image/png')}).json()
        image_data = self.api.photos.saveMessagesPhoto(**upload_data)
        owner_id = image_data[0]['owner_id']
        media_id = image_data[0]['id']
        attachment = f'photo{owner_id}_{media_id}'

        self.api.messages.send(
            attachment=attachment,
            random_id=get_random_id(),
            peer_id=event.object.message['peer_id']
        )

    def send_step(self, step, event, text, context):
        if 'text' in step:
            self.send_text(event, step['text'].format(**context))
        if 'image' in step:
            handler = getattr(handlers, step['image'])
            image = handler(text, context)
            self.send_image(event, image)

    def start_scenario(self, user_id, scenario_name, event, text):
        scenario = settings.SCENARIOS_TICKET[scenario_name]
        first_step = scenario['first_step']
        step = scenario['steps'][first_step]
        self.send_step(step, event, text, context={})
        UserState(user_id=str(user_id), scenario_name=scenario_name, step_name=first_step, context={})

    def continue_scenario(self, text, state, event):
        steps = settings.SCENARIOS_TICKET[state.scenario_name]['steps']
        step = steps[state.step_name]

        handler = getattr(handlers, step['handler'])
        if handler(text=text, context=state.context):
            # next_step
            next_step = steps[step['next_step']]
            self.send_step(next_step, event, text, state.context)
            if next_step['next_step']:
                # switch to next step
                state.step_name = step['next_step']
            else:
                # finish scenario
                log.info('Запрос на перелет из {departure} в {arrival} на дату {date}, номер рейса {number_of_flight}, '
                         'количество мест {number_of_seats}, комментарий: {comment}, телефон: {phone}'
                         .format(**state.context))
                TicketRequest(departure=state.context['departure'],
                              arrival=state.context['arrival'],
                              date=state.context['date'],
                              number_of_flight=state.context['number_of_flight'],
                              number_of_seats=state.context['number_of_seats'],
                              comment=state.context['comment'],
                              phone=state.context['phone'])
                state.delete()
        else:
            # retry current step
            text_to_send = step['failure_text'].format(**state.context)
            self.send_text(event, text_to_send)
            vars_of_text = ["Между выбранными городами нет рейса. На данный момент есть только полеты между городами: "
                            "Москва-Гонконг, Москва-Сеул, Гонконг-Макао", "Ваш запрос удален. Попробуйте еще раз"]
            if step['to_step'] and text_to_send in vars_of_text:
                # switch to to step
                state.step_name = step['to_step']
                state.delete()


if __name__ == "__main__":
    configure_logging()
    bot = Bot(settings.GROUP_ID, settings.TOKEN)
    bot.run()
