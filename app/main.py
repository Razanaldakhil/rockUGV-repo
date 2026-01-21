"""
RockUGV Border Surveillance System - FastAPI Application
Real-time YOLO object detection with USB camera support

Author: Border Surveillance Team
Date: January 2026
"""

from fastapi import FastAPI, Response, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
import cv2
import numpy as np
from ultralytics import YOLO
from camera import USBCamera
import time
import threading
import os
from datetime import datetime

app = FastAPI(
    title="RockUGV Detection API",
    description="AI-powered border surveillance with real-time object detection",
    version="1.0.0"
)

# Global variables
model = None
camera = None
detection_count = 0
start_time = None


@app.on_event("startup")
async def startup():
    """Initialize model and camera on startup"""
    global model, camera, start_time
    
    start_time = datetime.now()
    
    # Load YOLO model
    model_path = "/app/models/best.pt"
    fallback_path = "yolov8n.pt"
    
    print("=" * 50)
    print("RockUGV Border Surveillance System")
    print("=" * 50)
    print(f"Starting at: {start_time}")
    
    print("\n[1/2] Loading YOLO model...")
    try:
        if os.path.exists(model_path):
            model = YOLO(model_path)
            print(f"✓ Loaded custom model: {model_path}")
        else:
            print(f"⚠ Model not found at {model_path}")
            model = YOLO(fallback_path)
            print(f"✓ Using fallback model: {fallback_path}")
        
        # Print model info
        print(f"  Classes: {model.names}")
    except Exception as e:
        print(f"✗ Error loading model: {e}")
        raise
    
    # Initialize camera
    print("\n[2/2] Initializing camera...")
    camera = USBCamera(camera_id=0, width=640, height=480, fps=30)
    print("✓ Camera initialized (will start on first request)")
    
    print("\n" + "=" * 50)
    print("System ready! Access at http://localhost:8000")
    print("=" * 50 + "\n")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Main dashboard page"""
    uptime = datetime.now() - start_time if start_time else "N/A"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>RockUGV Detection</title>
        <style>
            * {{ box-sizing: border-box; }}
            body {{ 
                font-family: 'Segoe UI', Arial, sans-serif; 
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                color: #e6e6e6;
                min-height: 100vh;
            }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            h1 {{ 
                color: #4CAF50; 
                margin-bottom: 10px;
                font-size: 2em;
            }}
            .subtitle {{ color: #888; margin-bottom: 30px; }}
            .status-bar {{
                background: #252540;
                padding: 15px 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                display: flex;
                gap: 30px;
                flex-wrap: wrap;
            }}
            .status-item {{ display: flex; align-items: center; gap: 8px; }}
            .status-dot {{ 
                width: 10px; 
                height: 10px; 
                border-radius: 50%; 
                background: #4CAF50;
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.5; }}
            }}
            .video-container {{
                background: #000;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                margin-bottom: 20px;
            }}
            .stream {{ 
                width: 100%;
                max-width: 640px;
                display: block;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
            }}
            .info-card {{
                background: #252540;
                border-radius: 8px;
                padding: 20px;
            }}
            .info-card h3 {{
                color: #4CAF50;
                margin-top: 0;
                font-size: 1.1em;
            }}
            .info-card ul {{
                list-style: none;
                padding: 0;
                margin: 0;
            }}
            .info-card li {{
                padding: 8px 0;
                border-bottom: 1px solid #333;
            }}
            .info-card li:last-child {{ border-bottom: none; }}
            .info-card a {{
                color: #64B5F6;
                text-decoration: none;
            }}
            .info-card a:hover {{ text-decoration: underline; }}
            code {{
                background: #1a1a2e;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🪨 RockUGV Border Surveillance</h1>
            <p class="subtitle">AI-Powered Real-Time Detection System</p>
            
            <div class="status-bar">
                <div class="status-item">
                    <div class="status-dot"></div>
                    <span>System Online</span>
                </div>
                <div class="status-item">
                    <span>Uptime: {uptime}</span>
                </div>
                <div class="status-item">
                    <span>Model: {'Custom' if os.path.exists('/app/models/best.pt') else 'YOLOv8n'}</span>
                </div>
            </div>
            
            <div class="video-container">
                <img class="stream" src="/video_feed" alt="Live Detection Feed">
            </div>
            
            <div class="info-grid">
                <div class="info-card">
                    <h3>📡 API Endpoints</h3>
                    <ul>
                        <li><a href="/health">/health</a> - System health check</li>
                        <li><a href="/video_feed">/video_feed</a> - Live MJPEG stream</li>
                        <li><a href="/info">/info</a> - System information</li>
                        <li><a href="/docs">/docs</a> - Interactive API docs</li>
                    </ul>
                </div>
                
                <div class="info-card">
                    <h3>⚙️ Configuration</h3>
                    <ul>
                        <li>Resolution: <code>640x480</code></li>
                        <li>Frame Rate: <code>30 FPS</code></li>
                        <li>Camera: <code>/dev/video0</code></li>
                        <li>Port: <code>8000</code></li>
                    </ul>
                </div>
            </div>
        </div>
    </body>
    </html>
    """


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "model_loaded": model is not None,
        "model_path": "/app/models/best.pt" if os.path.exists("/app/models/best.pt") else "yolov8n.pt",
        "camera_initialized": camera is not None,
        "camera_active": camera.is_running() if camera else False,
        "uptime_seconds": (datetime.now() - start_time).total_seconds() if start_time else 0
    }


@app.get("/info")
async def info():
    """System information endpoint"""
    import torch
    
    return {
        "system": {
            "name": "RockUGV Border Surveillance",
            "version": "1.0.0",
            "start_time": start_time.isoformat() if start_time else None,
        },
        "model": {
            "loaded": model is not None,
            "classes": model.names if model else None,
            "type": "YOLO"
        },
        "camera": {
            "id": camera.camera_id if camera else None,
            "resolution": f"{camera.width}x{camera.height}" if camera else None,
            "fps": camera.fps if camera else None,
            "running": camera.is_running() if camera else False
        },
        "hardware": {
            "cuda_available": torch.cuda.is_available(),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "torch_version": torch.__version__
        }
    }


def generate_frames():
    """Generate MJPEG frames with detection overlay"""
    global model, camera, detection_count
    
    # Start camera if not running
    if not camera.is_running():
        success = camera.start()
        if not success:
            print("Failed to start camera!")
            return
    
    frame_count = 0
    fps_start = time.time()
    current_fps = 0
    
    while True:
        frame = camera.read()
        if frame is None:
            time.sleep(0.1)
            continue
        
        # Run detection
        if model:
            results = model(frame, verbose=False)
            frame = results[0].plot()
            
            # Count detections
            detections = len(results[0].boxes)
            detection_count += detections
        
        # Calculate FPS
        frame_count += 1
        if frame_count >= 30:
            elapsed = time.time() - fps_start
            current_fps = frame_count / elapsed
            frame_count = 0
            fps_start = time.time()
        
        # Add FPS overlay
        cv2.putText(frame, f"FPS: {current_fps:.1f}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Encode frame
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@app.get("/video_feed")
async def video_feed():
    """MJPEG video stream endpoint"""
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/snapshot")
async def snapshot():
    """Capture single frame with detection"""
    global model, camera
    
    if not camera.is_running():
        camera.start()
        time.sleep(0.5)  # Wait for camera to warm up
    
    frame = camera.read()
    if frame is None:
        raise HTTPException(status_code=503, detail="Camera not available")
    
    if model:
        results = model(frame, verbose=False)
        frame = results[0].plot()
    
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
    
    return Response(
        content=buffer.tobytes(),
        media_type="image/jpeg",
        headers={"Content-Disposition": "inline; filename=snapshot.jpg"}
    )


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    global camera
    print("\nShutting down RockUGV system...")
    if camera:
        camera.stop()
    print("✓ Camera released")
    print("✓ Shutdown complete")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
