import json
import os
import time
from datetime import datetime
from urllib.parse import urljoin

import cchardet as chardet
import requests
from lxml import etree

session = requests.session()
session.headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
}


def get_html(url):
    response = session.get(url)
    time.sleep(1)
    result = chardet.detect(response.content)
    response.encoding = result["encoding"]
    return etree.HTML(response.text)


def write_file(filename, content):
    with open(filename, mode='w', encoding="utf-8") as f:
        f.write(content)


def load_json(filename):
    with open(filename, mode="r", encoding="utf-8") as f:
        novel_list = json.load(f)
    return novel_list


def dump_json(novel_list, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(novel_list, f, ensure_ascii=False)


def get_chapter_list(url, chapter_xpath, last_chapter_index):
    html = get_html(url)
    chapter_list = html.xpath(chapter_xpath)[last_chapter_index:]
    for chapter in chapter_list:
        chapter_title = chapter.xpath("./child::node()")[0]
        chapter_url = chapter.xpath("./ancestor-or-self::node()/@href")[0]
        yield chapter_title, chapter_url


def get_chapter_content(url, content_xpath):
    html = get_html(url)
    content = html.xpath(content_xpath)[0]
    return etree.tostring(content, encoding="unicode", method="html", pretty_print=True)


def get_novel(novel):
    chapter_title_list = []

    chapter_list = get_chapter_list(
        novel["url"], novel["chapter_xpath"], novel["last_chapter_index"]
    )
    for index, (chapter_title, chapter_url) in enumerate(chapter_list):
        chapter_content = get_chapter_content(
            urljoin(novel["url"], chapter_url), novel["content_xpath"]
        )

        post_name = f"html/{novel['title']}-{index}.html"
        gen_post(chapter_title, chapter_content, post_name)

        chapter_title_list.append(chapter_title)

    novel["last_chapter_index"] += len(chapter_title_list)

    return novel["title"], chapter_title_list


def get_novel_list(novel_list):
    post_list = []
    for novel in novel_list:
        novel_title, chapter_title_list = get_novel(novel)
        if len(chapter_title_list) > 0:
            post_list.append((novel_title, chapter_title_list))

    if len(post_list) > 0:
        gen_opf(post_list)
        gen_toc_ncx(post_list)
        gen_toc_html(post_list)
        print(1)


def gen_post(title, content, filename):
    post = f'''
    <html lang="en" xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
        <head>
            <meta content="http://www.w3.org/1999/xhtml; charset=utf-8" http-equiv="Content-Type" />
            <title>{title}</title>
        </head>
        <body>
            <div id="section1"></div>
            <h1 id="title1" height="1em"><font size="7"><b>{title}</b></font></h1>
            {content}
        </body>
    </html>'''

    write_file(filename, post)


def gen_opf(post_list):
    item_list = []
    itemref_list = []
    for novel_title, chapter_title_list in post_list:
        for i in range(len(chapter_title_list)):
            item_list.append(
                f"<item href='html/{novel_title}-{i}.html' media-type='application/xhtml+xml' id='{novel_title}-{i}'/>"
            )
            itemref_list.append(f"<itemref idref='{novel_title}-{i}'/>")
    item = "\n".join(item_list)
    itemref = "\n".join(itemref_list)

    today = datetime.strftime(datetime.today(), '%Y-%m-%d')

    opf = f'''
    <?xml version='1.0' encoding='utf-8'?>
    <package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="novel-{today}">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc-metadata>
            <dc:title>Novel-{today}</dc:title>
            <dc:language>zh-CN</dc:language>
            <dc:subject>杂志</dc:subject>
            <dc:Identifier id="uid">novel-{today}</dc:Identifier>
            <dc:date>{today}</dc:date>
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


def gen_toc_ncx(post_list):
    section_list = []
    for novel_title, chapter_title_list in post_list:
        article_list = []
        for i, chapter_title in enumerate(chapter_title_list):
            article_list.append(f'''
            <navPoint class="article">
                <navLabel>
                    <text>{chapter_title}</text>
                </navLabel>
                <content src="html/{novel_title}-{i}.html#title1" />
            </navPoint>''')
        article = "\n".join(article_list)

        section_list.append(f'''
        <navPoint class="section">
            <navLabel>
                <text>{novel_title}</text>
            </navLabel>
            <content src="html/{novel_title}-0.html#section1" />
            {article}
        </navPoint>''')
    section = "\n".join(section_list)

    today = datetime.strftime(datetime.today(), '%Y-%m-%d')

    toc = f'''
    <?xml version='1.0' encoding='utf-8'?>
    <!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
    <ncx xmlns:mbp="http://mobipocket.com/ns/mbp" xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="en-GB">
        <head>
            <meta content="novel-{today}" name="dtb:uid" />
            <meta content="2" name="dtb:depth" />
            <meta content="0" name="dtb:totalPageCount" />
            <meta content="0" name="dtb:maxPageNumber" />
        </head>
        <docTitle>
            <text>GitHub Push</text>
        </docTitle>
        <navMap>
            <navPoint class="periodical">
                <navLabel>
                    <text>目录</text>
                </navLabel>
                <content src="html/toc.html" />
                {section}
            </navPoint>
        </navMap>
    </ncx>'''

    write_file("toc.ncx", toc)


def gen_toc_html(post_list):
    section_list = []
    for novel_title, chapter_title_list in post_list:
        article_list = []
        for i, chapter_title in enumerate(chapter_title_list):
            article_list.append(
                f"<li><a href='{novel_title}-{i}.html'>{chapter_title}</a></li>"
            )
        article = "\n".join(article_list)

        section_list.append(f'''
        <h4 height="1em">{novel_title}</h4>
        <ul>
            {article}
        </ul>''')
    section = "\n".join(section_list)

    toc = f'''
    <html>
        <head>
            <meta content="text/html; charset=utf-8" http-equiv="Content-Type"/>
            <title>目录</title>
        </head>
        <body>
            <h1>目录</h1>
            {section}
        </body>
    </html>'''

    write_file("html/toc.html", toc)


if __name__ == "__main__":
    os.mkdir("html")

    novel_list = load_json("novel_list.json")

    get_novel_list(novel_list)

    dump_json(novel_list, "novel_list.json")
