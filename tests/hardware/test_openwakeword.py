from openwakeword.model import Model

model = Model()

print("Available wake words:")
for name in model.models.keys():
    print("-", name)
