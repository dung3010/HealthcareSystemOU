from datetime import datetime, date, time, timedelta
from happ.models import Appointment, AppointmentStatus, User, DoctorSchedule


def is_working_hour(appt_time):
    return time(8, 0) <= appt_time < time(17, 0)


def is_future_datetime(appt_date, appt_time):
    appt_dt = datetime.combine(appt_date, appt_time)
    return appt_dt > datetime.now()


def is_within_30_days(appt_date):
    return 0 <= (appt_date - date.today()).days <= 30


def format_date(d):
    if d:
        return d.strftime('%d/%m/%Y')
    return ''


def format_time(t):
    if t:
        return t.strftime('%H:%M')
    return ''


def can_cancel_appointment(appointment):
    if appointment.status == AppointmentStatus.COMPLETED:
        return False, 'Không thể huỷ lịch đã hoàn thành.'

    if appointment.status == AppointmentStatus.CANCELLED:
        return False, 'Lịch này đã được huỷ trước đó.'

    appt_dt = datetime.combine(appointment.app_date, appointment.slot_time)
    now = datetime.now()
    if appt_dt < now:
        return False, 'Không thể huỷ lịch hẹn trong quá khứ.'

    if (appt_dt - now) < timedelta(hours=1):
        return False, 'Không thể huỷ lịch trong vòng 1 giờ trước giờ khám.'

    return True, None


def get_available_slots(doctor_id, date_str):

    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    now = datetime.now()

    schedule = DoctorSchedule.query.filter_by(
        doctor_id=doctor_id,
        work_date=target_date,
        active=True
    ).first()

    if not schedule or schedule.is_leave:
        return []

    start = datetime.combine(target_date, schedule.start_time)
    end = datetime.combine(target_date, schedule.end_time)
    slots = []

    while start < end:
        time_val = start.time()

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