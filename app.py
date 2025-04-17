import streamlit as st
import pypdf  # Using PyPDF instead of Fitz
import ollama  # Using local Gemma via Ollama
from typing import TypedDict, List, Dict, Any, Optional
import langgraph as lg
import json
from langgraph.graph import StateGraph
from langchain_ollama.embeddings import OllamaEmbeddings


# ---- STATE CLASS ---- #
class State(TypedDict):
    resume_pdf_path: Optional[str]
    resume_text: Optional[str]
    parsed_data: Dict[str, Any]
    resume_embedding: Optional[List[float]]
    processing_stage: str
    errors: List[str]
    matched_skills: List[str]
    missing_skills: List[str]
    recommended_courses: List[Dict[str, Any]]


# Initialize empty state
def get_initial_state() -> State:
    return {
        "resume_pdf_path": None,
        "resume_text": None,
        "parsed_data": {},
        "resume_embedding": None,
        "processing_stage": "initialized",
        "errors": [],
        "matched_skills": [],
        "missing_skills": [],
        "recommended_courses": [],
    }


# ---- RESUME PROCESSING ---- #
def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            text = "\n".join(
                [page.extract_text() for page in reader.pages if page.extract_text()]
            )
        return text
    except Exception as e:
        return ""


# ---- EMBEDDING GENERATION ---- #
def get_embeddings(text: str) -> List[float]:
    if not text.strip():
        print("No text found for embedding.")
        return []

    embed = OllamaEmbeddings(model="llama3.2:1b")
    response = embed.embed_query(text)
    print("Embedding response:", response)
    return response[0] if response else []


# ---- MATCHING SKILLS ---- #
def find_missing_skills(
    parsed_data: Dict[str, Any], skill_database: List[str]
) -> (List[str], List[str]):
    extracted_skills = parsed_data.get("skills", [])
    matched = list(set(extracted_skills) & set(skill_database))
    missing = list(set(skill_database) - set(extracted_skills))
    return matched, missing


def extract_skills(text: str) -> List[str]:
    skills = [
        "Python",
        "Machine Learning",
        "Data Science",
        "SQL",
        "AWS",
    ]  # Expand this list
    extracted = [skill for skill in skills if skill.lower() in text.lower()]
    print("Extracted Skills:", extracted)
    return extracted


# ---- TRAINING RECOMMENDATIONS ---- #
def recommend_training(
    missing_skills: List[str], course_database: Dict[str, str]
) -> List[Dict[str, Any]]:
    recommendations = [
        {"skill": skill, "course": course_database.get(skill, "No course found")}
        for skill in missing_skills
    ]
    return recommendations


# ---- LANGGRAPH WORKFLOW ---- #
def process_resume(state: State) -> State:
    if state["resume_pdf_path"]:
        state["resume_text"] = extract_text_from_pdf(state["resume_pdf_path"])
        state["parsed_data"]["skills"] = extract_skills(state["resume_text"])
        state["processing_stage"] = "text_extracted"
    return state


def generate_embeddings(state: State) -> State:
    if state["resume_text"]:
        state["resume_embedding"] = get_embeddings(state["resume_text"])
        state["processing_stage"] = "embedding_generated"
    return state


def match_skills(state: State) -> State:
    skill_database = ["Python", "Machine Learning", "Data Science", "SQL", "AWS"]
    matched, missing = find_missing_skills(state["parsed_data"], skill_database)
    state["matched_skills"] = matched
    state["missing_skills"] = missing
    state["processing_stage"] = "skills_matched"
    return state


def recommend_courses(state: State) -> State:
    course_database = {
        "Machine Learning": "Machine Learning Specialization - Coursera",
        "Data Science": "Data Science Bootcamp - Udemy",
        "SQL": "SQL for Data Analysis - DataCamp",
        "AWS": "AWS IBb - DataCamp",
    }
    state["recommended_courses"] = recommend_training(
        state["missing_skills"], course_database
    )
    state["processing_stage"] = "recommendations_ready"
    return state


# ---- BUILD LANGGRAPH ---- #
graph = StateGraph(State)
graph.add_node("process_resume", process_resume)
graph.add_node("generate_embeddings", generate_embeddings)
graph.add_node("match_skills", match_skills)
graph.add_node("recommend_courses", recommend_courses)
graph.add_edge("process_resume", "generate_embeddings")
graph.add_edge("generate_embeddings", "match_skills")
graph.add_edge("match_skills", "recommend_courses")
graph.set_entry_point("process_resume")
executor = graph.compile()

# ---- STREAMLIT UI ---- #
st.title("Learning & Development AI Agent")
sidebar = st.sidebar
sidebar.title("Workflow Diagram")
with sidebar:
    executor.get_graph(xray=True).draw_mermaid_png(output_file_path="graph.png")
    sidebar.image("graph.png")
# Display graph in sidebar

uploaded_file = st.file_uploader("Upload Employee Resume (PDF)", type=["pdf"])
if uploaded_file:
    with open("temp_resume.pdf", "wb") as f:
        f.write(uploaded_file.read())

    state = get_initial_state()
    state["resume_pdf_path"] = "temp_resume.pdf"
    state = executor.invoke(state)

    st.subheader("Extracted Skills")
    st.write(state["matched_skills"])

    st.subheader("Missing Skills")
    st.write(state["missing_skills"])

    st.subheader("Recommended Training Programs")
    for rec in state["recommended_courses"]:
        st.write(f"**{rec['skill']}**: {rec['course']}")
