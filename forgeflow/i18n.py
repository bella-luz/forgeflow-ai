"""Languages for the demo site and the outreach email."""
from __future__ import annotations

LANGUAGES = ["English", "Spanish", "French", "German", "Italian", "Portuguese"]
AUTO = "Auto (from the client's country)"

_BY_COUNTRY = {
    "Spanish": ("spain", "espana", "españa", "mexico", "méxico", "argentina", "colombia", "chile", "peru", "perú",
                "venezuela", "ecuador", "guatemala", "cuba", "bolivia", "dominican republic", "honduras", "paraguay",
                "el salvador", "nicaragua", "costa rica", "panama", "panamá", "uruguay"),
    "French": ("france", "belgium", "belgique", "luxembourg", "monaco", "senegal", "ivory coast", "cote d'ivoire", "morocco", "tunisia"),
    "German": ("germany", "deutschland", "austria", "österreich", "osterreich", "switzerland", "schweiz", "liechtenstein"),
    "Italian": ("italy", "italia", "san marino"),
    "Portuguese": ("portugal", "brazil", "brasil", "angola", "mozambique"),
}

_DIAL_CODES = {
    "spain": "34", "espana": "34", "españa": "34", "france": "33", "germany": "49", "italy": "39", "portugal": "351",
    "united kingdom": "44", "uk": "44", "england": "44", "ireland": "353", "pakistan": "92", "united states": "1",
    "usa": "1", "canada": "1", "mexico": "52", "netherlands": "31", "belgium": "32", "austria": "43", "switzerland": "41",
}


def language_for(country: str) -> str:
    c = (country or "").strip().lower()
    for language, countries in _BY_COUNTRY.items():
        if c in countries:
            return language
    return "English"


def resolve(choice: str, country: str) -> str:
    return choice if choice in LANGUAGES else language_for(country)


def whatsapp_number(phone: str, country: str) -> str:
    """International digits for a wa.me link, or empty when the country code is unknown."""
    digits = "".join(ch for ch in phone or "" if ch.isdigit())
    if not digits:
        return ""
    if phone.strip().startswith("+"):
        return digits
    if digits.startswith("00"):
        return digits[2:]
    code = _DIAL_CODES.get((country or "").strip().lower(), "")
    return code + digits.lstrip("0") if code and len(digits) >= 8 else ""


LABELS = {
    "English": {
        "lang": "en", "services": "Services", "about": "About us", "contact": "Contact", "address": "Address",
        "phone": "Phone", "email": "Email", "hours": "Opening hours", "find_us": "Find us",
        "notice": "Concept demo. This is not the official website of this business.", "prepared_by": "Prepared by",
        "contact_pending": "Contact details will be added once confirmed with the business.",
        "example_note": "Example services. We will replace these with your real ones.",
        "call": "Call now", "whatsapp": "WhatsApp", "directions": "Get directions", "your_name": "Your name",
        "your_phone": "Your phone", "service": "Service", "date": "Preferred date", "message": "Message",
        "send": "Send request", "demo_form": "Demo form: requests are not sent yet.", "footer": "Concept demo",
    },
    "Spanish": {
        "lang": "es", "services": "Servicios", "about": "Sobre nosotros", "contact": "Contacto", "address": "Dirección",
        "phone": "Teléfono", "email": "Correo electrónico", "hours": "Horario", "find_us": "Dónde estamos",
        "notice": "Demostración conceptual. Este no es el sitio web oficial de este negocio.", "prepared_by": "Preparado por",
        "contact_pending": "Los datos de contacto se añadirán cuando se confirmen con el negocio.",
        "example_note": "Servicios de ejemplo. Los cambiaremos por los tuyos.",
        "call": "Llamar ahora", "whatsapp": "WhatsApp", "directions": "Cómo llegar", "your_name": "Tu nombre",
        "your_phone": "Tu teléfono", "service": "Servicio", "date": "Fecha preferida", "message": "Mensaje",
        "send": "Enviar solicitud", "demo_form": "Formulario de demostración: aún no se envían solicitudes.",
        "footer": "Demostración conceptual",
    },
    "French": {
        "lang": "fr", "services": "Services", "about": "À propos", "contact": "Contact", "address": "Adresse",
        "phone": "Téléphone", "email": "E-mail", "hours": "Horaires", "find_us": "Nous trouver",
        "notice": "Démonstration conceptuelle. Ceci n'est pas le site officiel de cette entreprise.", "prepared_by": "Préparé par",
        "contact_pending": "Les coordonnées seront ajoutées après confirmation avec l'entreprise.",
        "example_note": "Services d'exemple. Nous les remplacerons par les vôtres.",
        "call": "Appeler", "whatsapp": "WhatsApp", "directions": "Itinéraire", "your_name": "Votre nom",
        "your_phone": "Votre téléphone", "service": "Service", "date": "Date souhaitée", "message": "Message",
        "send": "Envoyer la demande", "demo_form": "Formulaire de démonstration : les demandes ne sont pas encore envoyées.",
        "footer": "Démonstration conceptuelle",
    },
    "German": {
        "lang": "de", "services": "Leistungen", "about": "Über uns", "contact": "Kontakt", "address": "Adresse",
        "phone": "Telefon", "email": "E-Mail", "hours": "Öffnungszeiten", "find_us": "So finden Sie uns",
        "notice": "Konzept-Demo. Dies ist nicht die offizielle Website dieses Unternehmens.", "prepared_by": "Erstellt von",
        "contact_pending": "Kontaktdaten werden nach Bestätigung durch das Unternehmen ergänzt.",
        "example_note": "Beispielleistungen. Wir ersetzen sie durch Ihre eigenen.",
        "call": "Jetzt anrufen", "whatsapp": "WhatsApp", "directions": "Route planen", "your_name": "Ihr Name",
        "your_phone": "Ihre Telefonnummer", "service": "Leistung", "date": "Wunschtermin", "message": "Nachricht",
        "send": "Anfrage senden", "demo_form": "Demo-Formular: Anfragen werden noch nicht gesendet.",
        "footer": "Konzept-Demo",
    },
    "Italian": {
        "lang": "it", "services": "Servizi", "about": "Chi siamo", "contact": "Contatti", "address": "Indirizzo",
        "phone": "Telefono", "email": "E-mail", "hours": "Orari", "find_us": "Dove siamo",
        "notice": "Demo concettuale. Questo non è il sito ufficiale di questa attività.", "prepared_by": "Preparato da",
        "contact_pending": "I contatti saranno aggiunti dopo la conferma con l'attività.",
        "example_note": "Servizi di esempio. Li sostituiremo con i tuoi.",
        "call": "Chiama ora", "whatsapp": "WhatsApp", "directions": "Indicazioni", "your_name": "Il tuo nome",
        "your_phone": "Il tuo telefono", "service": "Servizio", "date": "Data preferita", "message": "Messaggio",
        "send": "Invia richiesta", "demo_form": "Modulo dimostrativo: le richieste non vengono ancora inviate.",
        "footer": "Demo concettuale",
    },
    "Portuguese": {
        "lang": "pt", "services": "Serviços", "about": "Sobre nós", "contact": "Contacto", "address": "Morada",
        "phone": "Telefone", "email": "E-mail", "hours": "Horário", "find_us": "Onde estamos",
        "notice": "Demonstração conceptual. Este não é o site oficial deste negócio.", "prepared_by": "Preparado por",
        "contact_pending": "Os contactos serão adicionados após confirmação com o negócio.",
        "example_note": "Serviços de exemplo. Vamos substituí-los pelos teus.",
        "call": "Ligar agora", "whatsapp": "WhatsApp", "directions": "Como chegar", "your_name": "O teu nome",
        "your_phone": "O teu telefone", "service": "Serviço", "date": "Data preferida", "message": "Mensagem",
        "send": "Enviar pedido", "demo_form": "Formulário de demonstração: os pedidos ainda não são enviados.",
        "footer": "Demonstração conceptual",
    },
}

OPT_OUT = {
    "English": 'If you would rather not hear from me again, reply "no thanks" and I will not contact you further.',
    "Spanish": 'Si prefiere no recibir más mensajes, responda "no, gracias" y no volveré a escribirle.',
    "French": 'Si vous préférez ne plus recevoir de messages, répondez « non merci » et je ne vous recontacterai pas.',
    "German": 'Wenn Sie keine weiteren Nachrichten wünschen, antworten Sie einfach „nein danke“ und ich melde mich nicht wieder.',
    "Italian": 'Se preferisce non ricevere altri messaggi, risponda "no grazie" e non la contatterò più.',
    "Portuguese": 'Se preferir não receber mais mensagens, responda "não, obrigado" e não voltarei a contactá-lo.',
}
