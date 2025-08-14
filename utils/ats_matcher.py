import json, re, pdfplumber
import cohere
from difflib import get_close_matches
import language_tool_python

co = cohere.Client("DmwRfZ1o5H61fkeHb715yul3iOJoB4m0ICyFS6DM")

def extract_text_from_pdf(filepath):
    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def clean_text(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return text

def load_skills():
    with open("utils/skills_list.json") as f:
        return set(json.load(f))

def extract_skills(text, skill_list):
    words = text.split()
    found = []
    for skill in skill_list:
        norm = skill.lower().replace(" ", "")
        if norm in words or get_close_matches(norm, words, n=1, cutoff=0.9):
            found.append(skill)
    return list(set(found))

def check_grammar(text):
    tool = language_tool_python.LanguageTool('en-US')
    matches = tool.check(text)
    return [{
        "text": text[match.offset:match.offset + match.errorLength],
        "message": match.message,
        "suggestions": match.replacements
    } for match in matches]

def analyze_resume_from_pdf(pdf_path, jd):
    text = extract_text_from_pdf(pdf_path)
    skills = load_skills()
    resume_skills = extract_skills(clean_text(text), skills)
    jd_skills = extract_skills(clean_text(jd), skills)

    matched = set(resume_skills) & set(jd_skills)
    missing = list(set(jd_skills) - set(resume_skills))

    suggestions = {
        skill: f"https://www.google.com/search?q=learn+{skill.replace(' ', '+')}"
        for skill in missing
    }

    score = round(len(matched) / len(jd_skills) * 100, 2) if jd_skills else 0
    return {
        "score": score,
        "matched_skills": list(matched),
        "missing_skills": suggestions,
        "grammar_issues": check_grammar(text),
        "ai_suggestions": get_resume_suggestions(text)
    }

def get_resume_suggestions(text):
    response = co.chat(message=f"Suggest 4–5 improvements for this resume:\n{text}", model="command-r", temperature=0.7)
    return response.text.strip()

def detect_job_role_from_text(text):
    response = co.chat(message=f"What job role best fits this resume? Just give the role title:\n{text}", model="command-r", temperature=0.5)
    return response.text.strip().lower()

def extract_resume_data_for_template(text):
    data = {
        "name": "",
        "email": "",
        "phone": "",
        "skills": [],
        "education": "",
        "experience": ""
    }
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    phone_match = re.search(r"\+?\d[\d\s\-\(\)]{8,}", text)
    name_match = re.findall(r"(?<=\n)[A-Z][a-z]+\s[A-Z][a-z]+", text)

    if name_match: data["name"] = name_match[0]
    if email_match: data["email"] = email_match.group()
    if phone_match: data["phone"] = phone_match.group()
    data["skills"] = list(set(re.findall(r"\b[a-zA-Z]{3,}\b", text)))

    return data

def generate_ai_html_template(role, data):
    prompt = f"""You are an expert resume designer. Create a complete modern HTML resume template for the job role: {role}.
Use the following user info:

Name: {data.get('name', '')}
Email: {data.get('email', '')}
Phone: {data.get('phone', '')}
Skills: {', '.join(data.get('skills', []))}
Education: {data.get('education', '')}
Experience: {data.get('experience', '')}

Return only complete HTML content starting with <!DOCTYPE html>.
"""
    response = co.chat(message=prompt, model="command-r", temperature=0.8)
    return response.text.strip()
