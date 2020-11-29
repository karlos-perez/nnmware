# nnmware(c)2012-2020

from __future__ import unicode_literals
from xml.etree.ElementTree import SubElement


def get_queryset_category(obj, main_obj, cat_obj, active=False):
    slug = obj.kwargs['slug']
    if 'parent_slugs' in obj.kwargs:
        parent_slugs = obj.kwargs['parent_slugs']
        parent = cat_obj.objects.all().filter(slug=parent_slugs[:-1])[0].id
        q = cat_obj.objects.get(parent=parent, slug=slug)
    else:
        q = cat_obj.objects.get(slug=slug, parent__isnull=True)
    array_child = [q.id]
    children = q.get_all_children()
    for child in children:
        array_child.append(child.pk)
    if active:
        return main_obj.objects.active().select_related().filter(category__in=array_child), q
    return main_obj.objects.select_related().filter(category__in=array_child), q


def recurse_for_children(current_node, parent_node, show_empty=True):
    child_count = current_node.children.count()

    if show_empty or child_count > 0:
        temp_parent = SubElement(parent_node, 'li')
        attrs = {'href': current_node.get_absolute_url(), 'id': 'category' + str(int(current_node.pk))}
        link = SubElement(temp_parent, 'a', attrs)
        link.text = current_node.name
        counter = current_node.obj_active_set.count()
        for child in current_node.get_all_children():
            counter += child.obj_active_set.count()
        if counter > 0:
            count_txt = SubElement(temp_parent, 'sup', {'class': 'amount'})
            count_txt.text = str(counter)
        if child_count > 0:
            new_parent = SubElement(temp_parent, 'ul')
            children = current_node.children.all()
            for child in children:
                recurse_for_children(child, new_parent)


def recurse_for_children_with_span(current_node, parent_node, show_empty=True):
    child_count = current_node.children.count()

    if show_empty or child_count > 0:
        temp_parent = SubElement(parent_node, 'li')
        attrs = {'href': current_node.get_absolute_url(), 'id': 'category' + str(int(current_node.pk))}
        link = SubElement(temp_parent, 'a', attrs)
        span = SubElement(link, 'span')
        span.text = current_node.name
        counter = current_node.obj_active_set.count()
        for child in current_node.get_all_children():
            counter += child.obj_active_set.count()
        if counter > 0:
            count_txt = SubElement(link, 'i')
            count_txt.text = str(counter)
        if child_count > 0:
            new_parent = SubElement(temp_parent, 'ul')
            children = current_node.children.all()
            for child in children:
                recurse_for_children_with_span(child, new_parent)

MONTH = ['Jan', 'Feb', 'Mar', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
         'Oct', 'Nov', 'Dec']


def recurse_for_date(app, _year, current_node, parent_node):
    y_parent = SubElement(parent_node, 'li')
    attrs = {'href': "/%s/%s" % (app, _year)}
    link = SubElement(y_parent, 'a', attrs)
    link.text = str(_year)
    new_parent = SubElement(y_parent, 'ul')
    for _month in MONTH:
        if _month in current_node.keys():
            m_parent = SubElement(new_parent, 'li')
            attrs = {'href': ("/%s/%s/%s" % (app, _year, _month))}
            link = SubElement(m_parent, 'a', attrs)
            link.text = _month
            day_parent = SubElement(m_parent, 'ul')
            _days = current_node[_month]
            _days.sort()
            for _day in _days:
                d_parent = SubElement(day_parent, 'li')
                attrs = {'href': ("/%s/%s/%s/%s" % (app, _year, _month, _day))}
                link = SubElement(d_parent, 'a', attrs)
                link.text = _day


def create_archive_list(_query):
    archive_list = {}

    for item in _query:
        if item.created_date.year not in archive_list.keys():
            archive_list[item.created_date.year] = {}
        else:
            pass

    for entry in _query:
        for item in archive_list.keys():
            _year = entry.created_date.year
            if _year == item:
                _month = entry.created_date.strftime("%b")
                if _month not in archive_list[item].keys():
                    archive_list[item][_month] = []

    for entry in _query:
        _year = entry.created_date.year
        _month = entry.created_date.strftime("%b")
        _day = entry.created_date.strftime("%d")
        if _day not in archive_list[_year][_month]:
            archive_list[_year][_month].append(_day)

    return archive_list


def create_userdate_list(_query):
    archive_list = {}

    for item in _query:
        if item.date_joined.year not in archive_list.keys():
            archive_list[item.date_joined.year] = {}
        else:
            pass

    for entry in _query:
        for item in archive_list.keys():
            _year = entry.date_joined.year
            if _year == item:
                _month = entry.date_joined.strftime("%b")
                if _month not in archive_list[item].keys():
                    archive_list[item][_month] = []

    for entry in _query:
        _year = entry.date_joined.year
        _month = entry.date_joined.strftime("%b")
        _day = entry.date_joined.strftime("%d")
        if _day not in archive_list[_year][_month]:
            archive_list[_year][_month].append(_day)

    return archive_list


def recurse_for_children_select(current_node, parent_node, show_empty=True):
    child_count = current_node.children.count()

    if show_empty or child_count > 0:
        temp_parent = SubElement(parent_node, 'li')
        category_pk = SubElement(temp_parent, 'i')
        category_pk.text = str(int(current_node.pk))
        span = SubElement(temp_parent, 'span')
        span.text = current_node.name
        if child_count > 0:
            new_parent = SubElement(temp_parent, 'ul')
            children = current_node.children.all()
            for child in children:
                recurse_for_children_select(child, new_parent)
