from django.shortcuts import render

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

@csrf_exempt
def sop_chatbot(request):
    """Handles Chat Requests & Uses OpenAI to Answer Based on the Most Relevant SOP"""
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            user_message = data.get("message", "").strip()

            if not user_message:
                return JsonResponse({"error": "Message is required"}, status=400)

            if not OPENAI_API_KEY:
                return JsonResponse({"error": "OpenAI API key is missing"}, status=500)

            # ✅ Find the most relevant SOP document
            relevant_sop = find_relevant_sop(user_message)
            if not relevant_sop:
                return JsonResponse({"error": "No relevant SOP found for this query."}, status=400)

            # ✅ Extract text from the relevant SOP
            sop_text = extract_text_from_pdf(relevant_sop.document.path)

            # ✅ Use OpenAI's New ChatCompletion API
            client = openai.OpenAI(api_key=OPENAI_API_KEY)

            response = client.chat.completions.create(
                model="gpt-4",
                #model="gpt-3.5-turbo",  # Switched to gpt-3.5-turbo
                messages=[
                    {"role": "system", "content": f"Use this SOP to answer the question:\n{sop_text}"},
                    {"role": "user", "content": user_message}
                ]
            )

            return JsonResponse({"response": response.choices[0].message.content})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except openai.AuthenticationError:
            return JsonResponse({"error": "Invalid OpenAI API key"}, status=401)
        except openai.OpenAIError as e:
            return JsonResponse({"error": f"OpenAI API Error: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({"error": f"Internal Server Error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)
