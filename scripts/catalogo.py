"""Catálogos fijos usados para generar los datos de ejemplo.

Todo lo que está aquí es ficticio pero plausible para un distribuidor
de vehículos y maquinaria en Nicaragua. Los montos están en córdobas (NIO).
"""

# (nombre, prefijo de código, descripción)
CATEGORIAS = [
    ("Filtros", "FIL", "Filtros de aceite, aire, combustible, cabina e hidráulicos"),
    ("Frenos", "FRE", "Pastillas, zapatas, discos y componentes de freno"),
    ("Suspensión y dirección", "SUS", "Amortiguadores, terminales, rótulas y bujes"),
    ("Motor", "MOT", "Componentes internos y periféricos del motor"),
    ("Sistema eléctrico", "ELE", "Alternadores, arranques, baterías, sensores e iluminación"),
    ("Transmisión y embrague", "TRA", "Embragues, juntas homocinéticas y kits de arrastre"),
    ("Enfriamiento", "ENF", "Bombas de agua, termostatos, radiadores y refrigerantes"),
    ("Lubricantes", "LUB", "Aceites de motor, transmisión, hidráulicos y grasas"),
    ("Hidráulica", "HID", "Componentes hidráulicos y de cucharón para maquinaria"),
]

# (nombre, país, contacto, teléfono, email, días de entrega mín, máx)
PROVEEDORES = [
    ("Importadora Nipona de Repuestos S.A.", "Japón", "Kenji Watanabe", "+81 3-5555-0142", "ventas@nipona-repuestos.example", 20, 35),
    ("Seúl Auto Parts Co., Ltd.", "Corea del Sur", "Min-jun Park", "+82 2-5555-0187", "export@seulautoparts.example", 20, 35),
    ("Distribuidora Centroamericana de Autopartes S.A.", "Costa Rica", "Andrea Solís", "+506 2555-0123", "pedidos@dcautopartes.example", 7, 12),
    ("Heavy Equipment Supply Inc.", "Estados Unidos", "Mike Robertson", "+1 305-555-0164", "orders@hesupply.example", 15, 25),
    ("MotoPartes Panamá S.A.", "Panamá", "Luis Carrasco", "+507 555-0109", "ventas@motopartespa.example", 7, 12),
    ("Lubricantes y Químicos de Nicaragua S.A.", "Nicaragua", "María José Rocha", "+505 2255-0171", "ventas@lubriquim.example", 3, 6),
    ("Autopartes del Pacífico S.A.", "Nicaragua", "Roberto Gutiérrez", "+505 2255-0138", "compras@autopacifico.example", 3, 6),
    ("Camiones y Partes de México S.A. de C.V.", "México", "Alejandra Fuentes", "+52 55-5555-0196", "ventas@camionespartes.example", 10, 15),
]

# Qué proveedor surte cada marca. Las que no aparecen las surte Autopartes del Pacífico.
PROVEEDOR_POR_MARCA = {
    "Toyota Genuine Parts": "Importadora Nipona de Repuestos S.A.",
    "Denso": "Importadora Nipona de Repuestos S.A.",
    "Aisin": "Importadora Nipona de Repuestos S.A.",
    "Akebono": "Importadora Nipona de Repuestos S.A.",
    "Exedy": "Importadora Nipona de Repuestos S.A.",
    "KYB": "Importadora Nipona de Repuestos S.A.",
    "NGK": "Importadora Nipona de Repuestos S.A.",
    "555": "Importadora Nipona de Repuestos S.A.",
    "Koyorad": "Importadora Nipona de Repuestos S.A.",
    "Hyundai Mobis": "Seúl Auto Parts Co., Ltd.",
    "Sakura": "Seúl Auto Parts Co., Ltd.",
    "Bosch": "Distribuidora Centroamericana de Autopartes S.A.",
    "Valeo": "Distribuidora Centroamericana de Autopartes S.A.",
    "Monroe": "Distribuidora Centroamericana de Autopartes S.A.",
    "Moog": "Distribuidora Centroamericana de Autopartes S.A.",
    "TRW": "Distribuidora Centroamericana de Autopartes S.A.",
    "Brembo": "Distribuidora Centroamericana de Autopartes S.A.",
    "Mahle": "Distribuidora Centroamericana de Autopartes S.A.",
    "Victor Reinz": "Distribuidora Centroamericana de Autopartes S.A.",
    "Gates": "Distribuidora Centroamericana de Autopartes S.A.",
    "WIX": "Distribuidora Centroamericana de Autopartes S.A.",
    "Fleetguard": "Heavy Equipment Supply Inc.",
    "Donaldson": "Heavy Equipment Supply Inc.",
    "Parker": "Heavy Equipment Supply Inc.",
    "Eaton": "Heavy Equipment Supply Inc.",
    "Yamaha Genuine Parts": "MotoPartes Panamá S.A.",
    "DID": "MotoPartes Panamá S.A.",
    "Mobil": "Lubricantes y Químicos de Nicaragua S.A.",
    "Castrol": "Lubricantes y Químicos de Nicaragua S.A.",
    "Shell": "Lubricantes y Químicos de Nicaragua S.A.",
    "Hino Genuine Parts": "Camiones y Partes de México S.A. de C.V.",
}

# Marcas de repuesto alternativo (aftermarket) por categoría.
MARCAS_POR_CATEGORIA = {
    "Filtros": ["Denso", "Bosch", "Sakura", "WIX"],
    "Frenos": ["Akebono", "Bosch", "Brembo", "TRW"],
    "Suspensión y dirección": ["KYB", "Monroe", "555", "Moog"],
    "Motor": ["Victor Reinz", "Mahle", "Aisin", "Gates"],
    "Sistema eléctrico": ["Denso", "Bosch", "Valeo", "NGK"],
    "Transmisión y embrague": ["Exedy", "Aisin", "Valeo"],
    "Enfriamiento": ["Aisin", "Gates", "Koyorad"],
    "Lubricantes": ["Mobil", "Castrol", "Shell"],
    "Hidráulica": ["Parker", "Gates", "Eaton"],
}
# Para camiones y maquinaria se prefieren marcas de servicio pesado.
MARCAS_PESADAS = {
    "Filtros": ["Fleetguard", "Donaldson"],
    "Hidráulica": ["Parker", "Eaton"],
}

# Clase de vehículo -> multiplicador de costo y factor de demanda.
CLASES = {
    "auto": {"costo": 1.0, "demanda": 1.0},
    "camion": {"costo": 1.7, "demanda": 0.5},
    "moto": {"costo": 0.35, "demanda": 1.2},
    "maquinaria": {"costo": 2.6, "demanda": 0.3},
}

# Grupos de modelos que comparten repuestos (misma plataforma o motor).
# código -> etiqueta, clase, marca original (o None), popularidad, modelos
# Cada modelo: (marca, modelo, año desde, año hasta, tipo)
GRUPOS = {
    "TGD": {
        "etiqueta": "Toyota diésel 2.4/2.8 (GD)", "clase": "auto",
        "oem": "Toyota Genuine Parts", "popularidad": 1.5,
        "modelos": [
            ("Toyota", "Hilux", 2016, 2024, "vehiculo"),
            ("Toyota", "Fortuner", 2016, 2024, "vehiculo"),
            ("Toyota", "Land Cruiser Prado", 2016, 2023, "vehiculo"),
        ],
    },
    "TKD": {
        "etiqueta": "Toyota diésel 2.5/3.0 (KD)", "clase": "auto",
        "oem": "Toyota Genuine Parts", "popularidad": 1.2,
        "modelos": [
            ("Toyota", "Hilux", 2005, 2015, "vehiculo"),
            ("Toyota", "Fortuner", 2005, 2015, "vehiculo"),
            ("Toyota", "Hiace", 2005, 2018, "vehiculo"),
        ],
    },
    "TGA": {
        "etiqueta": "Toyota gasolina 1.5–2.5", "clase": "auto",
        "oem": "Toyota Genuine Parts", "popularidad": 1.3,
        "modelos": [
            ("Toyota", "Corolla", 2014, 2019, "vehiculo"),
            ("Toyota", "Corolla", 2020, 2025, "vehiculo"),
            ("Toyota", "Yaris", 2018, 2024, "vehiculo"),
            ("Toyota", "RAV4", 2019, 2025, "vehiculo"),
        ],
    },
    "HYK": {
        "etiqueta": "Hyundai/Kia gasolina", "clase": "auto",
        "oem": "Hyundai Mobis", "popularidad": 1.0,
        "modelos": [
            ("Hyundai", "Tucson", 2016, 2021, "vehiculo"),
            ("Hyundai", "Accent", 2018, 2023, "vehiculo"),
            ("Hyundai", "Creta", 2017, 2024, "vehiculo"),
            ("Kia", "Sportage", 2016, 2021, "vehiculo"),
        ],
    },
    "NMI": {
        "etiqueta": "Nissan Frontier / Mitsubishi L200", "clase": "auto",
        "oem": None, "popularidad": 0.8,
        "modelos": [
            ("Nissan", "Frontier NP300", 2016, 2024, "vehiculo"),
            ("Mitsubishi", "L200", 2016, 2024, "vehiculo"),
        ],
    },
    "CAM": {
        "etiqueta": "Camiones Hino/Isuzu", "clase": "camion",
        "oem": "Hino Genuine Parts", "popularidad": 1.0,
        "modelos": [
            ("Hino", "Serie 300", 2012, 2024, "vehiculo"),
            ("Hino", "Serie 500", 2010, 2024, "vehiculo"),
            ("Isuzu", "NPR", 2010, 2023, "vehiculo"),
        ],
    },
    "MYA": {
        "etiqueta": "Motos Yamaha 125–150", "clase": "moto",
        "oem": "Yamaha Genuine Parts", "popularidad": 1.3,
        "modelos": [
            ("Yamaha", "YBR 125", 2010, 2024, "motocicleta"),
            ("Yamaha", "FZ 150", 2014, 2024, "motocicleta"),
            ("Yamaha", "XTZ 125", 2012, 2024, "motocicleta"),
        ],
    },
    "MOT": {
        "etiqueta": "Motos Honda/Suzuki 125–150", "clase": "moto",
        "oem": None, "popularidad": 0.9,
        "modelos": [
            ("Honda", "XR150L", 2015, 2024, "motocicleta"),
            ("Suzuki", "GN125", 2010, 2024, "motocicleta"),
        ],
    },
    "RET": {
        "etiqueta": "Retroexcavadoras CAT/John Deere", "clase": "maquinaria",
        "oem": None, "popularidad": 1.0,
        "modelos": [
            ("Caterpillar", "416F", 2014, 2022, "maquinaria"),
            ("John Deere", "310L", 2015, 2024, "maquinaria"),
        ],
    },
    "EXC": {
        "etiqueta": "Excavadoras Komatsu/CAT", "clase": "maquinaria",
        "oem": None, "popularidad": 0.8,
        "modelos": [
            ("Komatsu", "PC200-8", 2010, 2020, "maquinaria"),
            ("Caterpillar", "320", 2017, 2024, "maquinaria"),
        ],
    },
    "TRC": {
        "etiqueta": "Tractores agrícolas MF/John Deere", "clase": "maquinaria",
        "oem": None, "popularidad": 1.2,
        "modelos": [
            ("Massey Ferguson", "290", 2008, 2020, "maquinaria"),
            ("John Deere", "5075E", 2014, 2024, "maquinaria"),
        ],
    },
}

AUTOS = ["TGD", "TKD", "TGA", "HYK", "NMI"]
DIESEL = ["TGD", "TKD", "NMI", "CAM", "RET", "EXC", "TRC"]
MOTOS = ["MYA", "MOT"]
MAQUINARIA = ["RET", "EXC", "TRC"]
TODOS = AUTOS + ["CAM"] + MOTOS + MAQUINARIA

# Repuestos específicos: se crea uno por cada grupo de la lista.
# (categoría, nombre, grupos, costo base mín, costo base máx, demanda)
# El costo base es para autos; se ajusta con el multiplicador de la clase.
PLANTILLAS = [
    ("Filtros", "Filtro de aceite", TODOS, 220, 480, "alta"),
    ("Filtros", "Filtro de aire", TODOS, 380, 900, "alta"),
    ("Filtros", "Filtro de combustible", ["TGD", "TKD", "TGA", "HYK", "NMI", "CAM", "RET", "EXC", "TRC"], 450, 1100, "media"),
    ("Filtros", "Filtro de cabina (A/C)", AUTOS, 300, 650, "media"),
    ("Filtros", "Filtro hidráulico", MAQUINARIA, 900, 1800, "media"),
    ("Filtros", "Separador de agua", ["CAM", "RET", "EXC", "TRC"], 700, 1400, "media"),
    ("Frenos", "Pastillas de freno delanteras", AUTOS + MOTOS, 1200, 2800, "alta"),
    ("Frenos", "Pastillas de freno traseras", ["TGA", "HYK", "TGD"], 1000, 2200, "media"),
    ("Frenos", "Zapatas de freno traseras", ["TGD", "TKD", "NMI", "CAM", "MYA", "MOT"], 900, 2000, "media"),
    ("Frenos", "Disco de freno delantero", AUTOS, 1800, 4200, "media"),
    ("Frenos", "Cilindro de rueda trasero", ["TKD", "CAM"], 600, 1300, "baja"),
    ("Suspensión y dirección", "Amortiguador delantero", AUTOS + ["CAM"], 2200, 5200, "media"),
    ("Suspensión y dirección", "Terminal de dirección", AUTOS, 650, 1500, "media"),
    ("Suspensión y dirección", "Rótula inferior", AUTOS, 900, 2100, "media"),
    ("Suspensión y dirección", "Rodamiento de rueda delantera", AUTOS, 900, 2200, "media"),
    ("Suspensión y dirección", "Buje de barra estabilizadora", ["TGD", "TGA", "HYK"], 180, 420, "media"),
    ("Motor", "Juego de empaques de culata", AUTOS + ["CAM"], 2500, 6500, "baja"),
    ("Motor", "Kit de banda de distribución", ["TKD", "HYK", "NMI"], 3500, 7800, "baja"),
    ("Motor", "Bomba de aceite", ["TGD", "TKD", "CAM"], 4500, 9500, "baja"),
    ("Motor", "Inyector diésel", ["TGD", "TKD", "NMI", "CAM"], 7500, 16000, "baja"),
    ("Motor", "Banda de accesorios", AUTOS + ["CAM"], 450, 1100, "media"),
    ("Motor", "Kit de pistón y anillos", MOTOS, 2800, 5500, "baja"),
    ("Sistema eléctrico", "Alternador", ["TGD", "TKD", "TGA", "HYK", "CAM", "RET", "TRC"], 9000, 19000, "baja"),
    ("Sistema eléctrico", "Motor de arranque", ["TGD", "TKD", "TGA", "HYK", "CAM", "RET", "EXC", "TRC"], 8500, 18000, "baja"),
    ("Sistema eléctrico", "Juego de bujías (4)", ["TGA", "HYK"], 900, 2400, "media"),
    ("Sistema eléctrico", "Bujía", MOTOS, 350, 650, "alta"),
    ("Sistema eléctrico", "Sensor de oxígeno", ["TGA", "HYK"], 2800, 6000, "baja"),
    ("Sistema eléctrico", "Sensor ABS delantero", ["TGD", "TGA", "HYK"], 2200, 4800, "baja"),
    ("Sistema eléctrico", "Faro delantero", ["TGD", "TGA", "HYK"], 4500, 11000, "baja"),
    ("Transmisión y embrague", "Kit de embrague", AUTOS + ["CAM"] + MOTOS, 5500, 12500, "baja"),
    ("Transmisión y embrague", "Junta homocinética", ["TGD", "TGA", "HYK"], 3200, 7000, "baja"),
    ("Transmisión y embrague", "Kit de arrastre (cadena y piñones)", MOTOS, 3600, 6500, "media"),
    ("Transmisión y embrague", "Cable de clutch", MOTOS, 600, 1200, "media"),
    ("Enfriamiento", "Bomba de agua", ["TGD", "TKD", "TGA", "HYK", "NMI", "CAM", "RET", "TRC"], 2800, 6500, "baja"),
    ("Enfriamiento", "Termostato", AUTOS + ["CAM"], 550, 1300, "media"),
    ("Enfriamiento", "Radiador", ["TGD", "TKD", "TGA", "HYK", "CAM"], 7000, 15000, "baja"),
    ("Enfriamiento", "Manguera superior de radiador", ["TGD", "TKD", "TGA", "HYK"], 450, 1000, "media"),
    ("Hidráulica", "Kit de sellos de cilindro hidráulico", ["RET", "EXC"], 1100, 2400, "media"),
    ("Hidráulica", "Bomba hidráulica", MAQUINARIA, 22000, 42000, "baja"),
    ("Hidráulica", "Manguera hidráulica de alta presión", MAQUINARIA, 1000, 2200, "media"),
    ("Hidráulica", "Diente de cucharón", ["RET", "EXC"], 500, 1100, "media"),
    ("Hidráulica", "Pasador de cucharón", ["RET", "EXC"], 750, 1600, "baja"),
]

# Repuestos universales: un solo producto que sirve para varios grupos.
# (categoría, nombre, grupos compatibles, costo mín, costo máx, demanda)
UNIVERSALES = [
    ("Lubricantes", "Aceite de motor 15W-40 diésel (galón)", DIESEL, 950, 1250, "alta"),
    ("Lubricantes", "Aceite de motor 5W-30 sintético (galón)", ["TGA", "HYK"], 1300, 1700, "alta"),
    ("Lubricantes", "Aceite 20W-50 para moto 4T (litro)", MOTOS, 260, 380, "alta"),
    ("Lubricantes", "Aceite hidráulico ISO 68 (cubeta 5 gal)", MAQUINARIA, 4200, 5600, "media"),
    ("Lubricantes", "Aceite de transmisión 75W-90 (litro)", AUTOS + ["CAM"], 420, 650, "media"),
    ("Lubricantes", "Grasa multipropósito EP2 (libra)", DIESEL + MOTOS, 160, 260, "alta"),
    ("Frenos", "Líquido de frenos DOT 4 (500 ml)", AUTOS + ["CAM"] + MOTOS, 230, 340, "alta"),
    ("Enfriamiento", "Refrigerante premezclado 50/50 (galón)", AUTOS + ["CAM"] + MAQUINARIA, 520, 760, "alta"),
    ("Sistema eléctrico", "Batería 12V 70Ah", ["TGA", "HYK"], 4800, 6200, "media"),
    ("Sistema eléctrico", "Batería 12V 100Ah", ["TGD", "TKD", "NMI", "RET", "TRC"], 6800, 8900, "media"),
    ("Sistema eléctrico", "Batería 12V 7Ah para moto", MOTOS, 1100, 1600, "media"),
    ("Sistema eléctrico", "Bombillo halógeno H4 12V", ["TKD", "NMI", "CAM", "MYA", "MOT"], 120, 240, "media"),
]

# Transacciones por semana y cantidad máxima por transacción.
DEMANDA = {
    "alta": {"transacciones": 1.2, "cantidad_max": 4},
    "media": {"transacciones": 0.5, "cantidad_max": 2},
    "baja": {"transacciones": 0.12, "cantidad_max": 1},
}

# (nombre, código, ciudad, departamento, dirección, teléfono, peso de demanda)
SUCURSALES = [
    ("Managua Central", "MGA", "Managua", "Managua", "Carretera Norte, km 4.5", "2255-0100", 2.2),
    ("León", "LEO", "León", "León", "Bypass de León, frente a la rotonda Guadalupe", "2311-0200", 1.0),
    ("Granada", "GRA", "Granada", "Granada", "Carretera Masaya–Granada, km 45", "2552-0300", 0.8),
    ("Chinandega", "CHI", "Chinandega", "Chinandega", "Carretera a Corinto, km 133", "2341-0400", 0.9),
    ("Estelí", "EST", "Estelí", "Estelí", "Carretera Panamericana Norte, km 148", "2713-0500", 0.8),
]
