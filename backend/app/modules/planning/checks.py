"""
Fasta regler för om ett fordon och en förare passar ett jobb.

Reglerna används både i planeringsvyn och för att kontrollera AI:ns förslag.
De ger varningar, inga stopp: transportledaren har sista ordet.
"""

from backend.app.models.entities import Driver, Vehicle


def order_datum(order: dict) -> str:
    """Dagen jobbet utförs: upphämtningsdatum, annars första leveransdatum."""
    datum = order.get("upphamtning", {}).get("datum", "")
    if datum:
        return datum
    return next((plats["datum"] for plats in order.get("leveranser", []) if plats.get("datum")), "")


def total_vikt(order: dict) -> float:
    return sum(rad.get("vikt_kg") or 0 for rad in order.get("gods", []))


def antal_pallar(order: dict) -> int:
    return sum(rad.get("antal") or 0 for rad in order.get("gods", []) if rad.get("typ") == "EUR-pall")


def kontrollera_jobb(order: dict, vehicle: Vehicle | None, driver: Driver | None) -> list[str]:
    """Varningar för ett enskilt jobb på ett visst fordon med en viss förare."""
    if vehicle is None:
        return []
    krav = order.get("krav", {})
    reg = vehicle.registration_number
    varningar = []
    if krav.get("kyl") and not vehicle.has_cooling:
        varningar.append(f"Kräver kyl, men {reg} har ingen kyl.")
    if krav.get("bakgavellyft") and not vehicle.has_tail_lift:
        varningar.append(f"Kräver bakgavellyft, men {reg} har ingen.")
    if krav.get("kran") and not vehicle.has_crane:
        varningar.append(f"Kräver kran, men {reg} har ingen.")
    if krav.get("adr"):
        if not vehicle.adr_approved:
            varningar.append(f"Farligt gods (ADR), men {reg} är inte ADR-godkänd.")
        if driver is not None and not driver.has_adr_license:
            varningar.append(f"Farligt gods (ADR), men {driver.name} saknar ADR-behörighet.")
    vikt = total_vikt(order)
    if vehicle.max_weight_kg is not None and vikt > vehicle.max_weight_kg:
        varningar.append(f"Godset väger {vikt:.0f} kg, men {reg} tar max {vehicle.max_weight_kg} kg.")
    pallar = antal_pallar(order)
    if vehicle.pallet_places is not None and pallar > vehicle.pallet_places:
        varningar.append(f"{pallar} pallar, men {reg} har bara {vehicle.pallet_places} pallplatser.")
    return varningar


def kontrollera_bil(ordrar: list[dict], vehicle: Vehicle, forare: list[Driver]) -> list[str]:
    """Varningar för en bils hela dag."""
    reg = vehicle.registration_number
    varningar = []
    vikt = sum(total_vikt(order) for order in ordrar)
    if vehicle.max_weight_kg is not None and vikt > vehicle.max_weight_kg:
        varningar.append(
            f"Dagens jobb väger totalt {vikt:.0f} kg (max {vehicle.max_weight_kg} kg). "
            "Det går bara om allt inte är lastat samtidigt."
        )
    pallar = sum(antal_pallar(order) for order in ordrar)
    if vehicle.pallet_places is not None and pallar > vehicle.pallet_places:
        varningar.append(
            f"Dagens jobb har totalt {pallar} pallar ({vehicle.pallet_places} platser). "
            "Det går bara om allt inte är lastat samtidigt."
        )
    namn = sorted({driver.name for driver in forare})
    if len(namn) > 1:
        varningar.append(f"Flera förare på samma bil samma dag: {', '.join(namn)}.")
    return varningar
