# 🎯 LeadGen India

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Google Sheets](https://img.shields.io/badge/Google%20Sheets-34A853?style=for-the-badge&logo=google-sheets&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)

**AI-powered local business lead generation for Indian SMBs**

[Features](#-features) • [Tech Stack](#-tech-stack) • [How It Works](#-how-it-works) • [Screenshots](#-screenshots)

</div>


## 🚀 Features

### 🔍 Smart Lead Discovery
- **Google Maps Integration** - Scrapes local businesses using SerpAPI
- **Multi-City Search** - Target businesses across 20+ Indian cities
- **Quick Presets** - Healthcare, Wedding, Fitness, Education industry bundles
- **Advanced Filters** - Filter by score, rating, reviews, city, business type

### 🤖 AI-Powered Scoring
- **Dual Scoring System** - Rule-based + AI scoring (Google Gemini)
- **Website Analysis** - Detects SSL, mobile optimization, WhatsApp, booking systems
- **Urgency Detection** - Identifies HIGH/MEDIUM/LOW priority leads
- **Personalized Pitches** - AI generates custom pitch for each lead

### 📊 Data Management
- **Google Sheets Integration** - Auto-save leads with deduplication
- **Excel Export** - Multi-sheet export with city breakdown
- **CSV Export** - Simple data export
- **Real-time Progress** - Live pipeline status updates

### 💼 Lead Enrichment
- **Hunter.io Integration** - Automatic email finding
- **Contact Discovery** - Phone, email, website extraction
- **Business Intelligence** - Ratings, reviews, address, business type
- **Tech Stack Detection** - Identifies technologies used on websites

### 🎨 Modern Dashboard
- **Dark Theme UI** - Beautiful gradient design with custom fonts
- **Lead Cards** - Enhanced cards with action buttons (Call, Email, Copy Pitch)
- **Analytics Dashboard** - 5 key metrics + 4 interactive charts
- **Notes & Tags** - Add notes, tags, status, last contact date

## 🛠️ Tech Stack

### Core Technologies
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![Asyncio](https://img.shields.io/badge/Asyncio-3776AB?style=flat-square&logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white)

### APIs & Services
![SerpAPI](https://img.shields.io/badge/SerpAPI-4285F4?style=flat-square&logo=google&logoColor=white)
![OpenRouter](https://img.shields.io/badge/OpenRouter-412991?style=flat-square&logo=openai&logoColor=white)
![Google Sheets](https://img.shields.io/badge/Google%20Sheets-34A853?style=flat-square&logo=google-sheets&logoColor=white)
![Hunter.io](https://img.shields.io/badge/Hunter.io-FF6B35?style=flat-square&logo=hunter&logoColor=white)


## 🎯 How It Works

### 1️⃣ Search & Scrape
```
User Input → SerpAPI → Google Maps Results → Website Scraping
```
- Define business type + city combinations
- Fetch 20 results per query from Google Maps
- Scrape websites for technical signals
- Extract contact information

### 2️⃣ Score & Filter
```
Raw Leads → Rule-Based Scoring → AI Scoring → Qualified Leads
```
- **Rule-Based**: No website (10/10), Missing SSL (+2), No mobile (+2)
- **AI Scoring**: Gemini Flash 1.5 analyzes website content
- **Filtering**: Only leads with score ≥ 7 (configurable)

### 3️⃣ Enrich & Save
```
Qualified Leads → Hunter.io Email → Google Sheets → Export
```
- Find emails using Hunter.io domain search
- Save to Google Sheets with deduplication
- Export as CSV/Excel with multiple sheets
- Add notes, tags, and status tracking

## 📈 Scoring System

### Rule-Based Signals (1-10 points)
| Signal | Score Impact |
|--------|-------------|
| No website | 10/10 (highest priority) |
| Social media only | 9/10 |
| Missing SSL | +2 points |
| Not mobile optimized | +2 points |
| No WhatsApp | +1.5 points |
| No booking system | +1.5 points |

### AI Scoring (1-10 points)
- Website content analysis
- Digital maturity assessment
- Service opportunity identification
- Custom pitch generation

## 🎨 Dashboard Features

### 📋 Results Tab
- **Summary Metrics**: Total found, qualified leads, saved to sheet, avg score, high urgency
- **Advanced Filters**: Score range, urgency, rating, reviews, city, business type
- **Sorting Options**: By score, rating, reviews, urgency
- **Lead Cards**: Company info, contact details, signals, AI pitch
- **Action Buttons**: Call, Email, Copy Pitch, Add Notes

### 📊 Analytics Tab
- **Key Metrics**: Total leads, avg score, high urgency, no website, avg rating
- **Charts**: 
  - Score distribution histogram
  - Urgency breakdown pie chart
  - Top 10 cities bar chart
  - Business type distribution

### ⚙️ Settings Tab
- **Configuration Status**: API keys, Google Sheets setup
- **Documentation**: Setup guide, scoring explanation, search tips
- **Advanced Options**: Neighborhood targeting, competitor analysis

## 🌟 Key Highlights

✅ **Fully Async** - Concurrent scraping for 10x faster processing  
✅ **Smart Deduplication** - By company name + phone across pipeline  
✅ **Flexible Config** - .env file OR manual dashboard input  
✅ **Optional Sheets** - Works with or without Google Sheets  
✅ **Real-time Progress** - Live updates during pipeline execution  
✅ **Mobile Responsive** - Works on desktop, tablet, mobile  
✅ **Error Handling** - Graceful failures with detailed logging  
✅ **Cron Ready** - Automated weekly lead generation  


## 🎯 Use Cases

### 🏢 For Agencies
- Generate leads for web development services
- Find businesses needing digital transformation
- Target specific industries and cities
- Export leads for CRM integration

### 💼 For Freelancers
- Discover local businesses without websites
- Identify businesses with poor digital presence
- Generate personalized outreach pitches
- Track lead status and follow-ups

### 📊 For Market Research
- Analyze digital maturity by industry
- Compare cities and business types
- Track technology adoption trends
- Export data for further analysis

---
<div align="center">

**⭐ Star this repo if you find it useful!**

</div>
