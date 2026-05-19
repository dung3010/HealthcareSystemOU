from flask_admin import Admin, AdminIndexView, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user, logout_user
from flask import redirect, url_for
from happ import app, db
from happ.models import User, Doctor, Appointment, UserRole, DoctorSchedule

# Lớp bảo vệ cho trang Dashboard chính của Admin
class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        # Chỉ cho phép nếu đã đăng nhập và là ADMIN
        return current_user.is_authenticated and current_user.user_role == UserRole.ADMIN

    def inaccessible_callback(self, name, **kwargs):
        # Nếu không có quyền, đá về trang login
        return redirect(url_for('login_view'))

# Lớp bảo vệ cho các bảng dữ liệu (User, Doctor, Appointment)
class AuthenticatedModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role == UserRole.ADMIN

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login_view'))

class LogoutView(BaseView):
    @expose('/')
    def index(self):
        logout_user() # Xóa phiên đăng nhập
        return redirect(url_for('index')) # Chuyển hướng về trang chủ

    def is_accessible(self):
        return current_user.is_authenticated

# Khởi tạo Admin với IndexView tùy chỉnh
admin = Admin(app=app, name='HỆ THỐNG QUẢN TRỊ OU', index_view=MyAdminIndexView())
# Đưa các bảng vào trang Admin
admin.add_view(AuthenticatedModelView(User, db.session, name="Người dùng"))
admin.add_view(AuthenticatedModelView(Doctor, db.session, name="Bác sĩ"))
admin.add_view(AuthenticatedModelView(Appointment, db.session, name="Lịch hẹn"))
admin.add_view(AuthenticatedModelView(DoctorSchedule, db.session, name="Lịch trực bác sĩ"))
admin.add_view(LogoutView(name='Đăng xuất', endpoint='admin_logout'))