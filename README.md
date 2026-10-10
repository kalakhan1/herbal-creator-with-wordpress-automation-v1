# 🌿 Herbal Creator

Local Windows app — SEO Product + Blog Post generator for WooCommerce/WordPress.
No AI, no API, no internet needed. Pure Python.

**Multi-client ready** — change `Settings` page and reuse for any store.

---

## ✨ Features

- **Products** → CSV for WooCommerce (manual import)
- **Posts** → WordPress draft (REST API auto-push)
- **Batches** — organize products/posts in groups with category + tags + attributes
- **10 Keyword Types** — Focus, Primary, Short-tail, Long-tail, Navigational, Informational, Transactional, Commercial, Secondary, Semantic
- **Rank Math Fields** — Meta Title, Meta Description, Slug, Focus Keyword (with strict char limits)
- **SEO Score** — 14 checks, targets 80-85%
- **Internal Linking** — Product↔Product, Post↔Post, Post↔Product + About Us page
- **Pros & Cons** block on every article
- **Images** — Custom size + 9 CSS filters + uniform output
- **Multi-image posts** — 3 slots per post
- **WhatsApp button** on every article
- **Multi-client** — Settings page for store name, WhatsApp, currency, etc.

---

## 🚀 STEP 1 — Install Python

1. Download Python 3.10+ → https://www.python.org/downloads/
2. **Tick "Add Python to PATH"** at bottom of installer
3. Click Install Now

Verify:
```powershell
python --version
```

---

## 🚀 STEP 2 — Setup Project

```powershell
cd "C:\path\to\herbal_creator"
.\setup.ps1
```

If script is blocked:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then run setup again.

---

## 🚀 STEP 3 — Configure `.env`

Open `.env`:
```powershell
notepad .env
```

Fill in:
```
STORE_NAME=Your Store Name
STORE_WHATSAPP=923xxxxxxxxx
STORE_WHATSAPP_DISPLAY=+92 xxx xxx xxxx
WP_BASE_URL=https://your-site.com
WP_USERNAME=admin
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
```

### WordPress Application Password

1. WordPress → **Users → Profile**
2. Scroll to **Application Passwords**
3. Name: `Herbal Creator`
4. Click **Add New**
5. Copy password (spaces included)
6. Paste in `.env`

If section missing, add to `wp-config.php`:
```php
define('WP_APP_PASSWORDS_ENABLED', true);
```

---

## 🚀 STEP 4 — Run

```powershell
.\start.ps1
```

Open browser: **http://127.0.0.1:5000**

---

## 📖 Daily Workflow

### Products

1. Go to `/products`
2. **Create Batch:** name + category (Oils/Syrups/Majoon/etc.) + tags + attributes
3. **Add Products:** paste names → select batch → click Add
4. **⚡ Generate Batch** — generates 5 at a time
5. **🔗 Build Internal Links** — connects all products
6. **Export** → download CSV
7. **WooCommerce → Products → Import** — upload CSV

### Posts

1. Go to `/posts`
2. **Create Batch** — same as products
3. **Add Post** — title + source content (500+ words)
4. **⚡ Generate Batch**
5. **🖼 Post Images** (click on `0/3` button in Images column) — upload 3 images per post
6. **🔗 Build Internal Links**
7. **WordPress page** → push drafts

### Images

1. Go to `/images`
2. Set **Output Settings:** width, height, mode (Fit for uniform), bg color, quality, CSS filter
3. **🔍** on any tile → Google Images search
4. **Drag** downloaded image → tile → auto WebP + uniform size
5. **🔧 Rebuild** — change filter/size on existing

---

## 🌐 Publishing to WordPress

### Products → Manual WooCommerce Import

1. Export CSV → download
2. WordPress → **WooCommerce → Products → Import**
3. Upload CSV
4. Column mapping → **Import as meta data** for Rank Math fields
5. Tick **Update existing products** → Run

### Posts → Auto Draft via REST API

1. WordPress page → **🔌 Test Connection**
2. **👁 Dry Run** → preview titles
3. **📝 Create Drafts** → creates as drafts
4. WP Admin → Posts → Drafts → review + Publish manually

### Images → Either

- **REST API:** WordPress page → **⬆ Upload Images**
- **Manual:** Copy `uploads/products/` + `uploads/posts/` → WP Media Library

---

## 🌐 GitHub Setup

### First Time

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

### Push to GitHub

1. Create repo at https://github.com/new (Private recommended)
2. In project:
```powershell
git init
git branch -M main
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/herbal_creator.git
git push -u origin main
```

**Password:** GitHub needs Personal Access Token, not password:
1. https://github.com/settings/tokens
2. Generate new token (classic) → tick `repo` scope → copy
3. Use as password

### Future Updates

```powershell
git add .
git commit -m "Update message"
git push
```

### ⚠️ Never Commit

- `.env` (contains credentials)
- `.venv/`
- `data/`
- `uploads/`
- `output/`

All are in `.gitignore` — verify with `git status`.

---

## 📁 Folder Structure

```
herbal_creator/
├── main.py, config.py, database.py
├── requirements.txt, .env, .env.example
├── setup.ps1, start.ps1
├── services/
│   ├── text_engine.py, seo_service.py
│   ├── duplicate_service.py, internal_link_service.py
│   ├── keyword_strategy_service.py, page_service.py
│   ├── image_service.py, csv_service.py, wordpress_service.py
├── routes/
│   ├── dashboard.py, products.py, posts.py
│   ├── images.py, export.py, wordpress.py
│   ├── settings.py, pages.py, logs.py
├── templates/
│   ├── base.html, dashboard.html, products.html
│   ├── posts.html, images.html, pages.html
│   ├── settings.html, export.html, wordpress.html, logs.html
├── static/
│   ├── style.css, app.js
└── (auto folders: data/, logs/, uploads/, output/)
```

---

## 🔧 Troubleshooting

**Python not found:** reinstall with "Add to PATH"

**Scripts disabled:** `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

**Cannot reach WordPress:** check `.env` URL (no trailing slash, https://)

**Authentication failed:** username is login name, not email; App Password includes spaces

**Batch fails:** check `.env` has correct categories in dropdown; minimum 1 category required

**Content too similar:** regenerate with different title or source

**Slow generation:** reduce word count to 600

**Database reset:** `Remove-Item data\herbal.db`

**NLTK data missing:**
```powershell
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('stopwords')"
```

---

## 🔐 Security

- Never share `.env` on chat/email
- Use Private GitHub repo
- Rotate WordPress App Password every 90 days
- Only run on trusted local network

---

**Built for Khan Herbal Stores · Pure Python · Multi-client Ready**