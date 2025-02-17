# O  l _x notiBot
Automated bot that scrapes ads and sends them via Facebook Messenger.

🚀 **Early Alpha Version** – This is a very early-stage version. Expect bugs, missing features, and potential issues.

## ⚠️ Status: Early Alpha  
- This is a **very early version** of the project .  
- The bot **requires manual configuration** – the search URL and Facebook user ID must be set in `config.json`.  
- Some features are missing or under development.
  
## ✅ Features
- 🔍 Scrapes new ads listings based on url with filters
- 📩 Sends messages via Facebook Messenger API
- 💾 Stores previously processed ads to avoid duplicates
- 🔄 Automatically restarts in case of failure (systemd support)

## 📝 To-Do
- [ ] message design
- [ ] Improve error handling and logging
- [ ] Add support for multiple search filters
- [ ] Create a web interface for managing searches
