function cancelApp(btn) {
    const appId = btn.getAttribute('data-id');

    if(confirm('Bạn có chắc chắn muốn hủy lịch hẹn này không?')) {
        fetch(`/api/cancel-appointment/${appId}`, {
            method: 'POST'
        })
        .then(res => res.json())
        .then(data => {
            if(data.status === 'success') {
                alert(data.message);
                location.reload(); // Load lại trang để cập nhật trạng thái
            } else {
                alert('Lỗi: ' + data.message);
            }
        })
        .catch(err => console.error(err));
    }
}


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

// Chạy lần đầu khi load trang
renderDefaultSlots();