from memory.profile_manager import ProfileManager

pm = ProfileManager()

pm.create("person_001")

print(pm.load("person_001"))

