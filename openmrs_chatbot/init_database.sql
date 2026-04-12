-- ==============================================================================
-- OpenMRS Clinical Chatbot - Initial Database Schema
-- ==============================================================================
-- This SQL creates basic tables for the chatbot to function
-- Run this after creating the chatbot_dev database
--
-- Usage: mysql -u root -p chatbot_dev < init_database.sql

USE chatbot_dev;

-- ============================================================================
-- CORE TABLES (for chatbot testing without full OpenMRS)
-- ============================================================================

-- Person table (stores demographic information)
CREATE TABLE IF NOT EXISTS person (
    person_id INT PRIMARY KEY AUTO_INCREMENT,
    gender VARCHAR(1) NOT NULL CHECK (gender IN ('M', 'F', 'O', 'U')),
    birthdate DATE,
    dead BOOLEAN DEFAULT FALSE,
    death_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Patient table (extends person)
CREATE TABLE IF NOT EXISTS patient (
    patient_id INT PRIMARY KEY,
    FOREIGN KEY (patient_id) REFERENCES person(person_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Patient identifier (stores unique IDs like Medical Record Number)
CREATE TABLE IF NOT EXISTS patient_identifier (
    patient_identifier_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id INT NOT NULL,
    identifier VARCHAR(255) NOT NULL,
    identifier_type INT,
    voided BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
    UNIQUE KEY unique_identifier (patient_id, identifier)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Person name (stores patient names)
CREATE TABLE IF NOT EXISTS person_name (
    person_name_id INT PRIMARY KEY AUTO_INCREMENT,
    person_id INT NOT NULL,
    given_name VARCHAR(255),
    family_name VARCHAR(255),
    voided BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (person_id) REFERENCES person(person_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Person address
CREATE TABLE IF NOT EXISTS person_address (
    person_address_id INT PRIMARY KEY AUTO_INCREMENT,
    person_id INT NOT NULL,
    address1 VARCHAR(255),
    address2 VARCHAR(255),
    city_village VARCHAR(255),
    state_province VARCHAR(255),
    postal_code VARCHAR(255),
    voided BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (person_id) REFERENCES person(person_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Encounters (clinical visits)
CREATE TABLE IF NOT EXISTS encounter (
    encounter_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id INT NOT NULL,
    encounter_type INT,
    encounter_datetime DATETIME NOT NULL,
    voided BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patient(patient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Observations (vital signs, lab results, etc.)
CREATE TABLE IF NOT EXISTS obs (
    obs_id INT PRIMARY KEY AUTO_INCREMENT,
    person_id INT NOT NULL,
    concept_id INT,
    obs_datetime DATETIME NOT NULL,
    value_numeric DECIMAL(10,2),
    value_text TEXT,
    voided BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (person_id) REFERENCES person(person_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Medications/Drug Orders
CREATE TABLE IF NOT EXISTS drug_order (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id INT NOT NULL,
    concept_id INT,
    drug_id INT,
    start_date DATE NOT NULL,
    auto_expire_date DATE,
    discontinued BOOLEAN DEFAULT FALSE,
    voided BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patient(patient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ============================================================================
-- SAMPLE DATA (for testing)
-- ============================================================================

-- Insert sample patient
INSERT INTO person (person_id, gender, birthdate, dead) VALUES
(1, 'M', '1990-05-15', FALSE),
(2, 'F', '1985-03-22', FALSE),
(3, 'M', '1995-07-10', FALSE);

INSERT INTO patient (patient_id) VALUES (1), (2), (3);

-- Insert patient identifiers
INSERT INTO patient_identifier (patient_id, identifier, identifier_type) VALUES
(1, 'MRN001', 1),
(2, 'MRN002', 1),
(3, 'MRN003', 1);

-- Insert patient names
INSERT INTO person_name (person_id, given_name, family_name) VALUES
(1, 'John', 'Smith'),
(2, 'Jane', 'Doe'),
(3, 'Robert', 'Johnson');

-- Insert addresses
INSERT INTO person_address (person_id, address1, city_village, state_province, postal_code) VALUES
(1, '123 Main St', 'Springfield', 'IL', '62701'),
(2, '456 Oak Ave', 'Chicago', 'IL', '60601'),
(3, '789 Elm St', 'Peoria', 'IL', '61601');

-- ============================================================================
-- INDEXES (for better performance)
-- ============================================================================

CREATE INDEX idx_patient_person ON patient(patient_id);
CREATE INDEX idx_patient_identifier ON patient_identifier(patient_id);
CREATE INDEX idx_person_name ON person_name(person_id);
CREATE INDEX idx_person_address ON person_address(person_id);
CREATE INDEX idx_encounter_patient ON encounter(patient_id);
CREATE INDEX idx_obs_person ON obs(person_id);
CREATE INDEX idx_drug_order_patient ON drug_order(patient_id);

-- ============================================================================
-- SUMMARY
-- ============================================================================
-- Tables created: 9
-- Sample patients: 3 (IDs: 1, 2, 3)
--
-- NOTE: This is a minimal schema for testing. For full OpenMRS functionality,
-- you would need the complete OpenMRS database schema with all 50+ tables.
-- This basic setup allows the chatbot to function without a full OpenMRS instance.
-- ============================================================================
