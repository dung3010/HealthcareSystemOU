import os
import pytest
from flask import Flask
from datetime import date, time, datetime, timedelta

from happ import db, login
from happ.models import User, UserRole, Doctor, Appointment, AppointmentStatus
from happ.index import register_routes


def create_app():
    base_dir = os.path.dirname(os.path.dirname(__file__))  # Trỏ ra ngoài 1 cấp -> happ/
    template_dir = os.path.join(base_dir, 'templates')

    app = Flask(__name__, template_folder=template_dir)

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True
    app.secret_key = "test_secret_key_ou_clinic"

    db.init_app(app)
    login.init_app(app)
    register_routes(app=app)
    return app


@pytest.fixture
def test_app():
    app = create_app()
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def test_client(test_app):
    return test_app.test_client()


@pytest.fixture
def test_session(test_app):
    yield db.session
    db.session.rollback()


@pytest.fixture
def mock_cloudinary(monkeypatch):
    def fake_upload(file):
        return {'secure_url': 'https://res.cloudinary.com/fake-avatar.png'}

    monkeypatch.setattr('cloudinary.uploader.upload', fake_upload)


@pytest.fixture
def sample_data(test_session):
    import hashlib
    p_pass = str(hashlib.md5('123456'.encode('utf-8')).hexdigest())

    #tạo patient mẫu
    patients_list = []
    for i in range(1, 13):
        username_str = f"patient{i:02d}"
        name_str = f"Bệnh Nhân Mẫu {i:02d}"

        new_patient = User(
            name=name_str,
            username=username_str,
            password=p_pass,
            user_role=UserRole.PATIENT
        )
        patients_list.append(new_patient)
        test_session.add(new_patient)
    admin = User(name='Admin', username='admin', password=p_pass, user_role=UserRole.ADMIN)

    # tạo bác sĩ mẫu
    doc1 = Doctor(name='BS. Đào Thanh Hải', specialty='Nội khoa')
    doc2 = Doctor(name='BS. Trần Chính', specialty='Nhi khoa')

    test_session.add_all([admin, doc1, doc2])
    test_session.commit()

    data = {
        'admin': admin,
        'doc1': doc1,
        'doc2': doc2
    }

    for idx, p in enumerate(patients_list, start=1):
        data[f'patient{idx}'] = p
    return data