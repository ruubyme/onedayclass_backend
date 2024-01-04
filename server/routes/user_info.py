from flask import Blueprint, jsonify, request
from db_model.mysql import conn_mysqldb
from flask_jwt_extended import jwt_required
from flask_cors import cross_origin
from werkzeug.security import check_password_hash, generate_password_hash
import traceback

user_info_blueprint = Blueprint('user_info', __name__)

#user 정보 얻어오기 API 
@user_info_blueprint.route('/api/users/<user_id>', methods=['GET'])
@jwt_required()
def get_user_info(user_id):
  try:
    conn, cur = conn_mysqldb()
    
    cur.execute('SELECT * FROM user_info WHERE id = %s', (int(user_id)))
    userData = cur.fetchone()
    
    if userData:
      return jsonify({'status': 'success', 'data': userData})
    
    else:
      return jsonify({'status': 'error', 'message': 'User not found'})
    
  except Exception as e:
    return jsonify({'status': 'error', 'message': str(e)})
  
  finally:
    cur.close()
    conn.close()
    
#회원정보수정 API
@user_info_blueprint.route('/api/users/<user_id>', methods=['PATCH'])
@jwt_required()
def edit_user_info(user_id):
  conn, cur = conn_mysqldb()
  data = request.get_json()
  
  if not user_id or not data:
    return jsonify({'status': 'error', 'message': 'Invaild data'})
  
  try:
    set_clause = ', '.join(f"{key} = %s" for key in data.keys())
    values = list(data.values())
    
    cur.execute(f"UPDATE user_info SET {set_clause} WHERE id = %s", values + [user_id])
    conn.commit()
    
    #업데이트 된 데이터 가져오기 
    cur.execute("SELECT * FROM user_info WHERE id = %s", [user_id])
    updated_user_info = cur.fetchone()
    return jsonify({'status': 'success', 'data': updated_user_info})
  
  except Exception as e:
    conn.rollback() #오류 발생 시 롤백
    return jsonify({'status': 'error', 'message': str(e)})
  
  finally:
    cur.close()
    conn.close()
    
#비밀번호 수정 API 
@user_info_blueprint.route('/api/users/<user_id>/password', methods=['PATCH'])
@jwt_required()
@cross_origin()
def change_password(user_id):
    conn, cur = conn_mysqldb()
    data = request.get_json()
    current_password = data['currentPassword']
    new_password = data['newPassword']
    if not current_password or not new_password:
          return jsonify({'status': 'error', 'message': 'Password fields are required.'})
    
    try:
      #현재 비밀번호 검증 
      cur.execute('SELECT password FROM user_info WHERE id = %s', (int(user_id)))
      user_record = cur.fetchone()
      if user_record:
        stored_password_hash = user_record['password']
        if not check_password_hash(stored_password_hash, current_password):
          return jsonify({'status': 'error', 'message': '현재 비밀번호가 틀립니다.'})
        
        if check_password_hash(stored_password_hash, new_password):
          return jsonify({'status': 'error', 'message': '기존의 비밀번호와 동일합니다.'})
        
        #새 비밀번호 해시 생성 
        new_password_hash = generate_password_hash(new_password)
        
        cur.execute('UPDATE user_info SET password = %s WHERE id = %s', (new_password_hash, user_id))
        conn.commit()
        
        return jsonify({'status': 'success'})
      
      else:
        return jsonify({'status': 'error', 'message': 'User not found.'})
      
    except Exception as e:
      traceback_details = traceback.format_exc()
      print(traceback_details)
      conn.rollback() #오류 발생 시 롤백
      return jsonify({'status': 'error', 'message': str(e)})
    finally:
      cur.close()
      conn.close()

#특정 user의 북마크 리스트 얻어오기      
def get_bookmarkList(user_id):
  try:
    conn, cur = conn_mysqldb()
    
    cur.execute("SELECT * FROM user_bookmarks WHERE user_id = %s", (user_id,))
    bookmarks = cur.fetchall()
  
    detailed_bookmarks=[]
    for bookmark in bookmarks:
      #각 북마크의 class_id로 class 테이블에서 추가 정보 조회 
      cur.execute("SELECT class_name, description FROM class WHERE id = %s", (bookmark['class_id'],))
      class_info = cur.fetchone()
      
      detailed_bookmark = {
        **bookmark,
        'class_name': class_info['class_name'],
        'class_description': class_info['description'],
      }
      
      detailed_bookmarks.append(detailed_bookmark)
    return detailed_bookmarks
  
  except Exception as e:
    raise 
  
  finally:
    cur.close()
    conn.close()
  

#특정 user의 북마크 조회하기 
@user_info_blueprint.route('/api/user/<user_id>/bookmarks', methods=['GET'])
@cross_origin()
@jwt_required()
def get_bookmarks(user_id):
  class_id = request.args.get('classId', None) #선택적 파라미터 
  
  conn, cur = None, None 
  try: 
    #특정 클래스에 대한 북마크 정보 조회
    if class_id:
      conn, cur = conn_mysqldb()
      cur.execute("SELECT * FROM user_bookmarks WHERE user_id = %s AND class_id = %s", (user_id, class_id))
      if cur.fetchone():
        bookmarkStatus = True 
      else:
        bookmarkStatus = False
      return jsonify({"status": "success", "data": bookmarkStatus})
    
    #유저의 모든 북마크 정보 조회 
    else:
      bookmarks = get_bookmarkList(user_id)
      
      return jsonify({"status": "success", "data": bookmarks})
  except Exception as e:
    return jsonify({"status": "error", "message": str(e)})
  
  finally:
    if cur:
      cur.close()
    if conn:
      conn.close()
    
  
#북마크 추가하기 
@user_info_blueprint.route('/api/user/<user_id>/bookmarks', methods=['POST'])
@cross_origin()
@jwt_required()
def add_bookmarks(user_id):
  data = request.get_json()
  class_id = data.get('classId')
  conn, cur = conn_mysqldb()
  try:
    cur.execute("INSERT INTO user_bookmarks (user_id, class_id) VALUES (%s, %s)", (user_id, class_id))
    conn.commit()
    updated_bookmarks = get_bookmarkList(cur, user_id)
    return jsonify({'status': 'success', 'data': updated_bookmarks})
  
  except Exception as e:
    return jsonify({"status": "error", "message": str(e)})
  
  finally:
    cur.close()
    conn.close()
  
#북마크 삭제하기 
@user_info_blueprint.route('/api/user/<user_id>/bookmarks/<class_id>', methods=['DELETE'])
@cross_origin()
@jwt_required()
def remove_bookmarks(user_id, class_id):
  conn, cur = conn_mysqldb()
  try:
    cur.execute("DELETE FROM user_bookmarks WHERE user_id = %s AND class_id = %s", (user_id, class_id))
    conn.commit()
    updated_bookmarks = get_bookmarkList(cur, user_id)
    
    return jsonify({'status': 'success', 'data': updated_bookmarks})
  
  except Exception as e:
    return jsonify({"status": "error", "message": str(e)})

  finally:
    cur.close()
    conn.close()
      
#계정삭제
@user_info_blueprint.route('/api/users/<user_id>', methods=['DELETE'])
@jwt_required()
@cross_origin()
def delete_user(user_id):
  conn, cur = conn_mysqldb()
  
  try:
  # 사용자가 강사로 등록한 클래스 찾기
    cur.execute("SELECT id FROM class WHERE instructor_id = %s", (user_id,))
    classes = cur.fetchall()

    # 강사로 등록된 클래스와 연결된 class_dates 삭제
    for class_item in classes:
        cur.execute("DELETE FROM class_dates WHERE class_id = %s", (class_item['id'],))

    # 강사로 등록된 클래스 삭제
    cur.execute("DELETE FROM class WHERE instructor_id = %s", (user_id,))

    # 사용자와 관련된 나머지 데이터 삭제
    cur.execute("DELETE FROM class_reviews WHERE user_id = %s", (user_id,))
    cur.execute("DELETE FROM class_booking WHERE student_id = %s", (user_id,))
    cur.execute("DELETE FROM user_bookmarks WHERE user_id = %s", (user_id,))
    cur.execute("DELETE FROM payment WHERE user_id = %s", (user_id,))

    # 최종적으로 사용자 데이터 삭제
    cur.execute("DELETE FROM user_info WHERE id = %s", (user_id,))

    conn.commit()
    return jsonify({"status": "success"})

  except Exception as e:
      conn.rollback()
      return jsonify({"status": "error", "message": str(e)})
  finally:
      cur.close()
      conn.close()
