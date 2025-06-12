import datetime

class Record:
    def __init__(self, timestamp, water_gallons, electricity_kwh, gas_cubic_m, water_status, electricity_status, gas_status):
        self.timestamp = timestamp
        self.water_gallons = water_gallons
        self.electricity_kwh = electricity_kwh
        self.gas_cubic_m = gas_cubic_m
        self.water_status = water_status
        self.electricity_status = electricity_status
        self.gas_status = gas_status

class Material:
    def __init__(self, name, reuse_tip, recycle_tip, search_count=0):
        self.name = name
        self.reuse_tip = reuse_tip
        self.recycle_tip = recycle_tip
        self.search_count = search_count

utility_data = []
material_data = {}

def save_utility_usage(water, electricity, gas, water_status, electricity_status, gas_status):
    utility_data.append(Record(datetime.datetime.now(), water, electricity, gas, water_status, electricity_status, gas_status))

def get_utility_history(limit=10):
    return utility_data[-limit:]

def save_material(name, reuse_tip, recycle_tip):
    if name in material_data:
        material_data[name].search_count += 1
    else:
        material_data[name] = Material(name, reuse_tip, recycle_tip, 1)

def find_material(name):
    return material_data.get(name.lower(), None)

def get_popular_materials(n=5):
    return sorted(material_data.values(), key=lambda x: -x.search_count)[:n]
