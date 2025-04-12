from django.urls import path
from .views import home,upload_sop,chatbot_page,sop_chatbot
from .views import signup_view, login_view, logout_view, home, upload_sop, chatbot_page, sop_chatbot
from .views import analytics_dashboard


urlpatterns = [
    path("", home, name="home"),  # ✅ Add homepage URL
     path("upload/", upload_sop, name="upload_sop"),  # ✅ Add SOP Upload URL
     path("chatbot/", chatbot_page, name="chatbot_page"),
     path("api/chatbot/", sop_chatbot, name="sop_chatbot"),
     path("analytics/", analytics_dashboard, name="analytics_dashboard"),
     # ✅ Add these URLs for authentication
    path("signup/", signup_view, name="signup"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
]
