import time
from typing import List


class Article():

    def __init__(self, id: str, title: str, description: str):
        self.id = id
        self.title = title
        self.description = description

    def write_to_html(self, content: str):
        html = f'''
        <html lang="en" xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
            <head>
                <meta content="http://www.w3.org/1999/xhtml; charset=utf-8" http-equiv="Content-Type" />
                <title>{self.title}</title>
            </head>
            <body>
                <div id="section1"></div>
                <h1 id="title1" height="1em">
                    <font size="7">
                        <b>{self.title}</b>
                    </font>
                </h1>
                <br>
                {content}
            </body>
        </html>'''

        filename = f"html/{self.id}.html"
        with open(filename, mode='w', encoding="utf-8") as f:
            f.write(html)

    def to_opf(self):
        item = f"<item href='html/{self.id}.html' media-type='application/xhtml+xml' id='{self.id}'/>"
        itemref = f"<itemref idref='{self.id}'/>"
        return item, itemref

    def to_toc_ncx(self):
        return f'''
        <navPoint class="article">
            <navLabel>
                <text>{self.title}</text>
            </navLabel>
            <content src="html/{self.id}.html#title1" />
            <mbp:meta name="description">{self.description}</mbp:meta>
        </navPoint>'''

    def to_toc_html(self):
        return f"<li><a href='{self.id}.html'>{self.title}</a></li>"


class Section():

    def __init__(self, title: str):
        self.title = title
        self.article_list: List[Article] = []

    def append_article(self, article: Article):
        self.article_list.append(article)

    def to_toc_ncx(self):
        toc = "\n".join([
            article.to_toc_ncx() for article in self.article_list
        ])
        return f'''
        <navPoint class="section">
            <navLabel>
                <text>{self.title}</text>
            </navLabel>
            <content src="html/{self.article_list[0].id}.html#section1" />
            {toc}
        </navPoint>'''

    def to_toc_html(self):
        toc = "\n".join([
            article.to_toc_html() for article in self.article_list
        ])
        return f'''
        <h4 height="1em">{self.title}</h4>
        <ul>
            {toc}
        </ul>'''


class Magazine():

    def __init__(self, title: str):
        self.title = title
        self.section_list: List[Section] = []
        self.id = time.time_ns()
        self.now = time.strftime("%Y-%m-%d")

    def append_section(self, section: Section):
        if len(section.article_list) > 0:
            self.section_list.append(section)

    def write_to_opf(self):
        item, itemref = map(
            lambda list: "\n".join(list),
            zip(*(
                article.to_opf() for section in self.section_list for article in section.article_list
            ))
        )

        opf = f'''
        <?xml version='1.0' encoding='utf-8'?>
        <package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="{self.id}">
        <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
            <dc-metadata>
                <dc:title>{self.title} {self.now}</dc:title>
                <dc:language>zh-CN</dc:language>
                <dc:subject>杂志</dc:subject>
                <dc:Identifier id="uid">{self.id}</dc:Identifier>
                <dc:date>{self.now}</dc:date>
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

        with open("content.opf", mode='w', encoding="utf-8") as f:
            f.write(opf)

    def write_toc_ncx(self):
        point = "\n".join([
            section.to_toc_ncx() for section in self.section_list
        ])
        toc = f'''
        <?xml version='1.0' encoding='utf-8'?>
        <!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
        <ncx xmlns:mbp="http://mobipocket.com/ns/mbp" xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="en-GB">
            <head>
                <meta content="{self.id}" name="dtb:uid" />
                <meta content="2" name="dtb:depth" />
                <meta content="0" name="dtb:totalPageCount" />
                <meta content="0" name="dtb:maxPageNumber" />
            </head>
            <docTitle>
                <text>{self.title}</text>
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

        with open("toc.ncx", mode='w', encoding="utf-8") as f:
            f.write(toc)

    def write_toc_html(self):
        ul = "\n".join([
            section.to_toc_html() for section in self.section_list
        ])
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

        with open("html/toc.html", mode='w', encoding="utf-8") as f:
            f.write(toc)
