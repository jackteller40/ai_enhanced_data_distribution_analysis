import psycopg2
from faker import Faker
import random
import json

# Initialize Faker
fake = Faker()

# Database Connection Settings
DB_CONFIG = {
    "dbname": "foxi",
    "user": "admin",
    "password": "secret",
    "host": "127.0.0.1",
    "port": "5433"
}

# Enum Options from your schema
MATCH_TYPES = ['romantic', 'roommate']
SEARCHING_TYPES = ['something serious', 'open for anything', 'short-term fun']
GENDERS = ['woman', 'man', 'nonbinary', 'queer/other']
GENDER_PREFS = ['women', 'men', 'nonbinary/queer identities', 'everyone']
SLEEP_SCHEDULES = ['early bird', 'night owl', 'flexible']
GUEST_FREQS = ['often', 'rarely', 'sometimes']

def seed_database():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("Connected to database. Starting seed...")

        for i in range(20):
            # 1. ACCOUNTS
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1,99)}@marist.edu"
            
            cur.execute("""
                INSERT INTO accounts (email, password_hash)
                VALUES (%s, %s) RETURNING profile_id;
            """, (email, "hashed_password_placeholder"))
            
            profile_id = cur.fetchone()[0]

            # 2. PROFILES
            display_name = f"{first_name} {last_name}"
            major = random.choice(['Computer Science', 'Fashion', 'Business', 'Psychology', 'Digital Media'])
            grad_year = random.randint(2024, 2028)
            clubs = random.sample(['SGA', 'Computer Societ', 'Dance Ensemble', 'Club Volleyball', 'Esports'], k=random.randint(1, 3))
            
            cur.execute("""
                INSERT INTO profiles (
                    profile_id, display_name, major, graduation_year, clubs, 
                    bio, looking_for, romantically_searching_for, gender
                ) VALUES (%s, %s, %s, %s, %s, %s, %s::match_type_enum[], %s, %s::self_gender[]);
            """, (
                profile_id, display_name, major, grad_year, clubs,
                fake.paragraph(nb_sentences=2),
                random.sample(MATCH_TYPES, k=random.randint(1, 2)),
                random.choice(SEARCHING_TYPES),
                [random.choice(GENDERS)]
            ))

            # 3. ROMANTIC PREFERENCES
            romantic_weights = {
                "major": round(random.uniform(0, 1), 1),
                "clubs": round(random.uniform(0, 1), 1),
                "smoking": 1.0
            }
            
            cur.execute("""
                INSERT INTO romantic_preferences (
                    profile_id, interested_in_genders, own_gender, 
                    min_grad_yr, max_grad_yr, priority_weights
                ) VALUES (%s, %s::gender_preference[], %s, %s, %s, %s);
            """, (
                profile_id, 
                [random.choice(GENDER_PREFS)], 
                random.choice(GENDERS),
                grad_year - 2, grad_year + 2,
                json.dumps(romantic_weights)
            ))

            # 4. ROOMMATE PREFERENCES
            roommate_weights = {"cleanliness": 0.8, "noise_tolerance": 0.5}
            
            cur.execute("""
                INSERT INTO roommate_preferences (
                    profile_id, sleep_schedule, cleanliness, noise_tolerance,
                    guests_frequency, on_campus, priority_weights
                ) VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (
                profile_id,
                random.choice(SLEEP_SCHEDULES),
                random.randint(1, 5),
                random.randint(1, 5),
                random.choice(GUEST_FREQS),
                random.choice([True, False]),
                json.dumps(roommate_weights)
            ))

            # 5. PROFILE PHOTOS (Placeholder Base64)
            cur.execute("""
                INSERT INTO profile_photos (profile_id, photo_base64, position)
                VALUES (%s, %s, %s);
            """, (profile_id, "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==", 0))

        conn.commit()
        print(f"Successfully seeded 20 users!")

    except Exception as e:
        print(f"Error seeding data: {e}")
        if conn:
            conn.rollback()
    finally:
        if cur: cur.close()
        if conn: conn.close()

if __name__ == "__main__":
    seed_database()