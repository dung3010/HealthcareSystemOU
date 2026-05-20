from flask import render_template, request, redirect, url_for, jsonify,flash, abort
from flask_login import login_user, logout_user, login_required, current_user
from happ import app, login, admin
from happ.models import User, UserRole
from happ import dao, utils
from happ.dao import add_user
import hashlib
from happ.models import Appointment, AppointmentStatus
from datetime import datetime, timedelta, date


def register_routes(app):
    @app.route("/")
    def index():
        return render_template('index.html')

    @app.route("/dashboard", methods=['GET', 'POST'])
    @login_required
    def dashboard():
        #POST
        if request.method == 'POST':
            if dao.is_user_blocked(current_user):
                flash("Tài khoản của bạn đang bị hạn chế đặt lịch do hủy quá 3 lần/tuần!", "danger")
                return redirect(url_for('dashboard'))

            try:
                appt_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
                appt_time = datetime.strptime(request.form.get('time'), '%H:%M').time()
                doctor_id = int(request.form.get('doctor_id'))
            except (ValueError, TypeError):
                flash('Dữ liệu ngày giờ không hợp lệ.', 'danger')
                return redirect(url_for('dashboard'))

            appt, err = dao.add_appointment(
                patient_id=current_user.id,
                doctor_id=doctor_id,
                appt_date=appt_date,
                appt_time=appt_time
            )

            if err:
                flash(err, 'danger')
            else:
                flash('Đặt lịch thành công!', 'success')

            return redirect(url_for('dashboard'))

        # GET
        doctors = dao.load_doctors()
        my_appointments = dao.get_appointments_by_user(user_id=current_user.id)
        today = date.today().isoformat()
        max_date = (date.today() + timedelta(days=30)).isoformat()

        today_count = sum(
            1 for a in my_appointments
            if a.app_date == date.today() and a.status != AppointmentStatus.CANCELLED
        )


        return render_template('dashboard.html',
                               doctors=doctors,
                               my_appointments=my_appointments,
                               today=today,
                               max_date=max_date,
                               today_count=today_count)

    @app.route('/register')
    def register_view():
        return render_template('layout/register.html')

    @app.route('/register', methods=['post'])
    def register_process():
        err_msg = ''
        if request.method == 'POST':
            data = request.form
            password = data.get('password')
            confirm = data.get('confirm_password')

            if password == confirm:
                try:
                    dao.add_user(name=data.get('name'),
                                 username=data.get('username'),
                                 password=password,
                                 avatar=request.files.get('avatar'))
                    return redirect('/login')
                except Exception as ex:
                    err_msg = str(ex)
            else:
                err_msg = 'Mật khẩu không khớp!'

        return render_template('layout/register.html', err_msg=err_msg)





    @app.route('/login', methods=['get', 'post'])
    def login_view():
        err_msg = ""
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')

            user = dao.auth_user(username=username, password=password)

            if user:
                login_user(user=user)

                next_page = request.args.get('next')

                if next_page:
                    return redirect(next_page)

                # KIỂM TRA ROLE ĐỂ ĐIỀU HƯỚNG
                if user.user_role == UserRole.ADMIN:
                    return redirect(next_page if next_page else '/admin')
                else:
                    return redirect(next_page if next_page else url_for('index'))
            else:
                err_msg = "Tên đăng nhập hoặc mật khẩu không chính xác!"

        return render_template('layout/login.html', err_msg=err_msg)

    # @app.route('/admin')
    # @login_required
    # def admin_dashboard():
    #     if current_user.user_role != UserRole.ADMIN:
    #         abort(403)  # Ngắt luồng và hiển thị trang lỗi 403
    #
    #     return render_template('admin.html')

    # === THÊM ROUTE ĐĂNG XUẤT Ở ĐÂY ===
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('index'))

    # === THÊM ROUTE HỦY LỊCH Ở ĐÂY ===
    @app.route('/dashboard/<int:appt_id>/cancel', methods=['POST'])
    @login_required
    def cancel_appointment(appt_id):
        is_admin = (current_user.user_role == UserRole.ADMIN)

        ok, msg = dao.cancel_appointment(
            appt_id=appt_id,
            current_user_id=current_user.id,
            is_admin=is_admin
        )
        flash(msg, 'success' if ok else 'danger')
        return redirect(url_for('dashboard'))
    @app.route('/api/get-slots')
    def api_get_slots():
        doctor_id = request.args.get('doctor_id')
        date_val = request.args.get('date')

        if not doctor_id or not date_val:
            return jsonify([])

        slots = utils.get_available_slots(doctor_id, date_val)
        return jsonify(slots)


# === CẤU HÌNH FLASK-LOGIN CHO VIỆC CHƯA ĐĂNG NHẬP ===
login.login_view = 'login_view'
login.login_message = "Hãy đăng nhập để thực hiện hành động này."






@login.user_loader
def load_user(user_id):
    from happ.models import User
    return User.query.get(int(user_id))

if __name__ == '__main__':
    from happ.admin import *
    register_routes(app)
    app.run(debug=True)