from django.urls import path
from .views import home,upload_sop,chatbot_page,sop_chatbot

urlpatterns = [
    path("", home, name="home"),  # ✅ Add homepage URL
     path("upload/", upload_sop, name="upload_sop"),  # ✅ Add SOP Upload URL
     path("chatbot/", chatbot_page, name="chatbot_page"),
     path("api/chatbot/", sop_chatbot, name="sop_chatbot"),
]
