# nnmware(c)2012-2020

from __future__ import unicode_literals

from django.conf.urls import url

from nnmware.apps.board.views import BoardYearList, BoardDayList, BoardMonthList
from nnmware.apps.board.views import BoardList, BoardUserList, BoardCategory, \
    BoardDetail
from nnmware.apps.board.views import BoardSearch
from nnmware.apps.board.views import BoardEdit, BoardAdd


urlpatterns = [
    url(r'^search/$', BoardSearch.as_view(), name='board_search'),
    url(r'^(?P<year>\d{4})/$', BoardYearList.as_view(), name='board_year'),
    url(r'^(?P<year>\d{4})/(?P<month>\w{3})/$', BoardMonthList.as_view(), name='board_month'),
    url(r'^(?P<year>\d{4})/(?P<month>\w{3})/(?P<day>\d{1,2})/$', BoardDayList.as_view(), name='board_day'),
    url(r'^$', BoardList.as_view(), name="board_index"),
    url(r'^my/$', BoardUserList.as_view(), name="board_my"),
    url(r'^category/(?P<parent_slugs>[-\w]+/)*(?P<slug>[-\w]+)/$', BoardCategory.as_view(), name='board_category'),
    url(r'^(?P<pk>[0-9]+)/$', BoardDetail.as_view(), name="board_one"),
    url(r'^add/$', BoardAdd.as_view(), name="board_add"),
    url(r'^edit/(?P<pk>[0-9]+)/$', BoardEdit.as_view(), name="board_edit")
]
