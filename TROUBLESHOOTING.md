# 🧩 CDDBS – Troubleshooting Guide

This guide covers common issues developers may encounter when setting up and running the **CDDBS** stack (FastAPI + PostgreSQL + Gemini AI).

---

## ⚙️ 1. Docker Not Installed or Not Running

### **Symptom**
```
FileNotFoundError: [Errno 2] No such file or directory
docker.errors.DockerException: Error while fetching server API version
```

### **Cause**
The Docker daemon is not running, or Docker is not installed correctly.

### **Fix**
#### **1. Install Docker Engine (Ubuntu)**
```bash
sudo apt update
sudo apt install ca-certificates curl gnupg lsb-release
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg |   sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo   "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg]   https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" |   sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

#### **2. Start and enable the Docker service**
```bash
sudo systemctl enable --now docker
```

#### **3. Verify Docker is running**
```bash
sudo docker ps
```

---

## 🔒 2. Permission Denied on Docker Socket

### **Symptom**
```
PermissionError: [Errno 13] Permission denied
unable to get image 'postgres:15': permission denied while trying to connect to the Docker daemon socket
```

### **Cause**
Your user does not have permission to access the Docker daemon socket (`/var/run/docker.sock`).

### **Fix**
1. Add your user to the `docker` group:
   ```bash
   sudo usermod -aG docker $USER
   ```

2. Apply the new group membership:
   ```bash
   newgrp docker
   ```

3. Verify:
   ```bash
   groups
   ```
   You should see `docker` listed.

4. Test Docker access:
   ```bash
   docker run hello-world
   ```
---

## 🧱 3. `docker-compose` Not Found or Plugin Missing

### **Symptom**
```
unable to locate package docker-compose-plugin
docker-compose: command not found
```

### **Cause**
Docker Compose plugin is missing or legacy version not installed.

### **Fix**

#### **Modern Compose (preferred)**
Installed automatically via:
```bash
sudo apt install docker-compose-plugin
```
Then use:
```bash
docker compose up --build
```
> Note the space (`docker compose`), not a hyphen.

#### **Legacy Compose**
If your system doesn’t support the plugin:
```bash
sudo apt install python3-pip
sudo pip install docker-compose
docker-compose up --build
```

---

## ⚗️ 4. Version Warning in Compose

### **Symptom**
```
WARN[0000] the attribute `version` is obsolete, it will be ignored
```

### **Cause**
New Docker Compose no longer requires a `version:` key in `docker-compose.yml`.

### **Fix**
Remove or comment out the `version:` line in `docker-compose.yml`.  
The stack will still work correctly.

---

## 🔑 5. API Keys and Environment Variables

### **Symptom**
Application builds, but API calls fail or return authentication errors.

### **Cause**
`.env` file missing or incomplete (missing `GOOGLE_API_KEY` or `SERPAPI_KEY`).

### **Fix**
1. Copy the example:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` and set:
   ```
   SERPAPI_KEY=your_serpapi_key_here
   GOOGLE_API_KEY=your_google_api_key_here
   ```
3. Restart the container:
   ```bash
   docker compose up --build
   ```

---

## ✅ Quick Verification Checklist

| Check | Command | Expected |
|--------|----------|-----------|
| Docker service running | `sudo systemctl status docker` | `active (running)` |
| User in docker group | `groups $USER` | includes `docker` |
| Docker test works | `docker run hello-world` | "Hello from Docker!" message |
| Compose builds | `docker compose up --build` | Starts `db` and `web` containers |
| App online | Visit `http://localhost:8000` | FastAPI docs visible |

---

## 💡 Additional Tips

- If changes to `.env` don’t take effect, rebuild with `--build`.
- To clean all containers and images:
  ```bash
  docker system prune -af
  ```
- To reset the database volume:
  ```bash
  docker volume rm cddbs_postgres_data
  ```

---

### 🧾 Summary

If you experience:
- **FileNotFoundError** → Docker not running  
- **PermissionError** → Add user to `docker` group  
- **Plugin not found** → Install Docker Compose plugin or legacy version  
- **API failures** → Check `.env` keys  

Once these are resolved, the project should build and run reliably on any modern Ubuntu or Docker Desktop environment.

---
