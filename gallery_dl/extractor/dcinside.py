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
    pattern = BASE_PATTERN + r"(mgallery/)?(mini/)?board/view/\?id=(\w+)&no=(\d+)"
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


# class NaverBlogExtractor(NaverBase, Extractor):
#     """Extractor for a user's blog on blog.naver.com"""
#     subcategory = "blog"
#     categorytransfer = True
#     pattern = (r"(?:https?://)?blog\.naver\.com/"
#                r"(?:PostList.nhn\?(?:[^&#]+&)*blogId=([^&#]+)|(\w+)/?$)")
#     example = "https://blog.naver.com/BLOGID"

#     def __init__(self, match):
#         Extractor.__init__(self, match)
#         self.blog_id = match.group(1) or match.group(2)

#     def items(self):

#         # fetch first post number
#         url = "{}/PostList.nhn?blogId={}".format(self.root, self.blog_id)
#         post_num = text.extract(
#             self.request(url).text, 'gnFirstLogNo = "', '"',
#         )[0]

#         # setup params for API calls
#         url = "{}/PostViewBottomTitleListAsync.nhn".format(self.root)
#         params = {
#             "blogId"             : self.blog_id,
#             "logNo"              : post_num or "0",
#             "viewDate"           : "",
#             "categoryNo"         : "",
#             "parentCategoryNo"   : "",
#             "showNextPage"       : "true",
#             "showPreviousPage"   : "false",
#             "sortDateInMilli"    : "",
#             "isThumbnailViewType": "false",
#             "countPerPage"       : "",
#         }

#         # loop over all posts
#         while True:
#             data = self.request(url, params=params).json()

#             for post in data["postList"]:
#                 post["url"] = "{}/PostView.nhn?blogId={}&logNo={}".format(
#                     self.root, self.blog_id, post["logNo"])
#                 post["_extractor"] = NaverPostExtractor
#                 yield Message.Queue, post["url"], post

#             if not data["hasNextPage"]:
#                 return
#             params["logNo"] = data["nextIndexLogNo"]
#             params["sortDateInMilli"] = data["nextIndexSortDate"]
