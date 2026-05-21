import pytest
from datetime import date, time, datetime, timedelta
from happ import dao, db
from happ.models import Appointment, AppointmentStatus, DoctorSchedule
from happ.test.test_base import test_app, test_session, sample_data, test_client
def test_cancel_appointment_success(test_session, sample_data):
    patient1 = sample_data['patient1']
    doc1 = sample_data['doc1']
    tomorrow = date.today() + timedelta(days=1)

    appt, _ = dao.add_appointment(patient_id=patient1.id, doctor_id=doc1.id,
                                  appt_date=tomorrow, appt_time=time(9, 0))
    assert appt.status == AppointmentStatus.CONFIRMED
    success, err = dao.cancel_appointment(appt_id=appt.id, current_user_id=patient1.id)
    assert success is True
    assert appt.status == AppointmentStatus.CANCELLED

def test_cancel_appointment_wrong_patient(test_session, sample_data):
    patient1 = sample_data['patient1']
    patient2 = sample_data['patient2']
    doc1 = sample_data['doc1']
    tomorrow = date.today() + timedelta(days=1)

    appt, _ = dao.add_appointment(patient_id=patient1.id, doctor_id=doc1.id,
                                  appt_date=tomorrow, appt_time=time(9, 0))

    success, err = dao.cancel_appointment(appt_id=appt.id, current_user_id=patient2.id)
    assert success is False
    assert 'không có quyền' in err

def test_cancel_appointment_not_found(test_session, sample_data):
    success, err = dao.cancel_appointment(appt_id=999, current_user_id=1)
    assert success is False
    assert 'Không tìm thấy' in err

def test_cancel_appointment_admin_cancel(test_session, sample_data):
    patient1 = sample_data['patient1']
    admin = sample_data['admin']
    doc1 = sample_data['doc1']
    tomorrow = date.today() + timedelta(days=1)

    appt, _ = dao.add_appointment(patient_id=patient1.id, doctor_id=doc1.id,
                                  appt_date=tomorrow, appt_time=time(9, 0))

    success, err = dao.cancel_appointment(appt_id=appt.id,
                                     current_user_id=admin.id,
                                     is_admin=True)
    assert success is True
    assert appt.status == AppointmentStatus.CANCELLED
    assert 'thành công' in err


def test_cancel_appointment_block_user(test_session, sample_data):
    patient1 = sample_data['patient1']
    doc1 = sample_data['doc1']
    tomorrow = date.today() + timedelta(days=1)

    assert patient1.blocked_until is None

    base = datetime.strptime("09:00", "%H:%M")
    for i in range(4):
        appt_time = (base + timedelta(minutes=i * 20)).time()

        appt, _ = dao.add_appointment(patient_id=patient1.id, doctor_id=doc1.id, appt_date=tomorrow,
                                      appt_time=appt_time)

        dao.cancel_appointment(appt_id=appt.id, current_user_id=patient1.id)

    assert patient1.blocked_until is not None

def test_cancel_appointment_completed(test_session, sample_data):
    patient1 = sample_data['patient1']
    doc1 = sample_data['doc1']
    tomorrow = date.today() + timedelta(days=1)

    appt, _ = dao.add_appointment(patient_id=patient1.id, doctor_id=doc1.id,
                                  appt_date=tomorrow, appt_time=time(10, 0))


    appt.status = AppointmentStatus.COMPLETED
    test_session.commit()

    success, err = dao.cancel_appointment(appt_id=appt.id, current_user_id=patient1.id)

    assert success is False

def test_cancel_appointment_less_than_1_hour(test_session, sample_data):
    patient1 = sample_data['patient1']
    doc1 = sample_data['doc1']

    appt_date = date.today()
    appt_time = (datetime.now() + timedelta(minutes=30)).time()

    appt, _ = dao.add_appointment(patient_id=patient1.id, doctor_id=doc1.id,
                                  appt_date=appt_date, appt_time=appt_time)

    success, err = dao.cancel_appointment(appt_id=appt.id, current_user_id=patient1.id)

    assert success is False