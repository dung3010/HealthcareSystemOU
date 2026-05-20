const doctorSelect = document.querySelector('select[name="doctor_id"]');
const dateInput = document.querySelector('input[name="date"]');
const slotsGrid = document.getElementById('slots-grid');
const selectedTimeInput = document.getElementById('selected-time');

// Hàm tạo các ô giờ trống mặc định khi chưa chọn bác sĩ
function renderDefaultSlots() {
    slotsGrid.innerHTML = '';
    let start = 8 * 60; // 08:00 quy ra phút
    let end = 17 * 60;  // 17:00 quy ra phút

    for (let i = start; i < end; i += 20) {
        let h = Math.floor(i / 60).toString().padStart(2, '0');
        let m = (i % 60).toString().padStart(2, '0');
        let timeStr = `${h}:${m}`;

        const div = document.createElement('div');
        div.className = 'slot';
        div.textContent = timeStr;
        div.style.opacity = "0.5"; // Làm mờ vì chưa chọn bác sĩ/ngày
        div.style.cursor = "not-allowed";
        slotsGrid.appendChild(div);
    }
}

function fetchSlots() {
    const doctorId = doctorSelect.value;
    const date = dateInput.value;

    if (!doctorId || !date) {
        renderDefaultSlots();
        return;
    }

    fetch(`/api/get-slots?doctor_id=${doctorId}&date=${date}`)
    .then(res => res.json())
    .then(data => {
        slotsGrid.innerHTML = '';

        // THÊM: xử lý khi bác sĩ không có lịch trực
        if (data.length === 0) {
            slotsGrid.innerHTML = '<p style="font-size:12px;color:var(--text-hint);">Bác sĩ không có lịch trực vào ngày này.</p>';
            return;
        }

        data.forEach(slot => {
            const div = document.createElement('div');
            div.className = 'slot' + (slot.is_booked ? ' booked' : '');
            div.textContent = slot.time;

            if (!slot.is_booked) {
                div.style.opacity = "1";
                div.style.cursor = "pointer";
                div.onclick = function() {
                    document.querySelectorAll('.slot').forEach(s => s.classList.remove('selected'));
                    this.classList.add('selected');
                    selectedTimeInput.value = this.textContent;
                };
            } else {
                div.classList.add('booked');
            }
            slotsGrid.appendChild(div);
        });
    });
}

doctorSelect.addEventListener('change', fetchSlots);
dateInput.addEventListener('change', fetchSlots);


function confirmCancel(apptId) {
    Swal.fire({
        title: 'Xác nhận hủy lịch?',
        text: "Bạn có chắc chắn muốn hủy lịch hẹn khám này không?",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#2D5F4F', // Đổi màu nút khớp với tone màu chung --accent của nhóm
        cancelButtonColor: '#8B2E2E',  // Màu nút hủy --danger
        confirmButtonText: 'Đồng ý',
        cancelButtonText: 'Quay lại',
        background: '#FFFFFF',
        customClass: {
            popup: 'animated fadeInDown'
        }
    }).then((result) => {
        if (result.isConfirmed) {
            // Nếu bấm OK -> Tạo một form POST chạy ngầm để gửi yêu cầu lên Route Flask
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/dashboard/${apptId}/cancel`;
            document.body.appendChild(form);
            form.submit();
        }
    });
}

// Chạy lần đầu khi load trang
renderDefaultSlots();