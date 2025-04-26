# api/urls.py
from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('chat/', views.plain_django_chat_view, name='plain_chat_api'),
    path('sessions/', views.list_chat_sessions_async, name='list_chat_sessions'),

    # Modify the session detail path to potentially handle GET, PATCH, DELETE
    # We'll use separate views for clarity here
    path('session/<str:session_id_str>/', views.get_session_details_async, name='get_session_details'), # GET
    path('session/<str:session_id_str>/update_title/', views.update_session_title_async, name='update_session_title'), # PATCH (using separate sub-path)
    path('session/<str:session_id_str>/delete/', views.delete_session_async, name='delete_session'), # DELETE (using separate sub-path)

    # Alternative (less common for function views): a single path dispatching on method inside the view
    # path('session/<str:session_id_str>/', views.session_detail_manager_view, name='manage_session'),
]