from flask import Flask, request, jsonify, Blueprint, session
from flask_cors import CORS, cross_origin
from flask_login import login_manager, login_user, login_required, current_user, logout_user, UserMixin
from werkzeug.security import check_password_hash
from db_model.mysql import conn_mysqldb
from control.user_mgmt import User
from flask_jwt_extended import create_access_token
import logging
from datetime import timedelta

login_blueprint = Blueprint('login', __name__)
    

#로그인 API
@login_blueprint.route('/api/login', methods=['POST'])
@cross_origin()
def login():
  data = request.get_json()
  email = data['email']
  password = data['password']
  
  try:
    conn, cur = conn_mysqldb()
    cur.execute("SELECT * FROM user_info WHERE email = %s", (email,))
    user_data = cur.fetchone()
    
    if user_data:
      if check_password_hash(user_data['password'], password):
        #로그인 성공   
        user = User(user_data['id'], user_data['email'], user_data['name'], user_data['role'], user_data['address']) 
        login_user(user)
        
        #jwt 토큰 생성 (식별자로 user_id 값을 저장)
        token = create_access_token(identity=current_user.get_id(), additional_claims={'role': current_user.get_role()}, expires_delta=timedelta(days=30))
        print(current_user) 

        return jsonify({'status': 'success', 'data': {
          'id': current_user.get_id(),
          'email': current_user.get_email(),
          'name': current_user.get_name(),
          'role': current_user.get_role(),
          'address': current_user.get_address(),
          'token': token
        }})
      else:
        #비밀번호가 올바르지 않은 경우
        return jsonify({'status':'error', 'message': 'Invalid password'})
    else:
      #존재하지 않는 사용자인 경우
      return jsonify({'status':'error','message': 'User does not exist'})
    
  except Exception as e:
    logging.error(e, exc_info=True)
    return jsonify({'status': 'error','message': repr(e)})
  finally:
    cur.close()
    conn.close()
  
#로그아웃 API 
@login_blueprint.route('/api/logout')
@login_required
def logout():
  session.clear() #세션 초기화
  logout_user()
  return jsonify({'success': True})
  