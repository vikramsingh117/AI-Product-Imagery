# Product Image Extractor

AI-powered tool to extract the best product frame from a YouTube video, and optionally generate an enhanced product shot.

## Features

- Extract frames from YouTube videos at regular intervals
- Use Gemini to detect products and select the best frame for each product
- Clean, modern React/Next.js frontend
- Flask backend

## Setup

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure API key (used by both analysis and generation):
```bash
export GEMINI_API_KEY=your_api_key_here
```

5. Run the Flask server:
```bash
python app.py
```

Backend: `http://localhost:5000`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

The frontend will run on `http://localhost:3000`

## Usage

1. Start both backend and frontend servers
2. Open `http://localhost:3000` in your browser
3. Paste a YouTube video URL (product review, unboxing, or demo)
4. Click "Extract Product Images"
5. Wait for processing (may take 1-2 minutes)
6. View the detected products and their best frames

## API Endpoints

### POST /api/process-video
Process a YouTube video and extract best product frames.

**Request:**
```json
{
  "url": "https://www.youtube.com/watch?v=..."
}
```

**Response:**
```json
{
  "success": true,
  "total_frames_analyzed": 30,
  "products": [
    {
      "name": "Product Name",
      "best_frame": {
        "frame_number": 150,
        "timestamp": 5.0,
        "quality_score": 9,
        "image_base64": "..."
      }
    }
  ]
}
```

## Tech Stack

- **Backend**: Flask, Python
- **Frontend**: Next.js, React, TypeScript, Tailwind CSS
- **AI**:
  - Analysis: Gemini Flash (vision) via `google-generativeai`
  - Enhancement: Imagen 4 text-to-image via `google-genai` (optional)
- **Video Processing**: yt-dlp, OpenCV
- **Image Processing**: Pillow

## Configuration

- Env var: `GEMINI_API_KEY` (required)
- Models used:
  - Analysis model: `gemini-2.0-flash-lite` (prompt+image scoring)
  - Enhancement model: `imagen-4.0-generate-001` (text-to-image, optional)
- Enhanced images saved to: `backend/enhanced_images/`

## Install notes

Backend venv:
```bash
cd backend
./venv/bin/pip install -r requirements.txt
```

If you want enhancement:
```bash
./venv/bin/pip install google-genai
```

