# Face Authentication System

A modern, secure, and intelligent facial recognition-based authentication system with a clean web interface, real-time logging, and user management. Built using Flask, OpenCV, and the `face_recognition` library.

##  Features

- Register new users with 5 face samples
- Authenticate users in real-time using webcam input
- Dashboard with live statistics
- View authentication logs
- Soft-delete users (removes access but keeps record)
- Confidence threshold for secure recognition
- RESTful API endpoints for all major operations

## Tech Stack

- **Backend**: Python, Flask
- **Frontend**: HTML, CSS, JavaScript
- **Libraries**: `face_recognition`, `OpenCV`, `NumPy`
- **Database**: SQLite

## Installation

bash
git clone https://github.com/JokePeralta/Facial-Authentication-System-Prototype.git
cd face-auth-system
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt


## Running the App

bash
python app.py


Then visit:
http://localhost:5000 in your browser.

## Directory Structure


face-auth-system/
│
├── app.py                   # Main Flask app
├── database.py              # Database handling logic
├── templates/               # HTML frontend pages
│   ├── dashboard.html
│   ├── register.html
│   ├── authenticate.html
│   └── logs.html               
├── requirements.txt         # Dependencies
└── README.md


## API Endpoints

| Endpoint            | Method | Description               |
| ------------------- | ------ | ------------------------- |
| `/api/register`     | POST   | Register a new user       |
| `/api/authenticate` | POST   | Authenticate user         |
| `/api/check_face`   | POST   | Check if face is detected |
| `/api/delete_user`  | POST   | Soft-delete a user        |
| `/api/get_users`    | GET    | Get list of all users     |
| `/api/logs`         | GET    | Get recent auth logs      |
| `/api/stats`        | GET    | Get dashboard statistics  |

## How It Works

* During **registration**, user provides 5 face samples. Their encodings are averaged and stored.
* During **authentication**, a live webcam frame is compared with known encodings using facial distance.
* System logs every authentication attempt with time, user, confidence, and status (success/failed).
* All operations are handled securely on the backend using Flask and `face_recognition`.

## To Do

* Add liveliness detection (optional)
* Add login system for admin dashboard (optional)
* Extend to cloud-based storage or API gateway (optional)

## 👨‍💻 Author

Developed by **Shreyas Mali**

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).

```
