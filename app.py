from flask import Flask, render_template, request, session, send_file, redirect, url_for
import os
from utils.ats_matcher import (
    extract_text_from_pdf,
    analyze_resume_from_pdf,
    detect_job_role_from_text,
    generate_ai_html_template,
    extract_resume_data_for_template
)

app = Flask(__name__)
app.secret_key = "supersecretkey"
UPLOAD_FOLDER = "static"
TEMPLATE_FOLDER = "templates/generated"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    ai_template_filename = None

    if request.method == "POST":
        resume = request.files["resume_file"]
        jd = request.form.get("job_desc")

        if resume:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], resume.filename)
            resume.save(filepath)

            resume_text = extract_text_from_pdf(filepath)
            result = analyze_resume_from_pdf(filepath, jd)

            role = detect_job_role_from_text(resume_text)
            data = extract_resume_data_for_template(resume_text)

            # Generate AI HTML template
            ai_template_html = generate_ai_html_template(role, data)

            # Save the generated HTML
            ai_template_filename = f"ai_resume_{role.replace(' ', '_')}.html"
            template_path = os.path.join(TEMPLATE_FOLDER, ai_template_filename)
            with open(template_path, "w", encoding="utf-8") as f:
                f.write(ai_template_html)

            # Save info to session
            session["template_path"] = template_path
            session["template_filename"] = ai_template_filename
            session["generated_html"] = ai_template_html
            session["role"] = role
            result["template_recommendation"] = f"🔮 AI-generated template based on role: {role.title()}"

    return render_template("index.html", result=result)


@app.route("/preview")
def preview():
    html = session.get("generated_html")
    if not html:
        return "No template generated. Please upload a resume first.", 400
    return html


@app.route("/download")
def download():
    template_path = session.get("template_path")
    if not template_path or not os.path.exists(template_path):
        return "Template not available for download.", 404
    return send_file(template_path, as_attachment=True)


if __name__ == "__main__":
    os.makedirs(TEMPLATE_FOLDER, exist_ok=True)
    app.run(debug=True)
