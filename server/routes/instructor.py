from flask import Blueprint, jsonify, request
from db_model.mysql import conn_mysqldb
from flask_cors import cross_origin
import json

instructor_blueprint = Blueprint('instructor', __name__)

#강사의 id로 등록된 class를 불러오는 API
@instructor_blueprint.route('/api/get_classes_by_instructor', methods=["GET"])
@cross_origin()
def get_classes_by_instructor():
  instructor_id = request.args.get('id')
  
  try:
    conn, cur = conn_mysqldb()
    cur.execute(
       "SELECT * FROM class WHERE instructor_id = %s", (int(instructor_id),)
    )
    classes = cur.fetchall()
    
    #프로퍼티 명 변환 후 응답 
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
    
    #Class가 없을 경우에도 에러 메시지 대신 빈 리스트를 반환 
    return jsonify ({'status': 'success', 'data': modified_classes})
  except Exception as e:
    return jsonify({'status': 'error',  'message': str(e)})
  
  finally:
    cur.close()
    conn.close()
    
#클래스 삭제 
@instructor_blueprint.route('/api/class', methods=['DELETE'])
def delete_class_by_instructor():
  instructor_id = request.args.get('instructor_id')
  class_id = request.args.get('class_id')
  
  try:
    conn, cur = conn_mysqldb()
    
    #1. class_dates 테이블에서 해당 class_id와 관련된 데이터 전부 삭제 
    
    cur.execute(
            "DELETE FROM class_dates WHERE class_id = %s", (int(class_id))
        )
    
    #2. class 테이블에서 해당 class 삭제
    cur.execute(
            "DELETE FROM class WHERE id = %s AND instructor_id = %s", (int(class_id), int(instructor_id))
        )
    
    if cur.rowcount == 0:
      return jsonify({'status': 'error', 'message': 'No class found or you do not have permission to delete.'})
    conn.commit()
    return jsonify({'status': 'success'})
  
  except Exception as e:
    conn.rollback() #오류 발생 시 롤백
    return jsonify({'status': 'error', 'message': str(e)})
  
  finally:
    cur.close()
    conn.close()
    
#클래스 수정 
@instructor_blueprint.route('/api/class', methods=['PATCH'])
def update_class_by_instructor():
  instructor_id = request.json.get('instructor_id')
  class_id = request.json.get('class_id')
  data = request.json.get('data')
  
  if not class_id or not instructor_id or not data:
      return jsonify({'status': 'error', 'message': 'Invalid data'})
    
  #클라이언트에서 받은 필드 이름을 서버의 DB 필드 이름으로 변환
  field_mappings = {
    "curriculums": "curriculum",
    "targetStudents": "target_student",
    "className": "class_name"
  }
  
  for client_field, db_field in field_mappings.items():
    if client_field in data:
      data[db_field] = data.pop(client_field)
      
  if "curriculum" in data:
    data["curriculum"] = json.dumps(data["curriculum"])
    
  if "target_student" in data:
      data["target_student"] = json.dumps(data["target_student"])
  
  #업데이트 할 부분 sql 쿼리 생성 
  columns_to_update = ', '.join(f"{key} = %s" for key in data.keys())
  sql_query = f"UPDATE class SET {columns_to_update} WHERE id = %s AND instructor_id = %s"
  values = list(data.values()) + [class_id, instructor_id]
  
  try:
    conn, cur = conn_mysqldb()
    cur.execute(sql_query, values)
    conn.commit()
    return jsonify({'status': 'success'})
  
  except Exception as e:
    return jsonify({'status': 'error', 'message': str(e)})
  
  finally:
    cur.close()
    conn.close()
  