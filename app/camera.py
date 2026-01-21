import cv2
import threading
import time

class USBCamera:
    def __init__(self, camera_id=0, width=640, height=480, fps=30):
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        self.frame = None
        self.running = False
        self.lock = threading.Lock()
        
    def start(self):
        """Start the camera stream"""
        if self.running:
            return True
            
        self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            print(f" Failed to open camera {self.camera_id}")
            return False
        
        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        
        self.running = True
        
        # Start capture thread
        self.thread = threading.Thread(target=self._update_frame, daemon=True)
        self.thread.start()
        
        print(f" Camera {self.camera_id} started: {self.width}x{self.height} @ {self.fps}fps")
        return True
    
    def _update_frame(self):
        """Continuously read frames from camera"""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame
            time.sleep(0.01)
    
    def read(self):
        """Get the latest frame"""
        with self.lock:
            return self.frame.copy() if self.frame is not None else None
    
    def stop(self):
        """Stop the camera stream"""
        self.running = False
        if self.thread:
            self.thread.join()
        if self.cap:
            self.cap.release()
        print(f" Camera {self.camera_id} stopped")
    
    def is_running(self):
        return self.running
