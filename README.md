# LinkedIn Job Recommender 🎯

A smart job recommendation system that helps match your resume with relevant job opportunities using AI-powered analysis.

## 🌟 Features

- Resume analysis and skill extraction
- Intelligent job matching using JSearch API
- RESTful API with FastAPI
- Structured logging and error handling
- CORS support for frontend integration

## 🚀 Quick Start

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Add your RapidAPI key for JSearch API
   
5. Run the application:
   ```bash
   python -m app.main
   ```

## 📁 Project Structure

```
linkedin-job-recommender/
├── app/
│   ├── api/          # API routes and endpoints
│   ├── config/       # Configuration settings
│   ├── core/         # Core business logic
│   ├── models/       # Data models and schemas
│   ├── services/     # External services integration
│   └── utils/        # Utility functions
├── data/
│   ├── resumes/      # Storage for uploaded resumes
│   └── jobs/         # Cached job data
└── requirements.txt  # Project dependencies
```

## 🔗 API Endpoints

- `GET /`: Root endpoint with API information
- `GET /ping`: Health check endpoint
- `GET /api/health`: Detailed health status
- `POST /api/analyze-resume`: Upload and analyze resume
- `GET /api/jobs`: Get job recommendations

## 🛠️ Technologies

- Python 3.8+
- FastAPI
- JSearch API
- Logging
- CORS middleware

## 📝 License

MIT License

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 