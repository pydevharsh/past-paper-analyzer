import json
import re
from collections import Counter
from datetime import date, timedelta
from difflib import SequenceMatcher
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
from werkzeug.utils import secure_filename

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "webp"}

app = Flask(__name__)
CORS(app)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 80 * 1024 * 1024

latest_analysis = {}


HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI DecodeX - Smart Paper Analyzer</title>
    <style>
        * { box-sizing: border-box; }
        :root {
            --primary: #2563eb;
            --secondary: #06b6d4;
            --accent: #0f172a;
            --success: #0f766e;
            --warning: #f59e0b;
            --muted: #64748b;
            --soft: #eef6ff;
            --line: rgba(148, 163, 184, 0.28);
            --glass: rgba(255, 255, 255, 0.72);
        }
        body {
            margin: 0;
            min-height: 100vh;
            font-family: Inter, Segoe UI, Arial, sans-serif;
            color: var(--accent);
            background:
                radial-gradient(circle at 12% 10%, rgba(37, 99, 235, 0.22), transparent 30%),
                radial-gradient(circle at 88% 18%, rgba(6, 182, 212, 0.20), transparent 32%),
                radial-gradient(circle at 50% 100%, rgba(15, 118, 110, 0.13), transparent 35%),
                linear-gradient(135deg, #f8fbff 0%, #eef6ff 46%, #f8fafc 100%);
        }
        .shell {
            min-height: 100vh;
            padding: 24px;
        }
        .nav {
            max-width: 1240px;
            margin: 0 auto 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            padding: 16px 18px;
            border: 1px solid var(--line);
            border-radius: 18px;
            background: var(--glass);
            box-shadow: 0 18px 50px rgba(15, 23, 42, 0.10);
            backdrop-filter: blur(18px);
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .logo {
            width: 48px;
            height: 48px;
            border-radius: 14px;
            display: grid;
            place-items: center;
            color: white;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            font-weight: 900;
            box-shadow: 0 12px 28px rgba(37, 99, 235, 0.28);
        }
        h1, h2, h3, p { margin-top: 0; }
        .brand h1 { margin: 0; font-size: 24px; letter-spacing: 0; }
        .brand p { margin: 3px 0 0; color: #475569; font-size: 14px; }
        .badge {
            border: 1px solid rgba(37, 99, 235, 0.22);
            border-radius: 999px;
            padding: 9px 13px;
            color: #1d4ed8;
            background: rgba(255, 255, 255, 0.68);
            font-weight: 800;
            font-size: 13px;
        }
        .container {
            max-width: 1240px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: minmax(320px, 390px) 1fr;
            gap: 22px;
            align-items: start;
        }
        .glass {
            border: 1px solid var(--line);
            border-radius: 22px;
            background: var(--glass);
            box-shadow: 0 18px 50px rgba(15, 23, 42, 0.10);
            backdrop-filter: blur(18px);
        }
        .panel-header { padding: 22px 22px 0; }
        .panel-header h2 { margin-bottom: 8px; font-size: 21px; }
        .panel-header p { color: #475569; line-height: 1.55; font-size: 14px; }
        .panel-body { padding: 22px; }
        .step-list {
            display: grid;
            gap: 10px;
            margin: 16px 0 0;
        }
        .step {
            display: grid;
            grid-template-columns: 30px 1fr;
            gap: 10px;
            align-items: center;
            color: #475569;
            font-size: 13px;
        }
        .step span {
            width: 30px;
            height: 30px;
            display: grid;
            place-items: center;
            border-radius: 10px;
            color: white;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            font-weight: 900;
        }
        label {
            display: block;
            margin: 16px 0 8px;
            color: #1e293b;
            font-size: 14px;
            font-weight: 900;
        }
        label:first-child { margin-top: 0; }
        input, select {
            width: 100%;
            border: 1px solid rgba(148, 163, 184, 0.42);
            border-radius: 14px;
            padding: 13px 14px;
            font: inherit;
            color: #0f172a;
            background: rgba(255, 255, 255, 0.78);
            outline: none;
        }
        input:focus, select:focus {
            border-color: rgba(37, 99, 235, 0.65);
            box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.12);
        }
        .paper-input {
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 10px;
            align-items: center;
            margin-bottom: 10px;
        }
        .icon-btn {
            width: 44px;
            height: 44px;
            margin: 0;
            padding: 0;
            border-radius: 14px;
            background: #e11d48;
        }
        .hint {
            margin: 8px 0 0;
            color: #64748b;
            line-height: 1.45;
            font-size: 13px;
        }
        .row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        button {
            width: 100%;
            margin-top: 16px;
            border: 0;
            border-radius: 14px;
            padding: 14px 16px;
            color: white;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            font-weight: 900;
            cursor: pointer;
            box-shadow: 0 12px 26px rgba(37, 99, 235, 0.22);
        }
        button:hover { filter: brightness(0.97); }
        button:disabled { opacity: 0.65; cursor: not-allowed; }
        .secondary-btn {
            color: #1d4ed8;
            background: rgba(255, 255, 255, 0.76);
            border: 1px solid rgba(37, 99, 235, 0.26);
            box-shadow: none;
        }
        .status {
            min-height: 22px;
            margin-top: 12px;
            color: #1d4ed8;
            font-weight: 900;
            font-size: 14px;
        }
        .dashboard { display: grid; gap: 18px; }
        .empty {
            padding: 46px 24px;
            text-align: center;
            color: #475569;
            border: 1px dashed rgba(37, 99, 235, 0.35);
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.58);
            backdrop-filter: blur(18px);
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 14px;
        }
        .metric {
            padding: 18px;
            border: 1px solid var(--line);
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.68);
            backdrop-filter: blur(18px);
        }
        .metric span {
            color: #64748b;
            font-size: 12px;
            text-transform: uppercase;
            font-weight: 900;
        }
        .metric strong {
            display: block;
            margin-top: 9px;
            font-size: 28px;
        }
        .hero-result {
            display: grid;
            grid-template-columns: 1.1fr 0.9fr;
            gap: 18px;
        }
        .lane-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
        }
        .lane {
            min-height: 150px;
            padding: 16px;
            border: 1px solid var(--line);
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.68);
        }
        .lane h3 {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        .lane h3 span {
            min-width: 30px;
            text-align: center;
            border-radius: 999px;
            padding: 4px 8px;
            color: white;
            background: var(--primary);
            font-size: 12px;
        }
        .card {
            padding: 18px;
            border: 1px solid var(--line);
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.70);
            backdrop-filter: blur(18px);
        }
        .card h3 { margin-bottom: 14px; font-size: 18px; }
        .grid2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 18px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        th, td {
            padding: 12px 10px;
            border-bottom: 1px solid rgba(148, 163, 184, 0.24);
            text-align: left;
            vertical-align: top;
        }
        td.question-cell {
            max-width: 430px;
            line-height: 1.45;
        }
        th {
            color: #475569;
            font-size: 12px;
            text-transform: uppercase;
        }
        .pill {
            display: inline-flex;
            justify-content: center;
            min-width: 108px;
            border-radius: 999px;
            padding: 6px 10px;
            color: white;
            font-size: 12px;
            font-weight: 900;
        }
        .most-important { background: #2563eb; }
        .important { background: #0f766e; }
        .extra { background: #64748b; }
        .confidence {
            color: #475569;
            font-size: 12px;
            font-weight: 800;
        }
        .bar-row {
            display: grid;
            grid-template-columns: 130px 1fr 42px;
            gap: 10px;
            align-items: center;
            margin: 11px 0;
            font-size: 13px;
        }
        .bar-label {
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            font-weight: 800;
        }
        .bar-track {
            height: 14px;
            overflow: hidden;
            border-radius: 999px;
            background: rgba(148, 163, 184, 0.28);
        }
        .bar {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
        }
        .planner {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
        }
        .day {
            padding: 15px;
            border: 1px solid var(--line);
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.66);
        }
        .day strong { display: block; margin-bottom: 8px; }
        ul { margin: 0; padding-left: 18px; color: #334155; line-height: 1.55; }
        .warning {
            padding: 14px;
            border: 1px solid rgba(245, 158, 11, 0.35);
            border-radius: 18px;
            color: #92400e;
            background: rgba(255, 251, 235, 0.82);
        }
        @media (max-width: 980px) {
            .container, .grid2, .hero-result, .lane-grid { grid-template-columns: 1fr; }
            .metrics { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 560px) {
            .shell { padding: 14px; }
            .nav { align-items: flex-start; flex-direction: column; }
            .row, .metrics, .paper-input { grid-template-columns: 1fr; }
            .icon-btn { width: 100%; }
        }
    </style>
</head>
<body>
    <div class="shell">
        <nav class="nav">
            <div class="brand">
                <div class="logo">DX</div>
                <div>
                    <h1>AI DecodeX</h1>
                    <p>English past paper analyzer and smart study planner</p>
                </div>
            </div>
            <div class="badge">Hackathon Prototype</div>
        </nav>

        <main class="container">
            <section class="glass">
                <div class="panel-header">
                    <h2>Upload Past Papers</h2>
                    <p>Add one or more English question paper PDFs. The model compares repeated questions and ranks them for preparation.</p>
                    <div class="step-list">
                        <div class="step"><span>1</span><div>Upload English question papers only</div></div>
                        <div class="step"><span>2</span><div>Repeated questions are grouped automatically</div></div>
                        <div class="step"><span>3</span><div>Planner divides work by your days and hours</div></div>
                    </div>
                </div>
                <div class="panel-body">
                    <form id="analyzeForm">
                        <label>Past Year Paper PDFs / Images</label>
                        <div id="paperInputs">
                            <div class="paper-input">
                                <input name="papers" type="file" accept=".pdf,.png,.jpg,.jpeg,.webp" required>
                                <button class="icon-btn" type="button" onclick="removePaperInput(this)">X</button>
                            </div>
                        </div>
                        <button class="secondary-btn" type="button" onclick="addPaperInput()">Add Paper</button>
                        <p class="hint">Only English question papers are accepted. Gujarati/Hindi/result/marksheet files will be rejected.</p>

                        <div class="row">
                            <div>
                                <label for="days">Study Days</label>
                                <select id="days" name="days">
                                    <option value="3">3 days</option>
                                    <option value="5">5 days</option>
                                    <option value="7" selected>7 days</option>
                                    <option value="10">10 days</option>
                                    <option value="14">14 days</option>
                                    <option value="21">21 days</option>
                                </select>
                            </div>
                            <div>
                                <label for="hours">Hours / Day</label>
                                <select id="hours" name="hours">
                                    <option value="1">1 hour</option>
                                    <option value="2" selected>2 hours</option>
                                    <option value="3">3 hours</option>
                                    <option value="4">4 hours</option>
                                    <option value="5">5 hours</option>
                                    <option value="6">6 hours</option>
                                </select>
                            </div>
                        </div>

                        <button id="analyzeButton" type="submit">Analyze Questions</button>
                        <div id="status" class="status"></div>
                    </form>
                </div>
            </section>

            <section id="dashboard" class="dashboard">
                <div class="empty">Upload English past papers to see repeated questions, importance ranking, and study planner.</div>
            </section>
        </main>
    </div>

    <script>
        const form = document.getElementById("analyzeForm");
        const paperInputs = document.getElementById("paperInputs");
        const statusBox = document.getElementById("status");
        const dashboard = document.getElementById("dashboard");
        const analyzeButton = document.getElementById("analyzeButton");

        function addPaperInput() {
            const wrapper = document.createElement("div");
            wrapper.className = "paper-input";
            wrapper.innerHTML = `
                <input name="papers" type="file" accept=".pdf,.png,.jpg,.jpeg,.webp" required>
                <button class="icon-btn" type="button" onclick="removePaperInput(this)">X</button>
            `;
            paperInputs.appendChild(wrapper);
        }

        function removePaperInput(button) {
            if (paperInputs.children.length === 1) {
                paperInputs.querySelector("input").value = "";
                return;
            }
            button.parentElement.remove();
        }

        function escapeHtml(value) {
            return String(value)
                .replaceAll("&", "&amp;")
                .replaceAll("<", "&lt;")
                .replaceAll(">", "&gt;")
                .replaceAll('"', "&quot;");
        }

        function className(label) {
            return label.toLowerCase().replaceAll(" ", "-");
        }

        function bars(labels, values) {
            const maxValue = Math.max(...values, 1);
            return labels.map((label, index) => {
                const width = Math.max(5, Math.round((values[index] / maxValue) * 100));
                return `
                    <div class="bar-row">
                        <div class="bar-label" title="${escapeHtml(label)}">${escapeHtml(label)}</div>
                        <div class="bar-track"><div class="bar" style="width:${width}%"></div></div>
                        <strong>${values[index]}</strong>
                    </div>
                `;
            }).join("");
        }

        function renderDashboard(data) {
            const rejected = data.rejected_files.length
                ? `<div class="warning"><strong>Rejected files:</strong><ul>${data.rejected_files.map(item => `<li>${escapeHtml(item.filename)} - ${escapeHtml(item.reason)}</li>`).join("")}</ul></div>`
                : "";

            dashboard.innerHTML = `
                ${rejected}
                <div class="metrics">
                    <div class="metric"><span>Papers Added</span><strong>${data.metrics.valid_papers}</strong></div>
                    <div class="metric"><span>Questions Found</span><strong>${data.metrics.questions_found}</strong></div>
                    <div class="metric"><span>Repeated Groups</span><strong>${data.metrics.repeated_groups}</strong></div>
                    <div class="metric"><span>Model Confidence</span><strong>${data.metrics.confidence}%</strong></div>
                    <div class="metric"><span>Study Load</span><strong>${data.metrics.total_study_hours}h</strong></div>
                </div>

                <div class="hero-result">
                    <div class="card">
                        <h3>Top Repeated Questions</h3>
                        ${bars(data.charts.repeated.labels, data.charts.repeated.values)}
                    </div>
                    <div class="card">
                        <h3>Importance Split</h3>
                        ${bars(data.charts.importance.labels, data.charts.importance.values)}
                    </div>
                </div>

                <div class="lane-grid">
                    <div class="lane">
                        <h3>Most Important <span>${data.sections.most_important.length}</span></h3>
                        <ul>${data.sections.most_important.slice(0, 5).map(q => `<li>${escapeHtml(q)}</li>`).join("") || "<li>No high-repeat questions yet.</li>"}</ul>
                    </div>
                    <div class="lane">
                        <h3>Important <span>${data.sections.important.length}</span></h3>
                        <ul>${data.sections.important.slice(0, 5).map(q => `<li>${escapeHtml(q)}</li>`).join("") || "<li>No medium-priority questions yet.</li>"}</ul>
                    </div>
                    <div class="lane">
                        <h3>Extra <span>${data.sections.extra.length}</span></h3>
                        <ul>${data.sections.extra.slice(0, 5).map(q => `<li>${escapeHtml(q)}</li>`).join("") || "<li>No extra questions yet.</li>"}</ul>
                    </div>
                </div>

                <div class="card">
                    <h3>Question Ranking</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Question</th>
                                <th>Repeated</th>
                                <th>Papers</th>
                                <th>Marks</th>
                                <th>Score</th>
                                <th>Category</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.question_groups.map((item, index) => `
                                <tr>
                                    <td>${index + 1}</td>
                                    <td class="question-cell"><strong>${escapeHtml(item.question)}</strong><div class="confidence">${item.confidence}% match confidence</div></td>
                                    <td>${item.repeat_count}x</td>
                                    <td>${item.paper_count}</td>
                                    <td>${item.estimated_marks}</td>
                                    <td>${item.score}</td>
                                    <td><span class="pill ${className(item.category)}">${escapeHtml(item.category)}</span></td>
                                </tr>
                            `).join("")}
                        </tbody>
                    </table>
                </div>

                <div class="card">
                    <h3>Most Important</h3>
                    <ul>${data.sections.most_important.map(q => `<li>${escapeHtml(q)}</li>`).join("") || "<li>No repeated high-priority questions found.</li>"}</ul>
                </div>

                <div class="card">
                    <h3>Important</h3>
                    <ul>${data.sections.important.map(q => `<li>${escapeHtml(q)}</li>`).join("") || "<li>No medium-priority questions found.</li>"}</ul>
                </div>

                <div class="card">
                    <h3>Extra</h3>
                    <ul>${data.sections.extra.map(q => `<li>${escapeHtml(q)}</li>`).join("") || "<li>No extra questions found.</li>"}</ul>
                </div>

                <div class="card">
                    <h3>Study Planner</h3>
                    <div class="planner">
                        ${data.study_planner.map(day => `
                            <div class="day">
                                <strong>Day ${day.day} - ${escapeHtml(day.date)}</strong>
                                <ul>${day.tasks.map(task => `<li>${escapeHtml(task)}</li>`).join("")}</ul>
                            </div>
                        `).join("")}
                    </div>
                </div>
            `;
        }

        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            analyzeButton.disabled = true;
            statusBox.textContent = "Reading papers, comparing questions, and building planner...";

            try {
                const response = await fetch("/api/analyze", {
                    method: "POST",
                    body: new FormData(form)
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || "Analysis failed");
                renderDashboard(data);
                statusBox.textContent = "Analysis completed.";
            } catch (error) {
                statusBox.textContent = error.message;
            } finally {
                analyzeButton.disabled = false;
            }
        });
    </script>
</body>
</html>
"""


ENGLISH_QUESTION_WORDS = {
    "explain", "describe", "define", "differentiate", "compare", "discuss", "write",
    "derive", "solve", "calculate", "illustrate", "classify", "analyze", "evaluate",
    "what", "why", "how", "when", "where", "short note", "prove", "design", "state",
    "list", "draw", "prepare", "find", "show", "elaborate"
}

NON_ENGLISH_HINTS = [
    "પ્રશ્ન", "જવાબ", "ગુણ", "કોઈપણ", "નીચેના", "સમજાવો", "લખો",
    "प्रश्न", "उत्तर", "अंक", "समझाइए", "लिखिए", "निम्नलिखित"
]

RESULT_HINTS = {
    "result", "marksheet", "mark sheet", "grade", "cgpa", "sgpa", "roll no",
    "enrollment", "passed", "failed", "obtained marks", "percentage",
    "student name", "father name"
}

RANK_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "to", "of", "in", "on", "for", "and",
    "or", "with", "by", "as", "from", "that", "this", "these", "those", "following",
    "choose", "correct", "answer", "question", "write", "explain", "define", "describe",
    "given", "below", "above", "one", "any", "all"
}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def clean_text(text):
    text = re.sub(r"\r", "\n", text or "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalized(text):
    return re.sub(r"[^a-z0-9?.\s()/:-]", " ", (text or "").lower())


def save_upload(file, index=0):
    UPLOAD_DIR.mkdir(exist_ok=True)
    filename = secure_filename(file.filename or "paper.pdf")
    path = UPLOAD_DIR / f"{index}_{filename}"
    file.save(path)
    return path


def extract_pdf_text(path):
    if PyPDF2 is None:
        raise RuntimeError("PyPDF2 missing hai. Install karo: pip install PyPDF2")

    pages = []
    with open(path, "rb") as pdf_file:
        reader = PyPDF2.PdfReader(pdf_file)
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(f"\n[PAGE {page_number}]\n{page_text.strip()}")
    return clean_text("\n".join(pages))


def extract_image_text(path):
    try:
        from PIL import Image
        import pytesseract

        return clean_text(pytesseract.image_to_string(Image.open(path), lang="eng"))
    except Exception:
        return ""


def extract_text(path):
    ext = path.suffix.lower().replace(".", "")
    if ext == "pdf":
        return extract_pdf_text(path)
    if ext in {"png", "jpg", "jpeg", "webp"}:
        return extract_image_text(path)
    return ""


def english_ratio(text):
    letters = re.findall(r"[A-Za-z]", text or "")
    non_ascii_letters = re.findall(r"[^\W\d_]", text or "", flags=re.UNICODE)
    total_letters = len(non_ascii_letters)
    if total_letters == 0:
        return 0
    return len(letters) / total_letters


def is_english_question_paper(text):
    lower = normalized(text)
    if any(hint in (text or "") for hint in NON_ENGLISH_HINTS):
        return False, "Only English question papers are accepted"

    if english_ratio(text) < 0.82:
        return False, "Document does not look like an English paper"

    result_hits = sum(1 for word in RESULT_HINTS if word in lower)
    table_marks = len(re.findall(r"\b\d{1,3}\s*/\s*\d{1,3}\b", lower))
    if result_hits >= 2 or (result_hits >= 1 and table_marks >= 5):
        return False, "Looks like result/marksheet, not a question paper"

    question_word_hits = sum(1 for word in ENGLISH_QUESTION_WORDS if word in lower)
    numbered_questions = len(re.findall(r"(?:^|\n|\s)(?:q\.?|que\.?|question)?\s*\d{1,2}\s*[\).:-]", lower))
    marks_mentions = len(re.findall(r"\b\d{1,2}\s*(?:marks?|m)\b", lower))
    exam_shape = any(word in lower for word in ["answer any", "attempt", "maximum marks", "section", "time allowed"])

    if question_word_hits >= 2 and (numbered_questions >= 1 or marks_mentions >= 1 or exam_shape):
        return True, "Valid English question paper"

    return False, "Question paper pattern not detected"


def split_questions(text):
    text = clean_text(text)
    marker_pattern = re.compile(
        r"(?:^|\n|\s)(?:q\.?|que\.?|question)\s*\.?\s*(\d{1,3})\s*[\).:-]",
        flags=re.IGNORECASE,
    )
    markers = list(marker_pattern.finditer(text))
    questions = []

    if markers:
        for index, marker in enumerate(markers):
            start = marker.end()
            end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
            heading = extract_preceding_heading(text, marker.start())
            chunk = normalize_question_chunk(f"{heading} {text[start:end]}")
            if is_valid_question_text(chunk):
                questions.append(remove_noise(chunk))
    else:
        parts = re.split(
            r"(?:\n|^|\s{2,})\s*\d{1,2}\s*(?:\([a-z]\))?\s*[\).:-]\s*",
            text,
            flags=re.IGNORECASE,
        )

        for part in parts:
            part = clean_text(part)
            if len(part) < 24:
                continue
            candidates = re.split(r"(?<=[?])\s+|(?:\n\s*){2,}", part)
            for candidate in candidates:
                candidate = normalize_question_chunk(candidate)
                if is_valid_question_text(candidate):
                    questions.append(remove_noise(candidate))

    if len(questions) < 2:
        for line in text.splitlines():
            line = normalize_question_chunk(line)
            if is_valid_question_text(line):
                questions.append(remove_noise(line))

    return dedupe_exact([q for q in questions if len(q.split()) >= 3])[:300]


def normalize_question_chunk(chunk):
    chunk = clean_text(chunk)
    chunk = re.sub(r"\[PAGE\s+\d+\]", " ", chunk, flags=re.IGNORECASE)
    chunk = strip_next_section_heading(chunk)
    chunk = re.sub(r"^\(?[A-Da-d]\)\s*", "", chunk)
    chunk = re.sub(r"\s+", " ", chunk)
    return chunk.strip(" -:;")


def extract_preceding_heading(text, marker_start):
    prefix = text[max(0, marker_start - 220):marker_start]
    lines = [clean_text(line) for line in prefix.splitlines() if clean_text(line)]
    if not lines:
        return ""

    line = lines[-1].strip(" -")
    lower = normalized(line)
    heading_signals = [
        "identify", "choose", "change", "spot", "fill in", "substitute",
        "sentence", "meaning", "opposite", "similar", "spelt", "narration", "voice"
    ]
    ignored = ["passage", "read the passage", "q.no"]
    if len(line) <= 150 and any(signal in lower for signal in heading_signals) and not any(signal in lower for signal in ignored):
        return line
    return ""


def strip_next_section_heading(chunk):
    section_patterns = [
        r"\s+Identify the incorrectly spelt word:.*$",
        r"\s+Choose the word almost similar in meaning.*$",
        r"\s+Choose the word almost opposite in meaning.*$",
        r"\s+Choose the correct one word substitute.*$",
        r"\s+A sentence, split into four parts.*$",
        r"\s+Choose the most appropriate answer.*$",
        r"\s+Choose the sentence that conveys.*$",
        r"\s+Spot the erroneous parts.*$",
        r"\s+Change the narration:.*$",
        r"\s+Change the voice:.*$",
    ]
    for pattern in section_patterns:
        chunk = re.sub(pattern, "", chunk, flags=re.IGNORECASE | re.DOTALL)
    return chunk


def is_valid_question_text(question):
    if len(question) < 10:
        return False

    lower = normalized(question)
    word_count = len(re.findall(r"[A-Za-z]+", question))
    option_count = len(re.findall(r"\([A-Da-d]\)", question))
    has_question_word = any(word in lower for word in ENGLISH_QUESTION_WORDS)
    has_marks = bool(re.search(r"\b\d{1,2}\s*(?:marks?|m)\b", lower))
    has_question_mark = "?" in question
    has_blank = "____" in question or "blank" in lower
    has_colon_stem = ":" in question[:120]
    has_error_pattern = "no error" in lower

    if word_count <= 3:
        return False

    # Option-only text is not a question; MCQ stem + options is valid.
    if option_count >= 2 and not (has_question_word or has_question_mark or has_blank or has_colon_stem):
        return False

    return has_question_word or has_question_mark or has_blank or has_colon_stem or has_marks or has_error_pattern or option_count >= 2


def remove_noise(question):
    question = re.sub(r"\[PAGE\s+\d+\]", " ", question, flags=re.IGNORECASE)
    question = re.sub(r"\s+", " ", question).strip(" -:;")
    return question[:420]


def dedupe_exact(items):
    seen = set()
    result = []
    for item in items:
        key = normalized(item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def extract_marks(question):
    matches = re.findall(r"\b(\d{1,2})\s*(?:marks?|m)\b", normalized(question))
    if matches:
        return max(int(value) for value in matches)
    if len(re.findall(r"\([A-Da-d]\)", question)) >= 2:
        return 1
    if len(question) > 180:
        return 10
    if len(question) > 95:
        return 5
    return 2


def question_type(question):
    lower = normalized(question)
    if len(re.findall(r"\([A-Da-d]\)", question)) >= 2:
        return "MCQ"
    if "____" in question or "blank" in lower:
        return "Fill Blank"
    if "no error" in lower or "erroneous" in lower:
        return "Error Spotting"
    if "narration" in lower:
        return "Narration"
    if "voice" in lower:
        return "Voice"
    if "passage" in lower:
        return "Reading"
    return "Theory"


def quality_score(question):
    words = re.findall(r"[A-Za-z]+", question)
    option_count = len(re.findall(r"\([A-Da-d]\)", question))
    score = 35
    if "?" in question:
        score += 15
    if option_count >= 2:
        score += 20
    if 6 <= len(words) <= 60:
        score += 20
    elif len(words) > 60:
        score += 8
    if any(word in normalized(question) for word in ENGLISH_QUESTION_WORDS):
        score += 10
    return min(score, 100)


def canonical(question):
    text = normalized(question)
    text = re.sub(r"\b\d{1,2}\s*(?:marks?|m)\b", " ", text)
    text = re.sub(r"\([a-d]\)", " ", text)
    text = re.sub(r"\b(any|all|following|briefly|detail|suitable|example|diagram|choose|correct|answer)\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def content_tokens(question):
    return {
        token
        for token in re.findall(r"[a-z]{3,}", canonical(question))
        if token not in RANK_STOPWORDS
    }


def similarity(a, b):
    a_key = canonical(a)
    b_key = canonical(b)
    if not a_key or not b_key:
        return 0
    sequence_score = SequenceMatcher(None, a_key, b_key).ratio()
    a_tokens = content_tokens(a)
    b_tokens = content_tokens(b)
    if not a_tokens or not b_tokens:
        token_score = 0
    else:
        token_score = len(a_tokens & b_tokens) / len(a_tokens | b_tokens)
    return max(sequence_score, token_score * 1.12)


def group_similar_questions(question_records):
    groups = []

    for record in question_records:
        best_group = None
        best_score = 0
        for group in groups:
            score = similarity(record["question"], group["question"])
            if score > best_score:
                best_score = score
                best_group = group

        if best_group and best_score >= 0.74:
            best_group["repeat_count"] += 1
            best_group["paper_ids"].add(record["paper_id"])
            best_group["estimated_marks"] = max(best_group["estimated_marks"], record["marks"])
            best_group["quality"] = max(best_group["quality"], record["quality"])
            best_group["confidence"] = max(best_group["confidence"], round(best_score * 100))
            best_group["variants"].append(record["question"])
            if len(record["question"]) > len(best_group["question"]):
                best_group["question"] = record["question"]
        else:
            groups.append(
                {
                    "question": record["question"],
                    "repeat_count": 1,
                    "paper_ids": {record["paper_id"]},
                    "estimated_marks": record["marks"],
                    "quality": record["quality"],
                    "confidence": 100,
                    "type": record["type"],
                    "variants": [record["question"]],
                }
            )

    for group in groups:
        group["paper_count"] = len(group["paper_ids"])
        repeat_score = min(group["repeat_count"], 5) * 24
        coverage_score = min(group["paper_count"], 5) * 22
        marks_score = min(group["estimated_marks"], 10) * 5
        quality_bonus = round(group["quality"] * 0.25)
        group["score"] = repeat_score + coverage_score + marks_score + quality_bonus

    groups.sort(key=lambda item: (item["repeat_count"], item["paper_count"], item["estimated_marks"], item["score"]), reverse=True)
    return groups


def categorize_groups(groups, valid_paper_count):
    if valid_paper_count == 1:
        for index, group in enumerate(groups):
            if group["estimated_marks"] >= 8 or index < max(3, len(groups) // 4):
                group["category"] = "Most Important"
            elif group["estimated_marks"] >= 4 or index < max(6, len(groups) // 2):
                group["category"] = "Important"
            else:
                group["category"] = "Extra"
        return groups

    for group in groups:
        if group["repeat_count"] >= 2 or group["paper_count"] >= 2 or group["score"] >= 92:
            group["category"] = "Most Important"
        elif group["estimated_marks"] >= 5 or group["score"] >= 65:
            group["category"] = "Important"
        else:
            group["category"] = "Extra"
    return groups


def build_study_planner(groups, days, hours_per_day):
    ordered = sorted(
        groups,
        key=lambda item: (
            0 if item["category"] == "Most Important" else 1 if item["category"] == "Important" else 2,
            -item["repeat_count"],
            -item["estimated_marks"],
        ),
    )
    planner = []
    total_slots = max(days, 1)
    chunks = [[] for _ in range(total_slots)]

    for index, group in enumerate(ordered):
        chunks[index % total_slots].append(group)

    minutes = hours_per_day * 60
    start = date.today()
    for index, questions in enumerate(chunks):
        tasks = []
        if not questions:
            tasks.append("Revise formulas, definitions, and short notes from completed questions.")
        else:
            per_question = max(15, minutes // max(len(questions), 1))
            for group in questions[:6]:
                tasks.append(f"{per_question} min: {group['category']} - {group['question'][:95]}")
            if len(questions) > 6:
                tasks.append(f"Quick review: {len(questions) - 6} extra questions")

        planner.append(
            {
                "day": index + 1,
                "date": (start + timedelta(days=index)).strftime("%d %b %Y"),
                "tasks": tasks,
            }
        )
    return planner


def analysis_confidence(groups, valid_papers):
    if not groups or not valid_papers:
        return 0

    avg_question_confidence = sum(group["confidence"] for group in groups) / len(groups)
    repeated_ratio = sum(1 for group in groups if group["repeat_count"] > 1) / len(groups)
    paper_bonus = min(len(valid_papers), 5) * 3
    confidence = avg_question_confidence * 0.65 + repeated_ratio * 25 + paper_bonus
    return min(99, round(confidence))


def analyze_papers(files, days, hours_per_day):
    valid_papers = []
    rejected_files = []
    question_records = []

    for upload_index, uploaded in enumerate(files, start=1):
        if not uploaded or not uploaded.filename:
            continue
        if not allowed_file(uploaded.filename):
            rejected_files.append({"filename": uploaded.filename, "reason": "Unsupported file type"})
            continue

        path = save_upload(uploaded, upload_index)
        filename = secure_filename(uploaded.filename)
        paper_id = f"paper_{upload_index}_{filename}"
        text = extract_text(path)

        if len(text) < 80:
            rejected_files.append({"filename": filename, "reason": "Readable text not found. Upload text-based PDF or OCR-ready image."})
            continue

        is_valid, reason = is_english_question_paper(text)
        if not is_valid:
            rejected_files.append({"filename": filename, "reason": reason})
            continue

        questions = split_questions(text)
        if not questions:
            rejected_files.append({"filename": filename, "reason": "No clear English questions extracted"})
            continue

        valid_papers.append({"filename": filename, "paper_id": paper_id, "questions": len(questions)})
        for question in questions:
            question_records.append(
                {
                    "paper": filename,
                    "paper_id": paper_id,
                    "question": question,
                    "marks": extract_marks(question),
                    "quality": quality_score(question),
                    "type": question_type(question),
                }
            )

    if not valid_papers:
        raise ValueError("No valid English question paper detected. Upload English past paper PDF, not syllabus/result/non-English paper.")

    groups = categorize_groups(group_similar_questions(question_records), len(valid_papers))
    public_groups = []
    for group in groups:
        public_groups.append(
            {
                "question": group["question"],
                "repeat_count": group["repeat_count"],
                "paper_count": group["paper_count"],
                "estimated_marks": group["estimated_marks"],
                "category": group["category"],
                "score": group["score"],
                "confidence": group["confidence"],
                "type": group["type"],
                "variants": group["variants"][:3],
            }
        )

    section_counter = Counter(group["category"] for group in public_groups)
    top_repeated = public_groups[:10]

    return {
        "metrics": {
            "valid_papers": len(valid_papers),
            "questions_found": len(question_records),
            "repeated_groups": sum(1 for group in public_groups if group["repeat_count"] > 1),
            "confidence": analysis_confidence(public_groups, valid_papers),
            "total_study_hours": days * hours_per_day,
        },
        "valid_papers": valid_papers,
        "rejected_files": rejected_files,
        "question_groups": public_groups,
        "sections": {
            "most_important": [group["question"] for group in public_groups if group["category"] == "Most Important"],
            "important": [group["question"] for group in public_groups if group["category"] == "Important"],
            "extra": [group["question"] for group in public_groups if group["category"] == "Extra"],
        },
        "study_planner": build_study_planner(public_groups, days, hours_per_day),
        "charts": {
            "repeated": {
                "labels": [group["question"][:28] + ("..." if len(group["question"]) > 28 else "") for group in top_repeated],
                "values": [group["repeat_count"] for group in top_repeated],
            },
            "importance": {
                "labels": ["Most Important", "Important", "Extra"],
                "values": [section_counter["Most Important"], section_counter["Important"], section_counter["Extra"]],
            },
        },
    }


@app.route("/")
def home():
    return render_template_string(HTML_PAGE)


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    global latest_analysis

    files = request.files.getlist("papers")
    if not files:
        return jsonify({"error": "At least one English past paper upload karo."}), 400

    try:
        days = max(1, min(int(request.form.get("days", 7)), 45))
        hours_per_day = max(1, min(int(request.form.get("hours", 2)), 10))
    except ValueError:
        return jsonify({"error": "Study days/hours valid number hone chahiye."}), 400

    try:
        latest_analysis = analyze_papers(files, days, hours_per_day)
        return jsonify(latest_analysis)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        if PyPDF2 is not None and isinstance(error, PyPDF2.errors.PdfReadError):
            return jsonify({"error": "Uploaded PDF invalid ya unreadable hai."}), 400
        return jsonify({"error": f"Analysis failed: {str(error)}"}), 500


@app.route("/api/results", methods=["GET"])
def api_results():
    if not latest_analysis:
        return jsonify({"error": "No analysis available yet."}), 404
    return jsonify(latest_analysis)


@app.route("/api/export", methods=["GET"])
def api_export():
    if not latest_analysis:
        return jsonify({"error": "No analysis available yet."}), 404
    return app.response_class(
        response=json.dumps(latest_analysis, indent=2),
        status=200,
        mimetype="application/json",
    )


if __name__ == "__main__":
    app.run(debug=True)
