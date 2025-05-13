from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from app.views import (
    home, signup, upload_resume, analyze_job_match, analyze_resume,
    get_resume_suggestions, dashboard, resume_improvements, fetch_jobs
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', home, name='home'),
    path('signup/', signup, name='signup'),
    path('dashboard/', dashboard, name='dashboard'),
    path('upload-resume/', upload_resume, name='upload_resume'),
    path('analyze-job-match/<int:job_id>/', analyze_job_match, name='analyze_job_match'),
    path('analyze-resume/', analyze_resume, name='analyze_resume'),
    path('get-resume-suggestions/', get_resume_suggestions, name='get_resume_suggestions'),
    path('resume-improvements/<int:job_id>/', resume_improvements, name='resume_improvements'),
    path('fetch-jobs/<int:resume_id>/', fetch_jobs, name='fetch_jobs'),
    path("__reload__/", include("django_browser_reload.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)