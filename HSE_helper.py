import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, filters
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import sqlite3 as sql
from selenium import webdriver
import time

from params import OWNER_ID, MAIN_BOT_TOKEN, TEST_BOT_TOKEN


async def get_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Извлечение из базы данных информации о пользоветеле (группа, в которой он учится и год поступления на первый курс).
    '''
    group = cur.execute("SELECT grp, year FROM users WHERE id = ?", (update.effective_user.id,)).fetchone()

    if not group:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Для начала выбери свою группу, для этого отправь /select_group мне в личку")
        return 0, 0
    
    group, year = group[0], group[1]

    if year == 20:
        return table_2020, str(group)
    
    if year == 21:
        return table_2021, str(group)
    
    elif year == 22:
        return table_2022, str(group)
    
    else:
        return table_2023, str(group)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Отправка приветственного сообщения.
    '''
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Привет! Я бот для помощи по учебе в ВШЭ. Я могу подсказать расписание или отправить домашнее задание.\nДля выбора своей группы отправь\n/select_group")


async def send_course_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Отправка пользователю сообщения с выбором года, когда он поступил на первый курс.
    '''
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("2020", callback_data = "2020_course"), InlineKeyboardButton("2021", callback_data = "2021_course"), InlineKeyboardButton("2022", callback_data = "2022_course"), InlineKeyboardButton("2023", callback_data = "2023_course")]])
    await context.bot.send_message(chat_id=update.effective_chat.id, text="В каком году ты пришел на первый курс?", reply_markup=keyboard)


async def send_select_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Отправка пользователю сообщения с выбором группы, в которой он учится.
    '''
    if update.callback_query.data == "2020_course":
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(f"20{j}", callback_data=f"20{j}_group"), InlineKeyboardButton(f"20{j+1}", callback_data=f"20{j+1}_group")] for j in range(1, 11, 2)])
    
    elif update.callback_query.data == "2021_course":
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(f"21{j}", callback_data=f"21{j}_group"), InlineKeyboardButton(f"21{j+1}", callback_data=f"21{j+1}_group")] for j in range(1, 11, 2)])
    
    elif update.callback_query.data == "2022_course":
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(f"22{j}", callback_data=f"22{j}_group"), InlineKeyboardButton(f"22{j+1}", callback_data=f"22{j+1}_group")] for j in range(1, 11, 2)])
    
    else:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(f"23{j}", callback_data=f"23{j}_group"), InlineKeyboardButton(f"23{j+1}", callback_data=f"23{j+1}_group")] for j in range(1, 13, 2)])
    
    await context.bot.edit_message_text(chat_id=update.effective_chat.id,  message_id=update.callback_query.message.id, text="Теперь выбери группу для доступа к быстрому расписанию", reply_markup=keyboard)


async def select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Функция, которая вызывается при нажатии на клавиатуру в сообщении (InlineKeyboard).
    Подразделена на 3 варианта:
    - выбор дня, для получения расписания
    - выбор года, когда поступил в университет, для дальнейшего использования этой информации в создании расписания
    - выбор группы, в которой учится, для дальнейшего использования этой информации в создании расписания
    '''
    # выбрал день для расписания
    if update.callback_query.data in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]:
        await week_lessons(update, context)
    
    # выбрал год поступления
    elif update.callback_query.data in ["2020_course", "2021_course", "2022_course", "2023_course"]:
        await send_select_group(update, context)
    
    # выбрал свою группу
    else:
        user_id = update.effective_user.id
        res = cur.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        text = update.callback_query.data[:-6]
        group = int(text[2:])-1
        year = int(text[:2])

        if not res:
            cur.execute("INSERT INTO users VALUES (?, ?, ?)", (user_id, group, year))
        else:
            cur.execute("UPDATE users SET grp = ?, year = ? WHERE id = ?", (group, year, user_id))
        con.commit()

        await context.bot.delete_message(chat_id=user_id, message_id=update.callback_query.message.id)
        await context.bot.send_message(chat_id=update.effective_user.id, text=f"Твоя группа <b>{update.callback_query.data[:-6]}</b>\nКоманды с расписанием:\n/next - узнать, какая пара следующая\n/day - расписание на сегодня\n/tomorrow - расписание на завтра\n/week - расписание по дням недели", parse_mode="HTML")


async def day_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Создания сообщения для пользователя, с предметами на данный день недели.
    '''
    day = WEEK[datetime.now().weekday()]

    if day == "Воскресенье":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Сегодня выходной, можешь расслабиться")
        return
    
    table, group = await get_group(update, context)
    if not table:
        return
    
    text = make_day_table(day, group, table, False)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode="HTML", disable_web_page_preview=True)


async def next_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Создания сообщения для пользователя, показывающее, какая у него следующая пара.
    '''
    table, group = await get_group(update, context)

    if not table:
        return
    
    day = WEEK[datetime.now().weekday()]
    text = ""
    now = float(datetime.now().strftime('%H.%M'))

    for hour in sorted(table[day]):
        text += "="*30 + "\n"
        if now < float(hour.split(" - ")[0].replace(":", ".")):
            now = hour
            break
    else:
        now == "night"

    if now == "night" or group not in table[day][hour]:
        text = "Пары на сегодня закончились"
    else:
        text = make_hour_table(now, day, table, group)

    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode="HTML", disable_web_page_preview=True)


async def tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Создания сообщения для пользователя с предметами на следующий день недели.
    '''
    day = WEEK[(datetime.now().weekday() + 1)%7]

    if day == "Воскресенье":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Завтра выходной, можешь расслабиться")
        return
    
    table, group = await get_group(update, context)
    if not table:
        return
    
    text = make_day_table(day, group, table, False)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode="HTML", disable_web_page_preview=True)


async def week_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Создания сообщения для пользователя с предметами на определенный день недели.
    '''
    days_en_to_ru = {"Monday": "Понедельник", "Tuesday": "Вторник", "Wednesday": "Среда", "Thursday": "Четверг", "Friday": "Пятница", "Saturday": "Суббота"}
    table, group = await get_group(update, context)
    if not table:
        return
    
    day = days_en_to_ru[update.callback_query.data]
    text = make_day_table(day, group, table, False)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode="HTML", disable_web_page_preview=True)


async def ask_week_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Отправка сообщения с выбором дня, на который пользователь хочет увидеть расписание.
    '''
    group = cur.execute("SELECT grp FROM users WHERE id = ?", (update.effective_user.id,)).fetchone()

    if not group:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Для начала выбери свою группу, для этого отправь /select_group мне в личку")
        return
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Понедельник", callback_data=f"Monday"), InlineKeyboardButton("Вторник", callback_data=f"Tuesday"), InlineKeyboardButton("Среда", callback_data=f"Wednesday")],
                                    [InlineKeyboardButton("Четверг", callback_data=f"Thursday"), InlineKeyboardButton("Пятница", callback_data=f"Friday"), InlineKeyboardButton("Суббота", callback_data=f"Saturday")]])
    await context.bot.send_message(chat_id=update.effective_chat.id, text="На какой день ты хочешь увидеть расписание?", reply_markup=keyboard)


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
        if flag and now < float(hour.split(" - ")[0].replace(":", ".")):
            text += "✏<i>Следующая пара</i>✏\n"
            flag = False
        text += make_hour_table(hour, day, table, group)

    if text[-4:] == "b>\n":
        text += "="*30 + "\n"
        text += "Сегодня пар нет\n"
    text += "="*30 + "\n"

    return text


def fetch_html_with_selen(url: str) -> str:
    '''
    Извлечение кода сайта, с использованием модуля selenium, так как расписание сайта подгружается не сразу.
    '''
    try:
        global driver
        driver.get(url)
        time.sleep(0.5)
        page_source = driver.page_source
        return page_source
    except:
        return


async def update_table(context: ContextTypes.DEFAULT_TYPE = None) -> None:
    '''
    Функция, производящая обновление таблицы с расписанием. Вызывается каждые 24 часа.
    '''
    global driver
    current_datetime = datetime.now()
    delta = timedelta(days=6)
    fromdate, todate = current_datetime.strftime("%Y.%m.%d"), (current_datetime+delta).strftime("%Y.%m.%d")

    set_empty_table()
    
    driver = webdriver.Chrome()

    for course in groups:
        for i, g in enumerate(groups[course]):
            extract_lessons(fromdate=fromdate, todate=todate, groupid=g, course_number=course, group=str(i))
            
    driver.quit()


def extract_lessons(fromdate: str, todate: str, groupid: str, course_number: str, group: str) -> None:
    '''
    В этой функции происходит извлечение кода сайта с расписанием для отдельной группы курса.
    Далее из кода сайта извлекаются определенные HTML-классы, в которых содержится расписание уроков на день, и дни разделяются на часы
    и записываются в таблицу, для дальнейшей отправки пользователю.
    '''
    global table_2023, table_2022, table_2021, table_2020

    url = f"https://www.hse.ru/ba/ami/timetable?fromdate={fromdate}&todate={todate}&groupoid={groupid}&receiverType=3&timetable-courses={course_number}&timetable-groups={groupid}&timetable-view-switcher=list"
    html = fetch_html_with_selen(url)
    soup = BeautifulSoup(html, "html.parser")
    soup = soup.find_all(class_="tt-list__item")

    flag = False

    for day_table in soup:
        flag = True

        week_day: str
        day_table: BeautifulSoup

        week_day = day_table.find(class_="tt__title").text
        week_day = week_day[:week_day.find(",")].lower()
        week_day = week_day[0].upper() + week_day[1:]
        for pair in day_table.find_all(class_="pair"):

            pair: BeautifulSoup
            
            if pair.find(class_="fa fa-clock-o"):
                continue
            
            pair_time = pair.find(class_="pair__time").text + " - " + pair.find(class_="pair__time pair__time_end").text
            pair_name = pair.find(class_="pair__name").text.split("\n")
            while "" in pair_name:
                pair_name.pop(pair_name.index(""))

            if pair_name[0] == "Лекция":
                pair_name[0] = "[Л]"
            elif pair_name[0] == "Семинары":
                pair_name[0] = "[С]"
            elif pair_name[0] == "Практические занятия":
                pair_name[0] = "[ПЗ]"
            elif pair_name[0] == "Экзамен":
                pair_name[0] = "[Э]"
            elif pair_name[0] == "Контрольная работа":
                pair_name[0] = "[КР]"
            elif pair_name[0] == "Научно-исследовательский семинар":
                pair_name[0] = "[Н-И С]"
            else:
                pair_name[0] += "\n"

            if len(pair_name) > 1:
                pair_name[1] = pair_name[0] + f" <b>{pair_name[1][:pair_name[1].find('(')-1]}</b>"
                pair_name.pop(0)

            pair_name = "\n".join(pair_name)
            pair_details = pair.find(class_="pair__details").text.replace("\t", "").split("\n")
            
            i = 0
            while i < len(pair_details):
                if pair_details[i] == "" or pair_details[i] == "Покровский б-р, д.11" or "." in pair_details[i] and "/" in pair_details[-1]:
                    pair_details.pop(i)
                    continue
                elif "ауд." in pair_details[i]:
                    pair_details[i] = f"<i><u>{pair_details[i]}</u></i>\n"
                    pair_details = pair_details[:i+1]
                    break
                else:
                    if pair_details[i][:4] == "Вак_":
                        pair_details[i] = pair_details[i][4:]
                    if len(pair_details[i]) >= 21:
                        pair_details[i] += "\n"
                    else:
                        pair_details[i] += " "
                i += 1

            for url in pair.find_all("a"):
                href = url.get('href')
                if href != None and "hse" not in href:
                    pair_details.append(f"<a href=\"{href}\">Ссылка на занятие</a>\n")

            pair_details = "".join(pair_details)
            if pair_details[0] == " ":
                pair_details = pair_details[1:]

            if course_number == "1":
                table = table_2023
            elif course_number == "2":
                table = table_2022
            elif course_number == "3":
                table = table_2021
            else:
                table = table_2020

            if pair_time not in table[week_day]:
                table[week_day][pair_time] = {}
            if group not in table[week_day][pair_time]:
                table[week_day][pair_time][group] = {}
            if pair_name not in table[week_day][pair_time][group]:
                table[week_day][pair_time][group][pair_name] = []

            table[week_day][pair_time][group][pair_name].append(pair_details)
            
    if not flag:
        extract_lessons(fromdate, todate, groupid, course_number, group)
    

def set_empty_table() -> None:
    '''
    Функция, очищающая таблицу с расписанием.
    '''
    global table_2023, table_2022, table_2021, table_2020

    week_days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]

    table_2023 = {i: {} for i in week_days}
    table_2022 = {i: {} for i in week_days}
    table_2021 = {i: {} for i in week_days}
    table_2020 = {i: {} for i in week_days}


async def tell_everybody(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Функция вызывается, если владелец бота отправляет команду "/tell_everybody" с текстом после нее. 
    Всем пользователям бота будет отправлен текст из сообщения.
    Например, если владелец отправит "/tell_everybody Спасибо, что пользуетесь ботом!",
    пользователи получат сообщение "Спасибо, что пользуетесь ботом!".
    '''
    if update.message.chat_id != OWNER_ID:
        return
    
    text = update.message.text
    text = text[text.find("/tell_everybody")+len("/tell_everybody"):]
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Поделиться ботом", switch_inline_query="\n**Лучший бот с расписанием пар для учеников ПМИ ВШЭ**")]])
    res = cur.execute("SELECT id FROM users").fetchall()

    for i in res:
        await context.bot.send_message(chat_id=i[0], text=text, parse_mode="HTML", reply_markup=keyboard)


def launching_the_bot() -> None:
    '''
    Запуск бота.
    Добавления обработчиков событий и функций с повторяющимся запуском.
    '''
    app = ApplicationBuilder().token(TOKEN).build()

    app.job_queue.run_once(update_table, when=0)
    current_time = datetime.now()
    seconds_since_midnight = (current_time - current_time.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
    app.job_queue.run_once(update_table, when=86400-seconds_since_midnight)
    app.job_queue.run_repeating(update_table, interval=86400)
        
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("select_group", send_course_select))
    app.add_handler(CommandHandler("next", next_lesson))
    app.add_handler(CommandHandler("day", day_lessons))
    app.add_handler(CommandHandler("week", ask_week_lessons))
    app.add_handler(CommandHandler("tell_everybody", tell_everybody, filters.Chat(chat_id=OWNER_ID)))
    app.add_handler(CommandHandler("tomorrow", tomorrow))
    app.add_handler(CallbackQueryHandler(select))

    app.run_polling()



table_2023 = {}
table_2022 = {}
table_2021 = {}
table_2020 = {}

groups = {
        "1": ["номер_группы_с_сайта", "номер_группы_с_сайта", "номер_группы_с_сайта", "номер_группы_с_сайта", "номер_группы_с_сайта", "номер_группы_с_сайта"],
        "2": ["номер_группы_с_сайта", "номер_группы_с_сайта", "номер_группы_с_сайта", "номер_группы_с_сайта", "номер_группы_с_сайта", "номер_группы_с_сайта"],
        "3": ["номер_группы_с_сайта", "номер_группы_с_сайта", "номер_группы_с_сайта", "номер_группы_с_сайта", "номер_группы_с_сайта", "номер_группы_с_сайта"],
        "4": ["номер_группы_с_сайта", "номер_группы_с_сайта", "номер_группы_с_сайта", "номер_группы_с_сайта", "номер_группы_с_сайта", "номер_группы_с_сайта"]
    }


WEEK = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
lesson_times = ['9:30 - 10:50', '11:10 - 12:30', '13:00 - 14:20', '14:40 - 16:00', '16:20 - 17:40', '18:10 - 19:30', '19:40 - 21:00']


logging.basicConfig(
    format='HSEhelper: %(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


if __name__ == '__main__':

    try:
        mode = input("Test: 0\nMain: 1\n-> ")
        
        if mode == "0":
            TOKEN = TEST_BOT_TOKEN
        elif mode == "1":
            TOKEN = MAIN_BOT_TOKEN
        else:
            raise Exception("Invalide mode")

        con = sql.connect("users.db")
        cur = con.cursor()

        cur.execute("CREATE TABLE IF NOT EXISTS users (id, grp, year)")
        con.commit()
                
        launching_the_bot()  
          
    finally:
        con.close()
