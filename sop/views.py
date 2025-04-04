from django.shortcuts import render
from .models import SOPInteraction  # Import the model

import os
import openai

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai_client = openai.Client(api_key=OPENAI_API_KEY)

#create home page
def home(request):
    """Render homepage."""
    return render(request, "sop/home.html")

#create the upload view

from django.shortcuts import render, redirect
from .forms import SOPUploadForm
from .models import SOPDocument
#find relevant sop

def find_relevant_sop(user_message):
    """Search for the SOP document that best matches the user's query."""
    sop_documents = SOPDocument.objects.all()
    if not sop_documents:
        return None

    # ✅ Step 1: Check for direct matches in SOP titles
    for sop in sop_documents:
        if sop.title.lower() in user_message.lower():
            return sop  # ✅ Direct match found

    # ✅ Step 2: Use GPT to find the best SOP match
    sop_titles = [sop.title for sop in sop_documents]
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": f"User asked: {user_message}. Select the most relevant SOP title from this list: {sop_titles}"},
            {"role": "user", "content": "Pick the best SOP for the question."}
        ]
    )
    
    best_sop_title = response.choices[0].message.content.strip()
    
    for sop in sop_documents:
        if best_sop_title.lower() == sop.title.lower():
            return sop  # ✅ GPT-selected best match
    
    return None  # No relevant SOP found

#extract text from pdf
def extract_text_from_pdf(file_path):
    """Extracts text from a PDF file"""
    text = ""
    try:
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
    
    return text.strip()  # ✅ Return cleaned text



#sop sop chatbots
def upload_sop(request):
    """Handles SOP document uploads"""
    if request.method == "POST":
        form = SOPUploadForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("home")  # Redirect to home after upload
    else:
        form = SOPUploadForm()

    return render(request, "sop/upload_sop.html", {"form": form})

#define the chatbot view
def chatbot_page(request):
    """Renders the chatbot interface"""
    return render(request, "sop/chatbot.html")

#implemnt AI chatbot

import json
import os
import fitz  # PyMuPDF for extracting text from PDFs
import openai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import SOPDocument
from dotenv import load_dotenv

load_dotenv()  # Load environment variables

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
#Helper function to refine the search and make it more intelligent
import re

def extract_keywords(query):
    """Extracts important words from user query using regex"""
    query = query.lower()
    keywords = re.findall(r'\b\w{4,}\b', query)  # Finds words with 4+ letters
    return keywords

def search_sop(keywords):
    """Finds SOPs that contain relevant keywords by extracting text from PDFs"""
    matching_sops = []
    
    for sop in SOPDocument.objects.all():
        sop_text = extract_text_from_pdf(sop.document.path).lower()  # ✅ Extract text from the PDF

        for keyword in keywords:
            if keyword in sop_text:
                matching_sops.append(sop)
                break  # ✅ Stop searching once a match is found

    return matching_sops


#end of helper function
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import openai
import os
import fitz  # PyMuPDF for PDF extraction
from sentence_transformers import SentenceTransformer, util
from .models import SOPDocument
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI Client
openai_client = openai.Client(api_key=OPENAI_API_KEY)

# Load embedding model for semantic search
model = SentenceTransformer("all-MiniLM-L6-v2")

def clean_text(text):
    """Removes unwanted characters and formatting from extracted text."""
    text = re.sub(r"#", "", text)  # Remove `#` symbols
    text = re.sub(r"\n{2,}", "\n", text)  # Replace multiple newlines with a single newline
    text = text.strip()  # Remove extra spaces
    return text

def extract_text_from_pdf(file_path):
    """Extracts and cleans text from a PDF file."""
    text = ""
    try:
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text() + "\n"
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")

    return clean_text(text)  # ✅ Clean the extracted text before returning

def find_most_relevant_sop_section(user_message):
    """Finds the most relevant SOP section using semantic search."""
    sop_texts = []
    sop_files = SOPDocument.objects.all()

    for sop in sop_files:
        extracted_text = extract_text_from_pdf(sop.document.path)
        sop_texts.append({"title": sop.title, "content": extracted_text})

    if not sop_texts:
        return None  # No SOPs available

    # Embed user query and all SOP contents
    query_embedding = model.encode(user_message, convert_to_tensor=True)
    sop_embeddings = [model.encode(sop["content"], convert_to_tensor=True) for sop in sop_texts]

    # Find the SOP with the highest similarity score
    best_match_index = max(range(len(sop_embeddings)), key=lambda i: util.pytorch_cos_sim(query_embedding, sop_embeddings[i])[0][0])

    return sop_texts[best_match_index]["content"]  # Return cleaned SOP content

#checks if we have a previous response
from django.db.models import Q
from difflib import SequenceMatcher  # For similarity checking

def get_previous_response(user_message):
    """Check if a similar question has been asked before."""
    interactions = SOPInteraction.objects.all()
    
    for interaction in interactions:
        similarity = SequenceMatcher(None, user_message.lower(), interaction.user_query.lower()).ratio()
        if similarity > 0.8:  # 80% similarity threshold
            return interaction.ai_response  # Return stored response
    
    return None  # No similar question found

#end of the check

@csrf_exempt
@login_required
@csrf_exempt
def sop_chatbot(request):
    """Handles Chat Requests & Uses OpenAI to Answer Based on the Most Relevant SOP"""
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            user_message = data.get("message", "").strip()
            is_voice = data.get("is_voice", False)  # Detect if the user is speaking

            if not user_message:
                return JsonResponse({"error": "Message is required"}, status=400)

            # ✅ Check if we already have an answer for this query
            previous_response = get_previous_response(user_message)
            if previous_response:
                return JsonResponse({"response": previous_response, "is_voice": is_voice})

            # ✅ Find the most relevant SOP
            relevant_sop = find_relevant_sop(user_message)
            if not relevant_sop:
                return JsonResponse({"error": "No relevant SOP found for this query."}, status=400)

            # ✅ Extract text from SOP
            sop_text = extract_text_from_pdf(relevant_sop.document.path)

            # ✅ Use OpenAI to generate a response
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"Use this SOP to answer the question:\n{sop_text}"},
                    {"role": "user", "content": user_message}
                ]
            )

            ai_response = response.choices[0].message.content.strip()

            # ✅ Save interaction for future learning
            SOPInteraction.objects.create(user_query=user_message, sop_used=relevant_sop, ai_response=ai_response)

            return JsonResponse({"response": ai_response, "is_voice": is_voice})

        except Exception as e:
            return JsonResponse({"error": f"Internal Server Error: {str(e)}"}, status=500)

#Allows users to rate the BOTs
@csrf_exempt
def feedback(request):
    """Stores user feedback on chatbot responses."""
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        query = data.get("query", "").strip()
        rating = data.get("rating")

        if not query or not rating:
            return JsonResponse({"error": "Query and rating are required"}, status=400)

        try:
            interaction = SOPInteraction.objects.filter(user_query=query).first()
            if interaction:
                interaction.feedback = rating
                interaction.save()
                return JsonResponse({"message": "Feedback recorded successfully"})
            else:
                return JsonResponse({"error": "No matching query found"}, status=400)

        except Exception as e:
            return JsonResponse({"error": f"Internal Server Error: {str(e)}"}, status=500)

#end of feedback


#allows only admin to upload SOP
from django.contrib.auth.decorators import login_required, user_passes_test

def is_admin(user):
    return user.is_authenticated and user.is_admin  # ✅ Admin check

@login_required
@user_passes_test(is_admin, login_url="home")  # ✅ Restrict SOP upload to admins
def upload_sop(request):
    if request.method == "POST":
        form = SOPUploadForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("home")
    else:
        form = SOPUploadForm()
    return render(request, "sop/upload_sop.html", {"form": form})

@login_required
def chatbot_page(request):
    return render(request, "sop/chatbot.html")


#adds sign up , login view

from django.contrib.auth import login, authenticate, logout
from django.shortcuts import render, redirect
from .forms import SignupForm, LoginForm

def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # ✅ Auto-login after signup
            return redirect("home")  # ✅ Redirect to homepage
    else:
        form = SignupForm()
    return render(request, "sop/signup.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("home")  # ✅ Redirect to homepage
    else:
        form = LoginForm()
    return render(request, "sop/login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("home")  # ✅ Redirect to homepage after logout

#Analytics Dashboad for Admin
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Count
from django.http import HttpResponseForbidden
from .models import SOPAnalytics

#@staff_member_required  # Restricts access to admin users
@login_required
@user_passes_test(is_admin)  # ✅ Only allow admin users

def analytics_dashboard(request):
    total_queries = SOPAnalytics.objects.count()
    avg_response_time = SOPAnalytics.objects.aggregate(avg_time=Avg("response_time"))["avg_time"] or 0  # Handle None
    top_queries = (
        SOPAnalytics.objects.values("query")
        .annotate(count=Count("query"))
        .order_by("-count")[:5]
    )

    return render(request, "sop/analytics_dashboard.html", {
        "total_queries": total_queries,
        "avg_response_time": round(avg_response_time, 2),  # Round for better display
        "top_queries": top_queries,
    })

