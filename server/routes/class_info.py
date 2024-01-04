from flask import Blueprint, jsonify, request
from db_model.mysql import conn_mysqldb
from flask_cors import cross_origin
import json
import traceback


class_info_blueprint = Blueprint('class_info', __name__)

def get_class_data_by_id(class_id):
    conn, cur = conn_mysqldb()
    try:
        cur.execute(
            'SELECT class_name, description, location, cost, target_student, content, curriculum, latitude, longitude FROM class WHERE id = %s', (int(class_id),)
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()

#get_class_addresses API 
@class_info_blueprint.route('/api/class_addresses', methods=["GET"])
def get_class_addresses():
  try:
    #db 연결 
    conn, cur = conn_mysqldb()
    
    #class 테이블에서 주소(location), id 컬럼 값 조회
    cur.execute('SELECT id, location FROM class')
    #class 테이블에서 class_id 값 조회 
    
    addresses = []
    for row in cur.fetchall():
      address = {
        'class_id': row['id'],
        'location': row['location']
      }
      addresses.append(address)
      
    return jsonify({'status': 'success', 'data':addresses})
  except Exception as e:
    return jsonify({'status': 'error', 'message': str(e)})
  
  finally:
    cur.close()
    conn.close()
  
#추가적인 수업 정보 API
@class_info_blueprint.route('/api/class_additional_data/<class_id>', methods=['GET'])
def get_class_additional_data(class_id):
  try:
    #db연결 
    conn, cur = conn_mysqldb()
    
    #class_id를 사용하여 클래스의 추가 정보 조회 
    cur.execute('SELECT id, class_name, cost, description FROM class WHERE id = %s', (int(class_id)))
    classData = cur.fetchone()
    
    if classData:
      class_additional_data = {
        'class_id': classData['id'],
        'class_name': classData['class_name'],
        'class_description': classData['description'],
        'cost': classData['cost'],
      }
      return jsonify({'status': 'success','data': class_additional_data})
    else:
      return jsonify({'status': 'error','message': 'Class not found'})
    
  except Exception as e:
    return jsonify({'status': 'error','message': str(e)})
  
  finally:
    cur.close()
    conn.close()
  
  
#class_detail page에 필요한 데이터 조회 API 
@class_info_blueprint.route('/api/get_class_detail/<class_id>', methods=["GET"])
def get_class_detail(class_id):
    classData = get_class_data_by_id(class_id)
    
    if classData:
      class_additional_data = {
        'className': classData['class_name'],
        'description': classData['description'],
        'location': classData['location'],
        'cost': classData['cost'],
        'targetStudents': json.loads(classData['target_student']),
        'content': classData['content'],
        'curriculums': json.loads(classData['curriculum']),
        'latitude': classData['latitude'],
        'longitude': classData['longitude']
      }
      return jsonify({'status': 'success', 'data': class_additional_data})
    else:
      return jsonify({'status': 'error', 'message': 'Class not found'})


    
#class_list에 필요한 모든 class 조회 
@class_info_blueprint.route('/api/class_list', methods=['GET'])
@cross_origin()
def get_class_list():
  city = request.args.get('city')
  district = request.args.get('district')
  
  conn, cur = conn_mysqldb()
  
  base_query = 'SELECT class_name, description, location, cost, id FROM class'
  conditions = []
  query_parameters = []
  
  if city:
    conditions.append("location LIKE %s")
    query_parameters.append(f"%{city}%")
  if district:
    conditions.append("location LIKE %s")
    query_parameters.append(f"%{district}%")
    
  if conditions:
    base_query += " WHERE " + " AND ".join(conditions)
    
    
  try:
    cur.execute(base_query, tuple(query_parameters))
    classes = cur.fetchall()
    
    #class_name을 className으로 변환 후 응답 
    modified_classes = []
    for class_data in classes:
      modified_data = {
        "classId": class_data["id"],
        "className": class_data["class_name"],
        "description": class_data["description"],
        "location": class_data["location"],
        "cost": class_data["cost"]
      }
      modified_classes.append(modified_data)
    
    return jsonify({'status': 'success', 'data': modified_classes})
  
  except Exception as e:
    return jsonify({'status': 'error', 'message': str(e)})
    
  finally:
    cur.close()
    conn.close()
    
# 주변 class 조회 
@class_info_blueprint.route('/api/nearby_class_list', methods=['GET'])
@cross_origin()
def get_nearby_class_list():
  minLat = request.args.get('minLat')
  maxLat = request.args.get('maxLat')
  minLng = request.args.get('minLng')
  maxLng = request.args.get('maxLng')
  
  conn, cur = conn_mysqldb()
  
  # 위도와 경도 값을 바탕으로 DB에서 조회
  query = """
  SELECT class_name, description, location, cost, id 
  FROM class
  WHERE latitude BETWEEN %s AND %s AND longitude BETWEEN %s AND %s
  """
  
  try:
    cur.execute(query, (minLat, maxLat, minLng, maxLng))
    classes = cur.fetchall()
    
     # class_name을 className으로 변환 후 응답 
    modified_classes = []
    for class_data in classes:
        modified_data = {
            "classId": class_data["id"],
            "className": class_data["class_name"],
            "description": class_data["description"],
            "location": class_data["location"],
            "cost": class_data["cost"]
        }
        modified_classes.append(modified_data)
    
    return jsonify({'status': 'success', 'data': modified_classes})
  
  except Exception as e:
      return jsonify({'status': 'error', 'message': str(e)})
    
  finally:
    cur.close()
    conn.close()
    
#class_date_id 로 예약날짜 조회 
@class_info_blueprint.route('/api/<class_date_id>/dates', methods=['GET'])
@cross_origin()
def get_class_date_by_class_date_id(class_date_id):
  conn, cur = conn_mysqldb()
  try:
    cur.execute("SELECT class_date FROM class_dates WHERE id = %s", (class_date_id,))
    class_date = cur.fetchone()
    
    #조회된 데이터가 없을 경우 
    if class_date is None:
      return jsonify({"status": "error", "message": "Class date not found"})
    
    return jsonify({"status": "success", "data": class_date})
  
  except Exception as e:
    traceback.print_exc()
    return jsonify({"status": "error", "message": str(e)})
  
  finally:
    cur.close()
    conn.close()
    
#class_date_id 로 class_id 조회 
@class_info_blueprint.route('/api/<class_date_id>/classId', methods=['GET'])
@cross_origin()
def get_class_id_by_class_date_id(class_date_id):
  conn, cur = conn_mysqldb()
  try:
    cur.execute("SELECT class_id FROM class_dates WHERE id = %s", (class_date_id,))
    class_id = cur.fetchone()
    
    #조회된 데이터가 없을 경우 
    if class_id is None:
      return jsonify({"status": "error", "message": "Class data not found"})
    
    return jsonify({"status": "success", "data": class_id})
  
  except Exception as e:
    traceback.print_exc()
    return jsonify({"status": "error", "message": str(e)})
  
  finally:
    cur.close()
    conn.close()


    
  
  
    
  

  

  
  
