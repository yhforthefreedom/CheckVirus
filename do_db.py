import sqlite3


class DoDb:
    _instance = None

    def __new__(cls, *args, **kw):
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __init__(self):
        # 创建数据库并获得连接
        self.conn = sqlite3.connect('app.db')
        # 获得游标
        self.c = self.conn.cursor()
        # 创建数据库表
        self.c.execute("""CREATE TABLE IF NOT EXISTS virus(
              app_name TEXT,
              package_name TEXT,
              brand TEXT,
              model TEXT,
              version_code INTEGER,
              version_name TEXT,
              check_time TEXT 
          )""")

    def close(self):
        self.c.close()
        self.conn.close()

    def insert_data(self, data):
        self.c.execute(f"INSERT INTO virus VALUES{data}")
        self.conn.commit()

    def search_data(self, data):
        self.c.execute(f"SELECT max(version_code) FROM virus WHERE app_name='{data}'")
        return self.c.fetchone()[0]
