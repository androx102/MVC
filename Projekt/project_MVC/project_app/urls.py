from django.urls import path

from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('', views.task_list, name='task_list'),
    path('board/', views.task_board, name='task_board'),
    path('tasks/new/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/', views.task_detail, name='task_detail'),
    path('tasks/<int:pk>/edit/', views.task_update, name='task_update'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),
    path('projects/', views.project_list, name='project_list'),
    path('projects/new/', views.project_create, name='project_create'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/<int:pk>/edit/', views.project_update, name='project_update'),
    path('teams/', views.team_list, name='team_list'),
    path('teams/new/', views.team_create, name='team_create'),
    path('teams/<int:pk>/', views.team_detail, name='team_detail'),
    path('teams/<int:pk>/edit/', views.team_update, name='team_update'),
    path('teams/<int:pk>/members/add/', views.team_member_add, name='team_member_add'),
    path('teams/<int:pk>/members/<int:membership_id>/remove/', views.team_member_remove, name='team_member_remove'),
    path('teams/<int:pk>/members/<int:membership_id>/role/', views.team_member_role, name='team_member_role'),
]
