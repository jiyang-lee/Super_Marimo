/* 
  MARIMO QUEST - 자바스크립트
  화면 전환, 퀘스트 완료, 모달, 리포트 탭 제어
*/

document.addEventListener('DOMContentLoaded', () => {
    // 1. 시간 업데이트
    updateTime();
    setInterval(updateTime, 1000);

    // 2. 초기 화면 설정 (홈)
    showScreen('home');

    // 3. 월별 차트 초기화
    initMonthlyChart();

    // 4. 모달 슬라이더 초기화
    initSliders();

    // 5. 알림 버튼 초기 상태 맞춤
    initNotiBtn();
});

// 상단 헤더 시간 업데이트
function updateTime() {
    const timeEl = document.getElementById('header-time');
    if (!timeEl) return;
    const now = new Date();
    const h = String(now.getHours()).padStart(2, '0');
    const m = String(now.getMinutes()).padStart(2, '0');
    timeEl.innerText = `${h}:${m}`;
}

// 화면 전환 함수
function showScreen(screenId) {
    // 보고서 탭은 센서 화면 아래에 붙어 있으므로 센서 화면을 열고 스크롤만 이동한다.
    const resolvedScreenId = screenId === 'report' ? 'sensor' : screenId;

    // 모든 섹션 숨기기
    const screens = document.querySelectorAll('.screen');
    screens.forEach(s => s.classList.remove('active'));

    // 대상 섹션 보이기
    const target = document.getElementById(`${resolvedScreenId}-screen`);
    if (target) target.classList.add('active');

    // 내비게이션 활성화 상태 동기화 (PC & Mobile)
    updateNavUI(screenId);

    if (screenId === 'report') {
        requestAnimationFrame(() => {
            const anchor = document.getElementById('report-anchor');
            if (anchor) anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }
}

function updateNavUI(screenId) {
    const pcItems = document.querySelectorAll('.pc-nav li');
    const mobileItems = document.querySelectorAll('.mobile-nav li');

    const screenIndexMap = {
        'home': 0,
        'sensor': 1,
        'chat': 2,
        'report': 3,
        'settings': 4
    };

    const idx = screenIndexMap[screenId];

    // PC 내비 업데이트
    pcItems.forEach((item, i) => {
        if (i === idx) item.classList.add('active');
        else item.classList.remove('active');
    });

    // Mobile 내비 업데이트
    mobileItems.forEach((item, i) => {
        if (i === idx) item.classList.add('active');
        else item.classList.remove('active');
    });
}

// 퀘스트 완료 처리
function completeQuest(btn) {
    if (btn.innerText === '실행') {
        btn.innerText = '완료';
        btn.style.backgroundColor = '#bdc3c7'; // 회색 처리
        btn.style.cursor = 'default';
        btn.parentElement.style.opacity = '0.6';
    }
}

// 보고서 탭 전환
function switchReport(type) {
    const weeklyTab = document.getElementById('tab-weekly');
    const monthlyTab = document.getElementById('tab-monthly');
    const weeklyContent = document.getElementById('weekly-content');
    const monthlyContent = document.getElementById('monthly-content');

    if (type === 'weekly') {
        weeklyTab.classList.add('active');
        monthlyTab.classList.remove('active');
        weeklyContent.classList.add('active');
        monthlyContent.classList.remove('active');
    } else {
        weeklyTab.classList.remove('active');
        monthlyTab.classList.add('active');
        weeklyContent.classList.remove('active');
        monthlyContent.classList.add('active');
    }
}

// 전역 차트 변수
let monthlyLineChart = null;

// 랜덤 데이터 생성 함수 (30 ~ 90 사이의 값 31개 - 일별 데이터)
function generateRandomData() {
    return Array.from({length: 31}, () => Math.floor(Math.random() * 60) + 30);
}

// 차트 초기화 함수
function initMonthlyChart() {
    const ctx = document.getElementById('monthlyChart');
    if (!ctx) return;

    // 기존 차트가 있으면 파괴
    if (monthlyLineChart) {
        monthlyLineChart.destroy();
    }

    // 1일부터 31일까지의 라벨 생성
    const dailyLabels = Array.from({length: 31}, (_, i) => `${i + 1}일`);

    monthlyLineChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dailyLabels,
            datasets: [
                {
                    label: '온도',
                    data: generateRandomData(),
                    borderColor: '#ff7675',
                    backgroundColor: '#ff7675',
                    tension: 0.3,
                    borderWidth: 3
                },
                {
                    label: '습도',
                    data: generateRandomData(),
                    borderColor: '#74b9ff',
                    backgroundColor: '#74b9ff',
                    tension: 0.3,
                    borderWidth: 3
                },
                {
                    label: '조도',
                    data: generateRandomData(),
                    borderColor: '#ffeaa7',
                    backgroundColor: '#ffeaa7',
                    tension: 0.3,
                    borderWidth: 3
                },
                {
                    label: '수위',
                    data: generateRandomData(),
                    borderColor: '#55efc4',
                    backgroundColor: '#55efc4',
                    tension: 0.3,
                    borderWidth: 3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            elements: {
                point: {
                    radius: 0,         // 평소에는 점 숨김
                    hitRadius: 10,     // 마우스 인식 범위
                    hoverRadius: 6     // 마우스 올렸을 때 점 크기
                }
            },
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                tooltip: {
                    enabled: true,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleFont: { family: 'VT323', size: 16 },
                    bodyFont: { family: 'VT323', size: 14 }
                },
                legend: {
                    position: 'bottom',
                    labels: {
                        font: { family: 'VT323', size: 16 }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { font: { family: 'VT323', size: 14 } }
                },
                x: {
                    ticks: { font: { family: 'VT323', size: 14 } }
                }
            }
        }
    });
}

// 먼슬리: 월 선택 시 그래프 업데이트
function selectMonth(month, btnElement) {
    // 버튼 활성화 상태 변경
    const buttons = btnElement.parentElement.querySelectorAll('.btn');
    buttons.forEach(btn => btn.classList.remove('active'));
    btnElement.classList.add('active');

    // 타이틀 변경
    const title = document.getElementById('monthly-chart-title');
    if (title) title.innerText = `${month}월 센서 추이`;

    // 차트 데이터 업데이트 및 애니메이션 재생
    if (monthlyLineChart) {
        monthlyLineChart.data.datasets.forEach(dataset => {
            dataset.data = generateRandomData();
        });
        monthlyLineChart.update();
    }
}

// 모달 제어
function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.style.display = 'flex';
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.style.display = 'none';
}

// 설정: 알림 토글 버튼
function toggleNotiBtn(btn) {
    if (btn.innerText.includes('ON')) {
        setNotiBtnState(btn, false);
    } else {
        setNotiBtnState(btn, true);
    }
}

function setNotiBtnState(btn, isOn) {
    if (!btn) return;
    if (isOn) {
        btn.innerText = 'ON';
        btn.style.backgroundColor = 'var(--accent-green)';
    } else {
        btn.innerText = 'OFF';
        btn.style.backgroundColor = '#e74c3c';
    }
}

function initNotiBtn() {
    const btn = document.getElementById('noti-btn');
    if (!btn) return;
    setNotiBtnState(btn, btn.innerText.includes('ON'));
}

// 채팅 전송 (더미)
function sendMessage() {
    const input = document.querySelector('.pixel-input');
    const display = document.getElementById('chat-display');
    
    if (input && input.value.trim() !== '') {
        const text = input.value;
        const now = new Date();
        const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

        // 사용자 메시지 추가
        const uMsg = document.createElement('div');
        uMsg.className = 'msg user-msg';
        uMsg.innerHTML = `<span class="msg-text">${text}</span><span class="chat-time">${timeStr}</span>`;
        display.appendChild(uMsg);

        input.value = '';
        display.scrollTop = display.scrollHeight;

        // 마리모 응답 (1초 뒤)
        setTimeout(() => {
            const mMsg = document.createElement('div');
            mMsg.className = 'msg marimo-msg';
            mMsg.innerHTML = `<span class="chat-avatar" aria-hidden="true"></span><div class="chat-bubble"><span class="msg-text">웅! 알겠어! ٩(◕ᗜ◕)و</span><span class="chat-time">${timeStr}</span></div>`;
            display.appendChild(mMsg);
            display.scrollTop = display.scrollHeight;
        }, 1000);
    }
}

// 센서 설정 모달 슬라이더 초기화
function initSliders() {
    const formatInt = {
        to: function(value) { return Math.round(value); },
        from: function(value) { return Math.round(value); }
    };

    const sliderTemp = document.getElementById('slider-temp');
    if (sliderTemp && !sliderTemp.noUiSlider) {
        noUiSlider.create(sliderTemp, {
            start: [20, 30], // 양끝 범위 예시
            connect: true,
            tooltips: true,
            format: formatInt,
            range: { 'min': 0, 'max': 100 }
        });
    }

    const sliderHum = document.getElementById('slider-hum');
    if (sliderHum && !sliderHum.noUiSlider) {
        noUiSlider.create(sliderHum, {
            start: [40, 60],
            connect: true,
            tooltips: true,
            format: formatInt,
            range: { 'min': 0, 'max': 100 }
        });
    }

    const sliderWater = document.getElementById('slider-water');
    if (sliderWater && !sliderWater.noUiSlider) {
        noUiSlider.create(sliderWater, {
            start: [50, 80],
            connect: true,
            tooltips: true,
            format: formatInt,
            range: { 'min': 0, 'max': 100 }
        });
    }

    const sliderLight = document.getElementById('slider-light');
    if (sliderLight && !sliderLight.noUiSlider) {
        noUiSlider.create(sliderLight, {
            start: [2000, 8000],
            connect: true,
            tooltips: true,
            format: formatInt,
            step: 100, // 조도는 숫자가 크므로 100단위로 조절
            range: { 'min': 0, 'max': 10000 }
        });
    }
}





