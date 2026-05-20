from flask_admin import Admin, AdminIndexView, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user, logout_user
from flask import redirect, url_for, abort
from happ import app, db
from happ.models import User, Doctor, Appointment, UserRole, DoctorSchedule


class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role == UserRole.ADMIN

    def inaccessible_callback(self, name, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login_view'))
        else:
            abort(403)

class AuthenticatedModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role == UserRole.ADMIN

    def inaccessible_callback(self, name, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login_view'))
        else:
            abort(403)

class LogoutView(BaseView):
    @expose('/')
    def index(self):
        logout_user()
        return redirect(url_for('index'))

    def is_accessible(self):
        return current_user.is_authenticated


class AppointmentModelView(AuthenticatedModelView):
    column_list = ['id', 'patient', 'doctor', 'app_date', 'slot_time', 'status']
    column_editable_list = ['status']
    column_labels = {
        'patient': 'Bệnh nhân',
        'doctor': 'Bác sĩ',
        'app_date': 'Ngày khám',
        'slot_time': 'Khung giờ',
        'status': 'Trạng thái'
    }

admin = Admin(app=app, name='HỆ THỐNG QUẢN TRỊ OU', index_view=MyAdminIndexView())
admin.add_view(AuthenticatedModelView(User, db.session, name="Người dùng"))
admin.add_view(AuthenticatedModelView(Doctor, db.session, name="Bác sĩ"))
admin.add_view(AppointmentModelView(Appointment, db.session, name="Lịch hẹn"))
admin.add_view(AuthenticatedModelView(DoctorSchedule, db.session, name="Lịch trực bác sĩ"))
admin.add_view(LogoutView(name='Đăng xuất', endpoint='admin_logout'))