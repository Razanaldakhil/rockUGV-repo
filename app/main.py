from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from PIL import Image
import io
import numpy as np
from ultralytics import YOLO
import cv2
import base64
import tempfile
import os
from camera import USBCamera

app = FastAPI(title="YOLOv8 Detection API with Camera Support")

# Global variables
MODEL_PATH = "/app/models/best.pt"
model = None
camera = None

@app.on_event("startup")
async def load_model():
    global model ,camera
    try:
        model = YOLO(MODEL_PATH)
        print(f" Model loaded successfully from {MODEL_PATH}")
        print(f" Classes: {model.names}")
        camera = USBCamera(camera_id=0,width=640,height=640)
        if camera.start():
          print("camera auto-started successfully")
        else:
          print("failed to auto-started camera")
    except Exception as e:
        print(f" Error loading model: {e}")

@app.on_event("shutdown")
async def shutdown():
    global camera
    if camera and camera.is_running():
        camera.stop()

@app.get("/")
def read_root():
    return {
        "status": "YOLOv8 Detection API with Camera Support",
        "model_loaded": model is not None,
        "camera_active": camera.is_running() if camera else False,
        "classes": ['person', 'face', 'knife', 'weapon', 'vehicle', 'bag', 'fire']
    }

# ==================== IMAGE DETECTION ====================

@app.post("/detect")
async def detect(file: UploadFile = File(...), conf_threshold: float = 0.1):
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        image_np = np.array(image)
        
        results = model(image_np, conf=conf_threshold)
        
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                detection = {
                    "class_id": int(box.cls[0]),
                    "class_name": model.names[int(box.cls[0])],
                    "confidence": float(box.conf[0]),
                    "bbox": {
                        "x1": float(box.xyxy[0][0]),
                        "y1": float(box.xyxy[0][1]),
                        "x2": float(box.xyxy[0][2]),
                        "y2": float(box.xyxy[0][3])
                    }
                }
                detections.append(detection)
        
        return {
            "filename": file.filename,
            "image_size": {"width": image.width, "height": image.height},
            "detections_count": len(detections),
            "detections": detections
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== VIDEO DETECTION ====================

@app.post("/detect-video")
async def detect_video(file: UploadFile = File(...), conf_threshold: float = 0.1):
    """Process video and return detection results"""
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    try:
        # Save uploaded video temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        # Open video
        cap = cv2.VideoCapture(tmp_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        frame_results = []
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Run detection
            results = model(frame, conf=conf_threshold)
            
            detections = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    detection = {
                        "class_name": model.names[int(box.cls[0])],
                        "confidence": float(box.conf[0])
                    }
                    detections.append(detection)
            
            if detections:  # Only save frames with detections
                frame_results.append({
                    "frame_number": frame_count,
                    "timestamp": frame_count / fps,
                    "detections": detections
                })
            
            frame_count += 1
        
        cap.release()
        os.unlink(tmp_path)
        
        return {
            "filename": file.filename,
            "total_frames": total_frames,
            "fps": fps,
            "duration": total_frames / fps,
            "frames_with_detections": len(frame_results),
            "results": frame_results
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== USB CAMERA CONTROL ====================

@app.post("/camera/start")
async def start_camera(camera_id: int = 0, width: int = 640, height: int = 480):
    """Start USB camera"""
    global camera
    
    if camera and camera.is_running():
        return {"message": "Camera already running", "camera_id": camera_id}
    
    camera = USBCamera(camera_id=camera_id, width=width, height=height)
    
    if camera.start():
        return {
            "message": "Camera started successfully",
            "camera_id": camera_id,
            "resolution": f"{width}x{height}"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to start camera")

@app.post("/camera/stop")
async def stop_camera():
    """Stop USB camera"""
    global camera
    
    if camera and camera.is_running():
        camera.stop()
        return {"message": "Camera stopped"}
    else:
        return {"message": "Camera was not running"}

@app.get("/camera/status")
async def camera_status():
    """Get camera status"""
    global camera
    
    return {
        "running": camera.is_running() if camera else False,
        "camera_id": camera.camera_id if camera else None
    }

@app.get("/camera/frame")
async def get_camera_frame(conf_threshold: float = 0.1):
    """Get single frame from camera with detections"""
    global camera, model
    
    if not camera or not camera.is_running():
        raise HTTPException(status_code=400, detail="Camera not running")
    
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    frame = camera.read()
    if frame is None:
        raise HTTPException(status_code=500, detail="Failed to read frame")
    
    # Run detection
    results = model(frame, conf=conf_threshold)
    
    # Annotate frame
    annotated_frame = results[0].plot()
    
    # Convert to JPEG
    _, buffer = cv2.imencode('.jpg', annotated_frame)
    
    return StreamingResponse(
        io.BytesIO(buffer.tobytes()),
        media_type="image/jpeg"
    )

@app.get("/camera/stream")
async def camera_stream():
    """Stream camera with real-time detection"""
    global camera, model
    
    if not camera or not camera.is_running():
        raise HTTPException(status_code=400, detail="Camera not running. Call /camera/start first")
    
    def generate():
        while camera and camera.is_running():
            frame = camera.read()
            if frame is None:
                continue
            
            # Run detection
            results = model(frame, conf=0.1)
            annotated_frame = results[0].plot()
            
            # Encode frame
            _, buffer = cv2.imencode('.jpg', annotated_frame)
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

# ==================== HEALTH & INFO ====================

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "camera_active": camera.is_running() if camera else False
    }

@app.get("/model-info")
def model_info():
    if model is None:
        return {"error": "Model not loaded"}
    
    return {
        "model_path": MODEL_PATH,
        "classes": model.names,
        "model_type": "YOLOv8n"
    }
