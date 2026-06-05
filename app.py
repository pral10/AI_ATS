from flask import Flask, request, jsonify, render_template, send_file
from pypdf import PdfReader
from openai import OpenAI
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
import json

# ---------- LOAD ENV FILE ----------
load_dotenv()

# ---------- INIT APP ----------
app = Flask(__name__)

# ---------- OPENAI CLIENT ----------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------- STORAGE ----------
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

CANDIDATES = []


# ---------- PDF TEXT ----------
def extract_text(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


# ---------- AI ----------
def analyze_resume(resume_text, job_text):

    prompt = f"""
You are an AI hiring manager.

Return JSON only:

{{
  "match_score": number,
  "recommendation": "Hire" | "Maybe" | "No",
  "summary": string,
  "strengths": [string],
  "missing_skills": [string]
}}

RESUME:
{resume_text}

JOB:
{job_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)


# ---------- HOME ----------
@app.route("/")
def home():
    return render_template("index.html")


# ---------- ANALYZE ----------
@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        file = request.files["resume"]
        job = request.form["job"]

        filename = secure_filename(file.filename)
        candidate_name = filename.replace(".pdf", "").replace(" ", "_")

        folder_path = os.path.join(UPLOAD_FOLDER, candidate_name)
        os.makedirs(folder_path, exist_ok=True)

        file_path = os.path.join(folder_path, filename)
        file.save(file_path)

        resume_text = extract_text(file_path)
        result = analyze_resume(resume_text, job)

        record = {
            "name": candidate_name,
            "filename": filename,
            "score": result["match_score"],
            "recommendation": result["recommendation"],
            "summary": result["summary"],
            "file_url": f"/resume/{candidate_name}/{filename}"
        }

        CANDIDATES.insert(0, record)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})


# ---------- HISTORY ----------
@app.route("/history")
def history():
    return jsonify(CANDIDATES)


# ---------- SERVE FILE ----------
@app.route("/resume/<candidate>/<filename>")
def resume(candidate, filename):
    path = os.path.join(UPLOAD_FOLDER, candidate, filename)
    return send_file(path)


# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)