from django.shortcuts import render

def index(request):
    return render(request,'index.html')

def options(request):
    return render(request,'options.html')

def jobs(request):
    return render(request,'jobs.html')

def user_job_description(request):
    return render(request,'user_job_description.html')

def resume_builder(request):
    return render(request,'resume_builder.html')