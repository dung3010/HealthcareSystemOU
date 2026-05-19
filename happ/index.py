from flask import render_template, request, redirect, url_for, jsonify,flash
from flask_login import login_user, logout_user, login_required, current_user
from happ import app, login, admin
from happ.models import User, UserRole
from happ import dao, utils
from happ.dao import add_user
import hashlib
from happ.models import Appointment
from datetime import datetime, timedelta, date


def register_routes(app):
    @app.route("/")
    def index():
        return render_template('index.html')

    @app.route("/dashboard")
    @login_required
    def dashboard():
    # Sau này có thể thêm @login_required ở đây để bắt buộc đăng nhập
    # Load dữ liệu cho Dashboard
        doctors = dao.load_doctors()
        # Lấy danh sách lịch hẹn của người dùng hiện tại để hiển thị ở bảng
        my_appointments = dao.get_appointments_by_user(user_id=current_user.id)

        # Các giá trị giới hạn cho input date
        today = date.today().isoformat()
        max_date = (date.today() + timedelta(days=30)).isoformat()

        # Đếm số lịch hôm nay còn hiệu lực (không tính đã hủy)
        from happ.models import AppointmentStatus
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
        # return render_template('dashboard.html')

    @app.route('/dashboard', methods=['POST'])
    @login_required
    def book_process():
        if dao.is_user_blocked(current_user):
            flash("Tài khoản của bạn đang bị hạn chế đặt lịch do hủy quá 3 lần/tuần!", "danger")
            return redirect(url_for('dashboard'))
        from datetime import datetime
        data = request.form

        try:
            appt_date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
            appt_time = datetime.strptime(data.get('time'), '%H:%M').time()
            doctor_id = int(data.get('doctor_id'))
        except (ValueError, TypeError):
            flash('Dữ liệu ngày giờ không hợp lệ.', 'danger')
            return redirect(url_for('dashboard'))

        # Gọi DAO để xử lý ràng buộc (20 khách/ngày, nghỉ phép...)
        appt, err = dao.add_appointment(
            patient_id=current_user.id,
            doctor_id=doctor_id,
            appt_date=appt_date,
            appt_time=appt_time
        )

        if err:
            flash(err, 'danger')  # err là thông báo lỗi từ DAO
            return redirect(url_for('dashboard'))

        flash('Đặt lịch thành công!', 'success')
        return redirect(url_for('dashboard'))



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
                    # Gọi hàm từ dao.py
                    dao.add_user(name=data.get('name'),
                                 username=data.get('username'),
                                 password=password,
                                 avatar=request.files.get('avatar'))
                    return redirect('/login')
                except Exception as ex:
                    err_msg = str(ex)  # Hiển thị lỗi từ dao (ví dụ: Username đã tồn tại)
            else:
                err_msg = 'Mật khẩu không khớp!'

        return render_template('layout/register.html', err_msg=err_msg)

    @app.route('/dashboard/<int:appt_id>/cancel', methods=['POST'])
    @login_required
    def cancel_appointment(appt_id):
        ok, msg = dao.cancel_appointment(appt_id=appt_id, current_user=current_user)
        flash(msg, 'success' if ok else 'danger')
        return redirect(url_for('dashboard'))



    @app.route('/login', methods=['get', 'post'])
    def login_view():
        err_msg = ""
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')

            # Gọi dao để kiểm tra database
            user = dao.auth_user(username=username, password=password)

            if user:
                login_user(user=user)

                # --- Lấy đường link cũ mà người dùng muốn vào (nếu có) ---
                next_page = request.args.get('next')

                next_page = request.args.get('next')

                # 2. Nếu có 'next', ưu tiên quay lại trang đó ngay
                if next_page:
                    return redirect(next_page)

                # KIỂM TRA ROLE ĐỂ ĐIỀU HƯỚNG
                if user.user_role == UserRole.ADMIN:
                    # Nếu có link cũ (next_page) thì ưu tiên về link đó, không thì về /admin
                    return redirect(next_page if next_page else '/admin')
                else:
                    # Nếu có link cũ thì ưu tiên về link đó, không thì về trang chủ
                    return redirect(next_page if next_page else url_for('index'))
            else:
                err_msg = "Tên đăng nhập hoặc mật khẩu không chính xác!"

        return render_template('layout/login.html', err_msg=err_msg)

    # === THÊM ROUTE ĐĂNG XUẤT Ở ĐÂY ===
    @app.route('/logout')
    @login_required # Chỉ ai đăng nhập rồi mới được đăng xuất
    def logout():
        logout_user() # Xóa session
        return redirect(url_for('index')) # Đá về trang chủ

    # === THÊM ROUTE HỦY LỊCH Ở ĐÂY ===
    @app.route('/api/cancel-appointment/<int:app_id>', methods=['POST'])
    @login_required  # Bắt buộc phải đăng nhập mới được gọi
    def api_cancel_appointment(app_id):
        # Gọi hàm dao xử lý hủy
        success, message = dao.cancel_appointment(app_id, current_user.id)

        if success:
            return jsonify({'status': 'success', 'message': message})
        else:
            return jsonify({'status': 'error', 'message': message}), 400

    @app.route('/api/get-slots')
    def api_get_slots():
        doctor_id = request.args.get('doctor_id')
        date_val = request.args.get('date')

        if not doctor_id or not date_val:
            return jsonify([])

        # Gọi hàm từ utils đã tạo ở trên
        slots = utils.get_available_slots(doctor_id, date_val)
        return jsonify(slots)


# === CẤU HÌNH FLASK-LOGIN CHO VIỆC CHƯA ĐĂNG NHẬP ===
login.login_view = 'login_view' # Chỉ định hàm xử lý trang đăng nhập
login.login_message = "Hãy đăng nhập để thực hiện hành động này." # Thông báo hiện ra khi bị đá về login
@app.route('/logout')
def logout_process():
    logout_user()
    return redirect('/login')






@login.user_loader
def load_user(user_id):
    from happ.models import User
    return User.query.get(int(user_id))

if __name__ == '__main__':
    from happ.admin import *
    register_routes(app)
    app.run(debug=True)