import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, filters
from datetime import datetime, timedelta
import sqlite3 as sql
from selenium import webdriver

from params import OWNER_ID, MAIN_BOT_TOKEN, TEST_BOT_TOKEN
from TelegramBot import TelegramBot
from utils import *


@TelegramBot.AddCommandHandler("start")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Отправка приветственного сообщения.
    '''
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Привет! Я бот для помощи по учебе в ВШЭ. Я могу подсказать расписание или отправить домашнее задание.\nДля выбора своей группы отправь\n/select_group")


@TelegramBot.AddCommandHandler("select_group")
async def send_course_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Отправка пользователю сообщения с выбором года, когда он поступил на первый курс.
    '''
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("2021", callback_data = "2021_course"),
        InlineKeyboardButton("2022", callback_data = "2022_course"),
        InlineKeyboardButton("2023", callback_data = "2023_course"),
        InlineKeyboardButton("2024", callback_data = "2024_course")
    ]])
    await context.bot.send_message(chat_id=update.effective_chat.id, text="В каком году ты пришел на первый курс?", reply_markup=keyboard)


async def send_select_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Отправка пользователю сообщения с выбором группы, в которой он учится.
    '''
    global groups
    if update.callback_query.data == "2021_course":
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"21{j}", callback_data=f"21{j}_group"),
            InlineKeyboardButton(f"21{j+1}", callback_data=f"21{j+1}_group")
        ] for j in range(1, len(groups["4"]), 2)])
    elif update.callback_query.data == "2022_course":
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"22{j}", callback_data=f"22{j}_group"),
            InlineKeyboardButton(f"22{j+1}", callback_data=f"22{j+1}_group")
        ] for j in range(1, len(groups["4"]), 2)])    
    elif update.callback_query.data == "2023_course":
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"23{j}", callback_data=f"23{j}_group"),
            InlineKeyboardButton(f"23{j+1}", callback_data=f"23{j+1}_group")
        ] for j in range(1, len(groups["2"]), 2)])    
    else:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"24{j}", callback_data=f"24{j}_group"),
            InlineKeyboardButton(f"24{j+1}", callback_data=f"24{j+1}_group")
        ] for j in range(1, len(groups["1"]), 2)])
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id, 
        message_id=update.callback_query.message.id,
        text="Теперь выбери группу для доступа к быстрому расписанию",
        reply_markup=keyboard
    )


@TelegramBot.AddCallbackQueryHandler()
async def select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Функция, которая вызывается при нажатии на клавиатуру в сообщении (InlineKeyboard).
    Подразделена на 3 варианта:
    - выбор дня, для получения расписания
    - выбор года, когда поступил в университет, для дальнейшего использования этой информации в создании расписания
    - выбор группы, в которой учится, для дальнейшего использования этой информации в создании расписания
    '''
    global cur, table

    # выбрал день для расписания
    if update.callback_query.data in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]:
        await week_lessons(update, context, cur, table)
    
    # выбрал год поступления
    elif update.callback_query.data in ["2021_course", "2022_course", "2023_course", "2024_course"]:
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
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text=f"Твоя группа <b>{update.callback_query.data[:-6]}</b>\nКоманды с расписанием:\n/next - узнать, какая пара следующая\n/day - расписание на сегодня\n/tomorrow - расписание на завтра\n/week - расписание по дням недели",
            parse_mode="HTML"
        )


@TelegramBot.AddCommandHandler("day")
async def day_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Создания сообщения для пользователя, с предметами на данный день недели.
    '''
    global cur, table

    day = WEEK[datetime.now().weekday()]
    if day == "Воскресенье":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Сегодня выходной, можешь расслабиться")
        return    
    curr_table, group = await get_group(update, context, cur, table)
    if not curr_table:
        return
    text = make_day_table(day, group, curr_table, True)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode="HTML", disable_web_page_preview=True)


@TelegramBot.AddCommandHandler("next")
async def next_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Создания сообщения для пользователя, показывающее, какая у него следующая пара.
    '''
    global cur, table

    curr_table, group = await get_group(update, context, cur, table)
    if not curr_table:
        return    
    day = WEEK[datetime.now().weekday()]
    text = ""
    now = float(datetime.now().strftime('%H.%M'))
    if day == "Воскресенье":        
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Сегодня выходной, можешь расслабиться")
        return
    for hour in sorted(curr_table[day]):
        text += "="*30 + "\n"
        if now < float(hour.split(" - ")[0].replace(":", ".")):
            now = hour
            break
    else:
        now == "night"
    if now == "night" or group not in curr_table[day][hour]:
        text = "Пары на сегодня закончились"
    else:
        text = make_hour_table(now, day, curr_table, group)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )


@TelegramBot.AddCommandHandler("tomorrow")
async def tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Создания сообщения для пользователя с предметами на следующий день недели.
    '''
    global cur, table

    day = WEEK[(datetime.now().weekday() + 1) % 7]
    if day == "Воскресенье":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Завтра выходной, можешь расслабиться")
        return
    curr_table, group = await get_group(update, context, cur, table)
    if not curr_table:
        return
    text = make_day_table(day, group, curr_table, False)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode="HTML", disable_web_page_preview=True)


@TelegramBot.AddCommandHandler("week")
async def ask_week_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''
    Отправка сообщения с выбором дня, на который пользователь хочет увидеть расписание.
    '''
    group = cur.execute("SELECT grp FROM users WHERE id = ?", (update.effective_user.id,)).fetchone()
    if not group:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Для начала выбери свою группу, для этого отправь /select_group мне в личку"
        )
        return
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Понедельник", callback_data=f"Monday"),
            InlineKeyboardButton("Вторник", callback_data=f"Tuesday"),
            InlineKeyboardButton("Среда", callback_data=f"Wednesday")
        ],
        [
            InlineKeyboardButton("Четверг", callback_data=f"Thursday"),
            InlineKeyboardButton("Пятница", callback_data=f"Friday"),
            InlineKeyboardButton("Суббота", callback_data=f"Saturday")
        ]
    ])
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="На какой день ты хочешь увидеть расписание?",
        reply_markup=keyboard
    )


@TelegramBot.AddJobQuery(repeating=True, first=10., interval=86400.)
async def update_table(context: ContextTypes.DEFAULT_TYPE = None) -> None:
    '''
    Функция, производящая обновление таблицы с расписанием. Вызывается каждые 24 часа.
    '''
    global driver, table, groups

    current_datetime = datetime.now()
    delta = timedelta(days=6)
    fromdate, todate = current_datetime.strftime("%Y.%m.%d"), (current_datetime+delta).strftime("%Y.%m.%d")
    table = set_empty_table(table)
    driver = webdriver.Chrome()
    try:
        for course in range(1, 5):
            for i, g in enumerate(groups[str(course)]):
                try:
                    table = extract_lessons(
                        fromdate=fromdate,
                        todate=todate,
                        groupid=g,
                        course_number=str(course),
                        group=str(i),
                        table=table,
                        driver=driver
                    )
                except:
                    continue
    finally:
        driver.quit()


@TelegramBot.AddCommandHandler("tell_everybody", filters=filters.Chat(chat_id=OWNER_ID))
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


table = {}

groups = {
    "1": [],
    "2": [],
    "3": [],
    "4": []
}


WEEK = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
lesson_times = ['9:30 - 10:50', '11:10 - 12:30', '13:00 - 14:20', '14:40 - 16:00', '16:20 - 17:40', '18:10 - 19:30', '19:40 - 21:00']


logging.basicConfig(
    format='HSEhelper: %(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

cur: sql.Cursor

if __name__ == '__main__':
    try:
        mode = input("Test: 0\nMain: 1\n-> ")
        if mode == "0":
            bot = TelegramBot(TEST_BOT_TOKEN)
        elif mode == "1":
            bot = TelegramBot(MAIN_BOT_TOKEN)
        else:
            raise Exception("Invalide mode")
        con = sql.connect("users.db")
        cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS users (id, grp, year)")
        con.commit()                
        bot.on()
    finally:
        con.close()
