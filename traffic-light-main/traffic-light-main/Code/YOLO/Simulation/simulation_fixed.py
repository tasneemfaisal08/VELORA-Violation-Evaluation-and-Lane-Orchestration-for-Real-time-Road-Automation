"""
Traffic Intersection Simulation — v9 (Strict Fluid Flow)
========================================================
- Fixed Countdown glitch: The counter NEVER goes backwards or increases.
- Strictly linear countdown from 15 seconds down to 0.
- When emergency vehicle passes, the remaining time continues to count down
  naturally, allowing a few trailing cars to pass before turning yellow.
"""

import random, math, time, threading, os, sys
import numpy as np
from collections import deque
from enum import Enum, auto
import pygame

# Fix Windows cp1252 UnicodeEncodeError for arrows / emoji in print()
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────
defaultRed    = 20    
defaultYellow = 5
defaultGreen  = 20
minGreen      = 5
maxGreen      = 45
detectionTime = 5
simTime       = 300

noOfSignals = 4
noOfLanes   = 2

TIME_OF_DAY_SPAWN = {'morning':0.6,'midday':1.2,'evening':0.7,'night':2.0}
def get_spawn_lambda(t):
    return list(TIME_OF_DAY_SPAWN.values())[(t//75)%4]

PRIORITY = {'ambulance':100,'firetruck':90,'police':80,
            'bus':40,'truck':30,'rickshaw':20,'car':10,'bike':5}
VEHICLE_TYPES    = {0:'car',1:'bus',2:'truck',3:'rickshaw',4:'bike',
                    5:'ambulance',6:'police',7:'firetruck'}
DIRECTION_NUMBERS   = {0:'right',1:'down',2:'left',3:'up'}
DIRECTION_TO_SIGNAL = {'right':0,'down':1,'left':2,'up':3}
speeds = {'car':2.25,'bus':1.8,'truck':1.8,'rickshaw':2.0,'bike':2.5,
          'ambulance':3.5,'police':3.2,'firetruck':3.0}
carTime=2.0; bikeTime=1.0; rickshawTime=2.25; busTime=2.5; truckTime=2.5

gap=20; gap2=20

VEHICLE_SIZES = {
    'car':(44,20),'bus':(58,24),'truck':(56,22),
    'rickshaw':(36,18),'bike':(30,14),
    'ambulance':(52,22),'police':(46,20),'firetruck':(58,24),
}

# ──────────────────────────────────────────────
# GLOBAL STATE
# ──────────────────────────────────────────────
signals     = []
timeElapsed = 0
currentGreen  = 0
nextGreen     = 1
currentYellow = 0

emergencyActive      = False
emergencySignal      = None
emergencyRequest     = None
emergencyLock        = threading.Lock()
emergencyDuration    = 15  # Fixed duration for emergency clear
emgYellowDuration    = 2
emgAllRedDuration    = 1
allRedActive         = False
emergencyCooldown    = 0
emergencyCooldownTime = 25  

vehicles = {d:{0:[],1:[],'crossed':0} for d in ('right','down','left','up')}
past_green_times = {d:deque(maxlen=10) for d in ('right','down','left','up')}

lane_tail = {(d,l):None for d in ('right','down','left','up') for l in range(2)}

x = {'right':[0,0],       'down':[720,760], 'left':[1400,1400],'up':[620,660]}
y = {'right':[350,390], 'down':[0,0],        'left':[480,440],  'up':[800,800]}
stopLines   = {'right':590,'down':330,'left':800,'up':535}
defaultStop = {'right':580,'down':320,'left':810,'up':545}
stops       = {'right':[580,580],'down':[320,320],
               'left':[810,810], 'up':[545,545]}
mid         = {'right':{'x':705,'y':420},'down':{'x':730,'y':450},
               'left':{'x':665,'y':458},'up':  {'x':648,'y':400}}

signalCoods      = [(530,230),(810,230),(810,570),(530,570)]
signalTimerCoods = [(530,210),(810,210),(810,550),(530,550)]
statsCoods       = [(370,210),(880,210),(880,550),(370,550)]

rotationAngle=3

pygame.init()
simulation = pygame.sprite.Group()
_vid=0
def next_vid():
    global _vid; _vid+=1; return _vid

# ──────────────────────────────────────────────
# FSM STATES
# ──────────────────────────────────────────────
class FSM(Enum):
    IDLE=auto(); MEASURE=auto(); DECIDE=auto()
    GREEN=auto(); YELLOW=auto(); SWITCH=auto(); FALLBACK=auto()
    EMERGENCY=auto(); EMG_YELLOW=auto(); EMG_ALL_RED=auto(); EMG_GREEN=auto()

fsmState = FSM.IDLE

# ──────────────────────────────────────────────
# TRAFFIC SIGNAL
# ──────────────────────────────────────────────
class TrafficSignal:
    def __init__(self,red,yellow,green,minimum,maximum):
        self.red=red; self.yellow=yellow; self.green=green
        self.minimum=minimum; self.maximum=maximum
        self.signalText='0'; self.totalGreenTime=0
        self.density=0.0; self.queue=0; self.avgWait=0.0; self.score=0.0
        self.nextOpenIn=0  

# ──────────────────────────────────────────────
# VEHICLE CLASS
# ──────────────────────────────────────────────
class Vehicle(pygame.sprite.Sprite):
    def __init__(self,lane,vehicleClass,direction_number,direction,will_turn):
        pygame.sprite.Sprite.__init__(self)
        self.vid=next_vid(); self.lane=lane; self.vehicleClass=vehicleClass
        self.priority=PRIORITY.get(vehicleClass,10)
        self.isEmergency=vehicleClass in ('ambulance','police','firetruck')
        self.speed=speeds[vehicleClass]; self.direction_number=direction_number
        self.direction=direction; self.crossed=0; self.willTurn=will_turn
        self.turned=0; self.rotateAngle=0
        self.spawnTime=time.time(); self.waitTime=0.0; self.state='moving'

        vehicles[direction][lane].append(self)
        self.index=len(vehicles[direction][lane])-1

        path="Code/YOLO/darkflow/images/"+direction+"/"+vehicleClass+".png"
        try:
            img=pygame.image.load(path).convert_alpha()
            self.originalImage=img; self.currentImage=img
        except Exception:
            w,h=VEHICLE_SIZES.get(vehicleClass,(40,18))
            if direction in ('up','down'):
                w,h=h,w
            surf=pygame.Surface((w,h),pygame.SRCALPHA)
            body={'car':(30,120,255),'bus':(255,165,0),'truck':(140,70,30),
                  'rickshaw':(0,180,0),'bike':(210,210,0),
                  'ambulance':(255,30,30),'police':(0,50,200),'firetruck':(210,40,40)}
            bc=body.get(vehicleClass,(180,180,180))
            surf.fill((*bc,230))
            pygame.draw.rect(surf,(255,255,255,200),surf.get_rect(),2)
            if direction in ('right','left'):
                pygame.draw.rect(surf,(180,230,255,200),pygame.Rect(4,3,w//3,h-6))
            else:
                pygame.draw.rect(surf,(180,230,255,200),pygame.Rect(3,4,w-6,h//3))
            if vehicleClass in ('ambulance','police','firetruck'):
                pygame.draw.rect(surf,(255,255,0,255),pygame.Rect(w//2-3,1,6,4))
            self.originalImage=surf; self.currentImage=surf

        vw=self.currentImage.get_rect().width
        vh=self.currentImage.get_rect().height
        tail=lane_tail.get((direction,lane))

        if direction=='right':
            self.stop=(min(defaultStop[direction],tail-gap) if tail is not None
                       else (vehicles[direction][lane][self.index-1].stop
                             -vehicles[direction][lane][self.index-1].currentImage.get_rect().width-gap
                             if self.index>0 and vehicles[direction][lane][self.index-1].crossed==0
                             else defaultStop[direction]))
            self.x=x[direction][lane]-vw-gap; self.y=y[direction][lane]
            x[direction][lane]=self.x; lane_tail[(direction,lane)]=self.x

        elif direction=='left':
            self.stop=(max(defaultStop[direction],tail+gap) if tail is not None
                       else (vehicles[direction][lane][self.index-1].stop
                             +vehicles[direction][lane][self.index-1].currentImage.get_rect().width+gap
                             if self.index>0 and vehicles[direction][lane][self.index-1].crossed==0
                             else defaultStop[direction]))
            self.x=x[direction][lane]+gap; self.y=y[direction][lane]
            x[direction][lane]=self.x+vw; lane_tail[(direction,lane)]=self.x+vw

        elif direction=='down':
            self.stop=(min(defaultStop[direction],tail-gap) if tail is not None
                       else (vehicles[direction][lane][self.index-1].stop
                             -vehicles[direction][lane][self.index-1].currentImage.get_rect().height-gap
                             if self.index>0 and vehicles[direction][lane][self.index-1].crossed==0
                             else defaultStop[direction]))
            self.x=x[direction][lane]; self.y=y[direction][lane]-vh-gap
            y[direction][lane]=self.y; lane_tail[(direction,lane)]=self.y

        elif direction=='up':
            self.stop=(max(defaultStop[direction],tail+gap) if tail is not None
                       else (vehicles[direction][lane][self.index-1].stop
                             +vehicles[direction][lane][self.index-1].currentImage.get_rect().height+gap
                             if self.index>0 and vehicles[direction][lane][self.index-1].crossed==0
                             else defaultStop[direction]))
            self.x=x[direction][lane]; self.y=y[direction][lane]+gap
            y[direction][lane]=self.y+vh; lane_tail[(direction,lane)]=self.y+vh

        simulation.add(self)

    def _can_advance(self):
        if self.index==0: return True
        prev=vehicles[self.direction][self.lane][self.index-1]
        if prev.turned==1: return True
        if self.direction=='right': return self.x+self.currentImage.get_rect().width<prev.x-gap2
        elif self.direction=='left': return self.x>prev.x+prev.currentImage.get_rect().width+gap2
        elif self.direction=='down': return self.y+self.currentImage.get_rect().height<prev.y-gap2
        elif self.direction=='up':  return self.y>prev.y+prev.currentImage.get_rect().height+gap2
        return True

    def _signal_allows(self):
        if allRedActive: return self.crossed==1
        sig_idx=DIRECTION_TO_SIGNAL[self.direction]
        return (currentGreen==sig_idx and currentYellow==0) or self.crossed==1

    def move_straight(self):
        d=self.direction
        blocked=False
        if d=='right': blocked=self.x+self.currentImage.get_rect().width>self.stop
        elif d=='left': blocked=self.x<self.stop
        elif d=='down': blocked=self.y+self.currentImage.get_rect().height>self.stop
        elif d=='up':   blocked=self.y<self.stop
        can_move=(not blocked or self._signal_allows()) and self._can_advance()
        if can_move:
            self.state='moving'
            if d=='right': self.x+=self.speed
            elif d=='left': self.x-=self.speed
            elif d=='down': self.y+=self.speed
            elif d=='up':   self.y-=self.speed
        else:
            self.state='waiting'; self.waitTime+=1.0/60.0

    def move_turn(self):
        d=self.direction; m=mid[d]; past_mid=False
        if d=='right': past_mid=self.x+self.currentImage.get_rect().width>=m['x']
        elif d=='down': past_mid=self.y+self.currentImage.get_rect().height>=m['y']
        elif d=='left': past_mid=self.x<=m['x']
        elif d=='up':   past_mid=self.y<=m['y']
        if not past_mid or self.crossed==0:
            self.move_straight()
        else:
            if self.turned==0:
                self.rotateAngle+=rotationAngle
                self.currentImage=pygame.transform.rotate(self.originalImage,-self.rotateAngle)
                if d=='right':  self.x+=2;   self.y+=1.8
                elif d=='down': self.x-=2.5; self.y+=2
                elif d=='left': self.x-=1.8; self.y-=2.5
                elif d=='up':   self.x+=1;   self.y-=1
                if self.rotateAngle>=90: self.turned=1
            else:
                if self._can_advance():
                    if d=='right': self.y+=self.speed
                    elif d=='down': self.x-=self.speed
                    elif d=='left': self.y-=self.speed
                    elif d=='up':   self.x+=self.speed

    def check_crossed(self):
        d=self.direction
        if self.crossed==0:
            if d=='right' and self.x+self.currentImage.get_rect().width>stopLines[d]:
                self.crossed=1; vehicles[d]['crossed']+=1
            elif d=='left' and self.x<stopLines[d]:
                self.crossed=1; vehicles[d]['crossed']+=1
            elif d=='down' and self.y+self.currentImage.get_rect().height>stopLines[d]:
                self.crossed=1; vehicles[d]['crossed']+=1
            elif d=='up' and self.y<stopLines[d]:
                self.crossed=1; vehicles[d]['crossed']+=1

    def move(self):
        self.check_crossed()
        if self.willTurn: self.move_turn()
        else: self.move_straight()

# ──────────────────────────────────────────────
# STATISTICS
# ──────────────────────────────────────────────
LANE_CAPACITY=20

def compute_lane_stats(sig_idx):
    direction=DIRECTION_NUMBERS[sig_idx]
    total_v=0; total_w=0; total_wt=0.0; has_emg=False; psum=0; now=time.time()
    for lane in range(2):
        for v in vehicles[direction][lane]:
            if v.crossed==0:
                total_v+=1; total_w+=1; total_wt+=now-v.spawnTime
                psum+=v.priority
                if v.isEmergency: has_emg=True
    density=min(1.0,total_v/(LANE_CAPACITY*2))
    avg_wait=total_wt/max(total_w,1) if total_w>0 else 0.0
    emg_bonus=200 if has_emg else 0
    score=density*40+avg_wait*0.5+emg_bonus+psum*0.05
    return total_v,density,avg_wait,has_emg,score

def update_all_stats():
    for i in range(noOfSignals):
        q,d,w,_,sc=compute_lane_stats(i)
        signals[i].queue=q; signals[i].density=d
        signals[i].avgWait=w; signals[i].score=sc

# ──────────────────────────────────────────────
# DECISION ENGINE
# ──────────────────────────────────────────────
def choose_next_green():
    best_i=-1; best_s=-1
    for i in range(noOfSignals):
        if i==currentGreen: continue
        if signals[i].score>best_s:
            best_s=signals[i].score; best_i=i
    return best_i if best_i>=0 else (currentGreen+1)%noOfSignals

def compute_dynamic_green(sig_idx):
    direction=DIRECTION_NUMBERS[sig_idx]
    noC=noB=noT=noR=noBike=0
    for lane in range(2):
        for v in vehicles[direction][lane]:
            if v.crossed==0:
                vc=v.vehicleClass
                if vc=='car': noC+=1
                elif vc=='bus': noB+=1
                elif vc=='truck': noT+=1
                elif vc=='rickshaw': noR+=1
                elif vc=='bike': noBike+=1
    total_q=noC+noB+noT+noR+noBike
    if total_q==0: return minGreen
    wcount=noC*carTime+noB*busTime+noT*truckTime+noR*rickshawTime+noBike*bikeTime
    raw=math.ceil(wcount/(noOfLanes+1))
    hist=past_green_times[direction]
    if len(hist)>=3:
        raw=int(raw*0.7+(sum(hist)/len(hist))*0.3)
    return max(minGreen,min(maxGreen,raw))

# ──────────────────────────────────────────────
# SIGNAL HELPERS
# ──────────────────────────────────────────────
def resetStops(sig_idx):
    d=DIRECTION_NUMBERS[sig_idx]
    for l in range(2):
        stops[d][l]=defaultStop[d]
        for v in vehicles[d][l]: v.stop=defaultStop[d]

def updateValues():
    for i in range(noOfSignals):
        if i==currentGreen:
            if currentYellow==0:
                # Continuous, uninterrupted countdown for everyone
                signals[i].green=max(0,signals[i].green-1)
                signals[i].totalGreenTime+=1
            else:
                signals[i].yellow=max(0,signals[i].yellow-1)
        else:
            signals[i].red=max(0,signals[i].red-1)

def backgroundTicker():
    while True:
        time.sleep(1)
        updateValues()

# ──────────────────────────────────────────────
# FSM (NATURAL CASCADE - NO ARBITRARY RE-RUNS)
# ──────────────────────────────────────────────
def repeat():
    global currentGreen,currentYellow,nextGreen,fsmState
    global emergencyActive,emergencySignal,emergencyRequest,allRedActive,emergencyCooldown

    fsmState=FSM.IDLE; detection_done=False

    while True:
        _emg=(FSM.EMERGENCY,FSM.EMG_YELLOW,FSM.EMG_ALL_RED,FSM.EMG_GREEN)
        if emergencyActive and fsmState not in _emg:
            fsmState=FSM.EMERGENCY

        if fsmState==FSM.IDLE:
            update_all_stats(); fsmState=FSM.MEASURE

        elif fsmState==FSM.MEASURE:
            update_all_stats()
            fsmState=FSM.DECIDE

        elif fsmState==FSM.DECIDE:
            nextGreen=choose_next_green()
            gt=compute_dynamic_green(nextGreen)
            signals[nextGreen].green=gt
            detection_done=True; currentYellow=0; fsmState=FSM.GREEN

        elif fsmState==FSM.GREEN:
            if emergencyActive: fsmState=FSM.EMERGENCY; continue
            if signals[currentGreen].green<=0: fsmState=FSM.YELLOW; continue
            if signals[nextGreen].red==detectionTime and not detection_done:
                update_all_stats()
                nextGreen=choose_next_green()
                signals[nextGreen].green=compute_dynamic_green(nextGreen)
                detection_done=True
            time.sleep(1)

        elif fsmState==FSM.YELLOW:
            currentYellow=1
            signals[currentGreen].yellow=defaultYellow
            resetStops(currentGreen)
            while signals[currentGreen].yellow>0: time.sleep(0.2)
            fsmState=FSM.SWITCH

        elif fsmState==FSM.SWITCH:
            currentYellow=0
            d=DIRECTION_NUMBERS[currentGreen]
            past_green_times[d].append(signals[currentGreen].totalGreenTime)
            signals[currentGreen].totalGreenTime=0
            signals[currentGreen].green=defaultGreen
            signals[currentGreen].yellow=defaultYellow
            signals[currentGreen].red=defaultGreen+defaultYellow  
            currentGreen=nextGreen
            signals[currentGreen].yellow=defaultYellow
            nextGreen=(currentGreen+1)%noOfSignals
            signals[nextGreen].red=signals[currentGreen].green+signals[currentGreen].yellow
            detection_done=False; fsmState=FSM.IDLE

        elif fsmState==FSM.FALLBACK:
            signals[nextGreen].green=defaultGreen; detection_done=True; fsmState=FSM.GREEN

        elif fsmState==FSM.EMERGENCY:
            target=emergencyRequest
            if target is None: time.sleep(0.2); continue
            if currentGreen==target and currentYellow==0: fsmState=FSM.EMG_GREEN
            else:
                nextGreen = target
                fsmState=FSM.EMG_YELLOW

        elif fsmState==FSM.EMG_YELLOW:
            currentYellow=1
            signals[currentGreen].yellow=emgYellowDuration
            resetStops(currentGreen)
            while signals[currentGreen].yellow>0: time.sleep(0.2)
            currentYellow=0; fsmState=FSM.EMG_ALL_RED

        elif fsmState==FSM.EMG_ALL_RED:
            allRedActive=True
            for i in range(noOfSignals):
                signals[i].green=0; signals[i].yellow=0
                signals[i].red=emgAllRedDuration+emergencyDuration+defaultYellow
            time.sleep(emgAllRedDuration)
            allRedActive=False; fsmState=FSM.EMG_GREEN

        elif fsmState==FSM.EMG_GREEN:
            target=emergencyRequest
            currentGreen=target; nextGreen=(currentGreen+1)%noOfSignals
            currentYellow=0
            
            # Give a fixed, ample time (15s) for the emergency phase to count down linearly
            signals[currentGreen].green = emergencyDuration
            for i in range(noOfSignals):
                if i != currentGreen:
                    signals[i].red = emergencyDuration + defaultYellow
                    signals[i].green = 0; signals[i].yellow = 0
            
            # The loop just waits for the standard background countdown to hit 0 naturally.
            # No edits, no jumps, no additions. Emergency vehicle crosses, trailing cars follow,
            # and the flow finishes purely and cleanly.
            while signals[currentGreen].green > 0:
                time.sleep(0.2)
            
            update_all_stats()
            best_i=-1; best_s=-1
            for i in range(noOfSignals):
                if i==currentGreen: continue
                if signals[i].score>best_s:
                    best_s=signals[i].score; best_i=i
            nextGreen=best_i if best_i>=0 else (currentGreen+1)%noOfSignals
            
            currentYellow=1
            signals[currentGreen].yellow=defaultYellow
            resetStops(currentGreen)
            while signals[currentGreen].yellow>0: time.sleep(0.2)
            currentYellow=0
            emergencyRequest=None; emergencySignal=None; emergencyActive=False
            emergencyCooldown=emergencyCooldownTime
            
            gt=compute_dynamic_green(nextGreen)
            signals[currentGreen].green=0
            signals[currentGreen].yellow=0
            signals[currentGreen].red=defaultGreen*noOfSignals
            
            currentGreen = nextGreen
            signals[currentGreen].green=gt
            signals[currentGreen].yellow=0
            signals[currentGreen].red=0
            
            for i in range(noOfSignals):
                if i!=currentGreen: signals[i].red=defaultGreen*noOfSignals
                
            nextGreen=(currentGreen+1)%noOfSignals
            fsmState=FSM.GREEN

# ──────────────────────────────────────────────
# SIGNAL INIT
# ──────────────────────────────────────────────
def initialize():
    slot = defaultGreen + defaultYellow
    red_offsets = [0, slot, slot*2, slot*3]
    for i in range(noOfSignals):
        ts = TrafficSignal(red_offsets[i], defaultYellow, defaultGreen, minGreen, maxGreen)
        signals.append(ts)
    repeat()

# ──────────────────────────────────────────────
# EMERGENCY TRIGGER
# ──────────────────────────────────────────────
def triggerEmergency(targetSignal,_dir):
    global emergencyActive,emergencySignal,emergencyRequest
    with emergencyLock:
        if emergencyActive: return
        emergencyActive=True; emergencySignal=targetSignal; emergencyRequest=targetSignal

# ──────────────────────────────────────────────
# VEHICLE GENERATION
# ──────────────────────────────────────────────
def generateVehicles():
    while True:
        lam=get_spawn_lambda(timeElapsed) * 0.5
        wait=max(0.10, np.random.exponential(lam))
        r=random.random()
        if   r<0.04: vt=random.randint(5,7)
        elif r<0.09: vt=1
        elif r<0.12: vt=2
        elif r<0.17: vt=3
        elif r<0.27: vt=4
        else:        vt=0
        dn=random.choices([0,1,2,3],weights=[25,25,25,25])[0]
        
        will_turn=0
        if vt not in (5,6,7) and random.random()<0.4:
            will_turn=1
            
        if will_turn:
            lane = 0 if dn == 1 else 1
        else:
            if vt == 4:
                lane = 1 if dn == 1 else 0
            elif vt in (1,2):
                lane = 0 if dn == 1 else 1
            else:
                lane = random.choice([0, 1])
                
        Vehicle(lane,VEHICLE_TYPES[vt],dn,DIRECTION_NUMBERS[dn],will_turn)
        time.sleep(wait)

def simulationTime():
    global timeElapsed, emergencyCooldown
    while True:
        time.sleep(1); timeElapsed+=1
        if emergencyCooldown > 0:
            emergencyCooldown -= 1
        if timeElapsed==simTime:
            total=sum(vehicles[DIRECTION_NUMBERS[i]]['crossed'] for i in range(4))
            print('\n=== SIMULATION END ===')
            for i in range(4):
                print(f"  {DIRECTION_NUMBERS[i]}: {vehicles[DIRECTION_NUMBERS[i]]['crossed']}")
            print(f"  Total: {total}  Throughput: {total/simTime:.2f} veh/s")
            os._exit(0)

# ──────────────────────────────────────────────
# DARK BACKGROUND BUILDER
# ──────────────────────────────────────────────
def build_background(W, H):
    surf = pygame.Surface((W, H))
    C_GRASS      = (18, 52, 18)
    C_ROAD       = (28, 28, 28)
    C_PAVEMENT   = (45, 45, 50)
    C_LANE_WHITE = (200, 200, 200)
    C_LANE_YEL   = (220, 180, 0)
    C_BUILDING_A = (35, 38, 50)
    C_BUILDING_B = (42, 30, 30)
    C_BUILDING_C = (30, 42, 35)
    C_ROOF_A     = (55, 25, 25)
    C_ROOF_B     = (25, 40, 55)
    C_WINDOW     = (255, 230, 120)
    C_DOOR       = (80, 50, 30)

    surf.fill(C_GRASS)
    int_left  = 590;  int_right = 800
    int_top   = 330;  int_bot   = 535

    pygame.draw.rect(surf, C_PAVEMENT, (0, int_top-10, W, int_bot-int_top+20))
    pygame.draw.rect(surf, C_ROAD,     (0, int_top, W, int_bot-int_top))
    pygame.draw.rect(surf, C_PAVEMENT, (int_left-10, 0, int_right-int_left+20, H))
    pygame.draw.rect(surf, C_ROAD,     (int_left, 0, int_right-int_left, H))
    pygame.draw.rect(surf, C_ROAD, (int_left, int_top, int_right-int_left, int_bot-int_top))

    stripe_w = 8; stripe_gap = 6
    for sx in range(int_left+10, int_right-10, stripe_w+stripe_gap):
        pygame.draw.rect(surf,(240,240,240),(sx, int_top-30, stripe_w, 28))
    for sx in range(int_left+10, int_right-10, stripe_w+stripe_gap):
        pygame.draw.rect(surf,(240,240,240),(sx, int_bot+2, stripe_w, 28))
    for sy in range(int_top+10, int_bot-10, stripe_w+stripe_gap):
        pygame.draw.rect(surf,(240,240,240),(int_left-30, sy, 28, stripe_w))
    for sy in range(int_top+10, int_bot-10, stripe_w+stripe_gap):
        pygame.draw.rect(surf,(240,240,240),(int_right+2, sy, 28, stripe_w))

    mid_y = (int_top + int_bot)//2
    dash_len=28; dash_gap=18
    for dx in range(0, W, dash_len+dash_gap):
        if dx+dash_len < int_left or dx > int_right:
            pygame.draw.rect(surf, C_LANE_WHITE,(dx, mid_y-1, dash_len, 3))
    pygame.draw.line(surf, C_LANE_YEL, (0,int_top+6),    (int_left-10,int_top+6),    3)
    pygame.draw.line(surf, C_LANE_YEL, (int_right+10,int_top+6), (W,int_top+6),      3)
    pygame.draw.line(surf, C_LANE_YEL, (0,int_bot-6),    (int_left-10,int_bot-6),    3)
    pygame.draw.line(surf, C_LANE_YEL, (int_right+10,int_bot-6),(W,int_bot-6),       3)

    mid_x=(int_left+int_right)//2
    for dy in range(0, H, dash_len+dash_gap):
        if dy+dash_len < int_top or dy > int_bot:
            pygame.draw.rect(surf, C_LANE_WHITE,(mid_x-1, dy, 3, dash_len))
    pygame.draw.line(surf, C_LANE_YEL, (int_left+6,0),      (int_left+6,int_top-10),    3)
    pygame.draw.line(surf, C_LANE_YEL, (int_left+6,int_bot+10),(int_left+6,H),            3)
    pygame.draw.line(surf, C_LANE_YEL, (int_right-6,0),     (int_right-6,int_top-10),   3)
    pygame.draw.line(surf, C_LANE_YEL, (int_right-6,int_bot+10),(int_right-6,H),          3)

    def draw_building(bx,by,bw,bh,bc,rc, win_rows=2, win_cols=3):
        pygame.draw.rect(surf, bc, (bx,by,bw,bh))
        pygame.draw.rect(surf, (60,60,60), (bx,by,bw,bh), 1)
        roof_h = bw//3
        pts = [(bx-4,by),(bx+bw+4,by),(bx+bw//2,by-roof_h)]
        pygame.draw.polygon(surf,rc,pts)
        pygame.draw.polygon(surf,(40,40,40),pts,1)
        ww=14; wh=12; wx_gap=8; wy_gap=10
        row_start_y = by+10
        for row in range(win_rows):
            wy = row_start_y + row*(wh+wy_gap)
            for col in range(win_cols):
                wx = bx+8 + col*(ww+wx_gap)
                if wx+ww < bx+bw-4:
                    lit = random.random() > 0.3
                    wc = C_WINDOW if lit else (30,30,30)
                    pygame.draw.rect(surf,wc,(wx,wy,ww,wh))
                    pygame.draw.rect(surf,(60,60,60),(wx,wy,ww,wh),1)
        dw=12; dh=18
        dx=bx+bw//2-dw//2; dy=by+bh-dh
        pygame.draw.rect(surf,C_DOOR,(dx,dy,dw,dh))
        pygame.draw.circle(surf,(200,160,60),(dx+dw-3,dy+dh//2),2)

    random.seed(42)
    draw_building( 50, 140, 90, 80, C_BUILDING_A, C_ROOF_A, 2,3)
    draw_building(180, 145, 70, 70, C_BUILDING_B, C_ROOF_B, 2,2)
    draw_building( 70, 240, 80, 75, C_BUILDING_C, C_ROOF_A, 2,3)
    draw_building(260, 230, 100,85, C_BUILDING_B, C_ROOF_B, 2,3)
    draw_building(870,  40, 90, 80, C_BUILDING_C, C_ROOF_B, 2,3)
    draw_building(1010, 55, 80, 70, C_BUILDING_A, C_ROOF_A, 2,2)
    draw_building(1150, 40, 95, 85, C_BUILDING_B, C_ROOF_A, 2,3)
    draw_building(1300, 60, 70, 75, C_BUILDING_C, C_ROOF_B, 2,2)
    draw_building( 60, 590, 90, 80, C_BUILDING_B, C_ROOF_A, 2,3)
    draw_building(220, 610, 80, 70, C_BUILDING_A, C_ROOF_B, 2,2)
    draw_building( 80, 700, 75, 70, C_BUILDING_C, C_ROOF_A, 2,3)
    draw_building(240, 700, 95, 85, C_BUILDING_B, C_ROOF_B, 2,3)
    draw_building(870, 660, 90, 80, C_BUILDING_A, C_ROOF_A, 2,3)
    draw_building(1020,605, 80, 75, C_BUILDING_C, C_ROOF_B, 2,2)
    draw_building(1160,590, 95, 85, C_BUILDING_B, C_ROOF_A, 2,3)
    draw_building(1310,610, 70, 70, C_BUILDING_A, C_ROOF_B, 2,2)
    return surf

def draw_rounded_panel(surf, rect, fill_colour, border_colour=None, radius=8, alpha=200):
    s=pygame.Surface((rect.w,rect.h),pygame.SRCALPHA)
    pygame.draw.rect(s,(*fill_colour,alpha),(0,0,rect.w,rect.h),border_radius=radius)
    if border_colour:
        pygame.draw.rect(s,(*border_colour,255),(0,0,rect.w,rect.h),2,border_radius=radius)
    surf.blit(s,(rect.x,rect.y))

def make_signal_light(state):
    w,h=32,80
    s=pygame.Surface((w,h),pygame.SRCALPHA)
    pygame.draw.rect(s,(25,25,25,240),(0,0,w,h),border_radius=6)
    pygame.draw.rect(s,(60,60,60,200),(0,0,w,h),2,border_radius=6)
    r_off=(80,0,0); y_off=(80,70,0); g_off=(0,80,0)
    r_on=(255,50,50); y_on=(255,210,0); g_on=(50,255,80)
    bulbs={'red':(r_on if state=='red' else r_off,(w//2,14)),
           'yellow':(y_on if state=='yellow' else y_off,(w//2,40)),
           'green':(g_on if state=='green' else g_off,(w//2,66))}
    for _,(col,pos) in bulbs.items():
        pygame.draw.circle(s,col,pos,11)
        if col not in (r_off,y_off,g_off):
            glow=pygame.Surface((30,30),pygame.SRCALPHA)
            pygame.draw.circle(glow,(*col,60),(15,15),15)
            s.blit(glow,(pos[0]-15,pos[1]-15))
    return s

# ──────────────────────────────────────────────
# MAIN UI
# ──────────────────────────────────────────────
class Main:
    threading.Thread(target=simulationTime,   daemon=True,name="timer").start()
    threading.Thread(target=initialize,        daemon=True,name="fsm").start()
    threading.Thread(target=backgroundTicker,  daemon=True,name="ticker").start()

    W,H=1400,800
    screen=pygame.display.set_mode((W,H))
    pygame.display.set_caption("AI Traffic Simulation v9 — Dark Mode")

    bg = build_background(W,H)

    fnt  = pygame.font.SysFont("consolas",18)
    fntS = pygame.font.SysFont("consolas",15)
    fntB = pygame.font.SysFont("consolas",24,bold=True)
    fntT = pygame.font.SysFont("consolas",13)

    BLACK=(0,0,0); WHITE=(240,240,240); GREY=(120,120,120)
    RED=(220,60,60); GRN=(60,220,80); YEL=(240,200,0)
    CYN=(0,210,230); ORG=(255,140,0); MAG=(200,60,200)
    PANEL_BG=(12,14,20); PANEL_BD_N=(50,60,80); PANEL_BD_G=(40,180,60)
    PANEL_BD_R=(180,40,40); PANEL_BD_Y=(200,160,0); PANEL_BD_E=(220,60,0)

    threading.Thread(target=generateVehicles,daemon=True,name="gen").start()
    clock=pygame.time.Clock()

    while True:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: sys.exit()

        screen.blit(bg,(0,0))

        # ══════════════════════════════════════════
        # TOP STATUS BAR
        # ══════════════════════════════════════════
        draw_rounded_panel(screen,pygame.Rect(5,5,340,120),(12,14,20),PANEL_BD_N,10,200)

        fsm_col=ORG if fsmState in (FSM.EMG_YELLOW,FSM.EMG_ALL_RED,FSM.EMG_GREEN) else CYN
        screen.blit(fntB.render(f"FSM: {fsmState.name}",True,fsm_col),(14,12))

        total_x=sum(vehicles[DIRECTION_NUMBERS[i]]['crossed'] for i in range(4))
        screen.blit(fnt.render(f"Time   {timeElapsed:>4}s / {simTime}s",True,WHITE),(14,44))
        screen.blit(fnt.render(f"Crossed {total_x:>4}  vehicles",True,WHITE),(14,66))
        lam_txt=f"Spawn λ = {get_spawn_lambda(timeElapsed):.2f}s"
        screen.blit(fntS.render(lam_txt,True,GREY),(14,90))

        # Status Panel (1 for active emergency, 0 for normal)
        status_val = "1" if emergencyActive else "0"
        draw_rounded_panel(screen,pygame.Rect(360,5,320,40),(12,14,20),PANEL_BD_N,8,220)
        screen.blit(fntB.render(f"Status: {status_val}",True,CYN),(368,12))

        # ══════════════════════════════════════════
        # PER-SIGNAL PANELS (NUMERIC ONLY)
        # ══════════════════════════════════════════
        for i in range(noOfSignals):
            sig=signals[i]; sx,sy=signalCoods[i]; tx,ty=signalTimerCoods[i]; px,py=statsCoods[i]

            if allRedActive:
                state='red'; val=max(0,sig.red); lc=RED; bd=PANEL_BD_R
            elif i==currentGreen:
                if currentYellow==1:
                    state='yellow'; val=max(0,sig.yellow); lc=YEL; bd=PANEL_BD_Y
                else:
                    state='green'; val=max(0,sig.green); lc=GRN if not emergencyActive else ORG
                    bd=PANEL_BD_G if not emergencyActive else PANEL_BD_E
            elif i==nextGreen and currentYellow==1:
                state='yellow'; val=max(0,signals[currentGreen].yellow); lc=YEL; bd=PANEL_BD_Y
            else:
                state='red'; val=max(0,sig.red); lc=RED; bd=PANEL_BD_R

            sig.signalText = f"{val}"

            light_surf=make_signal_light(state)
            screen.blit(light_surf,(sx,sy))

            # Timer number overlay
            timer_surf=fntB.render(f"{val}",True,lc)
            screen.blit(timer_surf,(tx-timer_surf.get_width()//2,ty-20))

            # Stats panel
            panel_w=130; panel_h=92
            draw_rounded_panel(screen,pygame.Rect(px-6,py-4,panel_w,panel_h),PANEL_BG,bd,8,210)

            dn=DIRECTION_NUMBERS[i].upper()
            dp=int(sig.density*100)
            dc=(255,max(0,int(200*(1-sig.density))),0)

            screen.blit(fntS.render(f"◈ {dn}   Q:{sig.queue:>3}",True,WHITE),(px,py+2))
            screen.blit(fntT.render(f"Density  {dp:>3}%",True,dc),(px,py+20))

            bar_w=int((panel_w-16)*sig.density)
            pygame.draw.rect(screen,(30,30,30),(px,py+36,panel_w-16,6),border_radius=3)
            if bar_w>0:
                bar_c=(60,200,60) if dp<40 else (200,150,0) if dp<70 else (220,50,50)
                pygame.draw.rect(screen,bar_c,(px,py+36,bar_w,6),border_radius=3)

            screen.blit(fntT.render(f"Wait    {sig.avgWait:>5.1f}s",True,(180,180,255)),(px,py+48))
            screen.blit(fntT.render(f"Score   {sig.score:>6.0f}",True,CYN),(px,py+65))

        # ══════════════════════════════════════════
        # EMERGENCY CHECK
        # ══════════════════════════════════════════
        if not emergencyActive and emergencyCooldown == 0:
            for v in list(simulation):
                if v.isEmergency and v.crossed == 0:
                    tgt = DIRECTION_TO_SIGNAL[v.direction]
                    threading.Thread(target=triggerEmergency,
                                     args=(tgt,v.direction),daemon=True).start()
                    break

        # ══════════════════════════════════════════
        # DRAW & MOVE VEHICLES
        # ══════════════════════════════════════════
        for v in simulation:
            screen.blit(v.currentImage,(int(v.x),int(v.y)))
            v.move()

        pygame.display.update()
        clock.tick(60)

Main()