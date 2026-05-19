from sqlalchemy.exc import IntegrityError
from happ.models import User, UserRole, Appointment, Doctor, DoctorSchedule
import hashlib
from happ import app, db, utils
import cloudinary.uploader
from flask_login import current_user
from sqlalchemy import func
from datetime import datetime, timedelta

# 1. Hàm lấy thông tin User bằng ID
# Phục vụ cho Flask-Login duy trì phiên đăng nhập (session)
def get_user_by_id(user_id):
    return User.query.get(user_id)


# 2. Hàm xác thực tài khoản (Authentication)
# Dùng để kiểm tra khi người dùng bấm nút "Đăng nhập"
def auth_user(username, password):
    if username and password:
        # Mã hóa MD5 mật khẩu người dùng nhập vào để so khớp với DB
        password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())

        # Tìm user có username và password khớp hoàn toàn
        return User.query.filter(User.username.__eq__(username.strip()),
                                 User.password.__eq__(password)).first()
    return None


# 3. Hàm lấy vai trò của User (Nếu cần dùng thêm logic ở index)
def get_user_role(user):
    if user:
        return user.user_role
    return None

def add_user(name, username, password, avatar):
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
    u = User(
        name=name.strip(),
        username=username.strip(),
        password=password
    )
    if avatar:
        res = cloudinary.uploader.upload(avatar)
        u.avatar = res.get("secure_url")
    db.session.add(u)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise Exception('Username đã tồn tại!')



def is_user_blocked(user):
    """Kiểm tra user có đang bị block đặt lịch không."""
    if user.blocked_until:
        if datetime.now() < user.blocked_until:
            return True
        else:
            user.blocked_until = None
            db.session.commit()
    return False


def record_cancel(user):
    """Ghi nhận 1 lần huỷ lịch, block 24h nếu >= 3 lần/tuần."""
    now = datetime.now()
    if not user.cancel_week_start or (now - user.cancel_week_start).days >= 7:
        user.cancel_week_start = now
        user.cancel_count_week = 0

    user.cancel_count_week += 1

    if user.cancel_count_week >= 3:
        user.blocked_until = now + timedelta(hours=24)

    db.session.commit()

# =============================DOCTOR=========================
def load_doctors():
    return Doctor.query.filter_by(active=True).all()


def get_doctor_by_id(doctor_id):
    return Doctor.query.get(int(doctor_id))


def add_doctor(name, specialty):
    d = Doctor(name=name.strip(), specialty=specialty.strip())
    db.session.add(d)
    db.session.commit()
    return d


def is_doctor_on_leave(doctor_id, target_date):
    """Kiểm tra bác sĩ có nghỉ phép vào ngày đó không."""
    return DoctorSchedule.query.filter_by(
        doctor_id=doctor_id,
        work_date=target_date,
        is_leave=True,
        active=True
    ).first() is not None


def count_doctor_appointments_gon(doctor_id, target_date):
    """Số lịch khám của bác sĩ trong 1 ngày (không tính Cancelled)."""
    return Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.app_date == target_date,
        Appointment.status != 'Cancelled',
        Appointment.active == True
    ).count()

# =============================APPOINTMENT=========================
def load_appointments(patient_id=None, doctor_id=None, status=None):
    query = Appointment.query.filter_by(active=True)
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    if doctor_id:
        query = query.filter_by(doctor_id=doctor_id)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(
        Appointment.app_date.asc(),
        Appointment.slot_time.asc()
    ).all()


def get_appointment_by_id(appt_id):
    return Appointment.query.get(int(appt_id))

def get_appointments_by_user(user_id):
    return Appointment.query.filter_by(patient_id=user_id).order_by(Appointment.app_date.asc()).all()


def add_appointment(patient_id, doctor_id, appt_date, appt_time):
    """
    Tạo lịch khám mới với đầy đủ validate nghiệp vụ.
    Trả về (appointment, error_message).
    """
    user = get_user_by_id(patient_id)
    doctor = get_doctor_by_id(doctor_id)

    if not user or not doctor:
        return None, 'Người dùng hoặc bác sĩ không tồn tại.'

    # 2. Chỉ đặt trong giờ làm việc 8:00–17:00
    if not utils.is_working_hour(appt_time):
        return None, 'Chỉ được đặt lịch trong giờ làm việc (8:00 – 17:00).'

    # 3. Không đặt lịch trong quá khứ
    if not utils.is_future_datetime(appt_date, appt_time):
        return None, 'Không được đặt lịch trong quá khứ.'

    # 4. Không đặt quá 30 ngày tương lai
    if not utils.is_within_30_days(appt_date):
        return None, 'Không được đặt lịch quá 30 ngày trong tương lai.'

    # 5. 1 khung giờ chỉ 1 bệnh nhân
    slot_taken = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.app_date == appt_date,
        Appointment.slot_time == appt_time,
        Appointment.status != 'Cancelled',
        Appointment.active == True
    ).first()
    if slot_taken:
        return None, 'Khung giờ này đã có bệnh nhân khác đặt.'

    # 6. Mỗi bệnh nhân tối đa 2 lịch/ngày
    daily_count = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.app_date == appt_date,
        Appointment.status != 'Cancelled',
        Appointment.active == True
    ).count()
    if daily_count >= 2:
        return None, 'Bạn đã đặt tối đa 2 lịch trong ngày này.'

    # 7. Bác sĩ không nghỉ phép
    if is_doctor_on_leave(doctor_id, appt_date):
        return None, 'Bác sĩ đang nghỉ phép vào ngày này.'

    # 8. Bác sĩ không vượt 20 lịch/ngày
    if count_doctor_appointments_gon(doctor_id, appt_date) >= 20:
        return None, 'Bác sĩ đã đầy lịch trong ngày này (tối đa 20 lịch).'

    # 9. Tài khoản không bị block
    if is_user_blocked(user):
        return None, f'Tài khoản bị hạn chế đặt lịch đến {utils.format_date(user.blocked_until.date())}.'

    appt = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        app_date=appt_date,
        slot_time=appt_time,
        status='CONFIRMED'
    )
    db.session.add(appt)
    db.session.commit()
    return appt, None


def cancel_appointment(appt_id, current_user):
    """
    Huỷ lịch khám. Chỉ bệnh nhân đặt hoặc admin mới được huỷ.
    Trả về (True/False, thông báo).
    """
    appt = get_appointment_by_id(appt_id)
    if not appt:
        return False, 'Không tìm thấy lịch khám.'

    # Chỉ bệnh nhân đó hoặc admin mới được huỷ
    is_owner = (appt.patient_id == current_user.id)
    is_admin = (current_user.user_role == UserRole.ADMIN)
    if not is_owner and not is_admin:
        return False, 'Bạn không có quyền huỷ lịch này.'

    ok, err = utils.can_cancel_appointment(appt)
    if not ok:
        return False, err

    appt.status = 'Cancelled'

    # Ghi nhận lần huỷ cho bệnh nhân (không tính admin huỷ)
    if is_owner and not is_admin:
        record_cancel(current_user)
    else:
        db.session.commit()

    return True, 'Huỷ lịch thành công.'


# if __name__ == '__main__':
#     with app.app_context():



from datetime import datetime, timedelta
from happ.models import Appointment, AppointmentStatus, db

#Logic huỷ lịch
# def cancel_appointment(appointment_id, current_user_id):
#     # 1. Tìm lịch hẹn
#     app = Appointment.query.get(appointment_id)
#     if not app:
#         return False, "Không tìm thấy lịch hẹn."
#
#     # 2. Ràng buộc: Chỉ bệnh nhân đặt lịch (hoặc admin sau này) mới được hủy
#     if app.patient_id != current_user_id:
#         return False, "Bạn không có quyền hủy lịch của người khác."
#
#     # 3. Ràng buộc: Không được hủy nếu trạng thái là COMPLETED
#     if app.status == AppointmentStatus.COMPLETED:
#         return False, "Không thể hủy lịch đã khám xong."
#
#     # 4. Ràng buộc: Không được hủy khi còn dưới 1 giờ trước giờ khám
#     # Ghép ngày và giờ khám lại thành 1 object datetime
#     appointment_datetime = datetime.combine(app.app_date, app.slot_time)
#     time_difference = appointment_datetime - datetime.now()
#
#     if time_difference < timedelta(hours=1):
#         return False, "Chỉ được hủy lịch trước giờ khám ít nhất 1 tiếng."
#
#     #Nếu pass được hết --> cho phép huỷ
#
#     # Đổi trạng thái thành CANCELLED
#     app.status = AppointmentStatus.CANCELLED
#
#     # Ràng buộc: Xử lý vụ hủy quá 3 lần/tuần
#     user = app.patient
#     user.cancel_count += 1
#
#     if user.cancel_count >= 3:
#         # Phạt hạn chế đặt lịch trong 24 giờ
#         user.restricted_until = datetime.now() + timedelta(hours=24)
#         # Có thể reset lại cancel_count về 0 ở đây nếu muốn bắt đầu chu kỳ mới, tùy logic nhóm bạn.
#
#     try:
#         db.session.commit()
#         return True, "Hủy lịch thành công!"
#     except Exception as e:
#         db.session.rollback()
#         return False, str(e)