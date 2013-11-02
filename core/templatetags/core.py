# -*- coding: utf-8 -*-
from datetime import timedelta
import re
from xml.etree.ElementTree import Element, SubElement, tostring
from django.template import Library, Node, TemplateSyntaxError, Variable, VariableDoesNotExist, loader
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.safestring import mark_safe
from django.db.models import Count, Sum
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.timezone import now
from nnmware.core.models import Tag, Video, Nnmcomment, Message
from nnmware.core.imgutil import make_thumbnail, get_image_size, make_watermark
from nnmware.core.abstract import Tree
from nnmware.core.data import *


register = Library()


def video_links(context, mode='random'):
    user = context["user"]
    try:
        category = context['category_panel']
    except KeyError:
        category = None
    videos = Video.objects.filter(created_date__gte=now() - timedelta(days=1))
    result = videos
    if user.is_authenticated():
        result = result.exclude(users_viewed=user)
    if category is not None:
        result = result.filter(tags=category)
    if mode == 'popular':
        result = list(result.order_by('-viewcount')[:2])
    else:
        result = list(result.order_by('?')[:2])
    if len(result) < 2:
        result.extend(list(videos.order_by('?')))
    if len(result) < 2:
        result.extend(list(Video.objects.order_by('?')))
    return result[:2]


@register.assignment_tag(takes_context=True)
def video_popular_links(context):
    return video_links(context, mode='popular')


@register.assignment_tag(takes_context=True)
def video_other_links(context):
    return video_links(context)


@register.assignment_tag
def tag_links():
    # Return most popular 10 Tags
    return Tag.objects.annotate(video_count=Count('video')).order_by('-video_count')[:10]


@register.assignment_tag
def tags_step2():
    # Return most popular 10 Tags
    return Tag.objects.annotate(video_count=Count('video')).order_by('-video_count')[:9]


@register.assignment_tag(takes_context=True)
def users_step2(context):
    request = context['request']
    # Return most popular 6 users
    return get_user_model().objects.exclude(username=request.user.username).annotate(
        video_count=Count('video')).order_by('-video_count')[:6]


@register.simple_tag
def video_views():
    return Video.objects.aggregate(Sum('viewcount'))['viewcount__sum']


@register.tag
def do_get_tree_path(token):
    result = ''
    for name, link in token.get_full_path():
        result += '<a href="%s">%s</a>' % name, link
    return result


@register.filter
def multiply(value, times):
    return value * times


@register.filter
def to_2_digits(value):
    return format(value, '.2f')


@register.filter
def inline_truncate(value, size):
    """Truncates a string to the given size placing the ellipsis at the middle of the string"""
    new = ''
    for w in value.split():
        if len(w) > size > 3:
            start = (size - 3) / 2
            end = (size - 3) - start
            new += ' ' + w[0:start] + '...' + w[-end:]
        else:
            new += ' ' + w[0:size]
    return new


inline_truncate.is_safe = True


@register.filter
def inline_word(value, size):
    """Append spaces in long word"""
    new = ''
    for w in value.split():
        if len(w) > size:
            while len(w) > size:
                new += w[:size]
                w = w[size:]
            new += ' ' + w
        else:
            new += ' ' + w
    return new


inline_word.is_safe = True


@register.filter
def latestdates(date):
    if now() - date < timedelta(hours=24):
        return 'red'
    else:
        return 'normal'


@register.filter
def short_urlize(url):
    if 'http://www.' in url:
        url_short = url[11:-1]
    elif 'http://' in url:
        url_short = url[7:-1]
    else:
        url_short = url
    result = "<a href='%s' target='_blank' >%s</a>" % (url, url_short)
    return mark_safe(result)


@register.filter
def sort_counter_quantity(val):
    return sorted(val, key=lambda x: x.allcount)


@register.filter
def sort_counter_money(val):
    return sorted(val, key=lambda x: x.fullmoney)


@register.filter
def sort_counter_effect(val):
    return sorted(val, key=lambda x: x.effect)

#######################################
### PAGINATOR TAG

LEADING_PAGE_RANGE_DISPLAYED = TRAILING_PAGE_RANGE_DISPLAYED = getattr(settings, 'PAGINATOR_RANGE_DISPLAYED', 10)
LEADING_PAGE_RANGE = TRAILING_PAGE_RANGE = 8
NUM_PAGES_OUTSIDE_RANGE = 2
ADJACENT_PAGES = 4


@register.assignment_tag(takes_context=True)
def paginator(context):
    """
    Paginator for CBV and paginate_by
    """
    num_pages = context["paginator"].num_pages
    curr_page_num = context["page_obj"].number
    in_leading_range = in_trailing_range = False
    pages_outside_leading_range = pages_outside_trailing_range = range(0)

    if num_pages <= LEADING_PAGE_RANGE_DISPLAYED:
        in_leading_range = in_trailing_range = True
        page_numbers = [n for n in range(1, num_pages + 1) if 0 < n <= num_pages]
    elif curr_page_num <= LEADING_PAGE_RANGE:
        in_leading_range = True
        page_numbers = [n for n in range(1, LEADING_PAGE_RANGE_DISPLAYED + 1) if 0 < n <= num_pages]
        pages_outside_leading_range = [n + num_pages for n in range(0, -NUM_PAGES_OUTSIDE_RANGE, -1)]
    elif curr_page_num > (num_pages - TRAILING_PAGE_RANGE):
        in_trailing_range = True
        page_numbers = [n for n in range(num_pages - TRAILING_PAGE_RANGE_DISPLAYED + 1, num_pages + 1) if
                        0 < n <= num_pages]
        pages_outside_trailing_range = [n + 1 for n in range(0, NUM_PAGES_OUTSIDE_RANGE)]
    else:
        page_numbers = [n for n in range(curr_page_num - ADJACENT_PAGES, curr_page_num + ADJACENT_PAGES + 1) if
                        0 < n <= num_pages]
        pages_outside_leading_range = [n + num_pages for n in range(0, -NUM_PAGES_OUTSIDE_RANGE, -1)]
        pages_outside_trailing_range = [n + 1 for n in range(0, NUM_PAGES_OUTSIDE_RANGE)]
    getvars = context['request'].GET.copy()
    if 'page' in getvars:
        del getvars['page']
    if len(getvars.keys()) > 0:
        new_getvars = "&%s" % getvars.urlencode()
    else:
        new_getvars = ''
    return {
        "getvars": new_getvars,
        "page_numbers": page_numbers,
        "in_leading_range": in_leading_range,
        "in_trailing_range": in_trailing_range,
        "pages_outside_leading_range": pages_outside_leading_range,
        "pages_outside_trailing_range": pages_outside_trailing_range
    }


@register.filter
def no_end_slash(value):
    if value[-1:] == '/':
        return value[:-1]
    else:
        return value


@register.filter
def phone_number(value):
    num = re.sub("[^0-9]", "", value)
    return '+' + num[:-10] + '(' + num[-10:-7] + ')' + num[-7:]


@register.filter
def icq_number(value):
    num = re.sub("[^0-9]", "", value)
    result = ''
    while len(num) > 3:
        result += num[:3]
        if len(num) > 3:
            result += '-'
        num = num[3:]
    result += num
    return result


@register.filter
def url_target_blank(text):
    return text.replace('<a ', '<a target="_blank" ')


url_target_blank.is_safe = True


def get_contenttype_kwargs(content_object):
    """
    Gets the basic kwargs necessary for almost all of the following tags.
    """
    kwargs = {
        'content_type': ContentType.objects.get_for_model(content_object).id,
        'object_id': getattr(content_object, 'pk', getattr(content_object, 'id')),
    }
    return kwargs


@register.simple_tag
def get_file_attach_url(content_object):
    kwargs = get_contenttype_kwargs(content_object)
    return reverse('doc_ajax', kwargs=kwargs)


@register.simple_tag
def get_image_attach_url(content_object):
    kwargs = get_contenttype_kwargs(content_object)
    return reverse('pic_ajax', kwargs=kwargs)


@register.simple_tag
def get_img_attach_url(content_object):
    kwargs = get_contenttype_kwargs(content_object)
    return reverse('img_ajax', kwargs=kwargs)


@register.simple_tag
def get_addon_image_attach_url(content_object):
    kwargs = get_contenttype_kwargs(content_object)
    return reverse('addon_img_ajax', kwargs=kwargs)


@register.simple_tag
def get_comment_url(content_object, parent=None):
    """
    Given an object and an optional parent, this tag gets the URL to POST to for the
    creation of new ``ThreadedComment`` objects.
    """
    kwargs = get_contenttype_kwargs(content_object)
    if parent:
        if not isinstance(parent, Nnmcomment):
            raise TemplateSyntaxError
        kwargs.update({'parent_id': getattr(parent, 'pk', getattr(parent, 'id'))})
        return reverse('comment_parent_add', kwargs=kwargs)
    else:
        return reverse('comment_add', kwargs=kwargs)


@register.simple_tag
def get_follow_url(content_object):
    kwargs = get_contenttype_kwargs(content_object)
    return reverse('follow', kwargs=kwargs)


@register.tag
def get_j_comment_tree(token):
    """
    Gets a tree (list of objects ordered by preorder tree traversal, and with an
    additional ``depth`` integer attribute annotated onto each ``ThreadedComment``.
    """
    try:
        split = token.split_contents()
    except ValueError:
        raise TemplateSyntaxError
    if len(split) == 5:
        return CommentTreeNode(split[2], split[4], split[3])
    elif len(split) == 6:
        return CommentTreeNode(split[2], split[5], split[3])
    else:
        raise TemplateSyntaxError


class CommentTreeNode(Node):
    def __init__(self, content_object, context_name, tree_root):
        self.content_object = Variable(content_object)
        self.tree_root = Variable(tree_root)
        self.tree_root_str = tree_root
        self.context_name = context_name

    def render(self, context):
        content_object = self.content_object.resolve(context)
        try:
            tree_root = self.tree_root.resolve(context)
        except VariableDoesNotExist:
            if self.tree_root_str == 'as':
                tree_root = None
            else:
                try:
                    tree_root = int(self.tree_root_str)
                except ValueError:
                    tree_root = self.tree_root_str
        context[self.context_name] = Nnmcomment.public.get_tree(content_object, root=tree_root)
        return ''


@register.tag
def get_comment_count(token):
    """
    Gets a count of how many ThreadedComment objects are attached to the given
    object.
    """
    try:
        split = token.split_contents()
    except ValueError:
        raise TemplateSyntaxError
    if split[1] != 'for' or split[3] != 'as':
        raise TemplateSyntaxError
    return NnmcommentCountNode(split[2], split[4])


class NnmcommentCountNode(Node):
    def __init__(self, content_object, context_name):
        self.content_object = Variable(content_object)
        self.context_name = context_name

    def render(self, context):
        content_object = self.content_object.resolve(context)
        context[self.context_name] = Nnmcomment.public.all_for_object(content_object).count()
        return ''


@register.filter
def nerd_comment(value):
    return 59 * value


@register.tag
def get_latest_comments(token):
    """
    Gets the latest comments by date_submitted.
    """
    try:
        split = token.split_contents()
    except ValueError:
        raise TemplateSyntaxError
    if len(split) != 4:
        raise TemplateSyntaxError
    if split[2] != 'as':
        raise TemplateSyntaxError
    return LatestCommentsNode(split[1], split[3])


class LatestCommentsNode(Node):
    def __init__(self, num, context_name):
        self.num = num
        self.context_name = context_name

    def render(self, context):
        comments = Nnmcomment.objects.order_by('-created_date')[:self.num]
        context[self.context_name] = comments
        return ''


@register.tag
def get_user_comments(token):
    """
    Gets all comments submitted by a particular user.
    """
    try:
        split = token.split_contents()
    except ValueError:
        raise TemplateSyntaxError
    if len(split) != 5:
        raise TemplateSyntaxError
    return UserCommentsNode(split[2], split[4])


class UserCommentsNode(Node):
    def __init__(self, user, context_name):
        self.user = Variable(user)
        self.context_name = context_name

    def render(self, context):
        user = self.user.resolve(context)
        context[self.context_name] = user.jcomment_set.all()
        return ''


@register.tag
def get_user_comment_count(token):
    """
    Gets the count of all comments submitted by a particular user.
    """
    try:
        split = token.split_contents()
    except ValueError:
        raise TemplateSyntaxError
    if len(split) != 5:
        raise TemplateSyntaxError
    return UserCommentCountNode(split[2], split[4])


class UserCommentCountNode(Node):
    def __init__(self, user, context_name):
        self.user = Variable(user)
        self.context_name = context_name

    def render(self, context):
        user = self.user.resolve(context)
        context[self.context_name] = user.jcomment_set.all().count()
        return ''

##################################################
## IMAGE RELATED FILTERS ##


@register.filter
def thumbnail(url, args=''):
    """ Returns thumbnail URL and create it if not already exists.
Usage::

    {{ url|thumbnail:"width=10,height=20" }}
    {{ url|thumbnail:"width=10" }}
    {{ url|thumbnail:"height=20,aspect=1" }}

Image is **proportionally** resized to dimension which is no greater than ``width x height``.

Thumbnail file is saved in the same location as the original image
and his name is constructed like this::

    %(dirname)s/%(basename)s_t[_w%(width)d][_h%(height)d].%(extension)s

or if only a width is requested (to be compatibile with admin interface)::

    %(dirname)s/%(basename)s_t%(width)d.%(extension)s

"""
    if url is None:
        return None
    kwargs = {}
    if args:
        if ',' not in args:
            # ensure at least one ','
            args += ','
        for arg in args.split(','):
            arg = arg.strip()
            if arg == '':
                continue
            kw, val = arg.split('=', 1)
            kw = kw.lower().encode('ascii')
            try:
                val = int(val)  # convert all ints
            except ValueError:
                raise TemplateSyntaxError
            kwargs[kw] = val

    if ('width' not in kwargs) and ('height' not in kwargs):
        raise TemplateSyntaxError

    ret = make_thumbnail(url, **kwargs)
    if ret is None:
        ret = url

    if not ret.startswith(settings.MEDIA_URL):
        ret = settings.MEDIA_URL + ret

    return ret


@register.filter
def image_width(url):
    width, height = get_image_size(url)
    return width


@register.filter
def image_height(url):
    width, height = get_image_size(url)
    return height


@register.filter
def watermark(url, arg=''):
    if url is None:
        return None
    try:
        if arg == 'center':
            ret = make_watermark(url, align='center')
        else:
            ret = make_watermark(url)
    except:
        ret = url
    if ret is None:
        ret = url
    if not ret.startswith(settings.MEDIA_URL):
        ret = settings.MEDIA_URL + ret
    return ret

######################################################
###  MENU RELATED BLOCK

#from nnmware.apps.forum.models import Category


def recurse_for_children(current_node, parent_node, show_empty=True):
    child_count = current_node.children.count()

    if show_empty or child_count > 0:
        temp_parent = SubElement(parent_node, 'li')
        attrs = {'href': current_node.get_absolute_url()}
        link = SubElement(temp_parent, 'a', attrs)
        link.text = current_node.name
        myval = SubElement(temp_parent, 'b')
        myval.text = " %s/%s" % (current_node.get_updated_count, current_node.get_valid_count)
        if child_count > 0:
            new_parent = SubElement(temp_parent, 'ul')
            children = current_node.children.all()
            for child in children:
                recurse_for_children(child, new_parent)


#@register.simple_tag
#def tree(app=None):
#    exec("""from nnmware.apps.%s.models import Category""" % app)
#    html = Element('root')
#    for node in Category.objects.all():
#        if not node.parent:
#            recurse_for_children(node, html)
#    return tostring(html, 'utf-8')

#@register.simple_tag
#def category_tree_series():
#    root = Element("root")
#    for cats in Category.objects.all().filter(slug='series'):
#        if not cats.parent:
#            recurse_for_children(cats, root)
#    return tostring(root, 'utf-8')


@register.simple_tag
def menu(app=None):
    if app == 'topic':
        from nnmware.apps.topic.models import Category as MenuCategory
    elif app == 'board':
        from nnmware.apps.board.models import Category as MenuCategory
    elif app == 'shop':
        from nnmware.apps.shop.models import ProductCategory as MenuCategory
    elif app == 'article':
        from nnmware.apps.article.models import Category as MenuCategory
    else:
        pass

    if 1 > 0:  # try:
        html = Element("ul")
        for node in MenuCategory.objects.all():
            if not node.parent:
                recurse_for_children(node, html)
        return tostring(html, 'utf-8')

#    except:
#        return 'error'


@register.simple_tag
def category_tree_series():
    root = Element("ul")
    for cats in Tree.objects.all().filter(slug='series'):
        if not cats.parent:
            recurse_for_children(cats, root)
    return tostring(root, 'utf-8')


@register.simple_tag
def menu_user(app=None):
    if app == 'users':
        Alldata = get_user_model()
    query = Alldata.objects.all().order_by('-date_joined')
    objects_years_dict = create_userdate_list(query)
    html = Element("ul")
    keyList = objects_years_dict.keys()
    for key in keyList:
        recurse_for_date(app, key, objects_years_dict[key], html)
    return tostring(html, 'utf-8')


@register.simple_tag
def menu_date(app=None):
    if app == 'article':
        from nnmware.apps.article.models import Article as Alldata
    elif app == 'topic':
        from nnmware.apps.topic.models import Topic as Alldata
    elif app == 'pic':
        from nnmware.core.models import Pic as Alldata
    elif app == 'doc':
        from nnmware.core.models import Doc as Alldata
    query = Alldata.objects.all().order_by('-created_date')
    objects_years_dict = create_archive_list(query)
    html = Element("ul")
    keyList = objects_years_dict.keys()
    for key in keyList:
        recurse_for_date(app, key, objects_years_dict[key], html)
    return tostring(html, 'utf-8')


r_nofollow = re.compile('<a (?![^>]*nofollow)')
s_nofollow = '<a rel="nofollow" '


@register.filter
def nofollow(value):
    return r_nofollow.sub(s_nofollow, value)


if settings.DEBUG:
    @register.inclusion_tag('core/debug.html')
    def site_debug():
        import re
        from django.db import connection

        queries = connection.queries
        query_time = 0
        query_count = 0
        for query in queries:
            query_time += float(query['time'])
            query_count += int(1)
        return {
            'query_time': query_time,
            'query_count': query_count}
else:
    @register.simple_tag
    def site_debug():
        return ''


@register.filter
def datelinks(value):
    """
    This filter formats date as "day.month.year" and sets links to
    day/month/year-based archives.

    For correct work there must be defined urls with names:
        - day_archive
        - month_archive
        - year_archive
    """
    return get_links(value.strftime('%d'), value.strftime('%m'), value.year)


@register.filter
def datelinks_by_string(value):
    """
    This filter creates from date formatted as "day.month.year" string with
    links to day/month/year-based archives.

    For correct work there must be defined urls with names:
        - day_archive
        - month_archive
        - year_archive
    """
    r = r'^(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4})$'
    try:
        day, month, year = re.match(r, value).groups()
    except AttributeError:
        return value
    return get_links(day, month, year)


def get_links(day, month, year):
    return mark_safe(loader.render_to_string('core/datelinks.html', {'year': year, 'month': month, 'day': day}))


@register.filter
def get_month(date):
    return date.strftime('%m')


@register.filter
def get_day(date):
    return date.strftime('%d')


@register.assignment_tag(takes_context=True)
def inbox_count(context):
    try:
        user = context['user']
        count = Message.objects.inbox_for(user).count()
    except (KeyError, AttributeError):
        count = ''
    return "%s" % count


@register.assignment_tag(takes_context=True)
def inbox_unread(context):
    try:
        user = context['user']
        count = user.received_messages.filter(read_at__isnull=True, recipient_deleted_at__isnull=True).count()
    except (KeyError, AttributeError):
        count = ''
    return "%s" % count


@register.assignment_tag(takes_context=True)
def outbox_count(context):
    try:
        user = context['user']
        count = Message.objects.outbox_for(user).count()
    except (KeyError, AttributeError):
        count = ''
    return "%s" % count


@register.assignment_tag(takes_context=True)
def trash_count(context):
    try:
        user = context['user']
        count = Message.objects.trash_for(user).count()
    except (KeyError, AttributeError):
        count = ''
    return "%s" % count

#####################################################
### SMILES OLD

EMOTICONS = {
    'O:-)': 'angel_mini',
    '@}-&gt;--': 'rose_mini',
    '*HEART*': 'heart_mini',
    '*OK*': 'music_mini2'}


@register.filter
def smiles(value):
    """
    Smiles library
    """
    for key, val in EMOTICONS.items():
        value = value.replace(key, """<img src="/s/emo/%s.gif" />""" % val)
    return value


smiles.is_safe = True


@register.simple_tag
def sum_discount(amount, discount):
    result = amount * (100 - discount) / 100
    return result


@register.simple_tag(takes_context=True)
def get_paginator_value(context):
    result = context['request'].session.get('paginator', str(settings.PAGINATE_BY))
    return result


@register.assignment_tag(takes_context=True)
def shop_compare(context):
    request = context['request']
    try:
        return len(request.session['shop_compare'])
    except:
        return 0


@register.assignment_tag(takes_context=True)
def shop_compare_list(context):
    request = context['request']
    try:
        return request.session['shop_compare']
    except:
        return []


@register.assignment_tag(takes_context=True)
def path_without_i18n(context):
    request = context['request']
    return request.get_full_path()[4:]


@register.assignment_tag
def is_holiday(date):
    if date.isoweekday() in [6,7]:
        return True
    return False


class SetVarNode(Node):

    def __init__(self, var_name, var_value):
        self.var_name = var_name
        self.var_value = var_value

    def render(self, context):
        try:
            value = Variable(self.var_value).resolve(context)
        except VariableDoesNotExist:
            value = ""
        context[self.var_name] = value
        return u""

@register.tag
def set_var(parser, token):
    """
        {% set <var_name>  = <var_value> %}
    """
    parts = token.split_contents()
    if len(parts) < 4:
        raise TemplateSyntaxError("'set' tag must be of the form:  {% set <var_name>  = <var_value> %}")
    return SetVarNode(parts[1], parts[3])


class RepeatNode(Node):
    def __init__(self, nodelist, count_from, count_to):
        self.nodelist = nodelist
        self.count_from = Variable(count_from)
        self.count_to = Variable(count_to)

    def render(self, context):
        output = self.nodelist.render(context)
        return output * (int(self.count_from.resolve(context)) - int(self.count_to.resolve(context)))

@register.tag
def repeat(parser, token):
    bits = token.split_contents()

    if len(bits) != 3:
        raise TemplateSyntaxError('%r tag requires 2 argument.' % bits[0])
    count_from = bits[1]
    count_to = bits[2]
    nodelist = parser.parse(('endrepeat',))
    parser.delete_first_token()
    return RepeatNode(nodelist, count_from, count_to)

@register.assignment_tag
def multiply_2args(arg1, arg2):
    result = arg1 * arg2
    return result



