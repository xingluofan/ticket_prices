import sqlite3
import time
import requests
import random
from XC_spider import get_calendar_detail,get_flight_info
from common.database import LiteDb as ld
from common.city_code import city,city_value,city_name,name_code,depart_arrival

def create_flight_table():
    ld().openDb('flight_info.sqlite')
    drop_city_sql = 'drop table if exists air_info'
    create_city_sql = 'create table if not exists air_info(departcity text,arrivalcity text,date text,price int)'
    ld().createTables(drop_city_sql)
    ld().createTables(create_city_sql)
    ld().closeDb()

def save_flight_info(air_res):
    ld().openDb('flight_info.sqlite')
    insert_city_sql = 'insert into air_info(departcity,arrivalcity,date,price) values(?,?,?,?)'
    ld().executeSql(insert_city_sql,air_res)
    ld().closeDb()

def get_flight(departcity, arrivalcity):
    depart_city_code = name_code(name=departcity)
    arrival_city_code = name_code(name=arrivalcity)
    try:
        print(f'爬取{departcity}飞往{arrivalcity}的数据')
        delay = random.uniform(0.1, 1.5)
        res = get_calendar_detail(depart_city_code, arrival_city_code)['data']
        print('爬取完毕')
        if res == {}:
            pass
        else:
            res0 = list(res.items())
            res1 = [(departcity, arrivalcity) for _ in range(len(res0))]
            result = [(loc[0], loc[1], date, value) for (date, value), loc in zip(res0, res1)]
            save_flight_info(result)
            time.sleep(delay)
    except requests.RequestException as e:
        print(f'{departcity}飞往{arrivalcity}爬取失败，失败原因为：{e}')

def querry_low_price():
    ld().openDb('flight_info.sqlite')
    query_sql = 'SELECT * FROM air_info WHERE price = (SELECT MIN(price) FROM air_info)'
    air_info = ld().executeSql(query_sql)
    ld().closeDb()
    return air_info
if __name__ == '__main__':
    create_flight_table()
    for departcity,arrivalcity in depart_arrival():
        get_flight(departcity,arrivalcity)
    # print(querry_low_price())