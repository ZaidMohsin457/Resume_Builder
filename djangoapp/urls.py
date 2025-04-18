from django.urls import path
from . import views

urlpatterns = [
    path('',views.index,name='index'),
    path('options/',views.options,name='options'),
    path('options/jobs/',views.jobs,name='jobs'),
    path('options/user_job_description/',views.user_job_description,name='user_job_description'),
    path('resume_builder/<int:analysis_id>/',views.resume_builder,name='resume_builder'),
]
