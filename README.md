# 🍽️ Food Rescue

### Smart Food Waste Management Platform

Food Rescue is a **web-based platform that connects food donors with volunteers** who collect surplus food and deliver it to people in need.
The system reduces food waste while ensuring safe and timely food redistribution.

This project demonstrates a **real-world full-stack system design** including role-based dashboards, donation workflows, delivery verification, and public transparency through an impact feed.

---

# 🌍 Problem Statement

Large amounts of edible food are wasted every day by:

* Restaurants
* Households
* Events
* Cafeterias

At the same time, many people struggle with **food insecurity**.

Existing donation channels often fail because:

* donors don't know where to donate
* logistics are unorganized
* volunteers cannot discover available food quickly
* there is little transparency or proof of delivery

Food Rescue solves this by creating a **digital coordination platform** between donors and volunteers.

---

# 🎯 Project Objective

The platform enables:

### Donors

to post surplus food donations with location and expiry details.

### Volunteers

to discover nearby donations, pick them up, and deliver them.

### Public users

to see proof of completed deliveries through an **Impact Feed**, building trust.

---

# 🧠 Core Concept

The platform operates using a **donation lifecycle**.

```
Donor posts food
↓
Volunteer discovers donation
↓
Volunteer accepts pickup
↓
Food collected
↓
Food delivered
↓
Delivery photo uploaded
↓
Impact feed updated
```

---

# 🏗️ System Architecture

Food Rescue is built using a **monolithic Django architecture**.

```
Frontend (Templates)
        ↓
Django Views
        ↓
Django ORM
        ↓
SQLite Database
```

### Components

| Layer          | Technology                      |
| -------------- | ------------------------------- |
| Frontend       | Django Templates + Tailwind CSS |
| Backend        | Django                          |
| Database       | SQLite                          |
| Authentication | Django Auth                     |
| Interactivity  | Alpine.js                       |
| Styling        | Tailwind CSS                    |
| Maps           | Google Maps links               |
| Image uploads  | Pillow                          |

---

# 📁 Project Structure

```
food_rescue_project/

manage.py
requirements.txt

food_rescue_project/
    settings.py
    urls.py
    asgi.py
    wsgi.py

users/
    models.py
    views.py
    forms.py
    admin.py
    apps.py
    signals.py
    urls.py

templates/users/
    base.html
    landing.html
    impact_feed.html
    donor_dashboard.html
    volunteer_dashboard.html
    create_donation.html
    donation_detail.html
    mark_delivered.html
    login.html
    register.html
    volunteer_profile.html

static/

media/

templatetags/
    food_rescue_tags.py
```

---

# 👥 User Roles

The platform supports **two primary roles**.

## Donor

A donor is someone who has surplus food.

Examples:

* restaurants
* households
* event organizers

Donors can:

* create donations
* edit donations
* cancel donations
* track pickup status
* view delivery confirmation

---

## Volunteer

A volunteer is someone who collects and distributes food.

Volunteers can:

* discover available donations
* filter donations by distance and type
* accept pickup
* mark pickup status
* confirm delivery

---

# 🔁 Donation Lifecycle

Each donation moves through several states.

| Status     | Description                         |
| ---------- | ----------------------------------- |
| Available  | Donation posted and awaiting pickup |
| Accepted   | Volunteer accepted pickup           |
| Picked Up  | Volunteer collected food            |
| On The Way | Food is being delivered             |
| Delivered  | Delivery completed                  |
| Expired    | Donation expired                    |
| Cancelled  | Donor cancelled donation            |

---

# 📦 Core Features

## 1. Donation Posting

Donors create a food listing with:

* food name
* food type (veg/non-veg)
* approximate quantity
* expiry time
* pickup location
* optional image

Location can be:

* automatically detected via GPS
* entered manually

---

## 2. Volunteer Discovery System

Volunteers see available donations with filters.

Filters include:

* food type
* distance

Distance options:

```
1 km
2 km
5 km
10 km
```

---

## 3. Pickup Workflow

A volunteer can **accept a donation**.

Rule:

```
First volunteer to accept
gets the pickup
```

If already accepted, other volunteers see:

```
Accepted • Assigned to another volunteer
```

---

## 4. Delivery Confirmation

After delivery, the volunteer must upload a **delivery confirmation photo**.

This prevents fraud and verifies successful distribution.

---

## 5. Public Impact Feed

The platform includes a **public transparency page**.

Purpose:

* build trust
* show real-world impact
* encourage new users

The page displays:

* delivery image
* food name
* meals served
* city
* delivery time

Privacy protection:

The feed **does not show**

* donor name
* volunteer phone
* exact addresses

---

# 🔔 Notification System

Notifications keep users informed of important events.

Triggers include:

* volunteer accepts donation
* volunteer cancels pickup
* delivery completed
* new donation posted

Notifications appear in the **navbar dropdown**.

---

# 📍 Location Handling

Donations include:

```
pickup_address
latitude
longitude
```

Navigation uses Google Maps links.

Example:

```
https://www.google.com/maps?q=latitude,longitude
```

Volunteers can open the route directly.

---

# 📊 Dashboards

## Donor Dashboard

Displays:

* total donations
* meals saved
* active donations
* completed deliveries

Donors can manage their donations from this page.

---

## Volunteer Dashboard

Displays:

* available donations
* filters
* accepted pickups
* delivery status

Volunteers manage pickups here.

---

# 🎨 UI Design Philosophy

The UI follows **modern SaaS design principles**.

Key ideas:

* data-driven layout
* strong typography hierarchy
* minimal icon usage
* large whitespace
* gradient hero sections
* card-based dashboards

Images are minimized to avoid a **“student project look”**.

Impact is communicated through **numbers and structured cards** instead.

---

# 📱 Mobile Support

The platform is fully responsive.

Features optimized for mobile:

* camera image uploads
* large touch buttons
* stacked card layout
* responsive grids

---

# 🔐 Security Considerations

The platform includes:

* Django authentication
* CSRF protection
* role-based access control
* protected routes

Example:

```
Donor cannot access volunteer dashboard
Volunteer cannot edit donations
```

---

# ⚙️ Installation Guide

### 1. Clone repository

```
git clone <repository-url>
cd food_rescue
```

---

### 2. Install dependencies

```
pip install -r requirements.txt
```

---

### 3. Run migrations

```
python manage.py makemigrations
python manage.py migrate
```

---

### 4. Create admin account

```
python manage.py createsuperuser
```

---

### 5. Run server

```
python manage.py runserver
```

---

### Access application

```
http://localhost:8000
```

Admin panel:

```
http://localhost:8000/admin
```

---

# 🧪 Testing the Workflow

Example test scenario.

### Donor

1. Register as donor
2. Create donation
3. Enter location and expiry

### Volunteer

1. Register as volunteer
2. Accept donation
3. Mark picked up
4. Mark delivered
5. Upload delivery photo

### Public

1. Visit impact feed
2. See completed deliveries

---

# 🚀 Future Improvements

Possible future features:

* AI food recognition
* real-time volunteer tracking
* push notifications
* multilingual support
* NGO organization accounts
* food safety tracking
* rating and trust system

---

# 💡 Key Learning Outcomes

This project demonstrates:

* full-stack web development
* system design thinking
* role-based architecture
* workflow automation
* UI/UX design principles
* real-world social impact problem solving

---

# 🤝 Contribution

Contributions are welcome.

Possible contributions include:

* improving UI
* optimizing database queries
* adding analytics
* improving mobile experience

---

# 📜 License

This project is intended for educational and social impact purposes.

---

# ❤️ Vision

Food Rescue aims to create a world where **surplus food reaches people instead of landfills**.

Small acts of redistribution can create **massive collective impact**.

“Reduce waste. Feed people.”
