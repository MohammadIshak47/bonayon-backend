"""Seed all 64 districts. Idempotent (matched by name_en). Run: python -m scripts.seed_districts

lat/lon are APPROXIMATE district headquarters coordinates, used only to query NASA POWER (which has ~50 km
resolution). Verify against an authoritative source before relying on them.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import District

# (division, name_en, name_bn, lat, lon)
DISTRICTS = [
    ("Dhaka", "Dhaka", "ঢাকা", 23.8103, 90.4125), ("Dhaka", "Gazipur", "গাজীপুর", 23.9999, 90.4203),
    ("Dhaka", "Narayanganj", "নারায়ণগঞ্জ", 23.6238, 90.5000), ("Dhaka", "Narsingdi", "নরসিংদী", 23.9322, 90.7151),
    ("Dhaka", "Manikganj", "মানিকগঞ্জ", 23.8617, 90.0003), ("Dhaka", "Munshiganj", "মুন্সিগঞ্জ", 23.5422, 90.5305),
    ("Dhaka", "Tangail", "টাঙ্গাইল", 24.2513, 89.9167), ("Dhaka", "Kishoreganj", "কিশোরগঞ্জ", 24.4449, 90.7766),
    ("Dhaka", "Faridpur", "ফরিদপুর", 23.6070, 89.8429), ("Dhaka", "Gopalganj", "গোপালগঞ্জ", 23.0051, 89.8266),
    ("Dhaka", "Madaripur", "মাদারীপুর", 23.1641, 90.1897), ("Dhaka", "Rajbari", "রাজবাড়ী", 23.7574, 89.6444),
    ("Dhaka", "Shariatpur", "শরীয়তপুর", 23.2423, 90.4348),
    ("Chattogram", "Chattogram", "চট্টগ্রাম", 22.3569, 91.7832), ("Chattogram", "Cox's Bazar", "কক্সবাজার", 21.4272, 92.0058),
    ("Chattogram", "Cumilla", "কুমিল্লা", 23.4607, 91.1809), ("Chattogram", "Feni", "ফেনী", 23.0159, 91.3976),
    ("Chattogram", "Brahmanbaria", "ব্রাহ্মণবাড়িয়া", 23.9571, 91.1115), ("Chattogram", "Rangamati", "রাঙ্গামাটি", 22.6533, 92.1753),
    ("Chattogram", "Noakhali", "নোয়াখালী", 22.8696, 91.0995), ("Chattogram", "Chandpur", "চাঁদপুর", 23.2513, 90.8518),
    ("Chattogram", "Lakshmipur", "লক্ষ্মীপুর", 22.9424, 90.8412), ("Chattogram", "Khagrachhari", "খাগড়াছড়ি", 23.1193, 91.9847),
    ("Chattogram", "Bandarban", "বান্দরবান", 22.1953, 92.2184),
    ("Rajshahi", "Rajshahi", "রাজশাহী", 24.3745, 88.6042), ("Rajshahi", "Bogura", "বগুড়া", 24.8465, 89.3773),
    ("Rajshahi", "Pabna", "পাবনা", 24.0064, 89.2372), ("Rajshahi", "Sirajganj", "সিরাজগঞ্জ", 24.4534, 89.7006),
    ("Rajshahi", "Natore", "নাটোর", 24.4206, 89.0003), ("Rajshahi", "Joypurhat", "জয়পুরহাট", 25.0968, 89.0227),
    ("Rajshahi", "Chapainawabganj", "চাঁপাইনবাবগঞ্জ", 24.5965, 88.2775), ("Rajshahi", "Naogaon", "নওগাঁ", 24.7936, 88.9318),
    ("Khulna", "Khulna", "খুলনা", 22.8456, 89.5403), ("Khulna", "Bagerhat", "বাগেরহাট", 22.6602, 89.7853),
    ("Khulna", "Satkhira", "সাতক্ষীরা", 22.7185, 89.0705), ("Khulna", "Jashore", "যশোর", 23.1664, 89.2081),
    ("Khulna", "Narail", "নড়াইল", 23.1725, 89.5127), ("Khulna", "Magura", "মাগুরা", 23.4873, 89.4199),
    ("Khulna", "Jhenaidah", "ঝিনাইদহ", 23.5448, 89.1539), ("Khulna", "Kushtia", "কুষ্টিয়া", 23.9013, 89.1205),
    ("Khulna", "Chuadanga", "চুয়াডাঙ্গা", 23.6402, 88.8418), ("Khulna", "Meherpur", "মেহেরপুর", 23.7622, 88.6318),
    ("Barishal", "Barishal", "বরিশাল", 22.7010, 90.3535), ("Barishal", "Bhola", "ভোলা", 22.6859, 90.6482),
    ("Barishal", "Jhalokati", "ঝালকাঠি", 22.6406, 90.1987), ("Barishal", "Patuakhali", "পটুয়াখালী", 22.3596, 90.3299),
    ("Barishal", "Pirojpur", "পিরোজপুর", 22.5791, 89.9759), ("Barishal", "Barguna", "বরগুনা", 22.1591, 90.1256),
    ("Sylhet", "Sylhet", "সিলেট", 24.8949, 91.8687), ("Sylhet", "Moulvibazar", "মৌলভীবাজার", 24.4829, 91.7774),
    ("Sylhet", "Habiganj", "হবিগঞ্জ", 24.3745, 91.4156), ("Sylhet", "Sunamganj", "সুনামগঞ্জ", 25.0658, 91.4073),
    ("Rangpur", "Rangpur", "রংপুর", 25.7439, 89.2752), ("Rangpur", "Dinajpur", "দিনাজপুর", 25.6217, 88.6354),
    ("Rangpur", "Kurigram", "কুড়িগ্রাম", 25.8054, 89.6361), ("Rangpur", "Gaibandha", "গাইবান্ধা", 25.3297, 89.5430),
    ("Rangpur", "Nilphamari", "নীলফামারী", 25.9310, 88.8560), ("Rangpur", "Lalmonirhat", "লালমনিরহাট", 25.9923, 89.2847),
    ("Rangpur", "Thakurgaon", "ঠাকুরগাঁও", 26.0337, 88.4616), ("Rangpur", "Panchagarh", "পঞ্চগড়", 26.3411, 88.5542),
    ("Mymensingh", "Mymensingh", "ময়মনসিংহ", 24.7471, 90.4203), ("Mymensingh", "Jamalpur", "জামালপুর", 24.9375, 89.9372),
    ("Mymensingh", "Netrokona", "নেত্রকোণা", 24.8700, 90.7279), ("Mymensingh", "Sherpur", "শেরপুর", 25.0205, 90.0153),
]


def seed(db: Session) -> int:
    assert len(DISTRICTS) == 64, "expected 64 districts"
    existing = {n for n in db.scalars(select(District.name_en))}
    new = [District(division=d, name_en=en, name_bn=bn, lat=lat, lon=lon) for d, en, bn, lat, lon in DISTRICTS if en not in existing]
    db.add_all(new)
    db.commit()
    return len(new)


if __name__ == "__main__":
    with SessionLocal() as session:
        print(f"Inserted {seed(session)} districts")
