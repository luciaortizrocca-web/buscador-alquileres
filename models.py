from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

@dataclass
class Propiedad:
    id: str
    portal: str
    titulo: str
    tipo: str  # PH, Casa, Departamento
    precio: int
    expensas: int
    moneda: str  # ARS
    barrio: str
    direccion: str
    ambientes: str
    superficie_m2: str
    tiene_exterior: bool
    detalle_exterior: str  # Balcón, Terraza, Patio
    url: str
    fecha_encontrado: str = ""

    def __post_init__(self):
        if not self.fecha_encontrado:
            self.fecha_encontrado = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def precio_total(self) -> int:
        return self.precio + (self.expensas if self.expensas > 0 else 0)

    def to_csv_row(self) -> list:
        return [
            self.fecha_encontrado,
            self.portal,
            self.id,
            self.tipo,
            self.barrio,
            self.direccion,
            f"{self.precio:,}".replace(",", "."),
            f"{self.expensas:,}".replace(",", ".") if self.expensas > 0 else "0",
            f"{self.precio_total:,}".replace(",", "."),
            self.ambientes,
            self.superficie_m2,
            self.detalle_exterior if self.tiene_exterior else "No",
            self.titulo,
            self.url,
            "Pendiente"  # Estado para que el usuario gestione en la planilla
        ]

    def formatear_alerta_telegram(self) -> str:
        simbolo = "$"
        precio_fmt = f"{self.precio:,}".replace(",", ".")
        exp_fmt = f"{self.expensas:,}".replace(",", ".") if self.expensas > 0 else "Sin expensas / No especifica"
        total_fmt = f"{self.precio_total:,}".replace(",", ".")
        
        exterior_ico = "🌿" if "patio" in self.detalle_exterior.lower() else "☀️"
        exterior_str = f"{exterior_ico} *Espacio al aire libre*: {self.detalle_exterior}" if self.tiene_exterior else "⚠️ Sin exterior explícito"
        
        msg = (
            f"🏠 *¡Nueva propiedad encontrada!* ({self.portal})\n\n"
            f"📍 *{self.tipo} en {self.barrio}*\n"
            f"📌 `{self.direccion}`\n\n"
            f"💰 *Alquiler*: {simbolo} {precio_fmt}\n"
            f"🧾 *Expensas*: {exp_fmt}\n"
            f"💵 *Costo Total Estimado*: {simbolo} {total_fmt}\n\n"
            f"🚪 *Ambientes*: {self.ambientes}\n"
            f"📐 *Superficie*: {self.superficie_m2}\n"
            f"{exterior_str}\n\n"
            f"📝 *{self.titulo}*\n\n"
            f"🔗 [Abrir Publicación en {self.portal}]({self.url})"
        )
        return msg
