import pymysql 
from dotenv import load_dotenv
import os 
from dbutils.pooled_db import PooledDB


# .env.local 파일 로드
load_dotenv('.env.local')

MYSQL_HOST = 'localhost'

POOL = PooledDB(
  creator=pymysql,
  maxconnections=50,
  user=os.getenv('DB_USER'),
  passwd=os.getenv('DB_PASSWORD'),
  host=MYSQL_HOST,
  port=3306,
  database='onedayclass_db',
  charset='utf8mb4'
  )

def conn_mysqldb():
  conn = POOL.connection()
  cursor = conn.cursor(pymysql.cursors.DictCursor)
  return conn, cursor
