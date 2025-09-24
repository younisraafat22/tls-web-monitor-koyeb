# Koyeb TLS Web Monitor - Deployment Guide

This directory contains the Koyeb-optimized deployment for the TLS Web Monitor tool.

## 🌟 Why Koyeb?

- **100% Free Tier**: 512MB RAM, no time limits, always-on
- **Native Docker Support**: Reliable Chrome installation through containers
- **Global Edge Network**: Fast deployment across multiple regions
- **Zero Configuration**: Deploy directly from GitHub or Docker

## 🚀 Quick Deployment

### Method 1: Docker Hub Deployment (Recommended)

1. **Push to Docker Hub** (one-time setup):
   ```bash
   # Build and push Docker image
   docker build -t yourusername/tls-web-monitor-koyeb .
   docker push yourusername/tls-web-monitor-koyeb
   ```

2. **Deploy on Koyeb**:
   - Go to [Koyeb Dashboard](https://app.koyeb.com/)
   - Click "Create App"
   - Select "Docker" as deployment method
   - Enter Docker image: `yourusername/tls-web-monitor-koyeb:latest`
   - Set environment variables (see below)
   - Click "Deploy"

### Method 2: GitHub Deployment

1. **Create new GitHub repository** with Koyeb deployment files
2. **Connect to Koyeb**:
   - Go to [Koyeb Dashboard](https://app.koyeb.com/)
   - Click "Create App"
   - Select "GitHub" and connect your repository
   - Koyeb will automatically detect the Dockerfile
   - Set environment variables (see below)
   - Click "Deploy"

## ⚙️ Required Environment Variables

Set these in the Koyeb dashboard during deployment:

```bash
# Mark as Koyeb deployment
KOYEB_DEPLOYMENT=true

# Chrome optimization
CHROME_BIN=/usr/bin/google-chrome-stable

# Python optimization
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
```

## 📧 Email Configuration

Update `config.json` with your email settings:

```json
{
  "notification": {
    "email": {
      "enabled": true,
      "sender_email": "your-email@gmail.com",
      "sender_password": "your-app-password",
      "receiver_email": "notification@gmail.com",
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "subject": "🎯 TLS Visa Slots Available!"
    }
  }
}
```

## 🔧 Advanced Configuration

### Custom Chrome Options
The Koyeb version includes optimized Chrome settings for cloud deployment:
- Memory optimization for 512MB limit
- Enhanced Cloudflare bypass
- Container-specific error handling

### Monitoring Settings
- **Check Interval**: 5-15 minutes (configurable)
- **Months to Check**: 1-3 months ahead
- **Auto-retry**: Built-in error recovery
- **Health Checks**: Automatic service monitoring

## 🛠️ Development & Testing

### Local Testing
```bash
# Test Docker container locally
docker build -t tls-monitor-koyeb .
docker run -p 5000:5000 --env-file .env tls-monitor-koyeb

# Test with docker-compose
docker-compose up --build
```

### Debug Mode
Enable debug logging by updating `config.json`:
```json
{
  "debug_mode": true,
  "log_level": "DEBUG"
}
```

## 📊 Monitoring & Logs

- **Web Interface**: Available at `https://your-app-name.koyeb.app`
- **Koyeb Logs**: View in Koyeb dashboard under "Logs" tab
- **Health Checks**: Automatic endpoint monitoring
- **Email Alerts**: Immediate notifications when slots are found

## 🚨 Troubleshooting

### Common Issues

1. **Chrome Not Found**:
   - Check Dockerfile Chrome installation
   - Verify CHROME_BIN environment variable
   - Review Koyeb build logs

2. **Memory Limits**:
   - Monitor memory usage in Koyeb dashboard
   - Adjust Chrome options if needed
   - Consider reducing check frequency

3. **Email Not Sending**:
   - Verify SMTP settings in config.json
   - Check app passwords for Gmail
   - Review email provider security settings

### Debug Commands
```bash
# Check Chrome installation
which google-chrome
google-chrome --version

# Test Selenium
python -c "from selenium import webdriver; print('Selenium OK')"

# Check memory usage
free -m
```

## 🎯 Deployment Checklist

- [ ] Update `config.json` with your TLS credentials
- [ ] Configure email notifications
- [ ] Set required environment variables
- [ ] Test Docker build locally
- [ ] Deploy to Koyeb
- [ ] Verify Chrome installation in logs
- [ ] Test login functionality
- [ ] Monitor for successful slot checks

## 💰 Cost Optimization

Koyeb's free tier includes:
- 512MB RAM (sufficient for headless Chrome)
- 5GB storage (more than enough)
- 100GB bandwidth/month
- No time limits or sleep

Perfect for running this monitoring tool 24/7 at zero cost!

## 🔄 Updates & Maintenance

- **Auto-updates**: Configure GitHub webhook for automatic redeployment
- **Monitoring**: Use Koyeb's built-in metrics and alerts
- **Scaling**: Upgrade to paid tier if needed for higher frequency

## 📞 Support

For Koyeb deployment issues:
1. Check Koyeb documentation: https://www.koyeb.com/docs
2. Review application logs in Koyeb dashboard
3. Test Docker container locally first
4. Contact Koyeb support if needed

---

**Happy Visa Hunting! 🎯**

This Koyeb deployment ensures your TLS visa slot monitor runs reliably in the cloud with zero cost and maximum uptime.