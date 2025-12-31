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
def get_flight_info(departure_city_code, arrival_city_code, departure_date=None, cabin='Y'):
    if departure_date is None:
        departure_date = datetime.now().strftime('%Y-%m-%d')
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

def get_calendar_detail(departure_city_code, arrival_city_code, departure_date=None, cabin='Y'):
    if departure_date is None:
        departure_date = datetime.now().strftime('%Y-%m-%d')
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


def get_feizhu_calendar_detail(departure_city_code, arrival_city_code, departure_date=None, cabin='Y'):
    detail_url = 'https://h5api.m.taobao.com/h5/mtop.trip.flight.calendar.cheapest/1.0/'
    appKey = "12574478"
    
    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y-%m-%d")
    print(f'Fetching Feizhu data: {departure_city_code} -> {arrival_city_code} on {formatted_date}')
    
    data = {
        "depCityCode": departure_city_code,
        "arrCityCode": arrival_city_code,
        "beginDate": formatted_date,
        "days": 90,
        "bizType": 0,
        "sceneType": 0,
        "tripType": 1,
        "averagePriceSearch": 'false',
        "h5Version": "1.31.1"
    }
    
    # Use a Session to manage cookies automatically
    session = requests.Session()
    
    # Use a fixed, modern Chrome User-Agent to match the Sec-Ch-Ua headers
    # Random UA from fake_useragent might mismatch with fixed Client Hints
    fixed_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    # Set common headers for all requests - mimicking a real Chrome browser on macOS
    session.headers.update({
        "User-Agent": fixed_ua,
        "Referer": "https://h5.m.taobao.com/",
        "Origin": "https://h5.m.taobao.com",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"'
    })

    # Step 1: First Request to get the Token (_m_h5_tk)
    # We send a request with an empty/dummy sign to trigger the token issuance
    t = str(int(time.time() * 1000))
    params_1 = {
        "jsv": "2.4.11",
        "appKey": appKey,
        "t": t,
        "sign": "1234567890", # Invalid sign to force token generation
        "api": "mtop.trip.flight.calendar.cheapest",
        "v": "1.0",
        "type": "originaljson",
        "dataType": "json",
        "data": json.dumps(data)
    }

    try:
        # Note: headers are already in session
        r1 = session.get(url=detail_url, params=params_1, timeout=10)
    except Exception as e:
        print(f"Network error during first request: {e}")
        return {'data': {}}

    # Check if we got the token
    cookies = session.cookies.get_dict()
    _m_h5_tk = cookies.get('_m_h5_tk')
    _m_h5_tk_enc = cookies.get('_m_h5_tk_enc')

    if not _m_h5_tk:
        print("Failed to get _m_h5_tk cookie in first attempt.")
        print(f"Status: {r1.status_code}")
        # print(f"Response: {r1.text[:200]}")
        return {'data': {}}
    
    print(f"Got Token: {_m_h5_tk[:10]}...")

    # Step 2: Calculate Sign with the new Token
    # Token format is usually "token_timestamp"
    token = _m_h5_tk.split('_')[0]
    t = str(int(time.time() * 1000))
    json_string_data = json.dumps(data)
    
    # Sign = md5(token & t & appKey & data)
    str_to_sign = f"{token}&{t}&{appKey}&{json_string_data}"
    sign = hex_md5(str_to_sign)
    
    # Step 3: Second Request with Valid Sign
    params_2 = {
        "jsv": "2.4.11",
        "appKey": appKey,
        "t": t,
        "sign": sign,
        "api": "mtop.trip.flight.calendar.cheapest",
        "v": "1.0",
        "type": "originaljson",
        "dataType": "json",
        "data": json_string_data
    }
    
    try:
        r2 = session.get(url=detail_url, params=params_2, timeout=10)
        result = r2.json()
        
        # Check if successful
        if "ret" in result and "SUCCESS" in result["ret"][0]:
            return result
        else:
            print(f"API Error: {result.get('ret', 'Unknown Error')}")
            return {'data': {}}
    except Exception as e:
        print(f"Error during second request: {e}")
        return {'data': {}}

def get_feizhu_calendar_detail_with_cookie(departure_city_code, arrival_city_code, cookie_header, departure_date=None, cabin='Y'):
    detail_url = 'https://h5api.m.taobao.com/h5/mtop.trip.flight.calendar.cheapest/1.0/'
    appKey = "12574478"
    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y-%m-%d")
    data = {
        "depCityCode": departure_city_code,
        "arrCityCode": arrival_city_code,
        "beginDate": formatted_date,
        "days": 90,
        "bizType": 0,
        "sceneType": 0,
        "tripType": 1,
        "averagePriceSearch": 'false',
        "h5Version": "1.31.1"
    }
    fixed_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    headers = {
        "User-Agent": fixed_ua,
        "Referer": "https://h5.m.taobao.com/",
        "Origin": "https://h5.m.taobao.com",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": cookie_header
    }
    t = str(int(time.time() * 1000))
    json_string_data = json.dumps(data)
    try:
        token_pair = [p for p in cookie_header.split(';') if p.strip().startswith('_m_h5_tk=')]
        if not token_pair:
            return {'data': {}}
        token_full = token_pair[0].split('=', 1)[1].strip()
        token = token_full.split('_')[0]
    except Exception:
        return {'data': {}}
    sign = hex_md5(f"{token}&{t}&{appKey}&{json_string_data}")
    params = {
        "jsv": "2.4.11",
        "appKey": appKey,
        "t": t,
        "sign": sign,
        "api": "mtop.trip.flight.calendar.cheapest",
        "v": "1.0",
        "type": "originaljson",
        "dataType": "json",
        "data": json_string_data
    }
    try:
        r = requests.get(url=detail_url, params=params, headers=headers, timeout=10)
        return r.json()
    except Exception:
        return {'data': {}}
