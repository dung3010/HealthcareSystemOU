import pytest
from datetime import date, time, datetime, timedelta
from happ import dao, db
from happ.models import Appointment, AppointmentStatus, DoctorSchedule
from happ.test.test_base import test_app, test_session, sample_data, test_client


# 1. Đăng nhập
def test_access_dashboard_view_unauthorized(test_client):
    response = test_client.get('/dashboard')

    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_book_appointment_success(test_session, sample_data):
    patient1 = sample_data['patient1']
    doc1 = sample_data['doc1']
    tomorrow = date.today() + timedelta(days=1)
    appt_time = time(9, 0)

    appt, err = dao.add_appointment(patient_id=patient1.id, doctor_id=doc1.id, appt_date=tomorrow, appt_time=appt_time)

    assert err is None
    assert appt is not None
    assert appt.status == AppointmentStatus.CONFIRMED


# 2. Giờ làm việc
@pytest.mark.parametrize("input_time, expected, expected_err", [
    (time(8, 0),  True,  None),
    (time(7, 59), False, 'Chỉ được đặt lịch trong giờ làm việc'),
    (time(17, 0), False, 'Chỉ được đặt lịch trong giờ làm việc'),

])
def test_book_appointment_working_hours(test_session, sample_data, input_time, expected, expected_err):
    patient1 = sample_data['patient1']
    doc1 = sample_data['doc1']
    tomorrow = date.today() + timedelta(days=1)

    appt, err = dao.add_appointment(
        patient_id=patient1.id,
        doctor_id=doc1.id,
        appt_date=tomorrow,
        appt_time=input_time
    )

    if expected:
        assert err is None
        assert appt is not None
    else:
        assert appt is None
        assert expected_err in err


# 3. Lịch trong QK
def test_book_appointment_past_date(test_session, sample_data):
    patient1 = sample_data['patient1']
    doc1 = sample_data['doc1']

    yesterday = date.today() - timedelta(days=1)
    appt_time = time(10, 0)

    appt, err = dao.add_appointment(patient_id=patient1.id, doctor_id=doc1.id, appt_date=yesterday, appt_time=appt_time)
    assert appt is None
    assert 'Không được đặt lịch trong quá khứ.' in err




# 4. 1 khung giờ chỉ 1 bệnh nhân
def test_book_appointment_slot_taken(test_session, sample_data):
    patient1 = sample_data['patient1']
    patient2 = sample_data['patient2']
    doc1 = sample_data['doc1']

    tomorrow = date.today() + timedelta(days=1)
    appt_time = time(10, 0)

    appt1, err1 = dao.add_appointment(patient_id=patient1.id, doctor_id=doc1.id, appt_date=tomorrow,
                                      appt_time=appt_time)
    #Success
    assert appt1 is not None
    assert err1 is None



    appt2, err2 = dao.add_appointment(patient_id=patient2.id, doctor_id=doc1.id, appt_date=tomorrow,
                                      appt_time=appt_time)

    #Fail
    assert appt2 is None
    assert 'Khung giờ này đã có bệnh nhân khác đặt.' in err2

#5. Tối đa 2 lịch/ngày
def test_book_appointment_max_per_day(test_session, sample_data):
    patient1 = sample_data['patient1']
    doc1 = sample_data['doc1']
    doc2 = sample_data['doc2']
    tomorrow = date.today() + timedelta(days=1)

    dao.add_appointment(patient_id=patient1.id, doctor_id=doc1.id,
                        appt_date=tomorrow, appt_time=time(9, 0))
    dao.add_appointment(patient_id=patient1.id, doctor_id=doc2.id,
                        appt_date=tomorrow, appt_time=time(10, 0))

    #Fail
    appt, err = dao.add_appointment(patient_id=patient1.id, doctor_id=doc1.id,
                                      appt_date=tomorrow, appt_time=time(11, 0))
    assert appt is None
    assert 'Bạn đã đặt tối đa 2 lịch trong ngày này.' in err

#6. Bác sĩ nghỉ phép
def test_book_appointment_doctor_is_leave(test_session, sample_data):
    doc1 = sample_data['doc1']
    patient1 = sample_data['patient1']
    tomorrow = date.today() + timedelta(days=1)

    leave = DoctorSchedule(
        doctor_id=doc1.id,
        work_date=tomorrow,
        start_time=time(8, 0),
        end_time=time(17, 0),
        is_leave=True
    )
    db.session.add(leave)
    db.session.commit()

    appt, err = dao.add_appointment(patient_id=patient1.id, doctor_id=doc1.id,
                                    appt_date=tomorrow, appt_time=time(9, 0))
    assert appt is None
    assert 'Bác sĩ đang nghỉ phép' in err

#7. Lịch quá 30 ngày trong tương lai
@pytest.mark.parametrize("days_next, expected, expected_err", [
    (30, True, None),
    (31, False, 'Không được đặt lịch quá 30 ngày trong tương lai')
])
def test_book_appointment_out_30_days(test_session, sample_data, days_next, expected, expected_err):
    patient1 = sample_data['patient1']
    doc1 = sample_data['doc1']

    target_date = date.today() + timedelta(days=days_next)
    appt_time = time(9, 0)

    appt, err = dao.add_appointment(
        patient_id=patient1.id,
        doctor_id=doc1.id,
        appt_date=target_date,
        appt_time=appt_time
    )

    if expected:
        assert err is None
        assert appt is not None
    else:
        assert appt is None
        assert expected_err in err

# 8. Bị hạn chế đặt lịch
def test_book_appointment_user_block(test_session, sample_data):
    patient1 = sample_data['patient1']
    doc1 = sample_data['doc1']
    tomorrow = date.today() + timedelta(days=1)

    # tài khoản bị block
    patient1.blocked_until = datetime.now() + timedelta(days=1)
    test_session.commit()

    appt, err = dao.add_appointment(patient_id=patient1.id, doctor_id=doc1.id, appt_date=tomorrow, appt_time=time(9, 0))
    assert appt is None
    assert 'Tài khoản bị hạn chế đặt lịch' in err


def test_book_appointment_doctor_max(test_session, sample_data):
    doc1 = sample_data['doc1']
    tomorrow = date.today() + timedelta(days=1)

    all_slots = []
    for hour in range(8, 17):
        all_slots.append(time(hour, 0))
        all_slots.append(time(hour, 20))
        all_slots.append(time(hour, 40))

    count = 0
    for p in range(1, 11):
        patient = sample_data[f'patient{p}']

        for i in range(2):
            appt_time = all_slots[count]

            appt, err = dao.add_appointment(
                patient_id=patient.id,
                doctor_id=doc1.id,
                appt_date=tomorrow,
                appt_time=appt_time
            )
            assert err is None
            assert appt is not None

            count += 1

    patient11 = sample_data['patient11']

    appt_11, err_11 = dao.add_appointment(
        patient_id=patient11.id,
        doctor_id=doc1.id,
        appt_date=tomorrow,
        appt_time=time(16, 40)
    )

    assert appt_11 is None
    assert 'Bác sĩ đã đầy lịch trong ngày' in err_11