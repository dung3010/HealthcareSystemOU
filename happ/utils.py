from datetime import datetime, date, time, timedelta
from happ.models import Appointment, AppointmentStatus, User, DoctorSchedule


def is_working_hour(appt_time):
    """Ràng buộc: chỉ đặt lịch trong giờ làm việc 8:00–17:00."""
    return time(8, 0) <= appt_time <= time(17, 0)


def is_future_datetime(appt_date, appt_time):
    """Ràng buộc: không đặt lịch trong quá khứ."""
    appt_dt = datetime.combine(appt_date, appt_time)
    return appt_dt > datetime.now()


def is_within_30_days(appt_date):
    """Ràng buộc: không đặt quá 30 ngày trong tương lai."""
    return 0 <= (appt_date - date.today()).days <= 30


def format_date(d):
    """Định dạng ngày hiển thị: 12/05/2026."""
    if d:
        return d.strftime('%d/%m/%Y')
    return ''


def format_time(t):
    """Định dạng giờ hiển thị: 08:30."""
    if t:
        return t.strftime('%H:%M')
    return ''


def can_cancel_appointment(appointment):
    """
    Kiểm tra lịch khám có thể huỷ không.
    Trả về (True/False, thông báo lỗi nếu có).
    """
    if appointment.status == 'Completed':
        return False, 'Không thể huỷ lịch đã hoàn thành.'

    if appointment.status == 'Cancelled':
        return False, 'Lịch này đã được huỷ trước đó.'

    appt_dt = datetime.combine(appointment.app_date, appointment.slot_time)
    if (appt_dt - datetime.now()) < timedelta(hours=1):
        return False, 'Không thể huỷ lịch trong vòng 1 giờ trước giờ khám.'

    return True, None


def get_available_slots(doctor_id, date_str):

    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    now = datetime.now()

    # Kiểm tra lịch trực của bác sĩ ngày đó
    schedule = DoctorSchedule.query.filter_by(
        doctor_id=doctor_id,
        work_date=target_date,
        active=True
    ).first()

    # Không có lịch trực hoặc đang nghỉ phép → trả về rỗng
    if not schedule or schedule.is_leave:
        return []

    # Dùng start_time/end_time từ lịch trực thay vì hardcode 8:00–17:00
    start = datetime.combine(target_date, schedule.start_time)
    end = datetime.combine(target_date, schedule.end_time)
    slots = []

    while start < end:
        time_val = start.time()

        # Ẩn giờ đã qua nếu là hôm nay
        if target_date == date.today():
            if datetime.combine(target_date, time_val) <= now:
                start += timedelta(minutes=20)
                continue

        is_booked = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.app_date == target_date,
            Appointment.slot_time == time_val,
            Appointment.status != AppointmentStatus.CANCELLED
        ).first() is not None

        slots.append({
            "time": start.strftime("%H:%M"),
            "is_booked": is_booked
        })
        start += timedelta(minutes=20)

    return slots