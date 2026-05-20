from sqlalchemy.exc import IntegrityError
from happ.models import User, UserRole, Appointment, Doctor, DoctorSchedule, AppointmentStatus
import hashlib
from happ import app, db, utils
import cloudinary.uploader
from datetime import datetime, timedelta

def get_user_by_id(user_id):
    return User.query.get(user_id)


#Xác thực tài khoản
def auth_user(username, password):
    if username and password:
        password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())

        return User.query.filter(User.username.__eq__(username.strip()),
                                 User.password.__eq__(password)).first()
    return None


# 3. Hàm lấy vai trò của User (Nếu cần dùng thêm logic ở index)
def get_user_role(user):
    if user:
        return user.user_role
    return None

def add_user(name, username, password, avatar):
    if not name or not name.strip():
        raise Exception('Họ và tên không được để trống!')
    if not username or not username.strip():
        raise Exception('Tên đăng nhập không được để trống!')
    if not password or not password.strip():
        raise Exception('Mật khẩu không được để trống!')
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
    if not user.cancel_week_start or (now - user.cancel_week_start) >= timedelta(days=7):
        user.cancel_week_start = now
        user.cancel_count_week = 0

    user.cancel_count_week += 1

    if user.cancel_count_week >= 3:
        user.blocked_until = now + timedelta(hours=24)


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
        Appointment.status != AppointmentStatus.CANCELLED,
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

    #1. Tài khoản không bị block
    if is_user_blocked(user):
        return None, f'Tài khoản bị hạn chế đặt lịch đến {utils.format_date(user.blocked_until.date())}.'

    #2. Chỉ đặt trong giờ làm việc 8:00–17:00
    if not utils.is_working_hour(appt_time):
        return None, 'Chỉ được đặt lịch trong giờ làm việc (8:00 – 17:00).'

    #3. Không đặt lịch trong quá khứ
    if not utils.is_future_datetime(appt_date, appt_time):
        return None, 'Không được đặt lịch trong quá khứ.'

    #4. Không đặt quá 30 ngày tương lai
    if not utils.is_within_30_days(appt_date):
        return None, 'Không được đặt lịch quá 30 ngày trong tương lai.'

    # 5. 1 khung giờ chỉ 1 bệnh nhân
    slot_taken = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.app_date == appt_date,
        Appointment.slot_time == appt_time,
        Appointment.status != AppointmentStatus.CANCELLED,
        Appointment.active == True
    ).first()
    if slot_taken:
        return None, 'Khung giờ này đã có bệnh nhân khác đặt.'

    #6. Mỗi bệnh nhân tối đa 2 lịch/ngày
    daily_count = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.app_date == appt_date,
        Appointment.status != AppointmentStatus.CANCELLED,
        Appointment.active == True
    ).count()
    if daily_count >= 2:
        return None, 'Bạn đã đặt tối đa 2 lịch trong ngày này.'

    #7. Bác sĩ không nghỉ phép
    if is_doctor_on_leave(doctor_id, appt_date):
        return None, 'Bác sĩ đang nghỉ phép vào ngày này.'

    #8. Bác sĩ không vượt 20 lịch/ngày
    if count_doctor_appointments_gon(doctor_id, appt_date) >= 20:
        return None, 'Bác sĩ đã đầy lịch trong ngày này (tối đa 20 lịch).'


    appt = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        app_date=appt_date,
        slot_time=appt_time,
        status=AppointmentStatus.CONFIRMED
    )
    db.session.add(appt)
    db.session.commit()
    return appt, None


def cancel_appointment(appt_id, current_user_id, is_admin = False):
    """
    Huỷ lịch khám. Chỉ bệnh nhân đặt hoặc admin mới được huỷ.
    Trả về (True/False, thông báo).
    """
    appt = get_appointment_by_id(appt_id)
    if not appt:
        return False, 'Không tìm thấy lịch khám.'

    # Chỉ bệnh nhân đó hoặc admin mới được huỷ
    is_owner = (appt.patient_id == current_user_id)
    if not is_owner and not is_admin:
        return False, 'Bạn không có quyền huỷ lịch này.'

    ok, err = utils.can_cancel_appointment(appt)
    if not ok:
        return False, err

    appt.status = AppointmentStatus.CANCELLED

    # Ghi nhận lần huỷ cho bệnh nhân (không tính admin huỷ)
    if is_owner and not is_admin:
        user = get_user_by_id(current_user_id)
        if user:
            record_cancel(user)
    try:
        db.session.commit()
        return True, 'Huỷ lịch thành công.'
    except Exception as ex:
        db.session.rollback()
        return False, f'Lỗi hệ thống khi lưu dữ liệu: {str(ex)}'






