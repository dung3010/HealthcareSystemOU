from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_admin import Admin
import cloudinary



app = Flask(__name__)
app.secret_key = '&(^&*^&*^U*HJBJKHJLHKJHK&*%^&57869856858'
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:Abc123@localhost/hcdb?charset=utf8mb4"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
db = SQLAlchemy(app=app)

login = LoginManager(app=app)
login.login_view = 'login_view'


login.login_message = "Vui lòng đăng nhập để thực hiện chức năng đặt lịch khám!"
login.login_message_category = "info"



cloudinary.config(cloud_name='dref2n2l6',
api_key='957731323237422',
api_secret='Mb82QfXhiCi8S5hYpQtLltvzzEg')