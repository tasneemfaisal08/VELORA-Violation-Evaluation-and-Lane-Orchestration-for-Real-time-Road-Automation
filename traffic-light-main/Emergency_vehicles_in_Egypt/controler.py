import os
import time
import math
from ultralytics import YOLO

# ─────────────────────────────────────────────────────────
# SYSTEM STATE CONFIGURATIONS (FROM SIMULATION LOGIC)
# ─────────────────────────────────────────────────────────
MIN_GREEN = 5
MAX_GREEN = 45
DEFAULT_YELLOW = 5
EMG_YELLOW_DURATION = 2
EMG_ALL_RED_DURATION = 1

# Priority scoring matrix & vehicle capacity distribution factors
PRIORITY = {0: 100, 1: 90, 4: 80, 5: 40, 6: 30, 2: 10, 7: 5} 
TIME_WEIGHTS = {2: 2.0, 7: 1.0, 5: 2.5, 6: 2.5} 

class TrafficControllerCore:
    def __init__(self, model_path):
        self.model = YOLO(model_path)
        self.emergency_active = False
        self.emergency_cooldown = 0
        self.last_cooldown_tick = time.time()
        
        self.current_green_lane = 0
        self.lane_wait_times = [0.0, 0.0, 0.0, 0.0] 
        self.last_update_time = time.time()

    def update_cooldown(self):
        """Manages the fallback immunity period for standard lanes post-override."""
        now = time.time()
        elapsed = now - self.last_cooldown_tick
        if elapsed >= 1.0:
            if self.emergency_cooldown > 0:
                self.emergency_cooldown -= int(elapsed)
            self.last_cooldown_tick = now

    def trigger_hardware_lights(self, lane_idx, state):
        """
        Production Serial Interface boundary.
        Replace prints directly with physical connection pipelines (e.g., Arduino serial.write()).
        """
        print(f"📡 [HARDWARE OUTPUT] -> Lane {lane_idx} State: {state.upper()}")

    def process_frame(self, frame):
        """Runs localized computer vision inferences to count queue classes."""
        results = self.model.predict(source=frame, conf=0.30, verbose=False)
        
        queue_count = 0
        priority_sum = 0
        has_emergency = False
        no_car = no_bike = no_bus = no_truck = 0

        if results[0].boxes is not None:
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                if cls_id == 3:  # Explicit exclusion of pedestrians from road queues
                    continue
                
                queue_count += 1
                priority_sum += PRIORITY.get(cls_id, 10)
                
                if cls_id in [0, 1, 4]: 
                    has_emergency = True
                
                if cls_id == 2: no_car += 1
                elif cls_id == 7: no_bike += 1
                elif cls_id == 5: no_bus += 1
                elif cls_id == 6: no_truck += 1

        density = min(1.0, queue_count / 40.0)
        return queue_count, density, has_emergency, priority_sum, (no_car, no_bike, no_bus, no_truck)

    def compute_dynamic_green(self, counts):
        """Executes the time-allocation algorithm based on aggregate volume weights."""
        no_car, no_bike, no_bus, no_truck = counts
        wcount = (no_car * TIME_WEIGHTS[2] + 
                  no_bike * TIME_WEIGHTS[7] + 
                  no_bus * TIME_WEIGHTS[5] + 
                  no_truck * TIME_WEIGHTS[6])
        raw = math.ceil(wcount / 3)
        return max(MIN_GREEN, min(MAX_GREEN, raw))

    def run_logic(self, frame):
        """The computational finite-state engine evaluating active intersection vectors."""
        self.update_cooldown()
        now = time.time()
        dt = now - self.last_update_time
        self.last_update_time = now

        # Compute raw infrastructure densities
        q, density, has_emg, psum, counts = self.process_frame(frame)
        
        for i in range(4):
            if i != self.current_green_lane:
                self.lane_wait_times[i] += dt
            else:
                self.lane_wait_times[i] = 0.0

        # Conditional Priority Handling Engine
        if has_emg and not self.emergency_active and self.emergency_cooldown == 0:
            self.emergency_active = True
            self.trigger_hardware_lights(self.current_green_lane, "yellow")
            return

        if self.emergency_active:
            if not has_emg:
                self.emergency_active = False
                self.emergency_cooldown = 15
                self.trigger_hardware_lights(self.current_green_lane, "yellow")
            return

        # Standard Mathematical Cost Optimization Rules
        avg_wait = self.lane_wait_times[self.current_green_lane]
        emg_bonus = 200 if has_emg else 0
        score = density * 40 + avg_wait * 0.5 + emg_bonus + psum * 0.05
        
        dynamic_green_time = self.compute_dynamic_green(counts)
        
        # System outputs phase calculations quietly for downstream API consumption
        return {
            "lane": self.current_green_lane,
            "calculated_score": score,
            "allocated_green_duration": dynamic_green_time,
            "vehicle_queue_count": q
        }