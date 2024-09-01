import time
from selenium import webdriver
from bs4 import BeautifulSoup


def fetch_html_with_selen(url: str, driver: webdriver.Chrome) -> str:
    '''
    Извлечение кода сайта, с использованием модуля selenium, так как расписание сайта подгружается не сразу.
    '''
    try:
        driver.get(url)
        time.sleep(0.5)
        page_source = driver.page_source
        return page_source
    except:
        return


def extract_lessons(
        fromdate: str,
        todate: str,
        groupid: str,
        course_number: str,
        group: str,
        table: dict,
        driver: webdriver.Chrome
    ) -> dict:
    '''
    В этой функции происходит извлечение кода сайта с расписанием для отдельной группы курса.
    Далее из кода сайта извлекаются определенные HTML-классы, в которых содержится расписание уроков на день, и дни разделяются на часы
    и записываются в таблицу, для дальнейшей отправки пользователю.
    '''

    url = f"https://www.hse.ru/ba/ami/timetable?fromdate={fromdate}&todate={todate}&groupoid={groupid}&receiverType=3&timetable-courses={course_number}&timetable-groups={groupid}&timetable-view-switcher=list"
    html = fetch_html_with_selen(url, driver)
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

            curr_table = table[course_number]

            if pair_time not in curr_table[week_day]:
                curr_table[week_day][pair_time] = {}
            if group not in curr_table[week_day][pair_time]:
                curr_table[week_day][pair_time][group] = {}
            if pair_name not in curr_table[week_day][pair_time][group]:
                curr_table[week_day][pair_time][group][pair_name] = []

            curr_table[week_day][pair_time][group][pair_name].append(pair_details)
            
    if not flag:
        table = extract_lessons(fromdate, todate, groupid, course_number, group, table)
    return table

