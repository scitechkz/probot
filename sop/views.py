import os
import json
import re
from difflib import SequenceMatcher

import fitz  # PyMuPDF
import openai
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, util

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt

from .forms import SOPUploadForm, SignupForm, LoginForm
from .models import SOPDocument, SOPInteraction

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = openai.Client(api_key=OPENAI_API_KEY)
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


# ========== BASIC VIEWS ==========

def home(request):
    return render(request, "sop/home.html")

@login_required
def chatbot_page(request):
    return render(request, "sop/chatbot.html")


# ========== AUTH VIEWS ==========

def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = SignupForm()
    return render(request, "sop/signup.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request, 
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"]
            )
            if user:
                login(request, user)
                return redirect("home")
    else:
        form = LoginForm()
    return render(request, "sop/login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("home")


# ========== SOP UPLOAD ==========

def is_admin(user):
    return user.is_authenticated and user.is_admin

@login_required
@user_passes_test(is_admin, login_url="home")
def upload_sop(request):
    if request.method == "POST":
        form = SOPUploadForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("home")
    else:
        form = SOPUploadForm()
    return render(request, "sop/upload_sop.html", {"form": form})


# ========== TEXT & SEARCH HELPERS ==========

def clean_text(text):
    text = re.sub(r"#", "", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()

def extract_text_from_pdf(file_path):
    text = ""
    try:
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text() + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return clean_text(text)

def extract_keywords(query):
    return re.findall(r'\b\w{4,}\b', query.lower())

def get_previous_response(user_message):
    for interaction in SOPInteraction.objects.all():
        similarity = SequenceMatcher(None, user_message.lower(), interaction.user_query.lower()).ratio()
        if similarity > 0.8:
            return interaction.ai_response
    return None

def find_relevant_sop(user_message):
    sop_documents = SOPDocument.objects.all()
    if not sop_documents:
        return None

    # Use embeddings to find the most relevant document based on the content
    sop_texts = [
        {"title": sop.title, "content": extract_text_from_pdf(sop.document.path), "id": sop.id}
        for sop in sop_documents
    ]

    query_embedding = embedding_model.encode(user_message, convert_to_tensor=True)
    sop_embeddings = [embedding_model.encode(sop["content"], convert_to_tensor=True) for sop in sop_texts]

    # Find the best matching document using cosine similarity
    best_index = max(range(len(sop_embeddings)), key=lambda i: util.pytorch_cos_sim(query_embedding, sop_embeddings[i])[0][0])
    
    best_sop = sop_texts[best_index]
    return SOPDocument.objects.get(id=best_sop["id"])

def find_most_relevant_sop_section(user_message):
    sop_documents = SOPDocument.objects.all()
    if not sop_documents:
        return None

    sop_texts = [
        {"title": sop.title, "content": extract_text_from_pdf(sop.document.path), "id": sop.id}
        for sop in sop_documents
    ]

    query_embedding = embedding_model.encode(user_message, convert_to_tensor=True)
    sop_embeddings = [embedding_model.encode(sop["content"], convert_to_tensor=True) for sop in sop_texts]

    best_index = max(range(len(sop_embeddings)), key=lambda i: util.pytorch_cos_sim(query_embedding, sop_embeddings[i])[0][0])
    
    best_sop = sop_texts[best_index]
    sop_content = best_sop["content"]

    # Extract a relevant snippet from the document content for the response
    snippet = sop_content[:500]  # Adjust the length of the snippet as needed
    return snippet


# ========== CHATBOT VIEW ==========

@csrf_exempt
@login_required
def sop_chatbot(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            user_message = data.get("message", "").strip()
            is_voice = data.get("is_voice", False)

            if not user_message:
                return JsonResponse({"error": "Message is required"}, status=400)

            previous_response = get_previous_response(user_message)
            if previous_response:
                return JsonResponse({"response": previous_response, "is_voice": is_voice})

            relevant_sop = find_relevant_sop(user_message)
            if not relevant_sop:
                response_message = "No relevant SOP found."
            else:
                sop_text = find_most_relevant_sop_section(user_message)

                # Query GPT with the SOP content
                response = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": f"Use this SOP to answer the question:\n{sop_text}"},
                              {"role": "user", "content": user_message}]
                )

                ai_response = response.choices[0].message.content.strip()
                SOPInteraction.objects.create(
                    user_query=user_message,
                    sop_used=relevant_sop,
                    ai_response=ai_response
                )

                response_message = ai_response

            # Return the response
            return JsonResponse({"response": response_message, "is_voice": is_voice})

        except Exception as e:
            return JsonResponse({"error": f"Server Error: {str(e)}"}, status=500)


# ========== FEEDBACK VIEW ==========

@csrf_exempt
def feedback(request):
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        query = data.get("query", "").strip()
        rating = data.get("rating")

        if not query or not rating:
            return JsonResponse({"error": "Query and rating required."}, status=400)

        try:
            interaction = SOPInteraction.objects.filter(user_query=query).first()
            if interaction:
                interaction.feedback = rating
                interaction.save()
                return JsonResponse({"message": "Feedback saved."})
            else:
                return JsonResponse({"error": "No matching query found."}, status=400)

        except Exception as e:
            return JsonResponse({"error": f"Server Error: {str(e)}"}, status=500)

from django.shortcuts import render

# Make sure this view exists in views.py
def analytics_dashboard(request):
    # Your logic here
    return render(request, 'analytics_dashboard.html')
