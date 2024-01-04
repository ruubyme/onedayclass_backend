from flask_login import UserMixin

#사용자 모델 정의 
class User(UserMixin):
  def __init__(self, user_id, user_email, user_name, user_role, user_address):
    self.id = user_id
    self.email = user_email
    self.name = user_name
    self.role = user_role
    self.address = user_address
    
  def get_id(self):
    return self.id 
  
  def get_email(self):
    return self.email
  
  def get_name(self):
    return self.name 
  
  def get_role(self):
    return self.role
  
  def get_address(self):
    return self.address 
  
  def __str__(self):
    return f"User: {self.name}, Email: {self.email} id: {self.id}"