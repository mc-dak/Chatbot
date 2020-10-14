from pony.orm import Database, Required, Json

from settings import DB_CONFIG

db = Database()
db.bind(**DB_CONFIG)


class UserState(db.Entity):
    """Состояние пользователя внутри сценария"""
    user_id = Required(str, unique=True)
    scenario_name = Required(str)
    step_name = Required(str)
    context = Required(Json)


class TicketRequest(db.Entity):
    departure = Required(str)
    arrival = Required(str)
    date = Required(str)
    number_of_flight = Required(str)
    number_of_seats = Required(str)
    comment = Required(str)
    phone = Required(str)


db.generate_mapping(create_tables=True)
