import json
import os
import time
from urllib.parse import urljoin

import cchardet as chardet
import requests
from lxml import etree
from tenacity import retry, stop_after_attempt, wait_random

from magazine import Article, Magazine, Section

session = requests.session()
session.headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
}


@retry(stop=stop_after_attempt(3), wait=wait_random(min=1, max=3))
def get_html(url):
    response = session.get(url, timeout=5)
    if(response.status_code > 399):
        raise IOError("connect error!")

    result = chardet.detect(response.content)
    response.encoding = result["encoding"]
    return response.text


def load_json(filename):
    with open(filename, mode="r", encoding="utf-8") as f:
        novel_list = json.load(f)
    return novel_list


def dump_json(novel_list, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(novel_list, f, ensure_ascii=False)


def get_chapter_list(url, chapter_xpath, last_chapter_index):
    html = get_html(url)
    parser = etree.HTML(html)
    chapter_list = parser.xpath(chapter_xpath)[last_chapter_index:]
    for chapter in chapter_list:
        chapter_title = chapter.xpath("./child::node()")[0]
        chapter_url = chapter.xpath("./ancestor-or-self::node()/@href")[0]
        yield chapter_title, chapter_url


def get_chapter_content(url, content_xpath):
    html = get_html(url)
    parser = etree.HTML(html)
    paragraph_list = parser.xpath(content_xpath)
    content = "<br>".join(
        map(
            lambda str: f"<p>&nbsp;&nbsp;&nbsp;&nbsp;{str.strip()}</p>", paragraph_list
        ))
    return paragraph_list[0], content


def get_section(novel):
    section = Section(novel["title"])

    chapter_list = get_chapter_list(
        novel["url"], novel["chapter_xpath"], novel["last_chapter_index"]
    )
    for index, (title, url) in enumerate(chapter_list):
        description, content = get_chapter_content(
            urljoin(novel["url"], url), novel["content_xpath"]
        )

        article = Article(
            f"{novel['title']}-{index}", title, description
        )

        article.write_to_html(content)

        section.append_article(article)

    novel["last_chapter_index"] += len(section.article_list)

    return section


if __name__ == "__main__":
    os.mkdir("html")

    setting = load_json("setting.json")

    magazine = Magazine(setting["title"])

    novel_list = setting["novel_list"]

    for novel in novel_list:
        magazine.append_section(get_section(novel))

    if len(magazine.section_list) > 0:
        magazine.write_to_opf()
        magazine.write_toc_ncx()
        magazine.write_toc_html()

        dump_json(setting, "setting.json")

        print(1)
