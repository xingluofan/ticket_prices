import sqlite3
import time
import requests
import random
import argparse
import json
import common.city_code
from XC_spider import get_feizhu_calendar_detail,get_feizhu_calendar_detail_with_cookie,get_flight_info
from common.database import LiteDb as ld
from common.city_code import city,city_value,city_name,name_code,depart_arrival
COOKIE_HEADER = None

def create_flight_table():
    ld().openDb('feizhu_info.sqlite')
    drop_city_sql = 'drop table if exists air_info'
    create_city_sql = 'create table if not exists air_info(departcity text,arrivalcity text,date text,price int,platform text)'
    ld().createTables(drop_city_sql)
    ld().createTables(create_city_sql)
    ld().closeDb()

def save_flight_info(air_res):
    print(f"Saving {len(air_res)} records...")
    ld().openDb('feizhu_info.sqlite')
    insert_city_sql = 'insert into air_info(departcity,arrivalcity,date,price,platform) values(?,?,?,?,?)'
    ld().executeSql(insert_city_sql,air_res)
    ld().closeDb()
    print("Saved.")

def get_flight(departcity, arrivalcity):
    depart_city_code = name_code(name=departcity)
    arrival_city_code = name_code(name=arrivalcity)
    platform = '飞猪'
    try:
        print(f'爬取{departcity}{depart_city_code}飞往{arrivalcity}{arrival_city_code}的数据')
        delay = random.uniform(0.1, 1.5)
        if COOKIE_HEADER:
            _res = get_feizhu_calendar_detail_with_cookie(depart_city_code, arrival_city_code, COOKIE_HEADER)['data']
        else:
            _res = get_feizhu_calendar_detail(depart_city_code, arrival_city_code)['data']
        print(f'看看_res{_res}')
        if 'ow' not in _res:
            print(f'未找到航班数据，可能触发了反爬或无数据: {_res}')
            return
        result = _res['ow']
        
        res = {}

        for item in result:
            dep_date = item['depDate']
            price = item['price']

            if price != 0:
                res[dep_date] = price

        print(f'爬取完毕-----{res}')
        if res == {}:
            pass
        else:
            res0 = list(res.items())
            res1 = [(departcity, arrivalcity) for _ in range(len(res0))]
            result = [(loc[0], loc[1], date, value, platform) for (date, value), loc in zip(res0, res1)]
            save_flight_info(result)
            time.sleep(delay)
    except requests.RequestException as e:
        print(f'{departcity}飞往{arrivalcity}爬取失败，失败原因为：{e}')

def querry_low_price():
    ld().openDb('feizhu_info.sqlite')
    query_sql = 'SELECT * FROM air_info WHERE price = (SELECT MIN(price) FROM air_info)'
    air_info = ld().executeSql(query_sql)
    ld().closeDb()
    return air_info
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cities', type=str)
    parser.add_argument('--cookie', type=str)
    args = parser.parse_args()
    if args.cities:
        common.city_code.city = json.loads(args.cities)
        common.city_code.city_value = list(common.city_code.city.items())
    if args.cookie:
        COOKIE_HEADER = args.cookie
    create_flight_table()
    for departcity,arrivalcity in depart_arrival():
        get_flight(departcity,arrivalcity)
