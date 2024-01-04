from flask import Blueprint, jsonify, request
from db_model.mysql import conn_mysqldb
from flask_cors import CORS, cross_origin
from flask_jwt_extended import jwt_required, get_jwt_identity
import traceback

review_blueprint = Blueprint('review', __name__)
  

#예약상태 확인
def check_if_user_has_confirmed_booking(cur, class_booking_id):
  cur.execute("SELECT status FROM class_booking WHERE id = %s", (class_booking_id,))
  booking_status = cur.fetchone()['status']
  return booking_status == 'confirmed'

#이미 작성된 리뷰가 존재하는지 확인 
def check_if_review_exists(cur, class_booking_id):
  cur.execute("SELECT COUNT(*) FROM class_reviews WHERE booking_id = %s", (class_booking_id,))
  review_count = cur.fetchone()['COUNT(*)']
  return review_count > 0

#데이터베이스의 user_id와 실제 요청자가 일치하는지 확인
def check_user_review(cur, review_id, user_id):
  cur.execute("SELECT COUNT(*) FROM class_reviews WHERE id = %s AND user_id = %s",  (review_id, user_id))  
  review_count = cur.fetchone()['COUNT(*)']
  return review_count > 0


#리뷰작성 API
@review_blueprint.route('/api/reviews', methods=['POST']) 
@jwt_required()
@cross_origin()
def createReview():
  data = request.get_json()
  class_id = data['classId']
  user_id = data['userId']
  class_date_id = data['classDateId']
  rating = data['rating']
  comment = data['comment'] if 'comment' in data else ""
  booking_id = data['bookingId']
  
  #빈 데이터 값이 있는지 확인
  if not all([class_id, user_id, class_date_id, booking_id]):
    error_msg = "Please fill in all required fields."
    return jsonify({'status': 'error', 'message': error_msg})
  
  
  conn, cur = conn_mysqldb()
  try:
    # 예약 상태가 'confirmed'가 아닐 경우
    if not check_if_user_has_confirmed_booking(cur, booking_id):
      return jsonify({'status': 'error', 'message': '완료된 수업이 아닙니다.'})

    if check_if_review_exists(cur, booking_id):
      return jsonify({'status': 'error', 'message': '이미 리뷰가 작성된 수업입니다.'})
    
    cur.execute("""
          INSERT INTO class_reviews (class_id, user_id, class_date_id, rating, comment, booking_id)
          VALUES (%s, %s, %s, %s, %s, %s)
          """, (class_id, user_id, class_date_id, rating, comment, booking_id))
    conn.commit()
    return jsonify({'status': 'success', 'message': '리뷰가 등록되었습니다.'})
    
  except Exception as e:
    conn.rollback()
    traceback.print_exc()
    return jsonify({'status': 'error', 'message': str(e)})
  finally:
    cur.close()
    conn.close()

#리뷰 조회 API
@review_blueprint.route('/api/reviews', methods=['GET']) 
@cross_origin()
def get_reviews():
  class_id = request.args.get('classId', None) #선택적 파라미터
  user_id = request.args.get('userId', None) #선택적 파라미터
  
  base_query = "SELECT * FROM class_reviews"
  params = ()
  if class_id is not None and user_id is not None:
    query = base_query +  " WHERE class_id = %s AND user_id = %s"
    params = (class_id, user_id)
  
  elif class_id is not None:
    query = base_query + " WHERE class_id = %s"
    params = (class_id,)
  elif user_id is not None:
      query = base_query + " WHERE user_id = %s"
      params = (user_id,)
  else: 
    query = base_query
  
  conn, cur = conn_mysqldb()
  try:
    cur.execute(query, params)
    reviews = cur.fetchall()
    
    detailed_reviews = []
    for review in reviews:
      #각 review 에 대한 클래스 정보 조회 
      cur.execute(
                "SELECT class_name, description FROM class WHERE id = %s",
                (review['class_id'],)
            )
      class_info = cur.fetchone() 
      #각 review 에 대한 클래스 날짜 정보 조회 
      cur.execute(
                "SELECT class_date FROM class_dates WHERE id = %s",
                (review['class_date_id'],)
            )
      class_date_info = cur.fetchone()
      
      #필요한 정보 합치기 
      detailed_review = {
        **review,
        'class_name': class_info['class_name'],
        'class_date': class_date_info['class_date']
      }
      detailed_reviews.append(detailed_review)
      detailed_reviews.sort(key=lambda x: x['created_at'], reverse=True)
    return jsonify({'status': 'success', 'data': detailed_reviews})
  except Exception as e:
    traceback.print_exc()
    return jsonify({'status': 'error', 'message': str(e)})
  finally:
    cur.close()
    conn.close()
    
#리뷰 삭제 API 
@review_blueprint.route('/api/reviews/<review_id>', methods=['DELETE']) 
@jwt_required()
@cross_origin()
def delete_reviews(review_id):
  user_id = get_jwt_identity()
  conn, cur = conn_mysqldb()
  
  try:
    if check_user_review(cur, review_id, user_id) == 0:
      return jsonify({'status': 'error', 'message': "해당 리뷰를 삭제할 권한이 없습니다."})
    
    cur.execute("DELETE FROM class_reviews WHERE id = %s", (review_id,))
    conn.commit()
    
    
    return jsonify({'status': 'success'})
  
  except Exception as e:
    conn.rollback()
    return jsonify({'status': 'error', 'message': str(e)}) 
  finally:
        
    cur.close()
    conn.close()
    
#강사의 comment 작성 API
@review_blueprint.route('/api/<review_id>/instructor_comment',methods=['POST'])
@jwt_required()
@cross_origin()
def create_comment_by_instructor(review_id):
  data = request.get_json()
  instructor_comment = data.get('comment')
  conn, cur = conn_mysqldb()
  if not instructor_comment:
    return jsonify({'status': 'error', 'message': 'No comment provided'})
  
  try:
    cur.execute(
            "UPDATE class_reviews SET instructor_comment = %s WHERE id = %s",
            (instructor_comment, review_id)
        )
    conn.commit()
    return jsonify({'status': 'success'})
  
  except Exception as e:
    conn.rollback()
    return jsonify({'status': 'error', 'message': str(e)}), 500
  finally:
    cur.close()
    conn.close()
    
#강사의 comment 삭제 API
@review_blueprint.route('/api/<review_id>/instructor_comment',methods=['DELETE'])
@jwt_required()
@cross_origin()
def delete_comment_by_instructor(review_id):
  conn, cur = conn_mysqldb()
  try:
    cur.execute(
            "UPDATE class_reviews SET instructor_comment = NULL WHERE id = %s",
            (review_id,)
        )
    conn.commit()
    return jsonify({'status': 'success'})
  
  except Exception as e:
    conn.rollback()
    return jsonify({'status': 'error', 'message': str(e)})
  
  finally:
    cur.close()
    conn.close()
    
  
  
