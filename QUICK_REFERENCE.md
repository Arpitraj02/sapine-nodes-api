# 🎯 Sapine Bot Hosting - Quick Reference Card

## Installation Commands

```bash
# One-click installation (Recommended!)
./install.sh

# Start the API
./start.sh

# Test the API
./test-api.sh
```

## API URLs

- 🏠 **Root**: http://localhost:8000/
- 📖 **Docs**: http://localhost:8000/docs
- 🔍 **ReDoc**: http://localhost:8000/redoc
- ❤️ **Health**: http://localhost:8000/health

## Authentication

### Register
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepass123"}'
```

### Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepass123"}'
```

### Get Profile
```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Database Commands

```bash
# Access PostgreSQL
docker exec -it sapine-postgres-db psql -U sapine_user -d sapine_bots

# View logs
docker logs sapine-postgres-db

# Stop database
docker stop sapine-postgres-db

# Start database
docker start sapine-postgres-db
```

## Application Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Start API manually
python -m app.main

# Install dependencies
pip install -r requirements.txt

# Check environment
cat .env
```

## File Structure

```
sapine-nodes-api/
├── install.sh          # 🎯 One-click installer (USE THIS!)
├── start.sh            # 🚀 Quick start script
├── test-api.sh         # 🧪 API testing script
├── SETUP_GUIDE.md      # 📖 Detailed setup guide
├── requirements.txt    # 📦 Python dependencies (with email-validator!)
├── .env               # 🔐 Your credentials (auto-generated)
└── app/
    ├── main.py        # 🏠 Main API application
    ├── auth.py        # 🔑 Authentication
    ├── models.py      # 📊 Database models
    ├── utils.py       # 🛠️ Utilities
    ├── db.py          # 💾 Database config
    ├── bots.py        # 🤖 Bot management
    ├── docker.py      # 🐳 Docker integration
    └── sockets.py     # 📡 WebSocket endpoints
```

## Common Issues & Solutions

### Issue: Email validator error
**Solution**: Already fixed! `email-validator` is in requirements.txt

### Issue: Docker permission denied
**Solution**: 
```bash
sudo usermod -aG docker $USER
# Log out and log back in
```

### Issue: Port already in use
**Solution**: Change PORT in .env file or kill the process:
```bash
sudo lsof -i :8000
```

### Issue: Database connection failed
**Solution**: 
```bash
docker start sapine-postgres-db
```

## Environment Variables

Key variables in `.env`:

- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - Auto-generated secret for JWT
- `PORT` - API port (default: 8000)
- `BOT_STORAGE_PATH` - Where bot files are stored

## Pro Tips

1. ✅ Always use `./install.sh` for first setup
2. ✅ Use `./start.sh` to quickly start the API
3. ✅ Run `./test-api.sh` to verify everything works
4. ✅ Visit `/docs` for interactive API documentation
5. ✅ Never commit your `.env` file!
6. ✅ Check logs if something goes wrong
7. ✅ Keep your dependencies updated

## Need Help?

- 📖 [SETUP_GUIDE.md](SETUP_GUIDE.md) - Complete setup guide
- 📚 [README.md](README.md) - Full documentation
- 🔒 [SECURITY.md](SECURITY.md) - Security features
- 🧪 [Testing.md](Testing.md) - Testing guide

## Docker Compose Alternative

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f
```

---

**Made with ❤️ for easy setup on Ubuntu!**
