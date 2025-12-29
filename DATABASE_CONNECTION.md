# Database Connection Guide (DBeaver)

This guide explains how to connect to the CDDBS PostgreSQL database using DBeaver or any PostgreSQL client.

## Connection Details

The database is running in a Docker container and is exposed on port `5432` on your local machine.

### Default Connection Parameters

Based on the `docker-compose.yml` and `.env` file:

- **Host**: `localhost` (or `127.0.0.1`)
- **Port**: `5432`
- **Database**: Value from `POSTGRES_DB` in your `.env` file (default: `cddbs`)
- **Username**: Value from `POSTGRES_USER` in your `.env` file (default: `admin`)
- **Password**: Value from `POSTGRES_PASSWORD` in your `.env` file (default: `admin`)

## Finding Your Actual Credentials

### Option 1: Check Your .env File

```bash
cat .env | grep POSTGRES
```

This will show:
- `POSTGRES_USER=your_username`
- `POSTGRES_PASSWORD=your_password`
- `POSTGRES_DB=your_database_name`

### Option 2: Check Docker Container Environment

```bash
docker compose exec db env | grep POSTGRES
```

## Connecting with DBeaver

### Step 1: Create New Connection

1. Open DBeaver
2. Click **"New Database Connection"** (plug icon) or go to `Database` → `New Database Connection`
3. Select **PostgreSQL** from the list
4. Click **Next**

### Step 2: Enter Connection Details

In the connection settings:

**Main Tab:**
- **Host**: `localhost`
- **Port**: `5432`
- **Database**: `cddbs` (or your value from `.env`)
- **Username**: `admin` (or your value from `.env`)
- **Password**: `admin` (or your value from `.env`)
- ✅ Check **"Save password"** if you want DBeaver to remember it

**Driver Properties Tab (Optional):**
- No changes needed for basic connection

### Step 3: Test Connection

1. Click **"Test Connection"** button
2. If prompted to download PostgreSQL driver, click **"Download"**
3. Wait for the driver to download and install
4. Click **"Test Connection"** again
5. You should see: **"Connected"** ✅

### Step 4: Connect

1. Click **"Finish"** to save the connection
2. Double-click the connection in the Database Navigator to connect
3. You should now see the database schema with tables:
   - `outlets`
   - `articles`
   - `reports`

## Troubleshooting

### Connection Refused Error

**Problem**: "Connection refused" or "Could not connect to server"

**Solutions**:
1. **Verify Docker container is running**:
   ```bash
   docker compose ps
   ```
   The `db` service should show status "Up"

2. **Check if port 5432 is available**:
   ```bash
   netstat -tuln | grep 5432
   # or
   ss -tuln | grep 5432
   ```
   Should show `0.0.0.0:5432` or `127.0.0.1:5432`

3. **Restart the database container**:
   ```bash
   docker compose restart db
   ```

### Authentication Failed Error

**Problem**: "FATAL: password authentication failed"

**Solutions**:
1. **Verify credentials in .env file**:
   ```bash
   cat .env | grep POSTGRES
   ```

2. **Check if .env file exists**:
   ```bash
   ls -la .env
   ```

3. **Reset database password** (if needed):
   - Stop containers: `docker compose down`
   - Update `.env` file with correct password
   - Start containers: `docker compose up -d`

### Database Does Not Exist Error

**Problem**: "FATAL: database 'cddbs' does not exist"

**Solutions**:
1. **Check actual database name**:
   ```bash
   docker compose exec db psql -U admin -l
   ```
   This lists all databases

2. **Create database if missing**:
   ```bash
   docker compose exec db psql -U admin -c "CREATE DATABASE cddbs;"
   ```

3. **Verify database name in .env**:
   Make sure `POSTGRES_DB` matches what you're connecting to

### Connection Timeout

**Problem**: Connection hangs or times out

**Solutions**:
1. **Check firewall settings**:
   - Ensure port 5432 is not blocked
   - On Linux: `sudo ufw status`

2. **Verify Docker port mapping**:
   ```bash
   docker compose ps db
   ```
   Should show `0.0.0.0:5432->5432/tcp`

3. **Try connecting from command line first**:
   ```bash
   docker compose exec db psql -U admin -d cddbs -c "SELECT version();"
   ```

## Quick Connection Test (Command Line)

Test your connection from the command line:

```bash
# Using docker compose
docker compose exec db psql -U admin -d cddbs -c "SELECT current_database(), current_user;"

# Or using psql directly (if installed locally)
psql -h localhost -p 5432 -U admin -d cddbs
```

## Connection String Format

If you need the connection string for other tools:

```
postgresql://admin:admin@localhost:5432/cddbs
```

Or with JDBC (for DBeaver):
```
jdbc:postgresql://localhost:5432/cddbs
```

## Viewing Database Tables

Once connected in DBeaver:

1. Expand your connection in the Database Navigator
2. Expand **"Databases"** → **"cddbs"** → **"Schemas"** → **"public"** → **"Tables"**
3. You should see:
   - `outlets` - News outlet information
   - `articles` - Fetched articles
   - `reports` - Analysis reports

## Common Queries

### View all outlets:
```sql
SELECT * FROM outlets;
```

### View recent reports:
```sql
SELECT id, outlet, country, created_at 
FROM reports 
ORDER BY created_at DESC 
LIMIT 10;
```

### View articles for an outlet:
```sql
SELECT a.id, a.title, a.link, a.created_at, o.name as outlet_name
FROM articles a
JOIN outlets o ON a.outlet_id = o.id
ORDER BY a.created_at DESC
LIMIT 20;
```

## Security Note

⚠️ **Important**: The default credentials (`admin/admin`) are for development only. For production, use strong passwords and restrict database access.

