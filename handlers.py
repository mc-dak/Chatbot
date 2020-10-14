#!/usr/bin/env python3
"""
Handler принимает text (текст входящего сообщения) и context (dict), а возвращает bool:
True если код пройден, False если данные введены неправильно
"""
import re
import settings
import datetime
from ticket import make_ticket

re_departure = re.compile(r'^[\w\-\s]{3,10}$')
re_arrival = re.compile(r'^[\w\-\s]{3,10}$')
re_date = re.compile(r"[\d]{1,2}-[\d]{1,2}-[\d]{4}")
re_flight = re.compile(r'^[1-6]$')
re_seats = re.compile(r'^[1-5]$')
re_phone = re.compile(r'^[\d]{11}$')


def handle_departure(text, context):
    match = re.match(re_departure, text)
    if match:
        for intent in settings.DESTINATIONS:
            if any(token in text.lower() for token in intent['departure']):
                context['departure'] = intent['right_departure']
                return True
    else:
        return False


def handle_arrival(text, context):
    match = re.match(re_arrival, text)
    context['error_message'] = None
    context['days_of_flights'] = []
    if match:
        for intent in settings.DESTINATIONS:
            if any(token in text.lower() for token in intent['arrival']):
                context['arrival'] = intent['right_arrival']
    else:
        context['error_message'] = "Прилета в этот город нет. На данный момент есть только полеты между " \
                                   "городами: Москва-Гонконг, Москва-Сеул, Гонконг-Макао"
        return False  # Многовато тут дублирования выходит, было бы хорошо эту функцию переосмыслить по возможности
    if len(context) == 3:
        context['error_message'] = "Прилета в этот город нет. На данный момент есть только полеты между " \
                                   "городами: Москва-Гонконг, Москва-Сеул, Гонконг-Макао"
        return False
    for intent in settings.DESTINATIONS:
        k = 0
        for key, value in intent.items():
            if value == context['departure'] or value == context['arrival']:
                k += 1
            if k == 2:
                if key == 'timetable':
                    if type(value) is tuple:
                        for element in value:
                            context[element] = intent['flight_number']
                            context['days_of_flights'].append(element)
                    else:
                        context[value] = intent['flight_number']
                        context['days_of_flights'].append(value)
    if len(context) > 4:
        return True
    else:
        context.pop('arrival')
        context['error_message'] = "Между выбранными городами нет рейса. На данный момент есть только полеты между " \
                                   "городами: Москва-Гонконг, Москва-Сеул, Гонконг-Макао"
        return False


def handle_date(text, context):
    date = re.findall(re_date, text)
    if date:
        date = datetime.datetime.strptime(text, '%d-%m-%Y')
        k = 0
        while k <= 4:
            for element in context['days_of_flights']:
                if (date.strftime('%A') == element) or (date.strftime('%d') == element):
                    k += 1
                    name_for_dict = 'option' + str(k)
                    date = datetime.date(year=date.year, month=date.month, day=date.day)
                    if date.strftime('%A') == element:
                        option = f"{k} : {context['departure']} - {context['arrival']}, {date}, " \
                                 f"{context[date.strftime('%A')]}"
                        context[name_for_dict] = option
                    else:
                        option = f"{k} : {context['departure']} - {context['arrival']}, {date}, " \
                                 f"{context[date.strftime('%d')]}"
                        context[name_for_dict] = option
            date += datetime.timedelta(days=1)
        for key in context['days_of_flights']:
            context.pop(key)
        context.pop('days_of_flights')
        context.pop('error_message')
        return True
    else:
        return False


def handle_flight(text, context):
    match = re.match(re_flight, text)
    if match:
        name_for_dict = 'option' + str(text)
        name, date, number_of_flight = context[name_for_dict].split(',')
        context['date'] = date[1:]
        context['number_of_flight'] = number_of_flight[1:]
        for k in range(1, 6):
            name_for_dict = 'option' + str(k)
            context.pop(name_for_dict)
        return True
    else:
        return False


def handle_seats(text, context):
    match = re.match(re_seats, text)
    if match:
        context['number_of_seats'] = text
        return True
    else:
        return False


def handle_comment(text, context):
    context['comment'] = text
    return True


def handle_answer(text, context):
    if text == 'да' or text == 'нет':
        if text == 'да':
            return True
        else:
            context['failure_answer'] = "Ваш запрос удален. Попробуйте еще раз"
            return False
    else:
        context['failure_answer'] = "Введите 'да' или 'нет'"
        return False


def handle_phone(text, context):
    match = re.match(re_phone, text)
    if match:
        context['phone'] = text
        return True
    else:
        return False


def generate_ticket(text, context):
    return make_ticket('Сидоров Василий Петрович', from_=context['departure'], to=context['arrival'], date=context['date'])
