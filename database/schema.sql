-- SIH26047 Smart Patient Case-Taking System
-- Run this in MySQL after logging in as a user with CREATE privileges:
--   mysql -u root -p < database/schema.sql

CREATE DATABASE IF NOT EXISTS patient_case_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE patient_case_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    full_name VARCHAR(120) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'doctor',
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS patients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id VARCHAR(30) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    age INT NOT NULL,
    gender VARCHAR(20) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    address TEXT NOT NULL,
    created_by_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_patients_user FOREIGN KEY (created_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS medical_cases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    case_number VARCHAR(30) NOT NULL UNIQUE,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    main_symptoms TEXT NOT NULL,
    duration VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    present_illness_description TEXT NOT NULL,
    symptoms_started VARCHAR(150) NOT NULL,
    progression TEXT NOT NULL,
    family_history TEXT NOT NULL,
    diet TEXT NOT NULL,
    sleep TEXT NOT NULL,
    lifestyle TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_cases_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    CONSTRAINT fk_cases_doctor FOREIGN KEY (doctor_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS medical_histories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    case_id INT NOT NULL UNIQUE,
    previous_diseases TEXT NOT NULL,
    previous_surgeries TEXT NOT NULL,
    hospitalizations TEXT NOT NULL,
    current_medications TEXT NOT NULL,
    allergies TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_history_case FOREIGN KEY (case_id) REFERENCES medical_cases(id) ON DELETE CASCADE
);

-- Additional tables (clinical_sessions, clinical_answers, clinical_summaries,
-- ayush_assessments, medical_documents, document_extractions, medications,
-- lab_results, medical_timeline, consents, red_flag_alerts, audit_logs)
-- and extra patient/user columns are created automatically by SQLAlchemy
-- and database/migrate.py when the Flask app starts.

