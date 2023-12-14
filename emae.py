from bs4 import BeautifulSoup
from requests_html import HTMLSession
import re
import datetime


def get_current_date() -> str:
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d")


class Reading:
    def __init__(self, title: str, lines: list[str]):
        self.title = title
        self.lines = lines
    
    def get_text(self):
        lines_text = '\n--'.join(self.lines)
        return f"{self.title}\n{lines_text}"


def parse_readings() -> list[Reading]:
    session = HTMLSession()
    r = session.get(f'https://azbyka.ru/biblia/days/{get_current_date()}')
    soup = BeautifulSoup(r.html.html)

    raw_readings = soup.select('[id*="reading-"]')
    raw_reading_contents = soup.select('[class*="tbl-content"]')
    result: list[Reading] = []

    for i, raw_reading in enumerate(raw_readings):
        reading_title = re.sub(' +', ' ', raw_reading.text.replace("\n", ""))
        content = raw_reading_contents[i]
        lines = content.select('[class*="verse lang-r"]')
        result_lines: list[str] = []
        for line in lines:
            result_lines.append(line.text)
        result.append(Reading(reading_title, result_lines))

    return result

for r in parse_readings():
    print(r.get_text())
    print()
