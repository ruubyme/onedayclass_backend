from flask import Blueprint, jsonify, request
from db_model.mysql import conn_mysqldb
from flask_jwt_extended import jwt_required, get_jwt_identity
import traceback
from flask_cors import cross_origin
from dotenv import load_dotenv
import os
import requests



class_booking_blueprint = Blueprint('class_booking', __name__)

load_dotenv('.env.local')
KAKAOPAY_ADMIN_KEY = os.getenv('KAKAOPAY_ADMINKEY')


#사용자가 특정 예약날짜를 예약했는지 확인하는 함수 
def check_user_booking(cur, student_id, class_date_id):
    try:
        cur.execute('''
            SELECT status FROM class_booking
            WHERE student_id = %s AND class_date_id = %s
            ''', (student_id, class_date_id))
        booking_result = cur.fetchone()
        return booking_result['status'] if booking_result else None
    except Exception as e:
        print(e)
        raise e

  
#특정 클래스의 모든 예약날짜 데이터 조회 
def get_class_dates_info(cur, class_id, student_id=None):
  try:
    #class_dates 테이블에서 특정 class_id에 대한 모든 class_dates와 해당 예약 수를 가져옴
    cur.execute('''
            SELECT cd.id, cd.class_date, cd.capacity, c.class_name as class_name,
            COUNT(case when cb.status <> 'cancelled' then 1 else null end) as booking_count
            FROM class_dates cd
            LEFT JOIN class_booking cb ON cd.id = cb.class_date_id AND cb.status <> 'cancelled'
            JOIN class c ON cd.class_id = c.id  # class 테이블과 JOIN
            WHERE cd.class_id = %s
            GROUP BY cd.id, c.class_name
            ''', (int(class_id)))
    
    class_dates_result = cur.fetchall()
    
    all_class_dates = []
    
    for row in class_dates_result:    
      class_date_id = row['id']
      class_date = row['class_date']
      class_capacity = row['capacity']
      booking_count = row['booking_count']
      class_name = row['class_name']
      
      remaining_seats = class_capacity - booking_count
      user_has_booked = False
      if student_id:
        user_has_booked = check_user_booking(cur, student_id, class_date_id) if student_id else None
      
      class_date_data = {
          'class_id': class_id,
          'class_date_id': class_date_id,
          'class_date': class_date,
          'class_capacity': class_capacity,
          'remaining_seats': remaining_seats,
          'user_has_booked': user_has_booked,
          'class_name': class_name,
      } 
      all_class_dates.append(class_date_data)
    return all_class_dates
  except Exception as e:
    print(e)
    raise

#class_date_id로 class 정보 얻어오기
def get_class_info_by_date_id(class_date_id):
  try:
      conn, cur = conn_mysqldb()
      cur.execute("""
          SELECT * FROM class_dates WHERE id = %s
      """, (class_date_id,))
      class_date_info = cur.fetchone()
      
      if class_date_info:
          class_id = class_date_info['class_id']
          # class 테이블에서 클래스의 상세 정보를 조회
          cur.execute("""
              SELECT * FROM class WHERE id = %s
          """, (class_id,))
          class_info = cur.fetchone()
          return class_info
      return None
  except Exception as e:
      print(e)
      raise
  finally:
      cur.close()
      conn.close()

#결제 진행 시 데이터처리 
def create_payment_record(user_id, class_date_id, amount):
  conn, cur = conn_mysqldb()
  try:
    cur.execute("""
            INSERT INTO payment (user_id, class_date_id, amount, status)
            VALUES (%s, %s, %s, 'pending')
        """, (user_id, class_date_id, amount))
    payment_id = cur.lastrowid
    conn.commit()
    return payment_id
  except Exception as e:
      conn.rollback()
      raise e
  finally:
      cur.close()
      conn.close()
      
#결제 성공 후 데이터처리 
def updated_booking_and_payment_status(class_date_id, payment_id):
  conn, cur = conn_mysqldb()
  try:
    # class_booking 테이블 업데이트
      cur.execute("""
          UPDATE class_booking
          SET status = 'confirmed'
          WHERE class_date_id = %s
      """, (class_date_id,))

      # payment 테이블 업데이트
      cur.execute("""
          UPDATE payment
          SET status = 'completed'
          WHERE id = %s
      """, (payment_id,))

      conn.commit()
  except Exception as e:
      conn.rollback()
      raise e
  finally:
      cur.close()
      conn.close()
      
#tid 저장 
def save_tid(payment_id, tid):
  conn, cur = conn_mysqldb()
  try:
    conn, cur = conn_mysqldb()
    cur.execute("""
        UPDATE payment
        SET tid = %s
        WHERE id = %s
    """, (tid, payment_id))
    conn.commit()
  except Exception as e:
      conn.rollback()
      raise e
  finally:
      cur.close()
      conn.close()
      
#tid 조회 
def gett_tid_by_payment_id(payment_id):
  conn, cur = conn_mysqldb()
  try:
    cur.execute("""
        SELECT tid
        FROM payment
        WHERE id = %s
    """, (payment_id,))
    result = cur.fetchone()
    return result['tid'] if result else None
  except Exception as e:
      print(e)
      return None
  finally:
      cur.close()
      conn.close()
    

#특정 클래스의 모든 예약날짜 가져오기
@class_booking_blueprint.route('/api/class_dates/<class_id>', methods=['GET'])
def get_class_dates(class_id):
  conn, cur = conn_mysqldb()
  try:
    student_id = request.args.get('student_id')
    
    class_dates = get_class_dates_info(cur, class_id, student_id)
    return jsonify({'status': 'success', 'all_class_dates': class_dates})    
    
  except Exception as e:
    traceback.print_exc()
    return jsonify({'status': 'error', 'message': str(e)})
  finally:
    cur.close()
    conn.close()

  
#특정 유저가 예약한 예약정보 모두 가져오기
@class_booking_blueprint.route('/api/class/<user_id>/booking', methods=['GET'])
@jwt_required()
def get_class(user_id):
  conn, cur = conn_mysqldb()
  
  try:
    # 해당 유저의 모든 클래스 예약 정보 조회
    cur.execute(
        "SELECT * FROM class_booking WHERE student_id = %s",
        (user_id,)
    )
      
    bookings = cur.fetchall()
    
    detailed_bookings = []
    for booking in bookings:
      #각 예약에 대한 클래스 정보 조회
      cur.execute(
                "SELECT class_name, description FROM class WHERE id = %s",
                (booking['class_id'],)
            )
      class_info = cur.fetchone() 
      #각 예약에 대한 클래스 날짜 정보 조회 
      cur.execute(
                "SELECT class_date FROM class_dates WHERE id = %s",
                (booking['class_date_id'],)
            )
      class_date_info = cur.fetchone()
      
      #각 예약에 대한 리뷰 정보 조회 
      cur.execute(
        "SELECT * FROM class_reviews WHERE class_date_id = %s AND user_id = %s",
        (booking['class_date_id'], user_id)
      )
      review_info = cur.fetchone()
      
      #필요한 정보 합치기 
      detailed_booking = {
        'id': booking['id'],
        'student_id': booking['student_id'],
        'class_id': booking['class_id'],
        'class_date_id': booking['class_date_id'],
        'status': booking['status'],
        'class_name': class_info['class_name'],
        'class_description': class_info['description'],
        'class_date': class_date_info['class_date'],
        'has_reviewed': bool(review_info),
      }
      
      detailed_bookings.append(detailed_booking)
    
    detailed_bookings.sort(key=lambda x: x['class_date'], reverse=True)
    return jsonify({"status": "success", "data": detailed_bookings})
  
  except Exception as e:
    traceback.print_exc()
    return jsonify({"status": "error", "message": str(e)})
  
  finally:
    cur.close()
    conn.close()
    
#class_date_id 로 예약한 예약자 명단 가져오기 
@class_booking_blueprint.route('/api/<class_date_id>/attendees', methods=['GET'])
def get_attendees_by_class_date_id(class_date_id):
  conn, cur = conn_mysqldb()
  query = """
    SELECT
      class_booking.*,
      user_info.name,
      user_info.email,
      user_info.phone_number
    FROM
      class_booking
    INNER JOIN user_info ON class_booking.student_id = user_info.id
    WHERE
      class_booking.class_date_id = %s;
    """
  try:
    cur.execute(query, (class_date_id,))
    attendees = cur.fetchall()
    return jsonify({"status": "success", "data": attendees})
  
  except Exception as e:
    traceback.print_exc()
    return jsonify({"status": "error", "message": str(e)})
  
  finally:
    cur.close()
    conn.close()
  
#클래스 예약하기 
@class_booking_blueprint.route('/api/class/booking', methods=['POST'])
@jwt_required()
def book_class():
  conn, cur = conn_mysqldb()
  try:
    data = request.get_json()
    class_id = data['classId']
    class_date_id = data['classDateId']
    student_id = get_jwt_identity()
    
    
    #중복 예약 확인
    booking_status = check_user_booking(cur, student_id, class_date_id)
    if booking_status in ['confirmed', 'pending']:
      return jsonify({'status': 'error', 'message': '이미 예약된 수업입니다.'})
    
    #취소된 예약이 있는 경우 상태 업데이트 
    if booking_status == 'cancelled':
      update_query = """
                UPDATE class_booking
                SET status = 'pending'
                WHERE student_id = %s AND class_date_id = %s AND status = 'cancelled'
            """
      cur.execute(update_query, (student_id, class_date_id))
    else:
      #예약 진행 
      query = """
          INSERT INTO class_booking (class_id, student_id, class_date_id, status)
          VALUES (%s, %s, %s, 'pending')
          """
      cur.execute(query, (class_id, student_id, class_date_id))
      
    #각 class_dates에 대한 예약 개수 업데이트 
    updated_class_dates_info = get_class_dates_info(cur, class_id, student_id)
    
    conn.commit()
    
    return jsonify({'status': 'success', 'data': updated_class_dates_info})
  
  except Exception as e:
    conn.rollback() #오류 발생 시 변경 사항 롤백
    traceback.print_exc()
    return jsonify({'status': 'error', 'message': str(e)})
  
  finally:
    cur.close()
    conn.close()
    
#클래스 예약 취소하기 
@class_booking_blueprint.route('/api/class/booking', methods=['PATCH'])
@jwt_required()
@cross_origin()
def cancel_booking():
  try:
    conn, cur = conn_mysqldb()
    student_id = get_jwt_identity()
    data = request.get_json()
    class_date_id = data['classDateId']
    class_id = data['classId']
        
    query = """
    UPDATE class_booking 
    SET status = 'cancelled' 
    WHERE class_date_id = %s AND student_id = %s AND status IN ('pending', 'confirmed')
    """
    
    cur.execute(query, (class_date_id, student_id,))
    if cur.rowcount == 0:
      return jsonify({"status": "error", "message": "Booking not found or already cancelled"})
    
     #각 class_dates에 대한 예약 개수 업데이트 
    updated_class_dates_info = get_class_dates_info(cur, class_id, student_id)
    conn.commit()
    return jsonify({"status": "success", "data": updated_class_dates_info})
  
  except Exception as e:
    conn.rollback() #오류 발생 시 변경 사항 롤백
    return jsonify({"status": "error", "message": str(e)})
  
  finally:
    cur.close()
    conn.close()
    
#클래스 결제 
@class_booking_blueprint.route('/api/<class_date_id>/payment', methods=['POST'])
@jwt_required()
@cross_origin()
def payment(class_date_id):
  user_id = get_jwt_identity()
  
  class_info = get_class_info_by_date_id(class_date_id)
  if not class_info:
    return jsonify({"status": "error", "message": "Class not found"})
  
  item_name = class_info['class_name']
  amount = class_info['cost']
  
  try:
    payment_id = create_payment_record(user_id, class_date_id, amount)
  except Exception as e:
    return jsonify({'status': 'error', 'message': str(e)})
  
  #카카오페이 결제 준비 요청
  headers = {
        "Authorization": f"KakaoAK {KAKAOPAY_ADMIN_KEY}",
        "Content-type": "application/x-www-form-urlencoded;charset=utf-8"
    }
  
  params = {
      "cid": "TC0ONETIME",  # 테스트용 CID
      "partner_order_id": payment_id,  # 가맹점 주문번호
      "partner_user_id": user_id,  # 가맹점 회원 ID
      "item_name": item_name,  # 상품명
      "quantity": 1,  # 상품 수량
      "total_amount": amount,  # 총 금액
      "tax_free_amount": 0,  # 비과세 금액
      "approval_url": f"http://localhost:3000/payment/success/{class_date_id}",  # 결제 성공 시 리다이렉트 URL
      "cancel_url": f"http://localhost:3000/payment/{class_date_id}",  # 결제 취소 시 리다이렉트 URL
      "fail_url": f"http://localhost:3000/payment/{class_date_id}"  # 결제 실패 시 리다이렉트 URL
  }
  
  response = requests.post("https://kapi.kakao.com/v1/payment/ready", headers=headers, data=params)
  response_data = response.json()
  
  if response.status_code == 200:
    tid = response_data.get("tid")
    try:
      save_tid(payment_id, tid)
    except Exception as e:
       return jsonify({'status': 'error', 'message': str(e)})
    
    responseData = {
      "next_redirect_pc_url": response_data.get("next_redirect_pc_url"),
      "paymentId": payment_id,
    }
    return jsonify({"status": "success", "data": responseData})
  else:
    traceback.print_exc()
    return jsonify({"status": "error", "message": "Failed to prepare payment"})

#클래스 결제 성공 
@class_booking_blueprint.route('/api/<class_date_id>/payment/success', methods=['POST'])
@jwt_required()
@cross_origin()
def payment_success(class_date_id):
  data = request.get_json()
  pg_token = data.get('pg_token')
  payment_id = data.get('paymentId')
  user_id = get_jwt_identity()
  tid = gett_tid_by_payment_id(payment_id)
  
  if not tid or not pg_token or not payment_id:
    return  jsonify({"status": "error", "message": "Required payment information is missing or invalid"})

  headers = {
        "Authorization": f"KakaoAK {KAKAOPAY_ADMIN_KEY}",
        "Content-type": "application/x-www-form-urlencoded;charset=utf-8"
    }
  data = {
        "cid": "TC0ONETIME",  # 테스트용 CID
        "tid": tid,          # 거래 ID
        "partner_order_id": payment_id,  # 가맹점 주문번호
        "partner_user_id": user_id,  # 가맹점 회원 ID
        "pg_token": pg_token # pg_token
    }
  response = requests.post("https://kapi.kakao.com/v1/payment/approve", headers=headers, data=data)
  payment_info = response.json()
  if response.status_code == 200:
    updated_booking_and_payment_status(class_date_id, payment_id)
    return jsonify({"status": "success"})
  
  else:
    traceback.print_exc()
    return ({"status": "error", "message": "Payment failed"})
  
  

    
      
      
    