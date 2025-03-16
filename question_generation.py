from PyPDF2 import PdfReader
import chromadb
import ollama

def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    return text

study_pdf_path = input("Enter Study Material PDF path: ").strip()
prev_paper_pdf_path = input("Enter Previous Question Paper PDF path: ").strip()

study_text = extract_text_from_pdf(study_pdf_path)
prev_text = extract_text_from_pdf(prev_paper_pdf_path)

chroma_client = chromadb.PersistentClient(path="./db")
try:
    chroma_client.delete_collection("exam_data")
except Exception:
    pass
collection = chroma_client.get_or_create_collection("exam_data")
collection.add(ids=["study_material"], documents=[study_text])
collection.add(ids=["previous_questions"], documents=[prev_text])


model = "mistral"
prompt = (
    "You are an expert in university-level exam question creation. "
    "Generate a new question paper that strictly follows the exact same structure, formatting, sections, and difficulty of the previous question paper. "
    "Replace the old questions with new ones derived from the study material, but do not change the numbering, section names, or formatting.\n\n"

    "### **Previous Exam Paper Format (Follow this exactly):**\n"
    f"{prev_text[:4000]}\n\n"

    "### **Study Material (Use this for new questions):**\n"
    f"{study_text[:4000]}\n\n"

    "🔹 **Rules for generation:**\n"
    "1. Maintain the same number of sections and questions.\n"
    "2 .Keep the same numbering, marks, and instructions.\n"
    "3 .Ensure difficulty matches the previous exam.\n"
    "4. Generate new questions from the study material.\n\n"

    "### **Generated Question Paper:**\n"
)

response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])

questions = response['message']['content']
print("\n✅ Generated Question Paper:\n", questions)

with open("generated_question_paper.txt", "w") as f:
    f.write(questions)

print("\n✅ Question paper successfully generated and saved as 'generated_question_paper.txt'.")
