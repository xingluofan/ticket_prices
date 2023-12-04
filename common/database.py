import sqlite3

'''写一个类打包成库，通用于储存信息的sqlite'''
'''函数返回值可优化'''
'''使用：使用'''
'''说明：1、单例模式连接数据库：避免数据库connect过多导致数据库down
        2、根据数据库增删查改性能对比，统一使用execute进行常规数据库操作
        3、且不做try操作：1、影响性能 2、若报错，外部调用无法确定问题所在，'''

class LiteDb(object):
    _instance = None

    def __new__(cls, *args, **kw):
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def openDb(self, dbname):
        self.dbname = dbname
        self.conn = sqlite3.connect(self.dbname)
        self.cursor = self.conn.cursor()

    def closeDb(self):
        '''
        关闭数据库
        :return:
        '''
        self.cursor.close()
        self.conn.close()

    def createTables(self, sql):
        '''
        example：'create table userinfo(name text, email text)'
        :return: result=[1,None]
        '''
        self.cursor.execute(sql)
        self.conn.commit()
        result = [1, None]
        return result

    def dropTables(self, sql):
        '''
        example:'drop table userinfo'
        :param sql:
        :return:result=[1,None]
        '''
        self.cursor.execute(sql)
        self.conn.commit()
        result = [1, None]
        return result

    def executeSql(self, sql, value=None):
        '''
        执行单个sql语句，只需要传入sql语句和值便可
        :param sql:'insert into user(name,password,number,status) values(?,?,?,?)'
                    'delete from user where name=?'
                    'updata user set status=? where name=?'
                    'select * from user where id=%s'
        :param value:[(123456,123456,123456,123456),(123,123,123,123)]
                value:'123456'
                value:(123,123)
        :return:result=[1,None]
        '''

        '''增、删、查、改'''
        if isinstance(value,list) and isinstance(value[0],(list,tuple)):
            for valu in value:
                self.cursor.execute(sql, valu)
            else:
                self.conn.commit()
                result = [1, self.cursor.fetchall()]
        else:
            '''执行单条语句：字符串、整型、数组'''
            if value:
                self.cursor.execute(sql, value)
            else:
                self.cursor.execute(sql)
            self.conn.commit()
            result = [1, self.cursor.fetchall()]
        return result
