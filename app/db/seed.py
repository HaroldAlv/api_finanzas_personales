from sqlmodel import Session, select
from app.models.financial import Account, Category

SEED_ACCOUNTS = [
    {"name": "Banco Caja Social",    "type": "bank"},
    {"name": "Bancolombia",          "type": "bank"},
    {"name": "Davivienda",           "type": "bank"},
    {"name": "Banco de Bogotá",      "type": "bank"},
    {"name": "BBVA",                 "type": "bank"},
    {"name": "Nequi",                "type": "digital_wallet"},
    {"name": "Daviplata",            "type": "digital_wallet"},
    {"name": "Efectivo",             "type": "cash"},
    {"name": "Éxito",                "type": "merchant"},
    {"name": "Carulla",              "type": "merchant"},
    {"name": "Alkosto",              "type": "merchant"},
    {"name": "Mercado Libre",        "type": "merchant"},
    {"name": "Falabella",            "type": "merchant"},
    {"name": "Homecenter",           "type": "merchant"},
    {"name": "Olímpica",             "type": "merchant"},
    {"name": "D1",                   "type": "merchant"},
    {"name": "Ara",                  "type": "merchant"},
]

SEED_CATEGORIES = [
    {"name": "Alimentación"},
    {"name": "Transporte"},
    {"name": "Vivienda"},
    {"name": "Servicios"},
    {"name": "Ocio y Entretenimiento"},
    {"name": "Salud"},
    {"name": "Educación"},
    {"name": "Ropa y Calzado"},
    {"name": "Otros"},
]

def run_seed(engine):
    """Ejecuta el seed data inicial si las tablas están vacías."""
    with Session(engine) as session:
        # Verificar e insertar Accounts
        statement_accounts = select(Account)
        accounts = session.exec(statement_accounts).first()
        if not accounts:
            for acc_data in SEED_ACCOUNTS:
                new_acc = Account(**acc_data)
                session.add(new_acc)
            
        # Verificar e insertar Categories
        statement_categories = select(Category)
        categories = session.exec(statement_categories).first()
        if not categories:
            for cat_data in SEED_CATEGORIES:
                new_cat = Category(name=cat_data["name"], description="Categoría genérica generada por seed.")
                session.add(new_cat)
                
        session.commit()
