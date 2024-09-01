from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from sqlite3 import Cursor


def set_empty_table(table: dict) -> dict:
    '''
    Функция, очищающая таблицу с расписанием.
    '''
    week_days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
    table = {str(c): {i: {} for i in week_days} for c in range(1, 5)}
    return table


def make_day_table(day: str, group: str, table: dict, today: bool) -> str:
    '''
    Извлечение уроков для определенного дня и создание сообщения с расписанием для пользователя.
    '''
    text = f"<b><u>{day}</u></b>\n"
    if table[day] == {} and today:
        return text + "="*30 + "\n" + "Сегодня пар нет\n" + "="*30 + "\n"
    elif table[day] == {} and not today:
        return text + "="*30 + "\n" + "Пар нет\n" + "="*30 + "\n"
    now = float(datetime.now().strftime('%H.%M'))
    flag = True
    for hour in sorted(table[day]):
        if group not in table[day][hour]:
            continue
        text += "="*30 + "\n"
        if today and flag and now < float(hour.split(" - ")[0].replace(":", ".")):
            text += "✏<i>Следующая пара</i>✏\n"
            flag = False
        text += make_hour_table(hour, day, table, group)
    if text == f"<b><u>{day}</u></b>\n":
        text += "="*30 + "\n"
        text += "Сегодня пар нет\n"
    text += "="*30 + "\n"
    return text


def make_hour_table(hour: str, day: str, table: dict, group: str) -> str:
    '''
    Создание отдельной части сообщения с парой, которая проходит в определенный промежуток времени.
    '''
    text = f"<b>{hour}</b>\n"
    for name in table[day][hour][group]:
        text += name + "\n"
        for details in table[day][hour][group][name]:
            text += details
        text += "ИЛИ\n"
    text = text[:-4]
    return text


async def week_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE, cur, table) -> None:
    '''
    Создания сообщения для пользователя с предметами на определенный день недели.
    '''
    days_en_to_ru = {
        "Monday": "Понедельник",
        "Tuesday": "Вторник",
        "Wednesday": "Среда",
        "Thursday": "Четверг",
        "Friday": "Пятница",
        "Saturday": "Суббота"
    }
    curr_table, group = await get_group(update, context, cur, table)
    if not table:
        return
    day = days_en_to_ru[update.callback_query.data]
    text = make_day_table(day, group, curr_table, False)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )


async def get_group(update: Update, context: ContextTypes.DEFAULT_TYPE, cur: Cursor, table: dict) -> None:
    '''
    Извлечение из базы данных информации о пользоветеле (группа, в которой он учится и год поступления на первый курс).
    '''
    group = cur.execute("SELECT grp, year FROM users WHERE id = ?", (update.effective_user.id,)).fetchone()

    if not group:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Для начала выбери свою группу, для этого отправь /select_group мне в личку"
        )
        return 0, 0
    group, year = group[0], group[1]
    if year == 21:
        return table["4"], str(group)    
    elif year == 22:
        return table["3"], str(group)    
    elif year == 23:
        return table["2"], str(group)    
    elif year == 24:
        return table["1"], str(group)
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Для начала выбери свою группу, для этого отправь /select_group мне в личку"
        )
        return 0, 0
        