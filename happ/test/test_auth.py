import pytest
import hashlib
from happ import dao
from happ.models import User
from happ.test.test_base import test_app, test_session, test_client, mock_cloudinary, sample_data


# test add_user (đăng ký)
@pytest.mark.parametrize("name, username, password, expected", [

    ("Trần Thị B", "patient_new", "123456", True),

    ("Test", "", "123456", False),  # Thiếu username
    ("Test", "newuser", "", False),  # Thiếu password
    ("Trần Văn C", "patient01", "password123", False) # Trùng username
])
def test_add_user(test_session, sample_data, name, username, password, expected):

    if expected:
        dao.add_user(name=name, username=username, password=password, avatar=None)

        u = User.query.filter_by(username=username).first()
        assert u is not None
        assert u.name == name
        assert u.password == str(hashlib.md5(password.encode('utf-8')).hexdigest())
    else:
        with pytest.raises(Exception):
            dao.add_user(name=name, username=username, password=password, avatar=None)





# test ath_user(đăng nhập)
@pytest.mark.parametrize("username, password, expected", [
    ("patient01", "123456", True),  # Đúng

    ("", "123456", False),  # Thiếu username
    ("patient01", "", False),  # Thiếu password
    (None, None, False),  # Cả hai đều rỗng

    ("patient01", "wrong123456", False),  # Sai password
    ("wrongpatient", "123456", False)  # Sai username
])
def test_auth_user(test_session, sample_data, username, password, expected):
    user = dao.auth_user(username=username, password=password)

    if expected:
        assert user is not None
        assert user.username == username
    else:
        assert user is None
