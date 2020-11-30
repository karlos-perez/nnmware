# nnmware(c)2012-2020

from __future__ import unicode_literals
from datetime import timedelta
from hashlib import sha1

from django.core.cache import cache
from django.db.models import Min, Count, Sum
from django.template import Library
from django.template.defaultfilters import stringfilter
from django.utils.timezone import now
from django.utils.translation import gettext as _

from nnmware.apps.address.models import City
from nnmware.apps.booking.models import Hotel, TWO_STAR, THREE_STAR, FOUR_STAR, FIVE_STAR, HotelOption, MINI_HOTEL, \
    PlacePrice, Availability, HOSTEL, APARTAMENTS, SettlementVariant, Room, RoomDiscount, STATUS_CHOICES
from nnmware.apps.money.models import ExchangeRate, Currency
from nnmware.core.maps import distance_to_object
from nnmware.core.utils import convert_to_date, setting

register = Library()


@register.simple_tag(takes_context=True)
def search_sticky_options(context):
    request = context['request']
    key = sha1(request.get_full_path(),).hexdigest()
    data_key = cache.get(key)
    result = HotelOption.objects.filter(in_search=True, sticky_in_search=True)
    if data_key:
        hotels = Hotel.objects.filter(pk__in=data_key)
        result = result.filter(hotel__in=hotels).distinct()
    return result.order_by('position')


@register.simple_tag(takes_context=True)
def search_options(context):
    request = context['request']
    key = sha1(request.get_full_path(),).hexdigest()
    data_key = cache.get(key)
    result = HotelOption.objects.filter(in_search=True, sticky_in_search=False)
    if data_key:
        hotels = Hotel.objects.filter(pk__in=data_key)
        result = result.filter(hotel__in=hotels).distinct()
    return result.order_by('position')


@register.simple_tag
def hotels_five_stars():
    result = Hotel.objects.filter(starcount=FIVE_STAR).select_related().order_by('name')
    return make_hotel_intro_list(result)


def make_hotel_intro_list(h_list):
    result = []
    arr_len = len(h_list)
    len_list, remainder = divmod(arr_len, 5)
    all_len = [len_list, len_list, len_list, len_list, len_list]
    for i in range(remainder):
        all_len[i] += 1
    for i in range(len(all_len)):
        result.append(h_list[:all_len[i]])
        h_list = h_list[all_len[i]:]
    return result


@register.simple_tag
def hotels_four_stars():
    result = Hotel.objects.filter(starcount=FOUR_STAR).select_related()
    return make_hotel_intro_list(result)


@register.simple_tag
def hotels_three_stars():
    result = Hotel.objects.filter(starcount=THREE_STAR).select_related()
    return make_hotel_intro_list(result)


@register.simple_tag
def hotels_two_stars():
    result = Hotel.objects.filter(starcount=TWO_STAR).select_related()
    return make_hotel_intro_list(result)


@register.simple_tag
def hotels_mini():
    result = Hotel.objects.filter(starcount=MINI_HOTEL).select_related()
    return make_hotel_intro_list(result)


@register.simple_tag
def hotels_hostel():
    result = Hotel.objects.filter(starcount=HOSTEL).select_related()
    return make_hotel_intro_list(result)


@register.simple_tag
def hotels_apartaments():
    result = Hotel.objects.filter(starcount=APARTAMENTS).select_related()
    return make_hotel_intro_list(result)


@register.simple_tag
def hotels_city():
    result = City.objects.all()
    return result


@register.simple_tag
def hotels_count():
    result = Hotel.objects.count()
    return result


@register.simple_tag
def city_count():
    result = City.objects.count()
    return result


@register.simple_tag
def hotels_best_offer():
    result = Hotel.objects.filter(best_offer=True).select_related().order_by('-current_amount')
    return result


@register.simple_tag
def hotels_top10():
    city = City.objects.get(slug='moscow')
    result = Hotel.objects.filter(in_top10=True, city=city).select_related().order_by('-current_amount')
    return result


@register.simple_tag(takes_context=True)
def search_url(context):
    request = context['request']
    url = request.get_full_path()
    if url.count('&order'):
        url = url.split('&order')[0] + '&'
    elif url.count('?order'):
        url = url.split('?order')[0] + '?'
    else:
        if url[-1] == '/':
            url += '?'
        else:
            url += '&'
    return url


@register.simple_tag(takes_context=True)
def minprice_hotel_date(context, hotel, on_date):
    request = context['request']
    date = convert_to_date(on_date)
    hotel_price = hotel.amount_on_date(date)
    return amount_request_currency(request, hotel_price)


@register.simple_tag(takes_context=True)
def room_price_date(context, room, on_date):
    request = context['request']
    date = convert_to_date(on_date)
    room_price = room.amount_on_date(date)
    return amount_request_currency(request, room_price)


def dates_guests_from_context(context):
    search_data = context['search_data']
    f_date = search_data['from_date']
    t_date = search_data['to_date']
    guests = search_data['guests']
    from_date = convert_to_date(f_date)
    to_date = convert_to_date(t_date)
    delta = (to_date - from_date).days
    date_period = (from_date, to_date - timedelta(days=1))
    return from_date, to_date, date_period, delta, guests


@register.simple_tag(takes_context=True)
def room_price_average(context, room, rate):
    from_date, to_date, date_period, delta, guests = dates_guests_from_context(context)
    s = room.settlement_on_date_for_guests(from_date, guests)
    all_sum = PlacePrice.objects.filter(settlement__room=room, settlement__settlement=s, date__range=date_period).\
        aggregate(Sum('amount'))
    room_sum = all_sum['amount__sum']
    result = room_sum / delta
    return convert_to_client_currency(result, rate)


@register.simple_tag(takes_context=True)
def room_full_amount(context, room, rate):
    from_date, to_date, date_period, delta, guests = dates_guests_from_context(context)
    settlement = SettlementVariant.objects.filter(room=room, settlement__gte=guests,
        placeprice__date__range=date_period, placeprice__amount__gt=0).annotate(valid_s=Count('pk')).\
        filter(valid_s__gte=delta).order_by('settlement').values_list('pk', flat=True).distinct()[0]
    result = PlacePrice.objects.filter(settlement__room=room, settlement__pk=settlement,
                                       date__range=date_period).aggregate(Sum('amount'))['amount__sum']
    return convert_to_client_currency(result, rate)


@register.simple_tag(takes_context=True)
def price_variants(context, room, rate):
    btype = context.get('btype')
    from_date, to_date, date_period, delta, guests = dates_guests_from_context(context)
    settlement = SettlementVariant.objects.filter(room=room, settlement__gte=guests,
        placeprice__date__range=date_period, placeprice__amount__gt=0).annotate(valid_s=Count('pk')).\
        filter(valid_s__gte=delta).order_by('settlement').values_list('pk', flat=True).distinct()[0]
    result = PlacePrice.objects.filter(settlement__room=room, settlement__pk=settlement,
                                       date__range=date_period).aggregate(Sum('amount'))['amount__sum']
    answer = convert_to_client_currency(result, rate)
    total_cost = answer
    discount = room.simple_discount
    prices = []
    ub, gb, nr = dict(), dict(), dict()
    variants = []
    if discount.ub:
        if 0 < discount.ub_discount < 100:
            ub['price'] = (answer * (100 - discount.ub_discount)) / 100
            ub['discount'] = discount.ub_discount
        else:
            ub['price'] = answer
            ub['discount'] = None
        ub['average'] = ub['price'] / delta
        ub['variant'] = 'ub'
        if btype == 'ub':
            total_cost = ub['price']
    if discount.gb:
        gb['days'] = from_date - timedelta(days=discount.gb_days)
        if 0 < discount.gb_discount < 100:
            gb['price'] = (answer * (100 - discount.gb_discount)) / 100
            gb['discount'] = discount.gb_discount
        else:
            gb['price'] = answer
            gb['discount'] = None
        if 0 < discount.gb_penalty <= 100:
            room_answer = PlacePrice.objects.get(settlement__room=room, settlement__pk=settlement, date=from_date)
            room_answer = convert_to_client_currency(room_answer.amount, rate)
            if gb['discount'] is not None:
                gb['penalty'] = (room_answer * (100 - gb['discount']) * discount.gb_penalty) / 10000
            else:
                gb['penalty'] = (room_answer * discount.gb_penalty) / 100
        else:
            gb['penalty'] = None
        gb['average'] = gb['price'] / delta
        gb['variant'] = 'gb'
        if btype == 'gb':
            total_cost = gb['price']
    if discount.nr:
        if 0 < discount.nr_discount < 100:
            nr['price'] = (answer * (100 - discount.nr_discount)) / 100
            nr['discount'] = discount.nr_discount
        else:
            nr['price'] = answer
            nr['discount'] = None
        if btype == 'nr':
            total_cost = nr['price']
        nr['average'] = nr['price'] / delta
        nr['variant'] = 'nr'
    if btype == 'ub' and bool(ub):
        variants.append(ub)
        if bool(gb):
            variants.append(gb)
        if bool(nr):
            variants.append(nr)
    elif btype == 'gb' and bool(gb):
        variants.append(gb)
        if bool(ub):
            variants.append(ub)
        if bool(nr):
            variants.append(nr)
    elif btype == 'nr' and bool(nr):
        variants.append(nr)
        if bool(ub):
            variants.append(ub)
        if bool(gb):
            variants.append(gb)
    else:
        if bool(ub):
            variants.append(ub)
        if bool(gb):
            variants.append(gb)
        if bool(nr):
            variants.append(nr)
    prices.append(variants)
    prices.append(answer / delta)
    prices.append(total_cost)
    prices.append(delta)
    prices.append(len(variants))
    return prices


@register.simple_tag(takes_context=True)
def room_full_amount_discount(context, room):
    from_date, to_date, date_period, delta, guests = dates_guests_from_context(context)
    # TODO Discount
    all_discount = RoomDiscount.objects.filter(date__range=date_period, room=room).annotate(Count('pk'))
    return all_discount


@register.simple_tag(takes_context=True)
def room_variant_s(context, room):
    from_date, to_date, date_period, delta, guests = dates_guests_from_context(context)
    s_pk = PlacePrice.objects.filter(settlement__room=room, settlement__settlement__gte=guests,
        date__range=date_period, amount__gte=0).annotate(valid_s=Sum('settlement')).\
        filter(valid_s__gte=delta).order_by('settlement__settlement').values_list('settlement__pk',
        flat=True).distinct()[0]
    variant = SettlementVariant.objects.get(pk=s_pk).settlement
    return range(0, int(variant))


@register.simple_tag(takes_context=True)
def room_variant(context, room):
    from_date, to_date, date_period, delta, guests = dates_guests_from_context(context)
    return room.settlement_on_date_for_guests(from_date, guests)


@register.simple_tag(takes_context=True)
def client_currency(context):
    request = context['request']
    try:
        currency = request.COOKIES['currency']
    except:
        currency = setting('CURRENCY', 'RUB')
    if currency == 'USD':
        return '$'
    elif currency == 'EUR':
        return '€'
    elif currency == 'JPY':
        return '¥'
    elif currency == 'GBP':
        return '£'
    else:
        return _('rub')


@register.simple_tag(takes_context=True)
def view_currency(context):
    request = context['request']
    try:
        currency = request.COOKIES['currency']
    except:
        currency = setting('CURRENCY', 'RUB')
    if currency == 'USD':
        return _('US Dollars')
    elif currency == 'EUR':
        return _('Euro')
    else:
        return _('Roubles')


@register.simple_tag
def convert_to_client_currency(amount, rate):
    try:
        if setting('OFFICIAL_RATE', True):
            exchange = rate.official_rate
        else:
            exchange = rate.rate
        return int((amount * rate.nominal) / exchange)
    except:
        return int(amount)


def amount_request_currency(request, amount):
    try:
        currency = Currency.objects.get(code=request.COOKIES['currency'])
        rate = ExchangeRate.objects.filter(currency=currency).filter(date__lte=now()).order_by('-date')[0]
        if setting('OFFICIAL_RATE', True):
            exchange = rate.official_rate
        else:
            exchange = rate.rate
        return int((amount * rate.nominal) / exchange)
    except:
        return int(amount)


def user_rate_from_request(request):
    try:
        user_currency = request.COOKIES['currency']
    except:
        user_currency = setting('CURRENCY', 'RUB')
    try:
        rate = ExchangeRate.objects.select_related().filter(currency__code=user_currency).\
            filter(date__lte=now()).order_by('-date')[0]
        return rate
    except:
        return None


@register.simple_tag(takes_context=True)
def user_currency_rate(context):
    request = context['request']
    return user_rate_from_request(request)


@register.simple_tag
def distance_for(origin, destiny):
    result = distance_to_object(origin, destiny)
    return format(result, '.2f')


@register.filter(is_safe=True)
@stringfilter
def rbtruncatechars(value, arg):
    """
    Truncates a string after a certain number of characters and add "..."
    """
    try:
        length = int(arg)
    except ValueError:  # Invalid literal for int().
        return value  # Fail silently.
    result = value[:length]
    while result[-1] == '.':
        result = result[:-1]
    return result + '...'


@register.filter
def min_3_days(d):
    return d - timedelta(days=3)


@register.simple_tag
def hotels_spb_count():
    result = Hotel.objects.filter(city__slug='spb').count()
    return result


@register.simple_tag
def hotels_moscow_count():
    result = Hotel.objects.filter(city__slug='moscow').count()
    return result


@register.simple_tag
def hotels_city_count(slug):
    # noinspection PyBroadException
    try:
        result = Hotel.objects.filter(city__slug=slug).count()
        return result
    except:
        return 0


# Make string of values for all dates + empty values
def make_values_by_dates(dates, array):
    all_dates = dict((d.strftime("%Y-%m-%d"), '') for d in dates)
    for k, v in array:
        all_dates[k.strftime("%Y-%m-%d")] = v
    result = [all_dates[k] for k in sorted(all_dates)]
    return result


@register.simple_tag
def settlement_prices_on_dates(settlement, dates):
    result = PlacePrice.objects.filter(settlement=settlement, date__in=dates).values_list('date', 'amount').\
        order_by('date')
    return make_values_by_dates(dates, result)


@register.simple_tag
def discount_on_dates(discount, room, dates):
    result = RoomDiscount.objects.filter(discount=discount, room=room, date__in=dates).values_list('date', 'value').\
        order_by('date')
    return make_values_by_dates(dates, result)


@register.simple_tag
def room_availability_on_dates(room, dates):
    result = Availability.objects.filter(room=room, date__in=dates).values_list('date', 'placecount').order_by('date')
    return make_values_by_dates(dates, result)


@register.simple_tag
def room_min_days_on_dates(room, dates):
    result = Availability.objects.filter(room=room, date__in=dates).values_list('date', 'min_days').order_by('date')
    return make_values_by_dates(dates, result)


@register.simple_tag
def room_avg_amount(amount, days):
    result = amount / days
    return format(result, '.2f')


@register.simple_tag(takes_context=True)
def stars_hotel_count(context):
    request = context['request']
    # search_data = context['search_data']
    # try:
    #     on_date = convert_to_date(search_data['from_date']) - timedelta(days=1)
    # except:
    #     on_date = now()
    # hotels_with_amount = PlacePrice.objects.filter(date=on_date, amount__gt=0).\
    #     values_list('settlement__room__hotel__pk', flat=True).distinct()
    result = Hotel.objects.all()   # filter(pk__in=hotels_with_amount)
    key = sha1('%s' % (request.get_full_path(),)).hexdigest()
    data_key = cache.get(key)
    if data_key:
        result = result.filter(pk__in=data_key).values('starcount').order_by('starcount').\
            annotate(Count('starcount'))
    else:
        result = result.values('starcount').order_by('starcount').annotate(Count('starcount'))
    return result


@register.simple_tag(takes_context=True)
def min_search_hotel_price(context, hotel):
    user_rate = context['user_currency_rate']
    from_date, to_date, date_period, delta, guests = dates_guests_from_context(context)
    rooms = Room.objects.filter(hotel=hotel, availability__date__range=date_period,
        availability__min_days__lte=delta, availability__placecount__gt=0).\
        annotate(num_days=Count('pk')).filter(num_days__gte=delta).order_by('pk').values_list('pk', flat=True).\
        distinct()
    result = PlacePrice.objects.filter(settlement__room__in=rooms, settlement__settlement__gte=guests,
         date=from_date, amount__gt=0).aggregate(Min('amount'))
    return convert_to_client_currency(int(result['amount__min']), user_rate)


@register.simple_tag(takes_context=True)
def search_minimal_hotel_cost(context, hotel, rate):
    from_date, to_date, date_period, delta, guests = dates_guests_from_context(context)
    rooms = hotel.available_rooms_for_guests_in_period(guests, from_date, to_date)
    result = []
    for room in rooms:
        room_res = []
        prices = price_variants(context, room, rate)[0]
        if bool(prices):
            for i in prices:
                room_res.append(i['price'])
        if bool(room_res):
            result.append(min(room_res))
    return min(result)


@register.simple_tag
def booking_statuses():
    return STATUS_CHOICES
