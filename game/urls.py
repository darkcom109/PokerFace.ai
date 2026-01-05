from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("play/", views.play, name="play"),
    path("play/new/", views.new_hand, name="new_hand"),
    path("play/action/<str:move>/", views.player_action, name="player_action"),
    path("collect/", views.collect_chips, name="collect_chips"),
    path("ai-tip/", views.ai_tip, name="ai_tip"),
]
