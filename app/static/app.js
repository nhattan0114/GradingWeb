// Trạng thái ứng dụng (Application State)
let currentGrade = "Khối 10";
let examConfig = null;
let selectedExamCode = "201";
let selectedFilterCode = "ALL"; // "ALL", "201", "202", ..., "SAI_MA_DE"
let selectedSortOrder = "score_desc"; // "score_desc", "score_asc", "sbd_asc"
let gradedResults = [];
let chartInstance = null;
let currentModalResultId = null;

// Khởi chạy khi load trang
document.addEventListener("DOMContentLoaded", async () => {
    setupCustomDialogEvents();
    await fetchGrades();
    await fetchConfig();
    await fetchResults();
    setupDropZone();
});

// ==========================================
// HỆ THỐNG THÔNG BÁO & HỘP THOẠI HIỆN ĐẠI (CUSTOM NOTIFICATION SYSTEM)
// ==========================================

/**
 * Hiển thị Toast thông báo nhanh góc trên bên phải
 * @param {string} message Nội dung thông báo
 * @param {'success'|'error'|'warning'|'info'} type Loại thông báo
 * @param {number} duration Thời gian hiển thị (ms)
 */
function showToast(message, type = 'info', duration = 3500) {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = "toast-enter pointer-events-auto flex items-start gap-3 p-3.5 bg-white rounded-xl shadow-xl border text-xs text-slate-800 transition-all";

    let iconName = "info";
    let iconClass = "text-moet-600 bg-blue-50 border-blue-200";
    let borderClass = "border-slate-200";

    if (type === "success") {
        iconName = "check-circle";
        iconClass = "text-emerald-600 bg-emerald-50 border-emerald-200";
        borderClass = "border-emerald-200";
    } else if (type === "error") {
        iconName = "alert-circle";
        iconClass = "text-red-600 bg-red-50 border-red-200";
        borderClass = "border-red-200";
    } else if (type === "warning") {
        iconName = "alert-triangle";
        iconClass = "text-amber-600 bg-amber-50 border-amber-200";
        borderClass = "border-amber-200";
    }

    toast.classList.add(...borderClass.split(" "));

    toast.innerHTML = `
        <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 border ${iconClass}">
            <i data-lucide="${iconName}" class="w-4 h-4"></i>
        </div>
        <div class="flex-1 pt-0.5 leading-relaxed font-semibold text-slate-700">
            ${message}
        </div>
        <button type="button" class="text-slate-400 hover:text-slate-600 transition p-0.5 rounded-lg flex-shrink-0" onclick="this.closest('.toast-enter').remove()">
            <i data-lucide="x" class="w-3.5 h-3.5"></i>
        </button>
    `;

    container.appendChild(toast);
    lucide.createIcons({ root: toast });

    setTimeout(() => {
        toast.classList.remove("toast-enter");
        toast.classList.add("toast-exit");
        setTimeout(() => toast.remove(), 250);
    }, duration);
}

/**
 * Hộp thoại Custom Dialog dùng chung cho Alert, Confirm, Prompt
 */
let currentDialogResolve = null;

function setupCustomDialogEvents() {
    const dialog = document.getElementById("custom-dialog");
    if (!dialog) return;

    // Light dismiss khi click ra ngoài backdrop (theo modern web guidance)
    dialog.addEventListener("click", (e) => {
        const rect = dialog.getBoundingClientRect();
        const isInDialog = (
            rect.top <= e.clientY && e.clientY <= rect.top + rect.height &&
            rect.left <= e.clientX && e.clientX <= rect.left + rect.width
        );
        if (!isInDialog) {
            dialog.close();
        }
    });

    dialog.addEventListener("close", () => {
        if (currentDialogResolve) {
            currentDialogResolve(dialog.dataset.dialogType === "prompt" ? null : false);
            currentDialogResolve = null;
        }
    });
}

/**
 * Hiển thị Alert hiện đại
 */
function showAlert({ title = "Thông Báo", message = "", type = "info", confirmText = "Đã Hiểu" }) {
    return new Promise((resolve) => {
        const dialog = document.getElementById("custom-dialog");
        if (!dialog) {
            window.alert(message);
            return resolve();
        }

        dialog.dataset.dialogType = "alert";
        currentDialogResolve = resolve;

        const iconBox = document.getElementById("custom-dialog-icon-box");
        const iconEl = document.getElementById("custom-dialog-icon");
        const titleEl = document.getElementById("custom-dialog-title");
        const msgEl = document.getElementById("custom-dialog-message");
        const inputWrap = document.getElementById("custom-dialog-input-wrapper");
        const btnCancel = document.getElementById("custom-dialog-btn-cancel");
        const btnConfirm = document.getElementById("custom-dialog-btn-confirm");

        titleEl.innerText = title;
        msgEl.innerText = message;
        inputWrap.classList.add("hidden");
        btnCancel.classList.add("hidden");

        btnConfirm.innerText = confirmText;
        btnConfirm.className = "px-5 py-2 bg-moet-600 hover:bg-moet-700 text-white text-xs font-semibold rounded-xl shadow-sm transition flex items-center gap-1.5";

        if (type === "error") {
            iconBox.className = "w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 bg-red-50 text-red-600 border border-red-100";
            iconEl.setAttribute("data-lucide", "alert-circle");
        } else if (type === "warning") {
            iconBox.className = "w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 bg-amber-50 text-amber-600 border border-amber-100";
            iconEl.setAttribute("data-lucide", "alert-triangle");
        } else if (type === "success") {
            iconBox.className = "w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 bg-emerald-50 text-emerald-600 border border-emerald-100";
            iconEl.setAttribute("data-lucide", "check-circle");
        } else {
            iconBox.className = "w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 bg-blue-50 text-moet-600 border border-blue-100";
            iconEl.setAttribute("data-lucide", "info");
        }
        lucide.createIcons({ root: iconBox });

        btnConfirm.onclick = () => {
            dialog.close();
            if (currentDialogResolve) {
                currentDialogResolve(true);
                currentDialogResolve = null;
            }
        };

        dialog.showModal();
        btnConfirm.focus();
    });
}

/**
 * Hiển thị Confirm hiện đại (trả về Promise<boolean>)
 */
function showConfirm({ title = "Xác Nhận", message = "", confirmText = "Đồng Ý", cancelText = "Hủy", isDanger = false, type = "warning" }) {
    return new Promise((resolve) => {
        const dialog = document.getElementById("custom-dialog");
        if (!dialog) {
            return resolve(window.confirm(message));
        }

        dialog.dataset.dialogType = "confirm";
        currentDialogResolve = resolve;

        const iconBox = document.getElementById("custom-dialog-icon-box");
        const iconEl = document.getElementById("custom-dialog-icon");
        const titleEl = document.getElementById("custom-dialog-title");
        const msgEl = document.getElementById("custom-dialog-message");
        const inputWrap = document.getElementById("custom-dialog-input-wrapper");
        const btnCancel = document.getElementById("custom-dialog-btn-cancel");
        const btnConfirm = document.getElementById("custom-dialog-btn-confirm");

        titleEl.innerText = title;
        msgEl.innerText = message;
        inputWrap.classList.add("hidden");
        btnCancel.classList.remove("hidden");
        btnCancel.innerText = cancelText;

        btnConfirm.innerText = confirmText;
        if (isDanger) {
            iconBox.className = "w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 bg-red-50 text-red-600 border border-red-100";
            iconEl.setAttribute("data-lucide", "trash-2");
            btnConfirm.className = "px-5 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-xl shadow-sm transition flex items-center gap-1.5";
        } else {
            iconBox.className = "w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 bg-amber-50 text-amber-600 border border-amber-100";
            iconEl.setAttribute("data-lucide", "alert-triangle");
            btnConfirm.className = "px-5 py-2 bg-moet-600 hover:bg-moet-700 text-white text-xs font-semibold rounded-xl shadow-sm transition flex items-center gap-1.5";
        }
        lucide.createIcons({ root: iconBox });

        btnCancel.onclick = () => {
            dialog.close();
            if (currentDialogResolve) {
                currentDialogResolve(false);
                currentDialogResolve = null;
            }
        };

        btnConfirm.onclick = () => {
            dialog.close();
            if (currentDialogResolve) {
                currentDialogResolve(true);
                currentDialogResolve = null;
            }
        };

        dialog.showModal();
        if (isDanger) {
            btnCancel.focus(); // Đặt focus vào nút Hủy để tránh bấm nhầm Enter gây mất dữ liệu
        } else {
            btnConfirm.focus();
        }
    });
}

/**
 * Hiển thị Prompt nhập liệu hiện đại (trả về Promise<string|null>)
 */
function showPrompt({ title = "Nhập Thông Tin", message = "", defaultValue = "", placeholder = "", confirmText = "Xác Nhận", cancelText = "Hủy", validateFn = null }) {
    return new Promise((resolve) => {
        const dialog = document.getElementById("custom-dialog");
        if (!dialog) {
            return resolve(window.prompt(message, defaultValue));
        }

        dialog.dataset.dialogType = "prompt";
        currentDialogResolve = resolve;

        const iconBox = document.getElementById("custom-dialog-icon-box");
        const iconEl = document.getElementById("custom-dialog-icon");
        const titleEl = document.getElementById("custom-dialog-title");
        const msgEl = document.getElementById("custom-dialog-message");
        const inputWrap = document.getElementById("custom-dialog-input-wrapper");
        const inputEl = document.getElementById("custom-dialog-input");
        const errorEl = document.getElementById("custom-dialog-error");
        const errorText = document.getElementById("custom-dialog-error-text");
        const btnCancel = document.getElementById("custom-dialog-btn-cancel");
        const btnConfirm = document.getElementById("custom-dialog-btn-confirm");

        titleEl.innerText = title;
        msgEl.innerText = message;
        inputWrap.classList.remove("hidden");
        errorEl.classList.add("hidden");
        inputEl.value = defaultValue || "";
        inputEl.placeholder = placeholder || "";

        btnCancel.classList.remove("hidden");
        btnCancel.innerText = cancelText;

        btnConfirm.innerText = confirmText;
        btnConfirm.className = "px-5 py-2 bg-moet-600 hover:bg-moet-700 text-white text-xs font-semibold rounded-xl shadow-sm transition flex items-center gap-1.5";

        iconBox.className = "w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 bg-blue-50 text-moet-600 border border-blue-100";
        iconEl.setAttribute("data-lucide", "edit-3");
        lucide.createIcons({ root: iconBox });

        const submitAction = () => {
            const val = inputEl.value.trim();
            if (validateFn) {
                const err = validateFn(val);
                if (err) {
                    errorText.innerText = err;
                    errorEl.classList.remove("hidden");
                    inputEl.focus();
                    return;
                }
            }
            dialog.close();
            if (currentDialogResolve) {
                currentDialogResolve(val);
                currentDialogResolve = null;
            }
        };

        inputEl.onkeydown = (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                submitAction();
            }
        };

        btnCancel.onclick = () => {
            dialog.close();
            if (currentDialogResolve) {
                currentDialogResolve(null);
                currentDialogResolve = null;
            }
        };

        btnConfirm.onclick = submitAction;

        dialog.showModal();
        inputEl.focus();
        inputEl.select();
    });
}

// Ghi đè alert mặc định của trình duyệt sang Popup hiện đại
window.alert = (msg) => showAlert({ title: "Thông Báo", message: String(msg), type: "info" });

// Sắp xếp danh sách kết quả theo lựa chọn
function sortResults(list, order) {
    return [...list].sort((a, b) => {
        if (order === "score_desc") {
            return b.total_score - a.total_score;
        } else if (order === "score_asc") {
            return a.total_score - b.total_score;
        } else if (order === "sbd_asc") {
            return (a.student_sbd || "").localeCompare(b.student_sbd || "", 'vi', { numeric: true });
        }
        return b.total_score - a.total_score;
    });
}

// Cập nhật cấu hình lên toàn bộ giao diện (Môn học, Mã đề, Ma trận đáp án)
function applyConfigToUI(cfg) {
    if (!cfg) return;
    examConfig = cfg;
    if (cfg.grade_level) {
        currentGrade = cfg.grade_level;
    }
    updateGradeUI();

    const subj = document.getElementById("cfg-subject");
    const exam = document.getElementById("cfg-exam");
    const year = document.getElementById("cfg-year");
    if (subj) subj.value = cfg.subject_name || "";
    if (exam) exam.value = cfg.exam_name || "";
    if (year) year.value = cfg.academic_year || "";

    if (document.getElementById("p1-header-title")) {
        document.getElementById("p1-header-title").innerHTML = `<i data-lucide="list-checks" class="w-4 h-4"></i> Phần I: Trắc Nghiệm (${cfg.part1_num_questions} câu - ${(cfg.part1_max_score || 3.0).toFixed(1)}đ)`;
    }
    if (document.getElementById("p2-header-title")) {
        document.getElementById("p2-header-title").innerHTML = `<i data-lucide="help-circle" class="w-4 h-4"></i> Phần II: Đúng / Sai (${cfg.part2_num_questions} câu - ${(cfg.part2_max_score || 2.0).toFixed(1)}đ)`;
    }
    if (document.getElementById("p3-header-title")) {
        document.getElementById("p3-header-title").innerHTML = `<i data-lucide="hash" class="w-4 h-4"></i> Phần III: Trả Lời Ngắn (${cfg.part3_num_questions} câu - ${(cfg.part3_max_score || 2.0).toFixed(1)}đ)`;
    }

    const availableCodes = Object.keys(cfg.keys || {}).sort();
    if (!availableCodes.includes(selectedExamCode)) {
        selectedExamCode = availableCodes.length > 0 ? availableCodes[0] : "201";
    }

    renderExamCodeChips();
    renderUploadForceCodeOptions();
    renderKeyMatrices();
    lucide.createIcons();
}

// Chuyển đổi khối thi (Khối 10, Khối 11, Khối 12)
async function changeGrade(gradeName) {
    if (!gradeName) return;
    currentGrade = gradeName;
    updateGradeUI();

    try {
        const formData = new URLSearchParams();
        formData.append("grade", currentGrade);
        const res = await fetch("/api/grades/select", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: formData.toString()
        });
        const data = await res.json();
        if (data && data.config) {
            applyConfigToUI(data.config);
        } else {
            await fetchConfig();
        }
    } catch (e) {
        console.error("Lỗi chọn khối:", e);
        await fetchConfig();
    }

    selectedFilterCode = "ALL";
    await fetchResults();

    const statsTab = document.getElementById("tab-stats");
    if (statsTab && !statsTab.classList.contains("hidden")) {
        renderStatistics();
    }
}

function updateGradeUI() {
    const grades = ["Khối 10", "Khối 11", "Khối 12"];
    grades.forEach(g => {
        const num = g.replace("Khối ", "").trim();
        const headerBtn = document.getElementById(`header-grade-btn-${num}`);
        const keysBtn = document.getElementById(`keys-grade-btn-${num}`);

        const isActive = (g === currentGrade);
        if (headerBtn) {
            if (isActive) {
                headerBtn.className = "grade-pill-btn px-2.5 py-1 rounded-lg text-xs font-bold transition bg-amber-400 text-slate-900 shadow";
            } else {
                headerBtn.className = "grade-pill-btn px-2.5 py-1 rounded-lg text-xs font-bold transition text-blue-100 hover:text-white hover:bg-white/10";
            }
        }
        if (keysBtn) {
            if (isActive) {
                keysBtn.className = "grade-tab-btn px-3.5 py-1.5 rounded-lg text-xs font-bold transition bg-moet-600 text-white shadow-sm";
            } else {
                keysBtn.className = "grade-tab-btn px-3.5 py-1.5 rounded-lg text-xs font-bold transition bg-slate-100 text-slate-700 hover:bg-slate-200";
            }
        }
    });

    const badge = document.getElementById("keys-current-grade-badge");
    if (badge) badge.innerText = currentGrade;
}

async function fetchGrades() {
    try {
        const res = await fetch("/api/grades");
        const data = await res.json();
        if (data.current_grade) {
            currentGrade = data.current_grade;
        }
        updateGradeUI();
    } catch (e) {
        console.error("Lỗi lấy danh sách khối:", e);
    }
}

// Chuyển Tab
function switchTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(el => el.classList.add("hidden"));
    document.getElementById(tabId).classList.remove("hidden");

    document.querySelectorAll(".nav-tab").forEach(btn => {
        btn.classList.remove("border-amber-300", "text-white");
        btn.classList.add("border-transparent", "text-blue-100");
    });

    const activeNav = {
        'tab-grading': 'nav-grading',
        'tab-keys': 'nav-keys',
        'tab-stats': 'nav-stats'
    }[tabId];

    if (activeNav) {
        document.getElementById(activeNav).classList.add("border-amber-300", "text-white");
        document.getElementById(activeNav).classList.remove("border-transparent", "text-blue-100");
    }

    if (tabId === 'tab-keys') {
        updateGradeUI();
        if (examConfig) {
            applyConfigToUI(examConfig);
        }
    } else if (tabId === 'tab-stats') {
        renderStatistics();
    }
}

// 1. Quản lý Cấu hình & Đáp án
async function fetchConfig() {
    try {
        const res = await fetch(`/api/config?grade=${encodeURIComponent(currentGrade)}`);
        const cfg = await res.json();
        applyConfigToUI(cfg);
    } catch (err) {
        console.error("Lỗi tải cấu hình:", err);
    }
}

function renderUploadForceCodeOptions() {
    const sel = document.getElementById("upload-force-code");
    if (!sel) return;
    const currentVal = sel.value;
    sel.innerHTML = `<option value="">🎯 Tự động theo Mã đề học sinh tô trên bài</option>`;
    const codes = Object.keys(examConfig.keys || {}).sort();
    codes.forEach(code => {
        const opt = document.createElement("option");
        opt.value = code;
        opt.textContent = `🔒 Chấm cố định theo Mã đề ${code}`;
        sel.appendChild(opt);
    });
    sel.value = currentVal;
}

function renderExamCodeChips() {
    const container = document.getElementById("exam-code-chips");
    container.innerHTML = "";

    const codes = Object.keys(examConfig.keys || {}).sort();
    if (codes.length === 0) {
        examConfig.keys["201"] = { exam_code: "201", part1: {}, part2: {}, part3: {} };
    }

    if (!codes.includes(selectedExamCode)) {
        selectedExamCode = Object.keys(examConfig.keys)[0];
    }

    Object.keys(examConfig.keys).forEach(code => {
        const chip = document.createElement("button");
        const isActive = code === selectedExamCode;
        chip.className = `px-3 py-1 text-xs font-bold rounded-lg transition ${
            isActive ? "bg-moet-600 text-white shadow-sm" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
        }`;
        chip.textContent = `Mã đề ${code}`;
        chip.onclick = () => {
            selectedExamCode = code;
            renderExamCodeChips();
            renderKeyMatrices();
        };
        container.appendChild(chip);
    });
}

async function addNewExamCode() {
    const code = await showPrompt({
        title: "Thêm Mã Đề Mới",
        message: `Nhập mã đề thi trắc nghiệm (3 chữ số, ví dụ 205) cho ${currentGrade}:`,
        placeholder: "205",
        confirmText: "Thêm Mã Đề",
        validateFn: (val) => {
            if (!val) return "Vui lòng nhập mã đề thi!";
            if (!/^\d{3}$/.test(val)) return "Mã đề nên gồm 3 chữ số (ví dụ: 201, 202, 205)!";
            if (examConfig?.keys && examConfig.keys[val]) return `Mã đề ${val} đã tồn tại trong ${currentGrade}!`;
            return null;
        }
    });

    if (code && code.trim()) {
        const c = code.trim();
        if (!examConfig.keys[c]) {
            examConfig.keys[c] = { exam_code: c, part1: {}, part2: {}, part3: {} };
            selectedExamCode = c;
            renderExamCodeChips();
            renderUploadForceCodeOptions();
            renderKeyMatrices();
            renderCodeFilterChips();
            showToast(`Đã thêm Mã đề ${c} vào ma trận đáp án!`, "success");
        } else {
            showToast(`Mã đề ${c} đã tồn tại trong ${currentGrade}!`, "warning");
        }
    }
}

async function renameCurrentExamCode() {
    if (!selectedExamCode) {
        showToast("Chưa chọn mã đề để đổi tên!", "warning");
        return;
    }
    const newCode = await showPrompt({
        title: "Đổi Tên Mã Đề",
        message: `Nhập tên mới cho Mã đề [${selectedExamCode}] (${currentGrade}):`,
        defaultValue: selectedExamCode,
        placeholder: "ví dụ: 205",
        confirmText: "Lưu Tên Mới",
        validateFn: (val) => {
            if (!val) return "Tên mã đề không được để trống!";
            if (val !== selectedExamCode && examConfig?.keys && examConfig.keys[val]) {
                return `Mã đề ${val} đã tồn tại trong ${currentGrade}!`;
            }
            return null;
        }
    });

    if (!newCode || newCode.trim() === "" || newCode.trim() === selectedExamCode) return;
    const trimmed = newCode.trim();

    try {
        const formData = new FormData();
        formData.append("old_code", selectedExamCode);
        formData.append("new_code", trimmed);
        formData.append("grade", currentGrade);

        const res = await fetch("/api/config/rename-code", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (res.ok && data.status === "success") {
            showToast(data.message || `Đã đổi tên thành Mã đề ${trimmed}`, "success");
            const oldCode = selectedExamCode;
            selectedExamCode = trimmed;
            if (selectedFilterCode === oldCode) {
                selectedFilterCode = trimmed;
            }
            await fetchConfig();
            await fetchResults();
        } else {
            showAlert({ title: "Không Thể Đổi Tên", message: data.detail || "Không thể đổi tên mã đề", type: "error" });
        }
    } catch (err) {
        showAlert({ title: "Lỗi Hệ Thống", message: "Lỗi khi đổi tên mã đề: " + err, type: "error" });
    }
}

async function deleteCurrentExamCode() {
    if (!selectedExamCode) return;
    const availableCodes = Object.keys(examConfig?.keys || {});
    if (availableCodes.length <= 1) {
        showAlert({
            title: "Không Thể Xóa",
            message: "Mỗi khối phải giữ lại ít nhất 1 mã đề đáp án trong ma trận.",
            type: "warning"
        });
        return;
    }
    const confirmed = await showConfirm({
        title: "Xóa Mã Đề Đáp Án",
        message: `Thầy/Cô có chắc chắn muốn xóa Mã đề [${selectedExamCode}] khỏi ${currentGrade} không?\nCác bài thi đã chấm theo mã đề này vẫn được bảo lưu điểm số.`,
        confirmText: "Xóa Mã Đề",
        isDanger: true
    });
    if (!confirmed) return;

    try {
        const res = await fetch(`/api/config/keys/${encodeURIComponent(selectedExamCode)}?grade=${encodeURIComponent(currentGrade)}`, {
            method: "DELETE"
        });
        const data = await res.json();
        if (res.ok && data.status === "success") {
            showToast(data.message || `Đã xóa Mã đề ${selectedExamCode}`, "success");
            const remaining = Object.keys(data.config?.keys || {});
            selectedExamCode = remaining.length > 0 ? remaining[0] : "201";
            if (selectedFilterCode === selectedExamCode) {
                selectedFilterCode = "ALL";
            }
            await fetchConfig();
            await fetchResults();
        } else {
            showAlert({ title: "Không Thể Xóa", message: data.detail || "Không thể xóa mã đề", type: "error" });
        }
    } catch (err) {
        showAlert({ title: "Lỗi Hệ Thống", message: "Lỗi khi xóa mã đề: " + err, type: "error" });
    }
}

function renderKeyMatrices() {
    const keyData = examConfig.keys[selectedExamCode] || { part1: {}, part2: {}, part3: {} };

    // 1. Phần I Matrix (Trắc nghiệm nhiều lựa chọn)
    const p1Container = document.getElementById("part1-matrix");
    p1Container.innerHTML = "";
    for (let i = 1; i <= examConfig.part1_num_questions; i++) {
        const qStr = i.toString();
        const currentAns = keyData.part1[qStr] || "";

        const row = document.createElement("div");
        row.className = "flex items-center justify-between text-xs py-1 border-b border-slate-100";
        row.innerHTML = `
            <span class="font-semibold text-slate-700 w-14">Câu ${qStr}:</span>
            <div class="flex space-x-1.5">
                ${['A', 'B', 'C', 'D'].map(opt => `
                    <button type="button" onclick="setPart1Key('${qStr}', '${opt}')" 
                        class="w-7 h-7 rounded-full border border-slate-300 flex items-center justify-center font-bold text-xs bubble-opt ${currentAns === opt ? 'active' : 'hover:bg-slate-100 text-slate-600'}">
                        ${opt}
                    </button>
                `).join('')}
            </div>
        `;
        p1Container.appendChild(row);
    }

    // 2. Phần II Matrix (Đúng/Sai)
    const p2Container = document.getElementById("part2-matrix");
    p2Container.innerHTML = "";
    for (let i = 1; i <= examConfig.part2_num_questions; i++) {
        const qStr = i.toString();
        const qChoices = keyData.part2[qStr] || {};

        const block = document.createElement("div");
        block.className = "p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-2";
        block.innerHTML = `
            <div class="font-bold text-slate-800">Câu ${qStr}:</div>
            <div class="grid grid-cols-2 gap-2">
                ${['a', 'b', 'c', 'd'].map(sub => {
                    const val = qChoices[sub];
                    return `
                        <div class="flex items-center justify-between bg-white px-2 py-1.5 rounded-lg border border-slate-200">
                            <span class="font-semibold text-slate-600">${sub})</span>
                            <div class="flex space-x-1">
                                <button type="button" onclick="setPart2Key('${qStr}', '${sub}', true)" 
                                    class="px-2 py-0.5 rounded text-xs font-bold transition ${val === true ? 'bg-emerald-600 text-white' : 'bg-slate-100 hover:bg-slate-200 text-slate-600'}">
                                    Đ
                                </button>
                                <button type="button" onclick="setPart2Key('${qStr}', '${sub}', false)" 
                                    class="px-2 py-0.5 rounded text-xs font-bold transition ${val === false ? 'bg-red-600 text-white' : 'bg-slate-100 hover:bg-slate-200 text-slate-600'}">
                                    S
                                </button>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
        p2Container.appendChild(block);
    }

    // 3. Phần III Matrix (Trả lời ngắn)
    const p3Container = document.getElementById("part3-matrix");
    p3Container.innerHTML = "";
    for (let i = 1; i <= examConfig.part3_num_questions; i++) {
        const qStr = i.toString();
        const currentAns = keyData.part3[qStr] || "";

        const row = document.createElement("div");
        row.className = "flex items-center justify-between text-xs py-1.5 border-b border-slate-100";
        row.innerHTML = `
            <span class="font-semibold text-slate-700 w-14">Câu ${qStr}:</span>
            <input type="text" value="${currentAns}" onchange="setPart3Key('${qStr}', this.value)" placeholder="vd: -3,5 hoặc 42"
                class="w-36 px-2.5 py-1 text-xs border border-slate-300 rounded-lg text-right font-bold text-emerald-800 focus:ring-1 focus:ring-moet-600 outline-none">
        `;
        p3Container.appendChild(row);
    }
}

function setPart1Key(qStr, opt) {
    if (!examConfig.keys[selectedExamCode]) return;
    examConfig.keys[selectedExamCode].part1[qStr] = opt;
    renderKeyMatrices();
}

function setPart2Key(qStr, sub, val) {
    if (!examConfig.keys[selectedExamCode]) return;
    if (!examConfig.keys[selectedExamCode].part2[qStr]) {
        examConfig.keys[selectedExamCode].part2[qStr] = {};
    }
    examConfig.keys[selectedExamCode].part2[qStr][sub] = val;
    renderKeyMatrices();
}

function setPart3Key(qStr, val) {
    if (!examConfig.keys[selectedExamCode]) return;
    examConfig.keys[selectedExamCode].part3[qStr] = val.trim();
}

async function saveExamConfig() {
    examConfig.grade_level = currentGrade;
    examConfig.subject_name = document.getElementById("cfg-subject").value;
    examConfig.exam_name = document.getElementById("cfg-exam").value;
    examConfig.academic_year = document.getElementById("cfg-year").value;

    try {
        const res = await fetch(`/api/config?grade=${encodeURIComponent(currentGrade)}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(examConfig)
        });
        const data = await res.json();
        if (res.ok && data.status === "success") {
            showToast(data.message || `Đã lưu ma trận đáp án cho ${currentGrade} thành công!`, "success");
        } else {
            showAlert({ title: "Lỗi Lưu Cấu Hình", message: data.detail || "Không thể lưu ma trận đáp án", type: "error" });
        }
    } catch (err) {
        showAlert({ title: "Lỗi Hệ Thống", message: "Lỗi khi lưu đáp án: " + err, type: "error" });
    }
}

// 2. Kéo Thả và Tải Lên Ảnh Bài Thi
function setupDropZone() {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");

    dropZone.onclick = () => fileInput.click();

    dropZone.ondragover = (e) => {
        e.preventDefault();
        dropZone.classList.add("border-moet-600", "bg-blue-50/50");
    };

    dropZone.ondragleave = () => {
        dropZone.classList.remove("border-moet-600", "bg-blue-50/50");
    };

    dropZone.ondrop = (e) => {
        e.preventDefault();
        dropZone.classList.remove("border-moet-600", "bg-blue-50/50");
        if (e.dataTransfer.files.length > 0) {
            uploadFiles(e.dataTransfer.files);
        }
    };

    fileInput.onchange = () => {
        if (fileInput.files.length > 0) {
            uploadFiles(fileInput.files);
        }
    };
}

async function uploadFiles(files) {
    const progressContainer = document.getElementById("progress-container");
    const progressBar = document.getElementById("progress-bar");
    const progressText = document.getElementById("progress-text");
    const progressPercent = document.getElementById("progress-percent");

    progressContainer.classList.remove("hidden");
    progressBar.style.width = "15%";
    progressPercent.innerText = "15%";
    progressText.innerText = `Đang nạp ${files.length} ảnh bài thi ${currentGrade}...`;

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
    }

    const forceCode = document.getElementById("upload-force-code").value;
    if (forceCode) {
        formData.append("force_exam_code", forceCode);
    }
    formData.append("grade", currentGrade);
    formData.append("use_ocr", "false");

    try {
        progressBar.style.width = "60%";
        progressPercent.innerText = "60%";
        progressText.innerText = "OMR Engine đang định vị 4 marker góc & quét chấm bài...";

        const res = await fetch("/api/grade/upload", {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        progressBar.style.width = "100%";
        progressPercent.innerText = "100%";
        progressText.innerText = `Đã hoàn tất chấm ${data.processed_count} bài thi!`;

        await fetchResults();

        setTimeout(() => {
            progressContainer.classList.add("hidden");
            progressBar.style.width = "0%";
        }, 1500);

    } catch (err) {
        showAlert({ title: "Lỗi Chấm Bài", message: "Lỗi trong quá trình chấm bài: " + err, type: "error" });
        progressContainer.classList.add("hidden");
    }
}

async function fetchResults() {
    try {
        const res = await fetch(`/api/results?grade=${encodeURIComponent(currentGrade)}`);
        gradedResults = await res.json();
        renderCodeFilterChips();
        renderResultsTable();
        updateFilterSummaryLabel();
    } catch (err) {
        console.error("Lỗi lấy danh sách kết quả:", err);
    }
}

// 3. Quản Lý Lọc Mã Đề & Sắp Xếp
function onSortOrderChange(val) {
    selectedSortOrder = val;
    renderResultsTable();
}

function renderCodeFilterChips() {
    const container = document.getElementById("code-filter-chips");
    if (!container) return;
    container.innerHTML = "";

    const validCodes = Object.keys(examConfig?.keys || {}).sort();

    // Đếm số lượng học sinh theo từng mã đề hợp lệ
    const validCounts = {};
    validCodes.forEach(code => {
        validCounts[code] = 0;
    });

    let invalidCount = 0;
    gradedResults.forEach(r => {
        if (r.exam_code && validCodes.includes(r.exam_code)) {
            validCounts[r.exam_code]++;
        } else {
            invalidCount++;
        }
    });

    // 1. Chip "Tất cả bài thi"
    const allChip = document.createElement("button");
    allChip.type = "button";
    allChip.className = `px-3 py-1 text-xs font-bold rounded-lg transition code-filter-btn ${
        selectedFilterCode === "ALL" ? "active" : "bg-white text-slate-700 hover:bg-slate-100 border border-slate-200"
    }`;
    allChip.innerHTML = `Tất cả bài thi <span class="ml-1 px-1.5 py-0.2 rounded-full text-[10px] ${selectedFilterCode === 'ALL' ? 'bg-white/30 text-white' : 'bg-slate-100 text-slate-600'}">${gradedResults.length}</span>`;
    allChip.onclick = () => {
        selectedFilterCode = "ALL";
        renderCodeFilterChips();
        renderResultsTable();
        updateFilterSummaryLabel();
    };
    container.appendChild(allChip);

    // 2. Chip riêng cho từng Mã Đề HỢP LỆ
    validCodes.forEach(code => {
        const count = validCounts[code];
        const chip = document.createElement("button");
        chip.type = "button";
        const isActive = selectedFilterCode === code;
        chip.className = `px-3 py-1 text-xs font-bold rounded-lg transition code-filter-btn ${
            isActive ? "active" : "bg-white text-slate-700 hover:bg-slate-100 border border-slate-200"
        }`;
        chip.innerHTML = `Mã đề ${code} <span class="ml-1 px-1.5 py-0.2 rounded-full text-[10px] ${isActive ? 'bg-white/30 text-white' : 'bg-slate-100 text-slate-600'}">${count}</span>`;
        chip.onclick = () => {
            selectedFilterCode = code;
            renderCodeFilterChips();
            renderResultsTable();
            updateFilterSummaryLabel();
        };
        container.appendChild(chip);
    });

    // 3. Lớp riêng: "Sai Mã Đề"
    if (invalidCount > 0) {
        const invChip = document.createElement("button");
        invChip.type = "button";
        const isInvActive = selectedFilterCode === "SAI_MA_DE";
        invChip.className = `px-3 py-1 text-xs font-bold rounded-lg transition flex items-center gap-1 ${
            isInvActive ? "bg-red-600 text-white shadow-sm" : "bg-red-50 text-red-700 hover:bg-red-100 border border-red-200"
        }`;
        invChip.innerHTML = `<i data-lucide="alert-triangle" class="w-3.5 h-3.5"></i> Sai mã đề <span class="ml-1 px-1.5 py-0.2 rounded-full text-[10px] ${isInvActive ? 'bg-white/30 text-white' : 'bg-red-200 text-red-800'}">${invalidCount}</span>`;
        invChip.onclick = () => {
            selectedFilterCode = "SAI_MA_DE";
            renderCodeFilterChips();
            renderResultsTable();
            updateFilterSummaryLabel();
        };
        container.appendChild(invChip);
    }

    updateFilterSummaryLabel();
}

function updateFilterSummaryLabel() {
    const filterLabel = document.getElementById("current-filter-label");

    let codeText = "Tất cả bài thi";
    if (selectedFilterCode === "SAI_MA_DE") {
        codeText = "Sai mã đề";
    } else if (selectedFilterCode !== "ALL") {
        codeText = `Mã ${selectedFilterCode}`;
    }

    if (filterLabel) {
        filterLabel.innerText = codeText;
    }

    const clearFilteredLabel = document.getElementById("label-clear-filtered");
    if (clearFilteredLabel) {
        if (selectedFilterCode === "SAI_MA_DE") {
            clearFilteredLabel.innerText = "Xóa các bài Sai mã đề";
        } else if (selectedFilterCode !== "ALL") {
            clearFilteredLabel.innerText = `Xóa các bài Mã ${selectedFilterCode}`;
        } else {
            clearFilteredLabel.innerText = `Xóa toàn bộ ${currentGrade}`;
        }
    }
}

function renderResultsTable() {
    const tbody = document.getElementById("results-tbody");
    const badgeCount = document.getElementById("badge-count");
    if (badgeCount) badgeCount.innerText = gradedResults.length;

    const validCodes = Object.keys(examConfig?.keys || {});

    // 1. Lọc theo mã đề
    let filtered = [];
    if (selectedFilterCode === "ALL") {
        filtered = gradedResults;
    } else if (selectedFilterCode === "SAI_MA_DE") {
        filtered = gradedResults.filter(r => !validCodes.includes(r.exam_code));
    } else {
        filtered = gradedResults.filter(r => r.exam_code === selectedFilterCode);
    }

    // 2. Sắp xếp danh sách
    filtered = sortResults(filtered, selectedSortOrder);

    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" class="px-6 py-12 text-center text-slate-400">
                    <i data-lucide="inbox" class="w-10 h-10 mx-auto mb-2 text-slate-300"></i>
                    ${gradedResults.length === 0 
                        ? 'Chưa có bài thi nào được chấm. Hãy tải ảnh bài thi lên để bắt đầu!' 
                        : 'Không tìm thấy bài thi nào phù hợp với bộ lọc mã đề đã chọn.'}
                </td>
            </tr>
        `;
        lucide.createIcons();
        return;
    }

    tbody.innerHTML = "";
    filtered.forEach((r, idx) => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-50 transition cursor-pointer";
        tr.onclick = (e) => {
            if (e.target.tagName !== "BUTTON" && e.target.tagName !== "I" && e.target.tagName !== "SELECT" && !e.target.closest("button")) {
                openInspectorModal(r.id);
            }
        };

        const isCornerError = r.exam_code === "LỖI_4_GÓC";
        const isUnknownCode = isCornerError || !validCodes.includes(r.exam_code);
        const hasIssues = r.flagged_issues && r.flagged_issues.length > 0;

        let statusBadge = "";
        if (isCornerError) {
            statusBadge = `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800" title="Không quét được 4 góc định vị. Yêu cầu chụp lại">Lỗi 4 góc (Chụp lại)</span>`;
        } else if (isUnknownCode) {
            statusBadge = `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800" title="Mã đề không hợp lệ. Cần đổi lại mã đề đúng">Sai mã đề</span>`;
        } else if (hasIssues) {
            statusBadge = `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800" title="${r.flagged_issues.join('; ')}">Cần xem lại</span>`;
        } else {
            statusBadge = `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">Hợp lệ</span>`;
        }

        // Cột Tên file bài thi
        const studentColumnHtml = `
            <div class="flex items-center gap-1.5 text-xs">
                <i data-lucide="file-text" class="w-3.5 h-3.5 text-moet-600 flex-shrink-0"></i>
                <span class="font-mono text-slate-700 font-semibold truncate max-w-[200px]" title="${r.file_name}">${r.file_name}</span>
            </div>
        `;

        // Cột Mã đề (Nếu sai thì bôi đỏ nổi bật)
        const codeDisplay = isUnknownCode 
            ? `<span class="px-2 py-0.5 rounded bg-red-100 text-red-800 font-bold font-mono text-xs border border-red-200" title="Mã đề không hợp lệ">${r.exam_code || "Trống"}</span>`
            : `<span class="font-bold text-slate-700">${r.exam_code}</span>`;

        tr.innerHTML = `
            <td class="px-4 py-3 text-center font-bold text-slate-600">${idx + 1}</td>
            <td class="px-4 py-3">${studentColumnHtml}</td>
            <td class="px-4 py-3 text-center font-mono font-bold text-moet-600 text-xs">${r.student_sbd || "---"}</td>
            <td class="px-4 py-3 text-center">${codeDisplay}</td>
            <td class="px-4 py-3 text-right font-medium text-slate-700">${r.score_part1.toFixed(2)}</td>
            <td class="px-4 py-3 text-right font-medium text-slate-700">${r.score_part2.toFixed(2)}</td>
            <td class="px-4 py-3 text-right font-medium text-slate-700">${r.score_part3.toFixed(2)}</td>
            <td class="px-4 py-3 text-right font-black ${isUnknownCode ? 'text-slate-400' : 'text-red-600'} text-base">${r.total_score.toFixed(2)}</td>
            <td class="px-4 py-3 text-center">${statusBadge}</td>
            <td class="px-4 py-3 text-center">
                <div class="flex items-center justify-center gap-1.5">
                    <button onclick="openInspectorModal('${r.id}')" class="px-2.5 py-1 text-xs font-semibold rounded-lg ${isUnknownCode ? 'bg-red-50 text-red-700 hover:bg-red-100' : 'bg-blue-50 text-moet-600 hover:bg-blue-100'} transition">
                        ${isCornerError ? 'Xem Lỗi / Chụp Lại' : (isUnknownCode ? 'Sửa Mã Đề' : 'Soát Lỗi')}
                    </button>
                    <button type="button" onclick="deleteSingleResultDirect('${r.id}', event)" class="p-1 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition" title="Xóa bài thi này">
                        <i data-lucide="trash-2" class="w-4 h-4"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
    lucide.createIcons();
}

// Quản Lý Xóa Bài Thi (Xóa theo mã đề / sai mã đề / khối hoặc toàn bộ)
function toggleClearDropdown(event) {
    if (event) event.stopPropagation();
    const menu = document.getElementById("clear-dropdown-menu");
    if (menu) {
        menu.classList.toggle("hidden");
    }
}

// Đóng menu khi bấm ra ngoài
document.addEventListener("click", (e) => {
    const menu = document.getElementById("clear-dropdown-menu");
    const btn = document.getElementById("btn-clear-dropdown");
    if (menu && !menu.classList.contains("hidden")) {
        if (!menu.contains(e.target) && (!btn || !btn.contains(e.target))) {
            menu.classList.add("hidden");
        }
    }
});

async function clearCurrentFilterResults() {
    const menu = document.getElementById("clear-dropdown-menu");
    if (menu) menu.classList.add("hidden");

    let filterDesc = [];
    if (selectedFilterCode === "SAI_MA_DE") {
        filterDesc.push("các bài 'Sai mã đề'");
    } else if (selectedFilterCode !== "ALL") {
        filterDesc.push(`các bài 'Mã đề ${selectedFilterCode}'`);
    }

    const descStr = filterDesc.length > 0 ? filterDesc.join(" ") : `tất cả các bài của ${currentGrade}`;
    const confirmed = await showConfirm({
        title: "Xác Nhận Xóa Bài Thi",
        message: `Thầy/Cô có chắc chắn muốn xóa ${descStr} không?\nDữ liệu đã xóa không thể phục hồi.`,
        confirmText: "Xóa Danh Sách",
        isDanger: true
    });
    if (!confirmed) return;

    try {
        const params = new URLSearchParams();
        if (currentGrade) params.append("grade", currentGrade);
        if (selectedFilterCode && selectedFilterCode !== "ALL") {
            params.append("exam_code", selectedFilterCode);
        }

        const res = await fetch(`/api/grade/clear?${params.toString()}`, { method: "POST" });
        const data = await res.json();
        showToast(data.message || "Đã xóa bài thi thành công!", "success");
        await fetchResults();
    } catch (err) {
        showAlert({ title: "Lỗi Khi Xóa", message: "Lỗi khi xóa bài thi: " + err, type: "error" });
    }
}

async function clearGradeResults() {
    const menu = document.getElementById("clear-dropdown-menu");
    if (menu) menu.classList.add("hidden");

    const confirmed = await showConfirm({
        title: "Xóa Toàn Bộ Bài Thi Khối",
        message: `Thầy/Cô có chắc chắn muốn xóa toàn bộ danh sách bài thi của ${currentGrade} không?\nThao tác này không thể hoàn tác!`,
        confirmText: "Xóa Toàn Bộ Khối",
        isDanger: true
    });
    if (!confirmed) return;

    try {
        const res = await fetch(`/api/grade/clear?grade=${encodeURIComponent(currentGrade)}`, { method: "POST" });
        const data = await res.json();
        showToast(data.message || `Đã xóa bài thi của ${currentGrade}`, "success");
        await fetchResults();
    } catch (err) {
        showAlert({ title: "Lỗi Khi Xóa", message: "Lỗi khi xóa bài thi: " + err, type: "error" });
    }
}

async function clearAllResults() {
    const menu = document.getElementById("clear-dropdown-menu");
    if (menu) menu.classList.add("hidden");

    const confirmed = await showConfirm({
        title: "⚠️ CẢNH BÁO: XÓA SẠCH DỮ LIỆU",
        message: "Thao tác này sẽ xóa sạch danh sách bài thi của TẤT CẢ các khối (Khối 10, Khối 11, Khối 12)!\nThầy/Cô có chắc chắn muốn tiếp tục không?",
        confirmText: "Xóa Sạch Tất Cả",
        isDanger: true
    });
    if (!confirmed) return;

    try {
        const res = await fetch("/api/grade/clear", { method: "POST" });
        const data = await res.json();
        showToast(data.message || "Đã xóa toàn bộ bài thi của tất cả các khối", "success");
        await fetchResults();
    } catch (err) {
        showAlert({ title: "Lỗi Khi Xóa", message: "Lỗi khi xóa bài thi: " + err, type: "error" });
    }
}

async function deleteSingleResultDirect(resultId, event) {
    if (event) {
        event.stopPropagation();
    }
    if (!resultId) return;

    const confirmed = await showConfirm({
        title: "Xóa Bài Thi",
        message: "Thầy/Cô có chắc chắn muốn xóa bài thi này khỏi danh sách kết quả không?",
        confirmText: "Xóa Bài Thi",
        isDanger: true
    });
    if (!confirmed) return;

    try {
        const res = await fetch(`/api/results/${resultId}`, {
            method: "DELETE"
        });
        const data = await res.json();
        if (res.ok && data.status === "success") {
            showToast("Đã xóa bài thi thành công!", "success");
            await fetchResults();
        } else {
            showAlert({ title: "Không Thể Xóa", message: data.detail || "Không thể xóa bài thi", type: "error" });
        }
    } catch (err) {
        showAlert({ title: "Lỗi Hệ Thống", message: "Lỗi khi xóa bài thi: " + err, type: "error" });
    }
}

// 5. Modal Soát Lỗi & Đổi Mã Đề (Chấm Lại Tức Thì)
function openInspectorModal(resultId) {
    const r = gradedResults.find(item => item.id === resultId);
    if (!r) return;
    currentModalResultId = resultId;

    const validCodes = Object.keys(examConfig.keys || {});
    const isUnknownCode = !validCodes.includes(r.exam_code);

    document.getElementById("modal-student-header").innerText = `Bài Thi: ${r.file_name}`;
    
    document.getElementById("modal-student-sub").innerHTML = `
        <div class="flex items-center gap-3 mt-1.5 flex-wrap">
            <span class="font-bold text-amber-300 text-xs">SBD: ${r.student_sbd || "---"}</span>
            <span class="font-bold ${isUnknownCode ? 'bg-red-500 text-white px-1.5 py-0.5 rounded' : 'text-emerald-300'} text-xs">Mã đề: ${r.exam_code || "---"}</span>
        </div>
    `;

    const editSbdEl = document.getElementById("modal-edit-sbd");
    if (editSbdEl) editSbdEl.value = r.student_sbd || "";

    document.getElementById("modal-score").innerText = `${r.total_score.toFixed(2)}đ`;
    document.getElementById("modal-p1-score").innerText = `Phần I (TN): ${r.score_part1.toFixed(2)}đ`;
    document.getElementById("modal-p2-score").innerText = `Phần II (Đ/S): ${r.score_part2.toFixed(2)}đ`;
    document.getElementById("modal-p3-score").innerText = `Phần III (Số): ${r.score_part3.toFixed(2)}đ`;

    if (r.annotated_image_url) {
        document.getElementById("modal-img").src = r.annotated_image_url;
    }

    // Danh sách lỗi/cảnh báo
    const issuesContainer = document.getElementById("modal-issues");
    issuesContainer.innerHTML = "";

    // Nếu bài bị lỗi 4 góc hoặc Sai Mã Đề -> Hiển thị hộp thông báo/xử lý tương ứng
    if (r.exam_code === "LỖI_4_GÓC") {
        const fixBlock = document.createElement("div");
        fixBlock.className = "p-3 bg-red-50 border border-red-300 rounded-xl text-xs space-y-2 text-red-950";
        fixBlock.innerHTML = `
            <div class="font-bold flex items-center gap-1.5 text-red-700 text-sm">
                <i data-lucide="alert-octagon" class="w-4 h-4 text-red-600"></i>
                Không nhận diện được đủ 4 ô vuông đen góc định vị!
            </div>
            <p class="text-slate-700 leading-relaxed">
                Hệ thống chỉ nắn phẳng hình học và chấm điểm chính xác khi nhìn thấy trọn vẹn <b>4 ô vuông đen</b> ở 4 góc của phiếu thi QM 2025 (ảnh hiện tại bị cắt góc, ngón tay che hoặc quá mờ).
            </p>
            <div class="p-2 bg-red-100/70 border border-red-200 rounded-lg text-red-800 font-semibold flex items-center gap-2">
                <i data-lucide="camera" class="w-4 h-4 flex-shrink-0 text-red-600"></i>
                <span><b>👉 Yêu cầu:</b> Vui lòng chụp lại ảnh bài thi bao quát, thẳng góc từ trên xuống và lấy đủ 4 ô vuông đen ở 4 góc bài thi.</span>
            </div>
        `;
        issuesContainer.appendChild(fixBlock);
    } else if (isUnknownCode) {
        const fixBlock = document.createElement("div");
        fixBlock.className = "p-3 bg-red-50 border border-red-200 rounded-xl text-xs space-y-2 text-red-900";
        fixBlock.innerHTML = `
            <div class="font-bold flex items-center gap-1.5 text-red-700">
                <i data-lucide="alert-octagon" class="w-4 h-4 text-red-600"></i>
                Mã đề '${r.exam_code || "Trống"}' không hợp lệ hoặc chưa có đáp án!
            </div>
            <p class="text-slate-600">Học sinh đã tô nhầm hoặc sai lệch mã đề. Thầy/Cô chọn mã đề đúng để hệ thống chấm lại ngay:</p>
            <div class="flex items-center gap-2">
                <select id="modal-select-correct-code" class="px-2.5 py-1 bg-white border border-red-300 rounded-lg font-bold text-slate-800 text-xs">
                    ${validCodes.map(c => `<option value="${c}">Chấm theo Mã đề ${c}</option>`).join('')}
                </select>
                <button type="button" onclick="regradeFromModal()" class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg transition flex items-center gap-1">
                    <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i> Chấm Lại Ngay
                </button>
            </div>
        `;
        issuesContainer.appendChild(fixBlock);
    }

    if (r.flagged_issues && r.flagged_issues.length > 0) {
        r.flagged_issues.forEach(issue => {
            const div = document.createElement("div");
            div.className = "text-xs px-3 py-1.5 bg-amber-50 border border-amber-200 text-amber-800 rounded-lg flex items-center gap-1.5";
            div.innerHTML = `<i data-lucide="alert-triangle" class="w-3.5 h-3.5 text-amber-600 flex-shrink-0"></i> <span>${issue}</span>`;
            issuesContainer.appendChild(div);
        });
    }

    // Chi tiết câu hỏi
    const qList = document.getElementById("modal-questions-list");
    qList.innerHTML = "";
    if (r.detailed_results && r.detailed_results.length > 0) {
        r.detailed_results.forEach(q => {
            const row = document.createElement("div");
            row.className = `p-2 rounded-lg border flex items-center justify-between ${
                q.is_correct ? 'bg-emerald-50/50 border-emerald-200 text-emerald-900' : 'bg-red-50/50 border-red-200 text-red-900'
            }`;

            let ansText = "";
            let keyText = "";
            if (q.part === 2) {
                const subAns = q.student_answer || {};
                const subKey = q.correct_answer || {};
                ansText = ['a','b','c','d'].map(k => `${k}:${subAns[k] === true ? 'Đ' : subAns[k] === false ? 'S' : '-'}`).join(' ');
                keyText = ['a','b','c','d'].map(k => `${k}:${subKey[k] === true ? 'Đ' : 'S'}`).join(' ');
            } else {
                ansText = q.student_answer || "Trống";
                keyText = q.correct_answer || "Chưa có";
            }

            row.innerHTML = `
                <div>
                    <span class="font-bold">Câu ${q.question_num} (Phần ${q.part}):</span>
                    <span class="ml-2">Tô: <b>${ansText}</b></span>
                    ${!q.is_correct ? `<span class="ml-2 text-slate-500">(Đ.Á: <b>${keyText}</b>)</span>` : ''}
                </div>
                <div class="font-bold">
                    +${q.score.toFixed(2)}đ
                </div>
            `;
            qList.appendChild(row);
        });
    } else {
        qList.innerHTML = `<div class="p-3 text-center text-slate-400 italic">Chưa có kết quả chi tiết từng câu do bài thi đang ở trạng thái 'Sai mã đề'. Hãy chọn mã đề đúng và bấm 'Chấm Lại Ngay'.</div>`;
    }

    document.getElementById("inspector-modal").classList.remove("hidden");
    lucide.createIcons();
}

async function regradeFromModal() {
    if (!currentModalResultId) return;
    const select = document.getElementById("modal-select-correct-code");
    if (!select) return;
    const targetCode = select.value;

    const formData = new FormData();
    formData.append("new_exam_code", targetCode);

    try {
        const res = await fetch(`/api/results/${currentModalResultId}/regrade`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (data.status === "success") {
            await fetchResults();
            openInspectorModal(currentModalResultId);
            showToast(`Đã chấm lại bài thi theo Mã đề ${targetCode} thành công!`, "success");
        } else {
            showAlert({ title: "Lỗi Chấm Lại", message: data.detail || "Không thể chấm lại bài thi", type: "error" });
        }
    } catch (err) {
        showAlert({ title: "Lỗi Hệ Thống", message: "Lỗi chấm lại: " + err, type: "error" });
    }
}

async function saveStudentInfoFromModal() {
    if (!currentModalResultId) return;
    const sbd = document.getElementById("modal-edit-sbd")?.value?.trim() || "";

    try {
        const res = await fetch(`/api/results/${currentModalResultId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                student_sbd: sbd
            })
        });
        const data = await res.json();
        if (data.status === "success") {
            const idx = gradedResults.findIndex(item => item.id === currentModalResultId);
            if (idx !== -1) {
                gradedResults[idx].student_sbd = sbd;
            }
            renderResultsTable();
            showToast("Đã cập nhật Số Báo Danh (SBD) thành công!", "success");
        } else {
            showAlert({ title: "Không Thể Lưu", message: data.detail || "Lỗi khi cập nhật SBD", type: "error" });
        }
    } catch (err) {
        showAlert({ title: "Lỗi Hệ Thống", message: "Lỗi khi lưu SBD: " + err, type: "error" });
    }
}

function closeModal() {
    document.getElementById("inspector-modal").classList.add("hidden");
    currentModalResultId = null;
}

async function deleteCurrentResultFromModal() {
    if (!currentModalResultId) return;
    const confirmed = await showConfirm({
        title: "Xóa Bài Thi",
        message: "Thầy/Cô có chắc chắn muốn xóa bài thi này khỏi danh sách kết quả không?",
        confirmText: "Xóa Bài Thi",
        isDanger: true
    });
    if (!confirmed) return;

    try {
        const res = await fetch(`/api/results/${currentModalResultId}`, {
            method: "DELETE"
        });
        const data = await res.json();
        if (res.ok && data.status === "success") {
            closeModal();
            showToast("Đã xóa bài thi thành công!", "success");
            await fetchResults();
        } else {
            showAlert({ title: "Không Thể Xóa", message: data.detail || "Không thể xóa bài thi", type: "error" });
        }
    } catch (err) {
        showAlert({ title: "Lỗi Hệ Thống", message: "Lỗi khi xóa bài thi: " + err, type: "error" });
    }
}

// 6. Thống Kê & Phổ Điểm (Theo Mẫu Chuẩn Bộ GD&ĐT)
let statsCodeFilter = "ALL";
let statsStepFilter = 0.25;

// Plugin Chart.js tự động vẽ số lượng thí sinh trên đầu mỗi cột
const chartDataLabelsPlugin = {
    id: 'chartDataLabelsPlugin',
    afterDatasetsDraw(chart) {
        const { ctx } = chart;
        chart.data.datasets.forEach((dataset, i) => {
            const meta = chart.getDatasetMeta(i);
            meta.data.forEach((bar, index) => {
                const val = dataset.data[index];
                if (val > 0) {
                    ctx.save();
                    ctx.fillStyle = '#1e3a8a'; // Xanh đậm dễ đọc
                    ctx.font = 'bold 9px sans-serif';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'bottom';
                    ctx.fillText(val.toString(), bar.x, bar.y - 3);
                    ctx.restore();
                }
            });
        });
    }
};

function onStatsFilterChange() {
    const codeSelect = document.getElementById("stats-code-filter");
    const stepSelect = document.getElementById("stats-step-filter");

    if (codeSelect) statsCodeFilter = codeSelect.value;
    if (stepSelect) statsStepFilter = parseFloat(stepSelect.value) || 0.25;

    renderStatistics();
}

function populateStatsFilters() {
    // 1. Mã đề filter
    const codeSelect = document.getElementById("stats-code-filter");
    if (codeSelect) {
        const currentVal = codeSelect.value || "ALL";
        const validCodes = Object.keys(examConfig?.keys || {}).sort();
        codeSelect.innerHTML = `<option value="ALL">Tất cả mã đề</option>`;
        validCodes.forEach(c => {
            const opt = document.createElement("option");
            opt.value = c;
            opt.textContent = `Mã đề ${c}`;
            codeSelect.appendChild(opt);
        });
        if (validCodes.includes(currentVal) || currentVal === "ALL") {
            codeSelect.value = currentVal;
            statsCodeFilter = currentVal;
        } else {
            codeSelect.value = "ALL";
            statsCodeFilter = "ALL";
        }
    }
}

function exportStatsChartImage() {
    const canvas = document.getElementById("chart-grades");
    if (!canvas || !chartInstance) {
        showToast("Chưa có biểu đồ phổ điểm để tải ảnh!", "warning");
        return;
    }
    const subj = (examConfig?.subject_name || "MonHoc").replace(/\s+/g, '_');
    const grade = (currentGrade || "Khoi").replace(/\s+/g, '_');
    const link = document.createElement("a");
    link.download = `PhoDiem_${grade}_${subj}.png`;
    link.href = canvas.toDataURL("image/png", 1.0);
    link.click();
}

function renderStatistics() {
    populateStatsFilters();

    const validCodes = Object.keys(examConfig?.keys || {});
    // Lọc bài thi thuộc khối hiện tại và có mã đề hợp lệ
    let filtered = gradedResults.filter(r => {
        const rGrade = r.grade_level || currentGrade;
        return rGrade === currentGrade && validCodes.includes(r.exam_code);
    });

    // Lọc theo mã đề nếu chọn
    if (statsCodeFilter && statsCodeFilter !== "ALL") {
        filtered = filtered.filter(r => r.exam_code === statsCodeFilter);
    }

    const scores = filtered.map(r => r.total_score).filter(s => s !== null && !isNaN(s));
    const n = scores.length;

    // Cập nhật các tiêu đề chuẩn mẫu Bộ GD&ĐT
    const subjName = (examConfig?.subject_name || "Vật lí 10").trim();
    const acadYear = (examConfig?.academic_year || "2026 - 2027").trim();
    const mainTitleEl = document.getElementById("stats-main-header-title");
    const subTitleEl = document.getElementById("stats-main-subtitle");
    const chartTitleEl = document.getElementById("chart-grades-title");
    const summaryLabelEl = document.getElementById("stats-filter-summary-label");
    const axisNoteEl = document.getElementById("chart-x-axis-note");

    const step = parseFloat(statsStepFilter) || 0.25;

    if (mainTitleEl) mainTitleEl.innerText = `PHỔ ĐIỂM MÔN ${subjName.toUpperCase()} NĂM ${acadYear}`;
    if (subTitleEl) subTitleEl.innerText = `Biểu đồ phổ điểm thi THPT môn ${subjName} - năm ${acadYear} • ${currentGrade}`;
    if (chartTitleEl) chartTitleEl.innerText = `Biểu đồ phổ điểm thi THPT môn ${subjName} - năm ${acadYear}`;
    if (axisNoteEl) axisNoteEl.innerText = `Trục hoành: Khoảng điểm (bước nhảy ${step.toFixed(2)}đ)`;

    const filterText = statsCodeFilter !== "ALL" ? `Mã ${statsCodeFilter} (${currentGrade})` : `Tất cả bài thi (${currentGrade})`;
    if (summaryLabelEl) summaryLabelEl.innerText = filterText;

    // Điểm tối đa thực tế của định dạng đề thi (3.0 + 2.0 + 2.0 = 7.0 hoặc 10.0)
    const maxPossibleScore = (examConfig?.part1_max_score || 3.0) + (examConfig?.part2_max_score || 2.0) + (examConfig?.part3_max_score || 2.0);
    const passThreshold = maxPossibleScore * 0.5;

    // Tính toán chỉ số thống kê (Bảng chuẩn như ảnh)
    let avg = 0;
    let median = 0;
    let stdDev = 0;
    let maxScoreCount = 0;
    let zeroScoreCount = 0;
    let modeScore = 0;
    let modeFreq = 0;
    let minScore = 0;
    let maxScore = 0;
    let passCount = 0;
    let passRate = 0;
    let paralysisCount = 0;

    if (n > 0) {
        const sorted = [...scores].sort((a, b) => a - b);
        minScore = sorted[0];
        maxScore = sorted[sorted.length - 1];

        // 1. ĐTB (Mean)
        const sum = scores.reduce((acc, s) => acc + s, 0);
        avg = sum / n;

        // 2. Trung vị (Median)
        const mid = Math.floor(n / 2);
        if (n % 2 !== 0) {
            median = sorted[mid];
        } else {
            median = (sorted[mid - 1] + sorted[mid]) / 2;
        }

        // 3. Độ lệch chuẩn (Sample Standard Deviation)
        if (n > 1) {
            const sqDiff = scores.reduce((acc, s) => acc + Math.pow(s - avg, 2), 0);
            stdDev = Math.sqrt(sqDiff / (n - 1));
        } else {
            stdDev = 0;
        }

        // 4. Số điểm tối đa, điểm 0, điểm liệt <= 1.0
        const maxThreshold = Math.round(maxPossibleScore * 100) / 100;
        maxScoreCount = scores.filter(s => Math.abs(s - maxThreshold) < 0.01).length;
        zeroScoreCount = scores.filter(s => s === 0).length;
        paralysisCount = scores.filter(s => s <= 1.0).length;

        // 5. Mốt (Mode)
        const freq = {};
        scores.forEach(s => {
            const key = (Math.round(s * 100) / 100).toFixed(2);
            freq[key] = (freq[key] || 0) + 1;
            if (freq[key] > modeFreq) {
                modeFreq = freq[key];
                modeScore = parseFloat(key);
            }
        });

        // 6. Tỉ lệ đạt
        passCount = scores.filter(s => s >= passThreshold).length;
        passRate = (passCount / n) * 100;
    }

    // Cập nhật giá trị vào Bảng Chỉ Số Thống Kê (chuẩn như ảnh)
    const tblTotal = document.getElementById("tbl-stat-total");
    const tblAvg = document.getElementById("tbl-stat-avg");
    const tblMedian = document.getElementById("tbl-stat-median");
    const tblStd = document.getElementById("tbl-stat-std");
    const tblMaxLabel = document.getElementById("tbl-stat-maxscore-label");
    const tblMaxCount = document.getElementById("tbl-stat-maxscore-count");
    const tblZero = document.getElementById("tbl-stat-zero");
    const tblMode = document.getElementById("tbl-stat-mode");
    const tblMax = document.getElementById("tbl-stat-max");
    const tblMin = document.getElementById("tbl-stat-min");
    const tblPassLabel = document.getElementById("tbl-stat-pass-label");
    const tblPass = document.getElementById("tbl-stat-pass");
    const tblParalysis = document.getElementById("tbl-stat-paralysis");

    if (tblTotal) tblTotal.innerText = n.toLocaleString('vi-VN');
    if (tblAvg) tblAvg.innerText = avg.toFixed(2);
    if (tblMedian) tblMedian.innerText = median.toFixed(2);
    if (tblStd) tblStd.innerText = stdDev.toFixed(2);
    if (tblMaxLabel) tblMaxLabel.innerText = `Số điểm ${maxPossibleScore.toFixed(1)}`;
    if (tblMaxCount) tblMaxCount.innerText = maxScoreCount;
    if (tblZero) tblZero.innerText = zeroScoreCount;
    if (tblMode) tblMode.innerText = n > 0 ? `${modeScore.toFixed(2)}đ (${modeFreq} em)` : "---";
    if (tblMax) tblMax.innerText = `${maxScore.toFixed(2)}đ`;
    if (tblMin) tblMin.innerText = `${minScore.toFixed(2)}đ`;
    if (tblPassLabel) tblPassLabel.innerText = `Tỉ lệ đạt (>= ${passThreshold.toFixed(1)}đ)`;
    if (tblPass) tblPass.innerText = `${passRate.toFixed(1)}% (${passCount}/${n})`;
    if (tblParalysis) tblParalysis.innerText = `${paralysisCount} em`;

    // 7. Tạo các Bins và Phân bổ cột điểm
    const numBins = Math.max(1, Math.round(maxPossibleScore / step));
    const labels = [];
    const bins = new Array(numBins).fill(0);

    for (let i = 0; i < numBins; i++) {
        const low = i * step;
        const high = (i + 1) * step;
        const lowStr = (Math.round(low * 100) / 100).toString().replace('.', ',');
        const highStr = (Math.round(high * 100) / 100).toString().replace('.', ',');
        if (i === 0) {
            labels.push(`[${lowStr}; ${highStr}]`);
        } else {
            labels.push(`(${lowStr}; ${highStr}]`);
        }
    }

    scores.forEach(s => {
        if (s <= 0) {
            bins[0]++;
        } else {
            let idx = Math.ceil(Math.round(s * 1000) / 1000 / step) - 1;
            idx = Math.max(0, Math.min(numBins - 1, idx));
            bins[idx]++;
        }
    });

    // 8. Vẽ Biểu Đồ Chart.js
    const canvas = document.getElementById("chart-grades");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (chartInstance) {
        chartInstance.destroy();
        chartInstance = null;
    }

    chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: `Số lượng thí sinh`,
                data: bins,
                backgroundColor: 'rgba(43, 108, 176, 0.88)', // Màu xanh dương chuẩn theo ảnh
                hoverBackgroundColor: 'rgba(30, 64, 175, 1)',
                borderColor: 'rgba(30, 64, 175, 1)',
                borderWidth: 1,
                borderRadius: 2,
                barPercentage: 0.96,
                categoryPercentage: 0.96
            }]
        },
        plugins: [chartDataLabelsPlugin],
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    top: 20, // Chừa khoảng trống phía trên đỉnh cột để hiển thị con số
                    bottom: 5
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(items) {
                            return `Khoảng điểm: ${items[0].label}`;
                        },
                        label: function(item) {
                            const count = item.raw;
                            const pct = n > 0 ? ((count / n) * 100).toFixed(1) : 0;
                            return `Số thí sinh: ${count} em (${pct}%)`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Điểm',
                        font: { weight: 'bold', size: 12 },
                        color: '#1e293b'
                    },
                    ticks: {
                        font: { size: 9 },
                        color: '#475569',
                        maxRotation: 90,
                        minRotation: 90,
                        autoSkip: false
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Số lượng thí sinh',
                        font: { weight: 'bold', size: 12 },
                        color: '#1e293b'
                    },
                    ticks: {
                        stepSize: 1,
                        precision: 0,
                        color: '#475569',
                        font: { size: 10 }
                    },
                    grid: {
                        color: 'rgba(226, 232, 240, 0.8)'
                    }
                }
            }
        }
    });

    lucide.createIcons();
}
