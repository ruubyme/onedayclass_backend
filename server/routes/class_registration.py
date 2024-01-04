from flask import request, Blueprint, jsonify
from flask_cors import cross_origin
from db_model.mysql import conn_mysqldb
from datetime import datetime 
import json
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

register_class_blueprint = Blueprint('register_class', __name__)

#클래스 등록 API 
@register_class_blueprint.route('/api/register_class', methods=['POST'])
@cross_origin()
@jwt_required() #토큰이 필요한 경우에만 요청을 처리
def classRegistration():
  conn, cur = conn_mysqldb()
  
  try:
    data = request.get_json()
    class_name = data['className']
    description = data['description']
    location = data['location']
    cost = data['cost']
    latitude = data['latitude']
    longitude = data['longitude']
    target_student = data['targetStudents']
    curriculum = data['curriculums']
    content = data['content']
    
    #토큰에서 사용자 정보 조회 (식별자로 저장된 user_id값을 추출 )
    user_id = get_jwt_identity()
    user_role = get_jwt().get('role') #토큰의 클레임에서 'role'값을 추출
    
    #role이 강사가 아니면 접근을 막음 
    if user_role != 'instructor':
      return jsonify({'status': 'error', 'message': 'Unauthorized access'})
    
    instructor_id = user_id
    
    #입력한 값 중에 빈 값이 있는지 확인 
    if not all([class_name, description, location, latitude, longitude, content]):
      error_msg = "Please fill in all required fields."
      return jsonify({'status': 'error', 'message': error_msg})
    
    #db 연결 
    conn, cur = conn_mysqldb()
    #데이터베이스 저장 
    cur.execute("INSERT INTO class (class_name, description, location, instructor_id, cost, latitude, longitude, target_student, curriculum, content) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (class_name, description, location, instructor_id, cost, latitude, longitude, json.dumps(target_student), json.dumps(curriculum), content))
    conn.commit()
    
    return jsonify({'status': 'success'})
  
  except Exception as e:
    return jsonify({'status': 'error', 'message': str(e)})
  
  finally:
    cur.close()
    conn.close()


#시간대 등록하는 api
@register_class_blueprint.route('/api/add_class_time/<class_id>', methods=['POST'])
@cross_origin()
@jwt_required() #토큰이 필요한 경우에만 요청을 처리
def add_class_date(class_id):
  data = request.get_json()
  class_date_str = data['classDateTime']
  capacity = data['capacity']
  
  #날짜와 시간 문자열을 datetime 객체로 변환 
  class_date = datetime.strptime(class_date_str, "%Y-%m-%dT%H:%M")
  #00초로 설정 (안할 시 오류남)
  class_date = class_date.replace(second=0)
  
  #토큰에서 사용자 정보 조회 (식별자로 저장된 user_id값을 추출 )
  user_id = get_jwt_identity()
  user_role = get_jwt().get('role') #토큰의 클레임에서 'role'값을 추출
  
  #role이 강사가 아니면 접근을 막음 
  if user_role != 'instructor':
    return jsonify({'status': 'error', 'message': 'Unauthorized access'})
  
  conn, cur = conn_mysqldb()
  
  #중복 등록 방지 
  cur.execute(
    "SELECT * FROM class_dates WHERE class_id = %s AND class_date = %s", (class_id, class_date)
  )
  if cur.fetchone()is not None:
    return jsonify({'status': 'error', 'message': 'The class time already exists'})
  
  try:
    cur.execute(
       "INSERT INTO class_dates (class_id, class_date, capacity) VALUES (%s, %s, %s)",(class_id, class_date, capacity)
    )
    conn.commit()
    
    return jsonify({'status': 'success'})
  except Exception as e:
    return jsonify({'status': 'error', 'message': str(e)})
  finally:
    cur.close()
    conn.close()
