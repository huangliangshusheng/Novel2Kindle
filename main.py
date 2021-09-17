import json
import os
import re
import time
from collections import namedtuple
from functools import reduce

import requests
from lxml import html
from tenacity import retry, stop_after_attempt, wait_random

Article = namedtuple("Article", "id, title, description")
Section = namedtuple("Section", "title, article_list")
Magazine = namedtuple("Magazine", "id, title, date, section_list",
                      defaults=(time.time_ns(), "Novel", time.strftime("%Y-%m-%d"), None))

session = requests.session()
session.headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
}

pattern = r"\n {2}(\S.*)\r\n([\S\s]+?)\r\n\r"


def wenku_spider(novel):
    def create_section(volume):
        vid = "".join(
            volume.xpath("../following-sibling::tr[1]/td[1]/a/@href")
        ).replace(".htm", "")
        if not vid:
            return None

        section_title = f"{title} {volume.text}"
        section_url = f"https://dl.wenku8.com/packtxt.php?aid={aid}&vid={vid}&charset=utf-8"

        response = fetch(section_url)
        text_list = re.findall(pattern, response.text)
        article_list = list(filter(None, (
            create_article(f"{section_title}-{index}", text)
            for index, text in enumerate(text_list)
        )))

        return Section(section_title, article_list)

    def create_article(id, text):
        line_list = text[1].split("\n")
        description, content = format_content(line_list)
        if not description:
            return None

        article = Article(id, text[0], description)
        write_Article(article, content)
        return article

    aid = novel["aid"]
    title = novel["title"]
    last_index = novel.get("last_index", -1)
    url = f"https://www.wenku8.net/novel/{aid // 1000}/{aid}/index.htm"

    volume_list = get_list(url, "//td[@class='vcss']")
    novel["last_index"] = len(volume_list)
    section_list = list(
        filter(None, map(create_section, volume_list[last_index:]))
    )

    return section_list


def default_spider(novel, chapter_xpath, content_xpath):
    def create_article(id, chapter):
        chapter_title = chapter.xpath("./child::node()")[0]
        chapter_url = chapter.xpath("./ancestor-or-self::node()/@href")[0]

        line_list = get_list(chapter_url, content_xpath)
        description, content = format_content(line_list)
        article = Article(id, chapter_title, description)
        write_Article(article, content)

        return article

    url = novel["url"]
    title = novel["title"]
    last_index = novel.get("last_index", -1)

    chapter_list = get_list(url, chapter_xpath, True)
    novel["last_index"] = len(chapter_list)
    article_list = list(
        create_article(f"{title}-{index}", chapter)
        for index, chapter in enumerate(chapter_list[last_index:])
    )

    if article_list:
        return [Section(title, article_list)]
    else:
        return []


def create_section_list(domain):
    novel_list = domain["novel_list"]

    if "wenku" == domain["domain"]:
        section_list = map(wenku_spider, novel_list)
    else:
        chapter_xpath = domain["chapter_xpath"]
        content_xpath = domain["content_xpath"]
        section_list = map(
            lambda novel: default_spider(novel, chapter_xpath, content_xpath),
            novel_list
        )

    return merge_list(section_list)


def write_magazine(manazine):
    def write_opf():
        item, itemref = map(
            lambda list: "\n".join(list),
            zip(*(
                article_to_opf(article) for section in manazine.section_list for article in section.article_list
            ))
        )

        opf = f'''
        <?xml version='1.0' encoding='utf-8'?>
        <package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="{manazine.id}">
        <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
            <dc-metadata>
                <dc:title>{manazine.title} {manazine.date}</dc:title>
                <dc:language>zh-CN</dc:language>
                <dc:subject>杂志</dc:subject>
                <dc:Identifier id="uid">{manazine.id}</dc:Identifier>
                <dc:date>{manazine.date}</dc:date>
            </dc-metadata>
            <x-metadata>
                <output content-type="application/x-mobipocket-subscription-magazine" encoding="utf-8"/>
                <EmbeddedCover>image/cover.jpg</EmbeddedCover>
            </x-metadata>
        </metadata>
        <manifest>
            <item href="html/toc.html" media-type="application/xhtml+xml" id="toc"/>
            <item href="toc.ncx" media-type="application/x-dtbncx+xml" id="ncx"/>
            {item}
            <item href="image/cover.jpg" media-type="image/jpeg" id="cover_img" />
        </manifest>
        <spine toc="ncx">
            <itemref idref="toc"/>
            {itemref}
        </spine>
        <guide>
            <reference href="html/toc.html" type="toc" title="Table of Contents" />
        </guide>
        </package>'''

        write_file("content.opf", opf)

    def write_toc_ncx():
        point = "\n".join(map(section_to_toc_ncx, manazine.section_list))

        toc = f'''
        <?xml version='1.0' encoding='utf-8'?>
        <!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
        <ncx xmlns:mbp="http://mobipocket.com/ns/mbp" xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="en-GB">
            <head>
                <meta content="{manazine.id}" name="dtb:uid" />
                <meta content="2" name="dtb:depth" />
                <meta content="0" name="dtb:totalPageCount" />
                <meta content="0" name="dtb:maxPageNumber" />
            </head>
            <docTitle>
                <text>{manazine.title}</text>
            </docTitle>
            <navMap>
                <navPoint class="periodical">
                    <navLabel>
                        <text>目录</text>
                    </navLabel>
                    <content src="html/toc.html" />
                    {point}
                </navPoint>
            </navMap>
        </ncx>'''

        write_file("toc.ncx", toc)

    def write_toc_html():
        ul = "\n".join(map(section_to_toc_html, manazine.section_list))
        toc = f'''
        <html>
            <head>
                <meta content="text/html; charset=utf-8" http-equiv="Content-Type"/>
                <title>目录</title>
            </head>
            <body>
                <h1>目录</h1>
                {ul}
            </body>
        </html>'''

        write_file("html/toc.html", toc)

    write_opf()
    write_toc_ncx()
    write_toc_html()


@retry(stop=stop_after_attempt(3), wait=wait_random(min=1, max=3))
def fetch(url):
    response = session.get(url, timeout=5)
    if(response.status_code > 399):
        raise IOError("connect error!")

    return response


def get_list(url, xpath, absolute_link=False):
    response = fetch(url)
    parser = html.fromstring(response.content)
    if absolute_link:
        parser.make_links_absolute(base_url=url)
    return parser.xpath(xpath)


def format_content(line_list):
    content_list = tuple(
        filter(None, map(lambda line: line.strip(), line_list))
    )
    if not content_list:
        return None, None

    description = content_list[0]
    content = "<br>".join(
        map(lambda line: f"<p>&nbsp;&nbsp;{line}</p>", content_list)
    )
    return description, content


def load_json(filename):
    with open(filename, mode="r", encoding="utf-8") as f:
        novel_list = json.load(f)
    return novel_list


def dump_json(novel_list, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(novel_list, f, ensure_ascii=False)


def write_file(filename, content):
    with open(filename, mode='w', encoding="utf-8") as f:
        f.write(content)


def write_Article(article, content):
    html = f'''
            <html lang="en" xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
                <head>
                    <meta content="http://www.w3.org/1999/xhtml; charset=utf-8" http-equiv="Content-Type" />
                    <title>{article.title}</title>
                </head>
                <body>
                    <div id="section1"></div>
                    <h1 id="title1" height="1em">
                        <font size="7">
                            <b>{article.title}</b>
                        </font>
                    </h1>
                    <br>
                    {content}
                </body>
            </html>'''

    filename = f"html/{article.id}.html"
    write_file(filename, html)


def article_to_opf(article):
    item = f"<item href='html/{article.id}.html' media-type='application/xhtml+xml' id='{article.id}'/>"
    itemref = f"<itemref idref='{article.id}'/>"
    return item, itemref


def article_to_toc_ncx(article):
    return f'''
        <navPoint class="article">
            <navLabel>
                <text>{article.title}</text>
            </navLabel>
            <content src="html/{article.id}.html#title1" />
            <mbp:meta name="description">{article.description}</mbp:meta>
        </navPoint>'''


def article_to_toc_html(article):
    return f"<li><a href='{article.id}.html'>{article.title}</a></li>"


def section_to_toc_ncx(section):
    if not section.article_list:
        return ""

    toc = "\n".join(map(article_to_toc_ncx, section.article_list))
    return f'''
        <navPoint class="section">
            <navLabel>
                <text>{section.title}</text>
            </navLabel>
            <content src="html/{section.article_list[0].id}.html#section1" />
            {toc}
        </navPoint>'''


def section_to_toc_html(section):
    if not section.article_list:
        return ""

    toc = "\n".join(map(article_to_toc_html, section.article_list))
    return f'''
        <h4 height="1em">{section.title}</h4>
        <ul>
            {toc}
        </ul>'''


def merge_list(list):
    return reduce(lambda x, y: x+y, list)


if __name__ == "__main__":
    os.mkdir("html")

    setting = load_json("setting.json")

    section_list = merge_list(map(create_section_list, setting["domain_list"]))

    if len(section_list) > 0:
        magazine = Magazine(title=setting.get(
            "title", "Novel"), section_list=section_list)

        write_magazine(magazine)

        dump_json(setting, "setting.json")

        print(1)
