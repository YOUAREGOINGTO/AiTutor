# api/urls.py
from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('chat/', views.plain_django_chat_view, name='plain_chat_api'),
    path('sessions/', views.list_chat_sessions_async, name='list_chat_sessions'),
    path('session/<str:session_id_str>/', views.get_session_details_async, name='get_session_details'), # GET
    path('session/<str:session_id_str>/update_title/', views.update_session_title_async, name='update_session_title'), # PATCH (using separate sub-path)
    path('session/<str:session_id_str>/delete/', views.delete_session_async, name='delete_session'),
    path('upload_temp_resource/', views.upload_temp_resource_view, name='upload_temp_resource'),

]