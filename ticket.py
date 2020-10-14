import argparse
import re
import time
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont


class NotNameError(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


def make_ticket(fio, from_, to, date):
    infile = './images/ticket_template.png'
    pos_fio = (46, 120)
    pos_from = (46, 190)
    pos_to = (46, 257)
    pos_date = (287, 257)
    font_color = (0, 0, 0)
    try:
        l_name, f_name, m_name = fio.split(' ')
        if not l_name.isalpha() or not f_name.isalpha() or not m_name.isalpha():
            raise NotNameError(f"Поле 'ФИО' содержит НЕ только буквы")
        elif re.search(r'[^\w\s-]', from_):
            raise NotNameError(f"Поле 'Откуда' содержит НЕ только буквы, пробел или дефис")
        elif re.search(r'[^\w\s-]', to):
            raise NotNameError(f"Поле 'Куда' содержит НЕ только буквы, пробел или дефис")
        valid_date = time.strptime(date, '%Y-%m-%d')

        base = Image.open(infile)
        draw = ImageDraw.Draw(base)
        font = ImageFont.truetype("./fonts/Arial_Narrow.ttf", 16)
        fio_to_ticket = l_name.upper() + ' ' + f_name[0].upper() + '.' + m_name[0].upper() + '.'
        date_to_ticket = str(valid_date[2]) + '.' + str(valid_date[1]) + '.' + str(valid_date[0])
        draw.text(pos_fio, fio_to_ticket, font_color, font=font)
        draw.text(pos_from, from_.upper(), font_color, font=font)
        draw.text(pos_to, to.upper(), font_color, font=font)
        draw.text(pos_date, date_to_ticket, font_color, font=font)

        temp_file = BytesIO()
        base.save(temp_file, 'png')
        temp_file.seek(0)
        return temp_file

    except IOError:
        print(f'Cannot open {infile}')
    except NotNameError as exc:
        print(f'{exc}')
    except ValueError as exc:
        if 'format' in exc.args[0]:
            print(f'{exc}')
        else:
            print(f"{exc} в строке {fio}")
