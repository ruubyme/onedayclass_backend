import pymysql 
from dotenv import load_dotenv
import os 
from dbutils.pooled_db import PooledDB


# .env.local 파일 로드
load_dotenv('.env.local')

POOL = PooledDB(
  creator=pymysql,
  maxconnections=50,
  user=os.getenv('DB_USER'),
  passwd=os.getenv('DB_PASSWORD'),
  host=os.getenv('DB_HOST'),
  port=55710,
  database=os.getenv('DB_NAME'),
  charset='utf8mb4',
  autocommit=True,
  ssl={'ca': os.getenv('SSL'), 'ssl_mode': 'VERIFY_IDENTITY'}
  )

def conn_mysqldb():
  conn = POOL.connection()
  cursor = conn.cursor(pymysql.cursors.DictCursor)
  return conn, cursor
