# -*- coding: utf-8 -*-

# Copyright 2019-2023 Mike Fährmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Extractors for https://gall.dcinside.com/"""

from .common import GalleryExtractor, Extractor, Message
from .. import text

BASE_PATTERN = r"(?:https?://)?gall\.dcinside\.com/"

class DcInsideBase():
    """Base class for dcinside extractors"""
    category = "dcinside"
    root = "https://gall.dcinside.com"


class DcPostExtractor(DcInsideBase, GalleryExtractor):
    """Extractor for posts on gall.dcinside.com"""
    subcategory = "post"
    filename_fmt = "{num:>03}.{extension}"
    directory_fmt = ("{category}", "{board[id]}",
                     "{post[date]:%Y-%m-%d} {post[title]}")
    archive_fmt = "{blog[id]}_{post[num]}_{num}"
    pattern = BASE_PATTERN + \
                r"(mgallery/)?(mini/)?board/view/\?id=(\w+)&no=(\d+)"
    example = "https://gall.dcinside.com/board/view/?id=BOARDID&no=12345"

    def __init__(self, match):
        mgal = match.group(1)
        mini = match.group(2)


        self.board_id = match.group(3)
        self.no = match.group(4)
        GalleryExtractor.__init__(self, match, match[0])

    def metadata(self, page):
        extr = text.extract_from(page)
        data = {
            "post": {
                "title"      : extr('"og:title" content="', '"'),
                "description": extr('"og:description" content="', '"'),
                "num"        : text.parse_int(self.no),
            },
            "board": {
                "id"         : self.board_id,
            },
        }
        data["post"]["date"] = text.parse_datetime(
                                extr('"gall_date" title="', '"'),
                                  "%Y-%m-%d %H:%M:%S")
        return data

    def images(self, page):

        php_images = [
            "https://dcimg" + url
            for url in text.extract_iter(page, 'img src="https://dcimg', '"')
        ]
        
        # check for gifs not following image format above
        php_gifs = [
            url
            for url in text.extract_iter(page, 'data-src="', '"')
        ]

        # remove duplicate gifs
        php_merged = list( dict.fromkeys(php_images + php_gifs))
        images = [(img, {'extension': 'jpg'}) for img in php_merged]

        # collect php urls for videos uploaded to dcinside
        php_movies = [
            "https://gall.dcinside.com/board/movie/movie_view?no="
            + url for url in text.extract_iter(page,
            'src="https://gall.dcinside.com/board/movie/movie_view?no=', '"')
        ]

        # videos need their php page loaded first
        videos = []
        if php_movies:
            for p in php_movies:
                with self.request(p) as url:
                    murl = text.extr(url.text,
                            "input type = 'hidden' value ='", "'")
                    videos.append((murl, {'extension': 'mp4'}))

        # collect embeded youtube video urls
        embeded_movies = [
            'ytdl:https://www.youtube.com/watch?v=' + 
            url for url in text.extract_iter(page,
            'embed src="https://www.youtube.com/embed/', '?')
        ]
        embeded = [(e, None) for e in embeded_movies]

        return images + videos + embeded


class DcBoardExtractor(DcInsideBase, Extractor):
    """Extractor for a board on gall.dcinside.com"""
    subcategory = "board"
    categorytransfer = True
    pattern = BASE_PATTERN + \
    r"(mgallery/)?(mini/)?board/lists/\?id=(\w+)(&page=(\d+))?"
    example = "https://gall.dcinside.com/board/view/?id=BOARDID&no=12345"

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.url = match.group(0)
        self.mgal = match.group(1)
        self.mini = match.group(2)
        self.board_id = match.group(3)
        self.page_index = int(match.group(5)) if match.group(5) else 1

    def items(self):

        # fetch first post number
        board_url = self.url
        
        base_post_url = 'https://gall.dcinside.com/'
        base_post_url += self.mgal if self.mgal else ""
        base_post_url += self.mini if self.mini else ""
        
        base_list_url = base_post_url + f'board/lists/?id='
        base_post_url = base_post_url + f'board/view/?id='
        total_pages = None

        page = self.request(board_url).text
        total_pages = int(text.extr(page, 'total_page">', '<', 1))


        # loop over all posts
        while True:
            page = self.request(board_url).text
            # f = open("page.html", "x")
            # f.write()
            if self.mgal:
                print(self.mgal)
                post_links = [link for link in text.extract_iter(page, 
                    f'href="/{self.mgal}board/view/?id=' , '"')]
            elif self.mini:
                post_links = [link for link in text.extract_iter(page, 
                    f'href="/{self.mini}board/view/?id=' , '"')]
            else:
                post_links = [link for link in text.extract_iter(page, 
                    f'href="/board/view/?id=' , '"')]
            
            for link in post_links:
                post = {}
                post["url"] = base_post_url + link
                post["_extractor"] = DcPostExtractor
                yield Message.Queue, post["url"], post

            if self.page_index >= total_pages:
                return

            # go to next page
            self.page_index += 1
            board_url = base_list_url + \
                 f"{self.board_id}&page={str(self.page_index)}"
