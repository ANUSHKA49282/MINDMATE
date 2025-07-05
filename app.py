import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from fpdf import FPDF
import os
from dotenv import load_dotenv
import re

# Load .env and Gemini key
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("models/gemini-1.5-flash-latest")

# Extract PDF content
def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

# Ask question
def ask_question(content, question):
    prompt = f"""Use the following notes:\n{content}\n\nQuestion: {question}\nAnswer:"""
    response = model.generate_content(prompt)
    return response.text

# Generate quiz
def generate_quiz(content, num_questions):
    prompt = f"""Generate {num_questions} multiple-choice questions from the following notes:\n\n{content}\n\nEach question should have 4 options (A, B, C, D) and clearly mention the correct answer below as 'Answer: A/B/C/D'."""
    response = model.generate_content(prompt)
    return response.text

# Remove emojis for PDF
def remove_unicode(text):
    return re.sub(r'[^\x00-\x7F]+', '', text)

# Save to PDF in current folder
def save_quiz_to_pdf(quiz_text, score_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    clean_text = remove_unicode(quiz_text + "\n\n" + score_text)
    for line in clean_text.split("\n"):
        pdf.cell(200, 10, txt=line, ln=1)
    path = "quiz_result.pdf"
    pdf.output(path)
    return path

# Streamlit UI
st.set_page_config(page_title="Chat & Quiz from PDF", layout="centered")
st.title("MindMate: Your AI-Powered Study Companion")

uploaded_file = st.file_uploader("Upload your PDF", type="pdf")

if uploaded_file:
    content = extract_text_from_pdf(uploaded_file)
    st.success("✅ PDF content loaded!")

    tab1, tab2 = st.tabs(["💬 Ask Questions", "📝 Generate Quiz"])

    # Chat tab
    with tab1:
        st.subheader("Ask something from the notes")
        question = st.text_input("Enter your question:")
        if question:
            answer = ask_question(content, question)
            st.write("**Answer:**", answer)

    # Quiz tab
    with tab2:
        st.subheader("Create a quiz")
        num = st.number_input("Number of questions", min_value=1, max_value=10, step=1)

        if st.button("Generate Quiz"):
            quiz = generate_quiz(content, num)
            st.session_state.quiz = quiz
            st.session_state.answers = []

            # Parse questions and correct answers
            st.session_state.questions = []
            lines = quiz.strip().split("\n")
            block = ""
            for line in lines:
                if line.lower().startswith("answer:"):
                    correct = line.split(":")[1].strip()
                    st.session_state.questions.append((block.strip(), correct))
                    block = ""
                else:
                    block += line + "\n"

        # Display quiz
        if "questions" in st.session_state:
            st.markdown("### 🧠 Answer the Quiz")
            st.session_state.user_answers = []

            for i, (qtext, correct_answer) in enumerate(st.session_state.questions):
                st.markdown(f"**Q{i+1})** {qtext}")  # Show question
                selected = st.radio(
                    label="Choose your answer:",
                    options=["A", "B", "C", "D"],
                    key=f"q_{i}",
                    index=None,
                    label_visibility="collapsed"
                )
                st.session_state.user_answers.append((selected, correct_answer))
                st.markdown("---")

            if st.button("Submit Answers"):
                score = 0
                st.markdown("## ✅ Results")

                for i, (user_ans, correct_ans) in enumerate(st.session_state.user_answers):
                    if user_ans is None:
                        st.warning(f"Q{i+1}) You didn’t answer this question.")
                        continue
                    correct = user_ans.upper() == correct_ans.upper()
                    st.write(
                        f"**Q{i+1})** You chose **{user_ans}** — {'✅ Correct' if correct else f'❌ Wrong (Correct: {correct_ans})'}"
                    )
                    if correct:
                        score += 1

                total = len([ua for ua, _ in st.session_state.user_answers if ua is not None])
                result = f"Your Final Score: {score}/{total}"
                st.success(result)

                file_path = save_quiz_to_pdf(st.session_state.quiz, result)
                with open(file_path, "rb") as f:
                    st.download_button("📥 Download Quiz + Result as PDF", f, file_name="quiz_result.pdf")
