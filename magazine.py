import time
from typing import List


class Article():

    def __init__(self, id: str, title: str, description: str):
        self._id = id
        self._title = title
        self._description = description

    def _to_opf(self):
        item = f"<item href='html/{self._id}.html' media-type='application/xhtml+xml' id='{self._id}'/>"
        itemref = f"<itemref idref='{self._id}'/>"
        return item, itemref

    def _to_toc_ncx(self):
        return f'''
        <navPoint class="article">
            <navLabel>
                <text>{self._title}</text>
            </navLabel>
            <content src="html/{self._id}.html#title1" />
            <mbp:meta name="description">{self._description}</mbp:meta>
        </navPoint>'''

    def _to_toc_html(self):
        return f"<li><a href='{self._id}.html'>{self._title}</a></li>"

    def write_to_html(self, content: str):
        html = f'''
            <html lang="en" xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
                <head>
                    <meta content="http://www.w3.org/1999/xhtml; charset=utf-8" http-equiv="Content-Type" />
                    <title>{self._title}</title>
                </head>
                <body>
                    <div id="section1"></div>
                    <h1 id="title1" height="1em">
                        <font size="7">
                            <b>{self._title}</b>
                        </font>
                    </h1>
                    <br>
                    {content}
                </body>
            </html>'''

        filename = f"html/{self._id}.html"
        with open(filename, mode='w', encoding="utf-8") as f:
            f.write(html)


class Section():

    def __init__(self, title: str):
        self._title = title
        self._article_list: List[Article] = []

    def __setitem__(self, key, value):
        self._article_list[key] = value

    def __getitem__(self, key):
        return self._article_list[key]

    def __delitem__(self, key):
        del self._article_list[key]

    def __len__(self):
        return len(self._article_list)

    def __iter__(self):
        return self._article_list

    def __contains__(self, key):
        return key in self._article_list

    def __reversed__(self):
        return list(reversed(self._article_list))

    def append(self, article):
        if article:
            self._article_list.append(article)

    def _to_toc_ncx(self):
        if len(self._article_list) == 0:
            return ""

        toc = "\n".join([
            article._to_toc_ncx() for article in self._article_list
        ])
        return f'''
        <navPoint class="section">
            <navLabel>
                <text>{self._title}</text>
            </navLabel>
            <content src="html/{self._article_list[0]._id}.html#section1" />
            {toc}
        </navPoint>'''

    def _to_toc_html(self):
        if len(self._article_list) == 0:
            return ""

        toc = "\n".join([
            article._to_toc_html() for article in self._article_list
        ])
        return f'''
        <h4 height="1em">{self._title}</h4>
        <ul>
            {toc}
        </ul>'''


class Magazine():

    def __init__(self, title: str):
        self._title = title
        self._section_list: List[Section] = []
        self._id = time.time_ns()
        self._now = time.strftime("%Y-%m-%d")

    def __setitem__(self, key, value):
        self._section_list[key] = value

    def __getitem__(self, key):
        return self._section_list[key]

    def __delitem__(self, key):
        del self._section_list[key]

    def __len__(self):
        return len(self._section_list)

    def __iter__(self):
        return self._section_list

    def __contains__(self, key):
        return key in self._section_list

    def __reversed__(self):
        return list(reversed(self._section_list))

    def append(self, section: Section):
        if section:
            self._section_list.append(section)

    def write_to_opf(self):
        item, itemref = map(
            lambda list: "\n".join(list),
            zip(*(
                article._to_opf() for section in self._section_list for article in section._article_list
            ))
        )

        opf = f'''
        <?xml version='1.0' encoding='utf-8'?>
        <package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="{self._id}">
        <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
            <dc-metadata>
                <dc:title>{self._title} {self._now}</dc:title>
                <dc:language>zh-CN</dc:language>
                <dc:subject>杂志</dc:subject>
                <dc:Identifier id="uid">{self._id}</dc:Identifier>
                <dc:date>{self._now}</dc:date>
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
            section._to_toc_ncx() for section in self._section_list
        ])
        toc = f'''
        <?xml version='1.0' encoding='utf-8'?>
        <!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
        <ncx xmlns:mbp="http://mobipocket.com/ns/mbp" xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="en-GB">
            <head>
                <meta content="{self._id}" name="dtb:uid" />
                <meta content="2" name="dtb:depth" />
                <meta content="0" name="dtb:totalPageCount" />
                <meta content="0" name="dtb:maxPageNumber" />
            </head>
            <docTitle>
                <text>{self._title}</text>
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
            section._to_toc_html() for section in self._section_list
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
