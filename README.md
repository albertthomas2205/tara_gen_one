# 🚀 Tara Gen One

Simple instructions to run the project.

---

## ⚙️ Setup

### 1. Clone the repository

```
git clone https://github.com/albertthomas2205/tara_gen_one
cd tara_gen_one
```

### 2. Create virtual environment

```
python -m venv venv
venv\\Scripts\\activate   # Windows
```

### 3. Install dependencies

```
pip install -r requirements.txt
pip install "uvicorn[standard]"
pip install channels channels-redis
```

---

## 🧠 Start Redis

### Option 1 (Docker)

```
docker run -d -p 6379:6379 redis
```

### Option 2 (WSL)

```
sudo apt update
sudo apt install redis-server
redis-server
```

---

## ▶️ Run the Project

```
uvicorn tara_2.asgi:application --host 0.0.0.0 --port 8000 --reload
```

---

## 🌐 Access

```
http://localhost:8000
```

---

## 🧪 Test API

```
curl -X POST http://localhost:8000/robot-battery/ \\
-H "Content-Type: application/json" \\
-d '{"robo_id":"RB1","battery_status":75}'
```

---

## ⚠️ Notes

* Make sure Redis is running on port 6379
* Use `0.0.0.0` to access from other devices
* Ensure ASGI is configured in Django

---

## 👨‍💻 Project Name

**Tara Gen One**
