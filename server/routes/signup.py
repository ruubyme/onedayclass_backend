from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS, cross_origin
from werkzeug.security import generate_password_hash
from db_model.mysql import conn_mysqldb
import traceback


signup_blueprint = Blueprint('signup', __name__)

#회원가입 API 
@signup_blueprint.route('/api/signup', methods=['POST'])
@cross_origin()
def signup():
  conn, cur = conn_mysqldb()
  
  try:
    data = request.get_json()
    name = data['name']
    email = data['email']
    password = data['password']
    phone_number = data['phone_number']
    address = data['address']
    zonecode = data['zonecode']
    address_detail = data['address_detail']
    role = data['role']
    
    #비밀번호 해시화 
    hashed_password = generate_password_hash(password)
    
    
    #입력한 값 중에 빈 값이 있는지 확인 
    if not all([name, email, password, phone_number, address, zonecode, role]):
      error_msg = "Please fill in all required fields."
      return jsonify({'status': 'error', "message": error_msg})
    
    
    #email 중복 체크 
    cur.execute("SELECT * FROM user_info WHERE email=%s", (email,))
    user = cur.fetchone()
    
    #입력한 email이 이미 존재한다면 
    if user:
      error_msg = "해당 이메일은 이미 존재합니다. 다른 이메일을 입력해주세요."
      return jsonify({'status': 'error', 'message': error_msg})
    else:
      cur.execute("INSERT INTO user_info (email, password, name, phone_number, address, zonecode, address_detail, role) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (email, hashed_password, name, phone_number, address, zonecode, address_detail, role))
      conn.commit()
      
      return jsonify({'status': 'success'})
    
  except Exception as e:
    traceback.print_exc()
    return jsonify({'status': 'error', 'message': str(e)})
  
  finally:
    cur.close()
    conn.close()
  