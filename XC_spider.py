import hashlib
import json
import logging
import random
import time
from datetime import datetime

import requests
from fake_useragent import UserAgent

# 参考文章：
#   - 机场列表 - 维基百科
#     https://zh.wikipedia.org/wiki/%E4%B8%AD%E5%8D%8E%E4%BA%BA%E6%B0%91%E5%85%B1%E5%92%8C%E5%9B%BD%E6%9C%BA%E5%9C%BA%E5%88%97%E8%A1%A8
#   - Chrome断点JS寻找淘宝签名sign https://blog.csdn.net/weixin_44818729/article/details/109400391

ua = UserAgent()

def get_cookie_bfa():
    random_str = "abcdefghijklmnopqrstuvwxyz1234567890"
    random_id = ""
    for _ in range(6):
        random_id += random.choice(random_str)
    t = str(int(round(time.time() * 1000)))

    bfa_list = ["1", t, random_id, "1", t, t, "1", "1"]
    bfa = "_bfa={}".format(".".join(bfa_list))
    return bfa

 
def hex_md5(s):
    m=hashlib.md5()
    m.update(s.encode('UTF-8'))
    return m.hexdigest()

# 获取调用携程 API 查询航班接口 Header 中所需的参数 sign
def get_sign(transaction_id, departure_city_code, arrival_city_code, departure_date):
    sign_value = transaction_id + departure_city_code + arrival_city_code + departure_date
    _sign = hashlib.md5()
    _sign.update(sign_value.encode('utf-8'))
    return _sign.hexdigest()

# 获取 transactionID 及航线数据
def get_transaction_id(departure_city_code, arrival_city_code, departure_date, cabin):
    flight_list_url = "https://flights.ctrip.com/international/search/api/flightlist" \
                      "/oneway-{}-{}?_=1&depdate={}&cabin={}&containstax=1" \
        .format(departure_city_code, arrival_city_code, departure_date, cabin)
    flight_list_req = requests.get(url=flight_list_url)
    if flight_list_req.status_code != 200:
        logging.error("get transaction id failed, status code {}".format(flight_list_req.status_code))
        return "", None

    try:
        flight_list_data = flight_list_req.json()["data"]
        transaction_id = flight_list_data["transactionID"]
    except Exception as e:
        logging.error("get transaction id failed, {}".format(e))
        return "", None

    return transaction_id, flight_list_data

# 获取航线具体信息与航班数据
def get_flight_info(departure_city_code, arrival_city_code, departure_date='2023-06-01', cabin='Y'):
    # 获取 transactionID 及航线数据
    transaction_id, flight_list_data = get_transaction_id(departure_city_code, arrival_city_code, departure_date, cabin)
    if transaction_id == "" or flight_list_data is None:
        return False, None

    # 获取调用携程 API 查询航班接口 Header 中所需的参数 sign
    sign = get_sign(transaction_id, departure_city_code, arrival_city_code, departure_date)

    # cookie 中的 bfa
    bfa = get_cookie_bfa()

    # 构造请求，查询数据
    search_url = "https://flights.ctrip.com/international/search/api/search/batchSearch"
    search_headers = {
        "transactionid": transaction_id,
        "sign": sign,
        "scope": flight_list_data["scope"],
        "origin": "https://flights.ctrip.com",
        "referer": "https://flights.ctrip.com/online/list/oneway-{}-{}"
                   "?_=1&depdate={}&cabin={}&containstax=1".format(departure_city_code, arrival_city_code,
                                                                   departure_date, cabin),
        "content-type": "application/json;charset=UTF-8",
        "user-agent": ua.chrome,
        "cookie": bfa,
    }
    r = requests.post(url=search_url, headers=search_headers, data=json.dumps(flight_list_data))

    if r.status_code != 200:
        logging.error("get flight info failed, status code {}".format(r.status_code))
        return False, None

    try:
        result_json = r.json()
        if result_json["data"]["context"]["flag"] != 0:
            logging.error("get flight info failed, {}".format(result_json))
            return False, None
    except Exception as e:
        logging.error("get flight info failed, {}".format(e))
        return False, None

    if "flightItineraryList" not in result_json["data"]:
        result_data = []
    else:
        result_data = result_json["data"]["flightItineraryList"]
    return True, result_data

def get_calendar_detail(departure_city_code, arrival_city_code, departure_date='2023-06-01', cabin='Y'):
    transaction_id, flight_list_data = get_transaction_id(departure_city_code, arrival_city_code, departure_date, cabin)
    bfa = get_cookie_bfa()
    detail_url = 'https://flights.ctrip.com/international/search/api/lowprice/calendar/getOwCalendarPrices'
    detail_headers = {
        "transactionid": transaction_id,
        "scope": flight_list_data["scope"],
        "origin": "https://flights.ctrip.com",
        "referer": "https://flights.ctrip.com/online/list/oneway-{}-{}"
                   "?_=1&depdate={}&cabin={}&containstax=1".format(departure_city_code, arrival_city_code,
                                                                   departure_date, cabin),
        "content-type": "application/json;charset=UTF-8",
        "user-agent": ua.chrome,
        "cookie": bfa
    }
    json_data = {
        "departCityCode": departure_city_code,
        "arrivalCityCode": arrival_city_code,
        "cabin": cabin
    }

    r = requests.get(url=detail_url, timeout=10, headers=detail_headers, params=json_data).json()
    return r


def get_feizhu_calendar_detail(departure_city_code, arrival_city_code, departure_date='2023-06-01', cabin='Y'):
    detail_url = 'https://h5api.m.taobao.com/h5/mtop.trip.flight.calendar.cheapest/1.0/'
    appKey="12574478"
    
    # _m_h5_tk="56fb1ff0b9074f2723dc26cab9638488_1701921305574"
    # _m_h5_tk_enc="0b9a08c2a068c2cfb6ceac45c65b8b70"
    
    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y-%m-%d")
    print('date:'+formatted_date)
    
    data = {"depCityCode":departure_city_code,"arrCityCode":arrival_city_code,"beginDate":formatted_date,"days":90,"bizType":0,"sceneType":0,"tripType":1,"averagePriceSearch":'false',"h5Version":"1.31.1"}
    
    json_data = {
        "appKey": appKey,
        "data": json.dumps(data),
    }
    html = requests.get(url=detail_url, timeout=10, params=json_data)
    
    print('html' + str(html.cookies['_m_h5_tk']))
    
    _m_h5_tk=html.cookies['_m_h5_tk']
    _m_h5_tk_enc=html.cookies['_m_h5_tk_enc']

    cookies = "_samesite_flag_=true; cookie2=1bbc3a64010bd3796dea57cc1aa8ecf4; t=d01e26f4fed9e796fcb6fd9451754f9f; _fli_isNotch=0; cna=PK/HHc4v8HQCAXFvA9IDgwud; _fli_titleHeight=0; _fli_screenDix=2; _tb_token_=393e7a7be83eb; _m_h5_tk=" + _m_h5_tk + "; _m_h5_tk_enc=" + _m_h5_tk_enc + "; isg=BGpqxYVj-0ofZHenqkt_PqK1u9YM2-41beSP7fQjFr1RJwrh3Gs-RbBVs1U712bN"
    # print('cookies:' + cookies)
    detail_headers = {
        "origin": "https://market.m.taobao.com",
        "referer": "https://market.m.taobao.com/",
        "content-type": "application/x-www-form-urlencoded",
        "user-agent": ua.chrome,
        "cookie": cookies,
        "Warehousecode": '{"clientType":"other","os":"ios","osVersion":"13.2.3","appVersion":"1.29.0","containerVersion":"0.0.0","pageType":"h5","ttid":"201300@travel_h5_3.1.0","spm":"181.7437871","spmUrl":"181.7437871.20000_ECONOMY_RECOMMEND.d0","spmPre":"/tbtrip.181.11925144.10840050.d10"}'
    }
    t=str(int(time.time() * 1000))

    json_string_data = json.dumps(data)
    
    token=_m_h5_tk.split('_')[0]
    print('data:' + json_string_data)
    print('t:' + t)
    
    u=token + '&' + t + '&' + appKey + '&' + json_string_data

    sign=hex_md5(u)

    json_data = {
        "type": "originaljson",
        "api": "mtop.trip.flight.calendar.cheapest",
        "v": "1.0",
        "ttid": "201300@travel_h5_3.1.0",
        "appKey": appKey,
        "sign": sign,
        "data": json_string_data,
        "t": t
    }
    
    print('sign:' + sign)

    r = requests.get(url=detail_url, timeout=10, headers=detail_headers, params=json_data).json()
    return r
